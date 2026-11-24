"""Framework regressions: invoke real entrypoints with no production tools."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ModeBoundaryTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "scripts").mkdir()
        for name in ("studio.py", "avs.sh", "vibe.sh", "lanshu.py", "intent.py", "nook.py", "vibe.py"):
            shutil.copy2(ROOT / "scripts" / name, self.root / "scripts" / name)

    def invoke(self, entry, *args):
        argv = ["/bin/bash"] if entry.endswith(".sh") else [sys.executable]
        return subprocess.run([*argv, self.root / "scripts" / entry, *args],
                              cwd=self.root, capture_output=True, text=True, timeout=10)

    def assert_rejected(self, entry, args, explanation):
        result = self.invoke(entry, *args)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(explanation, result.stderr)
        self.assertEqual({path.name for path in self.root.iterdir()}, {"scripts"})
        self.assertFalse((self.root / "scripts" / "__pycache__").exists())

    def test_studio_blocks_writes_before_opening_inputs_or_state(self):
        commands = {
            "make": ("missing.json",), "restore": ("fixture", "missing.zip"),
            "resume": ("fixture",), "revise-picture": ("fixture", "change.json"),
            "revise-edit": ("fixture", "operations.json"),
            "export": ("fixture", "--to", "out"),
        }
        for mode in ((), ("--mode", "design"), ("--mode", "research"),
                     ("--mode", "development")):
            for command, args in commands.items():
                with self.subTest(mode=mode, command=command):
                    required = "delivery" if command == "export" else "production"
                    self.assert_rejected("studio.py", (*mode, command, *args),
                                         f"需要显式 --mode {required}")
        self.assert_rejected("studio.py", ("--mode", "production", "export",
                                          "fixture", "--to", "out"), "需要显式 --mode delivery")
        self.assert_rejected("studio.py", ("--mode", "invalid", "resume", "fixture"), "invalid choice")

    def test_native_entries_block_before_upstream_dispatch(self):
        for command in (("ingest", "EP-FIXTURE"), ("plan", "EP-FIXTURE"),
                        ("adopt-analysis", "EP-FIXTURE", "missing.json"),
                        ("adopt-visual-review", "EP-FIXTURE", "missing.json"),
                        ("adopt-creative-review", "EP-FIXTURE", "missing.json"),
                        ("adopt-approval", "EP-FIXTURE", "missing.json"),
                        ("preview", "EP-FIXTURE"), ("final-render", "EP-FIXTURE"),
                        ("qa", "EP-FIXTURE"), ("creative-review", "EP-FIXTURE"),
                        ("deliver", "EP-FIXTURE"), ("export", "EP-FIXTURE"), ("episode", "create"),
                        ("assets", "approve"), ("content", "init"),
                        ("content", "approve"), ("timeline", "build"), ("subtitles", "build")):
            with self.subTest(command=command):
                self.assert_rejected("avs.sh", ("--mode", "development", *command),
                                     "需要显式 --mode production")
        self.assert_rejected("avs.sh", ("--mode", "production", "workflow", "resume"), "未接入")
        self.assert_rejected("avs.sh", ("doctor", "--json"), "scripts/studio.py doctor")
        self.assert_rejected("vibe.sh", ("fixture", "new", "lyric-mv"), "需要显式 --mode production")
        self.assert_rejected("lanshu.py", ("--out", "works/fixture"), "需要显式 --mode production")

    def test_explicit_mode_reaches_input_validation_without_rendering(self):
        result = self.invoke("studio.py", "--mode", "production", "make", "missing.json")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("missing.json", result.stderr)
        self.assertFalse((self.root / "works").exists())

    def test_vibe_runtime_check_reports_missing_without_falling_back_or_writing(self):
        result = self.invoke("vibe.sh", "runtime-check")
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["check"], "missing_dependencies")
        self.assertTrue(report["missing"])
        self.assertFalse(report["render_started"])
        self.assertFalse(report["model_request_sent"])
        self.assertEqual({path.name for path in self.root.iterdir()}, {"scripts"})
        self.assertFalse((self.root / "scripts/__pycache__").exists())

    def test_read_only_doctor_in_empty_runtime(self):
        (self.root / "docs").mkdir()
        (self.root / ".codex").mkdir()
        (self.root / ".codex" / "config.toml").write_text(
            'model = "gpt-6.1-sol"\nmodel_provider = "openai"\n')
        shutil.copy2(ROOT / "docs" / "capability-index.json", self.root / "docs")
        for name in ("migration-resources.jsonl", "migration-resources-salvaged.jsonl",
                     "migration-hyperframe-pinned.jsonl"):
            (self.root / "docs" / name).touch()
        result = self.invoke("studio.py", "doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["capabilities"]["editor"]["check"], "missing_dependencies")
        self.assertEqual(report["capabilities"]["nook"]["integration"], "adapted_unverified_media")
        self.assertFalse(report["model_session_verified"])
        self.assertFalse((self.root / ".studio").exists())
        self.assertFalse((self.root / "works").exists())

    def test_inventory_uses_current_presence_and_keeps_media_history_separate(self):
        docs = self.root / "docs"
        docs.mkdir()
        (self.root / ".codex").mkdir()
        (self.root / ".codex" / "config.toml").write_text(
            'model = "gpt-6.1-sol"\nmodel_provider = "openai"\n')
        shutil.copy2(ROOT / "docs" / "capability-index.json", docs)
        resource = self.root / "resources" / "auto-motion"
        resource.mkdir(parents=True)
        (resource / "PROMPT.md").write_text("Recovered fixture")

        def write_rows(name, rows):
            (docs / name).write_text("".join(json.dumps(row) + "\n" for row in rows))

        write_rows("migration-resources.jsonl", [
            {"repo": "vibe-motion/auto-motion", "path": "PROMPT.md", "blob": "fixture", "status": "missing"},
            {"repo": "captain-nook/nook_skills", "path": "LICENSE", "blob": "absent", "status": "missing"},
        ])
        write_rows("migration-resources-salvaged.jsonl", [
            {"resource": "auto-motion", "path": "PROMPT.md", "blob": "fixture", "status": "verified-tar"},
        ])
        restored = "workspace-content/objects/aa/restored"
        target = self.root / "sources/hyperframe-pinned" / restored
        target.parent.mkdir(parents=True)
        target.write_bytes(b"archive")
        write_rows("migration-hyperframe-pinned.jsonl", [
            {"path": restored, "status": "missing", "sha": hashlib.sha1(b"blob 7\0archive").hexdigest()},
            {"path": "workspace-content/objects/aa/example", "status": "missing", "size": 42},
            {"path": "workspace-content/objects/aa/unknown", "status": "missing"},
            {"path": "video-agent/example.js", "status": "missing"},
            {"path": "vendor/example", "status": "gitlink"},
        ])
        result = self.invoke("studio.py", "doctor", "--verify-resources")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)["source_inventory"]
        self.assertEqual(report["resources"]["unique_paths"], 2)
        self.assertEqual(report["resources"]["present_on_disk"], 1)
        self.assertEqual(report["resources"]["missing_by_resource"], {"nook-anim": 1})
        self.assertEqual(report["hyperframe"]["migration_counts"],
                         {"missing_media_objects": 3, "missing_other_paths": 1,
                          "different_local": 0, "gitlinks": 1})
        media = report["hyperframe"]["current_media"]
        self.assertEqual(media["present_on_disk"], 1)
        self.assertEqual(media["git_blob_mismatches"], [])
        self.assertEqual(media["missing_on_disk"], 2)
        self.assertEqual(media["missing_known_bytes"], 42)
        self.assertEqual(media["missing_unknown_size_paths"], 1)


if __name__ == "__main__":
    unittest.main()
