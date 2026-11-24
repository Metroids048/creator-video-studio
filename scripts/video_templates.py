"""Local style registry and paper/ink compiler; uses the existing code route."""
import hashlib
from datetime import date
import json
import math
from pathlib import Path
import re
import tempfile
import os


ROOT = Path(__file__).resolve().parents[1]

# Explicit instruction clauses only. Keep clauses on either side of punctuation
# or a positive contrast; do not strip bare 不, 不仅, or lyric dialogue in quotes.
NEGATIVE_DIRECTIVE = r"(?:不需要|不采用|不选择|不使用|不做|不用|不要|无需|避免|排除|禁止|别用|别做)"
NEGATIVE_CLAUSE = re.compile(
    NEGATIVE_DIRECTIVE +
    r"(?:(?!(?:而是|改为|改用|但是|但要|但用|但做|而用|而做))[^，,。；;！？!?\n])*"
)


def routing_text(value):
    """Mask bounded negative directives for features, preserving raw input hashes.

    This is not general semantic understanding. Quote spans are left untouched so
    a negative line in lyrics/dialogue cannot silently hide required performance.
    """
    parts = re.split(r'(“[^”]*”|「[^」]*」|"[^"\n]*")', value)
    constraints = []
    for index in range(0, len(parts), 2):
        constraints.extend(match.group() for match in NEGATIVE_CLAUSE.finditer(parts[index]))
        parts[index] = NEGATIVE_CLAUSE.sub(" ", parts[index])
    return "".join(parts), constraints


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def catalog(root=ROOT):
    return read(root / "templates/catalog.json")["templates"]


def active_catalog(root=ROOT):
    return [item for item in catalog(root) if item.get("curation", {}).get("status") != "archived"]


def qualification(market, method, files_present):
    """One current reading for CLI, matcher and gallery; history stays history."""
    gaps = []
    if not files_present:
        gaps.append('可运行工程文件')
    if not market['qualified']:
        gaps.append('近期市场依据')
    if not method['qualified']:
        gaps.append('同版换稿与完整审阅')
    return {'tier': 'adaptation_recorded' if files_present and method['qualified'] else
                    'engineering_candidate' if files_present else 'reference_only',
            'engine_files_present': files_present, 'market_qualified': market['qualified'],
            'adaptation_recorded': method['qualified'], 'production_eligible': not gaps,
            'gaps': gaps, 'content_quality_guaranteed': False}


def inventory(root=ROOT):
    registered = catalog(root)
    items = active_catalog(root)
    config = read(root / "templates/routing.json")
    qualifications = {}
    for item in items:
        market = benchmark_status(item["id"], root, config)
        qualifications[item["id"]] = {"market": market,
            "production_evidence": production_evidence(item, market, root, config)}
        q = qualifications[item['id']]
        q['qualification'] = qualification(market, q['production_evidence'],
                                            all((root / item[key]).exists() for key in ('entry', 'starter')))
    return {"production_qualified_count": sum(q['qualification']['production_eligible']
                                             for q in qualifications.values()),
        "market_qualified_count": sum(q["market"]["qualified"] for q in qualifications.values()),
        "style_count": len(items), "registered_count": len(registered),
        "archived": [{"id": item["id"], **item["curation"]} for item in registered
                     if item.get("curation", {}).get("status") == "archived"], "templates": [
        {**item, **qualifications[item["id"]], "files_present": all((root / item[key]).exists() for key in ("entry", "starter")),
         "sample_present": all((root / item["sample"][key]).is_file() for key in ("path", "poster"))
         if item.get("sample") else False}
        for item in items], "excluded": read(root / "templates/catalog.json")["excluded"],
        "supporting_collections": read(root / "templates/catalog.json").get("supporting_collections", []),
        "quality_guaranteed": False, "render_started": False}


