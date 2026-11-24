"""Exercise the studio AVS bridge with native contract fixtures, never media."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AvsPlanTest(unittest.TestCase):
    def test_adopts_native_agent_script_and_refuses_fallback_or_repeated_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "scripts").mkdir()
            for name in ("avs.sh", "avs-plan.py", "avs-adopt.py", "avs-stage.py"):
                shutil.copyfile(ROOT / "scripts" / name, root / "scripts" / name)
            native = root / "runtime/avs"
            (native / "config").mkdir(parents=True)
            (native / "AGENTS.md").write_text("Isolated AVS contract fixture.\n")
            (native / "config/project.yaml").write_text("project:\n  episodes_root: episodes\n")
            (native / "src").symlink_to(ROOT / "runtime/avs/src", target_is_directory=True)
            (native / "schemas").symlink_to(ROOT / "runtime/avs/schemas", target_is_directory=True)
            (root / "runtime/avs-venv").symlink_to(ROOT / "runtime/avs-venv", target_is_directory=True)
            setup = """
import importlib.util, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('native_fixture', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ep, model = module._publishable_episode(Path(sys.argv[2]), script=module._agent_script())
script = json.loads((ep / 'work/content/script.json').read_text())
script['author_id'] = 'codex:gpt-6.1-sol'
(ep / 'work/content/script.json').write_text(json.dumps(script, ensure_ascii=False))
brief = {
    'episode_id': model.id, 'platform': 'xiaohongshu',
    'target_audience': '合同校验夹具', 'core_pain': '保留输入的创作决策',
    'angle': script['angle'], 'hook': script['segments'][0]['spoken_text'],
    'duration_seconds': sum(s['duration_seconds'] for s in script['segments']),
    'structure': ['fixture-opening', 'fixture-evidence'],
    'must_use_asset_ids': ['shot-a'], 'forbidden_content': ['fixture-only'],
    'product_visual_ratio': 0.5, 'hook_variants': [{'id': 'custom', 'text': 'fixture'}],
}
(ep / 'work/content/creative-brief.json').write_text(json.dumps(brief, ensure_ascii=False))
"""
            result = subprocess.run([ROOT / "runtime/avs-venv/bin/python", "-B", "-c", setup,
                                     ROOT / "runtime/avs/tests/test_agent_content_gate.py", native],
                                    env={**os.environ, "PYTHONPATH": str(native / "src")},
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            ep = native / "episodes/active/WF-AGENT"
            script = ep / "work/content/script.json"
            original = script.read_text()
            brief = ep / "work/content/creative-brief.json"
            original_brief = brief.read_bytes()

            def invoke(*args):
                return subprocess.run(["/bin/bash", root / "scripts/avs.sh", *args],
                                      capture_output=True, text=True, timeout=30)

            def snapshot():
                return {p.relative_to(ep).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in ep.rglob("*") if p.is_file()}

            before = snapshot()
            denied = invoke("plan", "WF-AGENT")
            self.assertEqual(denied.returncode, 2, denied.stderr)
            self.assertIn("需要显式 --mode production", denied.stderr)
            self.assertEqual(snapshot(), before)
            direct = subprocess.run([ROOT / "runtime/avs-venv/bin/python", "-B",
                                     root / "scripts/avs-plan.py", "WF-AGENT"],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(direct.returncode, 2)
            self.assertEqual(snapshot(), before)
            for problem in ("deterministic", "bad-evidence", "analysis-blocked"):
                data = json.loads(original)
                if problem == "deterministic":
                    data["authored_by"] = "deterministic"
                elif problem == "bad-evidence":
                    data["segments"][1]["asset_refs"][0]["asset_id"] = "absent"
                analysis = ep / "work/analysis/asset-intelligence.json"
                saved_analysis = analysis.read_text()
                if problem == "analysis-blocked":
                    intelligence = json.loads(saved_analysis)
                    intelligence.update(blocked=True, blocking_reason="fixture blocked")
                    analysis.write_text(json.dumps(intelligence))
                script.write_text(json.dumps(data, ensure_ascii=False))
                frozen = snapshot()
                failed = invoke("--mode", "production", "plan", "WF-AGENT")
                self.assertNotEqual(failed.returncode, 0, failed.stdout)
                self.assertEqual(snapshot(), frozen)
                analysis.write_text(saved_analysis)
            script.write_text(original)
            for problem in ("absent", "identity", "duration", "hook", "angle", "assets", "platform"):
                data = json.loads(original_brief)
                if problem == "absent":
                    brief.unlink()
                else:
                    if problem == "identity":
                        data["episode_id"] = "OTHER"
                    elif problem == "duration":
                        data["duration_seconds"] += 1
                    elif problem == "hook":
                        data["hook"] = "wrong opening"
                    elif problem == "angle":
                        data["angle"] = "wrong angle"
                    elif problem == "assets":
                        data["must_use_asset_ids"] = []
                    brief.write_text(json.dumps(data, ensure_ascii=False))
                frozen = snapshot()
                args = ("--platform", "douyin") if problem == "platform" else ()
                failed = invoke("--mode", "production", "plan", "WF-AGENT", *args)
                self.assertNotEqual(failed.returncode, 0, failed.stdout)
                self.assertEqual(snapshot(), frozen)
                brief.write_bytes(original_brief)
            valid = invoke("--mode", "production", "plan", "WF-AGENT")
            self.assertEqual(valid.returncode, 0, valid.stderr)
            report = json.loads(valid.stdout)
            self.assertEqual(len(report["artifacts"]), 6)
            self.assertFalse(report["render_started"])
            self.assertFalse(report["model_request_sent"])
            saved = json.loads(script.read_text())
            self.assertEqual(saved["segments"], json.loads(original)["segments"])
            self.assertEqual(saved["reference_pattern_ids"], json.loads(original)["reference_pattern_ids"])
            self.assertEqual(brief.read_bytes(), original_brief)
            self.assertEqual(json.loads((ep / "work/content/hook-selection.json").read_text())["hook"],
                             json.loads(original_brief)["hook"])
            model = json.loads((ep / "episode.json").read_text())
            self.assertEqual(model["status"], "CONTENT_READY")
            self.assertIn("plan", model["completed_stages"])
            self.assertFalse(list(ep.rglob("*.mp4")))
            self.assertFalse((ep / "renders").exists())
            # A real read-only stage check reaches the pinned native workflow.
            # This fixture has no voice; it must stop before TTS or any media tool.
            before_check = snapshot()
            check = invoke("stage-check", "preview", "WF-AGENT")
            self.assertNotEqual(check.returncode, 0)
            self.assertIn("禁止自动 TTS", check.stderr)
            self.assertEqual(snapshot(), before_check)
            planner_bytes = script.read_bytes()
            data = json.loads(planner_bytes); data["segments"][0]["spoken_text"] += " changed"
            script.write_text(json.dumps(data, ensure_ascii=False))
            check = invoke("stage-check", "preview", "WF-AGENT")
            self.assertNotEqual(check.returncode, 0)
            self.assertIn("规划合同绑定已过期", check.stderr)
            script.write_bytes(planner_bytes)
            # Restore the exact planner bytes for the following repeated-stage check.
            receipt = json.loads((ep / "work/content/codex-plan.json").read_text())
            self.assertEqual(hashlib.sha256(script.read_bytes()).hexdigest(), receipt["bindings"]["work/content/script.json"])
            after = snapshot()
            repeated = invoke("--mode", "production", "plan", "WF-AGENT")
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(snapshot(), after)


if __name__ == "__main__":
    unittest.main()
