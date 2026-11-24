"""Exercise studio routes with isolated state and existing frozen packages."""
import hashlib
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
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from native_bundle import pack, scan


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False))
    return path


class FoundationTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        (self.root / "scripts").mkdir()
        for name in ("studio.py", "stage_handoff.py", "knowledge_song.py", "production_method.py",
                     "representative_review.py",
                     "content_adaptation.py", "video_review.py", "native_bundle.py", "workflow.py",
                     "lanshu.py", "intent.py", "nook.py", "vibe.py", "video_templates.py",
                     "event_templates.py", "photo_templates.py"):
            shutil.copy2(ROOT / "scripts" / name, self.root / "scripts" / name)
        shutil.copytree(ROOT / "templates", self.root / "templates")
        (self.root / "docs").mkdir()
        shutil.copy2(ROOT / "docs" / "capability-index.json", self.root / "docs")
        (self.root / ".codex").mkdir()
        (self.root / ".codex" / "config.toml").write_text('model = "gpt-6.1-sol"\nmodel_provider = "openai"\n')
        (self.root / "adapters").mkdir()

    def run_studio(self, *args, error=None, status=1):
        run = subprocess.run([sys.executable, self.root / "scripts" / "studio.py", *map(str, args)],
                             cwd=self.root, capture_output=True, text=True, timeout=30)
        if error:
            self.assertEqual(run.returncode, status, run.stderr)
            self.assertIn(error, run.stderr)
            return
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout) if run.stdout.startswith("{") else run.stdout.strip()

    def node(self):
        node = ROOT / ".studio" / "bin" / "node"
        if not node.is_file():
            self.skipTest("需要工作室固定 Node")
        local_bin = self.root / ".studio" / "bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        (local_bin / "node").symlink_to(node)

    def test_all_original_archives_import_with_same_bytes_and_no_current(self):
        for delivery, critical in {
            "focus-v0001": "native/timeline.json",
            "focus-restored-v0001": "native/timeline.json",
            "unsent-v0002": "shots/01-draft/film/scene.js",
            "last-desk-v0001": "shots/02-memory/media.json",
        }.items():
            archive = ROOT / "deliveries" / delivery / "editable.zip"
            if not archive.exists():
                self.skipTest(f"缺少冻结包 {delivery}")
            planned = self.run_studio("inspect-bundle", archive)
            if delivery == "focus-v0001":
                self.assertFalse((self.root / "works").exists())
            self.assertEqual(planned["integrity"], "legacy_crc_and_input_hashes")
            result = self.run_studio("--mode", "recovery", "import-native", delivery, archive)
            self.assertFalse(result["reused"])
            tree = Path(result["path"])
            with zipfile.ZipFile(archive) as z:
                self.assertEqual((tree / critical).read_bytes(), z.read(critical))
                self.assertEqual({p.relative_to(tree).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in tree.rglob("*") if p.is_file()}, planned["members"])
            status = self.run_studio("status", delivery)
            self.assertIsNone(status["current"])
            self.assertIsNone(status["pending"])
            self.assertEqual(status["native_import"]["archive_sha256"], planned["archive_sha256"])
            self.assertTrue(self.run_studio("--mode", "recovery", "import-native", delivery, archive)["reused"])
            (tree / critical).write_text("local modified copy")
            self.run_studio("--mode", "recovery", "import-native", delivery, archive, error="与回执不符")

    def test_spoken_intents_route_without_authorizing_or_creating_work(self):
        cases = (
            ("你先不着急做视频，把项目框架和路由补齐", "framework", "framework"),
            ("仅做研究，参考这个情绪短片", "research", "research"),
            ("我只有一个主题，你来定表现方式", "theme", "research"),
            ("帮我拆解一个参考，借鉴表达方法再原创", "reference", "reference"),
            ("把录屏、图片和文字剪一下，保留真实操作", "edit", "edit"),
            ("想做歌词 MV，先无旁白", "mv-silent", "vibe"),
            ("用代码画面、录屏和生成镜头混用", "mixed", "external"),
            ("只改中间画面，锁住其他镜头和音轨", "revision", "review"),
            ("把这个编辑过的原生工程原样恢复", "restore-native", "restore"),
            ("之前断流，先查上次任务的回执", "resume-unknown", "restore"),
            ("做一段水彩绘本动画", "storybook", "storybook"),
            ("用花叔艺术动效来拆镜头", "art-motion", "art"),
            ("参考 Remotion 的字幕动效做一份方案", "reference", "mg"),
            ("帮我规划 MG 字幕动效", "motion-graphics", "mg"),
            ("检查AVS的Episode", "edit", "edit"),
            ("展示商品功能，做一段电商广告片", "commerce", "mg"),
            ("用图生视频做一段镜头", "generated", "external"),
            ("导出当前版本的 ZIP", "delivery", "delivery"),
        )
        for request, profile, pack in cases:
            with self.subTest(request=request):
                result = self.run_studio("intent", request)
                self.assertEqual(result["profile"], profile)
                self.assertIn(pack, result["packs"])
                self.assertTrue(result["packs"][pack]["missing"])
                for key in ("render_started", "model_request_sent", "execution_authorized_by_route"):
                    self.assertFalse(result[key])
        self.assertEqual(self.run_studio("intent", "仅做研究", "--profile", "edit")["profile"],
                         "research")
        self.assertEqual(self.run_studio("intent", "先不做框架，只研究参考片")["profile"], "research")
        research = self.run_studio("intent", "只研究这支绘本动画参考，暂不制作")
        self.assertEqual(research["profile"], "research")
        self.assertEqual(set(research["packs"]), {"research", "reference", "storybook", "visual-design"})
        self.assertEqual(set(research["routes"]), {"research"})
        self.assertEqual(self.run_studio("intent", "先把项目底座搭好，不急着做",
                                         "--profile", "theme")["profile"], "framework")
        self.assertEqual(self.run_studio("intent", "这个怎么样")["selection"], "needs_codex_scope")
        self.assertEqual(self.run_studio("intent", "这个怎么样", "--profile", "reference")["selection"],
                         "codex")
        self.assertFalse((self.root / ".studio").exists())
        self.assertFalse((self.root / "works").exists())

    def test_editor_plan_uses_native_operations_without_preparing_media(self):
        self.node()
        (self.root / "runtime").mkdir()
        (self.root / "runtime/editor").symlink_to(ROOT / "runtime/editor", target_is_directory=True)
        shutil.copy2(ROOT / "adapters/native-editor.mjs", self.root / "adapters/native-editor.mjs")
        (self.root / ".studio/bin/ffprobe").symlink_to(ROOT / ".studio/bin/ffprobe")
        brief = json.loads((ROOT / "examples/briefs/focus.json").read_text())
        for item in brief["inputs"]:
            item["path"] = str((ROOT / "examples/briefs" / item["path"]).resolve())
        path = write(self.root / "brief.json", brief)
        result = self.run_studio("plan", path)
        self.assertTrue(result["editor_timeline"]["valid"])
        self.assertEqual(result["editor_timeline"]["frames"], 340)
        self.assertFalse(result["editor_timeline"]["media_prepared"])
        self.assertFalse(result["render_started"])
        guard = self.root / "read-only-guard.mjs"
        guard.write_text("""import fs from 'node:fs';
import cp from 'node:child_process';
import {syncBuiltinESMExports} from 'node:module';
const sensitive = value => /(?:\\.env|\\.local\\.env)$/.test(String(value));
for (const [target, key] of [[fs, 'readFileSync'], [fs.promises, 'readFile']]) {
  const original = target[key];
  target[key] = function(file, ...args) {
    if (sensitive(file)) throw Error('must not load legacy credentials');
    return original.call(this, file, ...args);
  };
}
for (const key of ['writeFile', 'mkdir', 'copyFile', 'rm', 'rename']) {
  fs.promises[key] = () => { throw Error('must not write media or cache'); };
}
const original = cp.spawnSync;
cp.spawnSync = function(exe, ...args) {
  if (exe !== process.env.HYPERFRAMES_FFPROBE_PATH) throw Error('must not dispatch media production');
  return original.call(this, exe, ...args);
};
cp.spawn = () => { throw Error('must not dispatch media production'); };
syncBuiltinESMExports();
""")
        guarded = subprocess.run([ROOT / ".studio/bin/node", "--import", guard,
                                  self.root / "adapters/native-editor.mjs", "--plan", self.root],
                                 input=json.dumps(brief), cwd=self.root, capture_output=True, text=True,
                                 env={"PATH": "/usr/bin:/bin", "HYPERFRAMES_FFPROBE_PATH": str(ROOT / ".studio/bin/ffprobe")},
                                 timeout=30)
        self.assertEqual(guarded.returncode, 0, guarded.stderr)
        self.assertTrue(json.loads(guarded.stdout)["valid"])
        for operations, message in (([{"type": "unsupported"}], "不支持的剪辑操作"),
                                    ([{"type": "keep_ranges", "ranges": [{"start": 0, "end": 99999}]}], "时间范围无效"),
                                    ([{"type": "output", "width": 65, "height": 720}], "输出尺寸"),
                                    ([{"type": "audio_add", "assetId": "screen", "start": 0, "end": 10}], "没有可用声音")):
            with self.subTest(operations=operations):
                brief["operations"] = operations
                self.run_studio("plan", write(path, brief), error=message)
        brief["operations"] = [{"type": "unsupported"}]
        write(path, brief)
        handoff = write(self.root / "editor-handoff.json", {"action": "plan", "route": "editor",
                        "request": "只核对编辑清单", "brief": str(path)})
        self.run_studio("--mode", "development", "workflow", handoff, error="不支持的剪辑操作")
        self.assertFalse((self.root / "works").exists())
        self.assertFalse((self.root / "runtime/editor/.state").exists())
        self.assertEqual({p.name for p in (self.root / ".studio").iterdir()}, {"bin"})

        # The same rejection must occur before candidate creation on rebuild,
        # full-operation revisions and local continuation, all owned by build.
        spec = importlib.util.spec_from_file_location("studio_editor_guard", self.root / "scripts/studio.py")
        studio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(studio)
        project = self.root / "works" / brief["id"]
        project.mkdir(parents=True)
        brief["operations"] = [{"type": "unsupported"}]
        with patch.object(studio, "render", side_effect=AssertionError("must not render")) as render:
            with self.assertRaises(subprocess.CalledProcessError) as failure:
                studio.build(project, brief)
            self.assertIn("不支持的剪辑操作", failure.exception.stderr)
            render.assert_not_called()
        self.assertFalse((project / "pending.json").exists())
        self.assertFalse((project / "versions").exists())

    def test_nook_plan_reads_native_contract_without_executing_user_scene(self):
        scene = self.root / "scene.py"
        scene.write_text("W, H, FPS, DUR = 1280, 720, 30, 5\n"
                         "SHOTS = []\ndef render(t): pass\nraise RuntimeError('not executed')\n")
        file = write(self.root / "handoff.json", {
            "action": "plan", "request": "核对场景接口", "route": "nook", "scene": "scene.py",
        })
        result = self.run_studio("workflow", file)
        self.assertEqual(result["checks"]["scene"]["check"], "syntax_and_interface_only")
        self.assertEqual(result["stop_at"], "plan")
        self.assertFalse(result["render_started"])
        for action, mode in (("inspect", "development"), ("continue", "recovery")):
            native_task = write(self.root / "native-inspect.json", {
                "action": action, "request": "只检查原生场景，不执行", "route": "nook",
                "scene": "scene.py",
            })
            snapshot = self.run_studio("--mode", mode, "workflow", native_task)
            self.assertEqual(snapshot["checks"]["scene"]["sha256"],
                             result["checks"]["scene"]["sha256"])
            self.assertEqual(snapshot["stop_at"], "native_status")
            self.assertEqual(snapshot["checks"]["native_state"]["status"], "unknown")
            self.assertFalse(snapshot["render_started"])
            self.assertEqual(bool(snapshot["blockers"]), action == "continue" or bool(result["blockers"]))
        scene.write_text(scene.read_text() + "FONT='C:/Windows/Fonts/STHUPO.TTF'\n")
        portable = self.run_studio("workflow", file)
        self.assertEqual(portable["checks"]["scene"]["host_specific_paths"],
                         ["C:/Windows/Fonts/STHUPO.TTF"])
        self.assertEqual(portable["next"], "resolve_blockers")
        scene.write_text(scene.read_text().replace("SHOTS", "BAD"))
        self.run_studio("workflow", file, error="SHOTS")
        scene.write_text("def render(")
        self.run_studio("workflow", file, error="场景语法无效")

    def test_nook_runtime_loads_project_fonts_instead_of_windows_defaults(self):
        result = subprocess.run([sys.executable, "-B", ROOT / "scripts/nook.py", "check"],
                                cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(set(report["fonts"]), {"FONT_UI", "FONT_HAND_EN", "FONT_HAND_ZH"})
        for font in report["fonts"].values():
            self.assertTrue(Path(font["path"]).is_file())
            self.assertEqual(font["sha256"], hashlib.sha256(Path(font["path"]).read_bytes()).hexdigest())
            self.assertNotIn("Windows/Fonts", font["path"])
        self.assertEqual(report["ffmpeg"], str(ROOT / ".studio/bin/ffmpeg"))
        self.assertFalse(report["render_started"])

    def test_nook_plan_rejects_invalid_constants_without_importing_scene(self):
        scene = self.root / "scene.py"
        file = write(self.root / "handoff.json", {
            "action": "plan", "request": "核对场景参数", "route": "nook", "scene": "scene.py",
        })
        for config, shots in (("0,720,30,5", "[]"), ("1280,720,-1,5", "[]"),
                              ("1280,720,30,0", "[]"), ("1280,720,30,5", "[(6,'late')]"),
                              ("1280,720,30,5", "[(2,'b'),(1,'a')]")):
            with self.subTest(config=config, shots=shots):
                scene.write_text(f"W,H,FPS,DUR={config}\nSHOTS={shots}\n"
                                 "def render(t): pass\nraise RuntimeError('must not execute')\n")
                self.run_studio("workflow", file, error="Nook 参数")
        scene.write_text("from missing import DURATION\nW,H,FPS,DUR=1280,720,30,DURATION\n"
                         "SHOTS=[]\ndef render(t): pass\n")
        report = self.run_studio("workflow", file)
        self.assertEqual(report["checks"]["scene"]["unresolved_constants"], ["DUR"])
        self.assertEqual(report["next"], "resolve_blockers")

    def test_art_handoff_runs_pinned_spec_lint_without_media(self):
        index = json.loads((ROOT / "docs/capability-index.json").read_text())
        route = index["routes"]["art"]
        for relative in (route["entry"], route["source"], *route["files"]):
            source = ROOT / relative
            if not source.is_file():
                self.skipTest("需要固定版花叔片段校验器")
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        spec = {"grammar": "t1_3b1b", "duration": 2, "cues": [{"at": 0, "kind": "title", "text": "fixture"}]}
        spec_file = write(self.root / "spec.json", spec)
        task = {"action": "plan", "request": "核对片段结构", "route": "art", "spec": "spec.json"}
        handoff = write(self.root / "handoff.json", task)
        result = self.run_studio("workflow", handoff)
        self.assertTrue(result["checks"]["art_spec"]["valid"])
        self.assertEqual(result["next"], "native_handoff")
        self.assertFalse(result["render_started"])
        for action, mode in (("inspect", "development"), ("continue", "recovery")):
            snapshot = self.run_studio("--mode", mode, "workflow", write(handoff, {**task, "action": action}))
            self.assertEqual(snapshot["checks"]["art_assets"]["spec_sha256"],
                             result["checks"]["art_assets"]["spec_sha256"])
            self.assertEqual(snapshot["stop_at"], "native_status")
            self.assertEqual(bool(snapshot["blockers"]), action == "continue")
        task["action"] = "create"
        result = self.run_studio("--mode", "production", "workflow", write(handoff, task))
        self.assertEqual(result["next"], "resolve_blockers")
        task["action"] = "plan"
        spec["cues"][0]["frames"] = "missing-frames"
        write(spec_file, spec)
        result = self.run_studio("workflow", write(handoff, task))
        self.assertEqual(result["next"], "resolve_blockers")
        self.assertIn("帧序列", result["checks"]["art_assets"]["error"])
        frames = self.root / "frames"
        frames.mkdir()
        (frames / "01.png").write_bytes(b"existence fixture, not decoded")
        spec["cues"][0]["frames"] = "frames"
        write(spec_file, spec)
        result = self.run_studio("workflow", handoff)
        self.assertEqual(result["next"], "native_handoff")
        self.assertEqual(result["checks"]["art_assets"]["local_files"], [str(frames / "01.png")])
        spec["cues"][0].pop("frames")
        spec["cues"][0]["image"] = "https://example.invalid/unfetched.png"
        write(spec_file, spec)
        result = self.run_studio("workflow", handoff)
        self.assertEqual(result["next"], "resolve_blockers")
        self.assertEqual(result["checks"]["art_assets"]["remote_assets"],
                         ["https://example.invalid/unfetched.png"])
        spec["cues"][0].pop("image")
        spec["cues"][0]["kind"] = "unsupported"
        write(spec_file, spec)
        result = self.run_studio("workflow", write(handoff, {**task, "action": "plan"}))
        self.assertFalse(result["checks"]["art_spec"]["valid"])
        self.assertEqual(result["next"], "resolve_blockers")
        spec["grammar"] = "y4_storytime"
        spec["cues"][0]["kind"] = "title"
        spec["data"] = {"character": "neutral"}
        write(spec_file, spec)
        result = self.run_studio("workflow", handoff)
        self.assertEqual(result["next"], "resolve_blockers")
        self.assertIn("角色帧库", result["checks"]["art_assets"]["error"])
        spec["data"]["character"] = {"frames": {"rest": "frames/01.png"}}
        write(spec_file, spec)
        result = self.run_studio("workflow", handoff)
        self.assertEqual(result["next"], "native_handoff")
        self.assertFalse((self.root / "works").exists())

    def test_avs_handoff_separates_review_package_from_codex_judgment(self):
        spec = importlib.util.spec_from_file_location("avs_handoff_studio", self.root / "scripts/studio.py")
        studio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(studio)
        cases = (("analyze", "command", ["analyze"], "codex"),
                 ("content", "agent", None, "codex"),
                 ("visual-review", "command", ["visual-review"], "codex"),
                 ("creative-review", "command", ["creative-review"], "local"),
                 ("preview", "command", ["preview"], "local"),
                 ("plan", "command", ["plan"], "local"),
                 ("ingest", "command", ["ingest"], "local"))
        for stage, kind, command, expected in cases:
            with self.subTest(stage=stage):
                original = {"episode_id": "EP-FIXTURE", "status": "INGESTED", "next_action": {
                    "stage": stage, "kind": kind, "command": command, "required_artifacts": []}}
                with patch.object(studio, "run", return_value=json.dumps(original)) as runner:
                    report = studio.inspect_avs("EP-FIXTURE")
                runner.assert_called_once()
                action = report["next_action"]
                self.assertEqual(action["execution"], expected)
                self.assertTrue(action["reads"])
                for relative in action["reads"]:
                    self.assertTrue((ROOT / relative).is_file(), relative)
                self.assertNotIn("command", action)
                self.assertFalse(report["render_started"])
                if stage == "plan":
                    self.assertEqual(action["argv"], ["scripts/avs.sh", "--mode", "production", "plan", "EP-FIXTURE"])
                    self.assertEqual(action["operation"], "adopt_validated_agent_script")
                if stage == "creative-review":
                    self.assertFalse(action["actual_review_verified"])

    def test_avs_native_status_never_uses_studio_current_or_requires_project_alias(self):
        import workflow

        spec = importlib.util.spec_from_file_location("native_status_studio", self.root / "scripts/studio.py")
        studio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(studio)
        native = {"episode_id": "EP-FIXTURE", "status": "INGESTED", "next_action": {
            "execution": "codex", "stage": "analyze", "state_owner": "episode.json"}}
        for action in ("inspect", "continue", "revise", "review", "export"):
            mode = {"inspect": "development", "continue": "recovery", "export": "delivery"}.get(action, "production")
            task = write(self.root / "avs-task.json", {
                "request": "核对原生 Episode，不制作", "action": action,
                "route": "avs", "episode": "EP-FIXTURE",
            })
            with patch.object(studio, "inspect_avs", return_value=native) as reader, \
                    patch.object(studio, "inspect_project", side_effect=AssertionError("wrong state owner")):
                result = workflow.handoff(studio, task, mode)
            reader.assert_called_once_with("EP-FIXTURE")
            self.assertEqual(result["checks"]["episode"], native)
            self.assertEqual(result["stop_at"], "native_status")
            self.assertEqual(bool(result["blockers"]), action not in {"inspect", "continue"})
            self.assertFalse(result["render_started"])
        self.assertFalse((self.root / "works").exists())

    def test_native_inspection_refuses_unknown_route_and_avoids_false_studio_state(self):
        for route in ("lanshu", "nook", "art", "avs-render", "research", "external"):
            file = write(self.root / "native-task.json", {
                "action": "inspect", "request": "核对原生工程", "project": "missing", "route": route,
            })
            result = self.run_studio("workflow", file)
            self.assertTrue(result["blockers"])
            self.assertNotIn("project", result["checks"])
            self.assertFalse(result["render_started"])
        file = write(file, {"action": "inspect", "request": "核对工程", "project": "missing", "route": "typo"})
        self.run_studio("workflow", file, error="能力索引未登记路线")

    def test_avs_render_alias_review_export_and_blocked_gate_keep_native_owner(self):
        import workflow
        spec = importlib.util.spec_from_file_location("avs_alias_studio", self.root / "scripts/studio.py")
        studio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(studio)
        for action, stage, mode in (("review", "visual-review", "development"),
                                    ("review", "creative-gate", "production"),
                                    ("export", "export", "delivery")):
            native = {"next_action": {"execution": "local", "stage": stage}}
            task = write(self.root / "avs-alias.json", {"request": "只核原生交接", "action": action,
                          "route": "avs-render", "episode": "EP-FIXTURE"})
            with patch.object(studio, "inspect_avs", return_value=native), \
                    patch.object(studio, "inspect_project", side_effect=AssertionError("wrong owner")):
                result = workflow.handoff(studio, task, mode)
            self.assertEqual(result["route"], "avs")
            self.assertEqual(result["route_alias"], "avs-render")
            self.assertFalse(result["blockers"])
            self.assertFalse(result["render_started"])
        blocked = {"episode_id": "EP-FIXTURE", "status": "BLOCKED", "next_action": {
            "stage": "recovery", "kind": "input", "command": None, "required_artifacts": []}}
        with patch.object(studio, "run", side_effect=[json.dumps(blocked), json.dumps({
                "blocked": True, "blocked_stage": "creative-gate"})]) as reader:
            report = studio.inspect_avs("EP-FIXTURE")
        self.assertEqual(reader.call_count, 2)
        self.assertEqual(report["next_action"]["stage"], "creative-gate")
        self.assertEqual(report["next_action"]["writeback_argv"][3], "adopt-creative-review")
        self.assertFalse((self.root / "works").exists())

    def test_vibe_handoff_checks_native_workspace_without_running_media(self):
        native = self.root / "works/vibe-fixture"
        native.mkdir(parents=True)
        (native / "src").mkdir()
        (native / "src/config.js").write_text("throw Error('never execute');")
        (native / "studio.html").write_text("fixture")
        (native / "FILM_STATUS.md").write_text("- [ ] 未验证\n")
        task = {"action": "inspect", "request": "只检查旧 MV 工程", "route": "vibe", "project": "fixture"}
        handoff = write(self.root / "task.json", task)
        result = self.run_studio("workflow", handoff)
        self.assertEqual(result["checks"]["native_workspace"]["path"], str(native))
        self.assertTrue(result["checks"]["native_workspace"]["missing_contracts"])
        self.assertIsNone(result["checks"]["native_workspace"]["current"])
        task["action"] = "continue"
        result = self.run_studio("--mode", "recovery", "workflow", write(handoff, task))
        self.assertEqual(result["next"], "inspect_native_records")
        self.assertFalse(result["render_started"])
        self.assertFalse((native / "current.json").exists())
        before = {p.relative_to(native): p.read_bytes() for p in native.rglob('*') if p.is_file()}
        (native / "BRIEF.md").write_text("fixture")
        (native / "STORYBOARD.md").write_text("fixture")
        write(native / "style.json", {"name": "fixture"})
        result = self.run_studio("workflow", write(handoff, {**task, "action": "inspect"}))
        self.assertEqual(result["checks"]["native_workspace"]["missing_contracts"], [])
        for name, content in before.items():
            self.assertEqual((native / name).read_bytes(), content)
        (native / "src/config.js").write_text("changed")
        changed = self.run_studio("workflow", handoff)["checks"]["native_workspace"]
        self.assertNotEqual(changed["bindings"], result["checks"]["native_workspace"]["bindings"])

    def test_picture_handoff_rejects_missing_shot_and_nonvisual_edits(self):
        archive = self.code_package("picture.zip")
        self.run_studio("--mode", "recovery", "import-native", "fixture", archive)
        project = self.root / "works/fixture"
        version = project / "versions/v0001"
        version.mkdir(parents=True)
        brief = {"id": "fixture", "inputs": [], "width": 64, "height": 64, "fps": 24,
                 "audio": {"mode": "silent"},
                 "shots": [{"id": "intro", "kind": "code", "frames": 24, "accent": "#123456"}]}
        (version / "video.mp4").write_bytes(b"structural binding fixture")
        write(version / "brief.json", brief)
        write(version / "receipt.json", {"project": "fixture", "version": "v0001", "delivery": {
            p: hashlib.sha256((version / p).read_bytes()).hexdigest() for p in ("video.mp4", "brief.json")}})
        write(project / "current.json", {"version": "v0001"})
        task = {"action": "revise", "request": "只改中间画面", "project": "fixture", "version": "v0001",
                "locks": ["声音及其他镜头"], "edit_kind": "picture", "patch": "patch.json"}
        handoff = write(self.root / "task.json", task)
        patch_file = self.root / "patch.json"
        write(patch_file, {"base": "v0001", "shot": "absent", "visual": {"title": "fixture"}})
        self.run_studio("--mode", "production", "workflow", handoff, error="无指定的代码动画镜头")
        write(patch_file, {"base": "v0001", "shot": "intro", "visual": {"frames": 900}})
        self.run_studio("--mode", "production", "workflow", handoff, error="仅接受画面字段")
        write(patch_file, {"base": "v0001", "shot": "intro", "visual": {"accent": "invalid"}})
        self.run_studio("--mode", "production", "workflow", handoff, error="六位十六进制")
        write(patch_file, {"base": "v0001", "shot": "intro", "visual": {"title": "fixture"}})
        result = self.run_studio("--mode", "production", "workflow", handoff)
        self.assertEqual(result["checks"]["picture_patch"]["shot"], "intro")
        self.assertEqual(result["checks"]["patch_sha256"], hashlib.sha256(patch_file.read_bytes()).hexdigest())
        self.assertEqual(json.loads((version / "brief.json").read_text()), brief)

    def code_package(self, name, **extra):
        output = self.root / name
        with zipfile.ZipFile(output, "w") as z:
            z.writestr("brief.json", json.dumps({"id": "fixture", "shots": [{"id": "intro", "kind": "code"}]}))
            for file in ("index.html", "scene.js", "shot.js", "font.ttf"):
                z.writestr(f"shots/intro/film/{file}", file)
            for key, value in extra.items():
                z.writestr(key, value)
        return output

    def test_import_mode_and_archive_rejection(self):
        valid = self.code_package("valid.zip")
        self.run_studio("import-native", "sample", valid, error="需要显式 --mode recovery", status=2)
        self.assertFalse((self.root / "works").exists())
        for name in ("../not-a-member", "Inputs/a", ".env", "/absolute"):
            with self.subTest(name=name):
                members = {name: "fixture"}
                if name == "Inputs/a":
                    members["inputs/b"] = "case conflict"
                bad = self.code_package("bad.zip", **members)
                self.run_studio("--mode", "recovery", "import-native", "sample", bad, error="工程包")
                self.assertFalse((self.root / "works" / "sample").exists())
                self.assertEqual(list((self.root / "works").iterdir()), [])
        valid = self.code_package("valid.zip")
        self.run_studio("--mode", "recovery", "import-native", "sample", valid)
        other = self.code_package("other.zip", notes="a different bundle")
        self.run_studio("--mode", "recovery", "import-native", "sample", other, error="已绑定其他原生包")

    def test_current_bundle_manifest_detects_changed_member(self):
        original = self.code_package("fixture.zip")
        tree = self.root / "files"
        with zipfile.ZipFile(original) as z:
            for name in z.namelist():
                path = tree / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(z.read(name))
        archive = self.root / "packed.zip"
        pack(archive, ((p.relative_to(tree).as_posix(), p) for p in tree.rglob("*") if p.is_file()),
             "fixture", "v0007", "code", lambda p: hashlib.sha256(p.read_bytes()).hexdigest())
        self.assertEqual(scan(archive)["source_version"], "v0007")
        altered = self.root / "altered.zip"
        with zipfile.ZipFile(archive) as source, zipfile.ZipFile(altered, "w") as target:
            for name in source.namelist():
                target.writestr(name, b"changed" if name.endswith("/scene.js") else source.read(name))
        self.run_studio("inspect-bundle", altered, error="完整性清单与内容不符")

    def test_native_patch_preserves_locked_tracks_and_parent(self):
        archive = ROOT / "deliveries" / "focus-v0001" / "editable.zip"
        if not archive.exists():
            self.skipTest("需要冻结剪辑包")
        self.node()
        shutil.copy2(ROOT / "adapters" / "native-patch.mjs", self.root / "adapters")
        for relative in ("lib/edit/timeline.mjs", "lib/orchestration/transition-catalog.mjs",
                         "lib/creative/effects.mjs", "lib/creative/contracts.mjs"):
            source = ROOT / "runtime" / "editor" / relative
            target = self.root / "runtime" / "editor" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        result = self.run_studio("--mode", "recovery", "import-native", "edit", archive)
        path = Path(result["path"]) / "native" / "timeline.json"
        original = path.read_bytes()
        parent = json.loads(original)
        patch = {"base": "import", "timeline_sha256": hashlib.sha256(original).hexdigest(),
                 "locked": ["audio", "clips", "output"],
                 "operations": [{"type": "caption_update", "id": parent["captions"][0]["id"], "text": "修订字幕"}]}
        patch_file = write(self.root / "patch.json", patch)
        candidate = self.run_studio("native-edit-plan", "edit", patch_file)
        self.assertEqual(candidate["changed"], ["captions"])
        self.assertEqual(candidate["timeline"]["audio"], parent["audio"])
        self.assertEqual(candidate["timeline"]["clips"], parent["clips"])
        self.assertEqual(path.read_bytes(), original)
        handoff_file = write(self.root / "handoff.json", {"action": "revise", "request": "只改字幕，锁定声音和画面",
            "project": "edit", "version": "import", "locks": ["原声音与画面"], "locked": ["audio", "clips"],
            "edit_kind": "native", "patch": "patch.json"})
        result_handoff = self.run_studio("--mode", "production", "workflow", handoff_file)
        self.assertEqual(result_handoff["checks"]["native_patch"], ["captions"])
        self.assertFalse(result_handoff["render_started"])
        unlocked = {**patch, "locked": ["output"]}
        write(patch_file, unlocked)
        self.run_studio("--mode", "production", "workflow", handoff_file,
                        error="补丁遗漏交接单锁定轨道")
        write(patch_file, patch)
        handoff = json.loads(handoff_file.read_text())
        handoff.pop("locked")
        self.run_studio("--mode", "production", "workflow", write(handoff_file, handoff),
                        error="锁定项映射为 locked 轨道")
        version = self.root / "works" / "edit" / "versions" / "v0001"
        shutil.copytree(Path(result["path"]), version)
        brief = json.loads((version / "brief.json").read_text())
        brief["id"] = "edit"
        write(version / "brief.json", brief)
        package_files = [(file.relative_to(version).as_posix(), file) for file in version.rglob("*")
                         if file.is_file() and file.name not in {"OPEN.md", "studio-bundle.json"}]
        pack(version / "editable.zip", package_files, "edit", "v0001", "editor",
             lambda file: hashlib.sha256(file.read_bytes()).hexdigest())
        (version / "video.mp4").write_bytes(b"binding fixture, not a rendered video")
        write(version / "receipt.json", {"project": "edit", "version": "v0001", "delivery": {
            name: hashlib.sha256((version / name).read_bytes()).hexdigest()
            for name in ("video.mp4", "editable.zip", "brief.json")}})
        version_patch = {**patch, "base": "v0001"}
        self.run_studio("native-edit-plan", "edit", write(patch_file, version_patch))
        changed_parent = json.loads(original)
        changed_parent["captions"][0]["text"] = "父版目录被手工修改"
        changed = write(version / "native" / "timeline.json", changed_parent)
        version_patch["timeline_sha256"] = hashlib.sha256(changed.read_bytes()).hexdigest()
        self.run_studio("native-edit-plan", "edit", write(patch_file, version_patch), error="原生文件与工程包不符")
        patch["locked"].append("captions")
        self.run_studio("native-edit-plan", "edit", write(patch_file, patch), error="改变了锁定轨道")
        patch["timeline_sha256"] = "0" * 64
        self.run_studio("native-edit-plan", "edit", write(patch_file, patch), error="时间线哈希不符")
        path.write_text("{}")
        self.run_studio("native-edit-plan", "edit", patch_file, error="素材清单与回执不符")

    def test_picture_reuse_checks_locked_audio_against_editable_archive(self):
        archive = ROOT / "deliveries" / "unsent-v0002" / "editable.zip"
        if not archive.exists():
            self.skipTest("需要冻结代码工程包")
        version = self.root / "works" / "unsent" / "versions" / "v0002"
        version.mkdir(parents=True)
        scan(archive, version)
        shutil.copy2(archive, version / "editable.zip")
        (version / "video.mp4").write_bytes(b"binding fixture")
        write(version / "receipt.json", {"project": "unsent", "version": "v0002", "delivery": {
            file: hashlib.sha256((version / file).read_bytes()).hexdigest()
            for file in ("video.mp4", "editable.zip", "brief.json")}})
        (version / "audio.m4a").write_bytes(b"changed locked audio")
        spec = importlib.util.spec_from_file_location("isolated_studio", self.root / "scripts" / "studio.py")
        studio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(studio)
        out = self.root / "candidate"
        out.mkdir()
        brief = json.loads((version / "brief.json").read_text())
        with patch.object(studio, "run", side_effect=AssertionError("unexpected media process")), \
                self.assertRaisesRegex(ValueError, "原生文件与工程包不符：audio.m4a"):
            studio.render(brief, version.parents[1], out, version)
        self.assertEqual(list(out.iterdir()), [])

    def test_declared_cover_reaches_actual_delivery_and_editable_bundle(self):
        spec = importlib.util.spec_from_file_location("isolated_studio", self.root / "scripts/studio.py")
        studio = importlib.util.module_from_spec(spec)
        # Match ordinary import semantics: review helpers consume this exact
        # isolated module/root, just as the real CLI consumes its __main__.
        registration = patch.dict(sys.modules, {spec.name: studio})
        registration.start()
        self.addCleanup(registration.stop)
        spec.loader.exec_module(studio)
        binary = self.root / ".studio/bin"
        binary.mkdir(parents=True)
        for name in ("ffmpeg", "ffprobe"):
            (binary / name).symlink_to(ROOT / ".studio/bin" / name)
        source = self.root / "source.mp4"
        studio.ff("-f", "lavfi", "-i", "color=blue:s=64x64:r=24:d=1", "-c:v", "libx264", source)
        cover = self.root / "cover.ppm"
        cover.write_bytes(b"P6\n64 64\n255\n" + bytes([255, 0, 0]) * 64 * 64)
        project = self.root / "works/cover-case"
        project.mkdir(parents=True)
        brief = {"id": "cover-case", "title": "Cover regression", "request": "Use supplied cover",
                 "width": 64, "height": 64, "fps": 24, "audio": {"mode": "silent"},
                 "coverAsset": "cover", "inputs": [
                     {"id": "picture", "kind": "video", "path": "source.mp4"},
                     {"id": "cover", "kind": "image", "path": "cover.ppm"}],
                 "shots": [{"id": "one", "kind": "media", "frames": 24, "asset": "picture", "cues": []}]}
        studio.import_inputs(brief, self.root / "brief.json", project)
        version = studio.build(project, brief)
        raw = subprocess.check_output([binary / "ffmpeg", "-v", "error", "-i", version / "cover.jpg",
                                       "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
        center = raw[(32 * 64 + 32) * 3: (32 * 64 + 32) * 3 + 3]
        self.assertGreater(center[0], 240, center)
        self.assertLess(center[2], 15, center)
        with zipfile.ZipFile(version / "editable.zip") as z:
            self.assertEqual(z.read("cover.jpg"), (version / "cover.jpg").read_bytes())
        self.assertEqual(studio.load(version / "publish.json")["cover"], "cover.jpg")
        studio.check_delivery(version)
        for bad in ("missing", "picture"):
            with self.assertRaisesRegex(ValueError, "封面需引用已声明的图片素材"):
                studio.check_inputs({**brief, "coverAsset": bad}, project)
        fallback = copy.deepcopy(brief)
        fallback.pop("coverAsset")
        next_version = studio.build(project, fallback, version)
        raw = subprocess.check_output([binary / "ffmpeg", "-v", "error", "-i", next_version / "cover.jpg",
                                       "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
        center = raw[(32 * 64 + 32) * 3: (32 * 64 + 32) * 3 + 3]
        self.assertLess(center[0], 15, center)
        self.assertGreater(center[2], 230, center)

    def test_media_revision_rebuilds_changed_sound_and_preserves_picture_only_audio(self):
        spec = importlib.util.spec_from_file_location("isolated_studio", self.root / "scripts" / "studio.py")
        studio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(studio)
        parent = self.root / "parent"
        parent.mkdir()
        cue = {"start": 0, "end": 12, "text": "old caption"}
        old = {"width": 64, "height": 64, "fps": 24, "audio": {"mode": "supplied", "asset": "old"},
               "shots": [{"id": "one", "kind": "media", "asset": "old-picture", "frames": 24,
                          "cues": [cue], "captionTiming": [cue]}]}
        write(parent / "brief.json", old)
        write(parent / "receipt.json", {"segments": []})
        (parent / "audio.m4a").write_bytes(b"old audio")
        (parent / "subtitles.srt").write_text("old caption")
        source = self.root / "new.wav"
        source.write_bytes(b"new audio fixture")
        for case in ("new-audio", "new-captions", "picture-only", "silent"):
            with self.subTest(case=case):
                brief = copy.deepcopy(old)
                shot = brief["shots"][0]
                shot.pop("captionTiming")
                shot["asset"] = "new-picture"
                if case == "new-audio":
                    brief["audio"]["asset"] = "new"
                elif case == "new-captions":
                    shot["cues"][0]["text"] = "new caption"
                elif case == "silent":
                    brief["audio"] = {"mode": "silent"}
                out = self.root / case
                out.mkdir()
                def fake_ff(*args):
                    Path(args[-1]).write_bytes(b"new audio")
                with patch.object(studio, "check_native_version"), \
                        patch.object(studio, "verified_input", return_value=source), \
                        patch.object(studio, "ff", side_effect=fake_ff) as audio_process, \
                        patch.object(studio, "media_segment", side_effect=RuntimeError("picture boundary")), \
                        self.assertRaisesRegex(RuntimeError, "picture boundary"):
                    studio.render(brief, self.root, out, parent)
                self.assertEqual(shot["captionTiming"], shot["cues"])
                if case == "silent":
                    self.assertFalse((out / "audio.m4a").exists())
                elif case == "picture-only":
                    self.assertEqual((out / "audio.m4a").read_bytes(), b"old audio")
                    audio_process.assert_not_called()
                else:
                    self.assertEqual((out / "audio.m4a").read_bytes(), b"new audio")
                expected = "new caption" if case == "new-captions" else "old caption"
                self.assertIn(expected, (out / "subtitles.srt").read_text())

    def test_code_revision_refuses_parent_native_file_edited_after_render(self):
        spec = importlib.util.spec_from_file_location("isolated_studio", self.root / "scripts" / "studio.py")
        studio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(studio)
        parent = self.root / "parent"
        page = parent / "shots/one/film/engine/index.html"
        page.parent.mkdir(parents=True)
        page.write_text("rendered page")
        cue = {"start": 0, "end": 12, "text": "caption"}
        brief = {"width": 64, "height": 64, "fps": 24, "audio": {"mode": "silent"},
                 "shots": [{"id": "one", "kind": "code", "engine": "lanshu", "frames": 24,
                            "cues": [cue], "captionTiming": [cue]}]}
        write(parent / "brief.json", brief)
        write(parent / "receipt.json", {"segments": [{"id": "one", "nativeFiles": {
            "shots/one/film/engine/index.html": studio.digest(page)}}]})
        (parent / "subtitles.srt").write_text("caption")
        for case in ("unchanged", "edited"):
            with self.subTest(case=case):
                if case == "edited":
                    page.write_text("hand edit after render")
                out = self.root / case
                out.mkdir()
                with patch.object(studio, "check_native_version"), \
                        patch.object(studio, "code_segment", side_effect=RuntimeError("picture boundary")) as segment:
                    expected = "picture boundary" if case == "unchanged" else "父版原生镜头校验失败"
                    with self.assertRaisesRegex(Exception, expected):
                        studio.render(copy.deepcopy(brief), self.root, out, parent)
                self.assertEqual(segment.call_count, 1 if case == "unchanged" else 0)

    def test_status_and_review_reject_changed_receipt_bound_native_files(self):
        project = self.root / "works/case"
        version = project / "versions/v0001"
        page = version / "shots/one/film/engine/index.html"
        page.parent.mkdir(parents=True)
        page.write_text("frozen source fixture")
        (version / "video.mp4").write_bytes(b"structural fixture, not playable media")
        write(version / "brief.json", {"id": "case"})
        write(project / "current.json", {"version": "v0001"})
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        write(version / "receipt.json", {"project": "case", "version": "v0001", "delivery": {
            name: sha(version / name) for name in ("video.mp4", "brief.json")}, "segments": [
                {"id": "one", "nativeFiles": {"shots/one/film/engine/index.html": sha(page)}}]})
        self.assertFalse(self.run_studio("status", "case")["delivery_ready"])
        page.write_text("source edited after receipt")
        self.run_studio("status", "case", error="原生镜头校验失败")
        self.run_studio("review-status", "case", "--version", "v0001", error="原生镜头校验失败")
        self.run_studio("--mode", "delivery", "export", "case", "--to", self.root / "delivery", error="原生镜头校验失败")
        self.assertFalse((self.root / "delivery").exists())

    def test_native_receipt_status_checks_output_source_and_stays_unregistered(self):
        source = self.root / "independent"
        source.mkdir()
        output, page = source / "candidate.mp4", source / "index.html"
        output.write_bytes(b"structural fixture, not playable media")
        page.write_text("source at export")
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        receipt = write(source / "receipt.json", {"file": str(output), "sha256": sha(output),
            "native_inputs": {"index.html": sha(page)}, "quality_approved": True})
        args = ("status", "--native-receipt", receipt, "--source-root", source)
        before = {p.name: p.read_bytes() for p in source.iterdir()}
        result = self.run_studio(*args)
        self.assertEqual(result["registration"], "independent_candidate")
        self.assertFalse(result["delivery_ready"])
        self.assertFalse(result["audio_verified"])
        alias = subprocess.run(["bash", ROOT / "scripts/vibe.sh", *map(str, args)],
                               capture_output=True, text=True, timeout=30)
        self.assertEqual(alias.returncode, 0, alias.stderr)
        self.assertFalse(json.loads(alias.stdout)["delivery_ready"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in source.iterdir()})
        self.assertFalse((self.root / "works").exists())
        output.write_bytes(b"different candidate")
        self.run_studio(*args, error="成片哈希不符")
        output.write_bytes(before[output.name])
        page.write_text("changed after export")
        self.run_studio(*args, error="导出后源文件已变化")
        data = json.loads(receipt.read_text())
        data["native_inputs"] = {"../outside.html": "0" * 64}
        write(receipt, data)
        self.run_studio(*args, error="超出工程")

    def test_resume_checks_candidate_identity_parent_and_pending_brief(self):
        project = self.root / "works" / "case"
        version = project / "versions" / "v0001"
        version.mkdir(parents=True)
        brief = {"id": "case", "title": "结构夹具", "request": "只核验续做提交",
                 "width": 64, "height": 64, "fps": 24, "audio": {"mode": "silent"},
                 "shots": [{"id": "one", "kind": "code", "frames": 24, "accent": "#123456"}]}
        write(version / "brief.json", brief)
        binary = self.root / ".studio/bin"
        binary.mkdir(parents=True)
        for name in ("ffmpeg", "ffprobe"):
            (binary / name).symlink_to(ROOT / ".studio/bin" / name)
        subprocess.run([str(binary / "ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
                        "color=blue:s=64x64:r=24:d=1", "-c:v", "libx264", str(version / "video.mp4")], check=True)
        receipt = {"project": "case", "version": "v0001", "parent": None, "delivery": {
            name: hashlib.sha256((version / name).read_bytes()).hexdigest()
            for name in ("video.mp4", "brief.json")}}
        for changed, error in (({"project": "other"}, "身份不一致"),
                               ({"version": "v0002"}, "身份不一致"),
                               ({"parent": "v0099"}, "父版不一致"),
                               ({}, "待完成需求不一致")):
            with self.subTest(changed=changed, error=error):
                write(version / "receipt.json", {**receipt, **changed})
                attempt_brief = {**brief, "title": "不同需求"} if not changed else brief
                pending = write(project / "pending.json", {"version": "v0001", "parent": None,
                                                            "brief": attempt_brief})
                before = pending.read_bytes()
                self.run_studio("--mode", "production", "resume", "case", error=error)
                self.assertFalse((project / "current.json").exists())
                self.assertEqual(pending.read_bytes(), before)
        computed = json.loads(json.dumps(brief))
        computed["shots"][0]["captionTiming"] = []
        write(version / "brief.json", computed)
        receipt["delivery"]["brief.json"] = hashlib.sha256((version / "brief.json").read_bytes()).hexdigest()
        write(version / "receipt.json", receipt)
        attempt = {"version": "v0001", "parent": None, "brief": brief}
        write(project / "pending.json", attempt)
        self.run_studio("--mode", "production", "resume", "case")
        self.assertEqual(json.loads((project / "current.json").read_text()), {"version": "v0001"})
        self.assertFalse((project / "pending.json").exists())
        # An interruption between pointer commit and pending unlink is safe to confirm again.
        write(project / "pending.json", attempt)
        self.run_studio("--mode", "production", "resume", "case")
        self.assertFalse((project / "pending.json").exists())
        self.assertEqual(self.run_studio("review-status", "case", "--version", "v0001")["status"], "pending")

    def test_resume_refuses_changed_active_parent_without_touching_candidate(self):
        project = self.root / "works" / "case"
        brief = {"id": "case", "width": 64, "height": 64, "fps": 24,
                 "audio": {"mode": "silent"},
                 "shots": [{"id": "one", "kind": "code", "frames": 24, "accent": "#123456"}]}
        for name in ("v0001", "v0002", "v0003"):
            version = project / "versions" / name
            version.mkdir(parents=True)
            (version / "video.mp4").write_bytes(b"binding fixture")
            write(version / "brief.json", brief)
            write(version / "receipt.json", {"project": "case", "version": name,
                "parent": "v0001" if name == "v0003" else None, "delivery": {
                    file: hashlib.sha256((version / file).read_bytes()).hexdigest()
                    for file in ("video.mp4", "brief.json")}})
        current = write(project / "current.json", {"version": "v0002"})
        pending = write(project / "pending.json", {"version": "v0003", "parent": "v0001", "brief": brief})
        before = (current.read_bytes(), pending.read_bytes())
        self.run_studio("--mode", "production", "resume", "case", error="活动版与待完成父版不一致")
        self.assertEqual((current.read_bytes(), pending.read_bytes()), before)

    def test_per_work_scene_audio_and_handoff(self):
        for name in ("first", "second"):
            base = self.root / name
            base.mkdir()
            (base / "scene.js").write_text(f"// {name}")
            (base / "media.mp4").write_text("Only a path fixture")
            (base / "layout.json").write_text("{}")
            with zipfile.ZipFile(base / "native.zip", "w") as archive:
                archive.writestr("scene.js", "// optional upstream edit source")
            brief = {"id": name, "request": "保留图像和片段来源", "width": 540, "height": 960, "fps": 24,
                     "audio": {"mode": "silent"}, "inputs": [
                         {"id": "scene", "kind": "scene", "path": "scene.js"},
                         {"id": "media", "kind": "video", "path": "media.mp4", "nativeAsset": "native"},
                         {"id": "layout", "kind": "data", "path": "layout.json"},
                         {"id": "native", "kind": "native", "path": "native.zip"},
                     ], "shots": [
                         {"id": "scene", "kind": "code", "frames": 24, "accent": "#123456",
                          "sceneAsset": "scene", "sceneAssets": ["layout"]},
                         {"id": "media", "kind": "media", "frames": 24, "asset": "media", "fit": "cover"},
                     ]}
            write(base / "brief.json", brief)
        plans = [self.run_studio("plan", self.root / name / "brief.json") for name in ("first", "second")]
        self.assertNotEqual(plans[0]["scenes"][0]["sha256"], plans[1]["scenes"][0]["sha256"])
        self.assertEqual(plans[0]["audio_mode"], "silent")
        self.assertEqual(plans[0]["total_frames"], 48)
        handoff = write(self.root / "first" / "task.json", {"action": "create", "request": "按这份 brief 创作",
                        "project": "first", "route": "code", "brief": "brief.json"})
        self.run_studio("workflow", handoff, error="与当前 --mode design 不匹配")
        result = self.run_studio("--mode", "production", "workflow", handoff)
        self.assertFalse(result["render_started"])
        self.assertTrue(any("绑定已登记风格模板" in item for item in result["blockers"]))
        self.assertFalse((self.root / "works").exists())
        brief["shots"][0]["sceneAsset"] = "missing"
        self.run_studio("plan", write(self.root / "second" / "brief.json", brief), error="已声明的 JS 场景")

    def test_scene_preparation_and_silent_cues_need_no_media_process(self):
        spec = importlib.util.spec_from_file_location("isolated_studio", self.root / "scripts" / "studio.py")
        studio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(studio)
        project = self.root / "candidate"
        project.mkdir()
        (project / "scene.js").write_text("// local scene")
        scene = {"id": "shot", "kind": "code", "sceneAsset": "source", "frames": 48,
                 "cues": [{"start": 4, "end": 12, "text": "Timed without speech"}]}
        brief = {"audio": {"mode": "silent"}, "fps": 24, "shots": [scene], "inputs": [
            {"id": "source", "path": "scene.js", "sha256": studio.digest(project / "scene.js")}]}
        out = project / "staged"
        out.mkdir()
        with patch.object(studio, "VIBE", ROOT / "runtime" / "vibe"), \
                patch.object(studio, "ADAPTERS", ROOT / "adapters"), \
                patch.object(studio, "run", side_effect=AssertionError("unexpected subprocess")):
            studio.prepare_sound(brief, project, out)
            studio.prepare_code_scene(scene, brief, project, out / "shot" / "film")
        self.assertFalse((out / "audio.m4a").exists())
        self.assertIn("Timed without speech", (out / "subtitles.srt").read_text())
        self.assertEqual((out / "shot" / "film" / "scene.js").read_bytes(), (project / "scene.js").read_bytes())

    def test_code_plan_checks_narration_and_media_contracts_without_production(self):
        (self.root / "scene.js").write_text("// static fixture, never executed")
        (self.root / "media.mp4").write_bytes(b"path fixture, never decoded")
        brief = {"id": "contracts", "width": 64, "height": 64, "fps": 24,
                 "inputs": [{"id": "scene", "kind": "scene", "path": "scene.js"},
                            {"id": "media", "kind": "video", "path": "media.mp4"}],
                 "shots": [{"id": "intro", "kind": "code", "frames": 48, "accent": "#123456",
                            "sceneAsset": "scene", "cues": ["Existing contract"]}]}
        path = self.root / "brief.json"
        for cues in ([], [""], ["  "], [{"spoken": 17}], [{"text": "caption", "spoken": ""}],
                     [None], "not a list"):
            with self.subTest(cues=cues):
                invalid = copy.deepcopy(brief)
                invalid["shots"][0]["cues"] = cues
                self.run_studio("plan", write(path, invalid), error="旁白")
                task = write(self.root / "task.json", {"action": "plan", "request": "核对合同，不制作",
                             "route": "code", "brief": "brief.json"})
                self.run_studio("workflow", task, error="旁白")
        for cues in (["text"], [{"text": "字幕", "spoken": "另读的口语"}],
                     [{"text": "", "spoken": "允许只读出、不显示字幕"}]):
            valid = copy.deepcopy(brief)
            valid["shots"][0]["cues"] = cues
            valid["shots"].append({"id": "pause", "kind": "media", "frames": 24, "asset": "media"})
            self.assertFalse(self.run_studio("plan", write(path, valid))["render_started"])
        for start in (-1, "nan", "inf", None, True):
            with self.subTest(start=start):
                invalid = copy.deepcopy(brief)
                invalid["audio"] = {"mode": "silent"}
                invalid["shots"] = [{"id": "media", "kind": "media", "frames": 24,
                                     "asset": "media", "in": start}]
                self.run_studio("plan", write(path, invalid), error="素材起点")
        for mode in ("silent", "supplied"):
            valid = copy.deepcopy(brief)
            valid["audio"] = {"mode": mode, "asset": "sound"}
            valid["shots"][0]["cues"] = [{"text": "caption", "start": 0, "end": 12}]
            (self.root / "sound.wav").write_bytes(b"path fixture, never decoded")
            valid["inputs"].append({"id": "sound", "kind": "audio", "path": "sound.wav"})
            self.assertEqual(self.run_studio("plan", write(path, valid))["audio_mode"], mode)
        self.assertFalse((self.root / "works").exists())
        self.assertFalse((self.root / ".studio").exists())

    def test_pinned_inputs_and_resume_fail_before_pending_or_render(self):
        spec = importlib.util.spec_from_file_location("isolated_studio", self.root / "scripts/studio.py")
        studio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(studio)
        scene = self.root / "scene.js"
        scene.write_text("// pinned original")
        brief = {"id": "contracts", "width": 64, "height": 64, "fps": 24, "audio": {"mode": "silent"},
                 "inputs": [{"id": "scene", "kind": "scene", "path": "scene.js",
                             "sha256": studio.digest(scene)}],
                 "shots": [{"id": "intro", "kind": "code", "frames": 48, "accent": "#123456",
                            "sceneAsset": "scene"}]}
        path = write(self.root / "brief.json", brief)
        self.assertFalse(self.run_studio("plan", path)["render_started"])
        scene.write_text("// changed after pinning")
        self.run_studio("plan", path, error="原始素材校验失败")
        editor = {**brief, "route": "editor", "primary": "scene", "operations": [{"type": "cut", "at": 1}]}
        self.run_studio("plan", write(self.root / "editor.json", editor), error="原始素材校验失败")
        project = self.root / "contracts"
        project.mkdir()
        with self.assertRaisesRegex(ValueError, "原始素材校验失败"):
            studio.import_inputs(copy.deepcopy(brief), path, project)
        self.assertFalse((project / "inputs").exists())
        shutil.copy2(scene, project / "scene.js")
        for invalid, message in ((brief, "原始素材校验失败"),
                                 ({**brief, "inputs": [], "shots": [{"id": "intro", "kind": "code",
                                   "frames": 48, "accent": "#123456", "sceneAsset": "missing"}]},
                                  "已声明的 JS 场景"),
                                 ({**brief, "audio": {"mode": "narrated"}}, "旁白")):
            with patch.object(studio, "render", side_effect=AssertionError("must not render")), \
                    self.assertRaisesRegex(ValueError, message):
                studio.build(project, invalid, version="v0001")
            self.assertFalse((project / "versions").exists())
            self.assertFalse((project / "pending.json").exists())

    def test_lanshu_native_compiler_reads_changed_story_without_media(self):
        kit = ROOT / "sources" / "zh-explainer" / "vendor" / "lanshu" / "explainer"
        if not (kit / "tools" / "sync.sh").is_file():
            self.skipTest("需要固定 Lanshu 编译器")
        style = "v1-editorial"
        target = self.root / "preview-staging"
        (target / "assets" / "audio").mkdir(parents=True)
        (target / "assets" / "audio" / "narration.wav").write_bytes(b"existing file prevents audio synthesis")
        story = self.root / "story"
        for duration in (10, 12):
            document = write(story / "story.json", {"duration": duration, "title": "structural fixture"})
            subprocess.run(["/bin/bash", kit / "tools" / "sync.sh", target, style, story],
                           check=True, capture_output=True, timeout=15)
            compiled = (target / "lib" / "story.js").read_bytes()
            self.assertEqual(compiled.split(b"\nwindow.STORY = ", 1)[1], document.read_bytes() + b";\n")
        local_kit = self.root / kit.relative_to(ROOT)
        (local_kit / "kits" / style / "starter").mkdir(parents=True)
        (local_kit / "tools").mkdir()
        for name in ("sync.sh", "stamp.py"):
            shutil.copy2(kit / "tools" / name, local_kit / "tools" / name)
        task = write(self.root / "inspect-story.json", {
            "action": "inspect", "request": "只检查故事绑定", "route": "lanshu",
            "story": "story", "style": style,
        })
        snapshot = self.run_studio("--mode", "development", "workflow", task)
        self.assertEqual(snapshot["checks"]["lanshu"]["story_sha256"], hashlib.sha256(document.read_bytes()).hexdigest())
        self.assertEqual(snapshot["stop_at"], "native_status")
        self.assertFalse(snapshot["checks"]["native_state"]["can_resume"])
        self.assertFalse((self.root / "works").exists())

    def test_research_and_unknown_task_do_not_dispatch(self):
        task = self.root / "task.json"
        write(task, {"action": "research", "request": "只研究这个方向"})
        result = self.run_studio("--mode", "research", "workflow", task)
        self.assertEqual(result["stop_at"], "research_delivery")
        write(task, {"action": "continue", "request": "看能否继续",
                     "external_task": {"id": "original", "provider": "historical"}})
        result = self.run_studio("--mode", "production", "workflow", task)
        self.assertEqual(result["checks"]["external_task"]["status"], "unknown")
        self.assertEqual(result["next"], "check_original_receipt")
        self.assertFalse((self.root / "works").exists())

    def test_review_separates_evidence_layers_and_refuses_stale_media(self):
        version = self.root / "works" / "case" / "versions" / "v0001"
        version.mkdir(parents=True)
        movie = version / "video.mp4"
        movie.write_bytes(b"hash fixture only")
        sha = hashlib.sha256(movie.read_bytes()).hexdigest()
        write(version / "receipt.json", {"project": "case", "version": "v0001", "delivery": {"video.mp4": sha}})
        write(version.parents[1] / "current.json", {"version": "v0001"})
        review = {"project": "case", "version": "v0001", "video_sha256": sha,
                  "checks": [{"layer": "visual", "status": "observed", "scope": "00:02-00:04",
                              "method": "记录格式夹具", "evidence": "fixture/reference"}]}
        file = write(self.root / "review.json", review)
        result = self.run_studio("review-check", file)
        self.assertTrue(result["is_current"])
        self.assertIn("listening", result["not_observed_in_record"])
        self.assertEqual(result["verified_here"], "artifact_binding_only")
        review["video_sha256"] = "0" * 64
        self.run_studio("review-check", write(file, review), error="绑定了其他产物")

    def test_recovery_and_local_copy_never_promote_failed_candidate(self):
        project = self.root / "works" / "case"
        for version in ("v0001", "v0002"):
            file = project / "versions" / version / "video.mp4"
            file.parent.mkdir(parents=True)
            file.write_text(version)
            write(file.with_name("receipt.json"), {"project": "case", "version": version,
                  "delivery": {"video.mp4": hashlib.sha256(file.read_bytes()).hexdigest()}})
        current = write(project / "current.json", {"version": "v0002"})
        pending = write(project / "pending.json", {"version": "v0003", "parent": "v0002"})
        interrupted = project / "versions" / ".v0003.building"
        interrupted.mkdir()
        self.run_studio("--mode", "recovery", "select-version", "case", "v0001", error="未完成候选")
        self.run_studio("--mode", "recovery", "abandon-candidate", "case", "v0002", error="确切版本")
        self.run_studio("--mode", "recovery", "abandon-candidate", "case", "v0003")
        self.assertTrue(interrupted.is_dir())
        self.assertFalse(pending.exists())
        self.assertEqual(json.loads(current.read_text())["version"], "v0002")
        self.run_studio("--mode", "recovery", "select-version", "case", "v0001")
        target = self.root / "exported"
        self.run_studio("--mode", "delivery", "export", "case", "--version", "v0002", "--to", target,
                        error="当前版本不一致")
        self.assertFalse(target.exists())
        self.run_studio("--mode", "delivery", "export", "case", "--version", "v0001", "--to", target,
                        error="质量交付被阻止")
        self.assertFalse(target.exists())
        self.assertEqual(json.loads(current.read_text())["version"], "v0001")

    def test_six_native_commerce_cases_route_individually(self):
        source = ROOT / "sources" / "hyperframe-local" / "video-agent"
        if not source.is_dir():
            self.skipTest("需要冻结 Hyperframe 来源")
        self.node()
        shutil.copy2(ROOT / "adapters" / "commerce-plan.mjs", self.root / "adapters")
        for name in ("lib/orchestration/commerce-router-v2.mjs", "config/routing/commerce-route-policy.v2.json"):
            target = self.root / "sources" / "hyperframe-local" / "video-agent" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, target)
        for scenario in ("launch", "demo", "detail", "collection", "promotion", "faq"):
            with self.subTest(scenario=scenario):
                key = "product_" + scenario
                file = write(self.root / "task.json", {"action": "plan", "request": "保留素材原证据",
                             "route": "editor", "commerce": True, "scenario": key})
                result = self.run_studio("workflow", file)
                self.assertEqual(result["checks"]["commerce"]["scenario"]["id"], key)
                self.assertFalse(result["render_started"])


if __name__ == "__main__":
    unittest.main()