def research_references(request, root=ROOT):
    """Return source-linked recipes without promoting them to production entries."""
    path = root / "templates/formats.json"
    if not path.is_file():
        return []
    request, _ = routing_text(request)
    results = []
    active = {item["id"] for item in active_catalog(root)}
    for item in read(path)["formats"]:
        hits = [tag for tag in item["tags"] if tag.casefold() in request.casefold()]
        source_urls = list(item.get("user_reference_urls", []))
        if isinstance(item.get("source"), str):
            source_urls.append(item["source"])
        matched_urls = [url for url in source_urls if url.casefold() in request.casefold()]
        explicit = bool(matched_urls) or any(name.casefold() in request.casefold()
                                              for name in (item["id"], item["name"]))
        if hits or explicit:
            historical = item.get("compatible_production_templates", [])
            compatible = [name for name in historical if name in active]
            implementation = item["implementation"]
            if historical and not compatible:
                implementation = "历史适配工程已归档，当前无生产适配。原记录：" + implementation
            results.append({"id": item["id"], "name": item["name"], "category": item["category"],
                            "matched": hits, "score": len(hits) + 20 * explicit,
                            "entry": item["entry"], "source": item["source"], "market": item["market"],
                            "matched_reference_urls": matched_urls,
                            "implementation": implementation, "research_only": True,
                            "method_sources": item.get("method_sources", []),
                            "method_source_index": item.get("method_source_index"),
                            "compatible_production_templates": compatible,
                            "archived_production_templates": [name for name in item.get("compatible_production_templates", []) if name not in active],
                            "production_template": False})
    return sorted(results, key=lambda item: (-item["score"], item["id"]))[:5]


def match(request, format="16:9", root=ROOT, script="", purpose="production"):
    if not request.strip():
        raise ValueError("先提供赛道、受众、内容承诺和表达方向")
    if purpose not in {"production", "engineering_validation"}:
        raise ValueError("未知模板选择用途")
    config = read(root / "templates/routing.json")
    positive_request, request_constraints = routing_text(request)
    positive_script, script_constraints = routing_text(script)
    # Exact registered style/cue exclusions only; do not infer broader semantics.
    excluded_targets = [(clause, re.sub(r"(?:风格|模板|效果|视频)$", "",
                         re.sub("^" + NEGATIVE_DIRECTIVE, "", clause).strip()).casefold())
                        for clause in request_constraints + script_constraints]
    text = positive_request + "\n" + positive_script
    results, rejected = [], []
    references = research_references(request, root)
    strongest = [r for r in references if r["score"] == references[0]["score"]] if references else []
    compatible = {name for r in strongest for name in r["compatible_production_templates"]}
    for item in catalog(root):
        profile = config["profiles"].get(item["id"], {})
        hits = [tag for tag in item["tags"] if tag.casefold() in text.casefold()]
        explicit = [name for name in (item["id"], item["name"], item.get("style", ""))
                    if name and name.casefold() in positive_request.casefold()]
        tracks = [cue for cue in profile.get("track_cues", []) if cue.casefold() in text.casefold()]
        grammar = [cue for cue in profile.get("grammar_cues", []) if cue.casefold() in text.casefold()]
        score = len(hits) + 2 * len(tracks) + 3 * len(grammar) + 100 * bool(explicit)
        if score >= 3 or explicit or (hits and item.get("curation", {}).get("status") == "archived"):
            if item.get("curation", {}).get("status") == "archived":
                rejected.append({"id": item["id"], "reason": "同质或质量不足，已归档退出新片推荐",
                                 "replacement": item["curation"].get("replacement"),
                                 "replacement_is_compatibility_claim": False})
                continue
            aliases = {name.casefold() for name in
                       [item["id"], item["name"], item.get("style", ""), *item["tags"],
                        *profile.get("track_cues", [])] if name}
            exclusions = [clause for clause, target in excluded_targets if target in aliases]
            if exclusions:
                rejected.append({"id": item["id"], "reason": "用户明确排除该风格或形式", "evidence": exclusions})
                continue
            if format not in item["formats"]:
                rejected.append({"id": item["id"], "reason": "画幅未适配", "formats": item["formats"]})
                continue
            if references and not explicit and item["id"] not in compatible:
                rejected.append({"id": item["id"], "reason": "已命中具体参考形式，但此底座未验证可承载其核心画面语法",
                                 "evidence": [r["id"] for r in strongest]})
                continue
            unsupported = [hint for hint in item.get("unsupported_hints", []) + profile.get("exclude", []) if hint in text]
            if unsupported:
                rejected.append({"id": item["id"], "reason": "内容超出物件模板的表演范围", "evidence": unsupported})
                continue
            # Grammar alone (e.g. "最后完成") must not turn an unrelated topic into a fit.
            if not (hits or tracks or explicit):
                continue
            market = benchmark_status(item["id"], root, config)
            production = production_evidence(item, market, root, config)
            results.append({"id": item["id"], "name": item["name"], "matched": hits,
                            "explicit": explicit, "score": score,
                            "track_evidence": tracks, "grammar_evidence": grammar,
                            "content_analysis": profile, "market": market,
                            "production_evidence": production,
                            "qualification": qualification(market, production,
                                all((root / item[key]).exists() for key in ('entry', 'starter'))),
                            "readiness": item["readiness"], "limits": item["limits"],
                            "validation": item["validation"], "fit": item["fit"],
                            "curation": item.get("curation"),
                            "sample": item.get("sample"), "adaptation": item.get("adaptation"),
                            "entry": item["entry"], "input_contract": item["input_contract"],
                            "preview": "templates/gallery/index.html#" + item["id"]})
    results.sort(key=lambda item: (-item["score"], item["id"]))
    qualified = [item for item in results if item['qualification']['production_eligible']]
    candidates = qualified if purpose == "production" else results
    return {"candidates": candidates[:3], "engineering_candidates": results[:3],
            "purpose": purpose, "format": format, "auto_selected": False,
            "semantic_fit_verified": False,
            "required_next": "先核具体参考与对标基准，已有基准复用；在固定形式内将新稿逐事件绑定原工程，获准后验证换稿效果",
            "rejected": rejected,
            "research_references": references,
            "negative_constraints": {"topic": request_constraints, "script": script_constraints},
            "method": config["method"], "script_sha256": text_sha(script),
            "next": "compare_fit_and_select" if candidates else "benchmark_gap" if results else "no_compatible_template",
            "render_started": False}


