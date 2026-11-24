#!/usr/bin/env python3
"""Read-only checks for the pinned Nook engine and its scene interface."""
import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "resources/nook-anim/nook-anim"
PYTHON = ROOT / "runtime/nook-venv/bin/python"


def runtime_environment():
    # Source defaults are Windows font paths. Bind project-owned substitutions
    # explicitly, without changing the preserved upstream configuration.
    fonts = ROOT / "runtime/vibe/fonts"
    env = {k: os.environ[k] for k in ("HOME", "TMPDIR", "LANG") if k in os.environ}
    env.update({"NOOKANIM_FONT_UI": str(fonts / "LXGWWenKai-Medium.ttf"),
                "NOOKANIM_FONT_HAND_EN": str(fonts / "ShantellSans-VF.ttf"),
                "NOOKANIM_FONT_HAND_ZH": str(fonts / "MaShanZheng-Regular.ttf"),
                "NOOKANIM_FFMPEG": str(ROOT / ".studio/bin/ffmpeg")})
    for key, value in env.items():
        if key.startswith("NOOKANIM_") and not Path(value).is_file():
            raise ValueError("Nook 缺少项目字体或工具：" + value)
    return env


def check():
    # Only import pinned local engine code. Never import a user-supplied scene.
    command = """
import json
import hashlib
from importlib import import_module
from importlib.metadata import version
from pathlib import Path
from PIL import ImageFont
import sys
sys.path.insert(0, sys.argv[1])
modules = ('draw', 'render', 'post', 'audio', 'sketch', 'collage', 'wash', 'stick', 'mg')
for name in modules:
    import_module('nookanim.' + name)
core = import_module('nookanim.core')
if core.lerp(2, 6, 0.25) != 3:
    raise RuntimeError('Nook interpolation check failed')
packages = ('numpy', 'opencv-python-headless', 'pillow', 'scipy', 'imageio-ffmpeg')
config = import_module('nookanim.config')
fonts = {}
for key in ('FONT_UI', 'FONT_HAND_EN', 'FONT_HAND_ZH'):
    path = Path(getattr(config, key))
    ImageFont.truetype(str(path), 24)  # Load font metadata, without drawing a frame.
    fonts[key] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
print(json.dumps({'modules': modules, 'versions': {p: version(p) for p in packages},
                  'fonts': fonts, 'ffmpeg': config.ffmpeg()}))
"""
    result = subprocess.run(
        [PYTHON, "-IB", "-c", command, SOURCE / "scripts"], cwd=ROOT,
        env=runtime_environment(),
        check=True, capture_output=True, text=True, timeout=90,
    )
    report = json.loads(result.stdout)
    pins = json.loads((ROOT / "docs/nook-macos-arm64.lock.json").read_text())
    expected = {item["name"]: item["version"] for item in pins}
    if report["versions"] != expected:
        raise ValueError("Nook 本机依赖与工作室锁不一致")
    return {**report, "font_policy": "project substitutions; original Windows fonts preserved in source",
            "runtime_execution": "imports_versions_and_font_metadata_only",
            "native_production_verified": False}


def plan(path):
    path = path.resolve(strict=True)
    if path.suffix != ".py":
        raise ValueError("Nook 场景必须是 .py 文件")
    data = path.read_bytes()
    try:
        tree = ast.parse(data, filename=str(path))
    except SyntaxError as exc:
        raise ValueError(f"Nook 场景语法无效（第 {exc.lineno} 行）：{exc.msg}") from exc
    names, values = set(), {}

    def constant(node):
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, (ast.List, ast.Tuple)):
            return [constant(element) for element in node.elts]
        return ast.literal_eval(node)

    def assign(target, node):
        if isinstance(target, ast.Name):
            values.pop(target.id, None)
            try:
                values[target.id] = constant(node)
            except (ValueError, TypeError, KeyError):
                pass
        elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(node, (ast.Tuple, ast.List)):
            if len(target.elts) == len(node.elts):
                for left, right in zip(target.elts, node.elts):
                    assign(left, right)
    for item in tree.body:
        if isinstance(item, ast.Assign):
            targets = item.targets
        elif isinstance(item, ast.AnnAssign) and item.value is not None:
            targets = [item.target]
        else:
            continue
        for target in targets:
            names.update(name.id for name in ast.walk(target)
                         if isinstance(name, ast.Name) and isinstance(name.ctx, ast.Store))
            assign(target, item.value)
    required = {"W", "H", "FPS", "DUR", "SHOTS"}
    if not required <= names:
        raise ValueError(f"Nook 场景缺少顶层常量：{', '.join(sorted(required - names))}")
    render = next((node for node in tree.body if isinstance(node, ast.FunctionDef)
                   and node.name == "render"), None)
    if (not render or len(render.args.posonlyargs + render.args.args) != 1
            or render.args.kwonlyargs or render.args.vararg or render.args.kwarg):
        raise ValueError("Nook 场景须定义 render(t)")
    for name in ("W", "H", "FPS", "DUR"):
        if name in values:
            value = values[name]
            if (type(value) not in (int, float) or not math.isfinite(value) or value <= 0
                    or name in {"W", "H"} and int(value) != value):
                raise ValueError(f"Nook 参数 {name} 须为正的有限数，画幅须为整数")
    if "SHOTS" in values:
        shots = values["SHOTS"]
        previous = -1
        if not isinstance(shots, (list, tuple)):
            raise ValueError("Nook 参数 SHOTS 须为镜头起始时间和名称的列表")
        for shot in shots:
            if not isinstance(shot, (list, tuple)) or len(shot) != 2:
                raise ValueError("Nook 参数 SHOTS 每项须为 (起始秒, 名称)")
            start, label = shot
            if (type(start) not in (int, float) or not math.isfinite(start) or start < 0
                    or start <= previous or "DUR" in values and start >= values["DUR"]
                    or not isinstance(label, str) or not label.strip()):
                raise ValueError("Nook 参数 SHOTS 须按有效时间递增且处于片长内，并有名称")
            previous = start
    unresolved = sorted(required - values.keys())
    host_paths = sorted({node.value for node in ast.walk(tree)
                         if isinstance(node, ast.Constant) and isinstance(node.value, str)
                         and len(node.value) > 2 and node.value[0].isalpha()
                         and node.value[1:3] in {":/", ":\\"}})
    return {"scene": str(path), "sha256": hashlib.sha256(data).hexdigest(),
            "interface": "W/H/FPS/DUR/SHOTS and render(t)", "check": "syntax_and_interface_only",
            "literal_config": {key: values[key] for key in sorted(required & values.keys())},
            "unresolved_constants": unresolved, "literal_config_verified": not unresolved,
            "host_specific_paths": host_paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    commands.add_parser("plan").add_argument("scene", type=Path)
    args = parser.parse_args()
    try:
        report = check() if args.command == "check" else plan(args.scene)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, (getattr(exc, "stderr", None) or str(exc)).strip() + "\n")
    print(json.dumps({**report, "render_started": False, "model_request_sent": False},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
