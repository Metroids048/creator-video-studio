"""Offline publication revisions. No account, upload, model or render calls."""
from html import escape
from pathlib import Path
import re
import math
import shutil
import struct
import tempfile
import zipfile
import content_strategy


def source(studio, project, version):
    project = studio.identifier(project)
    if not re.fullmatch(r"v[0-9]{4,}", version):
        raise ValueError("发布必须绑定确切制作版本")
    path = studio.works_root() / project / "versions" / version
    receipt = studio.check_delivery(path)
    return path, {"project": project, "version": version,
                  "video_sha256": receipt["delivery"]["video.mp4"],
                  "receipt_sha256": studio.digest(path / "receipt.json")}


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} 不能为空")
    return value.strip()


def png_size(path):
    with path.open("rb") as stream:
        header = stream.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError("封面必须是 PNG")
    width, height = struct.unpack(">II", header[16:24])
    if not width or not height:
        raise ValueError("封面尺寸无效")
    return [width, height]


def packaging_quality(spec, require_image_bindings=True):
    """Validate recorded provenance; this cannot authenticate a tool call or judge aesthetics."""
    research = spec.get("cover_research")
    if not isinstance(research, dict) or not research.get("references"):
        raise ValueError("新包装必须提供封面参考研究 cover_research")
    text(research.get("selection_reason"), "封面参考取舍")
    refs = set()
    for ref in research["references"]:
        ref_id = text(ref.get("id"), "封面参考ID")
        if ref_id in refs or not re.match(r"https://[^/]+/", text(ref.get("url"), "参考原帖")):
            raise ValueError("封面参考ID重复或缺少HTTPS原帖链接")
        refs.add(ref_id)
        for field in ("checked_at", "metrics_source", "visual_observation", "relevance", "limitation"):
            text(ref.get(field), f"封面参考 {field}")
        metrics = ref.get("metrics")
        if not isinstance(metrics, dict) or not metrics or set(metrics) - {"likes", "views"}:
            raise ValueError("参考指标须区分 likes/views，未知用 null")
        if any(v is not None and (type(v) not in (int, float) or not math.isfinite(v) or v < 0)
               for v in metrics.values()):
            raise ValueError("参考指标须为非负数或 null")
    model_exposed = True
    for cover in spec["covers"]:
        gen = cover.get("generation")
        if not isinstance(gen, dict) or gen.get("tool") != "image_gen.imagegen" or gen.get("requested_model") != "Codex Image 2":
            raise ValueError("新封面须记录 Codex Image 2 原生图像工具来源，不得静默替换")
        if "reported_model" not in gen or gen["reported_model"] not in (None, "gpt-image-2", "Image 2", "Codex Image 2"):
            raise ValueError("模型未暴露须填 null；已报告其他模型不能冒充 Image 2")
        model_exposed = model_exposed and gen["reported_model"] is not None
        for field in ("prompt", "evidence"):
            text(gen.get(field), f"封面生成 {field}")
        if gen.get("image_sha256") != cover["sha256"]:
            raise ValueError("封面生成记录与实际图片哈希不符")
        ids = gen.get("reference_ids")
        if not isinstance(ids, list) or not ids or not all(isinstance(x, str) and x in refs for x in ids):
            raise ValueError("封面生成须引用本次研究中已查看的参考")
    checks = spec["review"].get("checks")
    required = {"video_visual", "video_audio", "cover_visual", "platform_crop", "user_acceptance"}
    if not isinstance(checks, list) or len(checks) != len(required):
        raise ValueError("质量记录须分别覆盖视频视觉、听审、封面、平台裁切、用户反馈")
    layers = set()
    for check in checks:
        layer = check.get("layer")
        if layer not in required or layer in layers or check.get("status") not in {"observed", "issue", "unobserved"}:
            raise ValueError("质量记录层级重复或状态无效")
        layers.add(layer)
        text(check.get("scope"), "质量观察范围"); text(check.get("method"), "质量观察方法")
        if check["status"] != "unobserved":
            text(check.get("evidence"), "质量观察证据")
            if require_image_bindings and layer in {"cover_visual", "platform_crop"}:
                images = check.get("images")
                if (not isinstance(images, list) or len(images) != len(spec['covers'])
                        or any(not isinstance(x, dict) or type(x.get('index')) is not int for x in images)
                        or {x['index'] for x in images} != set(range(len(spec['covers'])))):
                    raise ValueError("封面观察缺少两张具体图片绑定")
                for item in images:
                    if item.get('sha256') != spec['covers'][item['index']]['sha256']:
                        raise ValueError("封面观察图片绑定已过期")
                    text(item.get('observation'), '逐图文字边缘、构图或裁切观察')
    pending = sorted(c["layer"] for c in checks if c["status"] == "unobserved")
    issues = sorted(c["layer"] for c in checks if c["status"] == "issue")
    return {"status": "candidate", "pending": pending, "issues": issues,
            "model_verification": "reported" if model_exposed else "not_exposed",
            "verified_here": "record_structure_and_artifact_binding_only"}


