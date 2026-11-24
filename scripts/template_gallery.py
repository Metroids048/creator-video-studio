"""Build a local catalogue from the registry; replay existing media, never render films."""
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
from urllib.parse import quote
import webbrowser

from video_templates import ROOT, catalog, inventory, match, sha


def build(root=ROOT):
    output = root / "templates/gallery"
    registered = catalog(root)
    items = [item for item in registered if item.get("curation", {}).get("status") != "archived"]
    # Refuse missing/stale source media before writing the derived directory.
    for item in items:
        sample = item["sample"]
        for path, expected in sample["hashes"].items():
            if sha(root / path) != expected:
                raise ValueError(f"样片已变化，先核来源并更新登记：{path}")
        for key in ("path", "poster", "story"):
            if not (root / sample[key]).is_file():
                raise ValueError(f"缺样片依赖：{sample[key]}")
        adaptation = item.get("adaptation", {})
        if (not isinstance(adaptation.get("steps"), list) or not adaptation["steps"]
                or not all(isinstance(step, str) and step.strip() for step in adaptation["steps"])
                or not adaptation.get("avoid")):
            raise ValueError(f"缺完整换稿步骤或适配限制：{item.get('id')}")
    (output / "native").mkdir(parents=True, exist_ok=True)
    for item in items:
        sample = item["sample"]
        if sample["kind"] != "native-html":
            continue
        target = root / sample["player"]
        source = root / sample["path"]
        relative = Path(os.path.relpath(source.parent, target.parent)).as_posix()
        # Keep old projects immutable. Relative asset attributes point back to their
        # existing dependencies. Inline CSS font/image URLs need the same rewrite.
        content = source.read_text()
        content = re.sub(r'((?:src|href)=["\'])(?![a-z]+:|/|#)([^"\']+)',
                         lambda m: m[1] + quote(relative + "/" + m[2], safe="/[]"), content)
        content = re.sub(r'(url\(\s*["\']?)(?![a-z]+:|/|#)([^"\')\s]+)',
                         lambda m: m[1] + quote(relative + "/" + m[2], safe="/[]"), content)
        content = content.replace("</body>", '<script src="../player-bridge.js"></script></body>')
        target.write_text(content)
    qualification = inventory(root)
    items = qualification["templates"]
    payload = json.dumps(items, ensure_ascii=False).replace("<", "\\u003c")
    page = (output / "shell.html").read_text().replace("__CATALOG_JSON__", payload)
    formats_path = root / "templates/formats.json"
    formats = json.loads(formats_path.read_text())["formats"] if formats_path.is_file() else []
    active = {item["id"] for item in items}
    for item in formats:
        historical = item.get("compatible_production_templates", [])
        item["compatible_production_templates"] = [name for name in historical if name in active]
        if historical and not item["compatible_production_templates"]:
            item["implementation"] = "历史适配工程已归档，当前无生产适配。原记录：" + item["implementation"]
    page = page.replace("__FORMATS_JSON__", json.dumps(formats, ensure_ascii=False).replace("<", "\\u003c"))
    page = page.replace("__STYLE_COUNT__", str(len(items))).replace("__RESEARCH_COUNT__", str(len(formats)))
    page = page.replace("__PRODUCTION_COUNT__", str(qualification["production_qualified_count"]))
    page = page.replace("__MARKET_COUNT__", str(qualification["market_qualified_count"]))
    page = page.replace("__ARCHIVED_COUNT__", str(len(registered) - len(items)))
    (output / "index.html").write_text(page)
    report = {"production_qualified_count": qualification["production_qualified_count"],
              "market_qualified_count": qualification["market_qualified_count"], "styles": len(items), "source": "templates/catalog.json", "render_started": False,
              "registered": len(registered), "archived": len(registered) - len(items),
              "research_recipes": len(formats), "research_recipes_are_production_templates": False,
              "gallery": "templates/gallery/index.html",
              "media_reused": True, "native_demos": sum(t["sample"]["kind"] == "native-html" for t in items),
              "source_hashes": {p: h for t in items for p, h in t["sample"]["hashes"].items()}}
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def preview(port=0, open_browser=False, root=ROOT):
    """Read-only, loopback-only server, restricted to gallery dependencies."""
    items = catalog(root)
    allowed_files = {"templates/gallery/index.html", "templates/gallery/app.js", "templates/gallery/style.css",
                     "templates/gallery/player-bridge.js", "templates/gallery/manifest.json"}
    allowed_dirs = ["works/kit-preview/"]
    formats_path = root / "templates/formats.json"
    if formats_path.is_file():
        allowed_files.update(item["entry"] for item in json.loads(formats_path.read_text())["formats"])
    for item in items:
        allowed_files.update((item["entry"], item["sample"]["player"], item["sample"]["poster"], item["sample"]["story"]))
        allowed_files.update(item["sample"].get(k) for k in ("beats", "alternate", "learning_film", "comparison", "editable", "brief") if item["sample"].get(k))

    class Handler(SimpleHTTPRequestHandler):
        def do_POST(self):
            # Read-only routing uses the same full-copy implementation as the CLI.
            # No selection receipt, work, or render is created by the preview page.
            if self.path != "/api/templates/match":
                self.send_error(404)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 262144:
                    raise ValueError("请输入主题与完整文案，合计不超过256KB")
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError("路由输入必须是对象")
                topic, script = payload.get("topic"), payload.get("script")
                format = payload.get("format", "16:9")
                if (not isinstance(topic, str) or not topic.strip()
                        or not isinstance(script, str) or not script.strip()):
                    raise ValueError("需同时提供主题与完整文案")
                if format not in {"16:9", "9:16"}:
                    raise ValueError("未知目标画幅")
                result = match(topic, format, root, script, "production")
                status = 200
            except (ValueError, TypeError) as error:
                result, status = {"error": str(error), "render_started": False}, 400
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def send_head(self):
            self._remaining = None
            resolved = Path(self.translate_path(self.path)).resolve()
            try:
                relative = resolved.relative_to(root.resolve()).as_posix()
            except ValueError:
                self.send_error(404)
                return None
            if ((any(p.startswith(".") for p in Path(relative).parts) and relative not in allowed_files)
                    or not (relative in allowed_files or any(relative.startswith(p) for p in allowed_dirs))
                    or not resolved.is_file()):
                self.send_error(404)
                return None
            byte_range = self.headers.get("Range")
            if byte_range and resolved.suffix.lower() in (".mp4", ".mp3", ".wav"):
                size = resolved.stat().st_size
                match = re.fullmatch(r"bytes=(\d*)-(\d*)", byte_range)
                start, end = 0, size - 1
                if match and any(match.groups()):
                    left, right = match.groups()
                    if left:
                        start = int(left)
                        end = min(int(right), size - 1) if right else size - 1
                    else:
                        start = max(0, size - int(right))
                else:
                    start = size
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return None
                source = resolved.open("rb")
                source.seek(start)
                self._remaining = end - start + 1
                self.send_response(206)
                self.send_header("Content-Type", self.guess_type(str(resolved)))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.send_header("Content-Length", str(self._remaining))
                self.end_headers()
                return source
            return super().send_head()

        def copyfile(self, source, outputfile):
            try:
                if self._remaining is None:
                    return super().copyfile(source, outputfile)
                while self._remaining:
                    chunk = source.read(min(65536, self._remaining))
                    if not chunk:
                        break
                    outputfile.write(chunk)
                    self._remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                # Switching samples cancels an in-flight browser media request.
                pass

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=str(root)))
    url = f"http://127.0.0.1:{server.server_port}/templates/gallery/index.html"
    print(json.dumps({"url": url, "read_only": True, "render_started": False}, ensure_ascii=False), flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
