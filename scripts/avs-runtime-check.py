"""Run AVS's pinned, read-only runtime checks. No broad AVS doctor."""
from dataclasses import asdict
import json
import os
from pathlib import Path

from avs.doctor import check_ffmpeg, check_ffprobe, check_hyperframes, check_node
from avs.creative.reference_matcher import select_reference_patterns
import jsonschema

root = Path.cwd()
checks = {
    "node": asdict(check_node()),
    "ffmpeg": asdict(check_ffmpeg()),
    "ffprobe": asdict(check_ffprobe()),
}
cli = root / "node_modules/hyperframes/bin/hyperframes.mjs"
pinned = json.loads((root / "package.json").read_text())["devDependencies"]["hyperframes"]
if cli.is_file():
    checks["hyperframes"] = asdict(check_hyperframes(root))
    checks["hyperframes"]["passed"] &= checks["hyperframes"]["version"] == pinned
else:
    checks["hyperframes"] = {"passed": False, "message": "Missing pinned local CLI"}
checks["hyperframes"]["pinned"] = pinned
browser = Path(os.environ["HYPERFRAMES_BROWSER_PATH"])
checks["chrome_path"] = {"passed": browser.is_file() and os.access(browser, os.X_OK),
                         "path": str(browser)}
try:
    selection = select_reference_patterns("RUNTIME-CHECK")
    schema = json.loads((root / "schemas/reference-selection.schema.json").read_text())
    jsonschema.Draft7Validator(schema).validate(selection)
    checks["reference_library"] = {"passed": True, "path": "knowledge/references/patterns.yaml",
                                   "pattern_ids": [s["pattern_id"] for s in selection["selections"]]}
except (OSError, ValueError, jsonschema.ValidationError) as error:
    checks["reference_library"] = {"passed": False, "message": str(error)}
print(json.dumps({"checks": checks, "ready_for_media_test": all(c["passed"] for c in checks.values()),
                  "render_started": False, "model_request_sent": False}, ensure_ascii=False, indent=2))