def text_sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def benchmark_status(template_id, root=ROOT, config=None):
    config = config or read(root / "templates/routing.json")
    valid, rejected, seen = [], [], set()
    today = date.today()
    years = config.get("benchmark_policy", {}).get("max_age_years", 3)
    try:
        cutoff = today.replace(year=today.year - years)
    except ValueError:  # Leap day is the only missing date in an earlier year.
        cutoff = today.replace(year=today.year - years, day=28)
    for source in config["benchmarks"].get(template_id, []):
        evidence = root / source.get("evidence", "")
        issues = []
        if not (source.get("likes", 0) >= config["threshold_likes"]
                and source.get("source_role") == "original" and source.get("mechanism_reviewed")
                and source.get("full_observation") and source.get("url") not in seen
                and source.get("url") and evidence.is_file()
                and source.get("evidence_sha256") == sha(evidence)):
            issues.append("原帖指标、观察资格、唯一性或证据哈希不成立")
        else:
            try:
                rows = read(evidence).get("sources", [])
                original = next(row for row in rows if row.get("url") == source["url"])
                if any(original.get(key) != source.get(key) for key in
                       ('likes', 'source_role', 'mechanism_reviewed', 'full_observation')):
                    raise ValueError('原帖指标或观察结论与源记录矛盾')
                if (original.get('observer_kind') != 'human'
                        or original.get('observation_method') != 'human_normal_speed'
                        or original.get('limitations') != []):
                    raise ValueError('缺完整观察回执；尚无已验证 AI 连续声画感知适配器')
                published = original.get("published")
                if source.get("published", published) != published:
                    raise ValueError("发布日期与原证据不一致")
                day = date.fromisoformat(published)
                if not cutoff <= day <= today:
                    raise ValueError("原帖不在近三年范围内或日期在未来")
            except (OSError, ValueError, TypeError, StopIteration, AttributeError) as error:
                issues.append('原帖依据无效：' + str(error))
        if not issues:
            valid.append(source)
            seen.add(source["url"])
        else:
            rejected.append({"url": source.get("url"), "reasons": issues})
    return {"qualified": len(valid) >= 2, "confirmed_count": len(valid), "required_count": 2,
            "threshold_likes": config["threshold_likes"], "sources": valid,
            "rejected_sources": rejected, "publication_cutoff": cutoff.isoformat(),
            "as_of": today.isoformat(),
            "gap": max(0, 2 - len(valid)), "retention_verified": False}


