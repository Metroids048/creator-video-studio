"""Native HTML preparation, roundtrip and failure gates; never starts a browser."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import html_shot
from native_bundle import pack, scan

class HTMLShotTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name).resolve()
        spec = importlib.util.spec_from_file_location("isolated_html_studio", ROOT / "scripts/studio.py")
        self.studio = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.studio
        self.addCleanup(lambda: sys.modules.pop(spec.name, None))
        spec.loader.exec_module(self.studio)

    def brief(self, engine="art", style=None):
        scene = self.project / "original.json"
        scene.write_text(json.dumps({"grammar":"y4_storytime", "duration":2, "fps":24,
            "width":320,"height":180,"data":{"character":"poses"},
            "cues":[{"at":0,"kind":"point","text":"fixture"}]}))
        poses = self.project / "poses"
        poses.mkdir(exist_ok=True)
        rows = [{"id":"scene","kind":"scene","path":"original.json"}]
        for name, pose in (("pose-a","rest"),("pose-b","talk")):
            (poses / (pose+".png")).write_bytes(b"structural fixture, not a generated image")
            rows.append({"id":name,"kind":"image","path":"poses/"+pose+".png"})
        shot = {"id":"own-shot","kind":"code","engine":engine,"sceneAsset":"scene",
                "sceneAssets":["pose-a","pose-b"],"frames":48,"fps":24,"width":320,"height":180}
        if engine == "lanshu":
            shot.update(style=style, beatsAsset="beats",width=1920,height=1080)
            scene.write_text(json.dumps({"duration":2,"lines":[],"recap":{"start":1,"end":2}}))
            (self.project / "own-beats.js").write_text("// isolated author fixture; never evaluated\n")
            rows.append({"id":"beats","kind":"scene","path":"own-beats.js"})
        brief = {"id":"isolated","route":"code","width":shot["width"],"height":shot["height"],
                 "fps":24,"audio":{"mode":"silent"},"inputs":rows,"shots":[shot]}
        self.studio.import_inputs(brief, self.project/"brief-source.json", self.project)
        scene.unlink()
        shutil.rmtree(poses)
        return brief,shot

    def roundtrip(self, native, brief):
        output = native.parents[2]
        (output / "inputs").mkdir()
        for row in brief["inputs"]:
            shutil.copyfile(self.project/row["path"],output/row["path"])
        (output / "brief.json").write_text(json.dumps(brief))
        archive = self.project / (output.name+".zip")
        pack(archive,[(p.relative_to(output).as_posix(),p) for p in output.rglob("*") if p.is_file()],
             "isolated","v0001","code",self.studio.digest)
        report=scan(archive)
        self.assertIn("shots/own-shot/film/scene.json",report["members"])

    def test_art_import_preserves_pose_names_and_native_roundtrip(self):
        brief,shot=self.brief()
        self.studio.validate(brief)
        self.studio.check_inputs(brief,self.project)
        native=self.project/"candidate/shots/own-shot/film"
        self.studio.prepare_code_scene(shot,brief,self.project,native)
        spec=json.loads((native/"effective-spec.json").read_text())
        self.assertEqual(spec["data"]["character"]["frames"],
                         {"rest":"/assets/pose-a.png","talk":"/assets/pose-b.png"})
        self.assertEqual((native/"scene.json").read_bytes(),(self.project/"inputs/scene.json").read_bytes())
        self.roundtrip(native,brief)
        revised=self.project/"revision/shots/own-shot/film"
        self.studio.prepare_code_scene(shot,brief,self.project,revised,native)
        self.assertEqual((native/"engine/clip.js").read_bytes(),(revised/"engine/clip.js").read_bytes())
        self.assertEqual((native/"render-shot.mjs").read_bytes(),(revised/"render-shot.mjs").read_bytes())

    def test_all_lanshu_styles_prepare_offline_with_own_story_and_beats(self):
        import lanshu
        brief,base=self.brief("lanshu",lanshu.STYLES[0])
        for style in lanshu.STYLES:
            with self.subTest(style=style):
                shot={**base,"style":style}
                this={**brief,"shots":[shot]}
                self.studio.validate(this)
                self.studio.check_inputs(this,self.project)
                native=self.project/style/"shots/own-shot/film"
                self.studio.prepare_code_scene(shot,this,self.project,native)
                self.assertEqual((native/"engine/beats.js").read_bytes(),(self.project/"inputs/beats.js").read_bytes())
                html=(native/"engine/index.html").read_text()
                self.assertNotIn("<audio",html)
                self.assertNotIn("https://cdn.jsdelivr.net/npm/gsap",html)
                self.assertEqual(html.count('id="studio-assets"'),1)
                self.assertIn('data-duration="2"',html)
                self.assertTrue((native/"engine/font-source.json").is_file())
                self.roundtrip(native,this)
                revised=self.project/(style+"-revision")/"shots/own-shot/film"
                self.studio.prepare_code_scene(shot,this,self.project,revised,native)
                self.assertEqual((native/"engine/font-source.json").read_bytes(),(revised/"engine/font-source.json").read_bytes())
                self.assertEqual((revised/"engine/index.html").read_text().count('id="studio-assets"'),1)

    def test_contract_and_cache_reject_incomplete_or_wrong_output(self):
        brief,shot=self.brief()
        bad=copy.deepcopy(brief)
        bad["shots"][0]["sceneAssets"]=[]
        with self.assertRaisesRegex(ValueError,"素材未闭合"):
            self.studio.check_inputs(bad,self.project)
        with patch.object(html_shot,"render") as renderer,patch.object(self.studio,"probe") as probe:
            probe.return_value={"streams":[{"codec_type":"video","nb_frames":"47","width":320,
                                           "height":180,"avg_frame_rate":"24/1"}]}
            with self.assertRaisesRegex(ValueError,"未写入有效缓存"):
                self.studio.code_segment(shot,brief,self.project/"bad-candidate",self.project)
            self.assertEqual(renderer.call_count,1)
            self.assertIn(".cache/video",str(renderer.call_args.args[2]))
        self.assertFalse(list(self.project.rglob("*.mp4")))
        self.assertFalse(list(self.project.rglob("receipt.json")))

    def test_declared_page_params_only_change_owned_page_anchors(self):
        brief, shot = self.brief("lanshu", "v1-editorial")
        native = self.project / "parent/shots/own-shot/film"
        self.studio.prepare_code_scene(shot, brief, self.project, native)
        shot["pageParams"] = {"captionSize": 60, "turn": 1.05, "lead": 0.04, "tail": 0.04}
        revised = self.project / "revision/shots/own-shot/film"
        self.studio.prepare_code_scene(shot, brief, self.project, revised, native)
        original = (native / "engine/index.html").read_text()
        expected = original.replace("const TURN = 0.9;", "const TURN = 1.05;")
        expected = expected.replace("lead: 0.08, tail: 0.1", "lead: 0.04, tail: 0.04")
        expected = expected.replace("</head>", '<style id="studio-page-params">.kit-cap { font-size: 60px; }</style>\n</head>')
        self.assertEqual((revised / "engine/index.html").read_text(), expected)
        for path in (native / "engine").rglob("*"):
            if path.is_file() and path.name != "index.html":
                self.assertEqual(path.read_bytes(), (revised / "engine" / path.relative_to(native / "engine")).read_bytes())
        manifest = self.studio.load(revised.parent / "scene-source.json")
        self.assertEqual(manifest["files"]["engine/index.html"], self.studio.digest(revised / "engine/index.html"))
        # Repeating declared parameters must be idempotent, including the CSS block.
        again = self.project / "again/shots/own-shot/film"
        self.studio.prepare_code_scene(shot, brief, self.project, again, revised)
        self.assertEqual((again / "engine/index.html").read_text(), expected)

    def test_page_params_validate_at_plan_and_revision_entry(self):
        brief, shot = self.brief("lanshu", "v1-editorial")
        for params in ({"css": "body{}"}, {"turn": "1;alert(1)"}, {"lead": True},
                       {"tail": -1}, {"captionSize": 0}, {"turn": float("nan")}, []):
            with self.subTest(params=params), self.assertRaisesRegex(ValueError, "pageParams"):
                self.studio.validate({**brief, "shots": [{**shot, "pageParams": params}]})
        for engine, style in (("art", None), ("lanshu", "v2-signal")):
            with self.subTest(engine=engine), self.assertRaisesRegex(ValueError, "pageParams"):
                self.studio.validate({**brief, "shots": [{**shot, "engine": engine, "style": style,
                                                        "pageParams": {"turn": 1.05}}]})
        shot["pageParams"] = {"turn": 1.05}
        version = self.project / "versions/v0001"
        version.mkdir(parents=True)
        self.studio.save(version / "brief.json", brief)
        result = self.studio.picture_brief(version, {"base": "v0001", "shot": shot["id"],
            "visual": {"pageParams": {"captionSize": 60}}})
        self.assertEqual(result["shots"][0]["pageParams"], {"turn": 1.05, "captionSize": 60})

    def test_page_params_refuse_changed_native_anchor_and_implicit_reset(self):
        brief, shot = self.brief("lanshu", "v1-editorial")
        shot["pageParams"] = {"turn": 1.05}
        native = self.project / "parent/shots/own-shot/film"
        self.studio.prepare_code_scene(shot, brief, self.project, native)
        with self.assertRaisesRegex(ValueError, "pageParams"):
            self.studio.prepare_code_scene({k:v for k,v in shot.items() if k != "pageParams"},
                                          brief, self.project, self.project / "reset", native)
        # Unit coverage for a missing anchor; parent integrity is tested through status/render separately.
        page = native / "engine/index.html"
        page.write_text(page.read_text().replace("const TURN =", "const RENAMED ="))
        with self.assertRaisesRegex(ValueError, "锚点"):
            self.studio.prepare_code_scene(shot, brief, self.project, self.project / "bad-anchor", native)

    def test_picture_revision_imports_declared_new_visual_assets(self):
        brief, shot = self.brief("lanshu", "v1-editorial")
        version = self.project / "versions/v0001"
        version.mkdir(parents=True)
        self.studio.save(version / "brief.json", brief)
        texture = self.project / "earth.jpg"
        texture.write_bytes(b"structural fixture; not a visual quality sample")
        row = {"id": "earth", "kind": "image", "path": texture.name,
               "sha256": self.studio.digest(texture)}
        change = {"base": "v0001", "reason": "Use a declared texture in the existing shot",
                  "shot": shot["id"], "visual": {"sceneAssets": [*shot["sceneAssets"], "earth"]},
                  "inputs": [row]}
        for bad in ({**change, "visual": {"sceneAssets": shot["sceneAssets"]}},
                    {**change, "inputs": [{**row, "kind": "audio"}]},
                    {**change, "inputs": [{**row, "sha256": "0" * 64}]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.studio.picture_brief(version, bad, self.project / "change.json")
        preview = self.studio.picture_brief(version, change, self.project / "change.json", preview_only=True)
        self.assertEqual(next(r for r in preview["inputs"] if r["id"] == "earth")["path"], str(texture))
        self.assertFalse(list((self.project / "inputs").glob("picture-*")))
        revised = self.studio.picture_brief(version, change, self.project / "change.json")
        imported = next(r for r in revised["inputs"] if r["id"] == "earth")
        self.assertEqual((self.project / imported["path"]).read_bytes(), texture.read_bytes())
        native = self.project / "revised/shots/own-shot/film"
        self.studio.prepare_code_scene(revised["shots"][0], revised, self.project, native)
        self.assertEqual((native / "assets/earth.jpg").read_bytes(), texture.read_bytes())
        self.assertEqual(json.loads((version / "brief.json").read_text()), brief)

    def test_declared_params_do_not_bypass_real_parent_integrity_entry(self):
        brief, shot = self.brief("lanshu", "v1-editorial")
        shot["pageParams"] = {"captionSize": 60, "turn": 1.05}
        version = self.project / "isolated/versions/v0001"
        native = version / "shots/own-shot/film"
        self.studio.prepare_code_scene(shot, brief, self.project, native)
        self.studio.save(version / "brief.json", brief)
        (version / "video.mp4").write_bytes(b"structural integrity fixture; not a rendered video")
        files = {p.relative_to(version).as_posix(): self.studio.digest(p)
                 for p in (version / "shots").rglob("*") if p.is_file()}
        pack(version / "editable.zip", [(p.relative_to(version).as_posix(), p)
             for p in version.rglob("*") if p.is_file()] + [(row["path"], self.project / row["path"])
             for row in brief["inputs"]], brief["id"], "v0001", "code", self.studio.digest)
        self.studio.save(version / "receipt.json", {"project": brief["id"], "version": "v0001",
            "delivery": {name: self.studio.digest(version / name)
                         for name in ("video.mp4", "brief.json", "editable.zip")},
            "segments": [{"id": shot["id"], "nativeFiles": files}]})
        self.studio.check_native_version(version)
        # The real render entry checks the already-frozen parent before preparing a child.
        page = native / "engine/index.html"
        page.write_text(page.read_text().replace("const TURN = 1.05;", "const TURN = 1.7;"))
        with self.assertRaisesRegex(ValueError, "原生镜头校验失败"):
            self.studio.render(brief, self.project, self.project / "child", version)
        self.assertFalse((self.project / "child").exists())

    def test_renderer_clock_import_has_no_browser_or_media_side_effect(self):
        script="""import {frameTimes} from './adapters/native-html-shot.mjs';
        if(JSON.stringify(frameTimes({frames:3,fps:24}))!==JSON.stringify([0,1/24,2/24])) throw Error('clock');
        for(const shot of [{frames:0,fps:24},{frames:2.5,fps:24},{frames:2,fps:60}]) {
          let blocked=false;try{frameTimes(shot)}catch{blocked=true}if(!blocked)throw Error('invalid clock accepted');
        }"""
        subprocess.run([ROOT/".studio/bin/node","--input-type=module","-e",script],cwd=ROOT,check=True)

    def test_portrait_capture_uses_declared_native_canvas_and_preserves_legacy(self):
        script="""import {captureViewport} from './adapters/native-html-shot.mjs';
        const shot={engine:'opuscar',width:720,height:1280};
        if(JSON.stringify(captureViewport(shot,{canvas:{width:720,height:1280}}))!==JSON.stringify({width:720,height:1280})) throw Error('portrait regressed');
        if(JSON.stringify(captureViewport({...shot,width:1280,height:720}))!==JSON.stringify({width:1920,height:1080})) throw Error('legacy changed');
        let blocked=false;try{captureViewport(shot,{canvas:{width:720,height:720}})}catch{blocked=true}
        if(!blocked)throw Error('unsupported native canvas accepted');
        """
        subprocess.run([ROOT/".studio/bin/node","--input-type=module","-e",script],cwd=ROOT,check=True)

if __name__ == "__main__": unittest.main()
