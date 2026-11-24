"""Catalogue families must reach their real production preparer."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess
import hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from video_templates import prepare, selection_receipt, sha
from stage_handoff import fingerprint


class NativeTemplateDispatchTest(unittest.TestCase):
    def test_self_media_prepare_carries_strategy_to_real_plan_entry(self):
        # The historical boxcutter example is now explicitly unsupported. Use an
        # existing native engineering fixture, without claiming creative quality.
        source = ROOT / "productions/flower-field-story-1114/input.json"
        data = json.loads(source.read_text())
        data["project"] = str(source.parent / data["project"])
        data["purpose"] = "self-media"
        project = Path(data['project']) / 'project.json'
        data['script'] = json.loads(project.read_text())['content_promise']
        data['topic'] = '花海，花园随风开花'
        data['production_stage'] = 'representative'
        data['routing'] = selection_receipt(data['topic'], data['script'], '16:9',
                                            data['template'], 'engineering_validation')
        data['requirements'] = [{'id': 'fixture', 'text': 'synthetic data binding only'}]
        data['adaptation_inputs'] = [{'id': 'original', 'kind': 'data', 'path': str(project), 'sha256': sha(project)}]
        ref = {'pointer': '/content_promise', 'sha256': fingerprint(data['script'])}
        data['content_adaptation'] = {'schema': 1, 'script_sha256': hashlib.sha256(data['script'].encode()).hexdigest(),
            'units': [{'id': 'fixture', 'shot': 'native-style', 'frames': [0, 30], 'requirements': ['fixture'],
                'source': {**ref, 'asset': 'original'},
                'target': {**ref, 'file': 'source-pack.zip', 'member': 'project.json'},
                **{k: 'synthetic fixture only' for k in ('goal','before','action','after','reaction','camera','preserve','changes')},
                'capability': 'unverified'}]}
        snapshot = json.loads((ROOT / "productions/boxcutter-1114/content-plan.json").read_text())["content_strategy"]
        data["content_strategy"] = snapshot
        with tempfile.TemporaryDirectory() as directory:
            request, output = Path(directory)/"request.json", Path(directory)/"prepared"
            request.write_text(json.dumps(data, ensure_ascii=False))
            run = subprocess.run([sys.executable, ROOT/"scripts/studio.py", "--mode", "development",
                                  "templates", "prepare", request, "--to", output], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            brief = json.loads((output/"brief.json").read_text())
            self.assertEqual(brief.get("purpose"), "self-media")
            self.assertEqual(brief.get("content_strategy"), snapshot)
            plan = subprocess.run([sys.executable, ROOT/"scripts/studio.py", "plan", output/"brief.json"],
                                  capture_output=True, text=True)
            self.assertEqual(plan.returncode, 0, plan.stderr)
            self.assertEqual(json.loads(plan.stdout)["editorial"]["status"], "ready")

    def test_self_media_prepare_rejects_missing_strategy_before_writing(self):
        source = ROOT / "productions/boxcutter-1114/rig-trial-02/story-input.json"
        data = json.loads(source.read_text())
        data["project"] = str(source.parent / data["project"])
        data["purpose"] = "self-media"
        with tempfile.TemporaryDirectory() as directory:
            request, output = Path(directory)/"request.json", Path(directory)/"prepared"
            request.write_text(json.dumps(data, ensure_ascii=False))
            run = subprocess.run([sys.executable, ROOT/"scripts/studio.py", "--mode", "development",
                                  "templates", "prepare", request, "--to", output], capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertFalse(output.exists())

    def test_registered_studio_style_reaches_native_archive_preparer(self):
        source = ROOT / "productions/flower-field-story-1114/input.json"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "prepared"
            prepare(source, output)
            brief = json.loads((output / "brief.json").read_text())
            self.assertEqual(brief["template"]["id"], "studio-flower-field")
            self.assertEqual(brief["shots"][0]["engine"], "opuscar")
            self.assertTrue((output / "source-pack.zip").is_file())
            self.assertEqual(brief["audio"]["mode"], "supplied")


if __name__ == "__main__":
    unittest.main()
