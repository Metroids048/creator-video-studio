"""Read-only handoff for structured decisions made in the Codex conversation."""
import importlib.util
from pathlib import Path
import subprocess
import sys


ACTIONS = {
    "research": {"research"},
    "plan": {"design", "research", "development", "production"},
    "create": {"production"},
    "inspect": {"design", "research", "development", "recovery", "production", "delivery"},
    "restore": {"recovery"},
    "continue": {"recovery", "production"},
    "revise": {"production"},
    "review": {"development", "production", "delivery"},
    "export": {"delivery"},
    "publish": {"delivery"},
    "analytics": {"research", "development", "delivery"},
}
CHECKS = {"structure", "decode", "playback", "visual", "listening", "content", "user", "platform"}


def handoff(studio, path, mode):
    task = studio.load(path)
    action = task["action"]
    if mode not in ACTIONS.get(action, ()):
        raise ValueError(f"{action} 与当前 --mode {mode} 不匹配")
    if not isinstance(task.get("request"), str) or not task["request"].strip():
        raise ValueError("交接单需保留用户原始需求")
    locks = task.get("locks", [])
    if not isinstance(locks, list) or not all(isinstance(lock, str) and lock.strip() for lock in locks):
        raise ValueError("locks 需为可定位的锁定项清单")
    base = path.resolve().parent

    def local(key):
        return (base / task[key]).resolve(strict=True)

    project = studio.identifier(task["project"]) if "project" in task else None
    result = {"action": action, "mode": mode, "project": project, "locks": locks, "checks": {},
              "blockers": [], "model_config": studio.model_route(), "model_session_verified": False,
              "model_request_sent": False, "render_started": False}
    checks, blockers = result["checks"], result["blockers"]
    route = task.get("route")
    brief = studio.load(local("brief")) if "stages" in task or (
        action in {"plan", "create"} and task.get("brief")) else {}
    from knowledge_song import START_STAGE, required as needs_song_preview
    if "stages" in task:
        from stage_handoff import inspect as inspect_stages
        stage_report = result["stage_handoff"] = inspect_stages(task, path, brief)
        if needs_song_preview(brief) and START_STAGE not in stage_report["reusable"]:
            start = stage_report["stages"].get(START_STAGE, {})
            blockers.extend(start.get("issues") or ["缺知识歌曲开工阶段：" + START_STAGE])
            return {**result, "next": "confirm_song_start", "stop_at": START_STAGE}
        if stage_report["status"] != "ready":
            blockers.extend(stage_report["next_stages"])
            blockers.extend("未归属字段：" + field for field in stage_report["unowned_fields"])
            return {**result, "next": "consume_stage_handoff", "stop_at": "stage_handoff"}
        if route is None and action in {"plan", "create"}:
            route = brief.get("route", "code")
        if route == "native-knowledge" and action in {"plan", "create", "inspect"}:
            from native_knowledge import check as check_native_knowledge
            source = Path(studio.load(local("brief"))["native_root"]).resolve(strict=True)
            _, result["stage_handoff"] = check_native_knowledge(studio, source, path)
            return {**result, "next": "native-knowledge render", "stop_at": "native_production"}
    elif needs_song_preview(brief):
        blockers.append("缺知识歌曲开工阶段：" + START_STAGE)
        return {**result, "next": "confirm_song_start", "stop_at": START_STAGE}
    if action in {"plan", "create"} and route in {None, "code"} and "stages" not in task:
        from video_templates import match

        routing_input = brief
        script = (local("script_file").read_text() if task.get("script_file")
                  else routing_input.get("script", task.get("script", "")))
        result["template_route"] = match(routing_input.get("request", task["request"]),
                                         task.get("format", "16:9"), studio.ROOT, script,
                                         task.get("routing_purpose", "production"))
        result["template_gallery"] = "templates/gallery/index.html"
    routes = studio.load(studio.CAPABILITY_INDEX)["routes"]
    if route is not None and route not in routes:
        raise ValueError(f"能力索引未登记路线：{route}")
    if route == "avs-render":
        route = "avs"
        result["route_alias"] = "avs-render"
    native_input = {"nook": "scene", "art": "spec", "lanshu": "story"}.get(route)
    inspect_native_input = (action in {"inspect", "continue"} and native_input is not None
                            and bool(task.get(native_input)) and "external_task" not in task)
    if action == "research":
        return {**result, "next": "reference_evidence", "stop_at": "research_delivery"}
    if action in {"publish", "analytics"}:
        from publishing import plan as publication_plan
        from content_analytics import report as analytics_report

        if action == "publish":
            spec, _, _, target = publication_plan(studio, local("spec"))
            checks["publication"] = {"source": spec["source"], "target": str(target)}
            from publishing import packaging_quality
            checks["quality"] = packaging_quality(spec)
            from content_strategy import publication, creative_contract
            checks["editorial"] = creative_contract(publication(studio, spec, local("spec")))
            if project != spec["source"]["project"] or task.get("version") != spec["source"]["version"]:
                raise ValueError("交接与发布包来源版本不符")
        else:
            checks["analytics"] = analytics_report(studio, local("package"), local("metrics") if task.get("metrics") else None,
                                                  feedback_path=local("feedback") if task.get("feedback") else None)
            binding = checks["analytics"]["publication"]
            if project != binding["project"] or task.get("version") != binding["version"]:
                raise ValueError("交接与复盘来源版本不符")
        return {**result, "next": "publish-pack" if action == "publish" else "content-review",
                "stop_at": "offline_package" if action == "publish" else "local_review",
                "upload_started": False, "published": False}
    if action == "restore":
        if not project:
            raise ValueError("原样恢复需明确目标作品 ID")
        checks["bundle"] = studio.inspect_bundle(local("bundle"))
        return {**result, "next": "import-native", "stop_at": "native_import"}
    if action in {"inspect", "continue", "revise", "review", "export"} and not inspect_native_input:
        if "external_task" in task:
            external = task["external_task"]
            if not external.get("id") or not external.get("provider"):
                raise ValueError("外部任务需原 provider 和 task ID")
            checks["external_task"] = {"id": external["id"], "provider": external["provider"], "status": "unknown"}
            blockers.append("外部状态未经当前入口查询，保留原任务回执")
            return {**result, "next": "check_original_receipt", "stop_at": "status"}
        if route == "avs":
            if not task.get("episode"):
                blockers.append("缺原生 Episode 标识，不能用工作室作品 ID 代替")
            else:
                checks["episode"] = studio.inspect_avs(task["episode"])
                if action == "continue" and checks["episode"]["next_action"]["execution"] == "not_connected":
                    blockers.append("AVS 当前阶段的原生命令尚未开放，不能自动续跑或跳过")
            next_stage = checks.get("episode", {}).get("next_action", {}).get("stage")
            if action == "revise":
                blockers.append("AVS 返修先按原生 findings 修改作品副本；不自动 reset 或覆盖有效版本")
            elif action == "review" and next_stage not in {"visual-review", "creative-review", "creative-gate", "approve"}:
                blockers.append("当前 AVS 阶段不在审查关口，先核原生下一步")
            elif action == "export" and next_stage != "export":
                blockers.append("当前 AVS 尚未到原生 export，先完成同版审查、用户确认和交付")
            return {**result, "route": route, "next": "inspect_native_records",
                    "stop_at": "native_status"}
        if route not in {None, "code", "editor", "vibe"}:
            blockers.append("此路线没有工作室版本状态；先按原生计划核对输入，不能用通用 current 推断阶段")
            checks["native_entry"] = {"entry": routes[route]["entry"], "source": routes[route]["source"],
                                      "integration": routes[route]["integration"]}
            return {**result, "route": route, "next": "native_plan", "stop_at": "native_status"}
        if not project:
            raise ValueError(f"{action} 需指定作品")
        if task.get("route") == "vibe":
            from vibe import workspace

            checks["native_workspace"] = workspace(project, task.get("template"))
            if not checks["native_workspace"]["exists"]:
                blockers.append("Vibe 原生工程不存在")
            if action == "continue" and checks["native_workspace"]["missing_contracts"]:
                blockers.append("Vibe 原生交接记录不齐，不能依据媒体文件推断续做阶段")
            if action not in {"inspect", "continue"}:
                blockers.append("Vibe 返修/审查/导出仍用原生工程记录；不能冒用工作室 current 版本")
            return {**result, "route": "vibe", "next": "inspect_native_records",
                    "stop_at": "native_status"}
        status = studio.inspect_project(project)
        checks["project"] = status
        if action == "continue":
            return {**result, "next": "resume" if status["pending"] and mode == "production" else "status",
                    "stop_at": "status" if mode == "recovery" else "local_attempt_review"}
        if action == "inspect":
            return {**result, "next": "report_status", "stop_at": "status"}
        if action == "revise":
            if not task.get("version") or not locks:
                raise ValueError("局部返修需要父版及明确锁定项")
            if task["version"] != (status["current"] or ("import" if status["native_import"] else None)):
                raise ValueError("局部返修父版与当前工程不符")
            if status["pending"]:
                blockers.append("有本地未完候选，先核对并处理原尝试")
            edit_kind = task.get("edit_kind")
            if edit_kind == "native" and "patch" in task:
                project_path = studio.works_root() / project
                patch_file = local("patch")
                patch = studio.load(patch_file)
                if patch["base"] != task["version"]:
                    raise ValueError("交接单父版与原生补丁不一致")
                locked = task.get("locked")
                sections = {"clips", "audio", "captions", "overlays", "transitions", "output"}
                if (not isinstance(locked, list) or not locked
                        or not all(isinstance(track, str) and track in sections for track in locked)):
                    raise ValueError("原生返修交接单需将锁定项映射为 locked 轨道")
                if not isinstance(patch.get("locked"), list) or not set(locked) <= set(patch["locked"]):
                    raise ValueError("补丁遗漏交接单锁定轨道")
                checks["native_patch"] = studio.plan_native_edit(project_path, patch_file)["changed"]
                checks["locked"] = locked
                checks["patch_sha256"] = studio.digest(patch_file)
            elif edit_kind == "picture" and "patch" in task:
                patch_file = local("patch")
                patch = studio.load(patch_file)
                if patch.get("base") != task["version"] or not patch.get("shot"):
                    raise ValueError("画面补丁须绑定同一父版及目标镜头")
                studio.picture_brief(studio.works_root() / project / "versions" / task["version"],
                                     patch, patch_file, preview_only=True)
                checks["picture_patch"] = {"shot": patch["shot"], "fields": sorted(patch["visual"])}
                checks["patch_sha256"] = studio.digest(patch_file)
            else:
                blockers.append("缺少 picture 或 native 的实际补丁")
            return {**result, "next": "review_patch" if not blockers else "resolve_blockers",
                    "stop_at": "patch_handoff"}
        if action == "review":
            checks["review"] = check_review(studio, local("review"))
            if checks["review"]["project"] != project or (
                task.get("version") and checks["review"]["version"] != task["version"]
            ):
                raise ValueError("审查记录与任务版本不符")
            return {**result, "next": "report_review_coverage", "stop_at": "review"}
        if not status["current"] or task.get("version") != status["current"]:
            blockers.append("须明确绑定当前候选版本；可交付状态另核同版质量审查")
        if (status.get("quality") or {}).get("status") != "reviewed":
            blockers.extend((status.get("quality") or {}).get("blockers", ["缺少同版质量审查"]))
        return {**result, "next": "resolve_blockers" if blockers else "export", "stop_at": "local_delivery"}

    if route is None:
        return {**result, "next": "select_reference_and_scope", "stop_at": "creative_plan"}
    result["route"] = route
    capability = studio.inspect_capability(routes[route], studio.local_tools())
    checks["capability"] = capability
    if capability["check"] == "missing_dependencies":
        blockers.append("路线有缺失依赖，见 capability")
    if "brief" in task:
        brief = local("brief")
        if action == "create" and studio.load(brief).get("purpose") == "self-media" and not studio.load(brief).get("stage_handoff"):
            blockers.append("新自媒体交接缺 stage_handoff，先确认实际阶段产物")
        checks["brief"] = studio.plan(brief)
        if task.get("purpose") == "self-media" and checks["brief"]["editorial"]["status"] != "ready":
            blockers.append("自媒体策划未绑定就绪的受众与选题简报")
        if action == "create":
            from video_templates import check_binding

            try:
                checks["template"] = check_binding(studio.load(brief), studio.ROOT, require_selection=True)
            except ValueError as error:
                blockers.append(str(error))
        for engine, dependency in checks["brief"]["engine_capabilities"].items():
            if dependency["check"] == "missing_dependencies":
                blockers.append(f"{engine} 镜头有缺失依赖，见 brief.engine_capabilities")
        if route != checks["brief"]["route"] or (project and project != checks["brief"]["id"]):
            raise ValueError("交接单路线或作品与 brief 不符")
        result["project"] = checks["brief"]["id"]
        if (action == "create" and task.get("allow_legacy_scene") is not True
                and any(scene["source"] == "legacy-sample" for scene in checks["brief"]["scenes"])):
            blockers.append("新作品须为代码镜头提供自己的场景，或在确认范围后复用旧模板")
    elif route in {"code", "editor"}:
        blockers.append("缺工作室 brief")
    if route == "avs":
        if task.get("episode"):
            checks["episode"] = studio.inspect_avs(task["episode"])
            if checks["episode"]["next_action"]["execution"] == "not_connected":
                blockers.append("AVS 当前阶段的原生命令尚未开放，不能自动续跑或跳过")
        else:
            blockers.append("缺原生 Episode 标识")
    elif route == "lanshu":
        from lanshu import story_binding

        story = task.get("story", "kv-cache")
        local_story = base / story
        checks["lanshu"] = story_binding(task.get("style", "all"),
                                         str(local_story) if local_story.is_dir() else story)
        if not inspect_native_input:
            blockers.append("Lanshu 制作须用 code brief 的 engine=lanshu、style、sceneAsset=story JSON 和作品自己的 beatsAsset")
    elif route == "vibe":
        if task.get("template") not in {"lyric-mv", "knowledge-short"} or not project:
            blockers.append("Vibe 需作品 ID 与原生模板 lyric-mv 或 knowledge-short")
        else:
            from vibe import workspace

            checks["native_workspace"] = workspace(project, task["template"])
            if action == "create" and checks["native_workspace"]["exists"]:
                blockers.append("Vibe 原生工程已存在，先检查，不能覆盖初始化")
    elif route == "nook":
        from nook import plan as nook_plan

        if task.get("scene"):
            checks["scene"] = nook_plan(local("scene"))
            if checks["scene"]["unresolved_constants"]:
                blockers.append("Nook 参数含动态或导入值，须补齐可静态核对的原生配置")
            if checks["scene"]["host_specific_paths"]:
                blockers.append("Nook 场景仍引用其他宿主路径，须在作品副本显式适配素材或字体")
        else:
            blockers.append("缺 Nook 原生场景路径 scene")
        if action == "create":
            blockers.append("Nook 制作须用 code brief 的 engine=nook 镜头，以绑定作品版本和原生包")
    elif route == "art":
        if not task.get("spec"):
            blockers.append("缺花叔艺术动效的原生 JSON spec")
        elif capability["check"] != "missing_dependencies":
            spec = local("spec")
            if spec.suffix != ".json":
                raise ValueError("花叔片段 spec 须为 .json 文件")
            try:
                lint = subprocess.run([sys.executable, "-IB", studio.ROOT / capability["entry"], spec, "--strict"],
                                      capture_output=True, text=True, encoding="utf-8", timeout=15)
            except subprocess.TimeoutExpired as error:
                raise ValueError("花叔片段校验超时，先核对 spec 后再检查") from error
            checks["art_spec"] = {"path": str(spec), "valid": lint.returncode == 0,
                                  "findings": lint.stdout.strip() or lint.stderr.strip()}
            if lint.returncode:
                blockers.append("原生片段 spec 校验未通过")
            else:
                assets = art_assets(studio, spec)
                checks["art_assets"] = assets
                if "error" in assets:
                    blockers.append("原生片段素材依赖不齐，见 art_assets")
                if assets["remote_assets"]:
                    blockers.append("片段引用未落地的远端素材；需另行取回并核来源，不在计划检查中联网")
        if action == "create":
            blockers.append("花叔制作须用 code brief 的 engine=art、sceneAsset=spec JSON 和 sceneAssets，以绑定作品版本与原生包")
    elif route in {"avs-render", "research", "external"}:
        blockers.append("本路线当前不开放生产")
    if task.get("commerce"):
        argv = (studio.BIN / "node", studio.ADAPTERS / "commerce-plan.mjs", path.resolve())
        checks["commerce"] = studio.json.loads(studio.run(*argv, capture=True))
        if checks["commerce"]["scenario"]["status"] != "resolved":
            blockers.append("商务场景需 Codex 根据证据确认")
    if inspect_native_input:
        checks["native_state"] = {"status": "unknown", "basis": "source_contract_only",
                                  "current": None, "can_resume": False}
        if action == "continue":
            blockers.append("已核原生输入，但没有可核验的原生任务回执；不能推断未完阶段或自动重投")
        return {**result, "next": "resolve_blockers" if blockers else "report_native_inputs",
                "stop_at": "native_status"}
    return {**result, "next": "resolve_blockers" if blockers else "native_handoff", "stop_at": "plan"}