def check_component(component, root, starter, version):
    from stage_handoff import fingerprint
    source = (root / component['source']).resolve(strict=True)
    consumer = (root / component['consumer']).resolve(strict=True)
    if (not source.is_relative_to(starter.resolve()) or not consumer.is_relative_to(version.resolve())
            or sha(source) != component.get('source_sha256') or sha(consumer) != component.get('consumer_sha256')):
        raise ValueError('来源或改编组件已变化；分别绑定源与改编哈希')
    if not isinstance(component.get('changes'), str) or not component['changes'].strip():
        raise ValueError('缺改编差异；原样复用也须明确记录')
    brief = read(version / 'brief.json')
    shot = next((s for s in brief['shots'] if s['id'] == component.get('shot')), None)
    if shot is None or component.get('input') not in [shot.get('sceneAsset'), *shot.get('sceneAssets', [])]:
        raise ValueError('复制组件没有进入对应镜头输入')
    native = version / 'shots' / shot['id'] / 'film'
    receipt = read(native.parent / 'scene-source.json').get('consumption')
    if not receipt or not consumer.is_relative_to(native.resolve()):
        raise ValueError('缺真实原生准备入口的消费回执')
    inputs = {i['id']: i['sha256'] for i in brief['inputs']}
    if (receipt['inputs'].get(component['input']) != inputs[component['input']]
            or receipt['files'].get(consumer.relative_to(native.resolve()).as_posix()) != sha(consumer)):
        raise ValueError('原生消费回执与组件不一致')
    units = {u['id']: fingerprint(u) for u in brief.get('content_adaptation', {}).get('units', [])
             if u['shot'] == shot['id']}
    ids = component.get('events')
    if not ids or any(e not in units or receipt['events'].get(e) != units[e] for e in ids):
        raise ValueError('组件未绑定同版实际事件，不能用外壳证明表演复用')


def production_evidence(item, market, root=ROOT, config=None):
    """Bind a reused engineering method to an actual reviewed sample, not likes.

    This checks recorded provenance, not whether an observation is truthful or funny.
    No historical sample is silently granted a new proof.
    """
    config = config or read(root / "templates/routing.json")
    ref = config.get("method_proofs", {}).get(item["id"])
    try:
        if not ref:
            raise ValueError("缺实际工程复用与同版完整视听的方法证据；仅为工程储备")
        proof_path = (root / ref["file"]).resolve(strict=True)
        if not proof_path.is_relative_to(root.resolve()) or sha(proof_path) != ref["sha256"]:
            raise ValueError("方法证据越界或已变化")
        proof = read(proof_path)
        if (proof.get("template_id"), proof.get("template_version")) != (item["id"], item["version"]):
            raise ValueError("方法证据绑定其他工程")
        urls = {s["url"] for s in market["sources"]}
        if len(urls) < 2 or not urls.issubset(set(proof.get("reference_urls", []))):
            raise ValueError("方法未绑定本分支的近期原片")
        sample = item["sample"]
        version = root / "works" / sample["work"] / "versions" / sample["version"]
        if proof.get("video_sha256") != sha(version / "video.mp4"):
            raise ValueError("方法样片已变化")
        reused = proof.get("reused_components", [])
        if not reused or not proof.get("reuse_observation"):
            raise ValueError("缺实际角色/表演/镜头复用观察及源到消费文件绑定")
        for component in reused:
            check_component(component, root, root / item['starter'], version)
        import studio
        import video_review
        report = video_review.status(studio, version)
        if report["status"] != "reviewed" or sha(Path(report["record"])) != proof.get("review_sha256"):
            raise ValueError("方法样片缺当前同版完整审阅，或已被否决")
        return {"qualified": True, "proof_sha256": ref["sha256"],
                "verified": "bound_files_and_recorded_observations_only", "quality_guaranteed": False}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        return {"qualified": False, "reason": str(error), "quality_guaranteed": False}