def plan(studio, spec_path):
    spec = studio.load(spec_path)
    version, binding = source(studio, spec["source"]["project"], spec["source"]["version"])
    if spec["source"] != binding:
        raise ValueError("制作来源或哈希已变化，重新核对同版内容")
    if spec["platform"] != "douyin":
        raise ValueError("本阶段仅实现抖音离线包装")
    studio.identifier(spec["account_alias"])
    if not re.fullmatch(r"p[0-9]{4,}", spec["revision"]):
        raise ValueError("包装版本须为 p0001 等确切标识")
    titles = spec["titles"]
    if not isinstance(titles, list) or len(titles) != 3:
        raise ValueError("需三个有不同角度的标题候选")
    for title in titles:
        text(title["text"], "标题"); text(title["reason"], "标题依据")
    if type(spec["selected_title"]) is not int or spec["selected_title"] not in range(3):
        raise ValueError("selected_title 须为 0、1、2")
    text(spec["description"], "公开正文")
    tags = spec["tags"]
    if (not isinstance(tags, list) or not tags or len(set(tags)) != len(tags)
            or not all(isinstance(tag, str) and tag.strip() and not re.search(r"[#\s]", tag) for tag in tags)):
        raise ValueError("标签需为不含 #、空白的独立主题词且不重复")
    covers = spec["covers"]
    if not isinstance(covers, list) or len(covers) != 2:
        raise ValueError("需两个封面候选")
    cover_files = []
    for cover in covers:
        file = (spec_path.resolve().parent / cover["file"]).resolve(strict=True)
        if studio.digest(file) != cover["sha256"]:
            raise ValueError("封面哈希已变化")
        png_size(file); text(cover["angle"], "封面角度")
        cover_files.append(file)
    if type(spec["selected_cover"]) is not int or spec["selected_cover"] not in range(2):
        raise ValueError("selected_cover 须为 0 或 1")
    review = spec["review"]
    if review["video_sha256"] != binding["video_sha256"]:
        raise ValueError("内容审查与视频不符")
    text(review["content_observation"], "真实内容观察")
    if not isinstance(review["limitations"], list) or not all(isinstance(x, str) for x in review["limitations"]):
        raise ValueError("需记录审查限制")
    text(spec["rules"]["source"], "规则来源")
    text(spec["rules"]["checked_at"], "规则核查时间")
    text(spec["experiment"]["hypothesis"], "包装假设")
    text(spec["experiment"]["variable"], "本次观察变量")
    duration = studio.load(version / "receipt.json").get("media", {}).get("format", {}).get("duration")
    content_strategy.publication(studio, spec, spec_path, float(duration) if duration else None)
    packaging_quality(spec)
    from video_review import require as require_review
    require_review(studio, version)
    target = version.parents[1] / "publications" / version.name / spec["platform"] / spec["revision"]
    return spec, version, cover_files, target