def localize_art(module, data, base, aliases=None, source_base=None):
    """Retain native path/sequence semantics after studio inputs are renamed."""
    allowed = set()
    if aliases:
        original_file, original_dir = module._file, module._dir_frames
        source_base = Path(source_base) if source_base else Path(base)
        # A native pose directory uses original stems (rest/talk), not the IDs
        # assigned when studio imports renamed the files.
        character = (data.get('data') or {}).get('character')
        frames = character if isinstance(character, str) and character not in module.PRESETS else (
            character.get('frames') if isinstance(character, dict) else None)
        if isinstance(frames, str):
            directory_path = (source_base / frames).resolve()
            poses = {Path(key).stem: key for key in sorted(aliases)
                     if Path(key).parent == directory_path and Path(key).suffix.lower() in module.FRAME_EXT}
            if not poses:
                raise ValueError('原生角色帧库未声明素材：' + frames)
            if isinstance(character, str):
                data['data']['character'] = {'frames': poses}
            else:
                character['frames'] = poses
        def file(value, base, allowed, what):
            if not value or str(value).startswith(("data:", "http:", "https:")):
                return original_file(value, base, allowed, what)
            original = str((source_base / value).resolve())
            if original not in aliases:
                raise ValueError("spec 引用了未声明的原素材：" + original)
            return original_file(str(aliases[original]), base, allowed, what)
        def directory(value, base, what):
            original = (source_base / value).resolve()
            candidates = sorted((Path(key), path) for key, path in aliases.items()
                                if Path(key).parent == original and Path(key).suffix.lower() in module.FRAME_EXT)
            return [path for _, path in candidates] or None
        module._file, module._dir_frames = file, directory
        try:
            module.localize(data, base, allowed)
        finally:
            module._file, module._dir_frames = original_file, original_dir
    else:
        module.localize(data, base, allowed)
    return allowed


