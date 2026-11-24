"""Delivery regressions. Synthetic contracts test gates, never film quality."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import studio
import video_review
from review_fixture import reviewed_contract


class ReviewGateTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        active = patch.object(studio, "ROOT", self.root)
        active.start(); self.addCleanup(active.stop)
        self.version = self.root / "works/fixture/versions/v0001"
        self.version.mkdir(parents=True)
        (self.version / "video.mp4").write_bytes(b"synthetic video contract")
        studio.save(self.version / "brief.json", {"id": "fixture", "shots": []})
        studio.save(self.version / "receipt.json", {"project": "fixture", "version": "v0001",
                    "delivery": {"video.mp4": studio.digest(self.version / "video.mp4")}})

    def test_missing_review_never_delivers(self):
        with self.assertRaisesRegex(ValueError, "质量交付被阻止"):
            video_review.require(studio, self.version)

    def test_complete_contract_is_reviewed_not_user_accepted(self):
        reviewed_contract(studio, self.version)
        result = video_review.require(studio, self.version)
        self.assertEqual(result["user_acceptance"], "not_implied")
        self.assertEqual(result["verified_here"], "binding_coverage_and_recorded_decisions_only")

    def test_media_bound_user_rejection_survives_a_later_passing_review(self):
        reviewed_contract(studio, self.version)
        base, packet = video_review.manifest(studio, self.version)
        current = studio.load(base / "r0001.json")
        edit = self.root / "next-review.json"
        evidence = base / "user-feedback.json"
        studio.save(evidence, {"feedback": "user rejection fixture"})
        rejection = {"video_sha256": "0" * 64, "observation": "听完后明确否决本版",
                     "evidence": {evidence.name: studio.digest(evidence)}}
        studio.save(edit, {**current, "user_rejection": rejection})
        with self.assertRaisesRegex(ValueError, "确切成片"):
            video_review.save(studio, self.version, edit)
        rejection["video_sha256"] = packet["source"]["video_sha256"]
        studio.save(edit, {**current, "user_rejection": rejection})
        self.assertEqual(video_review.save(studio, self.version, edit)["user_acceptance"], "rejected")
        studio.save(edit, current)
        self.assertEqual(video_review.save(studio, self.version, edit)["status"], "blocked")
        with self.assertRaisesRegex(ValueError, "用户已否决"):
            video_review.require(studio, self.version)

    def test_status_distinguishes_current_candidate_and_delivery_readiness(self):
        studio.save(self.version.parents[1] / "current.json", {"version": "v0001"})
        result = studio.inspect_project("fixture")
        self.assertEqual(result["current_role"], "candidate")
        self.assertFalse(result["delivery_ready"])
        reviewed_contract(studio, self.version)
        result = studio.inspect_project("fixture")
        self.assertEqual(result["current_role"], "reviewed_candidate")
        self.assertTrue(result["delivery_ready"])
        self.assertEqual(result["user_acceptance"], "not_implied")

    def test_review_preparation_failure_preserves_parent_and_resumes_without_render(self):
        project = self.version.parents[1]
        studio.save(project / "current.json", {"version": "v0001"})
        brief = {"id": "fixture", "title": "commit ordering fixture", "request": "test",
                 "width": 64, "height": 64, "fps": 24, "audio": {"mode": "silent"},
                 "inputs": [], "shots": []}

        def render(document, project, target, parent):
            for name, data in {"video.mp4": b"synthetic candidate", "subtitles.srt": b""}.items():
                (target / name).write_bytes(data)
            studio.save(target / "brief.json", document)
            return []

        def ff(*args):
            if str(args[-1]).endswith("cover.jpg"):
                Path(args[-1]).write_bytes(b"synthetic cover")

        metadata = {"streams": [{"codec_type": "video"}], "format": {"duration": "1"}}
        def fail_before_commit(module, candidate):
            self.assertEqual(studio.load(project / "current.json"), {"version": "v0001"})
            self.assertTrue((project / "pending.json").is_file())
            studio.check_delivery(candidate)
            raise ValueError("fixture review preparation failure")

        # Only media construction is synthetic; use real build/pending/receipt/commit paths.
        with patch.object(studio, "validate"), patch.object(studio, "check_inputs"), \
                patch.object(studio, "render", side_effect=render) as renderer, \
                patch.object(studio, "probe", return_value=metadata), patch.object(studio, "ff", side_effect=ff), \
                patch.object(video_review, "prepare", side_effect=fail_before_commit):
            with self.assertRaisesRegex(ValueError, "review preparation failure"):
                studio.build(project, brief, self.version)
            renderer.assert_called_once()
        candidate = project / "versions/v0002"
        before = {p.name: p.read_bytes() for p in candidate.iterdir() if p.is_file()}
        self.assertEqual(studio.inspect_project("fixture")["pending"]["state"], "review_preparation_pending")
        # A repeated preparation failure in the existing-candidate branch cannot commit either.
        with patch.object(studio, "validate"), patch.object(studio, "render", side_effect=AssertionError("rerender")), \
                patch.object(video_review, "prepare", side_effect=fail_before_commit):
            with self.assertRaisesRegex(ValueError, "review preparation failure"):
                studio.build(project, brief, self.version, "v0002")
        def prepared(module, version):
            self.assertTrue((project / "pending.json").is_file())
            self.assertEqual(studio.load(project / "current.json"), {"version": "v0001"})
            return {"status": "pending"}
        with patch.object(studio, "validate"), patch.object(studio, "render", side_effect=AssertionError("rerender")), \
                patch.object(video_review, "prepare", side_effect=prepared):
            self.assertEqual(studio.build(project, brief, self.version, "v0002"), candidate)
        self.assertEqual(studio.load(project / "current.json"), {"version": "v0002"})
        self.assertFalse((project / "pending.json").exists())
        self.assertEqual(before, {p.name: p.read_bytes() for p in candidate.iterdir() if p.is_file()})
        self.assertFalse(studio.inspect_project("fixture")["delivery_ready"])

    def test_cli_resume_prepares_before_commit_and_reuses_exact_packet(self):
        # Run the actual CLI in an isolated root. No video is generated or decoded.
        scripts = self.root / "scripts"
        scripts.mkdir()
        for name in ("studio.py", "intent.py", "video_review.py", "stage_handoff.py",
                     "knowledge_song.py", "production_method.py", "representative_review.py"):
            shutil.copyfile(ROOT / "scripts" / name, scripts / name)
        project = self.version.parents[1]
        studio.save(project / "current.json", {"version": "v0001"})
        brief = {"id": "fixture", "title": "CLI resume fixture", "request": "test",
                 "width": 64, "height": 64, "fps": 24, "audio": {"mode": "silent"},
                 "inputs": [], "shots": [{"id": "one", "kind": "media", "frames": 24}]}
        candidate = project / "versions/v0002"
        candidate.mkdir()
        (candidate / "video.mp4").write_bytes(b"synthetic CLI candidate, not media")
        studio.save(candidate / "brief.json", brief)
        studio.save(candidate / "receipt.json", {
            "project": "fixture", "version": "v0002", "parent": "v0001",
            "delivery": {name: studio.digest(candidate / name) for name in ("video.mp4", "brief.json")}})
        studio.save(project / "pending.json", {"version": "v0002", "parent": "v0001", "brief": brief})
        command = [sys.executable, str(scripts / "studio.py"), "--mode", "production", "resume", "fixture"]
        # ffprobe is intentionally absent: review preparation must fail before committing.
        failed = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(failed.returncode, 0, failed.stdout)
        self.assertIn("ffprobe", failed.stderr)
        self.assertEqual(studio.load(project / "current.json"), {"version": "v0001"})
        self.assertTrue((project / "pending.json").is_file())
        before = {p.name: p.read_bytes() for p in candidate.iterdir()}
        packet, _ = reviewed_contract(studio, candidate)
        # Keep the synthetic packet, remove the synthetic decision: recovery is still pending review.
        (packet / "r0001.json").unlink()
        succeeded = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(succeeded.returncode, 0, succeeded.stderr)
        self.assertIn('"delivery_ready": false', succeeded.stdout)
        self.assertEqual(studio.load(project / "current.json"), {"version": "v0002"})
        self.assertFalse((project / "pending.json").exists())
        self.assertEqual(before, {p.name: p.read_bytes() for p in candidate.iterdir()})

    def test_partial_visual_audio_or_playback_and_unresolved_issue_block(self):
        base, review = reviewed_contract(studio, self.version)
        for layer in video_review.LAYERS:
            draft = copy.deepcopy(review)
            next(c for c in draft["checks"] if c["layer"] == layer)["status"] = "pending"
            studio.save(base / "draft.json", draft)
            self.assertEqual(video_review.save(studio, self.version, base / "draft.json")["status"], "blocked")
        draft = copy.deepcopy(review)
        draft["findings"] = [{"id": "clipping", "status": "open", "observation": "fixture clipping",
                              "evidence": {"frame0.png": studio.digest(base / "frame0.png")}}]
        studio.save(base / "draft.json", draft)
        video_review.save(studio, self.version, base / "draft.json")
        with self.assertRaisesRegex(ValueError, "未解决缺陷"):
            video_review.require(studio, self.version)
        studio.save(base / "draft.json", review)
        with self.assertRaisesRegex(ValueError, "遗漏历史缺陷"):
            video_review.save(studio, self.version, base / "draft.json")

    def test_stale_media_receipt_or_evidence_invalidates_review(self):
        for name in ("frame0.png", "fixture.txt"):
            base, _ = reviewed_contract(studio, self.version)
            (base / name).write_text("changed")
            with self.assertRaisesRegex(ValueError, "质量交付被阻止"):
                video_review.require(studio, self.version)
        reviewed_contract(studio, self.version)
        receipt = studio.load(self.version / "receipt.json")
        receipt["parent"] = "different binding"
        studio.save(self.version / "receipt.json", receipt)
        self.assertEqual(video_review.status(studio, self.version)["status"], "pending")

    def test_incomplete_sampling_and_fake_silent_audio_exemption_rejected(self):
        base, review = reviewed_contract(studio, self.version)
        review["checks"][0]["range"] = [0, .5]
        studio.save(base / "draft.json", review)
        with self.assertRaisesRegex(ValueError, "完整成片"):
            video_review.save(studio, self.version, base / "draft.json")
        base, review = reviewed_contract(studio, self.version)
        next(c for c in review["checks"] if c["layer"] == "listening")["status"] = "not_applicable"
        studio.save(base / "draft.json", review)
        with self.assertRaisesRegex(ValueError, "无音轨"):
            video_review.save(studio, self.version, base / "draft.json")
        review["frames"].pop()
        studio.save(base / "draft.json", review)
        with self.assertRaisesRegex(ValueError, "逐一覆盖"):
            video_review.save(studio, self.version, base / "draft.json")

    def test_real_export_cli_blocks_missing_review_before_copy(self):
        import shutil
        (self.root / "scripts").mkdir()
        for name in ("studio.py", "video_review.py"):
            shutil.copy2(ROOT / "scripts" / name, self.root / "scripts" / name)
        studio.save(self.version.parents[1] / "current.json", {"version": "v0001"})
        target = self.root / "delivery"
        # studio imports the intent profile declaration when constructing its parser.
        shutil.copy2(ROOT / "scripts/intent.py", self.root / "scripts/intent.py")
        result = subprocess.run([sys.executable, str(self.root / "scripts/studio.py"), "--mode", "delivery",
                                 "export", "fixture", "--version", "v0001", "--to", str(target)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("质量交付被阻止", result.stderr)
        self.assertFalse(target.exists())
        reviewed_contract(studio, self.version)
        result = subprocess.run([sys.executable, str(self.root / "scripts/studio.py"), "--mode", "delivery",
                                 "export", "fixture", "--version", "v0001", "--to", str(target)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target / "video.mp4").read_bytes(), (self.version / "video.mp4").read_bytes())
        self.assertTrue((target / "quality-review/frames.json").is_file())

    def test_real_extraction_is_full_resolution_pending_and_idempotent(self):
        source = self.root / "source.mp4"
        subprocess.run([str(ROOT / ".studio/bin/ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
                        "color=blue:s=64x64:r=24:d=1", "-c:v", "libx264", str(source)], check=True)
        (self.version / "video.mp4").write_bytes(source.read_bytes())
        studio.save(self.version / "receipt.json", {"project": "fixture", "version": "v0001",
                    "delivery": {"video.mp4": studio.digest(self.version / "video.mp4")}})
        result = subprocess.run([sys.executable, str(ROOT / "scripts/studio.py"), "--mode", "development",
                                 "--works-root", str(self.root / "works"), "review-prepare", "fixture",
                                 "--version", "v0001"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        prepared = json.loads(result.stdout)
        self.assertEqual(prepared["status"], "pending")
        self.assertIn("音频文件路径", prepared["audio_handoff"])
        packet = video_review.folder(studio, self.version)
        self.assertEqual(len(list((packet / "frames").glob("*.png"))), 2)
        frame = studio.probe(packet / "frames/000001.png")["streams"][0]
        self.assertEqual((frame["width"], frame["height"]), (64, 64))
        cross_check = packet / "cross-check.md"
        table = cross_check.read_text(encoding="utf-8")
        self.assertIn(studio.digest(self.version / "video.mp4"), table)
        self.assertIn(studio.digest(self.version / "receipt.json"), table)
        self.assertIn("待核对", table)
        self.assertIn(prepared["audio_handoff"], table)
        # Editorial notes stay editable; recovery must preserve them without invalidating the packet.
        cross_check.write_text(table + "\n助手观察：测试记录，不代表审阅通过。\n", encoding="utf-8")
        video_review.manifest(studio, self.version)
        before = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in packet.rglob("*") if p.is_file()}
        reused = video_review.prepare(studio, self.version)
        self.assertTrue(reused["reused"])
        self.assertEqual(reused["audio_handoff"], prepared["audio_handoff"])
        self.assertEqual(before, {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in before})
        self.assertEqual(video_review.status(studio, self.version)["status"], "pending")
        draft = studio.load(packet / "draft.json")
        content = next(check for check in draft["checks"] if check["layer"] == "content")
        content.update(status="issue", observation="夹具核对，仅验证证据绑定",
                       evidence={"cross-check.md": studio.digest(cross_check)})
        studio.save(packet / "draft.json", draft)
        self.assertEqual(video_review.save(studio, self.version, packet / "draft.json")["status"], "blocked")
        cross_check.write_text(table + "\n核对依据已变化\n", encoding="utf-8")
        self.assertIn("审查证据已变化", video_review.status(studio, self.version)["blockers"][0])


if __name__ == "__main__":
    unittest.main()
