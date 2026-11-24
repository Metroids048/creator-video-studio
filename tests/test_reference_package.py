"""CLI and original workflow checks with synthetic text packages; no AV/model run."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReferencePackageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.package = self.root / "reference"
        (self.package / "video/shots").mkdir(parents=True)
        (self.package / "VIDEO.md").write_text("# Synthetic fixture, not a real video analysis\n")
        for part in ("timeline", "sound", "cast"):
            (self.package / f"video/{part}.md").write_text(f"Synthetic {part}\n")
        (self.package / "video/shots/07.md").write_text("Synthetic shot seven\n")
        self.breakdown = {
            "tool": {"name": "rea-video", "version": "fixture"},
            "source": {"path": "/must/not/read/or/upload.mp4", "sha256_head": "not-a-full-hash"},
            "analysis": {"vlm": {"status": "ok", "whole_ok": True}},
            "whole_video_vlm": {"summary": "This synthetic answer proves no perception"},
            "shots": [{"index": 7, "vlm": {"_fallback": "mute_clip"}},
                      {"index": 8, "vlm": {"_fallback": "frames_only"}}]}
        self.save_breakdown()

    def save_breakdown(self):
        (self.package / "breakdown.json").write_text(json.dumps(self.breakdown))

    def cli(self, *args, error=None):
        mode = ["--mode", "research"] if args[0] == "workflow" else []
        result = subprocess.run([sys.executable, str(ROOT / "scripts/studio.py"), *mode, *map(str, args)],
                                cwd=self.root, capture_output=True, text=True, timeout=20)
        if error is not None:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(error, result.stderr)
            return
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def hashes(self):
        return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob("*") if p.is_file()}

    def test_inspection_preserves_package_and_never_attests_complete_av(self):
        before = self.hashes()
        report = self.cli("reference-inspect", self.package)
        self.assertEqual(self.hashes(), before)
        self.assertTrue(report["observation"]["whole_response_present"])
        self.assertFalse(report["observation"]["complete_av_verified"])
        self.assertFalse(report["source_media_verified"])
        self.assertEqual([r["fallback"] for r in report["observation"]["shot_fallbacks"]],
                         ["mute_clip", "frames_only"])
        for key in ("model_request_sent", "render_started", "state_written"):
            self.assertFalse(report[key])

    def test_topic_and_shot_return_only_consumed_handoff_files(self):
        sound = self.cli("reference-inspect", self.package, "--topic", "sound")
        self.assertEqual(sound["selected"]["text"], "Synthetic sound\n")
        self.assertIn(str(self.package / "video/sound.md"), sound["handoff"]["artifacts"])
        self.assertNotIn(str(self.package / "video/cast.md"), sound["handoff"]["artifacts"])
        shot = self.cli("reference-inspect", self.package, "--shot", 7)
        self.assertEqual(shot["selected"]["shot"]["index"], 7)
        file = shot["selected"]["file"]
        self.assertIn(file["path"], shot["handoff"]["artifacts"])
        self.assertEqual(file["sha256"], hashlib.sha256(Path(file["path"]).read_bytes()).hexdigest())
        self.cli("reference-inspect", self.package, "--topic", "timeline")

    def test_missing_shot_bad_producer_duplicate_index_and_escaping_file_rejected(self):
        self.cli("reference-inspect", self.package, "--shot", 9, error="不存在镜头")
        self.breakdown["tool"] = ["rea-video"]
        self.save_breakdown()
        self.cli("reference-inspect", self.package, error="仅支持 rea-video")
        self.breakdown["tool"] = {"name": "rea-video"}
        self.breakdown["shots"].append({"index": 7})
        self.save_breakdown()
        self.cli("reference-inspect", self.package, error="index 重复")
        self.breakdown["shots"].pop()
        self.save_breakdown()
        outside = self.root / "outside.md"
        outside.write_text("must not consume")
        (self.package / "video/sound.md").unlink()
        (self.package / "video/sound.md").symlink_to(outside)
        self.cli("reference-inspect", self.package, "--topic", "sound", error="越出包目录")

    def test_existing_workflow_freezes_selected_shot_and_invalidates_its_consumers(self):
        report = self.cli("reference-inspect", self.package, "--shot", 7)
        brief = {"id": "synthetic-reference", "script": "fixture"}
        task_path = self.root / "task.json"
        (self.root / "brief.json").write_text(json.dumps(brief))
        task = {"action": "research", "request": "Synthetic integration check only",
                "project": "synthetic-reference", "brief": "brief.json", "stages": [
                    {"id": "reference", "needs": [], "fields": [],
                     "artifacts": report["handoff"]["artifacts"]},
                    {"id": "script", "needs": ["reference"], "fields": ["/script"]},
                    {"id": "identity", "needs": [], "fields": ["/id"]}]}
        task_path.write_text(json.dumps(task))
        for stage in ("reference", "script", "identity"):
            self.cli("workflow", task_path, "--confirm-stage", stage)
        ready = self.cli("workflow", task_path)["stage_handoff"]
        self.assertEqual(ready["next_stages"], [])
        # An unconsumed topic must not force re-analysis or invalidate the stage.
        (self.package / "video/cast.md").write_text("Unconsumed cast revision")
        self.assertEqual(self.cli("workflow", task_path)["stage_handoff"]["next_stages"], [])
        (self.package / "video/shots/07.md").write_text("Changed consumed shot")
        changed = self.cli("workflow", task_path)["stage_handoff"]
        self.assertEqual(changed["reusable"], ["identity"])
        self.assertEqual(changed["next_stages"], ["reference"])
        self.cli("workflow", task_path, "--confirm-stage", "script", error="依赖")

    def test_live_routes_and_knowledge_song_context_expose_method(self):
        method = ROOT / ".agents/skills/studio-video-research/references/rea-video.md"
        for profile in ("reference", "research"):
            report = self.cli("intent", "研究指定视频链接的知识说唱形式，先不制作", "--profile", profile)
            self.assertIn(str(method.relative_to(ROOT)), json.dumps(report, ensure_ascii=False))
            self.assertFalse(report["execution_authorized_by_route"])
        result = self.cli("content-plan", "--format", "knowledge-song", "--question", "参考怎样衔接知识唱句与对象动作？")
        resources = result["development_context"]["resources"]
        resource = next(r for r in resources if r["file"] == str(method))
        self.assertEqual(resource["source_sha256"], hashlib.sha256(method.read_bytes()).hexdigest())
        self.assertEqual(resource["text"], method.read_text())
        self.assertFalse(result["model_request_sent"])
        self.assertFalse(result["render_started"])


if __name__ == "__main__":
    unittest.main()
