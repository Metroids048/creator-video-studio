"""Import genuine platform snapshots; keep missing data distinct from zero."""
from datetime import datetime
import math
from pathlib import Path
from statistics import median
import tempfile

from publishing import verify
import content_strategy


COUNTS = ("impressions", "views", "likes", "comments", "shares", "saves", "followers")


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("数据时间须含时区")
    return parsed


def validate(snapshot):
    for key in ("platform", "account_alias", "content_id", "content_type", "source"):
        if not isinstance(snapshot.get(key), str) or not snapshot[key].strip():
            raise ValueError(f"真实数据缺少 {key}")
    if snapshot.get("synthetic") is True:
        raise ValueError("演示数据不能作为真实复盘导入")
    published, observed = timestamp(snapshot["published_at"]), timestamp(snapshot["observed_at"])
    if observed < published:
        raise ValueError("采集时间早于发布时间")
    for key in ("window_hours", "duration_seconds"):
        value = snapshot[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{key} 必须为正数")
    if abs((observed - published).total_seconds()/3600 - snapshot["window_hours"]) > .1:
        raise ValueError("观察窗口与实际采集时间不符")
    metrics = snapshot["metrics"]
    if not isinstance(metrics, dict) or set(metrics) - set(COUNTS):
        raise ValueError("指标字段未知，需先映射平台口径")
    for key in COUNTS:
        value = metrics.get(key)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(f"{key} 须为非负整数或 null")
    if not any(metrics.get(key) is not None for key in COUNTS):
        raise ValueError("没有任何真实指标，保留待数据状态")
    return snapshot


def measures(snapshot):
    values = {key: snapshot["metrics"].get(key) for key in COUNTS}
    views = values["views"]
    for key in ("likes", "comments", "shares", "saves", "followers"):
        values[key + "_per_view"] = (values[key]/views if values[key] is not None and views else None)
    return values


def cohort(snapshot):
    # Exact duration and window are conservative; broad comparisons need a new explicit contract.
    return tuple(snapshot[key] for key in ("platform", "account_alias", "content_type", "duration_seconds", "window_hours"))


def analyze(current, baselines=()):
    validate(current)
    # At most one snapshot per distinct published content, never self-compare.
    comparable = {}
    for item in baselines:
        validate(item)
        if cohort(item) == cohort(current) and item["content_id"] != current["content_id"]:
            if item["content_id"] in comparable:
                raise ValueError("基线同一作品重复，先选定一个观察快照")
            comparable[item["content_id"]] = item
    values = measures(current)
    comparison = {}
    for key, value in values.items():
        samples = [measures(item)[key] for item in comparable.values() if measures(item)[key] is not None]
        reference = median(samples) if samples else None
        comparison[key] = {"value": value, "baseline_n": len(samples), "baseline_median": reference,
                           "relative_change": value/reference-1 if value is not None and reference else None}
    return {"status": "observed", "metrics": values, "comparison": comparison,
            "missing": [key for key in COUNTS if current["metrics"].get(key) is None],
            "coverage": sum(current["metrics"].get(key) is not None for key in COUNTS)/len(COUNTS),
            "baseline_contents": len(comparable), "excluded_baselines": len(baselines)-len(comparable),
            "conclusion": "描述性观察；不能把相关性解释为标题或封面的因果效果"}


def feedback(studio, path, manifest, binding):
    value = studio.load(path)
    if value.get("manifest_sha256") != binding["manifest_sha256"]:
        raise ValueError("反馈与本发布包不符")
    if value.get("kind") not in {"editorial_review", "user_feedback"}:
        raise ValueError("反馈须区分内容审查与真实用户反馈")
    if not isinstance(value.get("observations"), list) or not value["observations"]:
        raise ValueError("反馈缺少实际观察")
    if value["kind"] == "user_feedback":
        content_strategy.text(value.get("source"), "真实用户反馈来源")
    for observation in value["observations"]:
        content_strategy.text(observation, "反馈观察")
    for key in ("hypothesis", "variable", "alternative"):
        content_strategy.text(value.get(key), key)
    original = manifest.get("content_strategy")
    if not original:
        raise ValueError("旧包未绑定受众选题，先按新流程制作包装修订")
    topic = value["next_topic"]
    if topic.get("decision") != "research":
        raise ValueError("复盘回传为待研究选题，不能自动授权制作")
    checksum = studio.digest(path)
    evidence_id = "feedback-" + checksum[:12]
    topic = {**topic, "evidence": [*topic.get("evidence", []),
              {"id": evidence_id, "kind": "editorial_feedback", "source": f"{value['kind']} · manifest {binding['manifest_sha256']}",
               "observation": "；".join(value["observations"]), "limitation": "内容审查或反馈，不等同流量效果或因果证据"}],
              "evidence_ids": [*topic["evidence_ids"], evidence_id]}
    snapshot = content_strategy.freeze(original["account"], topic,
                                        [*original["inputs"], {"role":"feedback", "file":str(path.resolve()), "sha256":checksum}])
    content_strategy.validate(snapshot)
    return {"feedback": value, "feedback_sha256": checksum,
            "next_brief": {"content_strategy": snapshot, "request": topic["audience_question"],
                           "parent_publication_sha256": binding["manifest_sha256"],
                           "hypothesis": value["hypothesis"], "variable": value["variable"],
                           "alternative": value["alternative"], "production_authorized": False}}


def report(studio, package, metrics_path=None, baseline_paths=(), feedback_path=None):
    binding = verify(studio, package)
    manifest = studio.load(package / "manifest.json")
    result = {"publication": {**manifest["source"], "platform": manifest["platform"],
                              "account_alias": manifest["account_alias"], "revision": manifest["revision"],
                              "manifest_sha256": binding["manifest_sha256"]},
              "experiment": manifest["experiment"], "quality": binding["quality"],
              "published_by_this_workflow": False}
    if manifest.get("content_strategy"):
        result["content_strategy"] = manifest["content_strategy"]
    if feedback_path:
        result["learning"] = feedback(studio, feedback_path, manifest, binding)
    if metrics_path is None:
        return {**result, "status": "awaiting_data", "metrics": None, "baseline_contents": 0,
                "conclusion": "尚未发布，未导入真实平台数据；不能判断流量或包装效果",
                "next": "取得真实后台快照后导入；一次观察一个主要包装变量"}
    snapshot = validate(studio.load(metrics_path))
    if any(snapshot.get(key) != value for key, value in {
        "platform": manifest["platform"], "account_alias": manifest["account_alias"],
        "video_sha256": manifest["source"]["video_sha256"],
        "publication_manifest_sha256": binding["manifest_sha256"],
    }.items()):
        raise ValueError("指标与本发布包、账号或视频不符")
    baselines = [studio.load(path) for path in baseline_paths]
    return {**result, **analyze(snapshot, baselines), "snapshot": snapshot,
            "import": {"file": metrics_path.name, "sha256": studio.digest(metrics_path)},
            "baselines": [{"file": path.name, "sha256": studio.digest(path)} for path in baseline_paths]}


def save_review(studio, package, metrics_path=None, baseline_paths=(), feedback_path=None):
    result = report(studio, package, metrics_path, baseline_paths, feedback_path)
    p = result["publication"]
    parent = studio.works_root() / p["project"] / "analytics" / p["version"] / p["platform"] / p["revision"]
    parent.mkdir(parents=True, exist_ok=True)
    numbers = [int(path.name[1:]) for path in parent.iterdir() if path.is_dir() and path.name[1:].isdigit() and path.name.startswith('a')]
    destination = parent / f"a{max(numbers, default=0)+1:04d}"
    with tempfile.TemporaryDirectory(prefix=".review-", dir=parent) as temporary:
        stage = Path(temporary) / destination.name
        stage.mkdir()
        studio.save(stage / "report.json", result)
        if metrics_path:
            studio.save(stage / "snapshot.json", result["snapshot"])
        if result.get("learning"):
            studio.save(stage / "feedback.json", result["learning"]["feedback"])
            studio.save(stage / "next-brief.json", result["learning"]["next_brief"])
        lines = ["# 发布复盘", "", f"状态：{result['status']}", "", result["conclusion"], "",
                 f"质量记录（与流量分开）：{result['quality']}", "",
                 f"观察假设：{p['platform']} · {result['experiment']['hypothesis']}", "",
                 f"主要变量：{result['experiment']['variable']}", ""]
        if result["status"] == "observed":
            lines += ["| 指标 | 本条 | 同类中位数 | 基线条数 |", "|---|---:|---:|---:|"]
            for key, row in result["comparison"].items():
                show = lambda value: "缺失" if value is None else str(round(value, 4))
                lines.append(f"| {key} | {show(row['value'])} | {show(row['baseline_median'])} | {row['baseline_n']} |")
            lines += ["", "观察中的互动比率仅使用播放数作分母；不是平台官方综合分。", "", "下一条：先由 Codex 结合真实内容、评论与以上证据提出一个可检验改动，不自动改制作脚本。"]
        else:
            lines += ["暂无真实播放、互动或留存数据。", "", "下一次内容简报：沿用本条受众与准确内容承诺；暂不根据虚构结果改片。", "", result["next"]]
        if result.get("learning"):
            learning = result["learning"]["feedback"]
            lines += ["", f"## 本轮 {learning['kind']}（与流量数据分开）", "",
                      *[f"- {observation}" for observation in learning["observations"]], "",
                      f"下一次假设：{learning['hypothesis']}", f"主要变量：{learning['variable']}",
                      f"替代解释：{learning['alternative']}", "",
                      "next-brief.json 可直接交给 content-plan 读取，状态为 research，需选题判断后才可制作。"]
        (stage / "review.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
        stage.rename(destination)
    return {"path": str(destination), **result}
