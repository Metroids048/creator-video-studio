"""Test real workflow and production guards without rendering a film."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.knowledge_song import check_repaired_vocal
from scripts.song_listening import listening_pcm, pcm_sha256

ROOT = Path(__file__).resolve().parents[1]


class KnowledgeSongTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.task = self.base / "task.json"
        self.works = self.base / "works"
        request = json.loads((ROOT / "templates/paper-ink-landscape/v1/example.json").read_text())
        script = "旅人沿着山路行走，走到断桥前停下，转身发现另一条路径，绕过障碍到达山顶。"
        script_path = self.base / "script.txt"
        script_path.write_text(script)
        match = self.cli("--mode", "development", "templates", "match", "山路", "--script-file", script_path,
                         "--purpose", "engineering_validation", "--select", "paper-ink-landscape",
                         "--save", self.base / "routing.json")
        request.update(content_format="knowledge-song", stage_handoff={"task": str(self.task)},
                       topic="山路", script=script, routing=match["selection"])
        result = self.cli("--mode", "development", "templates", "prepare",
                          self.save("request.json", request), "--to", self.base / "prepared")
        self.brief_path = Path(result["brief"])
        self.brief = json.loads(self.brief_path.read_text())
        self.audio = self.brief_path.parent / "song.m4a"
        subprocess.run([ROOT / ".studio/bin/ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                        "sine=duration=12", "-c:a", "aac", self.audio], check=True, timeout=15)
        self.audio_hash = hashlib.sha256(self.audio.read_bytes()).hexdigest()
        self.brief["audio"] = {"mode": "supplied", "asset": "song"}
        self.brief["inputs"].append({"id": "song", "kind": "audio", "path": self.audio.name,
                                     "sha256": self.audio_hash})
        self.save(self.brief_path, self.brief)
        fields = ["/" + key for key in self.brief if key != "stage_handoff"]
        self.stages = [{"id": "source", "needs": [], "fields": fields}]
        self.save("task.json", {"action": "plan", "request": "核已准备的原始测试材料",
                               "project": self.brief["id"], "brief": str(self.brief_path), "stages": self.stages})
        self.cli("workflow", self.task, "--confirm-stage", "source")

    def cli(self, *args, error=None):
        result = subprocess.run([sys.executable, ROOT / "scripts/studio.py", *map(str, args)],
                                text=True, capture_output=True, timeout=20)
        if error:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn(error, result.stderr)
        else:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

    def save(self, name, data):
        path = self.base / name
        path.write_text(json.dumps(data, ensure_ascii=False))
        return path

    def ref(self, path):
        return {"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def listening_fixture(self):
        """Structural positive only. Tone fixtures do not represent music or listening."""
        reference = self.base / "reference.wav"
        subprocess.run([ROOT / ".studio/bin/ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                        "sine=frequency=660:duration=12", reference], check=True, timeout=15)
        prepared = self.cli("song-listening-prepare", self.audio, reference,
                            "--output", self.base / "listening")
        capture = json.loads(Path(prepared["capture_template"]).read_text())
        candidate_hash = pcm_sha256(listening_pcm(self.audio))
        reference_hash = pcm_sha256(listening_pcm(reference, 0, 12))
        capture["listener"] = {"kind": "human", "endpoint": "synthetic structural fixture"}
        responses = {}
        for row in capture["samples"]:
            response = {"silence": None}
            if row["pcm_sha256"] not in {candidate_hash, reference_hash}:
                response["silence"] = capture["control_mute"]
            response.update({name: {"time": 1, "observation": "结构测试响应"}
                             for name in ("vocal", "arrangement")})
            row["response"] = json.dumps(response, ensure_ascii=False)
            responses[row["pcm_sha256"]] = row
        pair = {"candidate": responses[candidate_hash]["id"], "reference": responses[reference_hash]["id"]}
        pair.update({name: {"status": "comparable", "observation": "结构测试对照"}
                     for name in ("vocal", "arrangement")})
        capture["pair_response"] = json.dumps(pair, ensure_ascii=False)
        listening = self.save("listening.json", capture)
        return reference, listening, capture

    def start_fixture(self):
        method = self.save("method.json", {"project": self.brief["id"], "engine": "fixture",
                           "version": "1", "voice": "fixture", "approach": "fixture",
                           "settings": {"fixture": True}})
        reference, listening, capture = self.listening_fixture()
        blind = {"sha256": self.audio_hash, "reference_provided": False, "start": 0, "duration": 5}
        first = self.save("start-one.jsonl", {**blind, "text": "纸桥没那么弯"})
        second = self.save("start-two.jsonl", {**blind, "text": "这座纸桥没那么弯"})
        method_hash = self.ref(method)["sha256"]
        generated = self.save("generation.json", {"fixture": True})
        data = {"mix": self.ref(self.audio), "reference": self.ref(reference),
                "targets": [{"forms": ["纸桥"], "range": [0, 2]},
                            {"forms": ["没那么弯"], "range": [2, 4]}],
                "observations": [{**self.ref(first), "observer": "one"}, {**self.ref(second), "observer": "two"}],
                "listening_source": self.ref(listening), "singing_method_sha256": method_hash,
                "method_run": {"method_sha256": method_hash, "mix_sha256": self.audio_hash,
                               "source": self.ref(generated)}}
        audition = self.save("start-audition.json", data)
        task = json.loads(self.task.read_text())
        task["stages"].append({"id": "song-start", "needs": [], "artifacts": [str(method), str(audition)]})
        self.save(self.task, task)
        return data, audition, listening, capture

    def test_make_and_resume_block_before_render_when_review_is_missing(self):
        report = self.cli("workflow", self.task)["stage_handoff"]
        self.assertEqual(report["missing_stages"], ["knowledge-song-preview", "song-start"])
        self.cli("--mode", "production", "--works-root", self.works, "make", self.brief_path,
                 error="阶段交接未就绪：knowledge-song-preview")
        self.assertFalse(self.works.exists())
        project = self.works / self.brief["id"]
        project.mkdir(parents=True)
        marker = self.save(project / "pending.json", {"brief": self.brief, "version": "v0001", "parent": None})
        self.cli("--mode", "production", "--works-root", self.works, "resume", self.brief["id"],
                 error="阶段交接未就绪：knowledge-song-preview")
        self.assertTrue(marker.is_file())
        self.assertFalse((project / "versions").exists())

    def test_cannot_relabel_a_frozen_full_brief_as_representative(self):
        brief = {**self.brief, "production_stage": "representative"}
        path = self.save(self.brief_path.parent / "mislabeled.json", brief)
        self.cli("scene-context", path, "--shot", "any", error="形式或制作范围不一致")
        brief["shots"] = [dict(brief["shots"][0], frames=13 * self.brief["fps"])]
        self.save(path, brief)
        self.cli("--mode", "production", "--works-root", self.works, "make", path, error="代表段制作限 12 秒")

    def test_actual_workflow_rejects_open_issues_and_outdated_media(self):
        # Synthetic seconds establish the actual media/file checks, without
        # conveying editorial approval or rendering a production work.
        roles = ("rough-cut", "opening", "mechanism", "ending")
        media = []
        checks = {}
        for role, color in zip(roles, ("red", "green", "blue", "black")):
            path = self.base / (role + ".mp4")
            duration = 12 if role == "rough-cut" else 0.2
            subprocess.run([ROOT / ".studio/bin/ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                            f"color={color}:s=32x32:d={duration}", "-i", self.audio,
                            "-shortest", "-c:v", "libx264", "-c:a", "aac", path], check=True, timeout=15)
            media.append(str(path))
            checks[role] = {"media_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "observation": "结构测试夹具", "timecode": "0:00", "status": "pass"}
        start, _, listening, _ = self.start_fixture()
        self.cli("workflow", self.task, "--confirm-stage", "song-start")
        observation = self.save("observations.json", {"open_issues": ["未核清楚动作"], "checks": checks})
        task = json.loads(self.task.read_text())
        task["stages"].append({"id": "knowledge-song-preview", "needs": ["source", "song-start"],
                               "artifacts": [str(observation), *media]})
        self.save(self.task, task)
        self.cli("workflow", self.task, "--confirm-stage", "knowledge-song-preview", error="仍有未关闭问题")
        report = {"open_issues": [], "checks": checks, "source_audio_sha256": self.audio_hash}
        self.save(observation, report)
        self.cli("workflow", self.task, "--confirm-stage", "knowledge-song-preview", error="缺独立质量观察项")
        quality = {name: {"status": "pass", "start": 0, "end": 0.16, "observation": "结构测试夹具"}
                   for name in ("vocal", "progression", "sync", "hook", "mechanism", "continuity", "payoff")}
        report["quality"] = quality
        self.save(observation, report)
        self.cli("workflow", self.task, "--confirm-stage", "knowledge-song-preview", error="缺少听辨或对标证据")

        def ref(path):
            return {"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

        blind = {"sha256": self.audio_hash, "reference_provided": False, "start": 0, "duration": 5}
        first = self.save("first.jsonl", {**blind, "text": "纸桥"})
        second = self.save("second.jsonl", {**blind, "text": "支桥"})
        comparison = {"status": "comparable", "observation": "结构测试夹具"}
        comparison_source = self.save("comparison.json", comparison)
        audition = {"mix": ref(self.audio), "reference": start["reference"],
                    "targets": [{"forms": ["纸桥"], "range": [0, 2]}],
                    "observations": [{**ref(first), "observer": "one"}, {**ref(second), "observer": "two"}],
                    "comparison": {key: comparison for key in ("vocal", "arrangement")},
                    "comparison_source": ref(comparison_source), "listening_source": start["listening_source"],
                    "singing_method_sha256": start["singing_method_sha256"], "method_run": start["method_run"]}
        audition_path = self.save("audition.json", audition)
        report["audio_audition"] = ref(audition_path)
        report["editorial_comparison"] = {
            "reference_sha256": audition["reference"]["sha256"],
            **{key: dict(comparison) for key in ("hook", "progression", "payoff")}}
        self.save(observation, report)
        self.cli("workflow", self.task, "--confirm-stage", "knowledge-song-preview", error="未稳定辨出「纸桥」")
        self.save(second, {**blind, "text": "这座纸桥"})
        audition["observations"][1].update(ref(second))
        self.save(audition_path, audition)
        report["audio_audition"] = ref(audition_path)
        report["editorial_comparison"]["progression"]["status"] = "below"
        self.save(observation, report)
        self.cli("workflow", self.task, "--confirm-stage", "knowledge-song-preview", error="新增信息及镜头推进未达对标")
        report["editorial_comparison"]["progression"]["status"] = "comparable"
        quality["vocal"]["delivery"] = "spoken"
        quality["progression"].update(status="issue", observation="重复第一次实验，没有新增比较")
        self.save(observation, report)
        stage = self.cli("workflow", self.task, "--stage", "knowledge-song-preview")
        issues = stage["issues"][0]
        self.assertIn("节奏念白或待核不能放行", issues)
        self.assertIn("没有新增比较", issues)
        self.cli("--mode", "production", "--works-root", self.works, "make", self.brief_path,
                 error="阶段交接未就绪：knowledge-song-preview")
        self.assertFalse(self.works.exists())
        quality["vocal"]["delivery"] = "sung"  # Shape-only positive fixture.
        quality["progression"]["status"] = "pass"
        quality["mechanism"]["end"] = 999
        self.save(observation, report)
        self.cli("workflow", self.task, "--confirm-stage", "knowledge-song-preview", error="缺素材内时间")
        quality["mechanism"]["end"] = 0.16
        self.save(observation, {**report, "source_audio_sha256": "0" * 64})
        self.cli("workflow", self.task, "--confirm-stage", "knowledge-song-preview", error="音轨未绑定")
        self.save(observation, report)
        short_track = self.base / "partial-audio.mp4"
        subprocess.run([ROOT / ".studio/bin/ffmpeg", "-v", "error", "-i", media[0],
                        "-f", "lavfi", "-i", "sine=duration=1", "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", short_track],
                       check=True, timeout=15)
        rough_hash = checks["rough-cut"]["media_sha256"]
        checks["rough-cut"]["media_sha256"] = hashlib.sha256(short_track.read_bytes()).hexdigest()
        self.save(observation, report)
        task["stages"][-1]["artifacts"][1] = str(short_track)
        self.save(self.task, task)
        self.cli("workflow", self.task, "--confirm-stage", "knowledge-song-preview", error="全曲粗剪时长")
        checks["rough-cut"]["media_sha256"] = rough_hash
        self.save(observation, report)
        task["stages"][-1]["artifacts"][1] = media[0]
        self.save(self.task, task)
        confirmed = self.cli("workflow", self.task, "--confirm-stage", "knowledge-song-preview")
        self.assertEqual(confirmed["stage_handoff"]["status"], "ready")
        self.assertEqual(self.cli("plan", self.brief_path)["production_method"]["preview_scope"], "full")
        original_listening = listening.read_bytes()
        listening.write_bytes(original_listening + b" ")
        self.cli("--mode", "production", "--works-root", self.works, "make", self.brief_path,
                 error="已变更或缺失：经盲测校准的实际听审")
        self.assertFalse(self.works.exists())
        listening.write_bytes(original_listening)
        original = Path(media[1]).read_bytes()
        Path(media[1]).write_bytes(original + b"stale")
        self.cli("plan", self.brief_path, error="knowledge-song-preview")
        Path(media[1]).write_bytes(original)
        changed = copy.deepcopy(self.brief)
        changed["title"] += "改动"
        self.save(self.brief_path, changed)
        self.cli("plan", self.brief_path, error="knowledge-song-preview")

    def test_actual_start_rejects_transcripts_and_uncalibrated_listening(self):
        data, audition, listening, capture = self.start_fixture()
        start = self.cli("workflow", self.task, "--stage", "song-start")
        self.assertEqual(start["decision"], "work_on_this_stage")
        self.assertEqual(start["issues"], ["尚未确认实际产物"])
        valid_capture = copy.deepcopy(capture)
        data["comparison"] = {name: {"status": "comparable", "observation": "旧报告自报通过"}
                              for name in ("vocal", "arrangement")}
        data.pop("listening_source")
        self.save(audition, data)
        self.cli("song-audition", audition, error="经盲测校准的实际听审")
        self.assertEqual(self.cli("workflow", self.task)["stop_at"], "song-start")
        self.cli("workflow", self.task, "--confirm-stage", "song-start", error="经盲测校准的实际听审")
        for row in capture["samples"]:
            row["response"] = '{"silence": null}'
        self.save(listening, capture)
        data["listening_source"] = self.ref(listening)
        self.save(audition, data)
        self.cli("workflow", self.task, "--confirm-stage", "song-start", error="未辨出盲测对照内已知静音区间")
        self.cli("--mode", "production", "--works-root", self.works, "make", self.brief_path,
                 error="未辨出盲测对照内已知静音区间")
        self.assertFalse(self.works.exists())
        task = json.loads(self.task.read_text())
        task["stages"].append({"id": "knowledge-song-preview", "needs": ["source"],
                               "artifacts": [str(audition)]})
        self.save(self.task, task)
        self.cli("workflow", self.task, "--confirm-stage", "knowledge-song-preview", error="须依赖 song-start")
        self.save(listening, valid_capture)
        data["listening_source"] = self.ref(listening)
        self.save(audition, data)
        self.save(self.brief_path, {"id": self.brief["id"], "content_format": "knowledge-song"})
        confirmation = self.cli("workflow", self.task, "--confirm-stage", "song-start")
        self.assertIn("song-start", confirmation["stage_handoff"]["reusable"])
        self.save(self.brief_path, self.brief)
        method = self.base / "method.json"
        spec = json.loads(method.read_text())
        spec["voice"] = "different"
        self.save(method, spec)
        self.cli("plan", self.brief_path, error="首听未绑定开工已验证的唱法")

    def test_v13_native_render_and_compose_consume_the_workflow(self):
        frozen = ROOT / "works/falling-footage-1117/authoring-v0013"
        source = self.base / "native"
        shutil.copytree(frozen, source, ignore=shutil.ignore_patterns("media"))
        prepared = self.cli("native-knowledge", "describe", source, "--project", "v13-probe")
        self.assertEqual(len(prepared["production_method"]["skills"]), 3)
        self.assertEqual(prepared["brief"]["representative_review"], 1)
        brief = self.save("native-brief.json", prepared["brief"])
        task = self.save("native-task.json", {
            "action": "plan", "request": "核查历史 V13 原生工程的制作入口",
            "project": prepared["brief"]["id"], "brief": str(brief),
            "stages": [{"id": "source", "needs": [], "fields": ["/" + key for key in prepared["brief"]]}],
        })
        self.cli("workflow", task, "--confirm-stage", "source")
        output = self.base / "no-render.mp4"
        invoke = ("--mode", "production", "native-knowledge")
        self.cli(*invoke, "render", source, "--task", task, error="knowledge-song-preview")
        self.cli(*invoke, "compose", source, "--task", task, "--output", output, error="representative-review")
        self.cli(*invoke, "render", frozen, "--task", task, error="历史工程只读")
        self.assertFalse(output.exists())
        self.assertFalse((source / "media").exists())

    def test_repaired_vocal_requires_same_dry_and_mixed_blind_evidence(self):
        dry = "a" * 64
        mixed = "b" * 64
        self.save("composition.json", {"assets": {"dry-vocal": {"file": "voice.wav", "sha256": dry}}})
        report = self.base / "preview.json"
        brief = {"route": "native-knowledge", "native_root": str(self.base),
                 "native_inputs": {"files": {"voice.wav": dry}}}
        with self.assertRaisesRegex(ValueError, "缺同版干声及混音"):
            check_repaired_vocal(brief, report, {}, mixed)

        def observation(filename, digest):
            path = self.save(filename, {"sha256": digest, "reference_provided": False, "text": "测试用句"})
            return {"file": filename, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

        dry_result = observation("dry.jsonl", dry)
        mixed_result = observation("mixed.jsonl", mixed)
        sync = {"blind_check": {"dry": dry_result, "mixed": mixed_result, "unresolved": []}}
        check_repaired_vocal(brief, report, sync, mixed)
        with self.assertRaisesRegex(ValueError, "未绑定本版音轨：mixed"):
            check_repaired_vocal(brief, report, sync, "c" * 64)
        sync["blind_check"]["unresolved"] = ["关键词仍有歧义"]
        with self.assertRaisesRegex(ValueError, "未解决的听辨分歧"):
            check_repaired_vocal(brief, report, sync, mixed)
        self.save("dry.jsonl", {})
        with self.assertRaisesRegex(ValueError, "回执已变更或缺失：dry"):
            check_repaired_vocal(brief, report, sync, mixed)


if __name__ == "__main__":
    unittest.main()
