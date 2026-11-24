#!/usr/bin/env python3
"""Read-only Vibe runtime and native-workspace checks; never execute scene code."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def workspace(project, template=None):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", project):
        raise ValueError("Vibe 作品 ID 无效")
    root = ROOT / "works" / ("vibe-" + project)
    if root.resolve() != root:
        raise ValueError("Vibe 工程路径不能经符号链接离开作品目录")
    if template is not None and template not in {"lyric-mv", "knowledge-short"}:
        raise ValueError("Vibe 模板须为 lyric-mv 或 knowledge-short")
    if root.exists():
        detected = "knowledge-short" if (root / "film").is_dir() else "lyric-mv"
        if template and template != detected:
            raise ValueError("Vibe 模板与原生工程不符")
        template = detected
    required = ["BRIEF.md", "FILM_STATUS.md", "style.json"]
    required += (["film/index.html"] if template == "knowledge-short"
                 else ["STORYBOARD.md", "studio.html"])
    records = {root / name for name in required}
    records.update(root / name for name in ("SOURCES.md", "score.py"))
    for folder in ("src", "film"):
        records.update(p for p in (root / folder).rglob("*") if p.suffix in {".js", ".json", ".html"})
    bindings = {}
    for p in sorted(records):
        if p.is_file():
            if p.resolve() != p:
                raise ValueError("Vibe 原生记录不能通过符号链接读取其他目录")
            bindings[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return {"path": str(root), "exists": root.is_dir(), "template": template,
            "missing_contracts": [name for name in required if not (root / name).is_file()],
            "bindings": bindings, "state_owner": "FILM_STATUS.md and native records",
            "current": None, "production_state": "not_inferred_from_files"}


def runtime_check():
    kit = ROOT / "runtime/vibe"
    python = ROOT / "runtime/vibe-venv/bin/python"
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    files = [python, chrome, *(ROOT / ".studio/bin" / n for n in ("node", "ffmpeg", "ffprobe")),
             kit / "bin/film.sh", kit / "qa/gate.py", kit / "render.mjs",
             kit / "templates/lyric-mv/studio.html", kit / "templates/knowledge-short/film/index.html"]
    missing = [str(p) for p in files if not p.is_file()]
    report = {"check": "missing_dependencies" if missing else "checking", "missing": missing}
    if missing:
        return report
    env = {k: os.environ[k] for k in ("HOME", "TMPDIR", "LANG") if k in os.environ}

    def run(*argv):
        return subprocess.check_output([str(a) for a in argv], cwd=kit, env=env, text=True, timeout=60).strip()

    packages = json.loads(run(python, "-IB", "-c", "import json,numpy,scipy,fontTools; "
                             "from importlib.metadata import version; "
                             "print(json.dumps({p:version(p) for p in ('numpy','scipy','fonttools')}))"))
    expected = {p["name"]: p["version"] for p in json.loads((ROOT / "docs/vibe-macos-arm64.lock.json").read_text())}
    if packages != expected:
        raise ValueError("Vibe Python 依赖与固定锁不一致")
    node = ROOT / ".studio/bin/node"
    modules = json.loads(run(node, "--input-type=module", "-e",
        "import {createRequire} from 'node:module'; const r=createRequire(process.cwd()+'/package.json'); "
        "await import(r.resolve('puppeteer-core')); "
        "console.log(JSON.stringify(Object.fromEntries(['puppeteer-core','p5','p5.brush'].map(n=>[n,r.resolve(n)]))))"))
    metrics = json.loads((kit / "styles/_metrics.json").read_text())
    styles = list(kit.glob("styles/[!_]*.json"))
    fonts = {"PermanentMarker-Regular.ttf", "ShantellSans-VF.ttf"}
    for p in styles:
        font = json.loads(p.read_text())["font"]
        fonts.add(font)
        if font not in metrics:
            raise ValueError("Vibe 字体缺少既有测量记录：" + font)
    missing_fonts = [name for name in sorted(fonts) if not (kit / "fonts" / name).is_file()]
    filters = run(ROOT / ".studio/bin/ffmpeg", "-hide_banner", "-filters")
    required = {"ass", "drawtext", "loudnorm", "ebur128", "showspectrumpic", "blackdetect", "freezedetect"}
    available = {line.split()[1] for line in filters.splitlines() if len(line.split()) >= 2}
    if missing_fonts or required - available:
        raise ValueError(f"Vibe 缺少字体 {missing_fonts} 或 FFmpeg 滤镜 {sorted(required - available)}")
    return {**report, "check": "verified_runtime", "python": str(python), "packages": packages,
            "node": run(node, "--version"), "modules": modules, "styles": len(styles),
            "fonts": sorted(fonts), "filters": sorted(required), "chrome": str(chrome),
            "runtime_execution": "imports_and_versions_only", "native_production_verified": False}


def gate(project, stage="plan"):
    native = workspace(project)
    if not native["exists"]:
        raise ValueError("Vibe 原生工程不存在")
    result = subprocess.run([ROOT / "runtime/vibe-venv/bin/python", "-IB",
                             ROOT / "runtime/vibe/qa/gate.py", native["path"], "--stage=" + stage],
                            env={k: os.environ[k] for k in ("HOME", "TMPDIR", "LANG") if k in os.environ},
                            capture_output=True, text=True, timeout=90)
    if result.returncode not in (0, 1) or "GATE_" not in result.stdout:
        raise ValueError(result.stderr.strip() or "Vibe 原生记录检查失败")
    return {"workspace": native, "stage": stage, "records_pass": result.returncode == 0,
            "findings": result.stdout.strip(), "verified_here": "native_records_only"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("runtime-check")
    commands.add_parser("inspect").add_argument("project")
    gate_parser = commands.add_parser("gate")
    gate_parser.add_argument("project")
    gate_parser.add_argument("--stage", choices=("plan", "build", "ship"), default="plan")
    args = parser.parse_args()
    try:
        if args.command == "runtime-check":
            report = runtime_check()
        elif args.command == "gate":
            report = gate(args.project, args.stage)
        else:
            report = workspace(args.project)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps({**report, "render_started": False, "model_request_sent": False}, ensure_ascii=False, indent=2))
    return 1 if report.get("check") == "missing_dependencies" or report.get("records_pass") is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
