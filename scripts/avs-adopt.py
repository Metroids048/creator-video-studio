#!/usr/bin/env python3
"""Validate Codex observations and adopt native AVS contracts, without an API."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ("asset-intelligence", "recording-analysis", "document-analysis", "transcription")
VISUAL_INPUTS = ("work/input-manifest.json", "work/content/script.json",
                 "work/content/evidence-map.json", "work/content/shot-plan.json", "work/timeline.json")


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local(ep, name):
    path = ep / name
    if Path(name).is_absolute() or ".." in Path(name).parts or path.resolve() != path:
        raise ValueError("合同只接受 Episode 内无符号链接的相对路径：" + name)
    return path


def schema(name, value):
    import jsonschema
    path = ROOT / "runtime/avs/schemas" / (name + ".schema.json")
    jsonschema.Draft7Validator(json.loads(path.read_text())).validate(value)


def indexed(rows, expected, label):
    ids = [row["asset_id"] for row in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError(label + " 的素材身份缺项、重复或越界")


def validate_analysis(ep, model, candidate):
    manifest = json.loads((ep / "work/input-manifest.json").read_text())
    schema("input-manifest", manifest)
    if manifest["episode_id"] != model.id:
        raise ValueError("素材清单与 Episode 不一致")
    rows = manifest["assets"]
    indexed(rows, {row["asset_id"] for row in rows}, "素材清单")
    good = [row for row in rows if row.get("status") == "ok"]
    if any(row["must_use"] and row.get("status") != "ok" for row in rows):
        raise ValueError("必用素材缺失或损坏，分析保持未完成")
    bindings = {"work/input-manifest.json": sha(ep / "work/input-manifest.json")}
    for row in good:
        path = local(ep, row.get("working_path") or row["source_path"])
        if not path.is_file() or sha(path) != row["sha256"]:
            raise ValueError("原生素材与清单哈希不一致：" + row["asset_id"])
        bindings[path.relative_to(ep).as_posix()] = row["sha256"]
    contracts = candidate["contracts"]
    if set(contracts) != set(ANALYSIS):
        raise ValueError("须提交四份原生分析合同，不隐式生成空分析")
    for name, value in contracts.items():
        if value.get("episode_id") != model.id or value.get("blocked"):
            raise ValueError("分析身份不一致或仍受阻：" + name)
    intelligence = contracts["asset-intelligence"]
    schema("asset-intelligence", intelligence)
    schema("recording-analysis", contracts["recording-analysis"])
    if intelligence["provider"] != "codex:gpt-6.1-sol" or intelligence.get("requires_provider_review"):
        raise ValueError("仅接本机 Codex 的实际观察，不启用旧 Provider")
    visual = {r["asset_id"] for r in good if r["source_type"] in {"screenshot", "recording", "video"}}
    recordings = {r["asset_id"] for r in good if r["source_type"] in {"recording", "video"}}
    documents = {r["asset_id"] for r in good if r["source_type"] in {"document", "text"}}
    voices = {r["asset_id"] for r in good if r["source_type"] == "audio"
              and r.get("audio_role") in {"narration", "original_voice"}}
    indexed(intelligence["assets"], visual, "视觉分析")
    indexed(contracts["recording-analysis"]["recordings"], recordings, "录屏分析")
    indexed(contracts["document-analysis"]["assets"], documents, "文档分析")
    indexed(contracts["transcription"]["transcripts"], voices, "语音转写")
    observations = candidate.get("observations", [])
    observed = {r["asset_id"]: r for r in observations}
    if len(observed) != len(observations):
        raise ValueError("观察记录素材身份重复")
    for row in good:
        kind = row["source_type"]
        methods = ({"actual_view", "actual_playback"} if kind in {"screenshot", "recording", "video"}
                   else {"document_read"} if kind in {"document", "text"}
                   else {"actual_listening", "verified_transcript"} if row["asset_id"] in voices else set())
        if methods:
            receipt = observed.get(row["asset_id"], {})
            if receipt.get("method") not in methods or not receipt.get("observation", "").strip():
                raise ValueError("缺实际观察记录，不能以文件存在代替理解：" + row["asset_id"])
    for row in intelligence["assets"]:
        if not row["visible_facts"] or not row["summary"].strip():
            raise ValueError("视觉事实未完成：" + row["asset_id"])
        for region in row["regions"]:
            x, y, w, h = region["box"]
            if min(x, y) < 0 or min(w, h) <= 0 or x + w > 1.000001 or y + h > 1.000001:
                raise ValueError("视觉区域超出归一化画幅")
    for row in contracts["document-analysis"]["assets"]:
        if row.get("status") != "ok" or not row.get("text", "").strip():
            raise ValueError("文档提取未完成")
    for row in contracts["transcription"]["transcripts"]:
        if not row.get("text", "").strip() or not isinstance(row.get("segments"), list):
            raise ValueError("语音转写未完成")
    return {"work/analysis/" + name + ".json": value for name, value in contracts.items()}, bindings


def validate_visual(ep, model, candidate):
    video = next((ep / name for name in ("renders/preview-with-motion.mp4", "renders/preview-with-captions.mp4")
                  if (ep / name).is_file()), None)
    if video is None:
        raise ValueError("缺真实预览文件，不创建通过记录")
    bindings = {name: sha(local(ep, name)) for name in VISUAL_INPUTS}
    bindings[video.relative_to(ep).as_posix()] = sha(video)
    contracts = candidate["contracts"]
    if set(contracts) != {"visual-review"}:
        raise ValueError("只接受当前预览的 visual-review 合同")
    review = contracts["visual-review"]
    if not isinstance(review.get("failures"), list) or type(review.get("passed")) is not bool:
        raise ValueError("视觉审查须有显式 passed 和 failures")
    if review["passed"] != (not review["failures"]) or (review["passed"] and review.get("blocked")):
        raise ValueError("视觉审查结论与发现不一致")
    for item in review["failures"]:
        if (not item.get("failure_code") or not item.get("required_fix")
                or not isinstance(item.get("timestamp"), (int, float)) or item["timestamp"] < 0):
            raise ValueError("审查发现缺定位或修复要求")
    observations = candidate.get("observations", [])
    if not observations or any(r.get("method") not in {"actual_view", "actual_playback"}
                               or not r.get("observation", "").strip() for r in observations):
        raise ValueError("缺真实画面观察；听审、用户认可不能由视觉审查推定")
    review = {**review, "semantic_provider": "codex:gpt-6.1-sol",
              "video_sha256": sha(video), "input_bindings": bindings}
    return {"work/qa/visual-review.json": review}, bindings


def validate_acceptance(ep, model, candidate, stage):
    from avs.delivery.package import _final_video_path, _require_current_qa, _require_passing_creative_review
    from avs.qa.approval import create_approval
    from avs.qa.creative_review import SCORE_WEIGHTS, evaluate_gate, weighted_overall
    from datetime import UTC, datetime
    video = _final_video_path(ep)
    if not video.is_file():
        raise ValueError("缺当前最终视频")
    _require_current_qa(ep, video)
    names = [*VISUAL_INPUTS, video.relative_to(ep).as_posix(),
             "delivery/qa-report.json", "work/qa/creative-review.json"]
    bindings = {name: sha(local(ep, name)) for name in names}
    if stage == "approve":
        _require_passing_creative_review(ep, video)
        if set(candidate["contracts"]) != {"visual-approval"}:
            raise ValueError("人工确认只接受 visual-approval 合同")
        evidence = candidate.get("human_evidence", {})
        if (evidence.get("source") != "user_message" or not evidence.get("reference", "").strip()
                or not evidence.get("text", "").strip() or not evidence.get("reviewer", "").strip()):
            raise ValueError("缺真实用户确认消息的引用和原文，不得由 Codex 自行批准")
        value = candidate["contracts"]["visual-approval"]
        checklist = value.get("checklist")
        if not isinstance(checklist, dict) or not checklist or any(type(v) is not bool or not v for v in checklist.values()):
            raise ValueError("人工确认必须逐项显式为 true；禁止默认全通过")
        approval = create_approval(ep, model.id, evidence["reviewer"], video,
                                   checklist=checklist, notes=value.get("notes"))
        return {"delivery/visual-approval.json": approval}, bindings
    if set(candidate["contracts"]) != {"creative-score"}:
        raise ValueError("创作审查只接受 creative-score，不重写客观度量")
    value = candidate["contracts"]["creative-score"]
    review = json.loads((ep / "work/qa/creative-review.json").read_text())
    if review.get("video_sha256") != sha(video):
        raise ValueError("审片包不属于当前视频")
    scores = value.get("scores", {})
    if set(scores) != set(SCORE_WEIGHTS) or any(type(v) not in (int, float) or not 0 <= v <= 10 for v in scores.values()):
        raise ValueError("须有十个真实审片维度的 0–10 分数")
    watched = value.get("reviewed_artifacts", [])
    if video.relative_to(ep).as_posix() not in watched:
        raise ValueError("须实际播放同版视频，不仅看联系表")
    for name in watched:
        bindings[name] = sha(local(ep, name))
    observations = candidate.get("observations", [])
    if not {"actual_playback", "actual_listening"} <= {r.get("method") for r in observations} or any(
            not r.get("observation", "").strip() for r in observations):
        raise ValueError("AVS 旁白片审查需实际播放和听审记录；不能以音轨存在代替")
    findings = value.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("审查发现须为列表")
    findings = [f for f in review.get("findings", []) if f.get("source") == "deterministic"] + [
        {**f, "source": "agent"} for f in findings]
    scores = {**scores, "overall": weighted_overall(scores)}
    round_index = value.get("repair_round", review.get("gate", {}).get("repair_round", 0))
    if type(round_index) is not int or not 0 <= round_index <= 3:
        raise ValueError("返修轮次须在原生有限轮次内，不能无限评分循环")
    if review.get("reviewer_kind") == "agent" and round_index != review.get("gate", {}).get("repair_round", 0) + 1:
        raise ValueError("重新审片须递增返修轮次，禁止清零旧失败记录")
    review.update(scores=scores, findings=findings, reviewer_kind="agent", reviewer_id="codex:gpt-6.1-sol",
                  reviewed_artifacts=watched, reviewed_at=datetime.now(UTC).isoformat(),
                  gate=evaluate_gate(review["metrics"], scores, findings, repair_round=round_index))
    schema("creative-review", review)
    return {"work/qa/creative-review.json": review}, bindings


def adopt(episode_id, stage, path):
    from avs.config import Config
    from avs.models.episode import EpisodeModel
    from avs.paths import find_episode_dir
    from avs.workflow import action_for_episode
    ep = find_episode_dir(Config(ROOT / "runtime/avs").episodes_root, episode_id)
    if ep is None:
        raise ValueError("原生 Episode 不存在")
    model = EpisodeModel.load(ep / "episode.json")
    action = action_for_episode(ep, model)
    current_stage = model.blocked_stage if action.stage == "recovery" and model.blocked else action.stage
    if model.id != episode_id or current_stage != stage or action.kind not in {"command", "recovery", "human"}:
        raise ValueError("当前原生阶段不允许此合同写回；先查 workflow status")
    candidate = json.loads(path.read_text())
    if candidate.get("episode_id") != episode_id or candidate.get("reviewed_by") != "codex:gpt-6.1-sol":
        raise ValueError("候选身份或本机 Codex 来源不一致")
    before = sha(ep / "episode.json")
    if stage in {"creative-gate", "approve"}:
        outputs, bindings = validate_acceptance(ep, model, candidate, stage)
    else:
        outputs, bindings = (validate_analysis if stage == "analyze" else validate_visual)(ep, model, candidate)
    if candidate.get("bindings") != bindings:
        raise ValueError("候选输入绑定已过期或不完整；重新核对同一版素材/预览")
    receipt = {**candidate, "contracts": {name: hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                                          for name, value in outputs.items()},
               "validated_here": "native_contract_and_provenance_only",
               "model_session_verified": False, "accepted": False}
    receipt_name = {"analyze": "work/analysis/codex-analysis.json", "visual-review": "work/qa/codex-visual-review.json",
                    "creative-gate": "work/qa/codex-creative-review.json", "approve": "work/qa/codex-human-approval.json"}[stage]
    outputs[receipt_name] = receipt
    if stage == "visual-review" and not outputs["work/qa/visual-review.json"]["passed"]:
        model.block("Codex 视觉审查有未解决发现；保留预览与修复定位", stage=stage)
    elif stage == "creative-gate":
        gate = outputs["work/qa/creative-review.json"]["gate"]
        if gate.get("technical_passed") and gate.get("creative_passed"):
            model.clear_block(stage=stage)
            model.complete_stage("creative-review")
            model.complete_stage(stage)
        else:
            model.block("创作审查未通过，按 findings 返修；不得覆盖已交付版", stage=stage)
    else:
        model.clear_block(stage=stage)
        model.complete_stage(stage)
    if before != sha(ep / "episode.json") or any(sha(local(ep, name)) != value for name, value in bindings.items()):
        raise ValueError("写回前原生状态或输入发生变化，未提交候选")
    # Keep earlier observations and blocked states as immutable evidence. This
    # history is not a second workflow state; episode.json remains authoritative.
    if local(ep, receipt_name).is_file():
        history = "work/codex-history/" + stage + "/" + sha(ep / receipt_name)
        previous = {name: json.loads(local(ep, name).read_text()) for name in [*outputs, "episode.json"]
                    if local(ep, name).is_file()}
        for name, value in previous.items():
            archived = history + "/" + name
            target = local(ep, archived)
            if target.exists() and json.loads(target.read_text()) != value:
                raise ValueError("历史证据冲突，保留现状并检查，不覆盖旧失败")
            outputs[archived] = value
        receipt["previous_observation"] = history
    # Stage all JSON before replacing any current contract; Episode commits last.
    with tempfile.TemporaryDirectory(prefix="studio-avs-adopt-") as temporary:
        staged = Path(temporary)
        for index, (name, value) in enumerate(outputs.items()):
            target = local(ep, name)
            if target.exists() and target.is_symlink():
                raise ValueError("输出不得使用符号链接")
            (staged / str(index)).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        model.save(staged / "episode.json")
        for name, source in [*((name, staged / str(i)) for i, name in enumerate(outputs)), ("episode.json", staged / "episode.json")]:
            target = local(ep, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".studio-adopt-", delete=False) as stream:
                pending = Path(stream.name)
                try:
                    stream.write(source.read_bytes())
                    stream.flush()
                    os.fsync(stream.fileno())
                except BaseException:
                    pending.unlink(missing_ok=True)
                    raise
            try:
                os.replace(pending, target)
            finally:
                pending.unlink(missing_ok=True)
    return {"episode_id": episode_id, "stage": stage, "state_owner": "episode.json",
            "artifacts": {name: sha(ep / name) for name in outputs},
            "validated_here": "native_contract_and_provenance_only", "accepted": False,
            "render_started": False, "model_request_sent": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("production",))
    parser.add_argument("stage", choices=("analyze", "visual-review", "creative-gate", "approve"))
    parser.add_argument("episode")
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    if args.mode != "production":
        parser.error("原生合同写回需要显式 --mode production")
    locks = ROOT / ".studio/avs-locks"
    locks.mkdir(parents=True, exist_ok=True)
    with (locks / (hashlib.sha256(args.episode.encode()).hexdigest() + ".lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        print(json.dumps(adopt(args.episode, args.stage, args.candidate.resolve()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