def preview(manifest):
    e = lambda value: escape(str(value), quote=True)
    final = manifest["final"]
    covers = "".join(f'<figure><img src="{e(c["file"])}" alt="封面{n+1}"><figcaption>{e(c["angle"])}</figcaption></figure>' for n, c in enumerate(manifest["covers"]))
    candidates = "".join(f'<li><b>{e(t["text"])}</b><p>{e(t["reason"])}</p></li>' for t in manifest["titles"])
    limits = "".join(f"<li>{e(x)}</li>" for x in manifest["review"]["limitations"])
    media = manifest.get("media", {})
    video_style = (f"aspect-ratio:{int(media['width'])}/{int(media['height'])};" if media.get("width") and media.get("height") else "max-height:60vh;")
    editorial = ""
    quality = manifest.get("quality", {"status": "legacy_unassessed"})
    quality_note = f'<section><h2>质量待验 · 候选包</h2><p>{e(quality)}</p><small>结构校验不代表审美、人审或流量效果通过；reported 仅表示来源记录有模型名，不是程序认证。not_exposed 表示工具未暴露底层模型。</small></section>'
    if manifest.get("content_strategy"):
        a, t = manifest["content_strategy"]["account"], manifest["content_strategy"]["topic"]
        proofs = "".join(f'<li>{e(p["at_seconds"])} 秒：{e(p["observation"])}</li>' for p in manifest["editorial"]["fulfillment"])
        tags = "".join(f'<li>#{e(b["tag"])} · {e(b["role"])}：{e(b["basis"])}</li>' for b in manifest["editorial"]["tag_basis"])
        evidence = "".join(f'<li>{e(x["kind"])}：{e(x["observation"])}<br><small>依据：{e(x["source"])}；限制：{e(x["limitation"])}</small></li>' for x in a["evidence"] + t["evidence"])
        editorial = f'<section><h2>这条内容为谁而做</h2><p>{e(a["audience"]["who"])} · {e(a["audience"]["situation"])}</p><p>观众的问题：{e(t["audience_question"])}</p><p>看完得到：{e(t["payoff"])}</p><details><summary>查看选题依据、片内兑现与标签选择</summary><h3>片内兑现</h3><ul>{proofs}</ul><h3>标签用途（相关性候选，热度未验证）</h3><ul>{tags}</ul><h3>依据与限制</h3><ul>{evidence}</ul></details></section>'
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' file:; media-src 'self' file:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>{e(final['title'])} · 发布预览</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f4f4ef;color:#20251e;font:16px/1.65 system-ui,sans-serif}}main{{max-width:1120px;margin:auto;padding:32px 24px}}h1{{font-size:30px;line-height:1.35}}h2{{font-size:22px}}.status{{color:#53622d;font-weight:700}}.hero{{display:grid;grid-template-columns:1.25fr 1fr;gap:28px}}video{{width:100%;background:#080c0e;border-radius:12px}}section{{background:white;padding:24px;margin:20px 0;border-radius:16px}}.tags{{color:#4d6823}}.covers{{display:flex;gap:24px;flex-wrap:wrap}}figure{{margin:0;max-width:260px}}img{{width:100%;display:block;border-radius:10px}}figcaption,small{{color:#596151}}.crop-grid{{display:flex;gap:20px;flex-wrap:wrap}}.crop img{{width:150px;height:200px;object-fit:cover}}.crop.square img{{height:150px}}.crop.wide img{{height:84px}}p{{white-space:pre-wrap}}a{{color:#36530e}}li{{margin:12px 0}}@media(max-width:750px){{.hero{{display:block}}main{{padding:16px}}h1{{font-size:24px}}}}
</style><main><div class="status">离线发布预览 · 抖音 · 未发布</div><h1>{e(final['title'])}</h1>
<div class="hero"><div><video controls playsinline preload="metadata" style="{video_style}object-fit:contain" poster="{e(final['cover'])}" src="video.mp4"></video><small>原视频保留原画幅，可全屏查看；本页不会上传素材。</small></div><section style="margin:0"><b>最终发布文案</b><p>{e(final['description'])}</p><p class="tags">{' '.join('#'+e(t) for t in final['tags'])}</p><small>账号：未接入（{e(manifest['account_alias'])}）<br>公开范围、发布时间：待实际发布时设置</small><p><a href="copy.md">查看候选与最终文案</a> · <a href="video.mp4" download>视频</a> · <a href="{e(final['cover'])}" download>选定封面</a></p></section></div>
<section><h2>两种封面</h2><div class="covers">{covers}</div><p>选定：封面 {manifest['selected_cover']+1}。竖封面单独排版，未裁剪或拉伸原视频。</p><h2>选定封面的裁切检查</h2><small>以下为中心裁切模拟，非平台真实页面或已验证的安全区。</small><div class="crop-grid"><figure class="crop"><img src="{e(final['cover'])}"><figcaption>3:4 中心裁切</figcaption></figure><figure class="crop square"><img src="{e(final['cover'])}"><figcaption>1:1 中心裁切</figcaption></figure><figure class="crop wide"><img src="{e(final['cover'])}"><figcaption>16:9 中心裁切</figcaption></figure></div></section>
{quality_note}{editorial}<section><h2>标题选择</h2><ol>{candidates}</ol><p>本次假设：{e(manifest['experiment']['hypothesis'])}</p><p>主要变量：{e(manifest['experiment']['variable'])}。实际效果待发布数据验证。</p></section>
<section><h2>内容核对与待验</h2><p>{e(manifest['review']['content_observation'])}</p><ul>{limits}</ul><small>规则依据：{e(manifest['rules']['source'])}；记录时间：{e(manifest['rules']['checked_at'])}。平台当前字段限制、裁切与账号权限尚未接入验证。</small></section></main></html>'''


def build(studio, spec_path):
    spec, version, covers, target = plan(studio, spec_path)
    if target.exists() or target.with_suffix(".zip").exists():
        raise ValueError("包装修订已存在，请使用新修订号，不覆盖旧包")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".publish-", dir=target.parent) as temporary:
        stage = Path(temporary) / target.name
        stage.mkdir()
        shutil.copyfile(version / "video.mp4", stage / "video.mp4")
        packed_covers = []
        for n, file in enumerate(covers):
            name = f"cover-{'ab'[n]}.png"
            shutil.copyfile(file, stage / name)
            packed_covers.append({"file": name, "sha256": studio.digest(stage / name),
                                  "size": png_size(stage / name), "angle": spec["covers"][n]["angle"],
                                  "promise_id": spec["covers"][n]["promise_id"],
                                  "generation": spec["covers"][n]["generation"]})
        subtitle = version / "subtitles.srt"
        if subtitle.is_file() and subtitle.stat().st_size:
            shutil.copyfile(subtitle, stage / "subtitles.srt")
        manifest = {key: spec[key] for key in ("source", "platform", "account_alias", "revision", "titles", "selected_title", "selected_cover", "review", "rules", "experiment")}
        duration = studio.load(version / "receipt.json").get("media", {}).get("format", {}).get("duration")
        manifest.update(schema=4, status="offline_ready", published=False, covers=packed_covers,
                        cover_research=spec["cover_research"], quality=packaging_quality(spec),
                        content_strategy=content_strategy.publication(studio, spec, spec_path, float(duration) if duration else None),
                        editorial=spec["editorial"],
                        final={"title": spec["titles"][spec["selected_title"]]["text"],
                               "description": spec["description"], "tags": spec["tags"],
                               "cover": packed_covers[spec["selected_cover"]]["file"]})
        from video_review import require as require_review
        manifest["video_review"] = require_review(studio, version)
        stream = next((s for s in studio.load(version / "receipt.json").get("media", {}).get("streams", [])
                       if s.get("codec_type") == "video"), {})
        manifest["media"] = {key: stream.get(key) for key in ("width", "height")}
        manifest["media"]["duration_seconds"] = float(duration) if duration else None
        studio.save(stage / "manifest.json", manifest)
        final = manifest["final"]
        copy = f"# 最终发布文案\n\n{final['title']}\n\n{final['description']}\n\n" + " ".join("#"+tag for tag in final["tags"])
        copy += "\n\n## 标题候选\n\n" + "\n\n".join(f"{i+1}. {t['text']}\n\n   {t['reason']}" for i,t in enumerate(spec["titles"]))
        copy += "\n\n离线候选包，质量待验，尚未发布；内部审查不属于公开正文。\n"
        (stage / "copy.md").write_text(copy, encoding="utf-8")
        (stage / "preview.html").write_text(preview(manifest), encoding="utf-8")
        studio.save(stage / "receipt.json", {"schema": 1, "status": "offline_ready", "published": False,
                    "channel": None, "platform_content_id": None, "platform_url": None,
                    "files": {p.name: studio.digest(p) for p in sorted(stage.iterdir())}})
        verify(studio, stage)
        archive = Path(temporary) / "package.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for file in sorted(stage.iterdir()):
                bundle.write(file, arcname=f"{target.name}/{file.name}")
        # Revalidate original before committing a publication, without touching current.
        if plan(studio, spec_path)[0] != spec:
            raise ValueError("构建期间包装输入发生变化，请使用核对后的输入重试")
        stage.rename(target)
        archive.rename(target.with_suffix(".zip"))
    return {"path": str(target), "archive": str(target.with_suffix('.zip')),
            "status": "offline_ready", "quality": manifest["quality"], "published": False, "source": spec["source"]}


def verify(studio, path):
    manifest, receipt = studio.load(path / "manifest.json"), studio.load(path / "receipt.json")
    if manifest["platform"] != "douyin" or not re.fullmatch(r"p[0-9]{4,}", manifest["revision"]):
        raise ValueError("发布包平台或修订号无效")
    studio.identifier(manifest["account_alias"])
    if (len(manifest["covers"]) != 2 or type(manifest["selected_cover"]) is not int
            or manifest["selected_cover"] not in range(2) or len(manifest["titles"]) != 3
            or type(manifest["selected_title"]) is not int or manifest["selected_title"] not in range(3)):
        raise ValueError("发布包候选或选中序号无效")
    _, binding = source(studio, manifest["source"]["project"], manifest["source"]["version"])
    if manifest["source"] != binding:
        raise ValueError("原制作版本或回执与发布包不符")
    if receipt["status"] != "offline_ready" or receipt["published"] is not False or manifest["published"] is not False:
        raise ValueError("离线包不能冒充已发布")
    required = {"video.mp4", "cover-a.png", "cover-b.png", "copy.md", "preview.html", "manifest.json"}
    if not required <= receipt["files"].keys():
        raise ValueError("发布包缺少核心文件")
    for name, checksum in receipt["files"].items():
        if Path(name).name != name or name in {".", ".."} or studio.digest(path / name) != checksum:
            raise ValueError(f"发布包文件哈希不符：{name}")
    if studio.digest(path / "video.mp4") != binding["video_sha256"]:
        raise ValueError("包内视频与制作版本不符")
    for cover in manifest["covers"]:
        if receipt["files"].get(cover["file"]) != cover["sha256"]:
            raise ValueError("封面与回执不符")
    selected = manifest["covers"][manifest["selected_cover"]]["file"]
    if manifest["final"]["cover"] != selected:
        raise ValueError("选定封面不一致")
    if manifest["final"]["title"] != manifest["titles"][manifest["selected_title"]]["text"]:
        raise ValueError("选定标题不一致")
    if manifest.get("schema") not in (1, 2, 3, 4):
        raise ValueError("未知发布包 schema")
    if manifest["schema"] in (2, 3, 4):
        content_strategy.validate_publication(manifest["content_strategy"], manifest,
                                              manifest.get("media", {}).get("duration_seconds"))
    quality = {"status": "legacy_unassessed"}
    if manifest["schema"] in (3, 4):
        quality = packaging_quality(manifest, require_image_bindings=manifest['schema'] >= 4)
        if manifest.get("quality") != quality:
            raise ValueError("质量摘要与实际记录不符")
    from video_review import status as review_status
    version, _ = source(studio, binding["project"], binding["version"])
    current_review = review_status(studio, version)
    blocked = current_review.get('status') != 'reviewed' or bool(quality.get('issues'))
    pending = manifest['schema'] < 4 or bool(quality.get('pending'))
    return {"status": "offline_ready", "published": False, "files_verified": len(receipt["files"]),
            "video_quality_now": current_review,
            "delivery_eligible": not blocked and not pending,
            "delivery_status": 'blocked' if blocked else 'pending' if pending else 'recorded_checks_passed',
            "quality": quality, "source": binding, "manifest_sha256": studio.digest(path / "manifest.json")}