def art_assets(studio, spec, aliases=None, source_base=None):
    """Reuse the pinned renderer's path semantics without importing the renderer."""
    source = studio.ROOT / "resources/huashu-art-motion/scripts/engine/spec_assets.py"
    module_spec = importlib.util.spec_from_file_location("studio_art_spec_assets", source)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    data = studio.load(spec)
    fields = [data.get("data") or {}, *data.get("cues", [])]
    refs = []
    for field in fields:
        if field.get("image"):
            refs.append(field["image"])
        if isinstance(field.get("frames"), list):
            refs.extend(field["frames"])
    character = (data.get("data") or {}).get("character")
    if isinstance(character, dict) and isinstance(character.get("frames"), dict):
        refs.extend(character["frames"].values())
    remote = sorted({ref for ref in refs if isinstance(ref, str) and ref.startswith(("http:", "https:"))})
    allowed = set()
    result = {"spec_sha256": studio.digest(spec), "local_files": [], "remote_assets": remote,
              "check": "native_path_existence_only", "media_decoded": False}
    try:
        allowed = localize_art(module, data, spec.parent, aliases, source_base)
        if data.get("grammar") == "y4_storytime":
            character = (data.get("data") or {}).get("character")
            frames = character.get("frames") if isinstance(character, dict) else None
            if not isinstance(frames, dict) or not (frames.get("rest") or frames.get("talk")):
                raise ValueError("y4 需要实际角色帧库，且至少有 rest 或 talk；旧预设不能用于此固定版")
    except (OSError, TypeError, ValueError) as error:
        return {**result, "error": str(error)}
    return {**result, "local_files": sorted(allowed)}


