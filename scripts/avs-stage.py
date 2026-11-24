#!/usr/bin/env python3
"""Guard the pinned deterministic AVS stages; check never runs media tools."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = {"preview": ("preview",), "final-render": ("final-render",),
            "technical-qa": ("qa",), "creative-review": ("creative", "review"),
            "deliver": ("deliver",), "export": ("export",)}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(episode_id, operation):
    from avs.config import Config
    from avs.models.episode import EpisodeModel
    from avs.paths import find_episode_dir
    from avs.workflow import action_for_episode
    ep = find_episode_dir(Config(ROOT / "runtime/avs").episodes_root, episode_id)
    if ep is None:
        raise ValueError("原生 Episode 不存在")
    if ep.resolve() != ep or any(p.is_symlink() for p in ep.rglob("*")):
        raise ValueError("原生工程不得包含符号链接")
    model = EpisodeModel.load(ep / "episode.json")
    action = action_for_episode(ep, model)
    stage = "technical-qa" if action.stage == "qa" else action.stage
    if model.id != episode_id or stage != operation or action.kind not in {"command", "recovery"}:
        raise ValueError("当前原生阶段不允许此操作；先查 workflow status，不跳阶段")
    if model.production_type == "SCREEN_DOCUMENTARY":
        raise ValueError("历史 SCREEN_DOCUMENTARY Pilot 绑定原交易样例；仅保留工程，不自动用于新任务")
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("studio_avs_contracts", ROOT / "scripts/avs-adopt.py")
    contracts = module_from_spec(spec)
    spec.loader.exec_module(contracts)
    if operation == "preview":
        from avs.creative import assert_agent_script, load_agent_script
        receipt = json.loads((ep / "work/content/codex-plan.json").read_text())
        plan_bindings = receipt.get("bindings", {})
        expected_plan = {"work/input-manifest.json", "work/analysis/asset-intelligence.json",
                         *["work/content/" + name + ".json" for name in
                           ("creative-brief", "reference-selection", "hook-selection", "script", "evidence-map", "shot-plan")]}
        if (receipt.get("episode_id") != model.id or set(plan_bindings) != expected_plan
                or any(not contracts.local(ep, name).is_file() or digest(ep / name) != sha
                       for name, sha in plan_bindings.items())):
            raise ValueError("规划合同绑定已过期，先核同版输入，不自动沿用旧镜头")
        manifest = json.loads((ep / "work/input-manifest.json").read_text())
        script = load_agent_script(ep)
        if script is None:
            raise ValueError("缺当前 Codex 原生脚本")
        assert_agent_script(script, manifest=manifest,
                            intelligence=json.loads((ep / "work/analysis/asset-intelligence.json").read_text()),
                            episode_id=model.id)
        voice = [r for r in manifest["assets"] if r.get("source_type") == "audio"
                 and r.get("status") == "ok" and r.get("audio_role") in {"narration", "original_voice"}]
        if not voice:
            raise ValueError("AVS 当前旁白路线须已有真实声音；禁止自动 TTS，无旁白任务用 code/Vibe/editor")
        for row in manifest["assets"]:
            if row.get("status") == "ok":
                path = contracts.local(ep, row.get("working_path") or row["source_path"])
                if not path.is_file() or digest(path) != row["sha256"]:
                    raise ValueError("素材哈希变化，先重新分析，不继续生产")
        timeline = ep / "work/timeline.json"
        if timeline.is_file():
            from avs.timeline.models import Timeline
            current = Timeline.load(timeline)
            if not any(t.kind == "audio" and t.audio_role == "voice" and t.clips for t in current.tracks):
                raise ValueError("现存时间线缺声音；先显式修复原生工程，不自动 TTS 或强制覆盖")
    if operation == "final-render":
        report = json.loads((ep / "work/qa/visual-review.json").read_text())
        bindings = report.get("input_bindings", {})
        videos = {"renders/preview-with-motion.mp4", "renders/preview-with-captions.mp4"}
        current_video = next((name for name in ("renders/preview-with-motion.mp4", "renders/preview-with-captions.mp4")
                              if (ep / name).is_file()), None)
        expected = set(contracts.VISUAL_INPUTS)
        if (not report.get("passed") or report.get("blocked")
                or report.get("semantic_provider") != "codex:gpt-6.1-sol"
                or not expected < set(bindings) or len(set(bindings) & videos) != 1
                or set(bindings) - expected - videos
                or current_video not in bindings or report.get("video_sha256") != digest(ep / current_video)
                or any(not contracts.local(ep, name).is_file() or digest(ep / name) != sha
                       for name, sha in bindings.items())):
            raise ValueError("视觉审查未通过或绑定已过期；禁止用旧审查放行最终渲染")
    paths = [p for p in ep.rglob("*") if p.is_file() and p.suffix in {".json", ".py", ".js"}]
    return ep, {"episode_id": model.id, "operation": operation,
                "state_owner": "episode.json", "argv": list(COMMANDS[operation]),
                "requires_mode": "production", "render_started": False,
                "model_request_sent": False, "accepted": False,
                "bindings": {p.relative_to(ep).as_posix(): digest(p) for p in sorted(paths)}}


def unavailable_narration(*args, **kwargs):
    raise RuntimeError("工作室禁用 AVS 自动 TTS；补真实声音后再交接，不自动生成")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", default="design", choices=("design", "research", "development", "production"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("operation", choices=tuple(COMMANDS))
    parser.add_argument("episode")
    args = parser.parse_args()
    if not args.check and args.mode != "production":
        parser.error("原生执行需要显式 --mode production")
    def perform():
        ep, report = check(args.episode, args.operation)
        if args.check:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return
        # Dependency substitution is a production policy boundary, not a mock:
        # the native preview may otherwise auto-create Edge TTS when voice is absent.
        from avs.render import tts
        tts.ensure_edge_narration = unavailable_narration
        from avs.cli import main as cli
        cli.main(args=[*COMMANDS[args.operation], args.episode], standalone_mode=False)
    if args.check:
        perform()
    else:
        locks = ROOT / ".studio/avs-locks"
        locks.mkdir(parents=True, exist_ok=True)
        with (locks / (hashlib.sha256(args.episode.encode()).hexdigest() + ".lock")).open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            perform()


if __name__ == "__main__":
    main()