def selection_receipt(topic, script, format, selected, purpose="production", root=ROOT):
    if not isinstance(script, str) or not script.strip():
        raise ValueError("路由需完整文案，不能只冻结主题")
    result = match(topic, format, root, script, purpose)
    candidate = next((c for c in result["engineering_candidates"] if c["id"] == selected), None)
    if candidate is None:
        raise ValueError("路由所选模板与本次全文/形式/画幅不适配")
    if purpose == "production" and not candidate["market"]["qualified"]:
        raise ValueError("路由所选模板仍缺双对标，不具备高流量生产资格；授权试验须明确 engineering_validation")
    if purpose == "production" and not candidate["production_evidence"]["qualified"]:
        raise ValueError(candidate["production_evidence"]["reason"])
    item = next(t for t in catalog(root) if t["id"] == selected)
    return {"schema": 1, "topic_sha256": text_sha(topic), "script_sha256": text_sha(script),
            "routing_sha256": sha(root / "templates/routing.json"),
            "catalog_sha256": sha(root / "templates/catalog.json"),
            "formats_sha256": sha(root / "templates/formats.json"),
            "template_id": selected, "template_version": item["version"], "format": format,
            "purpose": purpose, "track_evidence": candidate["track_evidence"],
            "grammar_evidence": candidate["grammar_evidence"], "market": candidate["market"],
            "production_evidence": candidate["production_evidence"],
            "quality_guaranteed": False}


def validate_selection(receipt, topic, script, format, selected, root=ROOT):
    if not isinstance(receipt, dict):
        raise ValueError("新建作品缺全文路由回执；请从 templates match/prepare 绑定本次主题与完整文案")
    if receipt.get("template_id") != selected:
        raise ValueError("路由模板与制作模板不一致")
    if receipt.get("topic_sha256") != text_sha(topic) or receipt.get("script_sha256") != text_sha(script):
        raise ValueError("路由输入已变化；需按本次主题与完整文案重新匹配")
    expected = selection_receipt(topic, script, format, selected, receipt.get("purpose"), root)
    if receipt != expected:
        raise ValueError("路由回执版本或证据已变化；重新匹配后再准备/制作")
    return expected


