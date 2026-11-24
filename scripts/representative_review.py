"""Check that whole-film production consumes the actual representative review."""
import json
import math
from pathlib import Path
import subprocess

from knowledge_song import BIN, audio_audition


STAGE = "representative-review"


def required(brief):
    return brief.get("representative_review") == 1


def review(artifacts, brief, *, singing_method=None, required_reference=None):
    song = brief.get("content_format") == "knowledge-song"
    if len(artifacts) != 3 + song:
        raise ValueError("代表段须绑定观察记录、实拍或原生样片、审阅端原始回执"
                         + ("和样片混音首听" if song else ""))
    notes, media, capture = artifacts[:3]
    report = json.loads(Path(notes["path"]).read_text())
    if (not isinstance(report, dict) or report.get("media_sha256") != media["sha256"]
            or report.get("capture_sha256") != capture["sha256"]):
        raise ValueError("代表段观察与实际样片或审阅端回执不符")
    if report.get("open_issues") != []:
        raise ValueError("代表段仍有未解决问题或缺问题清单")
    if (report.get("speed") != 1 or any(not isinstance(report.get(key), str) or not report[key].strip()
                                       for key in ("endpoint", "hard_case", "observation"))):
        raise ValueError("代表段须记录实际审阅入口、原速结果和最难镜头的具体观察")
    if not Path(capture["path"]).stat().st_size:
        raise ValueError("审阅端未留下实际回执")
    if report["endpoint"] == "Google AI Studio":
        raw = json.loads(Path(capture["path"]).read_text())
        hashes = raw.get("hashes", {})
        if (not raw.get("url", "").startswith("https://aistudio.google.com/prompts/")
                or not raw.get("run_state", "").rstrip().endswith("Response ready.")
                or not raw.get("report_turn") or hashes.get("state") != "done"
                or media["sha256"] not in {row.get("sha256") for row in hashes.get("files", [])}):
            raise ValueError("AI Studio 尚无这份样片的实际文件与完整回复回执")

    probe = subprocess.run([str(BIN / "ffprobe"), "-v", "error", "-show_entries",
                            "format=duration:stream=codec_type", "-of", "json", media["path"]],
                           capture_output=True, text=True)
    if probe.returncode:
        raise ValueError("代表段文件无法读出声画")
    tracks = json.loads(probe.stdout)
    kinds = {row["codec_type"] for row in tracks.get("streams", [])}
    if "video" not in kinds or (song and "audio" not in kinds):
        raise ValueError("代表段缺所需的画面或音轨")
    duration = float(tracks.get("format", {}).get("duration", 0))
    start, end = report.get("start"), report.get("end")
    if (not math.isfinite(duration) or type(start) not in (float, int) or type(end) not in (float, int)
            or not 0 <= start < end <= duration):
        raise ValueError("代表段观察须绑定实际片内时间窗")
    if "audio" in kinds and (not isinstance(report.get("listening"), str) or not report["listening"].strip()):
        raise ValueError("有声代表段缺同版听审观察")
    if song:
        audio_audition(Path(artifacts[3]["path"]), required_media=Path(media["path"]),
                       singing_method=singing_method, required_reference=required_reference)
