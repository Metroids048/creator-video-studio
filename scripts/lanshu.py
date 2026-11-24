#!/usr/bin/env python3
"""Compile and preview an original Lanshu kit in a studio-owned directory."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import http.server
import json
import math
import os
import shutil
import sys
import threading

sys.dont_write_bytecode = True
from studio import ROOT, BIN, ADAPTERS, ENV, load, save, run, ff, digest

SOURCE = ROOT / "sources" / "zh-explainer"
KIT = SOURCE / "vendor" / "lanshu" / "explainer"
STYLES = sorted(p.name for p in (KIT / "kits").glob("v*") if (p / "starter").is_dir())

def load_compatibility():
    # Reuse the source project's offline dependency and timing fixes only
    # after the studio entry has accepted the production mode.
    sys.path.insert(0, str(SOURCE / "tools"))
    saved_env = dict(os.environ)
    try:
        import video as compatibility
    finally:
        os.environ.clear()
        os.environ.update(saved_env)
    compatibility.BIN = str(BIN)
    source_run = getattr(compatibility, "_studio_original_run", compatibility.run)
    compatibility._studio_original_run = source_run

    def local_run(args, cwd=None, timeout=600, env=None):
        if str(args[1]).endswith("/bundle_three.mjs"):
            args = [args[0], ADAPTERS / "bundle-three.mjs", *args[2:]]
        return source_run(args, cwd=cwd, timeout=timeout, env=ENV)

    compatibility.run = local_run
    return compatibility


def story_binding(style, value):
    story = (KIT / "stories" / value).resolve()
    if not (story / "story.json").is_file():
        story = type(ROOT)(value).resolve()
    document = story / "story.json"
    if type(ROOT)(value).is_file() and type(ROOT)(value).suffix == ".json":
        document = type(ROOT)(value).resolve()
    if not document.is_file():
        raise ValueError("故事目录中缺少 story.json")
    data = load(document)
    duration = data["duration"]
    if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("故事需提供正数时长")
    if float((data.get("recap") or {}).get("end", 0)) > duration:
        raise ValueError("故事 recap 结束超过 duration，先明确镜头时长")
    if style != "all" and style not in STYLES:
        raise ValueError(f"未找到固定 Lanshu 样式：{style}")
    choices = STYLES if style == "all" else [style]
    if not choices:
        raise ValueError("未找到固定 Lanshu 样式")
    files = [KIT / "tools" / name for name in ("sync.sh", "stamp.py")]
    return {"styles": choices, "story": str(document), "story_sha256": digest(document),
            "duration_seconds": duration, "has_local_narration": (story / "audio/narration.wav").is_file(),
            "compiler": {str(file.relative_to(ROOT)): digest(file) for file in files},
            "output_contract": "landscape_style_preview", "render_started": False}


def compile_style(out, style, story, compatibility):
    target = out / style
    shutil.copytree(KIT / "kits" / style / "starter", target)
    run("bash", KIT / "tools" / "sync.sh", target, style, story)
    compiled = (target / "lib/story.js").read_bytes().split(b"\nwindow.STORY = ", 1)[-1]
    expected = (story / "story.json").read_bytes() + b";\n"
    if compiled != expected:
        raise ValueError("story.json 与实际编译载入的 story.js 不一致")
    run(sys.executable, KIT / "tools" / "stamp.py", target)
    compatibility.localize(target, style)
    data = load(story / "story.json")
    shutil.copy2(story / "story.json", target / "story.json")
    duration = data["duration"]
    ff("-f", "lavfi", "-t", duration, "-i", "anullsrc=r=48000:cl=mono", target / "assets/audio/sfx.wav")
    save(target / "studio-source.json", {"style": style, "story": story.name, "story_sha256": digest(story / "story.json"),
        "compiled_sha256": digest(target / "lib/story.js"),
        "sourceAudio": (story / "audio/narration.wav").is_file(), "effects": "silent for visual preview",
        "purpose": "kit visual preview"})
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("production",))
    parser.add_argument("--style", choices=[*STYLES, "all"], default="all")
    parser.add_argument("--story", default="kv-cache")
    parser.add_argument("--out", type=type(ROOT))
    parser.add_argument("--plan", action="store_true", help="只读绑定 story.json 与样式")
    args = parser.parse_args()
    if args.plan:
        if args.out:
            parser.error("--plan 不接受输出目录")
        try:
            print(json.dumps(story_binding(args.style, args.story), ensure_ascii=False, indent=2))
        except (OSError, KeyError, TypeError, ValueError) as error:
            parser.error(str(error))
        return
    if args.mode != "production":
        parser.error("Lanshu 预览会渲染，需要显式 --mode production")
    if args.out is None:
        parser.error("生产模式需提供 --out")
    out = args.out.resolve()
    allowed = ROOT / "works"
    if not out.is_relative_to(allowed) or out == allowed:
        parser.error("输出位置须位于本工作室 works/ 的专用目录")
    try:
        binding = story_binding(args.style, args.story)
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.error(str(error))
    story = type(ROOT)(binding["story"]).parent
    compatibility = load_compatibility()
    out.mkdir(parents=True, exist_ok=False)
    choices = binding["styles"]
    failed = {}
    def attempt(style):
        try:
            compile_style(out, style, story, compatibility)
        except Exception as error:
            return style, str(error)
        return style, None
    with ThreadPoolExecutor(max_workers=3) as executor:
        for style, error in executor.map(attempt, choices):
            if error:
                failed[style] = error
    save(out / "compile.json", {"failed": failed, "compiled": [s for s in choices if s not in failed]})
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=out)) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            run(BIN / "node", ADAPTERS / "preview-styles.mjs", out, server.server_port)
        finally:
            server.shutdown()
    results = load(out / "preview.json")
    if failed or any(item.get("errors") for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