def check_binding(brief, root=ROOT, require_selection=False):
    """Structural safeguard for NEW code films, never an aesthetic score."""
    if brief.get("route", "code") != "code":
        return {"required": False, "reason": "已有素材编辑沿原生时间线，不强套视觉模板"}
    binding = brief.get("template")
    if not isinstance(binding, dict):
        raise ValueError("新建代码视频需先确定内容方向并绑定已登记风格模板；不能从空白画布直接制作")
    selected = next((item for item in catalog(root) if item["id"] == binding.get("id")), None)
    if selected is None or binding.get("version") != selected["version"]:
        raise ValueError("模板 ID 或版本未登记")
    if selected.get("curation", {}).get("status") == "archived":
        raise ValueError("模板已归档，不能用于新建作品；旧工程恢复与同版返修沿原合同")
    direction = binding.get("direction", {})
    if not isinstance(direction, dict) or not all(isinstance(direction.get(key), str) and direction[key].strip()
               for key in ("track", "audience", "promise")):
        raise ValueError("模板绑定缺赛道、受众或本片内容承诺")
    divisor = math.gcd(brief["width"], brief["height"])
    format = f'{brief["width"] // divisor}:{brief["height"] // divisor}'
    if format not in selected["formats"]:
        raise ValueError("当前模板画幅尚未适配；不能靠直接裁切宣称已支持")
    code = [s for s in brief["shots"] if s["kind"] == "code"]
    if not code or any(s.get("engine", "vibe") != selected["engine"] for s in code):
        raise ValueError("代码镜头引擎与所选风格模板不一致")
    if selected["family"] in {"lanshu", "opuscar"} and any(s.get("style") != selected["style"] for s in code):
        raise ValueError("Lanshu 镜头 style 与模板不一致")
    if any(not s.get("sceneAsset") for s in code):
        raise ValueError("模板需绑定本片场景，不能只复用渲染外壳")
    if binding.get("known_unresolved_issues"):
        raise ValueError("仍有已知未修复问题，先修复再发起新片制作")
    if require_selection or binding.get("selection"):
        validate_selection(binding.get("selection"), brief.get("request", ""), brief.get("script", ""),
                           format, selected["id"], root)
        if (brief.get("purpose") == "self-media"
                and binding["selection"]["purpose"] == "engineering_validation"
                and brief.get("production_stage") != "representative"):
            raise ValueError("工程试验只允许自媒体代表段；不得用 engineering_validation 扩成整片")
    return {"id": selected["id"], "version": selected["version"], "direction": direction,
            "check": "structure_only", "quality_guaranteed": False}


def validate_paperink(data, root=ROOT):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", data.get("id", "")):
        raise ValueError("无效作品 ID")
    if data.get("template") != "paper-ink-landscape":
        raise ValueError("此准备器仅承接 paper-ink-landscape；蓝叔沿原生 story/beats 接口")
    def number(value):
        return type(value) in (int, float) and math.isfinite(value)
    duration = data.get("duration")
    if not number(duration) or not 1 <= duration <= 120 or duration * 30 != round(duration * 30):
        raise ValueError("时长需为1–120秒且落在30fps帧边界")
    if type(data.get("seed")) is not int or not number(data.get("worldWidth")) or data["worldWidth"] < 1280:
        raise ValueError("需确定的纸纹 seed 和至少1280宽的世界")
    for field in ("terrain", "backdrop"):
        points = data.get(field, [])
        if (len(points) < 3 or any(not isinstance(p, list) or len(p) != 2
                                or not all(number(v) for v in p) for p in points)
                or any(a[0] >= b[0] for a, b in zip(points, points[1:]))
                or points[0][0] != 0 or points[-1][0] != data["worldWidth"]
                or any(not 180 <= p[1] <= 620 for p in points)):
            raise ValueError(f"{field} 需从0覆盖世界宽度，x递增，y在180–620内")
    for field, values in (("camera", ("x", "zoom")), ("traveler", ("x",))):
        keys = data.get(field, [])
        if (len(keys) < 2 or any(not isinstance(k, dict) or not all(number(k.get(v)) for v in ("t", *values)) for k in keys)
                or keys[0]["t"] != 0 or keys[-1]["t"] != duration
                or any(a["t"] >= b["t"] for a, b in zip(keys, keys[1:]))
                or any(not 0 <= k["x"] <= data["worldWidth"] for k in keys)):
            raise ValueError(f"{field} 需递增关键帧，从0覆盖到片尾")
    if any(not .85 <= k["zoom"] <= 1.3 for k in data["camera"]):
        raise ValueError("相机缩放须在0.85–1.3，保护微人物尺度")
    end = 0
    for scene in data.get("scenes", []):
        if (scene.get("start") != end or not number(scene.get("end")) or scene["end"] <= end
                or scene["end"] * 30 != round(scene["end"] * 30)
                or any(not isinstance(scene.get(k), str) or not scene[k].strip()
                       for k in ("title", "caption", "cause", "action", "result"))
                or len(scene["title"]) > 22 or len(scene["caption"]) > 45):
            raise ValueError("分镜需连续，并有短标题、字幕、原因、动作和结果；不能只换字")
        end = scene["end"]
    if end != duration:
        raise ValueError("分镜未覆盖完整时长")
    if not isinstance(data.get("labels"), list) or any(
        not isinstance(label.get("text"), str) or len(label["text"]) > 12
        or not number(label.get("x")) or not 0 <= label["x"] <= data["worldWidth"] for label in data["labels"]
    ):
        raise ValueError("地标需短文字和有效位置")
    check_binding({"route": "code", "width": 1280, "height": 720,
                   "template": {"id": data["template"], "version": "1", "direction": data.get("direction")},
                   "shots": [{"kind": "code", "engine": "vibe", "sceneAsset": "scene"}]}, root)


