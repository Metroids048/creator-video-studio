"""Shared editorial inputs, consumed by planning, packaging and the next brief.

Codex supplies the editorial judgment. This module validates bindings and carries
the same decisions through the existing deterministic studio, without model calls.
"""
import hashlib
import json
import math
import re
from pathlib import Path


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} 不能为空")
    return value


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def freeze(account, topic, inputs):
    value = {"schema": 1, "account": account, "topic": topic, "inputs": inputs}
    return {**value, "data_sha256": fingerprint(value)}


def validate(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get("schema") != 1:
        raise ValueError("缺少有效的受众与选题简报 content_strategy")
    if snapshot.get("data_sha256") != fingerprint({k: v for k, v in snapshot.items() if k != "data_sha256"}):
        raise ValueError("受众与选题快照已变化，须重新策划并冻结")
    account, topic = snapshot["account"], snapshot["topic"]
    for key in ("alias", "platform", "promise"):
        text(account.get(key), f"账号 {key}")
    for key in ("who", "situation", "need"):
        text(account.get("audience", {}).get(key), f"受众 {key}")
    for key in ("id", "pillar", "audience_question", "payoff", "angle", "opening", "visual_plan", "goal"):
        text(topic.get(key), f"选题 {key}")
    if topic["pillar"] not in account.get("pillars", []):
        raise ValueError("选题不属于账号内容支柱")
    if topic.get("decision") not in {"ready", "research", "rejected"}:
        raise ValueError("选题须明确 ready/research/rejected 决策")
    evidence = account.get("evidence", []) + topic.get("evidence", [])
    ids = []
    for item in evidence:
        for key in ("id", "source", "observation", "limitation"):
            text(item.get(key), f"证据 {key}")
        if item.get("kind") not in {"user_decision", "public_observation", "video_observation", "hypothesis", "editorial_feedback"}:
            raise ValueError("证据须区分观察、用户决定与假设")
        ids.append(item["id"])
    if not evidence or len(set(ids)) != len(ids):
        raise ValueError("受众与选题需有不重复且注明限制的依据")
    promises = topic.get("promises", [])
    if not promises or len({p["id"] for p in promises}) != len(promises):
        raise ValueError("选题需有不重复的内容承诺")
    for promise in promises:
        text(promise["id"], "承诺 id"); text(promise.get("text"), "内容承诺")
    if not topic.get("evidence_ids") or not set(topic["evidence_ids"]) <= set(ids):
        raise ValueError("选题引用未知证据")
    return snapshot


def load(studio, path):
    document = studio.load(path)
    if "content_strategy" in document:
        return validate(document["content_strategy"])
    values, inputs = {}, []
    for role in ("account", "topic"):
        ref = document[role]
        file = (path.resolve().parent / ref["file"]).resolve(strict=True)
        if studio.digest(file) != ref["sha256"]:
            raise ValueError(f"{role} 输入哈希已变化，重新核对简报")
        values[role] = studio.load(file)
        inputs.append({"role": role, "file": str(file), "sha256": ref["sha256"]})
    return validate(freeze(values["account"], values["topic"], inputs))


def creative_contract(snapshot):
    validate(snapshot)
    a, t = snapshot["account"], snapshot["topic"]
    return {"status": t["decision"], "account_alias": a["alias"], "platform": a["platform"],
            "audience": a["audience"], "account_promise": a["promise"],
            "topic": t["id"], "viewer_question": t["audience_question"], "payoff": t["payoff"],
            "angle": t["angle"], "opening": t["opening"], "visual_plan": t["visual_plan"],
            "promises": t["promises"], "evidence_ids": t["evidence_ids"],
            "evidence": [item for item in a.get("evidence", []) + t.get("evidence", [])
                         if item["id"] in t["evidence_ids"]],
            "voice": a.get("voice", []), "avoid": a.get("avoid", []),
            "strategy_sha256": snapshot["data_sha256"]}


def editorial_resources(root):
    """Selected source passages for the creator, not upstream runtime instructions."""
    selections = [
        ("sources/video/third_party_skills/ip-strategist/references/02-选题方法论.md",
         "**【选题自检三问】**", "三问全过",
         "把宽泛话题拆成具体处境和有内容的回答；研究后才能选定答案。",
         "三问是编辑启发，不是程序验收；不采纳该来源的随机流量池与爆款必然性说法。"),
        ("sources/video/third_party_skills/ip-strategist/references/03-脚本骨架.md",
         "**信息密度 =", "**信息枚举**",
         "逐段辨认新增的解释、证据或事件；先删重复，再谈快慢。",
         "不是信息密度数值评分；快节奏、清单及高情绪均不保证好看。"),
        ("sources/zh-explainer/skills/vibe-film/references/topic-and-hook.md",
         "## 2.", "## 5.",
         "比较开头提出的问题与正文实际回答，核演示是否承担信息。",
         "是本地保存的方法版本，没有当前平台留存数据；示例不等于成功模板。"),
        ("sources/zh-explainer/skills/vibe-film/references/traffic-playbook.md",
         "## 1.", "## 3.",
         "区分知识答案、剧情后果和情绪关系的观看回报，避免全部改成故事。",
         "不能从技术通过推断观众喜欢，也不能从传播技巧推断流量。"),
    ]
    resources = []
    for name, start, end, use, limitation in selections:
        path = root / name
        raw = path.read_bytes()
        body = raw.decode("utf-8")
        begin = body.index(start)
        finish = body.index(end, begin + len(start))
        resources.append({"file": str(path), "source_sha256": hashlib.sha256(raw).hexdigest(),
                          "excerpt_start": start, "excerpt_end_exclusive": end,
                          "text": body[begin:finish].strip(), "use": use, "limitation": limitation})
    return resources


def previous_work(studio, path):
    """Return recorded feedback from a bound work, never grade the new input."""
    document = studio.load(path)
    project_id = document.get("id", "")
    if not isinstance(project_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", project_id):
        return {"status": "no_work_binding"}
    project = studio.works_root() / project_id
    # Reading an explicit historical version must not silently select current.
    if path.resolve().parent.parent == (project / "versions").resolve():
        version = path.resolve().parent
    elif (project / "current.json").is_file():
        name = studio.load(project / "current.json").get("version", "")
        if not isinstance(name, str) or not re.fullmatch(r"v[0-9]{4,}", name):
            raise ValueError("历史反馈的活动版本标识无效")
        version = project / "versions" / name
    else:
        return {"status": "no_work_binding"}
    import video_review
    report = video_review.status(studio, version)
    if not report.get("record"):
        return {"status": "unavailable", "version": str(version),
                "limitations": report.get("blockers", [])}
    record_path = Path(report["record"])
    record = studio.load(record_path)
    original = studio.load(version / "brief.json")
    same_content = all(document.get(key) == original.get(key) for key in ("script", "content_strategy"))
    result = {"status": "available", "relation": "same_script_and_strategy" if same_content else "earlier_content",
              "source": report["source"], "record": str(record_path), "record_sha256": studio.digest(record_path),
              "review_status": report["status"], "reviewer": record["reviewer"],
              "findings": record.get("findings", []), "checks": record.get("checks", []),
              "limitations": "只回传该历史版本的已记录观察；相同文稿不等于相同工程或画面，不决定本次内容质量。"}
    rejection = record_path.parent / "user-rejection.json"
    if rejection.is_file():
        feedback = studio.load(rejection)
        if feedback.get("video") != report["source"]:
            raise ValueError("用户反馈与历史审查版本不一致")
        result["user_feedback"] = {**feedback, "file": str(rejection), "file_sha256": studio.digest(rejection)}
    return result


def development_context(snapshot, root, *, question=None, content_format="general"):
    """Load working editorial material, without approving or generating content."""
    contract = creative_contract(snapshot) if snapshot is not None else {
        "viewer_question": text(question, "待研究问题"), "audience": None, "payoff": None,
        "opening": None, "visual_plan": None, "evidence": [], "avoid": [], "status": "research"}
    path = root / ".agents/skills/self-media-studio/references/原创内容开发.md"
    result = {"viewer_question": contract["viewer_question"],
            "audience": contract["audience"], "proposed_payoff": contract["payoff"],
            "current_opening": contract["opening"], "current_visual_plan": contract["visual_plan"],
            "evidence": contract["evidence"], "avoid": contract["avoid"],
            "topic_decision": contract["status"], "quality_status": "unassessed",
            "decision_scope": "已有简报的历史策划决定；不是当前质量、用户认可或制作授权",
            "resources": editorial_resources(root),
            "method": {"file": str(path), "text": path.read_text(encoding="utf-8")},
            "limitations": "此输出提供创作上下文，不自动写稿或评分；原创质量与人物表演仍未证明。"}
    workflow = root / "docs/制作配方/视频制作工作流.md"
    raw = workflow.read_bytes()
    workflow_hash = hashlib.sha256(raw).hexdigest()
    result["resources"].append({"file": str(workflow), "source_sha256": workflow_hash,
                                "text": raw.decode("utf-8"), "use": "跨任务复盘后的完整制作交接与返修方法",
                                "limitation": "流程消费材料，不代表媒体质量已验收或获准制作"})
    result["production_workflow"] = {
        "file": str(workflow), "source_sha256": workflow_hash,
        "stage_handoff": {"stage": "content", "artifacts": [str(workflow)]},
        "quality_inheritance": False,
    }
    if content_format == "knowledge-song":
        for name, use in [
            (".agents/skills/self-media-studio/references/知识歌曲开发.md", "将本题发展成事实、可唱句、音乐段落和连续解释场景；含可实际改写的示例"),
            ("docs/制作配方/知识歌曲首版.md", "消费V13返修后形成的首版方法与交接合同；换主题重写事实与事件，不继承旧片质量结论"),
            (".agents/skills/studio-video-research/references/rea-video.md", "已有参考先复用拆片包，将知识段落、唱句、声部、对象状态与镜头关联；不继承原曲或原秒数"),
            ("runtime/vibe/templates/knowledge-short/BRIEF.md", "复用知识锚点、因果图解和章节设计；不继承其中外部供应方或生产授权"),
        ]:
            file = root / name
            raw = file.read_bytes()
            result["resources"].append({"file": str(file), "source_sha256": hashlib.sha256(raw).hexdigest(),
                                        "text": raw.decode("utf-8"), "use": use,
                                        "limitation": "工程和文本材料，不是已定版歌曲、完整视听或质量认证"})
            if name == "docs/制作配方/知识歌曲首版.md":
                result["production_recipe"] = {
                    "file": str(file), "source_sha256": hashlib.sha256(raw).hexdigest(),
                    "stage_handoff": {"stage": "content", "artifacts": [str(file)]},
                    "quality_inheritance": False,
                    "scope": "将实际消费的配方和本题产物加入既有阶段交接；不绑定模型或自动确认阶段",
                }
        result["content_format"] = content_format
    elif content_format != "general":
        raise ValueError("不支持的内容形式")
    from visual_assets import inspect as visual_context
    from production_method import context as production_context
    result['production_method'] = production_context(root, content_format)
    result["visual_design"] = visual_context(root)
    return result


def publication(studio, spec, spec_path, duration=None):
    ref = spec.get("strategy")
    if not isinstance(ref, dict):
        raise ValueError("新发布包必须绑定受众与选题 strategy")
    file = (spec_path.resolve().parent / ref["file"]).resolve(strict=True)
    if studio.digest(file) != ref["sha256"]:
        raise ValueError("受众与选题入口哈希已变化")
    snapshot = load(studio, file)
    validate_publication(snapshot, spec, duration)
    return snapshot


def validate_publication(snapshot, spec, duration=None):
    validate(snapshot)
    account, topic = snapshot["account"], snapshot["topic"]
    if account["alias"] != spec["account_alias"] or account["platform"] != spec["platform"]:
        raise ValueError("受众简报与发布账号或平台不符")
    if topic["decision"] != "ready":
        raise ValueError("待研究或否决的选题不能进入发布包")
    promises = {p["id"] for p in topic["promises"]}
    editorial = spec.get("editorial", {})
    fulfilled = set()
    for item in editorial.get("fulfillment", []):
        seconds = item.get("at_seconds")
        if (type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0
                or (duration is not None and seconds >= duration)):
            raise ValueError("内容承诺需指向真实片内时间")
        if item.get("promise_id") not in promises:
            raise ValueError("内容审查引用未知承诺")
        text(item.get("observation"), "片内兑现观察")
        fulfilled.add(item["promise_id"])
    used = {item.get("promise_id") for item in spec["titles"] + spec["covers"]}
    if not used <= fulfilled or not fulfilled:
        raise ValueError("标题封面承诺没有片内兑现证据")
    basis = editorial.get("tag_basis", [])
    if [b.get("tag") for b in basis] != spec.get("tags", spec.get("final", {}).get("tags")):
        raise ValueError("每个标签须逐一说明依据，不能凭空补热词")
    evidence_ids = {e["id"] for e in account["evidence"] + topic["evidence"]}
    for item in basis:
        text(item.get("role"), "标签用途"); text(item.get("basis"), "标签依据")
        if item.get("evidence_id") not in evidence_ids:
            raise ValueError("标签引用未知证据")
    if len(editorial.get("cover_observations", [])) != 2:
        raise ValueError("需分别审查两张真实封面")
    for observation in editorial["cover_observations"]:
        text(observation, "封面观察")
    return snapshot
