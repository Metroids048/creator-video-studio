"""Exercise native contract writeback in isolated fixtures, without media tools."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AVSAdoptionTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "scripts").mkdir()
        for name in ("avs.sh", "avs-adopt.py", "avs-stage.py"):
            shutil.copyfile(ROOT / "scripts" / name, self.root / "scripts" / name)
        native = self.root / "runtime/avs"
        (native / "config").mkdir(parents=True)
        (native / "AGENTS.md").write_text("Contract fixtures only.\n")
        (native / "config/project.yaml").write_text("project:\n  episodes_root: episodes\n")
        for name in ("src", "schemas"):
            (native / name).symlink_to(ROOT / "runtime/avs" / name, target_is_directory=True)
        (self.root / "runtime/avs-venv").symlink_to(ROOT / "runtime/avs-venv", target_is_directory=True)
        self.native = native
        self.ep = native / "episodes/active/ADOPT-FIXTURE"
        (self.ep / "input").mkdir(parents=True)
        (self.ep / "work").mkdir()
        self.write("input/screenshot.fixture", "Not an image; native binding fixture only.")
        manifest = {"episode_id": "ADOPT-FIXTURE", "generated_at": "2026-11-12T00:00:00Z", "assets": [{
            "asset_id": "screen", "source_path": "input/screenshot.fixture", "working_path": "input/screenshot.fixture",
            "source_type": "screenshot", "must_use": True, "sha256": self.sha("input/screenshot.fixture"),
            "audio_role": None, "status": "ok"}]}
        self.write("work/input-manifest.json", manifest)
        self.model("analyze")

    def write(self, name, value):
        path = self.ep / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value))

    def sha(self, name):
        return hashlib.sha256((self.ep / name).read_bytes()).hexdigest()

    def snapshot(self):
        return {p.relative_to(self.ep).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.ep.rglob("*") if p.is_file()}

    def model(self, stage):
        code = """
import sys
from pathlib import Path
from avs.models.episode import EpisodeModel
m=EpisodeModel.create('ADOPT-FIXTURE')
m.transition('INGESTED');m.complete_stage('ingest')
if sys.argv[2] == 'visual-review':
 m.complete_stage('analyze');m.complete_stage('plan');m.complete_stage('preview')
 m.transition('CONTENT_READY');m.transition('ASSETS_READY');m.transition('TIMELINE_READY')
