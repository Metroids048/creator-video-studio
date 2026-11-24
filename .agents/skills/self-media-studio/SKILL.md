---
name: self-media-studio
description: 在本机 Codex 处理自媒体受众与选题、视频研究与制作、标题封面包装和内容复盘；也用于接手原生工程、检查版本及获准后的制作返修。
---

# 自媒体工作室入口

先按本聊天原要求和最新纠正确定产物、阶段、作品与 owner。项目稳定约定见根 `AGENTS.md`。只读 `STATUS.md` 文首相关条目及本作品当前请求／状态，按缺口补原始证据；不要每轮读取全历史或把过去“只设计／不制作”当当前授权。旧 Skill 全文保留于 `docs/history/context-before-20261116/self-media-studio.before.md`，仅供定位历史，不自动加载。

## 选路与实际交接

1. 用 `python3 scripts/studio.py intent '<原话>'` 找模式、路线和能力包，结合上下文决定，不让关键词覆盖真实动词。研究用 research，方案用 design，开发用 development，原样恢复用 recovery，具体获准制作／返修才用 production，复制已核交付用 delivery。模式参数不授予付费／发布权限。
2. 新内容先核用户参考／指定形式 → 对标基准与固定工程 → 模板内换内容；沿 `templates list/match` 与 `studio-video-templates` 看实际资格，不能以工程数量、标签或主观评分证明成熟。主题不适配时定位缺口，不强套最容易渲染的底座。按需读 [创作与选路](references/创作与选路.md)。

图片、封面、模板视觉升级和模板外方向，先读 [studio-visual-design](../studio-visual-design/SKILL.md)，用 `visual-assets` 消费真实素材与许可；`content-plan` 同时提供设计方法与素材目录。模板负责结构，素材/设计负责具体画面；模板不适配时可先研究并设计独立方向，不硬套近似模板。独立方向仍须关键画面、最难代表段与现有引擎适配，不能伪填模板绕过 make 资格；研究和设计不等于制作授权。
3. 内容开发用 `content-plan --question '<原问题>'` 或已有简报路径，消费其返回的 [整体视频制作工作流](../../../docs/制作配方/视频制作工作流.md) 全文/哈希，以实际输入输出衔接参考、内容、制作、审阅、返修和运营；知识歌曲再加 `--format knowledge-song`，消费实际返回的 [知识歌曲开发](references/知识歌曲开发.md) 和 [首版制作配方](../../../docs/制作配方/知识歌曲首版.md)。content-plan 的正文用于策划，prepare 会另行冻结方法为实际输入；把本题参考、事实/歌词/事件产物加入既有阶段 artifacts 后交接。先消费 `previous_work` 的真实反馈及原版，再改全文、歌词与因果画面，不预编动机来通过校验。已有有效完整稿、指定改编、恢复和返修保留原合同。方法材料在 [原创内容开发](references/原创内容开发.md)、[受众到复盘](references/受众到复盘.md)，仅按本题缺口加载。
4. Codex 自行把逐项要求和全文绑定 source→target 事件及实际镜头，沿 `templates prepare → plan/make/workflow` 消费。自媒体准备输入写 `purpose: self-media`，知识歌曲另写 `content_format: knowledge-song`；prepare 自动生成 `production-method.json`，作为 `studio-production-method` data 输入绑定哈希。plan 返回冻结执行 Prompt、配方正文；知识歌曲还返回已核13个源文件哈希的 V13 工程位置与动作/音乐/分层复用映射。实际读取并将保留函数→本题消费文件→替换事实/资产落实到镜头，不只引用视频路径。新自媒体 make 拒绝缺方法或缺 stage_handoff；失败不保存正式准备目录。沿现有 task 给该输入归属并核事件/镜头依赖，程序不自动确认阶段或判断审美，旧任务恢复不强制迁移。具体依赖合同见 [阶段交接与局部返修](../../../docs/阶段交接与局部返修.md)。`workflow --stage ID` 可复用就用真实原材料；局改先 scene-context，保留相邻连续性，只重开变化依赖及下游。
5. 工程用自己的真实入口与状态：工作室 `status`；Vibe `bash scripts/vibe.sh inspect <id>` 与 gate；AVS `avs-next <Episode>` 和 [AVS交接](references/AVS交接.md)；ZIP `inspect-bundle`。恢复用 `--mode recovery import-native`，回退 select-version；具体获准的未完版本才 resume。外部结果未知先查，不重复提交。不同 owner 不共享 current，也不接管其 execution。

## 原生制作与返修

按镜头选择已有 `vibe/nook/art/lanshu/opuscar`，绑定作品实际 sceneAsset/sceneAssets，Lanshu 另需 beatsAsset；消费原生合同及动效设计 Skill。复用要落到完整动作、镜头、工程和时间线，不能只借渲染器重写文字卡片。