def check_review(studio, file):
    evidence = studio.load(file)
    project = studio.identifier(evidence["project"])
    version = evidence["version"]
    if not isinstance(version, str) or not studio.re.fullmatch(r"v[0-9]{4,}", version):
        raise ValueError("审查须绑定确切版本")
    root = studio.works_root() / project
    target = root / "versions" / version
    receipt = studio.check_delivery(target)
    sha = receipt["delivery"]["video.mp4"]
    if evidence["video_sha256"] != sha:
        raise ValueError("审查记录绑定了其他产物，需重新核对")
    if (not isinstance(evidence["checks"], list) or not evidence["checks"]
            or len(evidence["checks"]) > 2000):
        raise ValueError("缺少有效审查条目")
    declared = set()
    for item in evidence["checks"]:
        if (item["layer"] not in CHECKS or item["status"] not in {"observed", "issue", "unobserved"}
                or not isinstance(item["scope"], str) or not item["scope"].strip()
                or not isinstance(item["method"], str) or not item["method"].strip()):
            raise ValueError("审查条目需说明层级、状态、观察范围和方法")
        if item["status"] != "unobserved":
            if not isinstance(item.get("evidence"), str) or not item["evidence"].strip():
                raise ValueError("已有观察需附证据引用")
            declared.add(item["layer"])
    current = studio.load(root / "current.json")["version"] if (root / "current.json").is_file() else None
    return {"project": project, "version": version, "current": current, "is_current": version == current,
            "video_sha256": sha, "declared_observed_layers": sorted(declared),
            "not_observed_in_record": sorted(CHECKS - declared),
            "issues": sum(item["status"] == "issue" for item in evidence["checks"]),
            "verified_here": "artifact_binding_only", "render_started": False}
