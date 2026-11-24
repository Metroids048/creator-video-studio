"""Read-only routing hints. Codex owns semantic intent and permission."""
import re


# Phrase evidence is deliberately conservative. The conversation can supply a profile.
PROJECT_REVIEW = re.compile(
    r"项目级复盘|(?:整个|整体|全)项目.{0,8}(?:复盘|审查|审计)"
    r"|(?:复盘|审查|审计)(?:一下|这个|整个|整体|全部|全)?(?:视频制作)?项目"
    r"|项目(?:架构|能力|设计)(?:审查|复盘|审计)"
    r"|(?:工程化|工作流|工作流程).{0,12}复盘"
    r"|(?:整个|整体|整套)(?:的)?视频工作流程"
)
PROFILES = {
    "framework": ("development", r"底座|框架|意图识别|路由匹配|路由管理|样片目录|风格模板|模板目录|模板封装|项目收尾|(?:改|整改|修复|优化)项目|项目.{0,5}(?:workflow|工作流)|装(?:一下)?(?:依赖|[Ss]kills?)|资源补齐|框架验收|" + PROJECT_REVIEW.pattern),
    "research": ("research", r"(?:只|先)(?:想|要)?(?:做)?(?:研究|调研)|(?:研究|调研)(?:方向|选题|起号)|只看方向"),
    "reference": ("research", r"参考|对标|逆向|拆解|表达方法|模仿|借鉴"),
    "restore-native": ("recovery", r"原样恢复|(?:恢复|导入|找回|接手).{0,20}(?:原生工程|原工程|工程包|时间线|\.zip\b)"),
    "resume-unknown": ("recovery", r"断流|状态未知|(?:继续|查).{0,8}(?:未完|上一单|上次的任务)|回执|之前.*(?:没结束|不知)"),
    "revision": ("design", r"只改|局部返修|锁住|锁轨|改中间|原样保留其他"),
    "review": ("development", r"审片|验片|审查成片|验收成片|检查成片|听审"),
    "publish": ("delivery", r"标题|封面|标签|发布包|发布文案|发布包装|发布预览"),
    "analytics": ("research", r"复盘|数据分析|播放数据|后台数据|互动数据|流量分析"),
    "delivery": ("delivery", r"发布包|交付包|导出|发布|上传"),
    "mixed": ("design", r"混用|混剪|混合镜头|组合镜头|代码.{0,18}(?:录屏|已有媒体|生成镜头)"),
    "generated": ("design", r"生成.{0,8}(?:视频|镜头)|生成式镜头|文生视频|图生视频|Seedance|Kling|可灵"),
    "image": ("design", r"生图|生成.{0,8}(?:图片|图像)|文生图|海报|主视觉"),
    "commerce": ("design", r"电商|商品演示|产品发布|广告片|品牌片|招商|品牌商单|SaaS"),
    "mv-silent": ("design", r"歌词|\bMV\b|无(?:对白|旁白|人声)|纯音乐|静音也能|图片卡点|照片卡点|图文共鸣|图文拼贴|照片拼贴|翻页画册|图片转场|图片混剪"),
    "edit": ("design", r"录屏|已有视频|保留.{0,8}操作|剪辑|现有素材|(?<![A-Za-z0-9])(?:AVS|ChatCut)(?![A-Za-z0-9])"),
    "storybook": ("design", r"绘本|故事书|漫剧|二维故事|水彩故事|纸片人|火柴人|线稿|Nook"),
    "art-motion": ("design", r"花叔|huashu|艺术动效|艺术动画|参数化(?:动效|动画)"),
    "explainer": ("design", r"讲解|科普|知识短片|工作原理|图解|机制|蓝书|蓝叔|Lanshu"),
    "motion-graphics": ("design", r"(?<![A-Za-z0-9])(?:MG|Remotion|HyperFrames?)(?![A-Za-z0-9])|代码动画|图表动效|字幕动效"),
    "theme": ("design", r"主题|题目|原创|做(?:一|个|一条|一个)|拍(?:一|个|一条|一个)"),
}
DEFERRED = re.compile(
    r"不(?:着急|急着?|需要|要|用|能|许|准)?(?:做(?:视频|成片|样片|(?=$|[，,。；;！？!?\s]))|制作|渲染|剪辑|导出|发布|上传|生成(?:视频|镜头)?)"
    r"|(?:先别|暂缓|暂不|别)(?:着急|急着)?(?:做(?:视频|成片|样片|(?=$|[，,。；;！？!?\s]))|制作|渲染|发布|上传|生成)"
    r"|(?:先)?不(?:用)?着急(?:做)?"
)
RESEARCH_ONLY = re.compile(r"(?:只|仅)(?:想|要|做)?(?:先)?(?:研究|调研)|只看方向")
FRAMEWORK_ONLY = re.compile(r"(?:只|仅)(?:做|想|要)?(?:搭|做)?(?:框架|底座)|先.{0,5}(?:搭|补齐)(?:项目)?(?:框架|底座)")
ORDER = ("framework", "research", "restore-native", "resume-unknown", "revision", "review", "analytics", "publish",
         "reference", "mixed", "commerce", "mv-silent", "edit", "storybook", "art-motion", "explainer",
         "motion-graphics", "generated", "image",
         "delivery", "theme")


