"""Exercise the real supplied-audio preparation path with encoded audio."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import studio


class LockedAudioTest(unittest.TestCase):
    def test_locked_aac_keeps_packets_and_rejects_timing_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "approved.m4a"
            studio.ff("-f", "lavfi", "-i", "sine=frequency=523:duration=1",
                      "-ar", 48000, "-c:a", "aac", source)
            brief = {"fps": 25, "audio": {"mode": "supplied", "asset": "music", "preserveEncoded": True},
                     "inputs": [{"id": "music", "kind": "audio", "path": source.name,
                                 "sha256": studio.digest(source)}],
                     "shots": [{"id": "one", "frames": 25, "cues": []}]}
            scene = root / "scene.js"
            scene.write_text("// Audio-path fixture; not rendered.")
            brief["inputs"].append({"id": "visual", "kind": "scene", "path": scene.name,
                                    "sha256": studio.digest(scene)})
            brief["shots"][0].update(kind="code", sceneAsset="visual")
            studio.check_inputs(brief, root)
            out = root / "candidate"
            out.mkdir()
            studio.prepare_sound(brief, root, out)
            def packets(path):
                return subprocess.check_output([studio.BIN / "ffmpeg", "-v", "error", "-i", path,
                                                "-map", "0:a:0", "-c:a", "copy", "-f", "adts", "-"])
            self.assertEqual(hashlib.sha256(packets(source)).hexdigest(),
                             hashlib.sha256(packets(out / "audio.m4a")).hexdigest())
            brief["shots"][0]["frames"] = 50
            with self.assertRaisesRegex(ValueError, "等长"):
                studio.check_inputs(brief, root)
            with self.assertRaisesRegex(ValueError, "等长"):
                studio.prepare_sound(brief, root, out)


if __name__ == "__main__":
    unittest.main()
