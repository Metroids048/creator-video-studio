"""Native Nook integration without importing a user scene or producing frames."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import nook_shot
from native_bundle import pack, scan


class NookShotTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        spec = importlib.util.spec_from_file_location("isolated_nook_studio", ROOT / "scripts/studio.py")
        self.studio = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.studio
        self.addCleanup(lambda: sys.modules.pop(spec.name, None))
        spec.loader.exec_module(self.studio)
        self.studio.ROOT = self.root
        self.studio.VIBE = self.root / "runtime/vibe"
        source = self.root / "resources/nook-anim"
        scripts = source / "nook-anim/scripts/nookanim"
        scripts.mkdir(parents=True)
        for name in ("render", "config", "__init__"):
            (scripts / f"{name}.py").write_text("# native fixture, must not execute\n")
        (scripts.parent / "run.py").write_text("raise RuntimeError('must not execute')\n")
        (source / "LICENSE").write_text("fixture license")
        (self.root / "docs").mkdir()
        (self.root / "docs/nook-macos-arm64.lock.json").write_text("[]")
        fonts = self.studio.VIBE / "fonts"
        fonts.mkdir(parents=True)
        for name in ("LXGWWenKai-Medium.ttf", "ShantellSans-VF.ttf", "MaShanZheng-Regular.ttf",
                     "OFL-WenKai.txt", "OFL-ShantellSans.txt", "OFL-MaShanZheng.txt"):
            (fonts / name).write_bytes(b"font metadata fixture")
        self.project = self.root / "project"
        self.project.mkdir()
        scene = self.project / "scene.py"
        scene.write_text("W,H,FPS,DUR=320,180,24,2\nSHOTS=[(0,'fixture')]\n"
                         "def render(t): pass\nraise RuntimeError('scene must not execute')\n")
        image = self.project / "reference.png"
        image.write_bytes(b"not a real picture; structural fixture only")
        self.shot = {"id": "nook-shot", "kind": "code", "engine": "nook", "sceneAsset": "scene",
                     "sceneAssets": ["reference"], "frames": 48, "width": 320, "height": 180, "fps": 24}
        self.brief = {"id": "project", "route": "code", "width": 320, "height": 180, "fps": 24,
                      "audio": {"mode": "silent"}, "shots": [self.shot], "inputs": [
                          {"id": "scene", "kind": "scene", "path": "scene.py", "sha256": self.studio.digest(scene)},
                          {"id": "reference", "kind": "image", "path": "reference.png", "sha256": self.studio.digest(image)}]}

    def test_native_preparation_freezes_engine_fonts_and_assets_and_roundtrips(self):
        self.studio.validate(self.brief)
        self.studio.check_inputs(self.brief, self.project)
        output = self.project / "version"
        native = output / "shots/nook-shot/film"
        with patch.object(nook_shot.subprocess, "run", side_effect=AssertionError("no process")):
            self.studio.prepare_code_scene(self.shot, self.brief, self.project, native)
        self.assertEqual((native / "scene.py").read_bytes(), (self.project / "scene.py").read_bytes())
        self.assertEqual(json.loads((native / "assets.json").read_text()), {"reference": "assets/reference.png"})
        self.assertTrue((native / "scripts/nookanim/render.py").is_file())
        # Use the same input location contract as real studio imports.
        brief = json.loads(json.dumps(self.brief))
        for item in brief["inputs"]:
            path = self.project / item["path"]
            dest = output / "inputs" / path.name
            dest.parent.mkdir(exist_ok=True)
            shutil.copyfile(path, dest)
            item["path"] = "inputs/" + path.name
        (output / "brief.json").write_text(json.dumps(brief))
        archive = self.project / "editable.zip"
        pack(archive, [(p.relative_to(output).as_posix(), p) for p in output.rglob("*") if p.is_file()],
             "project", "v0001", "code", self.studio.digest)
        extracted = self.project / "imported"
        extracted.mkdir()
        report = scan(archive, extracted)
        self.assertEqual((extracted / "shots/nook-shot/film/scene.py").read_bytes(), (native / "scene.py").read_bytes())
        self.assertIn("shots/nook-shot/film/scripts/nookanim/render.py", report["members"])
        (self.root / "resources/nook-anim/nook-anim/scripts/nookanim/render.py").write_text("changed shared engine")
        revised = self.project / "revision/shots/nook-shot/film"
        self.studio.prepare_code_scene(self.shot, self.brief, self.project, revised, native)
        self.assertEqual((revised / "scripts/nookanim/render.py").read_bytes(),
                         (native / "scripts/nookanim/render.py").read_bytes())
        (output / "brief.json").write_text(json.dumps(self.brief))
        with self.assertRaisesRegex(ValueError, "共享模板参数"):
            self.studio.picture_brief(output, {"shot": "nook-shot", "visual": {"title": "no silent no-op"}})

    def test_scene_mismatch_dynamic_config_and_unknown_engine_are_rejected(self):
        for key,value in (("width", 640), ("height", 360), ("fps", 30)):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "不一致"):
                self.studio.check_inputs({**self.brief, key: value}, self.project)
        for frames in (24, 49):
            with self.assertRaisesRegex(ValueError, "不一致"):
                self.studio.check_inputs({**self.brief, "shots": [{**self.shot,"frames": frames}]}, self.project)
        scene = self.project / "scene.py"
        scene.write_text(scene.read_text().replace("24,2", "24,unknown"))
        with self.assertRaisesRegex(ValueError, "原始素材校验失败"):
            self.studio.check_inputs(self.brief, self.project)
        self.brief["inputs"][0]["sha256"] = self.studio.digest(scene)
        with self.assertRaisesRegex(ValueError, "未闭合"):
            self.studio.check_inputs(self.brief, self.project)
        with self.assertRaisesRegex(ValueError, "未知代码"):
            self.studio.validate({**self.brief, "shots": [{**self.shot,"engine":"unknown"}]})

    def test_dispatch_uses_native_cache_copy_and_bad_output_is_not_promoted(self):
        out = self.project / "candidate"
        with patch.object(nook_shot, "render") as renderer, patch.object(self.studio, "probe") as probe:
            probe.return_value = {"streams": [{"codec_type": "video", "nb_frames": "47", "width": 320,
                                                "height": 180, "avg_frame_rate": "24/1"}]}
            with self.assertRaisesRegex(ValueError, "未写入有效缓存"):
                self.studio.code_segment(self.shot, self.brief, out, self.project)
            self.assertEqual(renderer.call_count, 1)
            native, target = renderer.call_args.args[2:]
            self.assertIn(".cache/video", str(native))
            self.assertTrue((native / "scene.py").is_file())
            self.assertFalse((target.parent / "receipt.json").exists())
            self.assertFalse((target.parent / "segment.mp4").exists())
        self.assertFalse(list(self.project.rglob("*.mp4")))

    def test_native_command_uses_frozen_fonts_and_no_other_nook_tool(self):
        import nook

        native = self.project / "native"
        target = self.project / "segment-tmp.mp4"
        with patch.object(nook, "runtime_environment", return_value={}), \
                patch.object(nook_shot.subprocess, "run") as command:
            nook_shot.render(self.studio, self.shot, native, target)
        argv = command.call_args.args[0]
        self.assertEqual(argv[2:], [native / "scripts/run.py", "render", native / "scene.py", "video", "--out", target])
        env = command.call_args.kwargs["env"]
        self.assertEqual(env["NOOKANIM_FONT_UI"], str(native / "fonts/LXGWWenKai-Medium.ttf"))
        self.assertEqual(command.call_args.kwargs["cwd"], native)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