def route_task(studio, request, profile=None, script=""):
    if not isinstance(request, str) or not request.strip():
        raise ValueError("请提供用户原始需求")
    index = studio.load(studio.CAPABILITY_INDEX)
    # Evaluate the positive part of every clause after removing deferred actions.
    deferred = list(dict.fromkeys(DEFERRED.findall(request)))
    from video_templates import match, routing_text
    positive, _ = routing_text(DEFERRED.sub("", request))
    matches = {
        name: list(dict.fromkeys(re.findall(pattern, positive, re.IGNORECASE)))[:5]
        for name, (_, pattern) in PROFILES.items()
    }
    candidates = [name for name in ORDER if matches[name]]
    selected = profile or (candidates[0] if candidates else None)
    new_creation = re.search(
        r"(?:做|制作|拍|生成)(?:一[条支部个段]|新的?)[^，。；;\n]{0,12}(?:视频|短片|动画|广告片|MV)",
        positive, re.IGNORECASE,
    )
    # Packaging mentioned alongside an explicit new video must not replace its
    # original creation route. These are still hints, never execution permission.
    if not profile and new_creation and selected in {"publish", "analytics"}:
        selected = next((name for name in candidates if name not in {"publish", "analytics"}), None)
    # A profile supplied by Codex can improve semantic matching, but cannot erase a
    # research/framework-only instruction or bypass the workflow/production guards.
    if FRAMEWORK_ONLY.search(request):
        selected = "framework"
    elif RESEARCH_ONLY.search(request):
        selected = "research"
    elif profile != "research" and matches["framework"] and deferred:
        selected = "framework"
    tools = studio.local_tools()
    entry = index["intent_profiles"].get(selected)
    routes = {name: studio.inspect_capability(index["routes"][name], tools)
              for name in entry["routes"]} if entry else {}
    packs = {}
    if entry:
        pack_names = list(entry["packs"])
        if selected not in {"restore-native", "resume-unknown", "review", "delivery", "analytics"}:
            pack_names.append("visual-design")
        if selected in {"framework", "theme", "explainer", "storybook", "art-motion", "motion-graphics", "mv-silent", "commerce", "mixed", "generated"}:
            pack_names.append("style-templates")
        if selected in {"research", "reference"}:
            for topic in ("reference", "storybook", "art-motion", "explainer", "motion-graphics",
                          "mv-silent", "commerce", "edit"):
                if matches[topic]:
                    pack_names.extend(index["intent_profiles"][topic]["packs"])
        if selected == "mixed" and matches["generated"]:
            pack_names.append("external")
        if selected == "publish" and matches["analytics"]:
            pack_names.append("analytics")
        if selected == "analytics" and matches["publish"]:
            pack_names.append("publish")
        if new_creation:
            pack_names.extend(name for name in ("publish", "analytics") if matches[name])
        for name in dict.fromkeys(pack_names):
            pack = index["skill_packs"][name]
            paths = [pack["skill"], *pack["reads"]]
            missing = [path for path in paths if not (studio.ROOT / path).is_file()]
            packs[name] = {**pack, "missing": missing}
    # New work starts from a bounded reference form; an existing draft is retained.
    fixed_adaptation = re.search(
        r"固定(?:原)?工程|(?:沿用|指定|套用|复用).{0,12}(?:工程|模板)", positive)
    reference_first = selected in {
        "theme", "storybook", "explainer", "art-motion", "motion-graphics",
        "mv-silent", "commerce", "mixed", "generated"}
    maintenance_only = selected == "framework" and (bool(deferred) or bool(PROJECT_REVIEW.search(positive)))
    return {
        "profile": selected, "selection": ("codex" if profile and profile == selected
                                           else "phrase_hint" if selected else "needs_codex_scope"),
        "candidate_profiles": [{"profile": name, "evidence": matches[name]} for name in candidates],
        "deferred_actions": deferred, "suggested_mode": PROFILES[selected][0] if selected else "design",
        "next": ("adapt_within_fixed_template" if fixed_adaptation else "select_reference_and_scope")
                if reference_first else entry["next"] if entry else "codex_confirm_goal_and_inputs",
        "packs": packs, "routes": routes, "model_config": studio.model_route(),
        "model_session_verified": False, "model_request_sent": False, "render_started": False,
        "execution_authorized_by_route": False,
        "template_match": ({"applicable": False, "reason": "本轮维护项目路线，不匹配或创建新作品",
                            "render_started": False} if maintenance_only else
                           match(request, "9:16" if re.search(r"9[:：]16|竖屏", request) else "16:9", studio.ROOT, script=script)
                           if selected not in {"restore-native", "resume-unknown", "revision", "review", "delivery", "edit", "publish", "analytics", "image"}
                           else {"applicable": False, "reason": "图片先定视觉方向与参考角色" if selected == "image" else "沿原工程、素材或版本处理，不重新匹配模板", "render_started": False}),
        "template_gallery": "templates/gallery/index.html",
        "creation_order": ["既有具体参考/指定模板与受众用途", "核对完整形式及可编辑工程边界", "获准后做对标基准并确认实际效果（已有合格基准复用）", "冻结风格与结构，模板内发展内容和脚本", "换稿最难代表段及同版完整验收", "该形式成立后持续复用，再扩下一形式"],
    }
