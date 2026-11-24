"""Real CLI checks in a disposable workspace; no media or model execution."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import importlib.util

ROOT = Path(__file__).resolve().parents[1]


class StageHandoffTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / "scripts", self.root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        (self.root / "docs").mkdir()
        shutil.copy2(ROOT / "docs/capability-index.json", self.root / "docs")
        (self.root / ".codex").mkdir()
        (self.root / ".codex/config.toml").write_text('model="gpt-6.1-sol"\nmodel_provider="openai"\n')
        self.asset = self.root / "scene.js"
        self.asset.write_text("export const scene = 1;\n")
        self.brief = {"id": "isolated", "route": "code", "request": "已有文案不重写", "script": "原文",
                      "title": "隔离入口测试", "width": 1280, "height": 720, "fps": 30,
                      "audio": {"mode": "silent"}, "inputs": [{"id": "scene", "kind": "scene", "path": "scene.js",
                      "sha256": hashlib.sha256(self.asset.read_bytes()).hexdigest()}],
                      "shots": [{"id": "one", "kind": "code", "frames": 30, "accent": "#ffffff",
                                 "sceneAsset": "scene", "cues": []}],
                      "stage_handoff": {"task": str(self.root / "task.json")}}
        self.task = {"action": "plan", "request": "只检查交接", "project": "isolated", "brief": "brief.json",
                     "stages": [
                         {"id": "content", "needs": [], "fields": ["/request", "/script", "/title"]},
                         {"id": "setup", "needs": [], "fields": ["/id", "/route", "/width", "/height", "/fps"]},
                         {"id": "picture", "needs": ["content", "setup"], "fields": ["/shots", "/inputs"],
                          "artifacts": ["scene.js"]},
                         {"id": "audio", "needs": ["content"], "fields": ["/audio"]}]}
        self.write("brief.json", self.brief)
        self.write("task.json", self.task)

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False))
        return path

    def test_event_dependency_cannot_be_omitted_from_picture_stage(self):
        self.brief['requirements'] = [{'id': 'payoff', 'text': '可见结果'}]
        self.brief['content_adaptation'] = {'units': [{'id': 'event', 'shot': 'one', 'requirements': ['payoff']}]}
        self.task['stages'][0]['fields'] += ['/requirements', '/content_adaptation']
        self.task['stages'][2]['needs'] = ['setup']
        self.write('brief.json', self.brief); self.write('task.json', self.task)
        run = subprocess.run([sys.executable, str(self.root / 'scripts/studio.py'), 'workflow',
                              str(self.root / 'task.json')], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn('事件依赖', run.stderr)
        self.task['stages'][2]['needs'].append('content')
        self.write('task.json', self.task)
        report = self.cli('workflow', self.root / 'task.json')
        self.assertIn('stage_handoff', report)

    def cli(self, *args, error=None):
        result = subprocess.run([sys.executable, str(self.root / "scripts/studio.py"), *map(str, args)],
                                cwd=self.root, text=True, capture_output=True, timeout=15)
        if error:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn(error, result.stderr)
            return result.stderr
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def confirm_all(self):
        for stage in ("content", "setup", "picture", "audio"):
            self.cli("workflow", self.root / "task.json", "--confirm-stage", stage)

    def test_checkpoint_reuse_is_idempotent_and_consumes_actual_outputs(self):
        self.confirm_all()
        before = (self.root / "task.json").read_bytes()
        report = self.cli("workflow", self.root / "task.json", "--confirm-stage", "picture")
        self.assertEqual((self.root / "task.json").read_bytes(), before)
        self.assertEqual(report["stage_handoff"]["reusable"], ["content", "setup", "picture", "audio"])
        self.assertEqual(report["stage_handoff"]["next_stages"], [])
        plan = self.cli("plan", self.root / "brief.json")
        self.assertEqual(plan["stage_handoff"]["status"], "ready")
        self.assertFalse((self.root / "works").exists())

    def test_picture_change_keeps_upstream_and_audio_then_requires_explicit_reopen(self):
        self.confirm_all()
        frozen = json.loads((self.root / "task.json").read_text())
        self.asset.write_text("export const scene = 2;\n")
        self.brief["inputs"][0]["sha256"] = hashlib.sha256(self.asset.read_bytes()).hexdigest()
        self.write("brief.json", self.brief)
        report = self.cli("workflow", self.root / "task.json")
        self.assertEqual(report["stage_handoff"]["reusable"], ["content", "setup", "audio"])
        self.assertEqual(report["stage_handoff"]["next_stages"], ["picture"])
        self.cli("workflow", self.root / "task.json", "--confirm-stage", "picture", error="reopen-stage")
        self.cli("plan", self.root / "brief.json", error="picture")
        self.cli("--mode", "production", "make", self.root / "brief.json", error="picture")
        self.assertFalse((self.root / "works").exists())
        evidence = self.root / "issue.txt"
        evidence.write_text("测试反例：只修改当前画面源文件，文案和音频不变")
        self.cli("workflow", self.root / "task.json", "--reopen-stage", "picture", "--reason", "修画面",
                 "--evidence", evidence)
        self.cli("workflow", self.root / "task.json", "--confirm-stage", "picture")
        after = json.loads((self.root / "task.json").read_text())
        for index in (0, 1, 3):
            self.assertEqual(after["stages"][index], frozen["stages"][index])
        self.assertEqual(len(after["stages"][2]["history"]), 1)
        self.cli("plan", self.root / "brief.json")

    def test_dependency_change_invalidates_only_descendants(self):
        self.confirm_all()
        self.brief["script"] = "用户纠正后的原文"
        self.write("brief.json", self.brief)
        report = self.cli("workflow", self.root / "task.json")["stage_handoff"]
        self.assertEqual(report["reusable"], ["setup"])
        self.assertEqual(report["next_stages"], ["content"])
        self.cli("workflow", self.root / "task.json", "--confirm-stage", "audio", error="依赖")

    def test_consumed_production_recipe_change_invalidates_content_and_descendants(self):
        recipe = self.root / 'knowledge-song-recipe.md'
        shutil.copy2(ROOT / 'docs/制作配方/视频制作工作流.md', recipe)
        self.task['stages'][0]['artifacts'] = [str(recipe)]
        self.write('task.json', self.task)
        self.confirm_all()
        report = self.cli('workflow', self.root / 'task.json')['stage_handoff']
        self.assertIn('content', report['reusable'])
        recipe.write_text(recipe.read_text() + '\n测试：方法依赖发生实质修改。\n')
        changed = self.cli('workflow', self.root / 'task.json')['stage_handoff']
        self.assertEqual(changed['reusable'], ['setup'])
        self.assertEqual(changed['next_stages'], ['content'])
        self.cli('plan', self.root / 'brief.json', error='content')
        self.assertFalse((self.root / 'works').exists())

    def test_incomplete_coverage_wrong_project_and_cycle_rejected(self):
        self.confirm_all()
        self.brief["voice"] = "unowned new field"
        self.write("brief.json", self.brief)
        self.cli("plan", self.root / "brief.json", error="未归属")
        self.brief.pop("voice")
        self.brief["id"] = "other-project"
        self.write("brief.json", self.brief)
        self.cli("plan", self.root / "brief.json", error="作品")
        self.write("brief.json", {**self.brief, "id": "isolated"})
        self.task["stages"][0]["needs"] = ["picture"]
        self.write("task.json", self.task)
        self.cli("workflow", self.root / "task.json", error="循环")

    def test_missing_artifact_and_changed_definition_cannot_reuse(self):
        self.confirm_all()
        task = json.loads((self.root / "task.json").read_text())
        task["stages"][2]["needs"] = ["setup"]
        self.write("task.json", task)
        changed = self.cli("workflow", self.root / "task.json")["stage_handoff"]
        self.assertNotIn("picture", changed["reusable"])
        self.asset.unlink()
        result = self.cli("workflow", self.root / "task.json")["stage_handoff"]
        self.assertNotIn("picture", result["reusable"])
        self.cli("plan", self.root / "brief.json", error="picture")

    def test_ambiguous_stage_actions_do_not_write_task(self):
        before = (self.root / "task.json").read_bytes()
        self.cli("workflow", self.root / "task.json", "--stage", "content", "--confirm-stage", "content",
                 error="不能与确认")
        self.cli("workflow", self.root / "task.json", "--confirm-stage", "content", "--reason", "unused",
                 error="仅用于 reopen-stage")
        self.assertEqual((self.root / "task.json").read_bytes(), before)

    def test_target_context_and_two_shot_dependency_scope(self):
        self.brief["shots"].append({**self.brief["shots"][0], "id": "two"})
        self.task["stages"][2]["fields"] = ["/shots/@one", "/inputs"]
        self.task["stages"].append({"id": "picture-two", "needs": ["content", "setup"], "fields": ["/shots/@two"]})
        self.write("brief.json", self.brief)
        self.write("task.json", self.task)
        self.confirm_all()
        self.cli("workflow", self.root / "task.json", "--confirm-stage", "picture-two")
        self.brief["shots"][0]["accent"] = "#112233"
        self.write("brief.json", self.brief)
        report = self.cli("workflow", self.root / "task.json", "--stage", "picture")
        self.assertEqual(report["decision"], "work_on_this_stage")
        self.assertEqual(set(report["inputs"]), {"content", "setup"})
        self.assertIn("picture-two", report["preserve_without_replanning"])
        reused = self.cli("workflow", self.root / "task.json", "--stage", "picture-two")
        self.assertEqual(reused["decision"], "reuse")

    def test_resume_rechecks_stale_handoff_before_render_or_new_version(self):
        self.confirm_all()
        project = self.root / "works/isolated"
        project.mkdir(parents=True)
        pending = self.write("works/isolated/pending.json", {"parent": None, "version": "v0001", "brief": self.brief})
        before = pending.read_bytes()
        self.asset.write_text("changed after prepared submit")
        self.cli("--mode", "production", "resume", "isolated", error="picture")
        self.assertEqual(pending.read_bytes(), before)
        self.assertFalse((project / "versions").exists())

    def test_material_relocation_does_not_invalidate_confirmed_content(self):
        self.confirm_all()
        shutil.copy2(self.asset, self.root / "imported-scene.js")
        self.brief["inputs"][0]["path"] = "imported-scene.js"
        self.brief["inputs"][0]["sourcePath"] = str(self.asset)
        self.brief["shots"][0]["captionTiming"] = []
        self.write("brief.json", self.brief)
        self.assertEqual(self.cli("plan", self.root / "brief.json")["stage_handoff"]["status"], "ready")

    def test_picture_patch_checks_changed_fields_without_resetting_upstream(self):
        self.confirm_all()
        sys.path.insert(0, str(self.root / "scripts"))
        self.addCleanup(lambda: sys.path.remove(str(self.root / "scripts")))
        spec = importlib.util.spec_from_file_location("isolated_studio", self.root / "scripts/studio.py")
        studio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(studio)
        version = self.root / "works/isolated/versions/v0001"
        version.mkdir(parents=True)
        self.write("works/isolated/versions/v0001/brief.json", self.brief)
        shutil.copy2(self.asset, self.root / "works/isolated/scene.js")
        change = {"base": "v0001", "shot": "one", "visual": {"accent": "#112233"}}
        with self.assertRaisesRegex(ValueError, "picture"):
            studio.picture_brief(version, change, preview_only=True)
        self.brief["shots"][0]["accent"] = "#112233"
        self.write("brief.json", self.brief)
        issue = self.root / "issue.txt"
        issue.write_text("隔离反例：仅画面颜色修改")
        self.cli("workflow", self.root / "task.json", "--reopen-stage", "picture", "--reason", "局部画面", "--evidence", issue)
        self.cli("workflow", self.root / "task.json", "--confirm-stage", "picture")
        result = studio.picture_brief(version, change, preview_only=True)
        self.assertEqual(result["script"], "原文")
        self.assertEqual(result["audio"], {"mode": "silent"})
        self.assertEqual(result["shots"][0]["accent"], "#112233")
        stripped = copy.deepcopy(result)
        stripped.pop("stage_handoff")
        with self.assertRaisesRegex(ValueError, "不得移除"):
            studio.build(version.parent.parent, stripped, version)

    def test_new_self_media_requires_handoff_and_repeat_prepare_cannot_overwrite(self):
        unmanaged = {"id": "new-self-media", "route": "editor", "purpose": "self-media"}
        self.cli("--mode", "production", "make", self.write("unmanaged.json", unmanaged), error="须绑定 stage_handoff")
        self.assertFalse((self.root / "works").exists())
        self.confirm_all()
        before = (self.root / "brief.json").read_bytes()
        source = self.write("source.json", {"template": "unused"})
        self.cli("--mode", "development", "templates", "prepare", source, "--to", self.root,
                 error="不得重复 prepare")
        self.assertEqual((self.root / "brief.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
