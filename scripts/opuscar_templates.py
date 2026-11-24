"""Freeze edited MIT Opuscar projects into the existing native HTML shot route.

No upstream build/setup/voice scripts run. The source archive is an ordinary
versioned input; the production renderer keeps external requests blocked.
"""
import json
from pathlib import Path
import shutil
import zipfile

from native_bundle import index, member_name


def unpack(source, target):
    with zipfile.ZipFile(source) as archive:
        files = index(archive)
        if not {"project.json", "LICENSE"} <= files.keys():
            raise ValueError("风格工程缺少 project.json 或许可证")
        for name, entry in files.items():
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as incoming, destination.open("wb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)


def validate_scene(studio, path, shot, brief, inputs):
    spec = studio.load(path)
    archive = inputs.get(spec.get("archive"))
    entry = member_name(spec.get("entry"))
    if not archive or archive[0] != "data" or spec["archive"] not in shot.get("sceneAssets", []):
        raise ValueError("风格镜头必须绑定本作品的完整 ZIP 工程")
    with zipfile.ZipFile(archive[1]) as source:
        files = index(source)
        if not {"project.json", "LICENSE", entry} <= files.keys():
            raise ValueError("风格工程入口或许可证不完整")
        project = json.loads(source.read(files["project.json"]))
        dimensions = (brief["width"], brief["height"])
        if dimensions not in {(1920, 1080), (1280, 720)}:
            # A portrait project must declare its own composed canvas. Existing
            # landscape projects cannot obtain portrait support by cropping.
            if (dimensions not in {(1080, 1920), (720, 1280)}
                    or project.get("canvas") != {"width": dimensions[0], "height": dimensions[1]}):
                raise ValueError("竖屏须提供与输出一致的原生重排画布")
        if spec.get("capture") != project.get("capture") or spec.get("capture") not in (None, "canvas"):
            raise ValueError("原生采集方式与本片工程不一致")
        if (project.get("template") != brief.get("template", {}).get("id")
                or project.get("style") != shot.get("style") or project.get("entry") != entry
                or not project.get("changed_files") or not project.get("content_promise")):
            raise ValueError("工程未绑定所选模板、本片内容与换稿文件")
        duration = project.get("duration")
        if type(duration) not in (float, int) or abs(duration * brief["fps"] - shot["frames"]) > .51:
            raise ValueError("工程时长与本片镜头不一致")
        if project.get("source_demo_unchanged") is not False:
            raise ValueError("原版演示不能作为新稿制作输入")
        from video_templates import sha
        # The archive manifest binds edited files, not merely an assertion of reuse.
        import hashlib
        for name, expected in project["changed_files"].items():
            member_name(name)
            if name not in files or hashlib.sha256(source.read(files[name])).hexdigest() != expected:
                raise ValueError("本片换稿文件与清单不一致：" + name)


def prepare(data, output, root, source_base):
    from video_templates import catalog, check_binding, sha
    selected = next((t for t in catalog(root) if t["id"] == data.get("template")), None)
    if selected is None or selected.get("family") != "opuscar":
        raise ValueError("未登记的 Opuscar 风格")
    source = (source_base / data["project"]).resolve()
    if not source.is_dir() or not (source / "project.json").is_file():
        raise ValueError("先按该模板 Skill 换稿，提供本片 project.json 与完整可编辑工程")
    project = json.loads((source / "project.json").read_text())
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("准备目录已存在；保留父版，使用新目录")
    fps = data.get("fps", 30)
    width, height = data.get("width", 1280), data.get("height", 720)
    binding = {"id": selected["id"], "version": selected["version"],
               "direction": data["direction"], "known_unresolved_issues": data.get("known_unresolved_issues", [])}
    shot = {"id": "native-style", "kind": "code", "engine": "opuscar", "style": selected["style"],
            "sceneAsset": "scene", "sceneAssets": ["source-pack"], "frames": round(project["duration"]*fps),
            "cues": []}
    brief = {"id": data["id"], "route": "code", "title": data["title"], "request": data["direction"]["promise"],
             "template": binding, "width": width, "height": height, "fps": fps,
             "audio": data.get("audio", {"mode": "silent"}), "shots": [shot]}
    check_binding(brief, root)
    audio = None
    if brief["audio"]["mode"] == "supplied":
        audio = (source_base / data["audio_file"]).resolve()
        if not audio.is_file():
            raise ValueError("同版音轨不存在")
    elif brief["audio"]["mode"] != "silent":
        raise ValueError("明确供给同版音轨，或在代表段阶段显式静音")
    # Validate file paths before creating any output; never follow source symlinks.
    paths = sorted(p for p in source.rglob("*") if p.is_file() or p.is_symlink())
    for path in paths:
        if path.is_symlink():
            raise ValueError("工程不能包含符号链接")
        member_name(path.relative_to(source).as_posix())
    output.mkdir(parents=True)
    with zipfile.ZipFile(output / "source-pack.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, path.relative_to(source).as_posix())
    spec = {"archive": "source-pack", "entry": project["entry"]}
    if project.get("capture") is not None:
        spec["capture"] = project["capture"]
    (output / "scene.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2)+"\n")
    brief["inputs"] = [{"id": name, "kind": kind, "path": file, "sha256": sha(output/file)}
                       for name, kind, file in (("scene", "scene", "scene.json"), ("source-pack", "data", "source-pack.zip"))]
    if brief["audio"]["mode"] == "supplied":
        destination = output / ("soundtrack"+audio.suffix)
        shutil.copyfile(audio, destination)
        brief["audio"] = {"mode": "supplied", "asset": "soundtrack"}
        brief["inputs"].append({"id": "soundtrack", "kind": "audio", "path": destination.name, "sha256": sha(destination)})
    (output / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2)+"\n")
    return {"brief": str(output/"brief.json"), "template": binding, "render_started": False,
            "next": "plan_then_workflow_then_authorized_make"}
