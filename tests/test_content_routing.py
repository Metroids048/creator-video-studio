"""Regressions for the user's full-copy routing and production qualification."""
import copy
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import video_templates as templates


class ContentRoutingTest(unittest.TestCase):
    def test_explicit_research_profile_survives_framework_topic_and_deferral(self):
        request_path = ROOT / "docs/research/2026-11-15-原片源码与工作室复盘/本轮研究请求.json"
        original = json.loads(request_path.read_text())["request"]
        cases = [
            (original, "research", "research", "codex"),
            (original, None, "framework", "phrase_hint"),
            ("只研究项目工作流，先不制作视频", "framework", "research", "phrase_hint"),
            ("只搭框架，先不制作视频", "research", "framework", "phrase_hint"),
        ]
        for request, profile, expected, selection in cases:
            with self.subTest(profile=profile, request=request[:40]):
                command = [sys.executable, str(ROOT / "scripts/studio.py"), "intent", request]
                if profile:
                    command += ["--profile", profile]
                run = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                result = json.loads(run.stdout)
                self.assertEqual(result["profile"], expected)
                self.assertEqual(result["selection"], selection)
                self.assertFalse(result["render_started"])
                self.assertFalse(result["execution_authorized_by_route"])

    def test_negative_style_constraint_preserves_lyrics_fit_and_receipt(self):
        script = "歌曲演唱第一句歌词：旧日的朋友，你还记得吗？画面从照片走进旧街；副歌举杯，最后两个人握住彼此的手。"
        topic = "把这首歌做成歌词意象MV"
        base = templates.match(topic, script=script)
        for negative in ("不做乐谱", "不要乐谱", "不用乐谱", "不需要乐谱"):
            with self.subTest(negative=negative):
                request = topic + "，" + negative
                result = templates.match(request, script=script)
                self.assertEqual(result["engineering_candidates"], base["engineering_candidates"])
                self.assertEqual(result["research_references"], base["research_references"])
                self.assertFalse(result["candidates"])
                receipt = templates.selection_receipt(request, script, "16:9", "studio-watercolor-music", "engineering_validation")
                templates.validate_selection(receipt, request, script, "16:9", "studio-watercolor-music")
        result = templates.match("不要歌词MV，而是乐谱光点", script="钢琴五线谱音符逐个亮起。")
        self.assertEqual(result["engineering_candidates"][0]["id"], "studio-music-score")
        self.assertFalse(templates.match("不要乐谱")["engineering_candidates"])

    def test_explicitly_excluded_style_cannot_reenter_through_full_copy(self):
        script = "歌曲演唱第一句歌词：旧日的朋友，你还记得吗？副歌用怀念与重逢的画面表达词义。"
        for excluded in ("不要水彩", "不采用studio-watercolor-music", "不用水彩模板"):
            result = templates.match("歌词意象MV，" + excluded, script=script)
            self.assertNotIn("studio-watercolor-music", [x["id"] for x in result["engineering_candidates"]])
            row = next(x for x in result["rejected"] if x["id"] == "studio-watercolor-music")
            self.assertIn("明确排除", row["reason"])
        # Quoted lyrics are content, not an instruction to prohibit their visual style.
        result = templates.match("歌词意象MV", script='歌曲演唱“不要水彩”，副歌画面逐句表达词义。')
        self.assertEqual(result["engineering_candidates"][0]["id"], "studio-watercolor-music")

    def test_negative_constraint_cannot_hide_positive_unsupported_full_copy(self):
        result = templates.match("object-assembly 台灯装配，不做多人对话", "9:16",
                                 script="台灯底座装配，但三个演员随后进行多人对话。")
        rejected = next(row for row in result["rejected"] if row["id"] == "object-assembly")
        self.assertIn("多人对话", rejected["evidence"])

    def test_real_intent_does_not_defer_creation_for_unwanted_score(self):
        run = subprocess.run([sys.executable, ROOT / "scripts/studio.py", "intent",
                              "做一条歌词意象MV，不做乐谱"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result["profile"], "mv-silent")
        self.assertEqual(result["deferred_actions"], [])
        self.assertFalse(result["execution_authorized_by_route"])
        run = subprocess.run([sys.executable, ROOT / "scripts/studio.py", "intent",
                              "只整理模板，先不制作视频，不渲染"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(json.loads(run.stdout)["deferred_actions"])

    def test_gallery_routes_full_copy_through_the_production_matcher(self):
        process = subprocess.Popen([sys.executable, ROOT / "scripts/studio.py", "templates", "preview"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            url = json.loads(process.stdout.readline())["url"].split("/templates/")[0]
            def post(payload):
                request = Request(url + "/api/templates/match", json.dumps(payload).encode(),
                                  {"Content-Type": "application/json"}, method="POST")
                with urlopen(request, timeout=10) as response:
                    return json.load(response)
            script = "歌曲演唱，逐句歌词变画面，副歌重逢。"
            result = post({"topic": "往日", "script": script, "format": "16:9"})
            self.assertEqual(result, templates.match("往日", script=script))
            self.assertEqual(result["engineering_candidates"][0]["id"], "studio-watercolor-music")
            self.assertFalse(result["candidates"])
            topic = "做成歌词意象MV，不做乐谱"
            result = post({"topic": topic, "script": script, "format": "16:9"})
            self.assertEqual(result, templates.match(topic, script=script))
            self.assertEqual(result["engineering_candidates"][0]["id"], "studio-watercolor-music")
            with self.assertRaises(HTTPError) as caught:
                post({"topic": "往日"})
            self.assertEqual(caught.exception.code, 400)
        finally:
            process.terminate()
            process.communicate(timeout=10)

    def test_full_copy_changes_fit_and_production_does_not_claim_market_success(self):
        result = templates.match("一个数字", script="九个人各赚10元，一个人赚100元。平均数变成19，中位数仍是10。把十个人逐个摆开，比较两个位置。")
        self.assertEqual(result["engineering_candidates"][0]["id"], "lanshu-v1-editorial")
        self.assertFalse(result["candidates"])
        self.assertEqual(result["next"], "benchmark_gap")
        self.assertTrue(result["script_sha256"])

    def test_lyrics_are_not_score_and_form_gaps_do_not_fall_back(self):
        result = templates.match("往日", script="歌曲演唱第一句歌词：旧日的朋友，你还记得吗？画面从照片走进旧街；副歌举杯，最后两个人握住彼此的手。")
        self.assertEqual(result["engineering_candidates"][0]["id"], "studio-watercolor-music")
        self.assertNotIn("studio-music-score", [x["id"] for x in result["engineering_candidates"]])
        self.assertFalse(templates.match("法庭真人长对白", script="三个演员连续争吵十分钟")["engineering_candidates"])
        self.assertFalse(templates.match("若卿的国风歌词道具", script="戏文在卷轴与折扇间转场")["engineering_candidates"])

    def test_receipt_is_consumed_by_prepare_and_rejects_changed_input(self):
        script = "旅人沿着山路行走，走到断桥前停下，转身发现另一条路径，绕过障碍到达山顶。"
        receipt = templates.selection_receipt("山路", script, "16:9", "paper-ink-landscape", "engineering_validation")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            story = templates.read(ROOT / "templates/paper-ink-landscape/v1/example.json")
            story.update(topic="山路", script=script, routing=receipt)
            source = base / "story.json"
            source.write_text(json.dumps(story, ensure_ascii=False))
            report = templates.prepare(source, base / "prepared", require_selection=True)
            brief = templates.read(report["brief"])
            self.assertEqual(brief["script"], script)
            templates.check_binding(brief, require_selection=True)
            task = base / "workflow.json"
            task.write_text(json.dumps({"action": "create", "route": "code", "request": "一个故事",
                                        "brief": "prepared/brief.json", "routing_purpose": "engineering_validation"}))
            run = subprocess.run([sys.executable, ROOT / "scripts/studio.py", "--mode", "production",
                                  "workflow", str(task)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            routed = json.loads(run.stdout)["template_route"]
            self.assertEqual(routed["script_sha256"], templates.text_sha(script))
            self.assertEqual(routed["engineering_candidates"][0]["id"], "paper-ink-landscape")
            brief["script"] += "现在换成歌曲。"
            with self.assertRaisesRegex(ValueError, "路由.*输入"):
                templates.check_binding(brief, require_selection=True)

    def test_actual_make_rejects_old_prepared_brief_before_creating_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief = json.loads((ROOT / "works/assembly-lamp-1113/versions/v0005/brief.json").read_text())
            brief["id"] = "routing-no-receipt-test"
            brief["template"].pop("selection", None)
            path = Path(tmp) / "brief.json"
            path.write_text(json.dumps(brief))
            run = subprocess.run([sys.executable, ROOT / "scripts/studio.py", "--mode", "production", "make", str(path)], capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("路由", run.stderr)
            self.assertFalse((ROOT / "works/routing-no-receipt-test").exists())

    def test_production_receipt_cannot_promote_unqualified_branch(self):
        with self.assertRaisesRegex(ValueError, "双对标"):
            templates.selection_receipt("歌词MV", "歌曲演唱，逐句歌词变画面，副歌重逢。", "16:9", "studio-watercolor-music", "production")

    def test_native_project_cannot_consume_a_different_copy(self):
        script = "歌曲演唱，逐句歌词变画面，副歌重逢。"
        receipt = templates.selection_receipt("歌词MV", script, "16:9", "studio-watercolor-music", "engineering_validation")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "native").mkdir()
            (base / "native/project.json").write_text(json.dumps({"content_promise": "旧版器乐动画"}))
            source = base / "story.json"
            source.write_text(json.dumps({"template": "studio-watercolor-music", "topic": "歌词MV",
                                          "script": script, "routing": receipt, "project": "native"}))
            with self.assertRaisesRegex(ValueError, "工程内容与全文"):
                templates.prepare(source, base / "prepared", require_selection=True)
            self.assertFalse((base / "prepared").exists())

    def test_source_file_change_invalidates_benchmark_claim(self):
        row = templates.read(ROOT / "templates/routing.json")["benchmarks"]["studio-watercolor-music"][0]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            original = {**row, "published": date.today().isoformat(), "observer_kind": "human",
                        "observation_method": "human_normal_speed", "limitations": [],
                        "note": "synthetic fixture, no real observation"}
            (base / "source.json").write_text(json.dumps({"sources": [original]}))
            row = {**row, "evidence": "source.json", "evidence_sha256": templates.sha(base / "source.json")}
            config = {"threshold_likes": 200000, "benchmarks": {"example": [row]}}
            self.assertEqual(templates.benchmark_status("example", base, config)["confirmed_count"], 1)
            (base / "source.json").write_text("changed capture")
            self.assertEqual(templates.benchmark_status("example", base, config)["confirmed_count"], 0)

    def test_stale_profile_and_changed_selection_are_rejected(self):
        script = "旅人沿山路行走，遇到断桥停下，换一条路径到达山顶。"
        receipt = templates.selection_receipt("山路", script, "16:9", "paper-ink-landscape", "engineering_validation")
        changed = copy.deepcopy(receipt)
        changed["routing_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "路由.*版本"):
            templates.validate_selection(changed, "山路", script, "16:9", "paper-ink-landscape")
        with self.assertRaisesRegex(ValueError, "路由.*模板"):
            templates.validate_selection(receipt, "山路", script, "16:9", "object-assembly")


if __name__ == "__main__":
    unittest.main()
