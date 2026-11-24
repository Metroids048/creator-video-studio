"""Freeze pinned art/Lanshu native projects into the existing code-shot flow."""
import copy
import importlib.util
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def validate_page_params(shot):
    if "pageParams" not in shot:
        return {}
    params = shot["pageParams"]
    if (shot.get("kind") != "code" or shot.get("engine") != "lanshu"
            or shot.get("style") != "v1-editorial"):
        raise ValueError("pageParams 目前仅支持 Lanshu v1-editorial 代码镜头")
    if not isinstance(params, dict) or not params.keys() <= {"captionSize", "turn", "lead", "tail"}:
        raise ValueError("pageParams 只接受 captionSize、turn、lead、tail")
    for key, value in params.items():
        try:
            finite = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            finite = False
        if (not finite
                or value < 0 or (key in {"captionSize", "turn"} and value == 0)):
            raise ValueError("pageParams 需有限数值；captionSize/turn 为正，lead/tail 非负")
    return params


def apply_page_params(html, params):
    """Edit only known native anchors; no free-form CSS or script input."""
    number = r"[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?"
    for key, value in params.items():
        if key == "captionSize":
            continue
        pattern = (rf"(\bconst TURN = ){number}(;)" if key == "turn" else
                   rf"(\bconst caps = new C\.Captions\(capsEl, S, \{{[^\n{{}}]*\b{key}:\s*){number}([, }}])")
        html, count = re.subn(pattern, lambda m: m[1] + str(value) + m[2], html)
        if count != 1:
            raise ValueError("pageParams 原生页面锚点发生变化：" + key)
    if "captionSize" in params:
        block = '<style id="studio-page-params">.kit-cap { font-size: ' + str(params["captionSize"]) + 'px; }</style>\n'
        marker = r'<style id="studio-page-params">.*?</style>\s*'
        if len(re.findall(marker, html, flags=re.S)) > 1 or html.count("</head>") != 1:
            raise ValueError("pageParams 原生页面锚点发生变化：captionSize")
        html = re.sub(marker, '', html, flags=re.S)
        html = html.replace("</head>", block + "</head>")
    return html


