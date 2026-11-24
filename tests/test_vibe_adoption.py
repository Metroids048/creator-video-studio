"""Adopt an existing Vibe film into an isolated review chain without rendering or touching it."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import studio

FFMPEG = ROOT / ".studio" / "bin" / "ffmpeg"
DEMO = ROOT / "works/vibe-falling-around-1115/demo-reference-20261116"
PARENT = "versions/rejected-100s-visual-zero-6b29dd01-20261116"
REAL = {"video": f"{PARENT}/out/还没落地-完整修复版.mp4",
        "audio": "assets/还没落地-原曲小节剪辑.wav",
        "subtitles": f"{PARENT}/共同下落-原歌词.srt"}
REAL_SHA = {"video": "6b29dd0129abff9a8ad794aae56f7f2cdeb14f1410a44894ed18fc91c518aa4e",
            "audio": "e702a9e31937eebf841ddfe45001ebaddcc9aa4f98be823f21c5873be9db2c35",
            "subtitles": "9814c4e94a65f25c46f66d2c9e002769e0fc45ae1aa4786b2beebae4a50cc028"}


def run(*args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "studio.py"), *map(str, args)],
                          cwd=ROOT, capture_output=True, text=True, timeout=600)


def snapshot(root, names):
    return {name: studio.digest(root / name) for name in names}


@unittest.skipUnless(FFMPEG.is_file(), "需要工作室 ffmpeg")
class VibeAdoptionTest(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="vibe-adopt-"))
        self.addCleanup(shutil.rmtree, self.temp, True)
        self.registry = self.temp / "registry"

    def film(self, *, audio_stream=True, cue_end="00:00:01,500"):
        root = self.temp / "src" / "film-a"
        (root / "out").mkdir(parents=True)
        inputs = ["-f", "lavfi", "-i", "testsrc=size=64x48:rate=25:duration=2"]
        if audio_stream:
            inputs += ["-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-shortest"]
        subprocess.run([FFMPEG, "-v", "error", *inputs, "-pix_fmt", "yuv420p", root / "out/final.mp4"], check=True)
        subprocess.run([FFMPEG, "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=2",
                        root / "audio.wav"], check=True)
        (root / "subs.srt").write_text(f"1\n00:00:00,500 --> {cue_end}\n人和球\n", encoding="utf-8")
        return root

    def adopt(self, root, request="字幕必须对应实际演唱", registry=None, **names):
        names = {"video": "out/final.mp4", "audio": "audio.wav", "subtitles": "subs.srt", **names}
        return run("--mode", "recovery", "--works-root", registry or self.registry, "adopt-vibe", "song-1115", root,
                   "--video", names["video"], "--audio", names["audio"], "--subtitles", names["subtitles"],
                   "--version", "v0001", "--request", request)

    def test_registers_probed_media_and_leaves_source_untouched(self):
        root = self.film()
        files = ("out/final.mp4", "audio.wav", "subs.srt")
        before = snapshot(root, files)
        adopted = self.adopt(root)
        self.assertEqual(adopted.returncode, 0, adopted.stderr)
        self.assertEqual(before, snapshot(root, files))
        version = self.registry / "vibe-song-1115/versions/v0001"
        brief = studio.load(version / "brief.json")
        self.assertEqual((brief["width"], brief["height"], brief["fps"]), (64, 48, 25.0))
        self.assertAlmostEqual(brief["duration_seconds"], 2.0, delta=0.1)
        self.assertEqual(brief["subtitles"]["cues"], [{"start": 0.5, "end": 1.5, "text": "人和球"}])
        self.assertEqual(brief["subtitles"]["sung_match"], "unverified")
        self.assertEqual(brief["audio"]["sha256"], before["audio.wav"])
        self.assertEqual(studio.digest(version / "video.mp4"), before["out/final.mp4"])
        status = run("--works-root", self.registry, "status", "vibe-song-1115")
        self.assertEqual(status.returncode, 0, status.stderr)
        report = json.loads(status.stdout)
        self.assertEqual((report["current"], report["delivery_ready"]), ("v0001", False))

    def test_requires_isolated_registry(self):
        root = self.film()
        missing = run("--mode", "recovery", "adopt-vibe", "song-1115", root, "--video", "out/final.mp4",
                      "--audio", "audio.wav", "--subtitles", "subs.srt", "--version", "v0001", "--request", "x")
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("--works-root", missing.stderr)
        live = self.adopt(root, registry=ROOT / "works")
        self.assertNotEqual(live.returncode, 0)
        self.assertIn("隔离", live.stderr)
        inside = self.adopt(root, registry=self.temp / "src")
        self.assertNotEqual(inside.returncode, 0)
        self.assertIn("登记根内", inside.stderr)

    def test_registry_anywhere_under_real_works_is_refused_before_creation(self):
        root = self.film()
        registry = ROOT / "works" / f".adopt-guard-{os.getpid()}" / "registry"
        self.addCleanup(shutil.rmtree, registry.parent, True)
        self.assertFalse(registry.parent.exists())
        refused = self.adopt(root, registry=registry)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("隔离", refused.stderr)
        self.assertFalse(registry.parent.exists())

    def test_tampered_locked_audio_fails_every_entry(self):
        root = self.film()
        self.assertEqual(self.adopt(root).returncode, 0)
        audio = self.registry / "vibe-song-1115/versions/v0001/inputs/approved-audio"
        with audio.open("ab") as handle:
            handle.write(b"tamper")
        status = run("--works-root", self.registry, "status", "vibe-song-1115")
        self.assertNotEqual(status.returncode, 0, status.stdout)
        self.assertIn("锁定音轨", status.stderr)
        prepared = run("--mode", "development", "--works-root", self.registry,
                       "review-prepare", "vibe-song-1115", "--version", "v0001")
        self.assertNotEqual(prepared.returncode, 0)
        self.assertIn("锁定音轨", prepared.stdout + prepared.stderr)
        exported = run("--mode", "delivery", "--works-root", self.registry,
                       "export", "vibe-song-1115", "--to", self.temp / "out")
        self.assertNotEqual(exported.returncode, 0)
        self.assertFalse((self.temp / "out").exists())
        again = self.adopt(root)
        self.assertNotEqual(again.returncode, 0)
        self.assertIn("锁定音轨", again.stderr)

    def test_review_prepare_export_block_and_rebinding(self):
        root = self.film()
        self.assertEqual(self.adopt(root).returncode, 0)
        prepared = run("--mode", "development", "--works-root", self.registry,
                       "review-prepare", "vibe-song-1115", "--version", "v0001")
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertEqual(json.loads(prepared.stdout)["status"], "pending")
        exported = run("--mode", "delivery", "--works-root", self.registry,
                       "export", "vibe-song-1115", "--to", self.temp / "out")
        self.assertNotEqual(exported.returncode, 0)
        self.assertIn("质量交付被阻止", exported.stderr)
        self.assertFalse((self.temp / "out").exists())
        again = self.adopt(root)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertTrue(json.loads(again.stdout)["reused"])
        self.assertNotEqual(self.adopt(root, "另一条要求").returncode, 0)
        (root / "subs.srt").write_text("1\n00:00:00,600 --> 00:00:01,500\n人和球\n", encoding="utf-8")
        changed = self.adopt(root)
        self.assertNotEqual(changed.returncode, 0)
        self.assertIn("已绑定", changed.stderr)

    def test_bad_inputs_fail_before_any_version(self):
        for kwargs, message in (({"audio_stream": False}, "音轨"), ({"cue_end": "00:00:09,000"}, "超出成片时长")):
            with self.subTest(message=message):
                shutil.rmtree(self.temp / "src", True)
                shutil.rmtree(self.registry, True)
                failed = self.adopt(self.film(**kwargs))
                self.assertNotEqual(failed.returncode, 0)
                self.assertIn(message, failed.stderr)
                self.assertFalse((self.registry / "vibe-song-1115/versions/v0001").exists())


@unittest.skipUnless(all((DEMO / p).is_file() for p in REAL.values()), "需要《还没落地》父版原件")
class RealParentAdoptionTest(unittest.TestCase):
    """Read-only check against the rejected parent; it proves binding, not picture quality."""

    def test_real_parent_registers_read_only_and_stays_blocked(self):
        temp = Path(tempfile.mkdtemp(prefix="vibe-adopt-real-"))
        self.addCleanup(shutil.rmtree, temp, True)
        registry = temp / "registry"
        before = {key: studio.digest(DEMO / path) for key, path in REAL.items()}
        self.assertEqual(before, REAL_SHA)
        args = ("--mode", "recovery", "--works-root", registry, "adopt-vibe", "falling-around-1115", DEMO,
                "--video", REAL["video"], "--audio", REAL["audio"], "--subtitles", REAL["subtitles"],
                "--version", "v0001", "--request", os.environ.get("ADOPT_REQUEST", "字幕必须对应实际演唱；画面逐句解释"))
        adopted = run(*args)
        self.assertEqual(adopted.returncode, 0, adopted.stderr)
        report = json.loads(adopted.stdout)
        self.assertEqual((report["sha256"], report["subtitle_cues"]), (REAL_SHA, 38))
        brief = studio.load(registry / "vibe-falling-around-1115/versions/v0001/brief.json")
        self.assertEqual((brief["width"], brief["height"], brief["fps"], brief["frames"]), (1920, 1080, 25.0, 2500))
        self.assertEqual(brief["subtitles"]["cues"][-1], {"start": 97.34, "end": 98.66, "text": "还没落地"})
        prepared = run("--mode", "development", "--works-root", registry,
                       "review-prepare", "vibe-falling-around-1115", "--version", "v0001")
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        exported = run("--mode", "delivery", "--works-root", registry,
                       "export", "vibe-falling-around-1115", "--to", temp / "out")
        self.assertNotEqual(exported.returncode, 0)
        self.assertIn("质量交付被阻止", exported.stderr)
        self.assertTrue(json.loads(run(*args).stdout)["reused"])
        self.assertEqual(before, {key: studio.digest(DEMO / path) for key, path in REAL.items()})


if __name__ == "__main__":
    unittest.main()
