"""Launch V13-derived project copies through Studio's knowledge-song handoff."""
import fcntl
from pathlib import Path
import sys
import tempfile

from knowledge_song import file_digest
from production_method import context
from stage_handoff import fingerprint, require
from video_review import AUDIO_HANDOFF


def local_file(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError("原生工程素材须保存在本任务目录内：" + str(name))
    return path


def inputs(studio, root):
    spec = studio.load(local_file(root, "composition.json"))
    picture = spec["assets"]["picture-source"]
    local_file(root, picture["file"])
    # The rendered picture digest is a derived result. The renderer records it
    # separately and the composition itself still checks the declared digest.
    picture.pop("sha256", None)
    files = {"render-shot.mjs", "compose.py", "shot.json", "effective-spec.json",
             "package.json", "beat-analysis.json", "engine/clip.html", "engine/scene.js"}
    files.update(asset["file"] for role, asset in spec["assets"].items() if role != "picture-source")
    for name in ("engine", "fonts"):
        files.update(path.relative_to(root).as_posix() for path in (root / name).rglob("*") if path.is_file())
    return {"files": {name: file_digest(local_file(root, name)) for name in sorted(files)},
            "composition": fingerprint(spec)}


def describe(studio, root, project, *, representative=True):
    method = context(studio.ROOT, "knowledge-song")
    brief = {"id": studio.identifier(project), "route": "native-knowledge",
             "content_format": "knowledge-song", "native_root": str(root),
             "native_inputs": inputs(studio, root), "method_sha256": fingerprint(method)}
    if representative:
        brief["representative_review"] = 1
    return brief, method


def check(studio, root, task_path):
    task_path = task_path.resolve(strict=True)
    task = studio.load(task_path)
    saved = studio.load(task_path.parent / task["brief"])
    # Historical task brief/receipts keep their original identity.
    brief, _ = describe(studio, root, task["project"], representative="representative_review" in saved)
    report = require({**brief, "stage_handoff": {"task": str(task_path)}}, task_path.parent)
    return brief, report


def packages(studio, root):
    if (root / "node_modules/puppeteer-core/package.json").is_file():
        return root / "package.json"
    return studio.ROOT / "runtime/vibe/package.json"


def preview(studio, root, output, start, count):
    shot = studio.load(local_file(root, "shot.json"))
    fps = shot["fps"]
    if not 1 <= count <= 12 * fps or start < 0 or start + count > shot["frames"]:
        raise ValueError("原生诊断片段限实际时间轴内不超过 12 秒")
    spec = studio.load(local_file(root, "composition.json"))
    audio = local_file(root, spec["assets"]["approved-audio"]["file"])
    if file_digest(audio) != spec["assets"]["approved-audio"]["sha256"]:
        raise ValueError("原生诊断音轨与工程声明不一致")
    with tempfile.TemporaryDirectory(prefix=".native-preview-", dir=output.parent) as temp:
        picture = Path(temp) / "picture.mp4"
        studio.run(studio.BIN / "node", studio.ADAPTERS / "native-html-shot.mjs",
                   root, picture, packages(studio, root), start, count)
        studio.run(studio.BIN / "ffmpeg", "-nostdin", "-v", "error", "-n", "-i", picture,
                   "-ss", str(start / fps), "-i", audio, "-map", "0:v:0", "-map", "1:a:0",
                   "-t", str(count / fps), "-c:v", "copy", "-c:a", "aac", output)
    return {"file": str(output), "sha256": file_digest(output), "diagnostic_only": True,
            "audio_handoff": AUDIO_HANDOFF}


def compose_candidate(studio, root, output, source, report, recheck):
    folder = output.parent
    receipt = {"source": source, "preview": fingerprint(report), "file": output.name}
    receipt_path = folder / "compose-receipt.json"
    if folder.exists() and (not folder.is_dir() or any(folder.iterdir())):
        if (output.is_file() and not output.is_symlink() and receipt_path.is_file()
                and not receipt_path.is_symlink()):
            receipt["sha256"] = file_digest(output)
            if studio.load(receipt_path) == receipt:
                recheck()
                return {"file": str(output), "sha256": receipt["sha256"], "reused": True,
                        "stage_handoff": report, "delivery_ready": False}
        raise ValueError("合成候选目录包含其它文件或已有回执不符；保留原目录")

    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".native-compose-", dir=folder.parent) as temporary:
        staged = Path(temporary) / "candidate"
        staged.mkdir()
        media = staged / output.name
        studio.run(sys.executable, local_file(root, "compose.py"), "--output", media, cwd=root, capture=True)
        checksum = file_digest(media)
        technical = staged / "technical-check.json"
        result = studio.load(technical)
        if (result.get("sha256") != checksum or result.get("file") != str(media)
                or result.get("full_decode") != "passed"):
            raise ValueError("原生合成技术回执与实际候选不一致")
        recheck()
        result["file"] = str(output)
        studio.save(technical, result)
        studio.save(staged / receipt_path.name, {**receipt, "sha256": checksum})
        staged.rename(folder)
    return {"file": str(output), "sha256": checksum, "reused": False,
            "stage_handoff": report, "delivery_ready": False}


