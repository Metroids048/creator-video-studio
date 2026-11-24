"""Read-only visual material lookup. Availability is not an aesthetic approval."""
import hashlib
import json
from pathlib import Path


CATALOG = "resources/visual-library/catalog.json"
METHOD = ".agents/skills/studio-visual-design/references/视觉设计方法.md"
REFERENCES = "resources/visual-library/reference-sources.json"
ALIASES = {
    "水彩": ["watercolor"], "版画": ["linocut"], "轮廓光": ["rim light"],
    "眩晕": ["dolly zoom"], "弹性": ["pop-in", "overshoot"],
    "颗粒": ["film grain"], "网点": ["halftone"], "孔版": ["risograph"],
    "故障": ["datamoshing"], "视差": ["parallax"], "蓝晒": ["cyanotype"],
}


def matches(text, query):
    text = text.casefold()
    return all(any(word in text for word in [term, *ALIASES.get(term, [])])
               for term in query.casefold().split())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bound_file(root, item):
    path = (root / item["path"]).resolve(strict=True)
    if not path.is_relative_to(root.resolve()):
        raise ValueError("视觉资产路径越出项目：" + item["path"])
    if digest(path) != item["sha256"]:
        raise ValueError("视觉资产或许可已变化：" + item["path"])
    return {**item, "absolute_path": str(path)}


def reference_libraries(root, query):
    """Offline reference lookup; source code, descriptive metadata and image rights differ."""
    manifest = root / REFERENCES
    sources = json.loads(manifest.read_text(encoding="utf-8"))
    result = []
    for library in sources["libraries"]:
        catalog_file = bound_file(root, library["catalog"])
        data = json.loads(Path(catalog_file["absolute_path"]).read_text(encoding="utf-8"))
        motion = library["id"] == "motion-prompt"
        entries = data["elements" if motion else "effects"]
        if len(entries) != library["count"] or len({e["id" if motion else "slug"] for e in entries}) != len(entries):
            raise ValueError("参考目录数量或身份不符：" + library["id"])
        license_info = {**library["license"], "files": [
            bound_file(root, f) for f in library["license"]["files"]]}
        selected = {key: {name: bound_file(root, file) for name, file in files.items()}
                    for key, files in library["selected"].items()}
        kits = [bound_file(root, file) for file in library.get("kits", [])]
        found = []
        if query.strip():
            for entry in entries:
                if not matches(json.dumps(entry, ensure_ascii=False), query):
                    continue
                key = entry["id" if motion else "slug"]
                local = selected.get(key, {})
                if motion:
                    item = {"id": key, "pack": entry["pack"], "name": entry["name"],
                            "meaning": entry["meaning"], "ask": entry["ask"],
                            "spec": entry["spec"], "use": entry["use"],
                            "preview_url": data["site"] + "#" + key, "files": local,
                            "kits": kits if "code" in local else [],
                            "code_status": "source_available_not_ported" if "code" in local else "specification_only"}
                    if "prompt" in local:
                        item["prompt_text"] = Path(local["prompt"]["absolute_path"]).read_text(encoding="utf-8")
                else:
                    item = {**entry, "url": library["url"].rstrip("/") + entry["article"],
                            "files": local, "image_use": "reference_only_no_artwork_license"}
                    if "detail" in local:
                        detail = json.loads(Path(local["detail"]["absolute_path"]).read_text(encoding="utf-8"))
                        item.update(prompt_text=detail.get("prompt"), definition=detail["effect"].get("body"),
                                    sources=detail["effect"].get("sources"), credit=detail["effect"].get("credit"))
                    else:
                        item["detail_status"] = "not_downloaded_use_official_reference_if_needed"
                found.append(item)
        result.append({k: library[k] for k in ("id", "name", "url", "version", "count", "use", "reference_only")}
                      | {"catalog": catalog_file, "license": license_info, "matches": found[:8],
                         "match_count": len(found), "returned": min(len(found), 8)})
    return {"manifest": str(manifest), "manifest_sha256": digest(manifest), "libraries": result,
            "query_required": not bool(query.strip()), "max_results_per_library": 8,
            "network_accessed": False}


def inspect(root, query="", recipe=None):
    root = Path(root).resolve()
    catalog_path = root / CATALOG
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    recipes = catalog["recipes"]
    if recipe:
        recipes = [item for item in recipes if item["id"] == recipe]
        if not recipes:
            raise ValueError("未知视觉配方：" + recipe)
    terms = query.casefold().split()
    ids = {value for item in recipes for value in item["asset_ids"]} if recipe else None
    assets = []
    for item in catalog["assets"]:
        haystack = " ".join([item["id"], item["name"], item["use"], *item["tags"]]).casefold()
        if ids is not None and item["id"] not in ids:
            continue
        if terms and not all(term in haystack for term in terms):
            continue
        if item["availability"] != "local" or not item["license"].get("spdx"):
            raise ValueError("资产未具备本地使用依据：" + item["id"])
        assets.append({**item, "files": [bound_file(root, f) for f in item["files"]],
                       "license": {**item["license"],
                                   "file": bound_file(root, item["license"]["file"])}})
    method = root / METHOD
    return {"schema": 1, "catalog": str(catalog_path), "catalog_sha256": digest(catalog_path),
            "query": query, "assets": assets, "recipes": recipes,
            "reference_libraries": reference_libraries(root, query),
            "method": {"file": str(method), "sha256": digest(method),
                       "text": method.read_text(encoding="utf-8")},
            "quality_status": "unassessed", "render_started": False,
            "limitations": "这是素材与视觉语言查询；visual-build 渲染 Overlay/Table。Motion Prompt 是规格/提示词与选取源码，Atlas 是参考资料，不把240/504项说成可直接渲染的组件或已授权图片。质量须按作品验证。"}