def prepare(source, output, root=ROOT, require_selection=False):
    """Publish a prepared directory only after all consumers accept its brief."""
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('准备目录已存在；保留父版，复用原 brief，不得重复 prepare 覆盖上游')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.prepare-', dir=output.parent) as temp:
        staged = Path(temp) / 'prepared'
        report = _prepare_bound(source, staged, root, require_selection)
        brief_path = Path(report['brief'])
        brief = read(brief_path)
        from content_adaptation import bind_prepared, inspect as inspect_adaptation
        bind_prepared(read(source), brief, Path(source).resolve().parent)
        from production_method import bind_prepared as bind_method
        bind_method(read(source), brief, staged, root)
        inputs = {item['id']: (item.get('kind'), (staged / item['path']).resolve(strict=True))
                  for item in brief['inputs']}
        if len(inputs) != len(brief['inputs']):
            raise ValueError('素材 ID 重复')
        inspect_adaptation(brief, inputs)
        brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + '\n')
        os.rename(staged, output)
    return {**report, 'brief': str(output / 'brief.json')}


def _prepare_bound(source, output, root=ROOT, require_selection=False):
    """Prepare one existing engine and bind the exact routing input to its brief."""
    data = read(source)
    existing = Path(output) / "brief.json"
    if existing.is_file() and read(existing).get("stage_handoff"):
        raise ValueError("已有阶段交接工程，直接复用 brief；局部返修不得重复 prepare 覆盖上游")
    if "stage_handoff" in data:
        ref = data["stage_handoff"]
        if not isinstance(ref, dict) or not isinstance(ref.get("task"), str):
            raise ValueError("stage_handoff 须绑定原 workflow task")
    # Carry the editorial contract across every engine preparer. Otherwise a
    # self-media request silently becomes an unbound brief at make/validate.
    strategy = data.get("content_strategy")
    if data.get("purpose") == "self-media" and not strategy:
        raise ValueError("自媒体制作需先通过 content-plan 绑定受众与选题")
    if strategy:
        from content_strategy import creative_contract
        if creative_contract(strategy)["status"] != "ready":
            raise ValueError("选题尚未就绪，不能进入制作")
    receipt = data.get("routing")
    if require_selection or receipt:
        width, height = data.get("width", 1280), data.get("height", 720)
        divisor = math.gcd(width, height)
        validate_selection(receipt, data.get("topic", ""), data.get("script", ""),
                           f"{width // divisor}:{height // divisor}", data.get("template"), root)
        selected = next((item for item in catalog(root) if item["id"] == data.get("template")), None)
        if selected and selected.get("family") == "opuscar":
            project = read(Path(source).resolve().parent / data["project"] / "project.json")
            if project.get("content_promise") != data["script"]:
                raise ValueError("可编辑工程内容与全文路由不一致；请冻结同一份完整文案")
    if (data.get("purpose") == "self-media" and isinstance(receipt, dict)
            and receipt.get("purpose") == "engineering_validation"
            and data.get("production_stage") != "representative"):
        raise ValueError("工程试验只允许自媒体代表段；不得用 engineering_validation 扩成整片")
    report = _prepare_engine(source, output, root)
    if receipt or "purpose" in data or strategy or "stage_handoff" in data:
        path = Path(report["brief"])
        brief = read(path)
        if "purpose" in data:
            brief["purpose"] = data["purpose"]
        if "production_stage" in data:
            brief["production_stage"] = data["production_stage"]
        if strategy:
            brief["content_strategy"] = strategy
        if "stage_handoff" in data:
            brief["stage_handoff"] = {"task": str((Path(source).resolve().parent / ref["task"]).resolve())}
        if receipt:
            brief.update(request=data["topic"], script=data["script"])
            brief["template"]["selection"] = receipt
            check_binding(brief, root, require_selection=True)
            report["routing"] = receipt
        path.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n")
    return report


