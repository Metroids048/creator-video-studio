"""Template selection, migration and actual production-entry safeguards."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import video_templates as templates


class VideoTemplatesTest(unittest.TestCase):
    def setUp(self):
        self.story = templates.read(ROOT / "templates/paper-ink-landscape/v1/example.json")

    def test_catalog_counts_styles_not_blank_canvas_or_reference_cards(self):
        report = templates.inventory()
        self.assertEqual(report["style_count"], 19)
        self.assertEqual(report["registered_count"], 44)
        self.assertEqual(len(report["archived"]), 25)
        self.assertEqual(sum(t["family"] == "lanshu" for t in report["templates"]), 4)
        self.assertEqual(len({t["curation"]["family"] for t in report["templates"]}), 19)
        self.assertTrue(all(t["files_present"] for t in report["templates"]))
        self.assertFalse(any("v0-canvas" in t["id"] for t in report["templates"]))

    def test_tactile_routes_respect_format_actor_and_revision_boundaries(self):
        for text, template in (("抖音竖屏桌灯零件装配", "object-assembly"),):
            result = templates.match(text, "9:16")
            self.assertEqual(result["engineering_candidates"][0]["id"], template)
            self.assertFalse(result["auto_selected"])
        self.assertFalse(templates.match("法庭真人多人长对话", "9:16")["engineering_candidates"])
        result = templates.match("纸艺人物打斗与多人对话", "9:16")
        self.assertFalse(result["engineering_candidates"])
        self.assertTrue(result["rejected"])
        run = subprocess.run([sys.executable, ROOT / "scripts/studio.py", "intent",
                              "只改旧片里的纸艺画面，锁住音轨和其他镜头"],
                             capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(run.stdout)["profile"], "revision")
        self.assertFalse(json.loads(run.stdout)["template_match"]["applicable"])

    def test_matching_explains_candidates_and_refuses_untested_vertical(self):
        candidates = templates.match("纸墨 山形 人物 路径 学习 反馈")["engineering_candidates"]
        self.assertEqual(candidates[0]["id"], "paper-ink-landscape")
        self.assertIn("反馈", candidates[0]["matched"])
        self.assertEqual(templates.match("纸墨 山形", "9:16")["next"], "no_compatible_template")

    def test_market_recipe_routes_without_becoming_a_production_template(self):
        result = templates.match("参考若卿，做一条国风歌词道具转场", "9:16")
        reference = result["research_references"][0]
        self.assertEqual(reference["id"], "lyric-prop")
        self.assertTrue(reference["research_only"])
        self.assertFalse(reference["production_template"])
        self.assertTrue((ROOT / reference["entry"]).is_file())
        self.assertGreater(reference["market"]["likes"], 200000)
        self.assertIsNone(reference["market"]["retention"])
        self.assertNotIn("lyric-prop", [item["id"] for item in templates.catalog()])
        self.assertFalse(reference["compatible_production_templates"])
        self.assertIn("已归档", reference["implementation"])
        brief = {"template": {"id": "lyric-prop", "version": "1"}}
        with self.assertRaisesRegex(ValueError, "未登记"):
            templates.check_binding(brief)

    def test_specific_market_form_does_not_fall_back_to_unrelated_generic_style(self):
        for text, reference in (("若卿的国风歌词道具", "lyric-prop"),
                                ("三维历史年代长轴", "history-axis")):
            result = templates.match(text)
            self.assertEqual(result["research_references"][0]["id"], reference)
            self.assertFalse(result["engineering_candidates"])
            self.assertEqual(result["next"], "no_compatible_template")
            self.assertTrue(result["rejected"])
        result = templates.match("花卉卡点音乐混剪", "9:16")
        self.assertEqual([x["id"] for x in result["engineering_candidates"]], ["photo-beat-montage"])
        self.assertEqual(templates.match("像素日常故事")["engineering_candidates"][0]["id"], "opuscar-pixel-story")

    def test_whole_source_review_does_not_misroute_distinct_paper_grammars(self):
        drawn = templates.match("Kevin的撕纸故事，窗口提问，再用拼贴剧情回答")
        ids = [row["id"] for row in drawn["engineering_candidates"]]
        self.assertIn("studio-paper-question", ids)
        self.assertNotIn("opuscar-one-line", ids)
        for text in ("黑白手绘成长，墨团成长", "纸艺人物打斗与多人对话"):
            result = templates.match(text)
            self.assertFalse(result["engineering_candidates"])
            self.assertTrue(result["research_references"])

    def test_source_engineering_candidate_keeps_its_actual_scope_in_intent_route(self):
        result = templates.match("角色MV歌曲叙事")
        reference = result["research_references"][0]
        self.assertEqual(reference["id"], "illustrated-song")
        self.assertIn("/2097752569212756134", reference["source"])
        self.assertEqual(reference["market"]["views"], 771278)
        self.assertTrue((ROOT / reference["method_source_index"]).is_file())
        source = reference["method_sources"][0]
        self.assertTrue((ROOT / source["entry"]).is_file())
        self.assertIn("not executed", source["scope"])
        self.assertIn("不是原帖源码", source["gap"])
        self.assertFalse(reference["production_template"])
        self.assertFalse(result["engineering_candidates"])

    def test_route_returns_real_preview_and_adaptation_not_only_template_name(self):
        for item in templates.active_catalog():
            candidate = templates.match(item["id"], item["formats"][0])["engineering_candidates"][0]
            self.assertEqual(candidate["id"], item["id"])
            self.assertTrue((ROOT / candidate["sample"]["player"]).is_file())
            self.assertTrue((ROOT / candidate["sample"]["story"]).is_file())
            self.assertTrue(candidate["adaptation"]["replace"])
            self.assertTrue(candidate["adaptation"]["example_request"])
            for path, expected in candidate["sample"]["hashes"].items():
                self.assertEqual(templates.sha(ROOT / path), expected)
        self.assertTrue(all(t["sample_present"] for t in templates.inventory()["templates"]))

    def test_boxcutter_failed_acting_is_not_offered_as_a_mature_template(self):
        request = "用黑白默片喜剧做开箱刀，复杂握持、转身、受力拆包装"
        run = subprocess.run([sys.executable, ROOT / "scripts/studio.py", "templates", "match", request],
                             capture_output=True, text=True, check=True)
        report = json.loads(run.stdout)
        self.assertNotIn("opuscar-silent-comedy", [c["id"] for c in report["candidates"]])
        self.assertNotIn("opuscar-silent-comedy", [c["id"] for c in report["engineering_candidates"]])
        self.assertTrue(any(c["id"] == "opuscar-silent-comedy" and "开箱刀" in c.get("evidence", [])
                            for c in report["rejected"]))

    def test_withdrawn_reference_review_blocks_fresh_production_selection(self):
        request = "黑白默片喜剧找眼镜"
        report = templates.match(request)
        candidate = next(c for c in report["engineering_candidates"] if c["id"] == "opuscar-silent-comedy")
        self.assertFalse(candidate["market"]["qualified"])
        self.assertNotIn("s13dLaTIHSg", [s["id"] for s in candidate["market"]["sources"]])
        with self.assertRaisesRegex(ValueError, "缺双对标"):
            templates.selection_receipt(request, "寻找眼镜，最后发现架在头顶。", "16:9",
                                        "opuscar-silent-comedy")
        self.assertEqual(templates.selection_receipt(request, "寻找眼镜，最后发现架在头顶。", "16:9",
                         "opuscar-silent-comedy", "engineering_validation")["purpose"], "engineering_validation")

    def test_intake_distinguishes_catalogue_new_creation_and_existing_edit(self):
        requests = (("整理样片目录和项目workflow，新视频下一轮再做", "framework"),
                    ("给SaaS产品做一条纸墨山形品牌片", "commerce"),
                    ("剪辑已有视频，保留原音", "edit"))
        for request, profile in requests:
            result = subprocess.run([sys.executable, ROOT / "scripts/studio.py", "intent", request],
                                    capture_output=True, text=True, check=True)
            report = json.loads(result.stdout)
            self.assertEqual(report["profile"], profile)
            self.assertFalse(report["render_started"])
            self.assertFalse(report["execution_authorized_by_route"])
            if profile == "edit":
                self.assertFalse(report["template_match"]["applicable"])
            else:
                self.assertIn("style-templates", report["packs"])
                self.assertEqual(report["template_gallery"], "templates/gallery/index.html")
                if profile == "commerce":
                    self.assertEqual(report["template_match"]["engineering_candidates"][0]["id"], "paper-ink-landscape")

    def test_preview_builder_rejects_changed_sample_before_writing(self):
        from template_gallery import build
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "templates").mkdir()
            (root / "changed.html").write_text("not registered bytes")
            (root / "templates/catalog.json").write_text(json.dumps({"templates": [
                {"sample": {"hashes": {"changed.html": "0" * 64}}}]}))
            with self.assertRaisesRegex(ValueError, "样片已变化"):
                build(root)
            self.assertFalse((root / "templates/gallery").exists())

    def test_preview_rejects_missing_adaptation_steps_from_actual_catalogue(self):
        from template_gallery import build
        from unittest.mock import patch
        item = copy.deepcopy(templates.catalog()[-2])
        item["adaptation"].pop("steps")
        with patch("template_gallery.catalog", return_value=[item]):
            with self.assertRaisesRegex(ValueError, "换稿步骤"):
                build(ROOT)

    def test_actual_preview_supports_video_seeking_and_blocks_private_paths(self):
        server = subprocess.Popen(
            [sys.executable, ROOT / "scripts/studio.py", "templates", "preview"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            url = json.loads(server.stdout.readline())["url"]
            origin = url.split("/templates/")[0]
            sample = templates.catalog()[-1]["sample"]["path"]
            data = (ROOT / sample).read_bytes()
            for header, expected, span in (("bytes=0-31", data[:32], f"0-31/{len(data)}"),
                                           ("bytes=-16", data[-16:], f"{len(data)-16}-{len(data)-1}/{len(data)}")):
                with urlopen(Request(origin + "/" + sample, headers={"Range": header}), timeout=10) as response:
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.headers["Content-Range"], "bytes " + span)
                    self.assertEqual(response.read(), expected)
            for path, headers, status in ((sample, {"Range": f"bytes={len(data)}-"}, 416),
                                          (".codex/config.toml", {}, 404)):
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(origin + "/" + path, headers=headers), timeout=10)
                self.assertEqual(error.exception.code, status)
        finally:
            server.terminate()
            server.communicate(timeout=10)

    def test_changed_story_geometry_and_camera_reach_frozen_scene(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for i in range(2):
                data = copy.deepcopy(self.story)
                data["id"] = f"migration-{i}"
                data["scenes"][0]["title"] = ["先练一次", "先做一个样件"][i]
                data["terrain"][2][1] -= 25 * i
                data["camera"][1]["x"] += 20 * i
                source = base / f"story-{i}.json"
                source.write_text(json.dumps(data))
                templates.prepare(source, base / f"out-{i}")
            scenes = [(base / f"out-{i}/scene.js").read_text() for i in range(2)]
            self.assertNotEqual(scenes[0], scenes[1])
            self.assertIn("先做一个样件", scenes[1])
            self.assertNotIn("reference-geometry", scenes[1])
            brief = templates.read(base / "out-1/brief.json")
            first = templates.read(base / "out-0/brief.json")
            self.assertNotEqual(first["shots"][0]["sceneAsset"], brief["shots"][0]["sceneAsset"])
            self.assertNotEqual(first["shots"][0]["sceneAssets"][-1], brief["shots"][0]["sceneAssets"][-1])
            self.assertTrue(brief["title"].strip())
            self.assertEqual(templates.check_binding(brief)["id"], "paper-ink-landscape")
            self.assertTrue(all(templates.sha(base / "out-1" / item["path"]) == item["sha256"] for item in brief["inputs"]))
            with self.assertRaisesRegex(ValueError, "保留父版"):
                templates.prepare(source, base / "out-1")

    def test_prepare_preserves_stage_task_reference_without_media(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            data = copy.deepcopy(self.story)
            data["stage_handoff"] = {"task": "task.json"}
            source = base / "source.json"
            source.write_text(json.dumps(data))
            templates.prepare(source, base / "out")
            brief = templates.read(base / "out/brief.json")
            self.assertEqual(brief["stage_handoff"], {"task": str((base / "task.json").resolve())})
            before = (base / "out/brief.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "不得重复 prepare"):
                templates.prepare(source, base / "out")
            self.assertEqual((base / "out/brief.json").read_bytes(), before)
            self.assertFalse(list(base.rglob("*.mp4")))

    def test_bad_camera_missing_causality_and_declared_defects_are_blocked(self):
        for mutate in (
            lambda d: d["camera"][1].update(t=0),
            lambda d: d["camera"][1].update(zoom=2),
            lambda d: d["scenes"][0].update(action=""),
            lambda d: d["scenes"][1].update(start=3),
        ):
            data = copy.deepcopy(self.story)
            mutate(data)
            with self.assertRaises(ValueError):
                templates.validate_paperink(data)
        brief = {"width": 1280, "height": 720, "template": {"id": "paper-ink-landscape", "version": "1",
                 "direction": self.story["direction"], "known_unresolved_issues": ["脚步滑动"]},
                 "shots": [{"kind": "code", "engine": "vibe", "sceneAsset": "scene"}]}
        with self.assertRaisesRegex(ValueError, "已知未修复"):
            templates.check_binding(brief)

    def test_actual_make_rejects_unbound_new_film_before_creating_project(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "brief.json"
            path.write_text(json.dumps({"id": "unbound-template-regression-fixture"}))
            result = subprocess.run([sys.executable, ROOT / "scripts/studio.py", "--mode", "production", "make", path],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("绑定已登记风格模板", result.stderr)
            self.assertFalse((ROOT / "works/unbound-template-regression-fixture").exists())

    def test_archived_styles_are_rejected_by_route_prepare_and_actual_make(self):
        result = templates.match("paper-cut-story", "9:16")
        self.assertFalse(result["engineering_candidates"])
        self.assertEqual(result["rejected"][0]["replacement"], "object-assembly")
        self.assertFalse(result["rejected"][0]["replacement_is_compatibility_claim"])
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "story.json"
            source.write_text(json.dumps({"template": "paper-cut-story"}))
            with self.assertRaisesRegex(ValueError, "已归档"):
                templates.prepare(source, base / "out")
            self.assertFalse((base / "out").exists())
            brief = base / "brief.json"
            brief.write_text(json.dumps({"id": "archived-template-regression-fixture",
                                         "template": {"id": "paper-cut-story", "version": "1"}}))
            result = subprocess.run([sys.executable, ROOT / "scripts/studio.py", "--mode", "production", "make", brief],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("模板已归档", result.stderr)
            self.assertFalse((ROOT / "works/archived-template-regression-fixture").exists())


if __name__ == "__main__":
    unittest.main()
