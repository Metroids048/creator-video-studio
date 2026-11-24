#!/usr/bin/env python3
"""Local production entry. Run with --help for the project and revision commands."""
import argparse
import copy
import fcntl
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".studio"
BIN = STATE / "bin"
ADAPTERS = ROOT / "adapters"
VIBE = ROOT / "runtime" / "vibe"
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CAPABILITY_INDEX = ROOT / "docs" / "capability-index.json"
WORKS_ROOT = None


def works_root():
    # An explicit isolated root keeps diagnostic registration away from live works.
    return WORKS_ROOT or ROOT / "works"
HYPERFRAME_ARCHIVE = "workspace-content/manifest.json"
HYPERFRAME_OBJECTS = "workspace-content/objects/"
HYPERFRAME_MANIFEST_BLOB = "60c6f7edd2b88e934d0873d767aaaab4bc1865f2"
MODES = ("design", "research", "development", "recovery", "production", "delivery")
WRITE_MODES = {"make": "production", "revise-picture": "production", "revise-audio": "production",
               "revise-edit": "production", "revise-native": "production", "restore": "production",
               "resume": "production", "export": "delivery", "import-native": "recovery", "adopt-vibe": "recovery",
               "select-version": "recovery", "abandon-candidate": "recovery",
               "publish-pack": "delivery", "content-review": "delivery",
               "review-prepare": "development", "review-save": "development"}
def executable(name):
    bundled = BIN / name
    return Path(shutil.which(str(bundled)) or shutil.which(name) or bundled)