def launch(studio, args):
    root = args.source.resolve(strict=True)
    if args.action == "describe":
        brief, method = describe(studio, root, args.project or root.name)
        return {"brief": brief, "production_method": method}
    if args.action == "check":
        _, report = check(studio, root, args.task)
        return {"stage_handoff": report, "render_started": False}

    archive = studio.ROOT / "works/falling-footage-1117"
    if root.is_relative_to(archive):
        raise ValueError("V13 历史工程只读；请使用本任务的独立副本")
    spec_path = local_file(root, "composition.json")
    receipt_path = local_file(root, ".native-knowledge-render.json")
    with local_file(root, ".native-knowledge.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.action == "preview":
            output = args.output.resolve()
            if output.is_relative_to(root) or output.is_relative_to(archive) or output.exists():
                raise ValueError("诊断输出须放在原生工程外的新路径")
            output.parent.mkdir(parents=True, exist_ok=True)
            return preview(studio, root, output, args.start_frame, args.frames)

        brief, report = check(studio, root, args.task)
        spec = studio.load(spec_path)
        asset = spec["assets"]["picture-source"]
        picture = local_file(root, asset["file"])
        brief_sha = fingerprint(brief)
        if args.action == "render":
            if picture.exists():
                checksum = file_digest(picture)
                if not receipt_path.is_file() or studio.load(receipt_path) != {"brief": brief_sha, "sha256": checksum}:
                    raise ValueError("目标画面已存在；返修使用新工程副本或新的画面路径")
                if asset.get("sha256") != checksum:
                    asset["sha256"] = checksum
                    studio.save(spec_path, spec)
                return {"file": str(picture), "sha256": checksum, "reused": True, "delivery_ready": False}
            picture.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".native-render-", dir=picture.parent) as temp:
                output = Path(temp) / "picture.mp4"
                studio.run(studio.BIN / "node", local_file(root, "render-shot.mjs"),
                           root, output, packages(studio, root))
                if check(studio, root, args.task) != (brief, report):
                    raise ValueError("原生渲染期间工程或预审发生变化，请按当前输入复验")
                asset["sha256"] = file_digest(output)
                studio.save(receipt_path, {"brief": brief_sha, "sha256": asset["sha256"]})
                output.rename(picture)
            studio.save(spec_path, spec)
            return {"file": str(picture), "sha256": asset["sha256"], "delivery_ready": False}

        actual = file_digest(picture)
        baseline = archive / "authoring-v0013"
        frozen_picture = studio.load(baseline / "composition.json")["assets"]["picture-source"]["sha256"]
        bound = {"brief": brief_sha, "sha256": actual}
        rendered = receipt_path.is_file() and studio.load(receipt_path) == bound
        inherited = actual == frozen_picture and brief["native_inputs"] == inputs(studio, baseline)
        if actual != asset.get("sha256") or not (rendered or inherited):
            raise ValueError("合成画面须来自同一已审工程的原生渲染或未经改动的 V13 冻结画面")
        output = args.output.resolve()
        composition_receipt = output.parent / "compose-receipt.json"
        if args.action == "register":
            project = (studio.works_root() / brief["id"]).resolve(strict=True)
            if (not root.is_relative_to(project) or not output.is_relative_to(project)
                    or output.is_relative_to(root) or output.is_relative_to(project / "versions")):
                raise ValueError("原生工程及其合成候选须归属同一作品，且候选在登记版本外")
            expected = {"source": bound, "preview": fingerprint(report), "file": output.name,
                        "sha256": file_digest(output)}
            if studio.load(composition_receipt) != expected:
                raise ValueError("原生候选与预审、渲染或合成回执不符")
            project_spec = studio.load(args.task)
            local_assets = {}
            media = {"video": expected["sha256"]}
            for key, role in (("audio", "approved-audio"), ("subtitles", "subtitles")):
                item = spec["assets"][role]
                local_assets[key] = str(local_file(root, item["file"]).relative_to(project))
                media[key] = item["sha256"]
            native = {"media": media, "composition": expected, "root": str(root.relative_to(project)),
                      "requirements": project_spec.get("requirements", [])}
            return studio.register_locked_film(project, project_spec.get("title", brief["id"]), project,
                                               str(output.relative_to(project)), local_assets["audio"],
                                               local_assets["subtitles"], args.version, project_spec["request"], native)

        if (output.parent.is_relative_to(root) or root.is_relative_to(output.parent)
                or output.parent.is_relative_to(archive) or archive.is_relative_to(output.parent)
                or output.name in {"render-command.json", "technical-check.json", composition_receipt.name}):
            raise ValueError("合成输出须位于原生工程外的独立候选目录")

        def recheck():
            if check(studio, root, args.task) != (brief, report) or file_digest(picture) != actual:
                raise ValueError("原生合成期间工程、画面或预审发生变化，候选未通过核验")

        return compose_candidate(studio, root, output, bound, report, recheck)
