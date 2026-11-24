"""Actual photo-story contracts: beat changes and frozen outputs stay bound."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import photo_templates
import studio


class PhotoContractTest(unittest.TestCase):
    def setUp(self):
        self.story = json.loads((ROOT / "productions/photo-formats-20261114/beat-story.json").read_text())

    def test_cut_off_the_bound_beat_is_rejected(self):
        photo_templates.validate(self.story)
        changed = copy.deepcopy(self.story)
        changed["scenes"][0]["end"] += 1
        changed["scenes"][1]["start"] += 1
        with self.assertRaisesRegex(ValueError, "换图必须落在"):
            photo_templates.validate(changed)

    def test_mirror_and_clear_hold_contract(self):
        changed = copy.deepcopy(self.story)
        changed["scenes"][0].update(mirror="xy", transitionFrames=7)
        photo_templates.validate(changed)
        changed["scenes"][0]["transitionFrames"] = 16
        with self.assertRaisesRegex(ValueError, "清晰展示"):
            photo_templates.validate(changed)
        changed["scenes"][0].update(mirror="other", transitionFrames=5)
        with self.assertRaisesRegex(ValueError, "镜像"):
            photo_templates.validate(changed)

    def test_complete_documentary_photo_fit_is_explicit(self):
        changed = copy.deepcopy(self.story)
        changed['scenes'][0]['fit'] = 'contain'
        photo_templates.validate(changed)
        changed['scenes'][0]['fit'] = 'stretch'
        with self.assertRaisesRegex(ValueError, '展示方式'):
            photo_templates.validate(changed)

    def test_frozen_story_and_audio_are_checked_at_production_entry(self):
        base = ROOT / "productions/photo-formats-20261114/beat-prepared"
        brief = json.loads((base / "brief.json").read_text())
        inputs = {x["id"]: (x["kind"], base / x["path"]) for x in brief["inputs"]}
        photo_templates.check_inputs(brief, inputs)
        changed = copy.deepcopy(brief)
        changed["shots"][0]["frames"] -= 1
        with self.assertRaises(ValueError):
            photo_templates.check_inputs(changed, inputs)
        changed = copy.deepcopy(brief)
        changed["shots"][0]["cues"] = []
        with self.assertRaises(ValueError):
            photo_templates.check_inputs(changed, inputs)

    def test_photo_request_keeps_representative_and_reports_archived_gap(self):
        import video_templates
        result = video_templates.match("花卉图片卡点音乐混剪", "9:16")
        self.assertEqual(result["engineering_candidates"][0]["id"], "photo-beat-montage")
        result = video_templates.match("给忙碌的人做图文共鸣照片拼贴画册", "9:16")
        self.assertFalse(result["engineering_candidates"])
        self.assertIn("tape-photo-essay", [item["id"] for item in result["rejected"]])

    def test_picture_revision_imports_bound_story_without_mutating_parent(self):
        source = ROOT / "productions/photo-formats-20261114/beat-prepared"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / "photo-work"
            project.mkdir()
            brief = json.loads((source / "brief.json").read_text())
            studio.import_inputs(brief, source / "brief.json", project)
            version = project / "versions/v0001"
            version.mkdir(parents=True)
            studio.save(version / "brief.json", brief)
            before = {p: studio.digest(p) for p in (project / "inputs").iterdir()}
            story = copy.deepcopy(self.story)
            story["scenes"][0].update(anchor=[.3, .5], mirror="x", transitionFrames=5)
            studio.save(base / "story.json", story)
            rendered = copy.deepcopy(story)
            for i, scene in enumerate(rendered["scenes"]):
                scene["asset"] = "photo-" + str(i)
            (base / "scene.js").write_text("const PHOTO_STORY = " + json.dumps(rendered) + ";\n" +
                                           (ROOT / "templates/photo-sequence/scene.js").read_text())
            change = {"base": "v0001", "reason": "Keep the photo subject visible",
                      "shot": "photos", "visual": {"sceneAsset": "scene"},
                      "inputs": [{"id": name, "kind": kind, "path": name + suffix,
                                  "sha256": studio.digest(base / (name + suffix))}
                                 for name, kind, suffix in (("story", "data", ".json"), ("scene", "scene", ".js"))]}
            change_path = base / "change.json"
            studio.save(change_path, change)
            files_before = {p for p in (project / "inputs").rglob("*")}
            preview = studio.picture_brief(version, change, change_path, preview_only=True)
            self.assertEqual({p for p in (project / "inputs").rglob("*")}, files_before)
            self.assertEqual(next(r for r in preview["inputs"] if r["id"] == "scene")["path"],
                             str((base / "scene.js").resolve()))
            revised = studio.picture_brief(version, change, change_path)
            studio.check_inputs(revised, project)
            self.assertEqual(revised["audio"], brief["audio"])
            self.assertEqual(revised["shots"], brief["shots"])
            self.assertEqual({p: studio.digest(p) for p in before}, before)
            self.assertEqual(studio.load(version / "brief.json"), brief)
            changed_rows = {r["id"]: r for r in revised["inputs"]}
            self.assertNotEqual(changed_rows["story"]["path"], "inputs/story.json")
            self.assertEqual(len(Path(changed_rows["story"]["path"]).parts), 2)
            # The shot ID is unchanged, but its frozen visual inputs changed.
            (version / "subtitles.srt").write_text("")
            (version / "audio.m4a").write_bytes(b"locked audio fixture")
            picture = version / "shots/photos/picture.mp4"
            picture.parent.mkdir(parents=True)
            picture.write_bytes(b"parent picture fixture")
            studio.save(version / "receipt.json", {"segments": [{
                "id": "photos", "sha256": studio.digest(picture), "nativeFiles": {}}]})
            for candidate in (brief, revised):
                candidate["shots"][0]["captionTiming"] = candidate["shots"][0]["cues"]
            studio.save(version / "brief.json", brief)
            out = project / "candidate"
            out.mkdir()
            with patch.object(studio, "check_native_version"), \
                    patch.object(studio, "code_segment", side_effect=RuntimeError("fingerprint boundary")), \
                    patch.object(studio, "ff"), \
                    self.assertRaisesRegex(RuntimeError, "fingerprint boundary"):
                studio.render(revised, project, out, version)
            self.assertEqual((out / "audio.m4a").read_bytes(), b"locked audio fixture")
            # A mismatched story must fail before any further files are imported.
            story["scenes"][0]["anchor"] = [.1, .2]
            studio.save(base / "story.json", story)
            change["inputs"][0]["sha256"] = studio.digest(base / "story.json")
            files_before = {p for p in (project / "inputs").rglob("*")}
            with self.assertRaisesRegex(ValueError, "本版故事"):
                studio.picture_brief(version, change, change_path)
            self.assertEqual({p for p in (project / "inputs").rglob("*")}, files_before)
            # This entry may never replace the soundtrack.
            change["inputs"] = [{"id": "music", "kind": "audio", "path": "story.json"}]
            with self.assertRaisesRegex(ValueError, "画面素材"):
                studio.picture_brief(version, change, change_path)


if __name__ == "__main__":
    unittest.main()
