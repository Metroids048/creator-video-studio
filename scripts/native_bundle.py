"""Round-trip studio editable archives without running their contents."""
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import unicodedata
import zipfile

MANIFEST = "studio-bundle.json"
ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
MAX_FILES = 20000
MAX_BYTES = 32 * 1024**3
MAX_JSON = 16 * 1024**2


def member_name(name):
    if (not isinstance(name, str) or any(ord(c) < 32 for c in name)
            or ":" in name or "\\" in name
            or any(p in {"", ".", ".."} for p in name.split("/"))):
        raise ValueError(f"工程包成员路径无效：{name!r}")
    sensitive = {".env", ".netrc", ".npmrc", ".pypirc", "credentials.json", "cookies.json",
                 "token.json", "id_rsa", "id_ed25519"}
    if any(p.casefold() in sensitive or p.casefold().startswith(".env.")
           or p.casefold().endswith((".pem", ".key", ".p12", ".pfx")) for p in name.split("/")):
        raise ValueError("工程包包含不允许导入的凭据文件类型")
    return name


def index(archive):
    entries = archive.infolist()
    if len(entries) > MAX_FILES or sum(i.file_size for i in entries) > MAX_BYTES:
        raise ValueError("工程包超出本地导入上限")
    files, spellings, directories, seen = {}, {}, set(), set()
    for entry in entries:
        is_dir = entry.is_dir()
        name = member_name(entry.orig_filename[:-1] if is_dir else entry.orig_filename)
        file_type = stat.S_IFMT(entry.external_attr >> 16)
        if (entry.flag_bits & 1 or file_type not in (0, stat.S_IFDIR if is_dir else stat.S_IFREG)
                or (is_dir and entry.file_size)):
            raise ValueError(f"工程包成员类型无效：{name}")
        parts = name.split("/")
        for n in range(1, len(parts) + 1):
            prefix = "/".join(parts[:n])
            key = unicodedata.normalize("NFC", prefix).casefold()
            if spellings.setdefault(key, prefix) != prefix:
                raise ValueError(f"工程包路径在本机冲突：{prefix}")
            if n < len(parts) or is_dir:
                directories.add(prefix)
        if name in seen:
            raise ValueError(f"工程包成员重复：{name}")
        seen.add(name)
        if not is_dir:
            files[name] = entry
    if files.keys() & directories:
        raise ValueError("工程包文件和目录冲突")
    return files


def read_json(archive, files, name):
    if name not in files or files[name].file_size > MAX_JSON:
        raise ValueError(f"工程包缺少有效的 {name}")
    return json.loads(archive.read(files[name]))


