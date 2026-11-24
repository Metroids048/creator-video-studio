"""Explicit platform-BGM masters keep the parent's complete picture contract."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import studio


class AudioRemovalTest(unittest.TestCase):
    def test_silent_revision_preserves_picture_and_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            version = Path(tmp) / "versions/v0001"
            version.mkdir(parents=True)
            brief = {"route": "code", "audio": {"mode": "supplied", "asset": "music"},
                     "inputs": [{"id": "music", "kind": "audio", "path": "music.wav"}],
                     "shots": [{"id": "garden", "frames": 840, "sceneAsset": "scene"}]}
            parent = version / "brief.json"
            parent.write_text(json.dumps(brief))
            change = Path(tmp) / "change.json"
            payload = {"base": "v0001", "reason": "Platform selects BGM later", "audio": {"mode": "silent"}}
            change.write_text(json.dumps(payload))
            with patch.object(studio, "validate"), patch.object(studio, "check_inputs"):
                result = studio.audio_brief(version, change)
            self.assertEqual(result["audio"], {"mode": "silent"})
            self.assertEqual(result["shots"], brief["shots"])
            self.assertEqual(result["inputs"], brief["inputs"])
            self.assertEqual(json.loads(parent.read_text()), brief)
            for update in ({"base": "v0000"}, {"inputs": [{"id": "extra"}]}, {"eventTimeline": {}}):
                change.write_text(json.dumps({**payload, **update}))
                with self.assertRaises(ValueError):
                    studio.audio_brief(version, change)
            changed = copy.deepcopy(brief)
            changed["eventTimeline"] = {"story": "material-sound-required"}
            parent.write_text(json.dumps(changed))
            change.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                studio.audio_brief(version, change)


if __name__ == "__main__":
    unittest.main()
