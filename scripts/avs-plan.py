#!/usr/bin/env python3
"""Adopt a validated Codex script through the pinned AVS planner, without media."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ("episode.json", "work/input-manifest.json",
          "work/analysis/asset-intelligence.json", "work/content/script.json",
          "work/content/creative-brief.json")
OUTPUTS = tuple("work/content/" + name + ".json" for name in
                ("creative-brief", "reference-selection", "hook-selection", "script", "evidence-map", "shot-plan"))


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def adopt(episode_id, platform=None):
    from avs.active import active_plan
    from avs.config import Config
    from avs.creative import assert_agent_script, load_agent_script
    from avs.models.episode import EpisodeModel
    from avs.paths import find_episode_dir
    from avs.workflow import action_for_episode
    import jsonschema

    native = ROOT / "runtime/avs"
    ep = find_episode_dir(Config(native).episodes_root, episode_id)
    if ep is None:
        raise ValueError("原生 Episode 不存在")
    model = EpisodeModel.load(ep / "episode.json")
    if model.id != episode_id:
        raise ValueError("Episode 身份不一致")
    for name in (*INPUTS, *OUTPUTS, "work/content/codex-plan.json"):
        path = ep / name
        if path.resolve() != path:
            raise ValueError("原生合同路径包含符号链接，保留原工程并停止：" + name)
    action = action_for_episode(ep, model)
    if action.kind != "command" or action.command != ("plan",):
        raise ValueError("当前原生阶段不允许 plan；先查 workflow status，不跳阶段或重新规划已完成稿")
    script = load_agent_script(ep)
    if script is None:
        raise ValueError("缺经过校验的 Codex 脚本，禁止确定性文案回退")
    assert_agent_script(script, manifest=json.loads((ep / INPUTS[1]).read_text()),
                        intelligence=json.loads((ep / INPUTS[2]).read_text()), episode_id=model.id)
    brief_path = ep / INPUTS[4]
    if not brief_path.is_file():
        raise ValueError("缺当前作品 creative-brief.json；禁止继承原仓交易样例的创作设定")
    brief = json.loads(brief_path.read_text())
    jsonschema.Draft7Validator(json.loads((native / "schemas/creative-brief.schema.json").read_text())).validate(brief)
    if brief["episode_id"] != model.id:
        raise ValueError("创作说明的 Episode 身份不一致")
    if platform is not None and platform != brief["platform"]:
        raise ValueError("平台参数与当前作品创作说明不一致")
    platform = brief["platform"]
    if abs(sum(segment["duration_seconds"] for segment in script["segments"]) - brief["duration_seconds"]) > 0.01:
        raise ValueError("创作说明与脚本时长不一致")
    if brief["hook"] != script["segments"][0]["spoken_text"]:
        raise ValueError("创作说明与脚本开头不一致")
    for script_key, brief_key in (("angle", "angle"), ("audience", "target_audience")):
        if script.get(script_key) and script[script_key] != brief[brief_key]:
            raise ValueError("创作说明与脚本字段不一致：" + script_key)
    manifest = json.loads((ep / INPUTS[1]).read_text())
    required = {asset["asset_id"] for asset in manifest.get("assets", []) if asset.get("must_use")}
    if set(brief["must_use_asset_ids"]) != required:
        raise ValueError("创作说明与素材清单的必用素材不一致")
    # The native planner writes several contracts. Prepare them in isolation so
    # invalid inputs and planner failures leave the original Episode untouched.
    hashes = {name: checksum(ep / name) for name in INPUTS}
    with tempfile.TemporaryDirectory(prefix="studio-avs-plan-") as directory:
        staged = Path(directory)
        for name in INPUTS:
            target = staged / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ep / name, target)
        active_plan(staged, EpisodeModel.load(staged / "episode.json"),
                    platform=platform,
                    pattern_ids=script.get("reference_pattern_ids") or None)
        # The pinned planner supplies evidence and shots, but its brief builder
        # contains trading-demo defaults. Retain this work's validated native
        # brief byte for byte instead of adopting those creative decisions.
        (staged / INPUTS[4]).write_bytes(brief_path.read_bytes())
        for name in OUTPUTS:
            if not (staged / name).is_file():
                raise ValueError("原生规划器缺输出：" + name)
        for contract, schema in (("script", "active-script"), ("creative-brief", "creative-brief"),
                                 ("reference-selection", "reference-selection"),
                                 ("evidence-map", "evidence-map"), ("shot-plan", "shot-plan")):
            jsonschema.Draft7Validator(json.loads((native / "schemas" / (schema + ".schema.json")).read_text())).validate(
                json.loads((staged / "work/content" / (contract + ".json")).read_text()))
        if any(checksum(ep / name) != sha for name, sha in hashes.items()):
            raise ValueError("原生输入在规划期间发生变化，未提交候选")
        # Commit Episode last. An interrupted contract copy cannot falsely mark
        # plan complete; the unchanged input script can be inspected before retry.
        receipt = {"episode_id": model.id, "operation": "adopt_agent_script",
                   "bindings": {**{name: value for name, value in hashes.items() if name != "episode.json"},
                                **{name: checksum(staged / name) for name in OUTPUTS}},
                   "accepted": False, "model_session_verified": False}
        receipt_name = "work/content/codex-plan.json"
        (staged / receipt_name).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        for name in (*OUTPUTS, receipt_name, "episode.json"):
            target = ep / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".studio-plan-", delete=False) as stream:
                temporary = Path(stream.name)
                try:
                    stream.write((staged / name).read_bytes())
                    stream.flush()
                    os.fsync(stream.fileno())
                except BaseException:
                    temporary.unlink(missing_ok=True)
                    raise
            try:
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
    return {"episode_id": model.id, "state_owner": "episode.json", "operation": "adopt_agent_script",
            "artifacts": {name: checksum(ep / name) for name in OUTPUTS},
            "render_started": False, "model_request_sent": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("production",))
    parser.add_argument("--platform", choices=("douyin", "xiaohongshu"))
    parser.add_argument("episode")
    args = parser.parse_args()
    if args.mode != "production":
        parser.error("原生合同写回需要显式 --mode production")
    locks = ROOT / ".studio/avs-locks"
    locks.mkdir(parents=True, exist_ok=True)
    with (locks / (hashlib.sha256(args.episode.encode()).hexdigest() + ".lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        report = adopt(args.episode, args.platform)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