m.save(Path(sys.argv[1])/'episode.json')
"""
        subprocess.run([ROOT / "runtime/avs-venv/bin/python", "-B", "-c", code, self.ep, stage],
                       env={**os.environ, "PYTHONPATH": str(self.native / "src")}, check=True)

    def invoke(self, operation, payload, mode="production"):
        path = self.root / "candidate.json"
        path.write_text(json.dumps(payload))
        return subprocess.run(["/bin/bash", self.root / "scripts/avs.sh", "--mode", mode,
                               operation, "ADOPT-FIXTURE", path], capture_output=True, text=True, timeout=15)

    def analysis(self):
        return {"episode_id": "ADOPT-FIXTURE", "reviewed_by": "codex:gpt-6.1-sol",
                "bindings": {name: self.sha(name) for name in ("work/input-manifest.json", "input/screenshot.fixture")},
                "observations": [{"asset_id": "screen", "method": "actual_view", "observation": "Structural test receipt, no visual acceptance."}],
                "contracts": {
                    "asset-intelligence": {"episode_id": "ADOPT-FIXTURE", "provider": "codex:gpt-6.1-sol", "assets": [{
                        "asset_id": "screen", "summary": "Contract fixture", "product_area": "Fixture", "visible_facts": ["Fixture fact"],
                        "regions": [{"region_id": "full-frame", "box": [0, 0, 1, 1], "meaning": "Fixture", "priority": 0.5}], "recommended_uses": []}]},
                    "recording-analysis": {"episode_id": "ADOPT-FIXTURE", "recordings": []},
                    "document-analysis": {"episode_id": "ADOPT-FIXTURE", "blocked": False, "assets": []},
                    "transcription": {"episode_id": "ADOPT-FIXTURE", "blocked": False, "transcripts": []}}}

    def test_analysis_rejects_stale_missing_api_and_incomplete_observations_then_commits_native_stage(self):
        original = self.snapshot()
        valid = self.analysis()
        denied = self.invoke("adopt-analysis", valid, "development")
        self.assertEqual(denied.returncode, 2, denied.stderr)
        for problem in ("stale", "provider", "missing", "observation", "roi"):
            candidate = json.loads(json.dumps(valid))
            if problem == "stale":
                candidate["bindings"]["input/screenshot.fixture"] = "0" * 64
            elif problem == "provider":
                candidate["contracts"]["asset-intelligence"]["provider"] = "external-api"
            elif problem == "missing":
                candidate["contracts"]["asset-intelligence"]["assets"] = []
            elif problem == "observation":
                candidate["observations"] = []
            else:
                candidate["contracts"]["asset-intelligence"]["assets"][0]["regions"][0]["box"] = [0, 0, 2, 1]
            result = self.invoke("adopt-analysis", candidate)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertEqual(self.snapshot(), original)
        result = self.invoke("adopt-analysis", valid)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["render_started"])
        self.assertFalse(report["model_request_sent"])
        self.assertFalse(report["accepted"])
        self.assertIn("analyze", json.loads((self.ep / "episode.json").read_text())["completed_stages"])
        after = self.snapshot()
        self.assertNotEqual(self.invoke("adopt-analysis", valid).returncode, 0)
        self.assertEqual(self.snapshot(), after)

    def test_visual_writeback_binds_same_preview_and_rejects_stale_approval(self):
        self.model("visual-review")
        names = ["work/content/script.json", "work/content/evidence-map.json", "work/content/shot-plan.json", "work/timeline.json"]
        for name in names:
            self.write(name, {})
        # This is deliberately not decodable: the test covers contracts, never viewing or rendering.
        video = "renders/preview-with-captions.mp4"
        self.write(video, "Not media; isolated hash-binding fixture only.")
        candidate = {"episode_id": "ADOPT-FIXTURE", "reviewed_by": "codex:gpt-6.1-sol",
                     "bindings": {name: self.sha(name) for name in ["work/input-manifest.json", *names, video]},
                     "observations": [{"method": "actual_view", "observation": "Contract fixture; not a viewing result."}],
                     "contracts": {"visual-review": {"passed": True, "blocked": False, "failures": []}}}
        original = self.snapshot()
        self.write(video, "Changed fixture bytes")
        changed = self.snapshot()
        self.assertNotEqual(self.invoke("adopt-visual-review", candidate).returncode, 0)
        self.assertEqual(self.snapshot(), changed)

        candidate["bindings"][video] = self.sha(video)
        result = self.invoke("adopt-visual-review", candidate)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((self.ep / "work/qa/visual-review.json").read_text())
        self.assertEqual(report["video_sha256"], self.sha(video))
        receipt = json.loads((self.ep / "work/qa/codex-visual-review.json").read_text())
        self.assertFalse(receipt["accepted"])
        self.assertEqual(receipt["validated_here"], "native_contract_and_provenance_only")
        current = self.snapshot()
        def check_stage(stage):
            return subprocess.run(["/bin/bash", self.root / "scripts/avs.sh", "stage-check", stage, "ADOPT-FIXTURE"],
                                  capture_output=True, text=True, timeout=15)
        check = check_stage("final-render")
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertFalse(json.loads(check.stdout)["render_started"])
        self.assertEqual(self.snapshot(), current)
        self.assertNotEqual(check_stage("preview").returncode, 0)
        self.write("renders/preview-with-motion.mp4", "New preferred preview fixture")
        self.assertNotEqual(check_stage("final-render").returncode, 0)
        (self.ep / "renders/preview-with-motion.mp4").unlink()
        self.write("work/content/shot-plan.json", {"changed": True})
        changed = self.snapshot()
        check = check_stage("final-render")
        self.assertNotEqual(check.returncode, 0)
        self.assertIn("绑定已过期", check.stderr)
        self.assertEqual(self.snapshot(), changed)

    def test_creative_and_human_writeback_require_bound_observations_and_explicit_confirmation(self):
        self.model("visual-review")
        video = "renders/final-with-captions.mp4"
        for name in ("work/content/script.json", "work/content/evidence-map.json",
                     "work/content/shot-plan.json", "work/timeline.json"):
            self.write(name, {})
        self.write(video, "Not media; acceptance contract fixture only.")
        self.write("delivery/qa-report.json", {"passed": True, "technical_passed": True,
                                               "video_sha256": self.sha(video)})
        # Build native metric/schema fixtures; no decoding, scores or human acceptance occurred.
        code = """
