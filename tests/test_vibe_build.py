"""Native build must consume the requested audio and propagate failed stages."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeBuildTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="native-build-"))
        self.addCleanup(shutil.rmtree, self.root)
        self.kit = self.root / "kit"
        (self.kit / "bin").mkdir(parents=True)
        (self.kit / "qa").mkdir()
        shutil.copy(ROOT / "runtime/vibe/bin/film.sh", self.kit / "bin/film.sh")
        (self.kit / "bin/env.sh").write_text('vf_need() { :; }\n')
        self.project = self.root / "project"
        self.project.mkdir()
        self.log = self.root / "calls"
        self.node = self.root / "node"
        self.node.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n'
                             '[[ "$*" != *"--$FAIL_STAGE"* ]] || exit 7\nexit 0\n')
        self.node.chmod(0o755)
        (self.kit / "qa/qa_film.py").write_text('import os,sys\nsys.exit(9 if os.getenv("FAIL_STAGE")=="qa" else 0)\n')

    def build(self, stage="never", *flags):
        return subprocess.run(["bash", self.kit / "bin/film.sh", "build", "v2",
                               "--audio=assets/认可 音轨.wav", *flags], text=True, capture_output=True,
                              env=dict(os.environ, FILM_ROOT=str(self.project), VF_NODE=str(self.node),
                                       VF_PY=shutil.which("python3"), CALL_LOG=str(self.log), FAIL_STAGE=stage))

    def test_explicit_audio_skips_score_and_reaches_encode(self):
        (self.project / "score.py").write_text("raise SystemExit('must not regenerate approved audio')")
        result = self.build("never", "--fps=25", "--crf=19")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text().splitlines()
        encode = next(c for c in calls if "--encode" in c)
        self.assertIn("--audio=assets/认可 音轨.wav", encode)
        self.assertIn("--fps=25", encode)
        self.assertIn("--crf=19", encode)
        self.assertNotIn("--fresh", "\n".join(calls))
        self.assertNotIn("--events", "\n".join(calls))

    def test_failed_subtitles_stop_before_frames(self):
        result = self.build("subs")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("--frames", self.log.read_text())

    def test_failed_qa_never_reports_done(self):
        result = self.build("qa")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("BUILD_DONE", result.stdout)
        self.assertNotIn("BUILD_CANDIDATE", result.stdout)

    def test_existing_parent_is_not_overwritten(self):
        (self.project / "out").mkdir()
        target = self.project / "out/project-v2.mp4"
        target.write_bytes(b"failed parent")
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())
        self.assertEqual(target.read_bytes(), b"failed parent")


class FrozenAudioCheckTest(unittest.TestCase):
    def run_render(self, root, *flags):
        node = ROOT / ".studio/bin/node"
        return subprocess.run([node, ROOT / "runtime/vibe/render.mjs", f"--root={root}", *flags],
                              text=True, capture_output=True)

    def test_wrong_audio_hash_is_rejected_before_the_page_check(self):
        root = Path(tempfile.mkdtemp(prefix="frozen-audio-"))
        self.addCleanup(shutil.rmtree, root)
        (root / "a.wav").write_bytes(b"approved")
        result = self.run_render(root, "--audio=a.wav", "--audio-sha256=deadbeef", "--frames")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("frozen audio changed", result.stderr)
        self.assertNotIn("no film/index.html", result.stderr)

    def test_matching_audio_hash_reaches_the_page_check(self):
        root = Path(tempfile.mkdtemp(prefix="frozen-audio-"))
        self.addCleanup(shutil.rmtree, root)
        (root / "a.wav").write_bytes(b"approved")
        digest = hashlib.sha256(b"approved").hexdigest()
        result = self.run_render(root, "--audio=a.wav", f"--audio-sha256={digest}", "--frames")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no film/index.html", result.stderr)