def check_native(archive, files, hashes):
    brief = read_json(archive, files, "brief.json")
    if not isinstance(brief.get("id"), str) or not ID.fullmatch(brief["id"]):
        raise ValueError("工程包缺少有效的作品 ID")
    route = brief.get("route", "code")

    def require(name, expected=None):
        member_name(name)
        if name not in hashes or (expected is not None and hashes[name] != expected):
            raise ValueError(f"工程包缺少匹配的成员：{name}")
        return name

    for item in brief.get("inputs", []):
        path = PurePosixPath(member_name(item["path"]))
        if len(path.parts) != 2 or path.parts[0] != "inputs" or not item.get("sha256"):
            raise ValueError("工程包原始输入缺少可验证的路径或哈希")
        require(item["path"], item["sha256"])
    if route == "editor":
        require("native/index.html")
        timeline = read_json(archive, files, "native/timeline.json")
        assets = read_json(archive, files, "native/manifest.json")
        if timeline["schemaVersion"] not in {1, 2} or not timeline["clips"]:
            raise ValueError("工程包原生时间线格式不受支持")
        by_id = {}
        for asset in assets:
            name = asset["id"]
            if not ID.fullmatch(name) or name in by_id:
                raise ValueError("工程包原生素材 ID 无效")
            by_id[name] = asset
        used = {clip["assetId"] for track in ("clips", "audio", "overlays")
                for clip in timeline.get(track, [])}
        for name in used:
            asset = by_id[name]
            work = member_name(asset["work"])
            suffix = PurePosixPath(work).suffix
            require(f"native/assets/{name}{suffix}", asset.get("fileHashes", {}).get(work))
            if asset.get("proxy"):
                require(f"native/assets/{name}-proxy.mp4", asset.get("fileHashes", {}).get(asset["proxy"]))
    elif route == "code" and brief.get("shots"):
        for shot in brief["shots"]:
            name = shot["id"]
            if not ID.fullmatch(name):
                raise ValueError("工程包镜头 ID 无效")
            if shot["kind"] == "code":
                engine = shot.get("engine", "vibe")
                if engine in {"art", "lanshu", "opuscar"}:
                    required = ("scene.json", "shot.json", "assets.json", "render-shot.mjs", "ENGINE-LICENSE")
                    required += (("effective-spec.json", "engine/clip.html", "engine/clip.js", "engine/spec_assets.py")
                                 if engine == "art" else
                                 ("engine/LICENSE", "engine/project.json") if engine == "opuscar" else
                                 ("engine/index.html", "engine/lib/story.js", "engine/beats.js", "engine/lib/core.js", "engine/lib/kit/kit.js", "engine/font-source.json"))
                    source = read_json(archive, files, f"shots/{name}/scene-source.json")
                    if source.get("engine") != engine or not source.get("files"):
                        raise ValueError("HTML 工程包缺少原生引擎指纹")
                    for file, sha in source["files"].items():
                        require(f"shots/{name}/film/{member_name(file)}", sha)
                    if any(file not in source["files"] for file in required):
                        raise ValueError("HTML 工程包引擎指纹未覆盖必要文件")
                    require(f"shots/{name}/film/scene.json", source.get("sha256"))
                elif engine == "nook":
                    required = ("scene.py", "shot.json", "assets.json", "scripts/run.py", "scripts/nookanim/render.py",
                                "scripts/nookanim/config.py", "dependencies.lock.json", "ENGINE-LICENSE",
                                "fonts/LXGWWenKai-Medium.ttf", "fonts/ShantellSans-VF.ttf", "fonts/MaShanZheng-Regular.ttf",
                                "fonts/OFL-WenKai.txt", "fonts/OFL-ShantellSans.txt", "fonts/OFL-MaShanZheng.txt")
                    source = read_json(archive, files, f"shots/{name}/scene-source.json")
                    if source.get("engine") != "nook" or not source.get("files"):
                        raise ValueError("Nook 工程包缺少原生引擎指纹")
                    for file, sha in source["files"].items():
                        require(f"shots/{name}/film/{member_name(file)}", sha)
                    if any(file not in source["files"] for file in required):
                        raise ValueError("Nook 工程包引擎指纹未覆盖必要文件")
                    require(f"shots/{name}/film/scene.py", source.get("sha256"))
                elif engine == "vibe":
                    required = ("index.html", "scene.js", "shot.js", "font.ttf")
                else:
                    raise ValueError("工程包包含未知代码镜头引擎")
                for file in required:
                    require(f"shots/{name}/film/{file}")
            elif shot["kind"] == "media":
                require(f"shots/{name}/media.json")
            else:
                raise ValueError("工程包包含未知镜头类型")
    else:
        raise ValueError(f"工程包原生路线尚未接入：{route}")
    return brief


def scan(path, destination=None):
    hashes = {}
    with zipfile.ZipFile(path) as archive:
        files = index(archive)
        if "brief.json" not in files:
            raise ValueError("工程包缺少 brief.json")
        for name, entry in files.items():
            digest = hashlib.sha256()
            with archive.open(entry) as source:
                target = destination / name if destination is not None else None
                if target is not None:
                    target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") if target is not None else nullcontext() as out:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(block)
                        if out is not None:
                            out.write(block)
            hashes[name] = digest.hexdigest()
        brief = check_native(archive, files, hashes)
        manifest = read_json(archive, files, MANIFEST) if MANIFEST in files else None
        version = None
        if manifest is not None:
            expected = {name: sha for name, sha in hashes.items() if name != MANIFEST}
            if (manifest.get("schema") != 1 or manifest.get("files") != expected
                    or manifest.get("project") != brief["id"]
                    or manifest.get("route") != brief.get("route", "code")):
                raise ValueError("工程包完整性清单与内容不符")
            version = manifest["version"]
            if not isinstance(version, str) or not re.fullmatch(r"v[0-9]{4,}", version):
                raise ValueError("工程包版本标识无效")
    return {"source_project": brief["id"], "source_version": version,
            "route": brief.get("route", "code"), "members": hashes,
            "integrity": "member_manifest" if manifest is not None else "legacy_crc_and_input_hashes"}


def pack(path, files, project, version, route, digest):
    # Stored project files and receipt have independent hashes. The manifest
    # excludes itself and the separately delivered master video.
    hashes = {}
    open_text = ("# 可编辑工程\n\n查看 `native/timeline.json` 或 `shots/*/film/`。"
                 "使用 studio.py inspect-bundle / import-native 检查或原样导入。\n").encode()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("OPEN.md", open_text)
        hashes["OPEN.md"] = hashlib.sha256(open_text).hexdigest()
        for name, source in files:
            member_name(name)
            if name in hashes or name == MANIFEST:
                raise ValueError(f"工程包成员重复：{name}")
            archive.write(source, name)
            hashes[name] = digest(source)
        manifest = json.dumps({"schema": 1, "project": project, "version": version,
                               "route": route, "files": hashes}, ensure_ascii=False, sort_keys=True)
        if len(manifest.encode()) > MAX_JSON:
            raise ValueError("工程包完整性清单超出导入上限")
        archive.writestr(MANIFEST, manifest)
        index(archive)