import json,sys
from pathlib import Path
from avs.models.episode import EpisodeModel
from avs.qa.creative_review import evaluate_gate
ep=Path(sys.argv[1]);m=EpisodeModel.load(ep/'episode.json')
m.transition('ROUGH_CUT_READY');m.transition('QA_PASSED')
m.complete_stage('visual-review');m.complete_stage('final-render');m.complete_stage('technical-qa')
m.save(ep/'episode.json')
metrics=dict(duration_seconds=2,shot_count=1,shot_duration_distinct_values=1,
shot_duration_min=2,shot_duration_max=2,longest_static_run_seconds=0,static_frame_ratio=0,
hook_static_seconds=0,visual_change_rate=1,max_black_border_ratio=0,
has_bgm=False,has_sfx=False,voice_providers=['fixture'],evidence_scale_factors=[])
review=dict(episode_id=m.id,video_path=sys.argv[2],video_sha256=sys.argv[3],
reviewed_at='2026-11-12T00:00:00Z',reviewer_kind='pending',reviewed_artifacts=[],metrics=metrics,
scores=None,findings=[],gate=evaluate_gate(metrics,None,[]),
review_package=dict(contact_sheets=[],sample_plan=[],frame_count=0))
(ep/'work/qa').mkdir(exist_ok=True)
(ep/'work/qa/creative-review.json').write_text(json.dumps(review))
"""
        subprocess.run([ROOT / "runtime/avs-venv/bin/python", "-B", "-c", code, self.ep, video, self.sha(video)],
                       env={**os.environ, "PYTHONPATH": str(self.native / "src")}, check=True)
        names = ["work/input-manifest.json", "work/content/script.json", "work/content/evidence-map.json",
                 "work/content/shot-plan.json", "work/timeline.json", video,
                 "delivery/qa-report.json", "work/qa/creative-review.json"]
        dimensions = ("hook", "narrative", "pacing", "visual_design", "human_tone", "audio", "caption",
                      "evidence_trust", "platform_fit", "memorability")
        candidate = {"episode_id": "ADOPT-FIXTURE", "reviewed_by": "codex:gpt-6.1-sol",
                     "bindings": {name: self.sha(name) for name in names},
                     "observations": [{"method": method, "observation": "Contract fixture, not actual media review."}
                                      for method in ("actual_playback", "actual_listening")],
                     "contracts": {"creative-score": {"scores": dict.fromkeys(dimensions, 9),
                         "reviewed_artifacts": [video], "findings": [], "repair_round": 0}}}
        original = self.snapshot()
        missing_listening = json.loads(json.dumps(candidate))
        missing_listening["observations"].pop()
        result = self.invoke("adopt-creative-review", missing_listening)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("听审", result.stderr)
        self.assertEqual(self.snapshot(), original)
        low = json.loads(json.dumps(candidate))
        low["contracts"]["creative-score"]["scores"] = dict.fromkeys(dimensions, 1)
        result = self.invoke("adopt-creative-review", low)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.ep / "episode.json").read_text())["blocked_stage"], "creative-gate")
        failed_review = (self.ep / "work/qa/creative-review.json").read_bytes()
        candidate["bindings"]["work/qa/creative-review.json"] = self.sha("work/qa/creative-review.json")
        blocked = self.snapshot()
        self.assertNotEqual(self.invoke("adopt-creative-review", candidate).returncode, 0)
        self.assertEqual(self.snapshot(), blocked)
        candidate["contracts"]["creative-score"]["repair_round"] = 1
        result = self.invoke("adopt-creative-review", candidate)
        self.assertEqual(result.returncode, 0, result.stderr)
        review = json.loads((self.ep / "work/qa/creative-review.json").read_text())
        self.assertTrue(review["gate"]["creative_passed"])
        self.assertEqual(review["metrics"]["voice_providers"], ["fixture"])
        archived = list((self.ep / "work/codex-history/creative-gate").glob("*/work/qa/creative-review.json"))
        self.assertEqual(len(archived), 1)
        self.assertEqual(json.loads(archived[0].read_text()), json.loads(failed_review))
        checklist = dict.fromkeys(("hook_clear_within_3s", "captions_readable", "composition_acceptable",
                                   "audio_acceptable", "no_placeholders", "facts_and_rights_checked"), True)
        approval = {"episode_id": "ADOPT-FIXTURE", "reviewed_by": "codex:gpt-6.1-sol",
                    "bindings": {name: self.sha(name) for name in names},
                    "contracts": {"visual-approval": {"checklist": checklist}}}
        original = self.snapshot()
        self.assertNotEqual(self.invoke("adopt-approval", approval).returncode, 0)
        self.assertEqual(self.snapshot(), original)
        approval["human_evidence"] = {"source": "user_message", "reference": "isolated-test-fixture",
                                      "text": "Fixture only; no user acceptance happened.", "reviewer": "test-fixture"}
        approval["contracts"]["visual-approval"]["checklist"]["audio_acceptable"] = False
        self.assertNotEqual(self.invoke("adopt-approval", approval).returncode, 0)
        self.assertEqual(self.snapshot(), original)
        approval["contracts"]["visual-approval"]["checklist"]["audio_acceptable"] = True
        result = self.invoke("adopt-approval", approval)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["accepted"])
        receipt = json.loads((self.ep / "work/qa/codex-human-approval.json").read_text())
        self.assertFalse(receipt["accepted"])
        self.assertFalse(receipt["model_session_verified"])
        self.assertIn("artifact_fingerprint", json.loads((self.ep / "delivery/visual-approval.json").read_text()))



if __name__ == "__main__":
    unittest.main()