def install_fonts(studio, target):
    """Copy full pinned font files offline; native per-style family/weight survives."""
    catalog = studio.load(studio.ROOT / "docs/lanshu-fonts.json")
    config = studio.load(target / "fonts.json")
    records = {}
    for relative, keys in config.items():
        if relative == "extra":
            continue
        rules = []
        for key in keys:
            face = catalog["faces"][key]
            for field in ("font", "license"):
                row = face[field]
                source = studio.ROOT / row["path"]
                if studio.digest(source) != row["sha256"]:
                    raise ValueError("固定字体或许可证已变化：" + row["path"])
                name = "assets/fonts/" + source.parent.name + "-" + source.name
                destination = target / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                records[name] = row
            url = "assets/fonts/" + (studio.ROOT / face["font"]["path"]).parent.name + "-" + (studio.ROOT / face["font"]["path"]).name
            rules.append('@font-face { font-family: ' + studio.json.dumps(face["family"]) +
                         '; src: url("' + url + '"); font-weight: ' + str(face["weight"]) +
                         '; font-style: ' + face.get("style", "normal") +
                         '; font-stretch: ' + face.get("stretch", "normal") + '; font-display: block; }')
        path = target / relative
        if not path.is_file() or not re.search(r'/\* fonts:begin \*/.*?/\* fonts:end \*/', path.read_text(), re.S):
            raise ValueError("原生字体标记不存在：" + relative)
        text = re.sub(r'/\* fonts:begin \*/.*?/\* fonts:end \*/',
                      lambda _: '/* fonts:begin */\n' + '\n'.join(rules) + '\n/* fonts:end */', path.read_text(), flags=re.S)
        path.write_text(text)
    # Reuse only the source's offline three-glyph correction, never its downloader.
    spec = importlib.util.spec_from_file_location("studio_glyph_fix", studio.ROOT / "sources/zh-explainer/tools/prepare_fonts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.fix_confusing_glyphs(target)
    studio.save(target / "font-source.json", {"catalog": catalog["commit"], "files": records})


def art_aliases(path, shot, brief, inputs):
    rows = {row["id"]: row for row in brief["inputs"]}
    aliases = {rows[name]["sourcePath"]: inputs[name][1]
               for name in shot.get("sceneAssets", []) if rows[name].get("sourcePath")}
    base = rows[shot["sceneAsset"]].get("sourcePath")
    return aliases, str(type(path)(base).parent) if base else None


def art_spec(studio, path, shot, brief, inputs):
    from workflow import art_assets

    data = studio.load(path)
    aliases, source_base = art_aliases(path, shot, brief, inputs)
    lint_data = copy.deepcopy(data)
    def lint_path(value):
        if isinstance(value, str) and not value.startswith(('data:', 'http:', 'https:')):
            return str(aliases.get(str((Path(source_base or path.parent) / value).resolve()), value))
        return value
    for cue in lint_data.get('cues', []):
        if cue.get('image'):
            cue['image'] = lint_path(cue['image'])
        if isinstance(cue.get('frames'), list):
            cue['frames'] = [lint_path(value) for value in cue['frames']]
    source = studio.ROOT / "resources/huashu-art-motion/scripts/clip_lint.py"
    with tempfile.TemporaryDirectory(prefix='studio-art-lint-') as temporary:
        lint_file = Path(temporary) / 'spec.json'
        # Absolute paths preserve the native lint's existence checks even when
        # the JSON now lives in an isolated imported project.
        for cue in lint_data.get('cues', []):
            for key in ('image', 'frames'):
                if key not in cue:
                    continue
                def absolute(value):
                    return str((path.parent / value).resolve()) if isinstance(value, str) and not value.startswith(('data:', 'http:', 'https:')) else value
                cue[key] = [absolute(v) for v in cue[key]] if isinstance(cue[key], list) else absolute(cue[key])
        lint_file.write_text(studio.json.dumps(lint_data))
        result = subprocess.run(["/usr/bin/python3", "-IB", source, lint_file, "--strict"],
                                capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise ValueError("艺术片段合同未通过：" + (result.stdout or result.stderr).strip())
    dimensions = (data.get("width", 1920), data.get("height", 1080), data.get("fps", 30))
    if (dimensions != (brief["width"], brief["height"], brief["fps"])
            or abs(data["duration"] * brief["fps"] - shot["frames"]) > 0.000001):
        raise ValueError("艺术片段的画幅、帧率或时长与镜头不一致")
    if data.get("alpha"):
        raise ValueError("工作室 MP4 镜头不承接透明输出；请在原生路线单独处理")
    assets = art_assets(studio, path, aliases, source_base)
    if assets.get("error") or assets["remote_assets"]:
        raise ValueError("艺术片段素材未闭合：" + str(assets))
    return data, assets


def validate_scene(studio, path, shot, brief, inputs):
    validate_page_params(shot)
    if shot["engine"] == "opuscar":
        from opuscar_templates import validate_scene as validate_opuscar
        validate_opuscar(studio, path, shot, brief, inputs)
    elif shot["engine"] == "art":
        _, report = art_spec(studio, path, shot, brief, inputs)
        declared = {str(inputs[name][1].resolve()) for name in shot.get("sceneAssets", [])}
        if not set(report["local_files"]) <= declared:
            raise ValueError("艺术片段引用了未在 sceneAssets 声明的文件")
    else:
        from lanshu import story_binding

        # story_binding intentionally preserves the native story; no invented timeline.
        binding = story_binding(shot.get("style"), str(path))
        if (binding["story"] != str(path.resolve()) or shot.get("style") == "all"
                or (brief["width"], brief["height"]) != (1920, 1080)
                or abs(binding["duration_seconds"] * brief["fps"] - shot["frames"]) > 0.000001):
            raise ValueError("Lanshu 镜头需单一样式、1920×1080 和与 story.json 相同的时长")
        beats = shot.get("beatsAsset")
        if beats not in inputs or inputs[beats][0] != "scene" or inputs[beats][1].suffix.lower() != ".js":
            raise ValueError("Lanshu 镜头需作品自己的 beatsAsset JS，不使用 starter 演示内容")


def copy_tree(source, target):
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError("原生引擎不能包含符号链接")
        if path.is_file() and not any(p in {"__pycache__", "node_modules", ".git"} for p in path.parts):
            destination = target / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)


def prepare(studio, shot, brief, project, native, previous=None):
    scene = studio.verified_input(brief, project, shot["sceneAsset"])
    inputs = {item["id"]: (item["kind"], studio.verified_input(brief, project, item["id"]))
              for item in brief["inputs"]}
    validate_scene(studio, scene, shot, brief, inputs)
    native.mkdir(parents=True)
    engine = shot["engine"]
    assets = {}
    for name in shot.get("sceneAssets", []):
        source = inputs[name][1]
        relative = "assets/" + name + source.suffix.lower()
        (native / "assets").mkdir(exist_ok=True)
        shutil.copyfile(source, native / relative)
        assets[name] = relative
    if previous is not None:
        prior = studio.load(previous / "shot.json")
        if prior.get("engine") != engine or prior.get("style") != shot.get("style"):
            raise ValueError("画面返修不能替换父版引擎或样式")
        if not prior.get("pageParams", {}).keys() <= shot.get("pageParams", {}).keys():
            raise ValueError("pageParams 不得隐式删除父版参数；请显式保留或重设数值")
        copy_tree(previous / "engine", native / "engine")
        for name in ("ENGINE-LICENSE", "render-shot.mjs"):
            shutil.copyfile(previous / name, native / name)
    else:
        shutil.copyfile(studio.ADAPTERS / "native-html-shot.mjs", native / "render-shot.mjs")
    shutil.copyfile(scene, native / "scene.json")
    if engine == "opuscar":
        from opuscar_templates import unpack
        # Each version freezes the author's complete edited project, including fonts.
        # Revisions keep the parent's renderer; they replace only the bound source pack.
        if (native / "engine").exists():
            shutil.rmtree(native / "engine")
        unpack(inputs[studio.load(scene)["archive"]][1], native / "engine")
        shutil.copyfile(native / "engine/LICENSE", native / "ENGINE-LICENSE")
    elif engine == "art":
        source = studio.ROOT / "resources/huashu-art-motion"
        if previous is None:
            copy_tree(source / "scripts/engine", native / "engine")
            shutil.copyfile(source / "LICENSE", native / "ENGINE-LICENSE")
        spec = copy.deepcopy(studio.load(scene))
        module_spec = importlib.util.spec_from_file_location("frozen_art_paths", native / "engine/spec_assets.py")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        from workflow import localize_art
        aliases, source_base = art_aliases(scene, shot, brief, inputs)
        localize_art(module, spec, scene.parent, aliases, source_base)
        from urllib.parse import unquote

        by_source = {str(inputs[name][1].resolve()): "/" + value for name, value in assets.items()}
        def relocate(value):
            if isinstance(value, str) and value.startswith("/__file__/"):
                return by_source[unquote(value[len("/__file__/"):])]
            if isinstance(value, list):
                return [relocate(v) for v in value]
            if isinstance(value, dict):
                return {k: relocate(v) for k, v in value.items()}
            return value
        studio.save(native / "effective-spec.json", relocate(spec))
    else:
        from lanshu import KIT, load_compatibility

        target = native / "engine"
        if previous is None:
            copy_tree(KIT / "kits" / shot["style"] / "starter", target)
            copy_tree(KIT / "kits" / shot["style"], target / "lib/kit")
            shutil.rmtree(target / "lib/kit/starter")
            for name in ("core.js", "sfxlib.py"):
                shutil.copyfile(KIT / "core" / name, target / "lib" / name)
            shutil.copyfile(KIT.parent / "LICENSE", native / "ENGINE-LICENSE")
        story = studio.load(scene)
        (target / "lib/story.js").write_text("window.STORY = " + studio.json.dumps(story, ensure_ascii=False) + ";\n")
        shutil.copyfile(inputs[shot["beatsAsset"]][1], target / "beats.js")
        studio.save(native / "assets.json", assets)
        html = (target / "index.html").read_text()
        # Audio is owned by the studio sound contract, never silent placeholder WAVs.
        html = re.sub(r"<audio\b[^>]*>.*?</audio>", "", html, flags=re.S)
        def stamp(match):
            tag = match.group(0)
            return re.sub(r'data-duration="[^"]*"', f'data-duration="{story["duration"]}"', tag)
        html = re.sub(r'<[a-z][^>]*data-stamp="story"[^>]*>', stamp, html)
        html = re.sub(r'<script id="studio-assets">.*?</script>\s*', '', html, flags=re.S)
        if html.count('<script src="beats.js">') != 1:
            raise ValueError("原生 beats.js 入口发生变化，保留父版并停止")
        html = html.replace('<script src="beats.js">',
                            '<script id="studio-assets">window.STUDIO_ASSETS=' + studio.json.dumps({k:"/"+v for k,v in assets.items()}) + ';</script>\n<script src="beats.js">')
        html = apply_page_params(html, validate_page_params(shot))
        (target / "index.html").write_text(html)
        if previous is None:
            load_compatibility().localize(target, shot["style"])
            install_fonts(studio, target)
    studio.save(native / "assets.json", assets)
    studio.save(native / "shot.json", shot)
    studio.save(native.parent / "scene-source.json", {
        "engine": engine, "asset": shot["sceneAsset"], "sha256": studio.digest(native / "scene.json"),
        "files": {p.relative_to(native).as_posix(): studio.digest(p)
                  for p in sorted(native.rglob("*")) if p.is_file()},
        "audio_owner": "studio brief; native visual project has no automatic sound generation",
    })


def render(studio, shot, native, target):
    studio.run(studio.BIN / "node", native / "render-shot.mjs", native, target,
               studio.VIBE / "package.json", cwd=native)