ENV = {
    **{key: os.environ[key] for key in ("HOME", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE")
       if key in os.environ},
    "PYTHONDONTWRITEBYTECODE": "1",
    "PATH": str(BIN) + os.pathsep + os.environ["PATH"],
    "HYPERFRAMES_NO_TELEMETRY": "1",
    "FFMPEG": str(executable("ffmpeg")),
    "FFPROBE": str(executable("ffprobe")),
    "HYPERFRAMES_FFMPEG_PATH": str(executable("ffmpeg")),
    "HYPERFRAMES_FFPROBE_PATH": str(executable("ffprobe")),
    "CHROME_PATH": os.environ.get("CHROME_PATH", CHROME),
    "PUPPETEER_EXECUTABLE_PATH": os.environ.get("CHROME_PATH", CHROME),
}


def model_route():
    # Read only the two string settings we own, including on macOS Python 3.9.
    config = (ROOT / ".codex" / "config.toml").read_text()
    settings = {}
    for key in ("model", "model_provider"):
        values = re.findall(rf'^{key}\s*=\s*"([^"]+)"\s*$', config, re.MULTILINE)
        if len(values) != 1:
            raise ValueError(f"工作室 Codex 配置缺少唯一的 {key}")
        settings[key] = values[0]
    if settings != {"model": "gpt-6.1-sol", "model_provider": "openai"}:
        raise ValueError("当前工作室仅使用本机 Codex 的 GPT-6.1 Sol")
    return {**settings, "host": "codex", "fallback": None}


def local_tools():
    tools = {name: os.access(executable(name), os.X_OK) for name in ("node", "ffmpeg", "ffprobe")}
    tools.update(codex=shutil.which("codex") is not None, chrome=Path(ENV["CHROME_PATH"]).is_file(),
                 say=Path("/usr/bin/say").is_file())
    return tools


def inspect_capability(record, tools):
    files = list(record["files"])
    if record["entry"]:
        files.append(record["entry"])
    missing_files = [path for path in files if not (ROOT / path).is_file()]
    if not (ROOT / record["source"]).exists():
        missing_files.append(record["source"])
    missing_tools = [name for name in record.get("tools", []) if not tools[name]]
    versions = {}
    for path in record.get("locks", []):
        if not (ROOT / path).is_file():
            missing_files.append(path)
        else:
            versions[path] = load(ROOT / path)["devDependencies"]["hyperframes"]
    return {
        "integration": record["integration"],
        "entry": record["entry"], "source": record["source"],
        "missing_files": missing_files, "missing_tools": missing_tools,
        "declared_hyperframes_versions": versions, "limits": record["limits"],
        "check": "missing_dependencies" if missing_files or missing_tools else "indexed_paths_present",
        "business_verified_here": False,
    }


def manifest_rows(path):
    with (ROOT / "docs" / path).open() as stream:
        for line in stream:
            yield json.loads(line)


def git_blob(path):
    if path.resolve() != path:
        return None
    with path.open("rb") as stream:
        checksum = hashlib.sha1(f"blob {os.fstat(stream.fileno()).st_size}\0".encode())
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def hyperframe_object_sizes():
    """Use byte ranges from the verified upstream 32 MiB chunk manifest."""
    path = ROOT / "sources" / "hyperframe-pinned" / HYPERFRAME_ARCHIVE
    if not path.is_file() or git_blob(path) != HYPERFRAME_MANIFEST_BLOB:
        return {}
    sizes = {}
    chunk_size = 32 * 1024**2
    for file in load(path)["files"]:
        remaining = file["bytes"]
        for chunk in file["chunks"]:
            size = min(chunk_size, remaining)
            if size <= 0 or sizes.setdefault(chunk, size) != size:
                raise ValueError("inconsistent Hyperframe chunk sizes in pinned manifest")
            remaining -= size
        if remaining:
            raise ValueError("incomplete Hyperframe chunk sizes in pinned manifest")
    return sizes


def inspect_source_inventory(aliases, verify=False):
    manifests = ("migration-resources.jsonl", "migration-resources-salvaged.jsonl")
    inventory_names = (*manifests, "migration-hyperframe-pinned.jsonl")
    missing_manifests = [name for name in inventory_names if not (ROOT / "docs" / name).is_file()]
    if missing_manifests:
        return {"check": "historical_inventory_unavailable", "missing_manifests": missing_manifests}
    blobs = {}
    for manifest in manifests:
        for row in manifest_rows(manifest):
            if "file" in row:
                path = row["file"]
            else:
                key = row.get("resource") or row["repo"]
                path = f"resources/{aliases.get(key, key)}/{row['path']}"
            blobs.setdefault(path, set()).add(row["blob"])
    missing, conflicts, mismatches, missing_paths = {}, [], [], []
    for path, hashes in blobs.items():
        if len(hashes) > 1:
            conflicts.append(path)
        target = ROOT / path
        if not target.is_file():
            group = Path(path).parts[1]
            missing[group] = missing.get(group, 0) + 1
            missing_paths.append(path)
        elif verify and git_blob(target) not in hashes:
            mismatches.append(path)
    historical = {"missing_media_objects": 0, "missing_other_paths": 0,
                  "different_local": 0, "gitlinks": 0}
    recovered, unrestored, different_recovered, different_unrestored = [], [], [], []
    archive_sizes = hyperframe_object_sizes() if verify else {}
    media = {"present_on_disk": 0, "git_blob_mismatches": [] if verify else None,
             "missing_on_disk": 0, "missing_known_bytes": 0, "missing_unknown_size_paths": 0,
             "sizes_include_pinned_manifest": bool(archive_sizes)}
    gitlinks = {}
    for row in manifest_rows("migration-hyperframe-pinned.jsonl"):
        path = row["path"]
        target = ROOT / "sources" / "hyperframe-pinned" / path
        if row["status"] == "missing":
            if path.startswith(HYPERFRAME_OBJECTS):
                historical["missing_media_objects"] += 1
                if target.is_file():
                    media["present_on_disk"] += 1
                    if verify and git_blob(target) != row["sha"]:
                        media["git_blob_mismatches"].append(path)
                else:
                    media["missing_on_disk"] += 1
                    size = row.get("size")
                    if size is None:
                        size = archive_sizes.get(target.name)
                    if size is None:
                        media["missing_unknown_size_paths"] += 1
                    else:
                        media["missing_known_bytes"] += size
            else:
                historical["missing_other_paths"] += 1
                paths = recovered if target.is_file() and git_blob(target) == row["sha"] else unrestored
                paths.append(path)
        elif row["status"] == "different-local":
            historical["different_local"] += 1
            paths = different_recovered if target.is_file() and git_blob(target) == row["sha"] else different_unrestored
            paths.append(path)
        elif row["status"] == "gitlink":
            historical["gitlinks"] += 1
            gitlinks[path] = {"commit": row.get("sha"), "archive_directory_present": target.is_dir()}
    return {
        "resources": {"manifests": manifests, "unique_paths": len(blobs),
                      "present_on_disk": len(blobs) - sum(missing.values()),
                      "missing_by_resource": missing, "missing_paths": missing_paths,
                      "manifest_blob_conflicts": conflicts, "git_blob_mismatches": mismatches if verify else None,
                      "check": "git_blob" if verify else "current_file_presence_only"},
        "hyperframe": {"manifest": "migration-hyperframe-pinned.jsonl",
                       "migration_counts": historical, "confirmed_recovered_other_paths": recovered,
                       "unrestored_other_paths": unrestored,
                       "confirmed_recovered_different_local_paths": different_recovered,
                       "unrestored_different_local_paths": different_unrestored,
                       "current_media": media, "gitlinks": gitlinks,
                       "check": "historical_counts_plus_current_overlay_checks"},
    }


def avs_media_versions(tools):
    result = {}
    for name in ("ffmpeg", "ffprobe"):
        dedicated = BIN / "avs" / name
        binary = dedicated if dedicated.is_file() and os.access(dedicated, os.X_OK) else executable(name)
        present = binary == dedicated or tools[name]
        output = run(binary, "-version", capture=True) if present else ""
        version = re.search(r"version (?:n)?([0-9]+)\.([0-9]+)(?:\.[0-9]+)?", output)
        display_path = binary.relative_to(ROOT) if binary.is_relative_to(ROOT) else binary
        result[name] = {"path": str(display_path) if present else None,
                        "version": version[0].split()[-1] if version else None,
                        "minimum": "6.0", "compatible": bool(version and (int(version[1]), int(version[2])) >= (6, 0))}
    return result


def inspect_framework(verify_resources=False):
    tools = local_tools()
    index = load(CAPABILITY_INDEX)
    capabilities = {name: inspect_capability(record, tools)
                    for name, record in index["routes"].items()}
    avs_tools = avs_media_versions(tools)
    if not all(value["compatible"] for value in avs_tools.values()):
        capabilities["avs-render"]["check"] = "missing_dependencies"
    return {
        "phase": "framework",
        "avs_media_tools": avs_tools,
        "model_config": model_route(),
        "model_session_verified": False,
        "tools_present": tools,
        "adapter_files_present": {
            name: not capabilities[name]["missing_files"]
            for name in ("code", "editor", "lanshu", "avs", "vibe")
        },
        "avs_hyperframes_cli_present":
            (ROOT / "runtime/avs/node_modules/hyperframes/bin/hyperframes.mjs").is_file(),
        "capabilities": capabilities,
        "source_inventory": inspect_source_inventory(index["resource_aliases"], verify_resources),
        "write_modes": WRITE_MODES,
        "model_request_sent": False,
        "render_started": False,
    }


def plan_editor(brief, base):
    result = subprocess.run([str(executable("node")), str(ADAPTERS / "native-editor.mjs"), "--plan", str(base)],
                            input=json.dumps(brief), env=ENV, cwd=ROOT, text=True,
                            capture_output=True, check=True)
    return json.loads(result.stdout)


def plan(brief_path):
    brief_path = brief_path.resolve(strict=True)
    brief = load(brief_path)
    from stage_handoff import require as require_handoff
    stage_report = require_handoff(brief, brief_path.parent)
    validate(brief)
    inputs = check_inputs(brief, brief_path.parent)
    route = brief.get("route", "code")
    editor_timeline = None
    if route == "editor":
        editor_timeline = plan_editor(brief, brief_path.parent)
    scenes = [
        {"shot": shot["id"], "engine": shot.get("engine", "vibe"), "source": shot.get("sceneAsset", "legacy-sample"),
         "sha256": digest(inputs[shot["sceneAsset"]][1] if shot.get("sceneAsset") else ADAPTERS / "scene.js")}
        for shot in brief.get("shots", []) if shot["kind"] == "code"
    ]
    from content_adaptation import inspect as inspect_adaptation
    from production_method import inspect as inspect_method
    return {
        "id": brief["id"], "route": route, "model_config": model_route(),
        "stage_handoff": stage_report,
        "editorial": editorial_plan(brief),
        "content_adaptation": inspect_adaptation(brief, inputs),
        "production_method": inspect_method(brief, inputs),
        "capability": inspect_capability(load(CAPABILITY_INDEX)["routes"][route], local_tools()),
        "input_ids": list(inputs), "scenes": scenes,
        "engine_capabilities": {engine: inspect_capability(
            load(CAPABILITY_INDEX)["routes"]["code" if engine == "vibe" else engine], local_tools())
            for engine in sorted({scene["engine"] for scene in scenes})},
        "audio_mode": brief.get("audio", {}).get("mode", "narrated") if route == "code" else "timeline",
        "output": {key: brief[key] for key in ("width", "height", "fps") if key in brief},
        "shot_count": len(brief.get("shots", [])),
        "total_frames": sum(shot["frames"] for shot in brief["shots"]) if route == "code" else None,
        "shot_kinds": sorted({shot["kind"] for shot in brief.get("shots", [])}),
        "operation_count": len(brief.get("operations", [])),
        "editor_timeline": editor_timeline,
        "model_request_sent": False, "render_started": False,
    }


def inspect_avs(episode_id):
    # The upstream Episode state is authoritative. Translate its proposed action
    # at the studio boundary instead of executing its original workflow runner.
    route = model_route()
    episode = json.loads(run("/bin/bash", ROOT / "scripts/avs.sh", "workflow", "status",
                             episode_id, "--json", capture=True))
    action = episode["next_action"]
    command = tuple(action.pop("command") or ())
    stage = action["stage"]
    if stage == "recovery":
        state = json.loads(run("/bin/bash", ROOT / "scripts/avs.sh", "episode", "status",
                               episode_id, "--json", capture=True))
        if state.get("blocked") and state.get("blocked_stage") in {"analyze", "visual-review", "creative-gate"}:
            stage = action["stage"] = state["blocked_stage"]
            action["kind"] = "human" if stage == "creative-gate" else "command"
    # These are source contracts, not permission to run their legacy commands.
    native = "runtime/avs/"
    stage_reads = {
        "analyze": ["schemas/input-manifest.schema.json", "schemas/asset-intelligence.schema.json"],
        "story-mine": ["skills-src/screen-story-miner/SKILL.md", "schemas/evidence-map.schema.json"],
        "direct": ["skills-src/short-video-director/SKILL.md", "schemas/creative-brief.schema.json"],
        "content": ["skills-src/write-video-script/SKILL.md", "skills-src/create-storyboard/SKILL.md",
                    "schemas/active-script.schema.json", "src/avs/content/schema.py"],
        "plan": ["schemas/creative-brief.schema.json", "schemas/evidence-map.schema.json",
                 "schemas/shot-plan.schema.json"],
        "pilot-review": ["skills-src/pilot-gate/SKILL.md"],
        "visual-review": ["skills-src/visual-critic/SKILL.md", "schemas/visual-approval.schema.json"],
        "creative-review": ["src/avs/qa/creative_review.py", "schemas/creative-review.schema.json"],
        "creative-gate": ["skills-src/quality-review/SKILL.md", "schemas/creative-review.schema.json"],
        "assets": ["skills-src/prepare-assets/SKILL.md", "schemas/asset-manifest.schema.json"],
        "deliver": ["skills-src/create-publish-pack/SKILL.md", "schemas/delivery-manifest.schema.json"],
    }
    action["reads"] = [".agents/skills/self-media-studio/references/AVS交接.md",
                       *[native + p for p in stage_reads.get(stage, ["skills-src/orchestrate-video-production/SKILL.md"])]]
    action["state_owner"] = "episode.json"
    if action["kind"] in {"human", "input", "complete"}:
        execution = action["kind"]
    elif action["kind"] == "agent" or stage in {
        "analyze", "story-mine", "direct", "visual-review", "pilot-review",
    }:
        execution = "codex"
        action["kind"] = "agent"
        action["model_config"] = route
        action["handoff_only"] = True
        action["writeback"] = "原生合同；先验证再确认状态，不执行旧 Provider 或自动 resume"
        if stage in {"analyze", "visual-review"}:
            operation = "adopt-analysis" if stage == "analyze" else "adopt-visual-review"
            action["writeback_argv"] = ["scripts/avs.sh", "--mode", "production", operation,
                                        episode["episode_id"], "<当前候选.json>"]
            action["writeback_requires_mode"] = "production"
        elif stage in {"story-mine", "direct", "pilot-review"}:
            execution = "not_connected"
            action["blocker"] = "历史 Pilot 路线绑定交易样例；保留原工程和独立评审方法，新录屏用通用 AVS/editor，不自动改造或跳过 Pilot"
    elif command in {("ingest",), ("plan",), ("content", "init"), ("timeline", "build"), ("subtitles", "build"),
                      ("preview",), ("final-render",), ("qa",), ("creative-review",), ("deliver",), ("export",)}:
        execution = "local"
        action["requires_mode"] = "production"
        action["argv"] = ["scripts/avs.sh", "--mode", "production", *command, episode["episode_id"]]
        if command == ("plan",):
            action["operation"] = "adopt_validated_agent_script"
        if command in {("preview",), ("final-render",), ("qa",), ("creative-review",), ("deliver",), ("export",)}:
            operation = "technical-qa" if command == ("qa",) else command[0]
            action["check_argv"] = ["scripts/avs.sh", "stage-check", operation, episode["episode_id"]]
            action["media_execution_verified"] = False
    else:
        execution = "not_connected"
        action["blocker"] = "该原生命令尚未开放工作室执行；保留阶段和源合同，不能自动跳过"
    if stage in {"creative-gate", "approve"}:
        operation = "adopt-creative-review" if stage == "creative-gate" else "adopt-approval"
        action["writeback_argv"] = ["scripts/avs.sh", "--mode", "production", operation,
                                    episode["episode_id"], "<同版观察或人工确认.json>"]
        action["writeback_requires_mode"] = "production"
        action["actual_review_verified"] = False
    if stage == "creative-review" and command == ("creative-review",):
        action["operation"] = "prepare_native_review_package"
        action["actual_review_verified"] = False
    action["execution"] = execution
    return {**episode, "model_request_sent": False, "render_started": False}


def run(*argv, capture=False, cwd=ROOT):
    return subprocess.run([str(arg) for arg in argv], cwd=cwd, env=ENV,
                          check=True, capture_output=capture, text=capture).stdout


def ff(*argv):
    run(executable("ffmpeg"), "-nostdin", "-hide_banner", "-loglevel", "error", "-y", *argv)


def probe(path):
    return json.loads(run(executable("ffprobe"), "-v", "error", "-show_streams", "-show_format",
                          "-of", "json", path, capture=True))


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(path, data):
    temp = path.with_name("." + path.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def identifier(value):
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError(f"项目或镜头 ID 无效：{value}")
    return value


def from_project(project, value):
    path = (project / value).resolve()
    if not path.is_relative_to(project.resolve()) or not path.is_file():
        raise ValueError(f"素材超出工程或不存在：{value}")
    return path


def checked_input_digest(item, source):
    sha = digest(source)
    if "sha256" in item and item["sha256"] != sha:
        raise ValueError(f"原始素材校验失败：{item['id']}")
    return sha


def import_inputs(brief, brief_path, project):
    if brief.get("stage_handoff"):
        brief["stage_handoff"]["task"] = str((brief_path.parent / brief["stage_handoff"]["task"]).resolve(strict=True))
    for item in brief.get("inputs", []):
        name = identifier(item["id"])
        src = (brief_path.parent / item["path"]).resolve()
        if not src.is_file():
            raise FileNotFoundError(src)
        dest = project / "inputs" / (name + src.suffix.lower())
        sha = checked_input_digest(item, src)
        item.setdefault("sourcePath", str(src))
        if dest.exists():
            if digest(dest) != sha:
                raise ValueError(f"已有不同素材，需使用新素材 ID：{name}")
        else:
            dest.parent.mkdir(exist_ok=True)
            temp = dest.with_name("." + dest.name + ".tmp")
            shutil.copyfile(src, temp)
            temp.replace(dest)
        item["path"] = dest.relative_to(project).as_posix()
        item["sha256"] = sha


def picture_brief(version, change, change_path=None, preview_only=False):
    from stage_handoff import require as require_handoff
    brief = load(version / "brief.json")
    if change.get("base", version.name) != version.name:
        raise ValueError("画面返修基线已变化，先检查 status")
    edits = change.get("visual")
    if (not isinstance(edits, dict) or not edits
            or not edits.keys() <= {"motif", "accent", "title", "kicker", "sceneAsset", "sceneAssets", "beatsAsset", "pageParams"}):
        raise ValueError("仅接受画面字段")
    target = next((s for s in brief.get("shots", [])
                   if s["id"] == change.get("shot") and s["kind"] == "code"), None)
    if target is None:
        raise ValueError("该版本无指定的代码动画镜头")
    engine = target.get("engine", "vibe")
    allowed = {"sceneAsset", "sceneAssets"} | ({"beatsAsset", "pageParams"} if engine == "lanshu" else set())
    if (engine != "vibe" and not edits.keys() <= allowed) or (engine == "vibe" and {"beatsAsset", "pageParams"} & edits.keys()):
        raise ValueError("原生画面返修须修改 sceneAsset/sceneAssets（Lanshu 可改 beatsAsset/pageParams），不接受无效的共享模板参数")
    original_visual_ids = {target.get("sceneAsset"), target.get("beatsAsset"), *target.get("sceneAssets", [])}
    if "pageParams" in edits:
        from html_shot import validate_page_params
        validate_page_params({**target, "pageParams": edits["pageParams"]})
        edits = {**edits, "pageParams": {**target.get("pageParams", {}), **edits["pageParams"]}}
    target.update(edits)
    visual_ids = {target.get("sceneAsset"), target.get("beatsAsset"), *target.get("sceneAssets", [])}
    replacements = change.get("inputs", [])
    if replacements:
        if (change_path is None or change.get("base") != version.name or not change.get("reason")
                or not change.keys() <= {"base", "reason", "shot", "visual", "inputs"}):
            raise ValueError("替换画面素材须绑定确切父版、原因及修改文件")
        old_rows = {row["id"]: row for row in brief["inputs"]}
        seen = set()
        preview = copy.deepcopy(brief)
        for row in preview["inputs"]:
            row["path"] = str(from_project(version.parent.parent, row["path"]))
        preview_rows = {row["id"]: row for row in preview["inputs"]}
        staged = []
        for row in replacements:
            name = identifier(row["id"])
            existing = old_rows.get(name)
            if (name in seen or name not in visual_ids
                    or (existing is not None and (name not in original_visual_ids
                        or row.get("kind") != existing["kind"]))
                    or (existing is None and (name not in target.get("sceneAssets", [])
                        or row.get("kind") not in {"image", "font", "data", "video"}))
                    or row.get("kind") not in {"scene", "image", "font", "data", "video"}):
                raise ValueError("仅接受本镜头已有画面素材或显式声明的新附属画面素材，音轨请用 revise-audio")
            seen.add(name)
            source = (change_path.resolve().parent / row["path"]).resolve(strict=True)
            checksum = checked_input_digest(row, source)
            if existing is None:
                preview_rows[name] = {"id": name, "kind": row["kind"]}
                preview["inputs"].append(preview_rows[name])
            preview_rows[name].update(path=str(source), sha256=checksum, sourcePath=str(source))
            staged.append((name, source, checksum, row["kind"]))
        # Check the complete replacement together. A new scene must still agree
        # with its story, frame clock, captions and unchanged soundtrack.
        require_handoff(preview, version.parent.parent)
        validate(preview)
        check_inputs(preview, change_path.resolve().parent)
        if preview_only:
            return preview
        for name, source, checksum, kind in staged:
            relative = Path("inputs") / ("picture-" + checksum + "-" + name + source.suffix.lower())
            destination = version.parent.parent / relative
            if destination.exists():
                if digest(destination) != checksum:
                    raise ValueError("画面返修缓存校验失败：" + name)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            if name not in old_rows:
                old_rows[name] = {"id": name, "kind": kind}
                brief["inputs"].append(old_rows[name])
            old_rows[name].update(path=relative.as_posix(), sha256=checksum, sourcePath=str(source))
    require_handoff(brief, version.parent.parent)
    validate(brief)
    check_inputs(brief, version.parent.parent)
    return brief


def audio_brief(version, change_path):
    """Replace or explicitly remove sound while keeping picture inputs intact."""
    from stage_handoff import require as require_handoff
    change = load(change_path)
    brief = load(version / "brief.json")
    if change.get("base") != version.name or brief.get("route") != "code":
        raise ValueError("音轨返修须绑定当前代码作品的确切父版")
    if not change.keys() <= {"base", "reason", "inputs", "audio", "eventTimeline"} or not change.get("reason"):
        raise ValueError("音轨返修只接受音频、同步表、新素材及原因")
    if change.get("audio") == {"mode": "silent"}:
        if change.get("inputs") or "eventTimeline" in brief or "eventTimeline" in change:
            raise ValueError("移除音轨不能附加素材或绕过故事声音同步合同")
        brief["audio"] = {"mode": "silent"}
        brief["audioRevision"] = {"base": version.name, "reason": change["reason"]}
        require_handoff(brief, version.parent.parent)
        validate(brief)
        check_inputs(brief, version.parent.parent)
        return brief
    additions = copy.deepcopy(change.get("inputs", []))
    old_ids = {row["id"] for row in brief["inputs"]}
    if (not additions or any(row.get("id") in old_ids or row.get("kind") not in {"audio", "data"}
                             for row in additions)):
        raise ValueError("替换音轨和同步表须使用新的素材 ID，保留父版")
    if change.get("audio", {}).get("mode") != "supplied":
        raise ValueError("此返修入口需提供实际音轨")
    brief["audio"] = change["audio"]
    if "eventTimeline" in brief:
        timeline = change.get("eventTimeline", {})
        if timeline.get("story") != brief["eventTimeline"]["story"]:
            raise ValueError("音轨返修不能改变原故事")
        brief["eventTimeline"] = timeline
    elif "eventTimeline" in change:
        raise ValueError("不能通过音轨返修增加故事时间线")
    # Check all replacement files before importing them into the work.
    preview = copy.deepcopy(brief)
    for row in preview["inputs"]:
        row["path"] = str(from_project(version.parent.parent, row["path"]))
    preview["inputs"].extend(additions)
    require_handoff(preview, version.parent.parent)
    validate(preview)
    check_inputs(preview, change_path.resolve().parent)
    imported = {"inputs": additions}
    import_inputs(imported, change_path.resolve(), version.parent.parent)
    brief["inputs"].extend(additions)
    brief["audioRevision"] = {"base": version.name, "reason": change["reason"]}
    check_inputs(brief, version.parent.parent)
    return brief


def check_inputs(brief, base):
    inputs = {}
    for item in brief.get("inputs", []):
        name = identifier(item["id"])
        if name in inputs:
            raise ValueError(f"素材 ID 重复：{name}")
        src = (base / item["path"]).resolve(strict=True)
        if not src.is_file():
            raise ValueError(f"素材不是文件：{item['path']}")
        if "sha256" in item:
            checked_input_digest(item, src)
        inputs[name] = (item.get("kind"), src)
    from production_method import inspect as inspect_method
    inspect_method(brief, inputs)
    if "coverAsset" in brief:
        cover = brief["coverAsset"]
        if not isinstance(cover, str) or cover not in inputs or inputs[cover][0] != "image":
            raise ValueError("封面需引用已声明的图片素材")
    for item in brief.get("inputs", []):
        native = item.get("nativeAsset")
        if native is not None and (native not in inputs or inputs[native][0] != "native"
                                   or not zipfile.is_zipfile(inputs[native][1])):
            raise ValueError("原生交接需引用已声明的 ZIP 素材")
    if brief.get("route") == "editor":
        if brief.get("primary") not in inputs or inputs[brief["primary"]][0] != "video":
            raise ValueError("主剪辑素材必须是视频")
        for op in brief["operations"]:
            if "assetId" in op and op["assetId"] not in inputs:
                raise ValueError(f"操作引用未声明的素材：{op['assetId']}")
        return inputs
    for shot in brief["shots"]:
        if shot["kind"] == "media":
            asset = shot.get("asset")
            if asset not in inputs or inputs[asset][0] != "video":
                raise ValueError(f"镜头引用未声明的视频：{shot['id']}")
        else:
            scene = shot.get("sceneAsset")
            engine = shot.get("engine", "vibe")
            if engine in {"art", "lanshu", "opuscar"}:
                if scene not in inputs or inputs[scene][0] != "scene" or inputs[scene][1].suffix.lower() != ".json":
                    raise ValueError(f"原生 HTML 镜头需要已声明的 JSON 场景素材：{shot['id']}")
                from html_shot import validate_scene

                validate_scene(sys.modules[__name__], inputs[scene][1], shot, brief, inputs)
                scene = None
            if engine == "nook":
                if scene not in inputs or inputs[scene][0] != "scene" or inputs[scene][1].suffix.lower() != ".py":
                    raise ValueError(f"Nook 镜头需要已声明的 Python 场景素材：{shot['id']}")
                from nook_shot import validate_scene

                validate_scene(inputs[scene][1], shot, brief)
                scene = None  # The JS scene contract below applies only to Vibe.
            if scene is not None and (scene not in inputs or inputs[scene][0] != "scene"
                                      or inputs[scene][1].suffix.lower() != ".js"):
                raise ValueError(f"镜头需要已声明的 JS 场景素材：{shot['id']}")
            if any(asset not in inputs or inputs[asset][0] not in {"image", "font", "data", "audio", "video"}
                   for asset in shot.get("sceneAssets", [])):
                raise ValueError(f"镜头附属素材未声明或类型不支持：{shot['id']}")
    audio = brief.get("audio", {})
    if audio.get("mode") == "supplied":
        if audio.get("asset") not in inputs or inputs[audio["asset"]][0] != "audio":
            raise ValueError("外部音轨需引用已声明的音频素材")
        if audio.get("preserveEncoded"):
            check_preserved_audio(inputs[audio["asset"]][1], brief)
    from event_templates import check_inputs as check_event_inputs
    check_event_inputs(brief, inputs)
    from photo_templates import check_inputs as check_photo_inputs
    check_photo_inputs(brief, inputs)
    from content_adaptation import inspect as inspect_adaptation
    inspect_adaptation(brief, inputs)
    return inputs


def media_start(shot):
    try:
        start = float(shot.get("in", 0))
    except (TypeError, ValueError, OverflowError):
        raise ValueError("视频素材起点必须是有限的非负秒数") from None
    if isinstance(shot.get("in"), bool) or not math.isfinite(start) or start < 0:
        raise ValueError("视频素材起点必须是有限的非负秒数")
    return start


def editorial_plan(brief):
    if not brief.get("content_strategy"):
        return {"status": "unbound", "note": "保留原制作合同；尚未绑定自媒体受众与选题"}
    from content_strategy import creative_contract
    return creative_contract(brief["content_strategy"])


def validate(brief):
    identifier(brief["id"])
    if brief.get("purpose") == "self-media" and not brief.get("content_strategy"):
        raise ValueError("自媒体制作需先通过 content-plan 绑定受众与选题")
    if brief.get("content_strategy"):
        if editorial_plan(brief)["status"] != "ready":
            raise ValueError("选题尚未就绪，不能进入制作")
    if brief.get("route", "code") == "editor":
        if not brief.get("inputs") or not brief.get("operations"):
            raise ValueError("编辑路线需提供输入、主素材和剪辑操作")
        return
    if brief.get("route", "code") != "code":
        raise ValueError("未知制作路线")
    w, h, fps = (brief[key] for key in ("width", "height", "fps"))
    if not (all(type(n) is int and n % 2 == 0 and 64 <= n <= 1920 for n in (w, h))
            and fps in (24, 25, 30)):
        raise ValueError("画幅须是 64–1920 的偶数，帧率支持 24、25、30")
    if not brief["shots"]:
        raise ValueError("至少需要一个镜头")
    audio = brief.get("audio", {})
    if audio.get("mode", "narrated") not in {"narrated", "silent", "supplied"}:
        raise ValueError("未知声音模式")
    if "preserveEncoded" in audio and (type(audio["preserveEncoded"]) is not bool
                                      or audio.get("mode") != "supplied"):
        raise ValueError("preserveEncoded 须为外部音轨的布尔选项")
    narrated = audio.get("mode", "narrated") == "narrated"
    narration_count = 0
    names = set()
    for shot in brief["shots"]:
        name = identifier(shot["id"])
        if (name in names or shot["kind"] not in {"code", "media"}
                or type(shot["frames"]) is not int or not 1 <= shot["frames"] <= fps * 120):
            raise ValueError(f"镜头 ID、类型或时长无效：{name}")
        names.add(name)
        if shot["kind"] == "code" and shot.get("engine", "vibe") not in {"vibe", "nook", "art", "lanshu", "opuscar"}:
            raise ValueError("未知代码镜头引擎")
        if "pageParams" in shot:
            from html_shot import validate_page_params
            validate_page_params(shot)
        if (shot["kind"] == "code" and shot.get("engine", "vibe") == "vibe"
                and not re.fullmatch(r"#[a-fA-F0-9]{6}", shot["accent"])):
            raise ValueError("镜头颜色需为六位十六进制值")
        if shot.get("fit", "contain") not in {"contain", "cover"}:
            raise ValueError("画幅适配只支持 contain 或 cover")
        if "captionsBaked" in shot and (shot["kind"] != "media" or type(shot["captionsBaked"]) is not bool):
            raise ValueError("已烧录字幕标记仅支持媒体镜头的布尔值")
        if len(set(shot.get("sceneAssets", []))) != len(shot.get("sceneAssets", [])):
            raise ValueError("镜头附属素材 ID 重复")
        if shot["kind"] == "media":
            media_start(shot)
        cues = shot.get("cues", [])
        if not isinstance(cues, list):
            raise ValueError("旁白或定时字幕 cues 必须是列表")
        for cue in cues:
            if narrated:
                text = cue if isinstance(cue, str) else cue.get("text") if isinstance(cue, dict) else None
                spoken = cue.get("spoken", text) if isinstance(cue, dict) else text
                if not isinstance(text, str) or not isinstance(spoken, str) or not spoken.strip():
                    raise ValueError("旁白需为非空文字，或包含 text 和非空 spoken 的对象")
                narration_count += 1
            else:
                if (not isinstance(cue, dict) or not isinstance(cue.get("text"), str)
                        or any(type(cue.get(key)) is not int for key in ("start", "end"))
                        or not 0 <= cue["start"] < cue["end"] <= shot["frames"]):
                    raise ValueError("无旁白时的字幕需使用镜头内 start/end 帧和 text")
    if narrated and not narration_count:
        raise ValueError("旁白模式至少需要一条有效旁白；无对白请显式选择 silent 或 supplied")


def srt_stamp(frame, fps):
    ms = round(frame * 1000 / fps)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def write_srt(path, cues, fps):
    path.write_text("\n".join(f"{i}\n{srt_stamp(c['start'], fps)} --> "
                               f"{srt_stamp(c['end'], fps)}\n{c['text']}\n"
                               for i, c in enumerate(cues, 1)))


def narration(brief, project, out):
    fps = brief["fps"]
    cache = project / ".cache" / "voice"
    cache.mkdir(parents=True, exist_ok=True)
    audio_dir = out / "voice"
    audio_dir.mkdir()
    sources, all_cues, at = [], [], 0
    for shot in brief["shots"]:
        cues, cursor = [], math.ceil(.32 * fps)
        for i, value in enumerate(shot.get("cues", [])):
            text = value if isinstance(value, str) else value["text"]
            spoken = text if isinstance(value, str) else value.get("spoken", text)
            voice = brief.get("voice", "Tingting")
            speed = str(brief.get("voice_rate", 184))
            key = hashlib.sha256(json.dumps([voice, speed, spoken], ensure_ascii=False).encode()).hexdigest()
            wav = cache / (key + ".wav")
            if not wav.exists():
                aiff = cache / (key + ".aiff")
                temp = cache / (key + ".tmp.wav")
                run("/usr/bin/say", "-v", voice, "-r", speed, "-o", aiff, spoken)
                ff("-i", aiff, "-ar", 48000, "-ac", 1, temp)
                temp.replace(wav)
                aiff.unlink()
            duration = float(probe(wav)["format"]["duration"])
            end = cursor + math.ceil(duration * fps)
            if end > shot["frames"]:
                raise ValueError(f"{shot['id']} 的实际旁白需要至少 {end} 帧，分镜只留了 {shot['frames']} 帧")
            cue = {"start": cursor, "end": end, "text": text}
            cues.append(cue)
            all_cues.append({**cue, "start": at + cursor, "end": at + end})
            saved = audio_dir / f"{shot['id']}-{i+1:02}.wav"
            shutil.copyfile(wav, saved)
            sources.append((saved, round((at + cursor) * 48000 / fps)))
            cursor = end + math.ceil(.14 * fps)
        shot["captionTiming"] = cues
        at += shot["frames"]
    if not sources:
        raise ValueError("成片需要旁白或使用剪辑路线配置原音")
    duration = at / fps
    # Quiet original synth bed underneath the narration.
    room = f"aevalsrc='0.015*(sin(2*PI*110*t)+0.4*sin(2*PI*164.81*t))*pow(sin(PI*t/{duration}),2)':s=48000:d={duration}"
    ff("-f", "lavfi", "-i", room, "-c:a", "pcm_s16le", audio_dir / "bed.wav")
    inputs = [audio_dir / "bed.wav"] + [path for path, _ in sources]
    filters = [f"[{i}:a]adelay={samples}S:all=1[v{i}]"
               for i, (_, samples) in enumerate(sources, 1)]
    filters.append("[0:a]" + "".join(f"[v{i}]" for i in range(1, len(inputs))) +
                   f"amix=inputs={len(inputs)}:duration=first:normalize=0,"
                   "highpass=f=45,alimiter=limit=0.87:latency=1,apad")
    ff(*[part for path in inputs for part in ("-i", path)], "-filter_complex", ";".join(filters),
       "-t", duration, "-ar", 48000, "-c:a", "aac", "-b:a", "160k", out / "audio.m4a")
    write_srt(out / "subtitles.srt", all_cues, fps)


def verified_input(brief, project, name):
    item = next((item for item in brief.get("inputs", []) if item["id"] == name), None)
    if item is None:
        raise ValueError(f"素材未声明：{name}")
    src = from_project(project, item["path"])
    if digest(src) != item["sha256"]:
        raise ValueError(f"原始素材校验失败：{name}")
    return src


def prepare_code_scene(shot, brief, project, native, previous=None):
    if shot.get("engine") in {"art", "lanshu", "opuscar"}:
        from html_shot import prepare

        return prepare(sys.modules[__name__], shot, brief, project, native, previous)
    if shot.get("engine", "vibe") == "nook":
        from nook_shot import prepare

        return prepare(sys.modules[__name__], shot, brief, project, native, previous)
    native.mkdir(parents=True)
    if previous is None:
        for src, name in ((ADAPTERS / "code-shot.html", "index.html"),
                          (VIBE / "fonts" / "SmileySans-Oblique.ttf", "font.ttf"),
                          (VIBE / "fonts" / "OFL-SmileySans.txt", "FONT-LICENSE.txt")):
            shutil.copyfile(src, native / name)
    else:
        for name in ("index.html", "font.ttf", "FONT-LICENSE.txt"):
            shutil.copyfile(previous / name, native / name)
    scene = (verified_input(brief, project, shot["sceneAsset"]) if shot.get("sceneAsset")
             else previous / "scene.js" if previous else ADAPTERS / "scene.js")
    shutil.copyfile(scene, native / "scene.js")
    assets = {}
    for name in shot.get("sceneAssets", []):
        src = verified_input(brief, project, name)
        item = next(item for item in brief["inputs"] if item["id"] == name)
        # Frozen input IDs rename files. ES modules still resolve their own
        # relative imports, so retain their original module basenames.
        filename = Path(item.get("sourcePath", src.name)).name if src.suffix.lower() in {".js", ".mjs"} else src.name
        relative = "assets/" + filename
        if relative in assets.values():
            raise ValueError(f"镜头附属素材文件名冲突：{filename}")
        (native / "assets").mkdir(exist_ok=True)
        shutil.copyfile(src, native / relative)
        assets[name] = relative
    shot_data = {**shot, "localAssets": assets} if assets else shot
    (native / "shot.js").write_text("const shot = " + json.dumps(shot_data, ensure_ascii=False) + ";\n")
    save(native.parent / "scene-source.json", {
        "asset": shot.get("sceneAsset"), "sha256": digest(native / "scene.js"),
        "assets": {name: digest(native / relative) for name, relative in assets.items()},
        "engine_sha256": digest(VIBE / "render.mjs"),
    })


def code_segment(shot, brief, out, project, previous=None):
    native = out / "shots" / shot["id"] / "film"
    prepare_code_scene(shot, brief, project, native, previous)
    from content_adaptation import record_consumption
    record_consumption(brief, shot, native)
    hashes = {path.relative_to(native).as_posix(): digest(path)
              for path in sorted(native.rglob("*")) if path.is_file()}
    hashes["@scene-source"] = digest(native.parent / "scene-source.json")
    key = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    work = project / ".cache" / "video" / key
    work.mkdir(parents=True, exist_ok=True)
    if not (work / "film").exists():
        shutil.copytree(native, work / "film")
    target = work / "segment.mp4"
    receipt = work / "receipt.json"
    hit = target.exists() and receipt.exists() and load(receipt)["sha256"] == digest(target)
    if not hit:
        tmp = work / "segment-tmp.mp4"
        tmp.unlink(missing_ok=True)
        if shot.get("engine") in {"art", "lanshu", "opuscar"}:
            from html_shot import render as render_html

            render_html(sys.modules[__name__], shot, work / "film", tmp)
        elif shot.get("engine", "vibe") == "nook":
            from nook_shot import render as render_nook

            render_nook(sys.modules[__name__], shot, work / "film", tmp)
        else:
            fps = f"--fps={shot['fps']}"
            run(executable("node"), VIBE / "render.mjs", f"--root={work}", "--frames", "--workers=2", fps)
            run(executable("node"), VIBE / "render.mjs", f"--root={work}", "--encode", f"--out={tmp}", fps)
        picture = next(stream for stream in probe(tmp)["streams"] if stream["codec_type"] == "video")
        if (int(picture["nb_frames"]), picture["width"], picture["height"], Fraction(picture["avg_frame_rate"])) != (
                shot["frames"], shot["width"], shot["height"], shot["fps"]):
            raise ValueError("代码镜头产物与分镜不符，未写入有效缓存")
        tmp.replace(target)
        save(receipt, {"sha256": digest(target)})
    return target, hit


def media_segment(shot, brief, project, out):
    start = media_start(shot)
    inputs = {a["id"]: a for a in brief["inputs"]}
    item = inputs[shot["asset"]]
    src = from_project(project, item["path"])
    if digest(src) != item["sha256"]:
        raise ValueError(f"原始素材校验失败：{item['id']}")
    native = out / "shots" / shot["id"]
    native.mkdir(parents=True)
    save(native / "media.json", shot)
    fps, w, h = (shot[name] for name in ("fps", "width", "height"))
    write_srt(native / "local.srt", shot["cues"], fps)
    target = native / "source-segment.mp4"
    fit = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
           if shot.get("fit") == "cover" else
           f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x181c20")
    filters = f"fps={fps},{fit},setsar=1"
    if shot["cues"] and not shot.get("captionsBaked", False):
        filters += ",subtitles=local.srt:force_style='FontName=PingFang SC,FontSize=19,Outline=1,MarginV=30'"
    run(executable("ffmpeg"), "-nostdin", "-v", "error", "-y", "-ss", start, "-i", src,
        "-vf", filters, "-frames:v", shot["frames"], "-an", "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-preset", "slow", "-crf", 16,
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-movflags", "+faststart", target, cwd=native)
    return target, False


def check_preserved_audio(source, brief):
    """A locked AAC track must already fit; never silently pad or transcode it."""
    info = probe(source)
    streams = info.get("streams", [])
    duration = float(info.get("format", {}).get("duration", 0))
    expected = sum(shot["frames"] for shot in brief["shots"]) / brief["fps"]
    if (len(streams) != 1 or streams[0].get("codec_type") != "audio"
            or streams[0].get("codec_name") != "aac"
            or not math.isfinite(duration) or abs(duration - expected) > 1 / brief["fps"]):
        raise ValueError("保留编码的锁定音轨须为与画面等长的纯 AAC 音频；不自动补齐或重编码")


def prepare_sound(brief, project, out):
    audio = brief.get("audio", {})
    mode = audio.get("mode", "narrated")
    if mode == "narrated":
        narration(brief, project, out)
        return
    fps = brief["fps"]
    all_cues, at = [], 0
    for shot in brief["shots"]:
        shot["captionTiming"] = shot.get("cues", [])
        all_cues.extend({**cue, "start": cue["start"] + at, "end": cue["end"] + at}
                        for cue in shot["captionTiming"])
        at += shot["frames"]
    write_srt(out / "subtitles.srt", all_cues, fps)
    if mode == "supplied":
        src = verified_input(brief, project, audio["asset"])
        if audio.get("preserveEncoded"):
            check_preserved_audio(src, brief)
            ff("-i", src, "-map", "0:a:0", "-c:a", "copy", out / "audio.m4a")
        else:
            ff("-i", src, "-vn", "-af", "apad", "-t", at / fps,
               "-ar", 48000, "-c:a", "aac", "-b:a", "160k", out / "audio.m4a")


def render(brief, project, out, parent=None):
    if brief.get("route") == "editor":
        save(out / "brief.json", brief)
        if "nativeEdit" in brief:
            edit = brief["nativeEdit"]
            source = native_source(project, edit["base"])
            check_native_patch(source, edit)
            save(out / "native-patch.json", edit)
            run(executable("node"), ADAPTERS / "native-patch.mjs", "render", source, out / "native-patch.json", out)
        else:
            run(executable("node"), ADAPTERS / "native-editor.mjs", project, out)
        return []
    parent_brief = None
    if parent:
        check_native_version(parent)
        parent_brief = load(parent / "brief.json")
    # Picture-only edits preserve exact audio; changed timing/captions/audio rebuild sound.
    sound_keys = lambda value: [(s["id"], s["frames"], s.get("cues", [])) for s in value["shots"]]
    input_keys = lambda value, name: [(r["kind"], r.get("sha256")) for r in value.get("inputs", [])
                                     if r["id"] == name]
    reuse_sound = (parent_brief is not None and brief["fps"] == parent_brief["fps"]
                   and brief.get("audio", {}) == parent_brief.get("audio", {})
                   and input_keys(brief, brief.get("audio", {}).get("asset"))
                   == input_keys(parent_brief, parent_brief.get("audio", {}).get("asset"))
                   and sound_keys(brief) == sound_keys(parent_brief))
    if reuse_sound:
        shutil.copyfile(parent / "subtitles.srt", out / "subtitles.srt")
        if (parent / "audio.m4a").exists():
            shutil.copyfile(parent / "audio.m4a", out / "audio.m4a")
        if (parent / "voice").is_dir():
            shutil.copytree(parent / "voice", out / "voice")
        for shot, old in zip(brief["shots"], parent_brief["shots"]):
            shot["captionTiming"] = copy.deepcopy(old["captionTiming"])
    else:
        prepare_sound(brief, project, out)
    save(out / "brief.json", brief)
    receipts, segments = [], []
    prior = {shot["id"]: shot for shot in parent_brief["shots"]} if parent else {}
    parent_receipts = {item["id"]: item for item in load(parent / "receipt.json")["segments"]} if parent else {}
    for shot in brief["shots"]:
        data = {**shot, **{key: brief[key] for key in ("width", "height", "fps")},
                "cues": shot["captionTiming"]}
        relative = Path("shots") / shot["id"] / "picture.mp4"
        # Code shots use code_segment's complete frozen-file fingerprint. Shot
        # fields alone miss replacements that retain the same input IDs.
        if (shot["kind"] == "media" and prior.get(shot["id"]) == shot
                and all(brief[k] == parent_brief[k] for k in ("width", "height", "fps"))
                and input_keys(brief, shot["asset"]) == input_keys(parent_brief, shot["asset"])):
            old = parent_receipts[shot["id"]]
            for name, sha in old.get("nativeFiles", {}).items():
                if digest(from_project(parent, name)) != sha:
                    raise ValueError(f"父版原生镜头校验失败：{name}")
            if digest(parent / relative) != old["sha256"]:
                raise ValueError(f"父版镜头文件校验失败：{shot['id']}")
            shutil.copytree((parent / relative).parent, (out / relative).parent)
            segments.append(relative)
            receipts.append({**old, "cacheHit": True, "reusedFrom": parent.name})
            continue
        if shot["kind"] == "media":
            src, hit = media_segment(data, brief, project, out)
        else:
            previous = parent / "shots" / shot["id"] / "film" if parent else None
            if previous is not None and shot["id"] in parent_receipts:
                # Revisions copy the parent's frozen native project; a file edited
                # after the parent rendered would otherwise reach the new film.
                for name, sha in parent_receipts[shot["id"]].get("nativeFiles", {}).items():
                    if digest(from_project(parent, name)) != sha:
                        raise ValueError(f"父版原生镜头校验失败：{name}")
            src, hit = code_segment(data, brief, out, project, previous)
        video = next(stream for stream in probe(src)["streams"] if stream["codec_type"] == "video")
        if (int(video["nb_frames"]), video["width"], video["height"], Fraction(video["avg_frame_rate"])) != (
                shot["frames"], data["width"], data["height"], data["fps"]):
            raise ValueError(f"镜头 {shot['id']} 的帧数、画幅或帧率与分镜不符")
        shutil.copyfile(src, out / relative)
        segments.append(relative)
        receipts.append({"id": shot["id"], "kind": shot["kind"], "frames": shot["frames"],
                         "file": str(relative), "sha256": digest(src), "cacheHit": hit,
                         "nativeFiles": {path.relative_to(out).as_posix(): digest(path)
                                         for path in sorted((out / relative.parent).rglob("*"))
                                         if path.is_file() and path != out / relative}})
    (out / "segments.txt").write_text("".join(f"file '{name.as_posix()}'\n" for name in segments))
    audio = ("-i", out / "audio.m4a", "-map", "0:v:0", "-map", "1:a:0") if (out / "audio.m4a").is_file() else ()
    ff("-f", "concat", "-safe", 0, "-i", out / "segments.txt", *audio,
       "-c", "copy", "-movflags", "+faststart", out / "video.mp4")
    return receipts


def latest(project):
    active = load(project / "current.json")["version"]
    if not isinstance(active, str) or not re.fullmatch(r"v[0-9]{4,}", active):
        raise ValueError("活动版本标识无效")
    version = project / "versions" / active
    check_delivery(version)
    return version


def inspect_bundle(bundle):
    from native_bundle import scan

    report = scan(bundle)
    return {**report, "archive_sha256": digest(bundle), "render_started": False}


def import_native(bundle, project_id):
    from native_bundle import scan

    project = works_root() / identifier(project_id)
    destination = project / "imports" / "native"
    # Stage on the destination filesystem and publish only verified bytes.
    works = works_root()
    works.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".native-import-", dir=works) as temp:
        staged = Path(temp) / "native"
        staged.mkdir()
        archive = staged / "editable.zip"
        shutil.copyfile(bundle, archive)
        sha = digest(archive)
        report = scan(archive, staged / "tree")
        receipt = {**report, "project": project_id, "archive_sha256": sha}
        save(staged / "receipt.json", receipt)
        project.mkdir(exist_ok=True)
        with (project / ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if (project / "current.json").exists() or (project / "pending.json").exists():
                raise ValueError("原样导入须使用无活动版本或待完成任务的作品 ID")
            if destination.exists():
                previous = load(destination / "receipt.json")
                if previous != receipt:
                    raise ValueError("此作品 ID 已绑定其他原生包")
                if digest(destination / "editable.zip") != sha or any(
                    digest(from_project(destination / "tree", name)) != expected
                    for name, expected in receipt["members"].items()
                ):
                    raise ValueError("已导入原生工程与回执不符，保留现场并使用新作品 ID")
                reused = True
            else:
                destination.parent.mkdir(exist_ok=True)
                staged.rename(destination)
                reused = False
    return {"project": project_id, "path": str(destination / "tree"), "route": report["route"],
            "archive_sha256": sha, "reused": reused, "render_started": False}


def srt_cues(path):
    """Parse an SRT file into timed cues; text is a subtitle record, not proof of singing."""
    stamp = re.compile(r"(\d+):(\d\d):(\d\d)[,.](\d{3})")
    cues = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            raise ValueError("字幕块缺少时间轴：" + block[:40])
        left, right = lines[timing].split("-->", 1)
        bounds = []
        for side in (left, right):
            match = stamp.search(side)
            if not match:
                raise ValueError("字幕时间格式无效：" + lines[timing])
            h, m, s, ms = map(int, match.groups())
            bounds.append(round(h * 3600 + m * 60 + s + ms / 1000, 3))
        text = "\n".join(lines[timing + 1:])
        if not text or bounds[1] <= bounds[0]:
            raise ValueError("字幕块文本为空或时间倒置：" + lines[timing])
        cues.append({"start": bounds[0], "end": bounds[1], "text": text})
    if not cues:
        raise ValueError("收编字幕没有可核对的唱词")
    return cues


def adopt_vibe(project_id, source, video, audio, subtitles, version, request):
    """Register an existing Vibe film into an isolated version and review chain.

    Copies bytes only. Never renders and never writes inside the source film or
    the source project's state. Registration is not quality acceptance, and the
    subtitle file is recorded as supplied text, not verified as actual singing.
    """
    short = identifier(project_id)
    root = works_root().resolve()
    source = Path(source).resolve(strict=True)
    live = (ROOT / "works").resolve()
    if WORKS_ROOT is None or root.is_relative_to(live) or live.is_relative_to(root):
        raise ValueError("收编登记根必须是隔离目录，不能位于或包含仓库 works/ 树")
    if source.is_relative_to(root):
        raise ValueError("收编源不能位于登记根内")
    return register_locked_film(root / ("vibe-" + short), short, source, video, audio, subtitles,
                                version, request)


def register_locked_film(project, title, source, video, audio, subtitles, version, request, native=None):
    route = "native-knowledge" if native else "adopted-vibe"
    def member(relative, label):
        path = (source / relative).resolve()
        if not path.is_relative_to(source) or not path.is_file():
            raise ValueError(f"收编{label}不存在或越出源目录：{relative}")
        return path

    video_path, audio_path, subtitle_path = member(video, "成片"), member(audio, "音轨"), member(subtitles, "字幕")
    if not re.fullmatch(r"v[0-9]{4,}", version):
        raise ValueError("收编版本标识无效")
    if not isinstance(request, str) or not request.strip():
        raise ValueError("收编须保留本版原要求")
    hashes = {"video": digest(video_path), "audio": digest(audio_path), "subtitles": digest(subtitle_path)}
    if native and hashes != native["media"]:
        raise ValueError("待登记文件与已预审并合成的原生文件不一致")
    cues = srt_cues(subtitle_path)
    media = probe(video_path)
    picture = next((s for s in media["streams"] if s.get("codec_type") == "video"), None)
    if picture is None:
        raise ValueError("收编成片缺少画面流")
    if not any(s.get("codec_type") == "audio" for s in media["streams"]):
        raise ValueError("收编成片缺少音轨，不能绑定已认可音轨")
    num, _, den = picture["avg_frame_rate"].partition("/")
    fps = float(num) / float(den or 1)
    duration = float(media["format"]["duration"])
    if not (fps > 0 and math.isfinite(duration) and duration > 0):
        raise ValueError("无法从成片确定帧率或时长")
    if cues[-1]["end"] > duration + 0.5:
        raise ValueError("字幕时间超出成片时长，字幕与成片不是同一版")
    brief = {"id": project.name, "title": title, "request": request.strip(),
             "route": route,
             "width": int(picture["width"]), "height": int(picture["height"]),
             "fps": round(fps, 6), "duration_seconds": duration,
             "frames": int(picture["nb_frames"]) if str(picture.get("nb_frames", "")).isdigit() else None,
             "audio": {"mode": "supplied", "asset": "approved-audio", "sha256": hashes["audio"], "locked": True},
             "requirements": [{"id": "r1", "text": request.strip()}],
             "inputs": [{"id": "approved-audio", "kind": "audio", "path": "inputs/approved-audio",
                         "sha256": hashes["audio"]}],
             "subtitles": {"cues": cues, "sha256": hashes["subtitles"],
                           "sung_match": "unverified", "picture_match": "unverified"},
             "adopted_from": {"source": str(source), "video": video, "audio": audio, "subtitles": subtitles,
                              "sha256": hashes},
             "content_adaptation": None, "unknown": ["唱词是否等于实际演唱", "逐句画面是否解释该句",
                                                     "成片内嵌音轨是否等于登记音轨", "画面质量与用户认可"]}
    if native:
        brief["content_format"] = "knowledge-song"
        brief["requirements"] = native["requirements"] or brief["requirements"]
        brief["native_handoff"] = native
    destination = project / "versions" / version
    project.mkdir(parents=True, exist_ok=True)
    with (project / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (project / "pending.json").exists():
            raise ValueError("此登记有未完版本，先用 status 核对，不覆盖")
        current = project / "current.json"
        active = latest(project) if current.exists() else None
        parent = None
        if active and active.name != version:
            if not native or check_delivery(active).get("route") != route or int(active.name[1:]) >= int(version[1:]):
                raise ValueError("此登记已绑定其他活动版本，保留现场并使用新版本号")
            parent = active.name
        if destination.exists():
            receipt = check_delivery(destination)
            if (receipt.get("adopted") != hashes or load(destination / "brief.json") != brief
                    or digest(destination / "inputs" / "approved-audio") != hashes["audio"]
                    or (native and (not active or active.name != version) and receipt.get("parent") != parent)):
                raise ValueError("此版本已绑定其他成片、音轨、字幕或要求，保留父版并使用新版本号")
            if native and (not active or active.name != version):
                save(current, {"version": version})
            return {"project": project.name, "version": version, "reused": True, "works_root": str(project.parent),
                    "delivery_ready": False, "render_started": False}
        (project / "versions").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".adopt-", dir=project / "versions") as temp:
            staged = Path(temp) / version
            (staged / "inputs").mkdir(parents=True)
            shutil.copyfile(video_path, staged / "video.mp4")
            shutil.copyfile(audio_path, staged / "inputs" / "approved-audio")
            shutil.copyfile(subtitle_path, staged / "subtitles.srt")
            save(staged / "brief.json", brief)
            copied = {"video": digest(staged / "video.mp4"), "audio": digest(staged / "inputs" / "approved-audio"),
                      "subtitles": digest(staged / "subtitles.srt")}
            if copied != hashes:
                raise ValueError("收编期间源文件变化，拒绝登记混合版本")
            files = ("video.mp4", "subtitles.srt", "brief.json")
            save(staged / "receipt.json", {"project": project.name, "version": version, "parent": parent,
                                           "route": route, "adopted": hashes, "media": media,
                                           "delivery": {name: digest(staged / name) for name in files}})
            staged.rename(destination)
        save(current, {"version": version})
    return {"project": project.name, "version": version, "reused": False, "works_root": str(project.parent),
            "delivery_ready": False, "sha256": hashes, "subtitle_cues": len(cues),
            "duration_seconds": duration, "render_started": False,
            "verified_here": "registration_and_byte_binding_only; sung_match_and_quality_unverified"}


def native_source(project, base):
    if base == "import":
        imported = project / "imports" / "native"
        receipt = load(imported / "receipt.json")
        if receipt["route"] != "editor":
            raise ValueError("该导入是代码工程，请在逐镜源码中修改")
        for name in ("native/timeline.json", "native/manifest.json"):
            if digest(from_project(imported / "tree", name)) != receipt["members"][name]:
                raise ValueError("已导入的原生时间线或素材清单与回执不符")
        check_native_tree(imported / "tree", receipt["members"])
        return imported / "tree" / "native"
    if not isinstance(base, str) or not re.fullmatch(r"v[0-9]{4,}", base):
        raise ValueError("补丁需绑定 import 或确切的 vNNNN")
    version = project / "versions" / base
    check_native_version(version)
    return version / "native"


def check_native_patch(source, patch):
    if (not re.fullmatch(r"[a-f0-9]{64}", patch.get("timeline_sha256", ""))
            or digest(source / "timeline.json") != patch["timeline_sha256"]):
        raise ValueError("补丁与原生时间线哈希不符")
    sections = {"clips", "audio", "captions", "overlays", "transitions", "output"}
    if (not isinstance(patch.get("locked"), list) or not set(patch["locked"]) <= sections
            or not isinstance(patch.get("operations"), list) or not 1 <= len(patch["operations"]) <= 2000):
        raise ValueError("补丁需提供有效 locked 与 operations")


def plan_native_edit(project, patch_path):
    patch = load(patch_path)
    source = native_source(project, patch["base"])
    check_native_patch(source, patch)
    output = run(executable("node"), ADAPTERS / "native-patch.mjs", "plan", source, patch_path.resolve(), capture=True)
    return {"project": project.name, "base": patch["base"], **json.loads(output), "render_started": False}


def inspect_project(project_id):
    from video_review import status as review_status
    project = works_root() / identifier(project_id)
    if not project.is_dir():
        raise FileNotFoundError(project)
    current = project / "current.json"
    pending = project / "pending.json"
    active = latest(project) if current.is_file() else None
    attempt = load(pending) if pending.is_file() else None
    imported = project / "imports" / "native"
    native = load(imported / "receipt.json") if (imported / "receipt.json").is_file() else None
    quality = review_status(sys.modules[__name__], active) if active else None
    ready = bool(quality and quality["status"] == "reviewed")
    return {"project": project_id, "current": active.name if active else None,
            "native_import": {**{key: native[key] for key in ("source_project", "source_version", "route", "archive_sha256")},
                              "path": str(imported / "tree")} if native else None,
            "delivery_hashes_verified": bool(active),
            "quality": quality,
            "current_role": ("reviewed_candidate" if ready else "candidate") if active else None,
            "delivery_ready": ready, "user_acceptance": (quality or {}).get("user_acceptance", "not_implied"),
            "pending": {"version": attempt["version"], "parent": attempt["parent"],
                        "state": ("candidate_commit_pending" if active and active.name == attempt["version"]
                                  else "review_preparation_pending" if (project / "versions" / attempt["version"]).is_dir()
                                  else "local_candidate_unconfirmed")} if attempt else None,
            "render_started": False}


def check_delivery(version):
    receipt = load(version / "receipt.json")
    if (not re.fullmatch(r"v[0-9]{4,}", version.name)
            or receipt.get("project") != version.parent.parent.name or receipt.get("version") != version.name):
        raise ValueError("作品版本与回执身份不一致")
    if "video.mp4" not in receipt["delivery"]:
        raise ValueError(f"{version.name} 回执缺少成片绑定")
    for name, sha in receipt["delivery"].items():
        if Path(name).name != name or name in {"", ".", ".."} or digest(from_project(version, name)) != sha:
            raise ValueError(f"{version.name} 交付文件校验失败：{name}")
    for segment in receipt.get("segments", []):
        for name, sha in segment.get("nativeFiles", {}).items():
            path = from_project(version, name)
            if not path.is_file() or digest(path) != sha:
                raise ValueError(f"{version.name} 原生镜头校验失败：{name}；导出后源文件已变化")
        if segment.get("file"):
            path = from_project(version, segment["file"])
            if not path.is_file() or digest(path) != segment.get("sha256"):
                raise ValueError(f"{version.name} 镜头文件校验失败：{segment['file']}")
    adopted = receipt.get("adopted")
    if adopted is not None:
        # Adopted versions bind a locked audio file outside delivery; every entry must see a change.
        audio = version / "inputs" / "approved-audio"
        if (not isinstance(adopted, dict) or adopted.get("video") != receipt["delivery"]["video.mp4"]
                or not audio.is_file() or digest(audio) != adopted.get("audio")):
            raise ValueError(f"{version.name} 锁定音轨校验失败：inputs/approved-audio 与登记哈希不符")
    return receipt


def inspect_native_receipt(receipt_path, source_root):
    """Read a standalone candidate's bindings without adopting or approving it."""
    root = source_root.resolve(strict=True)
    if not root.is_dir() or not receipt_path.resolve(strict=True).is_relative_to(root):
        raise ValueError("独立回执路径须位于显式 source-root 内")
    receipt = load(receipt_path)
    bindings = receipt.get("native_inputs")
    if (not isinstance(bindings, dict) or not bindings
            or not isinstance(receipt.get("file"), str)
            or not re.fullmatch(r"[a-f0-9]{64}", receipt.get("sha256", ""))
            or any(not isinstance(name, str) or not isinstance(sha, str)
                   or not re.fullmatch(r"[a-f0-9]{64}", sha) for name, sha in bindings.items())):
        raise ValueError("独立候选缺少有效的 file/sha256/native_inputs 绑定；不能据文件存在推断")
    output = from_project(root, receipt["file"])
    if not output.is_file() or digest(output) != receipt["sha256"]:
        raise ValueError("独立候选成片哈希不符：" + str(output))
    changed = []
    for name, sha in bindings.items():
        path = from_project(root, name)
        if not path.is_file() or digest(path) != sha:
            changed.append(name)
    if changed:
        raise ValueError("独立候选导出后源文件已变化：" + ", ".join(changed))
    return {"registration": "independent_candidate", "receipt": str(receipt_path.resolve()),
            "video": str(output), "sha256": receipt["sha256"],
            "delivery_hashes_verified": True, "native_inputs_verified": len(bindings),
            "audio_verified": False, "quality": "not_verified", "delivery_ready": False,
            "user_acceptance": "not_implied", "render_started": False}


def check_native_tree(tree, members):
    for name, sha in members.items():
        path = (tree / name).resolve()
        if (not path.is_relative_to(tree.resolve()) or not path.is_file() or digest(path) != sha):
            raise ValueError(f"原生文件与工程包不符：{name}")


def check_native_version(version):
    from native_bundle import MANIFEST, scan

    receipt = check_delivery(version)
    if "editable.zip" not in receipt["delivery"]:
        raise ValueError("版本回执缺少原生工程包绑定")
    report = scan(version / "editable.zip")
    if (report["source_project"] != version.parent.parent.name
            or report["source_version"] not in (None, version.name)):
        raise ValueError("原生工程包与作品版本身份不一致")
    # Inputs live at project level; OPEN.md and the bundle manifest are created only inside the ZIP.
    members = {name: sha for name, sha in report["members"].items()
               if name not in {"OPEN.md", MANIFEST} and not name.startswith("inputs/")}
    check_native_tree(version, members)


def commit_candidate(project, destination, pending):
    # A failed review-packet preparation must leave the parent and resume input
    # intact. A complete candidate is reusable on resume without rendering again.
    from video_review import prepare
    from stage_handoff import require as require_handoff
    require_handoff(load(destination / "brief.json"), project)
    prepare(sys.modules[__name__], destination)
    save(project / "current.json", {"version": destination.name})
    pending.unlink()
    return destination


def build(project, brief, parent=None, version=None):
    from stage_handoff import require as require_handoff
    if parent:
        previous_handoff = load(parent / "brief.json").get("stage_handoff")
        if previous_handoff and brief.get("stage_handoff") != previous_handoff:
            raise ValueError("返修不得移除或替换父版阶段交接")
    require_handoff(brief, project)
    validate(brief)
    if brief["id"] != project.name:
        raise ValueError("待完成需求与作品身份不一致")
    if version is not None and (not isinstance(version, str) or not re.fullmatch(r"v[0-9]{4,}", version)):
        raise ValueError("待完成版本标识无效")
    versions = project / "versions"
    if parent:
        if parent.parent != versions or not re.fullmatch(r"v[0-9]{4,}", parent.name):
            raise ValueError("待完成父版标识无效")
        check_delivery(parent)
    current = latest(project).name if (project / "current.json").exists() else None
    expected_parent = parent.name if parent else None
    confirming_commit = version is not None and current == version and (versions / version).is_dir()
    if current != expected_parent and not confirming_commit:
        raise ValueError("活动版与待完成父版不一致，保留候选并先核对 status")
    if not (version is not None and (versions / version).is_dir()):
        check_inputs(brief, project)
        if brief.get("route") == "editor" and not brief.get("nativeEdit"):
            plan_editor(brief, project)
    versions.mkdir(exist_ok=True)
    pending = project / "pending.json"
    if version is None:
        if pending.exists():
            raise ValueError("此作品有未完版本，先用 resume 续做")
        used = [int(path.name[1:]) for path in versions.iterdir()
                if path.is_dir() and re.fullmatch(r"v[0-9]{4,}", path.name)]
        used.extend(int(path.name.split(".")[1][1:]) for path in project.glob(".v*.abandoned-*.json")
                    if re.fullmatch(r"\.v[0-9]{4,}\.abandoned-[0-9]+\.json", path.name))
        number = max(used, default=0) + 1
        version = f"v{number:04d}"
        save(pending, {"brief": brief, "parent": parent.name if parent else None, "version": version})
    destination = versions / version
    if destination.exists():
        receipt = check_delivery(destination)
        if receipt.get("parent") != expected_parent:
            raise ValueError("候选回执与待完成父版不一致")
        if "brief.json" not in receipt["delivery"]:
            raise ValueError("候选回执缺少待完成需求绑定")
        candidate_brief, expected_brief = load(destination / "brief.json"), copy.deepcopy(brief)
        for document in (candidate_brief, expected_brief):
            if document.get("route", "code") == "code":
                for shot in document.get("shots", []):
                    shot.pop("captionTiming", None)
        if candidate_brief != expected_brief:
            raise ValueError("候选工程与待完成需求不一致")
        return commit_candidate(project, destination, pending)
    work = versions / ("." + version + ".building")
    if work.exists():
        # An interrupted attempt stays outside the delivery index. Reuse independently verified render caches.
        work.rename(versions / f".{version}.interrupted-{time.time_ns()}")
    work.mkdir()
    segments = render(brief, project, work, parent)
    metadata = probe(work / "video.mp4")
    picture = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
    if segments and int(picture["nb_frames"]) != sum(shot["frames"] for shot in brief["shots"]):
        raise ValueError("合成帧数与镜头表不一致")
    audio = any(stream["codec_type"] == "audio" for stream in metadata["streams"])
    if brief.get("route", "code") == "code":
        if audio == (brief.get("audio", {}).get("mode") == "silent"):
            raise ValueError("成片音轨与声明的声音模式不符")
    elif not audio:
        native_timeline = load(work / "native" / "timeline.json")
        assets = {item["id"]: item for item in load(work / "native" / "manifest.json")}
        if native_timeline["audio"] or any(assets[c["assetId"]].get("hasAudio") and c["gain"] > 0
                                           for c in native_timeline["clips"] + native_timeline["overlays"]):
            raise ValueError("原生时间线要求音轨，成片缺少音轨")
    ff("-i", work / "video.mp4", "-f", "null", "-")
    if "coverAsset" in brief:
        cover = verified_input(brief, project, brief["coverAsset"])
        ff("-i", cover, "-frames:v", 1, "-q:v", 2, work / "cover.jpg")
    else:
        frame_at = min(1.3, float(metadata["format"]["duration"]) / 3)
        ff("-ss", frame_at, "-i", work / "video.mp4", "-frames:v", 1, work / "cover.jpg")
    save(work / "publish.json", {"title": brief["title"], "description": brief.get("description", brief["request"]),
                                "cover": "cover.jpg", "subtitleFile": "subtitles.srt", "published": False,
                                "sources": brief.get("inputs", [])})
    from native_bundle import pack

    archive = work / "editable.zip"
    members = [(path.relative_to(work).as_posix(), path) for path in sorted(work.rglob("*"))
               if path.is_file() and path != work / "video.mp4"]
    members += [(item["path"], from_project(project, item["path"])) for item in brief.get("inputs", [])]
    pack(archive, members, brief["id"], version, brief.get("route", "code"), digest)
    files = ("video.mp4", "editable.zip", "subtitles.srt", "cover.jpg", "publish.json", "brief.json")
    save(work / "receipt.json", {"project": brief["id"], "version": version,
                                 "parent": parent.name if parent else None, "route": brief.get("route", "code"),
                                 "segments": segments, "media": metadata,
                                 "nativeBase": brief.get("nativeEdit", {}).get("base"),
                                 "nativeInputs": {item["id"]: item["nativeAsset"] for item in brief.get("inputs", [])
                                                  if "nativeAsset" in item},
                                 "delivery": {name: digest(work / name) for name in files}})
    work.rename(destination)
    return commit_candidate(project, destination, pending)


def restore_bundle(bundle_path, project, project_id):
    from native_bundle import scan

    scan(bundle_path)
    with zipfile.ZipFile(bundle_path) as bundle:
        brief = json.loads(bundle.read("brief.json"))
        if "nativeEdit" in brief:
            raise ValueError("该包有原生父版编辑，请用 import-native 再继续原生编辑")
        source_id = identifier(brief["id"])
        brief["id"] = project_id
        brief["restoredFrom"] = {"project": source_id, "archiveSha256": digest(bundle_path)}
        for item in brief.get("inputs", []):
            item_path = Path(item["path"])
            if item_path.parts != ("inputs", item_path.name) or item_path.name in {".", ".."}:
                raise ValueError("恢复包素材路径无效")
            dest = project / item_path
            dest.parent.mkdir(exist_ok=True)
            temporary = dest.with_name("." + dest.name + ".restoring")
            try:
                with bundle.open(item["path"]) as source, temporary.open("wb") as out:
                    shutil.copyfileobj(source, out)
                if digest(temporary) != item["sha256"]:
                    raise ValueError(f"恢复包素材校验失败：{item['id']}")
                if dest.exists() and digest(dest) != item["sha256"]:
                    raise ValueError(f"恢复素材与现有素材冲突：{item['id']}")
                temporary.replace(dest)
            finally:
                temporary.unlink(missing_ok=True)
    return brief


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, default="design",
                        help="工作室入口的显式执行模式（默认 design，只读）")
    parser.add_argument("--works-root", type=Path,
                        help="隔离的作品根（诊断登记用）；默认仓库 works/。adopt-vibe 必须显式给出")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="只读检查工作室配置和本地入口")
    doctor.add_argument("--verify-resources", action="store_true", help="另校验已落地资源的 Git blob")
    from intent import PROFILES
    intent = commands.add_parser("intent", help="匹配自然语言、工作模式、Skill 与路线；只读")
    intent.add_argument("request")
    intent.add_argument("--profile", choices=PROFILES, help="由 Codex 按上下文确认的意图")
    intent.add_argument("--script-file", type=Path, help="读取完整文案参与模板适配")
    visual = commands.add_parser("visual-assets", help="只读检索真实视觉素材、许可与设计配方，不生成")
    visual.add_argument("--query", default="", help="按名称、用途和标签筛选；多个词以空格分开")
    visual.add_argument("--recipe", help="只列指定视觉配方和它使用的素材")
    visual_build = commands.add_parser("visual-build", help="用已接入源码生成可编辑关键画面或待审动效素材")
    visual_build.add_argument("--engine", choices=["overlay", "table"], required=True)
    visual_build.add_argument("--input", type=Path, required=True)
    visual_build.add_argument("--out", type=Path, required=True, help="必须是尚不存在的新版本目录")
    visual_build.add_argument("--still", type=float, default=2)
    visual_build.add_argument("--video", action="store_true")
    visual_compose = commands.add_parser("visual-compose", help="将同版透明包装素材实际合成到本地图片或视频")
    visual_compose.add_argument("--material", type=Path, required=True)
    visual_compose.add_argument("--background", type=Path, required=True)
    visual_compose.add_argument("--out", type=Path, required=True)
    templates = commands.add_parser("templates", help="风格模板目录、内容匹配和工程准备")
    template_commands = templates.add_subparsers(dest="template_command", required=True)
    template_commands.add_parser("list", help="只读列出真实风格及验证范围")
    template_commands.add_parser("gallery", help="从目录和既有样片构建预览页，不渲染；需 development")
    template_preview = template_commands.add_parser("preview", help="只读启动本机样片预览服务")
    template_preview.add_argument("--port", type=int, default=0)
    template_preview.add_argument("--open", action="store_true", help="在本机浏览器打开目录")
    template_match = template_commands.add_parser("match", help="按内容方向推荐候选，不自动制作")
    template_match.add_argument("request")
    template_match.add_argument("--format", choices=("16:9", "9:16"), default="16:9")
    template_match.add_argument("--script-file", type=Path, help="完整文案，逐字绑定本次选择")
    template_match.add_argument("--purpose", choices=("production", "engineering_validation"), default="production")
    template_match.add_argument("--select", help="确认适配的工程 ID；不绕过双对标/画幅/形式检查")
    template_match.add_argument("--save", type=Path, help="保存可供 prepare 消费的路由回执；需 development")
    template_prepare = template_commands.add_parser("prepare", help="准备纸墨模板工程，不渲染")
    template_prepare.add_argument("story", type=Path)
    template_prepare.add_argument("--to", type=Path, required=True)
    commands.add_parser("plan", help="只读检查 brief 的选路和素材引用").add_argument("brief", type=Path)
    reference = commands.add_parser("reference-inspect", help="按需读取已有rea-video拆片包，不分析媒体或调用模型")
    reference.add_argument("package", type=Path)
    reference_part = reference.add_mutually_exclusive_group()
    # Import only when this command runs; parser setup must not require every sibling module.
    reference_part.add_argument("--topic")
    reference_part.add_argument("--shot", type=int)
    scene_context_parser = commands.add_parser('scene-context', help='读取当前镜头、前后事件和保留要求；不重写整稿')
    scene_context_parser.add_argument('brief', type=Path)
    scene_context_parser.add_argument('--shot', required=True)
    status_parser = commands.add_parser("status", help="只读核对活动版本，或显式绑定的独立候选回执")
    status_parser.add_argument("project", nargs="?")
    status_parser.add_argument("--native-receipt", type=Path)
    status_parser.add_argument("--source-root", type=Path)
    commands.add_parser("avs-next", help="只读查看 AVS 状态及工作室接手方式").add_argument("episode")
    commands.add_parser("inspect-bundle", help="核对原生工程包，不执行包内内容").add_argument("bundle", type=Path)
    native = commands.add_parser("import-native", help="原样导入，无渲染或版本切换")
    commands.add_parser("song-audition", help="核对实际混音盲辨及独立校准的音频听审，不渲染").add_argument(
        "report", type=Path)
    listen = commands.add_parser("song-listening-prepare", help="准备 1× 匿名音频和静音盲测，供实际听审")
    listen.add_argument("mix", type=Path)
    listen.add_argument("reference", type=Path)
    listen.add_argument("--output", type=Path, required=True)
    listen.add_argument("--reference-start", type=float, default=0)
    listen.add_argument("--reference-seconds", type=float, default=12)
    native_knowledge = commands.add_parser("native-knowledge", help="V13 派生工程的实际诊断、预审和整片制作入口")
    native_actions = native_knowledge.add_subparsers(dest="action", required=True)
    for action in ("describe", "check", "preview", "render", "compose", "register"):
        native_action = native_actions.add_parser(action)
        native_action.add_argument("source", type=Path)
        if action == "describe":
            native_action.add_argument("--project")
        if action in {"check", "render", "compose", "register"}:
            native_action.add_argument("--task", type=Path, required=True)
        if action in {"preview", "compose", "register"}:
            native_action.add_argument("--output", type=Path, required=True)
        if action == "register":
            native_action.add_argument("--version", required=True)
        if action == "preview":
            native_action.add_argument("--start-frame", type=int, required=True)
            native_action.add_argument("--frames", type=int, required=True)
    native.add_argument("project")
    native.add_argument("bundle", type=Path)
    adopt = commands.add_parser("adopt-vibe", help="只读收编已有 Vibe 成片到隔离登记根；不渲染、不改源作品")
    adopt.add_argument("project", help="Vibe 作品短 ID，不含 vibe- 前缀")
    adopt.add_argument("source", type=Path, help="只读源工程目录，不能是登记根或其子目录")
    adopt.add_argument("--video", required=True, help="源目录内的成片相对路径")
    adopt.add_argument("--audio", required=True, help="源目录内已认可音轨的相对路径")
    adopt.add_argument("--subtitles", required=True, help="源目录内字幕相对路径")
    adopt.add_argument("--version", required=True, help="登记版本，如 v0001")
    adopt.add_argument("--request", required=True, help="本版必须保留的原要求")
    workflow_parser = commands.add_parser("workflow", help="核对阶段交接；显式 confirm/reopen 只保存交接记录，不制作")
    workflow_parser.add_argument("task", type=Path)
    stage_change = workflow_parser.add_mutually_exclusive_group()
    stage_change.add_argument("--confirm-stage", help="冻结已存在的阶段字段、文件和依赖；不是人审认可")
    stage_change.add_argument("--reopen-stage", help="只开放指定阶段及下游，保留上游和历史")
    workflow_parser.add_argument("--reason")
    workflow_parser.add_argument("--evidence", type=Path)
    workflow_parser.add_argument("--stage", help="只返回该阶段及直接依赖的实际上下文，避免重新规划全片")
    commands.add_parser("review-check", help="核对审查记录绑定与声明覆盖").add_argument("review", type=Path)
    for command in ("review-prepare", "review-status", "review-save"):
        review = commands.add_parser(command, help="同版全片审查包、结论及交付状态；不渲染")
        review.add_argument("project")
        review.add_argument("--version", required=True)
        if command == "review-save":
            review.add_argument("review", type=Path)
    select = commands.add_parser("select-version", help="切换到已核验的旧版，不渲染")
    select.add_argument("project")
    select.add_argument("version")
    abandon = commands.add_parser("abandon-candidate", help="归档确切的未完候选，保留活动版和现场")
    abandon.add_argument("project")
    abandon.add_argument("version")
    commands.add_parser("make").add_argument("brief", type=Path)
    revise = commands.add_parser("revise-picture")
    revise.add_argument("project")
    revise.add_argument("change", type=Path)
    sound = commands.add_parser("revise-audio", help="沿父版替换或移除音轨，复用未改画面")
    sound.add_argument("project")
    sound.add_argument("change", type=Path)
    edit = commands.add_parser("revise-edit")
    edit.add_argument("project")
    edit.add_argument("operations", type=Path)
    for name in ("native-edit-plan", "revise-native"):
        patch = commands.add_parser(name)
        patch.add_argument("project")
        patch.add_argument("patch", type=Path)
    restore = commands.add_parser("restore", help="从包内输入重建并渲染；不是原样恢复")
    restore.add_argument("project")
    restore.add_argument("bundle", type=Path)
    commands.add_parser("resume", help="继续本地未完制作，可能渲染；先用 status 查询").add_argument("project")
    export = commands.add_parser("export")
    export.add_argument("project")
    export.add_argument("--version", help="将复制锁定到已经审查的当前版本")
    export.add_argument("--to", type=Path, required=True)
    content_plan = commands.add_parser("content-plan", help="从原始问题研究，或读取既有简报及真实失败反馈；不制作")
    content_plan.add_argument("context", type=Path, nargs="?")
    content_plan.add_argument("--question", help="尚未确定答案的原始问题；不要求预填开头、结尾或画面")
    content_plan.add_argument("--format", choices=("general", "knowledge-song"), default="general",
                              help="显式选用知识歌曲的事实、乐句、音乐段落与解释画面工作材料")
    for command in ("publish-check", "publish-pack"):
        commands.add_parser(command, help="检查或构建离线发布包；不上传").add_argument("spec", type=Path)
    commands.add_parser("publish-verify", help="核对离线包及原视频哈希").add_argument("package", type=Path)
    for command in ("content-analyze", "content-review"):
        analytics = commands.add_parser(command, help="分析或保存发布复盘；无数据时保持待验")
        analytics.add_argument("package", type=Path)
        analytics.add_argument("--metrics", type=Path)
        analytics.add_argument("--baseline", type=Path, action="append", default=[])
        analytics.add_argument("--feedback", type=Path, help="绑定本包的内容审查或真实用户反馈，回传下一次简报")
    args = parser.parse_args()
    global WORKS_ROOT
    WORKS_ROOT = args.works_root.resolve() if args.works_root else None
    required_mode = WRITE_MODES.get(args.command)
    if required_mode and args.mode != required_mode:
        parser.error(f"{args.command} 需要显式 --mode {required_mode}，请放在子命令前")
    if args.command == "song-audition":
        from knowledge_song import audio_audition
        print(json.dumps(audio_audition(args.report), ensure_ascii=False, indent=2))
        return
    if args.command == "song-listening-prepare":
        from song_listening import prepare as prepare_listening
        result = prepare_listening(args.mix, args.reference, args.output,
                                   args.reference_start, args.reference_seconds)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "native-knowledge":
        if args.action in {"preview", "render", "compose"} and args.mode != "production":
            parser.error("原生 preview/render/compose 需要显式 --mode production")
        if args.action == "register" and args.mode != "recovery":
            parser.error("原生 register 需要显式 --mode recovery")
        from native_knowledge import launch
        print(json.dumps(launch(sys.modules[__name__], args), ensure_ascii=False, indent=2))
        return
    if args.command == "adopt-vibe" and args.works_root is None:
        parser.error("adopt-vibe 必须显式 --works-root 指向隔离登记根，不能写入仓库 works/")
    if args.command in {"review-prepare", "review-status", "review-save"}:
        import video_review
        project = works_root() / identifier(args.project)
        if not re.fullmatch(r"v[0-9]{4,}", args.version):
            raise ValueError("审查必须绑定确切版本")
        version = project / "versions" / args.version
        if args.command == "review-status":
            # Integrity failures are errors, not an ordinary pending quality review.
            check_delivery(version)
            report = video_review.status(sys.modules[__name__], version)
        else:
            with (project / ".lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                report = (video_review.prepare(sys.modules[__name__], version) if args.command == "review-prepare"
                          else video_review.save(sys.modules[__name__], version, args.review))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    if args.command == "content-plan":
        from content_strategy import load as load_strategy, creative_contract, development_context, previous_work
        if (args.context is None) == (args.question is None):
            parser.error("content-plan 需提供简报路径或 --question，二者择一")
        snapshot = load_strategy(sys.modules[__name__], args.context) if args.context else None
        development = development_context(snapshot, ROOT, question=args.question, content_format=args.format)
        if args.context:
            development["previous_work"] = previous_work(sys.modules[__name__], args.context)
        print(json.dumps({"content_strategy": snapshot, "creative_contract": creative_contract(snapshot) if snapshot else None,
                          "development_context": development,
                          "render_started": False, "model_request_sent": False}, ensure_ascii=False, indent=2))
        return
    if args.command in {"publish-check", "publish-pack", "publish-verify", "content-analyze", "content-review"}:
        from publishing import plan as publication_plan, build as publication_build, verify as publication_verify
        from content_analytics import report as analytics_report, save_review

        studio = sys.modules[__name__]
        if args.command in {"publish-check", "publish-pack"}:
            spec, _, _, target = publication_plan(studio, args.spec)
            if args.command == "publish-check":
                from content_strategy import publication, creative_contract
                from publishing import packaging_quality
                report = {"source": spec["source"], "target": str(target), "status": "checked", "published": False,
                          "editorial": creative_contract(publication(studio, spec, args.spec)),
                          "quality": packaging_quality(spec)}
            else:
                project = works_root() / spec["source"]["project"]
                with (project / ".lock").open("a") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    report = publication_build(studio, args.spec)
        elif args.command == "publish-verify":
            report = publication_verify(studio, args.package)
        elif args.command == "content-analyze":
            report = analytics_report(studio, args.package, args.metrics, args.baseline, args.feedback)
        else:
            checked = publication_verify(studio, args.package)
            project = works_root() / checked["source"]["project"]
            with (project / ".lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                report = save_review(studio, args.package, args.metrics, args.baseline, args.feedback)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    if args.command == "templates":
        from video_templates import inventory, match, prepare

        if args.template_command in {"prepare", "gallery"} and args.mode != "development":
            parser.error(f"templates {args.template_command} 需 --mode development；此入口不渲染")
        if args.template_command == "preview":
            from template_gallery import preview
            preview(args.port, args.open, ROOT)
            return
        if args.template_command == "gallery":
            from template_gallery import build as build_gallery
            print(json.dumps(build_gallery(ROOT), ensure_ascii=False, indent=2))
            return
        if args.template_command == "list":
            report = inventory(ROOT)
        elif args.template_command == "match":
            script = args.script_file.read_text() if args.script_file else ""
            report = match(args.request, args.format, ROOT, script, args.purpose)
            if args.save:
                if args.mode != "development":
                    parser.error("保存路由回执需 --mode development")
                from video_templates import selection_receipt
                selected = args.select or (report["candidates"][0]["id"] if report["candidates"] else None)
                if not selected:
                    raise ValueError("没有符合本次用途的候选；不能保存空白兜底")
                receipt = selection_receipt(args.request, script, args.format, selected, args.purpose, ROOT)
                if args.save.exists():
                    raise ValueError("路由回执已存在，保留父版并使用新文件")
                args.save.parent.mkdir(parents=True, exist_ok=True)
                save(args.save, receipt)
                report["selection"] = receipt
        else:
            report = prepare(args.story, args.to, ROOT, require_selection=True)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    if args.command in {"doctor", "intent", "plan", "status", "avs-next", "inspect-bundle", "import-native", "adopt-vibe", "native-edit-plan", "workflow", "review-check"}:
        if args.command == "doctor":
            report = inspect_framework(args.verify_resources)
        elif args.command == "intent":
            from intent import route_task

            report = route_task(sys.modules[__name__], args.request, args.profile,
                                script=args.script_file.read_text() if args.script_file else "")
        elif args.command == "plan":
            report = plan(args.brief)
        elif args.command == "status":
            if args.native_receipt is not None:
                if args.project or args.source_root is None:
                    raise ValueError("独立候选 status 须同时指定 --native-receipt/--source-root，不接受 project")
                report = inspect_native_receipt(args.native_receipt, args.source_root)
            else:
                if not args.project or args.source_root is not None:
                    raise ValueError("status 须指定 project，或 --native-receipt/--source-root")
                report = inspect_project(args.project)
        elif args.command == "inspect-bundle":
            report = inspect_bundle(args.bundle)
        elif args.command == "native-edit-plan":
            report = plan_native_edit(works_root() / identifier(args.project), args.patch)
        elif args.command == "workflow":
            from workflow import handoff
            if args.stage and (args.confirm_stage or args.reopen_stage):
                raise ValueError("stage 查询不能与确认或重开一起使用")
            if (args.reason or args.evidence) and not args.reopen_stage:
                raise ValueError("reason/evidence 仅用于 reopen-stage")
            if args.confirm_stage or args.reopen_stage:
                from stage_handoff import update
                report = {"stage_handoff": update(args.task, args.confirm_stage, args.reopen_stage,
                                                  args.reason, args.evidence),
                          "model_request_sent": False, "render_started": False}
            elif args.stage:
                from stage_handoff import inspect as inspect_stages, context as stage_context
                report = stage_context(inspect_stages(load(args.task), args.task), args.stage)
            else:
                report = handoff(sys.modules[__name__], args.task, args.mode)
        elif args.command == "review-check":
            from workflow import check_review

            report = check_review(sys.modules[__name__], args.review)
        elif args.command == "import-native":
            report = import_native(args.bundle, args.project)
        elif args.command == "adopt-vibe":
            report = adopt_vibe(args.project, args.source, args.video, args.audio,
                                args.subtitles, args.version, args.request)
        else:
            report = inspect_avs(args.episode)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    if args.command == 'visual-assets':
        from visual_assets import inspect as inspect_visual_assets
        print(json.dumps(inspect_visual_assets(ROOT, args.query, args.recipe), ensure_ascii=False, indent=2))
        return
    if args.command == 'visual-build':
        if args.mode not in {"research", "development"}:
            parser.error("visual-build 需要 research 或 development 模式及当前任务的制作/验证授权")
        from visual_assets import inspect as inspect_visual_assets
        inspect_visual_assets(ROOT, recipe="editable-motion")
        subprocess.run([str(executable("node")), str(ROOT / "scripts/visual-materials/render.cjs"),
                        args.engine, str(args.input.resolve()), str(args.out.resolve()), str(args.still),
                        "video" if args.video else "still"], check=True, cwd=ROOT)
        return
    if args.command == 'visual-compose':
        if args.mode not in {"research", "development"}:
            parser.error("visual-compose 需要 research 或 development 模式及当前任务授权")
        from visual_composite import compose
        print(json.dumps(compose(sys.modules[__name__], args.material, args.background, args.out),
                         ensure_ascii=False, indent=2))
        return
    if args.command == 'reference-inspect':
        from reference_package import TOPICS, inspect
        if args.topic is not None and args.topic not in TOPICS:
            parser.error("未知拆片主题：" + args.topic)
        print(json.dumps(inspect(args.package, args.topic, args.shot), ensure_ascii=False, indent=2))
        return
    if args.command == 'scene-context':
        from content_adaptation import scene_context
        brief = load(args.brief)
        inputs = check_inputs(brief, args.brief.resolve().parent)
        print(json.dumps(scene_context(brief, inputs, args.shot), ensure_ascii=False, indent=2))
        return
    brief = load(args.brief) if args.command == "make" else None
    if brief:
        from stage_handoff import require as require_handoff
        require_handoff(brief, args.brief.resolve().parent)
        from video_templates import check_binding

        check_binding(brief, ROOT, require_selection=True)
        existing = works_root() / identifier(brief["id"])
        if (brief.get("purpose") == "self-media" and not brief.get("stage_handoff")
                and not (existing / "current.json").exists() and not (existing / "pending.json").exists()):
            raise ValueError("新自媒体作品须绑定 stage_handoff；先确认实际阶段产物，不迁移旧任务")
        from production_method import require_new
        require_new(brief, check_inputs(brief, args.brief.resolve().parent),
                    existing=(existing / 'current.json').exists() or (existing / 'pending.json').exists())
    STATE.mkdir(exist_ok=True)
    project = works_root() / identifier(brief["id"] if brief else args.project)
    if brief:
        plan(args.brief)
    if brief or args.command == "restore":
        project.mkdir(parents=True, exist_ok=True)
    if not project.is_dir():
        raise FileNotFoundError(project)
    with (project / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        pending = project / "pending.json"
        if args.command in {"make", "restore"} and (project / "imports" / "native").exists():
            raise ValueError("作品 ID 已绑定原生导入，请从原生工程继续或使用新 ID")
        if args.command == "abandon-candidate":
            if (not re.fullmatch(r"v[0-9]{4,}", args.version) or not pending.is_file()
                    or load(pending)["version"] != args.version):
                raise ValueError("只可归档当前未完候选的确切版本")
            if (project / "versions" / args.version).exists():
                raise ValueError("候选文件已提交，请核对后使用 resume 收尾")
            archived = project / f".{args.version}.abandoned-{time.time_ns()}.json"
            pending.rename(archived)
            print(archived)
            return
        if args.command == "select-version":
            if pending.exists() or not re.fullmatch(r"v[0-9]{4,}", args.version):
                raise ValueError("切换需确切版本号，且不能有未完成候选")
            version = project / "versions" / args.version
            check_delivery(version)
            save(project / "current.json", {"version": version.name})
        elif args.command == "resume":
            if not pending.exists():
                raise ValueError("没有可继续的本地待完成版本")
            attempt = load(pending)
            if attempt["parent"] is not None and (
                not isinstance(attempt["parent"], str) or not re.fullmatch(r"v[0-9]{4,}", attempt["parent"])
            ):
                raise ValueError("待完成父版标识无效")
            parent = project / "versions" / attempt["parent"] if attempt["parent"] else None
            version = build(project, attempt["brief"], parent, attempt["version"])
        elif args.command == "revise-native":
            patch = load(args.patch)
            parent = latest(project) if (project / "current.json").exists() else None
            expected = parent.name if parent else "import"
            if patch["base"] != expected:
                raise ValueError("补丁基线与当前工程不符，先检查 status")
            if pending.exists():
                raise ValueError("此作品有未完版本，先检查 status")
            preview = plan_native_edit(project, args.patch)
            if patch != load(args.patch):
                raise ValueError("规划期间补丁已变化，请重新核对")
            if not preview["changed"]:
                raise ValueError("补丁没有改变原生时间线")
            source = native_source(project, expected)
            brief_path = source.parent / "brief.json"
            brief = load(brief_path)
            if parent is None:
                brief["restoredFrom"] = load(source.parents[1] / "receipt.json")["archive_sha256"]
                brief["id"] = project.name
                import_inputs(brief, brief_path, project)
            brief["nativeEdit"] = patch
            version = build(project, brief, parent)
        elif args.command == "restore":
            if (project / "current.json").exists() or pending.exists():
                raise ValueError("恢复包须使用新的作品 ID，已有未完版本请用 resume")
            version = build(project, restore_bundle(args.bundle, project, project.name))
        elif args.command == "make":
            import_inputs(brief, args.brief.resolve(), project)
            if (project / "current.json").exists():
                version = latest(project)
                before = load(version / "brief.json")
                normalized = copy.deepcopy(before)
                for shot in normalized.get("shots", []):
                    shot.pop("captionTiming", None)
                if normalized != brief:
                    raise ValueError("此 ID 已有其他成片，需用新 ID 或局部修改命令")
            else:
                version = build(project, brief)
        else:
            version = latest(project)
        if args.command == "revise-picture":
            change = load(args.change)
            brief = picture_brief(version, change, args.change)
            brief["pictureRevision"] = change
            if brief != load(version / "brief.json"):
                version = build(project, brief, version)
        if args.command == "revise-audio":
            brief = audio_brief(version, args.change)
            version = build(project, brief, version)
        if args.command == "revise-edit":
            brief = load(version / "brief.json")
            if brief.get("route") != "editor":
                raise ValueError("该作品未使用原生剪辑时间线")
            if "nativeEdit" in brief:
                raise ValueError("该作品基于原生补丁，请继续使用 revise-native")
            operations = load(args.operations)
            if brief["operations"] != operations:
                brief["operations"] = operations
                version = build(project, brief, version)
        if args.command == "export":
            if args.version and version.name != args.version:
                raise ValueError("待导出版本与当前版本不一致，先核对 status")
            from video_review import require as require_review
            quality = require_review(sys.modules[__name__], version)
            target = args.to.resolve()
            if target.exists():
                raise ValueError(f"导出目录已存在：{target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".studio-export-", dir=target.parent) as staging:
                temp = Path(staging) / "delivery"
                temp.mkdir()
                for name in (*load(version / "receipt.json")["delivery"], "receipt.json"):
                    shutil.copyfile(version / name, temp / name)
                shutil.copytree(Path(quality["packet"]), temp / "quality-review")
                if require_review(sys.modules[__name__], version) != quality:
                    raise ValueError("导出期间审查变化，拒绝交付")
                if target.exists():
                    raise ValueError(f"导出目录已存在：{target}")
                temp.rename(target)
            print(target)
        print(version)
        if args.command != "export":
            from video_review import status as review_status, prepare as prepare_review
            production = args.command in {"make", "resume", "restore", "revise-picture", "revise-audio",
                                          "revise-edit", "revise-native"}
            quality = (prepare_review(sys.modules[__name__], version) if production
                       else review_status(sys.modules[__name__], version))
            print(json.dumps({"quality": quality, "next": "review-save", "delivery_ready": quality["status"] == "reviewed"},
                             ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (OSError, AttributeError, KeyError, TypeError, ValueError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr.strip(), file=sys.stderr)
        sys.exit(1)
