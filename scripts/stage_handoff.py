"""Frozen stage outputs inside the existing workflow task, never a job runner."""
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

from knowledge_song import START_STAGE, STAGE as PREVIEW_STAGE, check_diagnostic_scope, file_digest
from knowledge_song import required as needs_preview
from knowledge_song import review as review_preview, review_start
from representative_review import STAGE as REPRESENTATIVE_STAGE, required as needs_representative
from representative_review import review as review_representative


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def normalized(brief):
    value = copy.deepcopy(brief)
    value.pop("stage_handoff", None)
    for key in ("pictureRevision", "audioRevision"):
        value.pop(key, None)
    for row in value.get("inputs", []):
        row.pop("path", None)
        row.pop("sourcePath", None)
    for shot in value.get("shots", []):
        shot.pop("captionTiming", None)
    return value


def select(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("阶段 fields 须使用 /field 或 /shots/@镜头ID/field")
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        try:
            if isinstance(value, list):
                if token.startswith("@"):
                    matches = [row for row in value if isinstance(row, dict) and row.get("id") == token[1:]]
                    if len(matches) != 1:
                        raise ValueError("阶段选择器须唯一匹配：" + pointer)
                    value = matches[0]
                else:
                    raise ValueError("列表阶段绑定须用稳定 @ID，不能用位置索引：" + pointer)
            else:
                value = value[token]
        except (KeyError, TypeError):
            raise ValueError("阶段字段不存在：" + pointer) from None
    return value


def leaves(value, prefix=""):
    if isinstance(value, dict) and value:
        for key, child in value.items():
            yield from leaves(child, prefix + "/" + key.replace("~", "~0").replace("/", "~1"))
    elif isinstance(value, list) and value and all(isinstance(x, dict) and "id" in x for x in value):
        for child in value:
            yield from leaves(child, prefix + "/@" + child["id"])
    else:
        yield prefix


def ordered(task):
    nodes = task.get("stages")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("交接单缺 stages")
    by_id = {}
    owners = []
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("阶段须为对象")
        key = node.get("id")
        if not isinstance(key, str) or not key.strip() or key in by_id:
            raise ValueError("阶段 ID 缺失或重复")
        if (not isinstance(node.get("needs"), list)
                or not all(isinstance(x, str) and x for x in node["needs"])
                or len(set(node["needs"])) != len(node["needs"])):
            raise ValueError("阶段 needs 须为无重复依赖清单")
        fields, artifacts = node.get("fields", []), node.get("artifacts", [])
        if not isinstance(fields, list) or not isinstance(artifacts, list) or not (fields or artifacts):
            raise ValueError("阶段须绑定实际字段或产物")
        for field in fields:
            if not isinstance(field, str) or not field.startswith("/"):
                raise ValueError("无效阶段字段")
            if any(field == old or field.startswith(old + "/") or old.startswith(field + "/") for old in owners):
                raise ValueError("阶段字段重复归属：" + field)
            owners.append(field)
        if not all(isinstance(x, str) and x for x in artifacts):
            raise ValueError("产物路径无效")
        by_id[key] = node
    result, visiting = [], set()

    def visit(key):
        if key not in by_id:
            raise ValueError("阶段依赖不存在：" + key)
        if key in visiting:
            raise ValueError("阶段依赖循环：" + key)
        if key in result:
            return
        visiting.add(key)
        for parent in by_id[key]["needs"]:
            visit(parent)
        visiting.remove(key)
        result.append(key)

    for key in by_id:
        visit(key)
    return [by_id[key] for key in result]


def snapshot(node, brief, base, reports):
    files = []
    for name in node.get("artifacts", []):
        path = (base / name).resolve(strict=True)
        files.append({"path": str(path), "sha256": file_digest(path)})
    result = {"definition": {key: node.get(key, []) for key in ("id", "needs", "fields", "artifacts")},
              "fields": {field: select(brief, field) for field in node.get("fields", [])},
              "artifacts": files, "dependencies": {key: reports[key]["receipt"] for key in node["needs"]}}
    start = reports.get(START_STAGE, {}).get("current")
    listening_binding = ({"singing_method": start["artifacts"][0]["sha256"],
                          "required_reference": start["audition"]["reference_sha256"]}
                         if start and needs_preview(brief) else {})
    if node["id"] == START_STAGE and needs_preview(brief):
        result["audition"] = review_start(files, brief)
    if node["id"] == PREVIEW_STAGE and needs_preview(brief):
        review_preview(files, brief, **listening_binding)
        result["previewed_brief"] = fingerprint(brief)
    if node["id"] == REPRESENTATIVE_STAGE and needs_representative(brief):
        review_representative(files, brief, **listening_binding)
    return result


def check_event_dependencies(nodes, brief):
    """A picture cannot stay reusable after its causal event owner changes."""
    def owner(pointer):
        matches = [n['id'] for n in nodes for field in n.get('fields', [])
                   if pointer == field or pointer.startswith(field + '/')]
        return matches[0] if len(matches) == 1 else None

    by_id = {n['id']: n for n in nodes}

    def ancestors(key):
        found = set()
        for parent in by_id[key]['needs']:
            found.add(parent); found.update(ancestors(parent))
        return found

    def require_dependency(child, parent, label):
        if not child or not parent:
            raise ValueError('事件依赖缺少完整字段归属：' + label)
        if child != parent and parent not in ancestors(child):
            raise ValueError('事件依赖遗漏：' + child + ' 必须消费 ' + parent + '（' + label + '）')

    esc = lambda value: value.replace('~', '~0').replace('/', '~1')
    for unit in brief.get('content_adaptation', {}).get('units', []):
        event = owner('/content_adaptation/units/@' + esc(unit['id']))
        picture = owner('/shots/@' + esc(unit['shot']) + '/sceneAsset')
        require_dependency(event, owner('/script'), unit['id'] + '/script')
        for key in unit['requirements']:
            require_dependency(event, owner('/requirements/@' + esc(key)), unit['id'] + '/' + key)
        require_dependency(picture, event, unit['id'] + '/picture')


def inspect(task, path, brief=None):
    path = Path(path).resolve()
    if brief is None:
        brief = json.loads((path.parent / task["brief"]).read_text())
    if task.get("project") != brief.get("id"):
        raise ValueError("阶段交接与作品身份不符")
    brief = normalized(brief)
    nodes = ordered(task)
    check_event_dependencies(nodes, brief)
    by_id = {node["id"]: node for node in nodes}
    ancestors = {}
    for node in nodes:
        parents = node["needs"]
        ancestors[node["id"]] = set(parents).union(*(ancestors[key] for key in parents))
    review_dependencies = {}
    missing = []
    if needs_preview(brief):
        if PREVIEW_STAGE not in by_id:
            missing.append(PREVIEW_STAGE)
        if START_STAGE not in by_id:
            missing.append(START_STAGE)
        review_dependencies[PREVIEW_STAGE] = [START_STAGE]
    if needs_representative(brief):
        if REPRESENTATIVE_STAGE not in by_id:
            missing.append(REPRESENTATIVE_STAGE)
        if needs_preview(brief):
            review_dependencies[REPRESENTATIVE_STAGE] = [START_STAGE]
            review_dependencies[PREVIEW_STAGE].append(REPRESENTATIVE_STAGE)

    reports = {}
    for node in nodes:
        key = node["id"]
        dependency_issues = [f"{key} 须依赖 {parent}"
                             for parent in review_dependencies.get(key, []) if parent not in ancestors[key]]
        if key == START_STAGE and needs_preview(brief) and node["needs"]:
            dependency_issues.append(START_STAGE + " 须在整曲和代表段审查之前独立确认")
        missing.extend(dependency_issues)
        issues = []
        parents = [parent for parent in node["needs"] if reports[parent]["status"] != "reusable"]
        if parents:
            issues.append("依赖未就绪：" + ", ".join(parents))
        issues.extend(dependency_issues)
        current = None
        if not dependency_issues and not (parents and key in review_dependencies):
            try:
                current = snapshot(node, brief, path.parent, reports)
            except (OSError, ValueError) as error:
                issues.append(str(error))
        confirmed = node.get("confirmed")
        if confirmed is None:
            issues.append("尚未确认实际产物")
        elif current != confirmed:
            issues.append("字段、产物或依赖已变化；需显式 reopen-stage")
        reports[key] = {"status": "stale" if issues else "reusable", "issues": issues, "needs": node["needs"],
                        "receipt": fingerprint(confirmed) if confirmed else None,
                        "current": current, "dependencies_ready": not parents and not dependency_issues}
    fields = [field for node in nodes for field in node.get("fields", [])]
    uncovered = [leaf for leaf in leaves(brief) if not any(leaf == field or leaf.startswith(field + "/") for field in fields)]
    ready = not missing and all(row["status"] == "reusable" for row in reports.values()) and not uncovered
    return {"status": "ready" if ready else "blocked", "task": str(path),
            "reusable": [key for key, row in reports.items() if row["status"] == "reusable"],
            "next_stages": missing + [key for key, row in reports.items() if row["status"] != "reusable" and row["dependencies_ready"]],
            "missing_stages": missing,
            "unowned_fields": uncovered, "stages": reports,
            "verified": "file_hashes_field_values_and_dependencies_only", "model_request_sent": False,
            "render_started": False}


def require(brief, base):
    check_diagnostic_scope(brief)
    ref = brief.get("stage_handoff")
    if ref is None:
        if needs_preview(brief):
            raise ValueError("知识歌曲整片须先绑定阶段交接及 " + START_STAGE + "、" + PREVIEW_STAGE)
        if needs_representative(brief):
            raise ValueError("整片须先绑定阶段交接及 " + REPRESENTATIVE_STAGE)
        return {"status": "legacy_untracked", "protection": False}
    if not isinstance(ref, dict) or not isinstance(ref.get("task"), str):
        raise ValueError("stage_handoff 须绑定原 workflow task")
    path = (Path(base) / ref["task"]).resolve(strict=True)
    task = json.loads(path.read_text())
    report = inspect(task, path, brief)
    if report["status"] != "ready":
        bad = report["missing_stages"] + [key for key, row in report["stages"].items() if row["status"] != "reusable"]
        review_issues = [report["stages"].get(key, {}).get("issues", [])
                         for key in (START_STAGE, REPRESENTATIVE_STAGE, PREVIEW_STAGE)]
        preview_detail = "".join("；" + issues[0] for issues in review_issues if issues)
        raise ValueError("阶段交接未就绪：" + ", ".join(bad) + "; 未归属字段：" + ", ".join(report["unowned_fields"])
                         + preview_detail
                         + "；读取 workflow，只重开失效阶段，复用 " + ", ".join(report["reusable"]))
    return report


def context(report, stage):
    if stage not in report["stages"]:
        raise ValueError("阶段不存在：" + stage)
    row = report["stages"][stage]
    current = row["current"]
    parents = row["needs"]
    return {"stage": stage, "decision": "reuse" if row["status"] == "reusable" else
            "work_on_this_stage" if row["dependencies_ready"] else "resolve_changed_dependencies",
            "issues": row["issues"], "existing_output": current,
            "inputs": {key: report["stages"][key]["current"] for key in parents
                       if report["stages"][key]["status"] == "reusable"},
            "preserve_without_replanning": [key for key in report["reusable"] if key != stage],
            "next_stages": report["next_stages"], "unowned_fields": report["unowned_fields"],
            "model_request_sent": False, "render_started": False}


def update(path, confirm=None, reopen=None, reason=None, evidence=None):
    path = Path(path).resolve(strict=True)
    with path.with_suffix(path.suffix + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        task = json.loads(path.read_text())
        nodes = ordered(task)
        key = confirm or reopen
        node = next((node for node in nodes if node["id"] == key), None)
        if node is None:
            raise ValueError("阶段不存在：" + str(key))
        if reopen:
            if not reason or not reason.strip() or not evidence:
                raise ValueError("重开阶段须有原因和实际反例文件 --reason / --evidence")
            source = Path(evidence).resolve(strict=True)
            change = {"stage": reopen, "reason": reason, "evidence": str(source),
                      "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
            affected = {reopen}
            for row in nodes:
                if affected.intersection(row["needs"]):
                    affected.add(row["id"])
                if row["id"] in affected and "confirmed" in row:
                    row.setdefault("history", []).append({"confirmed": row.pop("confirmed"), "change": change})
        else:
            report = inspect(task, path)
            state = report["stages"][confirm]
            if not state["dependencies_ready"]:
                raise ValueError("阶段依赖尚未就绪：" + "; ".join(state["issues"]))
            if state["status"] == "reusable":
                return report
            if node.get("confirmed") is not None:
                raise ValueError("已有确认发生变化，先 reopen-stage 并保留反例")
            if state["current"] is None:
                raise ValueError("实际阶段产物不可用：" + "; ".join(state["issues"]))
            node["confirmed"] = state["current"]
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(task, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return inspect(task, path)