def _prepare_engine(source, output, root=ROOT):
    data = read(source)
    selected = next((item for item in catalog(root) if item["id"] == data.get("template")), None)
    if selected and selected.get("curation", {}).get("status") == "archived":
        raise ValueError("模板已归档，不能准备新片；旧工程恢复与同版返修沿原合同")
    from event_templates import IDS, prepare as prepare_events
    if data.get("template") in IDS:
        return prepare_events(data, output, root)
    from photo_templates import IDS as PHOTO_IDS, prepare as prepare_photos
    if data.get("template") in PHOTO_IDS:
        return prepare_photos(data, output, root, Path(source).resolve().parent)
    selected = next((item for item in catalog(root) if item["id"] == data.get("template")), None)
    if selected and selected.get("family") == "opuscar":
        from opuscar_templates import prepare as prepare_opuscar
        return prepare_opuscar(data, output, root, Path(source).resolve().parent)
    validate_paperink(data, root)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("准备目录已存在；保留父版，使用新目录")
    template = root / "templates/paper-ink-landscape/v1"
    font = root / "runtime/lanshu-fonts/notoserifsc/NotoSerifSC[wght].ttf"
    license = font.parent / "OFL.txt"
    renderer = (template / "scene.js").read_text()
    # Read every dependency before creating any output.
    font_bytes, license_bytes = font.read_bytes(), license.read_bytes()
    output.mkdir(parents=True)
    (output / "story.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    (output / "scene.js").write_text("const TEMPLATE_STORY = " + json.dumps(data, ensure_ascii=False) + ";\n" + renderer)
    (output / "paperink.ttf").write_bytes(font_bytes)
    (output / "OFL.txt").write_bytes(license_bytes)
    binding = {"id": data["template"], "version": "1", "direction": data["direction"],
               "renderer_sha256": sha(template / "scene.js"), "known_unresolved_issues": []}
    scene_id = "scene-" + sha(output / "scene.js")[:16]
    story_id = "story-" + sha(output / "story.json")[:16]
    inputs = [{"id": name, "kind": kind, "path": path, "sha256": sha(output / path)} for name, kind, path in (
        (scene_id, "scene", "scene.js"), ("paperink-font", "data", "paperink.ttf"),
        ("font-license", "data", "OFL.txt"), (story_id, "data", "story.json"))]
    brief = {"id": data["id"], "route": "code", "title": data["scenes"][0]["title"], "request": data["direction"]["promise"],
             "template": binding, "width": 1280, "height": 720, "fps": 30, "audio": {"mode": "silent"},
             "inputs": inputs, "shots": [{"id": "paperink", "kind": "code", "engine": "vibe", "accent": "#9d4836",
                 "frames": round(data["duration"] * 30), "sceneAsset": scene_id, "sceneAssets": ["paperink-font", "font-license", story_id],
                 "cues": [{"start": round(s["start"] * 30), "end": round(s["end"] * 30), "text": s["caption"]} for s in data["scenes"]]}]}
    (output / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n")
    return {"brief": str(output / "brief.json"), "template": binding, "render_started": False,
            "next": "plan_then_workflow_then_authorized_make"}