Vibe 原生 `vf build <新版本> --audio=<既有音轨> --audio-sha256=<实际哈希>` 会跳过 score.py；字幕提取／帧缓存／编码／技术 QA 失败必须非零。相同源指纹的帧默认恢复；源变更后明确 fresh 或在删除受影响帧后 keep。已有目标拒绝覆盖。**这是候选生成路径，尚不等同 studio 阶段 DAG 或质量放行。** 技术通过后仍须同版完整审阅，不以 BUILD_CANDIDATE 当交付。

蓝叔／艺术原生画面走 studio 的 `engine: lanshu|art` 镜头，返修整目录复制父版并先按父版回执 `nativeFiles` 核哈希。内容只经声明的 story／beats／sceneAssets 进入；`lanshu/v1-editorial` 另可声明 `pageParams: {captionSize, turn, lead, tail}`。`revise-picture` 合并父版参数，未知键、其他样式、任意 CSS/脚本均拒绝。作品自写导出脚本不进入放行链。独立候选可用 `studio.py status --native-receipt <回执> --source-root <工程根>`（或 `vibe.sh status` 同参数）只读核对成片与已绑定源码；失败返回非零，通过仍不登记、不审片、不核内嵌音轨。

改画保音沿[制作流程](../../../docs/制作流程.md#场景音频和版本合同)：确切父版提取 AAC，brief 声明 `audio.preserveEncoded: true`，输入检查和声音准备拒绝时长不符；最终比较 AAC 数据哈希，WAV 只核自身身份。本片暴露的测量端点、手物接触和相机全路径检查消费同文档的具体反例；逐项实际观察，不以检查表或测试通过宣称高分。

已有 Vibe 成片用 `studio.py --mode recovery --works-root <隔离根> adopt-vibe`，只复制原成片、锁定音轨、字幕，登记根不可位于或包含仓库 works，不改 source／owner。收编不接入原生工程，返修画面须走上面的镜头路径。登记后 status → review-prepare → review-save → export；锁轨哈希变化会拒绝，登记不证明实唱同步、画面解释或用户认可。

声音定版后时间线消费实际演唱，不拿目标歌词当听辨证据；改画面沿锁轨，不默认重唱。返修先 [审查与版本](references/审查与版本.md) 及 studio-video-review；原生先 native-edit-plan，代码画面指定父版／镜头。代表段的原因、动作或连续性不成立时先诊断，不换名扩片、不用自评分覆盖用户否决。

知识歌曲先比较真实主唱乐句并冻结音轨，再审全曲粗剪和开头、最难机制、结尾三段。按[专项配方](../../../docs/制作配方/知识歌曲首版.md)把实际歌曲输入、同版带声音的媒体和七项质量观察绑定到 `knowledge-song-preview`。Studio 的 make、恢复和返修，V13 副本的 `native-knowledge render/compose` 都消费该阶段。待核项和明显问题留在制作侧；只有确需用户决定创作方向才展示内部诊断段。其余视频的代表段沿[制作流程](../../../docs/制作流程.md#代表段先确认方向)。

## 审阅与交付

从陌生观众判断开头为何停下、过程为何继续、结尾得到什么，落实 [观众视角与制作避坑](../../../docs/观众视角与制作避坑.md)。完整画面与音轨必须绑定同一版。抽帧、SRT、解码、浏览器播放、外部模型评分不能替代完整正常速度看听；工具能力不足明确待验，不冒填真人。已验证的外部 AI 连续声画入口 `aistudio_full_av_v1` 沿 [实际回执与限制](../../../docs/reviews/2026-11-17-连续画面审阅与返修闭环.md) 使用；不证明模型内部逐帧感知，`review-save` 不能靠换方法名放行。

`review-prepare` 只是诊断包，按[三份主记录](references/审查与版本.md#一次审查的三份主记录)归集材料、逐条交叉核对，再实际审阅并 review-save/review-status；export 与离线包装消费同版审查。未审、否决或过期不得称合格，可以明确提供诊断预览。交付用 `--mode delivery export <ID> --version <版本> --to <目录>`，核实际附件及可编辑范围，不把旧 complete 或文件存在当完成。

包装读 studio-publish，真实数据复盘读 studio-content-analytics；沿原成片新增侧记录，不渲染、不切 current，不接账号／上传／发布。封面遵循项目 Image 2 约定及实际图片观察。研究、模板目录和历史反馈仅按需要定向查，不重跑已有效昂贵步骤。

具体调用方法见 [制作流程](../../../docs/制作流程.md) 与 [整改入口](../../../docs/内容改编与整改后的入口.md)。每次交接留当前目标、输入版本、可消费真实产物／任务回执、保护项、失败／未知与下一允许动作；这是持续执行的恢复点，不是无故停止已授权工作的理由。
