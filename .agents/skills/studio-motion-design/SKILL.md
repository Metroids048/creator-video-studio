---
name: studio-motion-design
description: 为工作室的代码动画、绘本、静默故事、MV、图解和商务动效选择可编辑原生路线，按镜头接入已校验资源。
---

阶段操作统一读取[阶段交接与局部返修](../../../docs/阶段交接与局部返修.md)。处理当前镜头前读取 `workflow <task> --stage <镜头阶段>`，复用有效内容与声音；把单镜字段、源文件和共享角色依赖分清。返回reuse时不重新调用P1/P2；只在候选副本修改。

知识歌曲在整片前，用 `knowledge-song-preview` 检查有声全曲粗剪和三段实样。V13 派生工程用 `native-knowledge preview` 从真实时轴取段。查手机尺寸下的主体和因果，逐区间查箭头语义、相机路径、道具入场到接触；记录实际观察与时间码。存在疑点就先修可编辑镜头。用 `native-knowledge render/compose` 启动通过预审的整片。

沿 plan 返回的 `production_method` 实际消费冻结执行 Prompt、方法正文和适配的源码映射；知识歌曲准备输入显式带 `content_format: knowledge-song`。V13 的 `musicClock/accent`、连续状态及分层/相机代码是可查的本片实现，先核语义适配再复制到本任务副本，不把船舱、物理箭头、旧音轨当万能素材。动效先改变对象关系与观众理解，再落实际乐句/重音；随机晃动、平移整图、添加无关真人、仅改颜色标题不构成内容推进。把开头、最难机制与结尾一起核；箭头检查量的含义和相机全路径，接触与离场/归来检查连续过程。这里是执行动作要求，哈希绑定不认证这些动作已做好。

视觉方向或画面质感未定时先消费 [studio-visual-design](../studio-visual-design/SKILL.md) 的方向板、关键画面和真实资产，再选本表原生路线。`studio.py visual-assets --recipe <ID>` 返回文件/许可/哈希；代码镜头实际引用资产，生成镜头区分外观参考与运动描述。装饰纹理和特效不能替代动作与信息推进。

系列视频与连续 MG 按[视觉设计方法](../studio-visual-design/references/视觉设计方法.md)的“系列与镜头”执行：沿原作品合同固定风格、角色与已认可声音，每段先写看点及源对象→动作→结果→交接，先验证有声音的最难完整过程。包装卡用 `visual-build --engine overlay`，三件组件过程示例用 `--engine table`；具体输入和既有媒体/原生 ZIP 交接见 `resources/visual-library/README.md`。这两个素材入口不新增整片模板资格，不绕过 workflow 与 review/export。其他关系必须改可编辑场景后重验，不能只换标签。


## 2026-11-15参考方法的实际使用

调用P2/D2先建立事实→因果状态→事件，再按P3/D5把最终音轨乐句、重音和动作对应。知识说唱必须保单位与限定条件，不是科普叠节拍；声部、画内角色、肖像与拟人道具分别标记。角色教育参考的重复词句应伴随反应升级和最后行动兑现。生活片保留小动作与出门/归家结构，不能用平移静图替代要求的表演。每镜只消费同一manifest当前段及相邻首末状态，保护角色/道具/空间连续。

具体证据及边界见[七条参考与源码复盘](../../../docs/research/2026-11-15-原片源码与工作室复盘/研究总览.md)，执行沿现有[P1–P6](../../../docs/research/2026-11-13-后续制作方法与Prompt.md)及[制作流程](../../../docs/制作流程.md)。这些为当前Skill执行指引；除明确列出的CLI检查外，不声称已实现自动质量拦截或新增生产能力。


输入为创作目标、参考规则、镜头需求、画幅、角色/素材、声音条件及锁定项。输出每镜的起始状态、动作、结果、观众信息、原生引擎、素材与时间证据。只打开匹配能力。

新原创先完成受众问题、具体内容及粗略画面关系，再按 `studio-video-templates` 和 `docs/视频风格模板目录.md` 核候选工程能否承载。内容工作沿主Skill的[原创内容开发](../self-media-studio/references/原创内容开发.md)；不得先选一套现成动画再倒推故事。指定模板改编、已确认完整稿、旧片返修与原生恢复保留原合同和父工程。阶段授权先核当前聊天原话及STATUS中对应任务；历史整改阶段的“不制片”不作为新任务授权判断；本轮动作沿当前用户原文。统一目录为13观看家族、18工程分支＋1专业乐谱；44研究配方不计成熟生产模板。下方学习片与V9仅为历史方法。

已有内容进入制作设计后，才按 `docs/research/2026-11-13-后续制作方法与Prompt.md` 使用P1–P4：内容及粗略镜头→工程承载与源码复用→精确分镜／声音时间线→获准后的完整因果代表段→整片。有效阶段直接复用，不机械重做。保留场景、角色、道具、运动方向与出入场状态；字幕只补画面未表达的推理，主要阅读区一次一处。配音由用户决定，无配音片不得默认TTS。

六维专项按 `docs/research/2026-11-13-六维方法与Prompt.md`：P2先D2因果链，再D1注意力／景别、D3支撑与落定、D4字幕揭晓；P3用D5声音；封面交D6。用事件ID串联起始／落定姿态、朝向、接触、视线、道具与观众新信息，写回原生分镜，不新增状态机。本片工程与时间映射见同目录 `2026-11-13-v0009不渲染走查.md`：`storyTime/presentationTime`先转换再对字幕和声音；源码内事件秒数不等于成片秒数。以上为历史v0009映射，不能作为当前阶段或授权判断。未来获准具体制作后，按所选模板和该片实际时轴执行；历史独立临摹授权不驱动本轮动作。

已核的候选中，painted适合绘画故事，Shotcraft适合产品动效；固定提交、源码入口与未安装范围见上述手册。二者并未注册为工作室原生引擎，不得虚构 `engine=painted/shotcraft`。在获准制作的任务内补齐所需原生工程，保留其可编辑源，再按已有媒体／`nativeAsset`或原生时间线合同接入；若确需新增适配，按实际缺口最小处理，不替换成熟场景为简陋卡片求通过。来源目录保持不变。

| 需求 | 资源与交接 |
| --- | --- |
| 过程、机制、几何动画 | `resources/auto-motion/PROMPT.md` 提供按SRT语义分段、连续时间覆盖和单镜任务组织；原文把镜内创作交给其他执行者，不提供可信动作分解或机制设计。只复用时间组织，不执行其委派命令。另用 `sources/hyperframe-local/hyperframes/skills/hyperframes-core/SKILL.md` 的时间/组合契约。工作室代码镜头用独立场景，不改旧样片模板 |
| 二维绘本、角色动作 | 用 `resources/storybook/hand-drawn-storybook-animation/SKILL.md` 的角色分层与镜头方式。纸片、线稿、火柴人、MG、水墨读取 `resources/nook-anim/nook-anim/references/scene-api.md` 和匹配的风格卡。固定角色素材、场景时间和姿态控制。Nook 接入状态用 doctor 核对；依赖缺失时保留原生选项并说明替代路线 |
| 横屏图解 | 读 `sources/zh-explainer/vendor/lanshu/explainer/KITS.md`，用 `python3 scripts/lanshu.py --plan --style <kit> --story <故事目录或内置名称>` 核对 story 与 kit 绑定。作品级 `engine=lanshu` 接 story JSON 与自己的 beats JS，13 套 kit、字体/许可及固定核心进入工程；离线准备已验，实际整片/新故事呈现另验 |
| 艺术动效、参数化片段 | 从 `resources/huashu-art-motion/references/09-视频动画语法.md` 及 `references/风格配方/INDEX.md` 选一套语法和风格；保留原生片段 spec。工作室 `workflow` 的 `art` 路线调用固定版 `scripts/clip_lint.py`，再复用 `scripts/engine/spec_assets.py` 核本地图片、帧序列和角色帧库。远端素材未落地时阻塞；`y4_storytime` 须有真实 `rest` 或 `talk` 角色帧，不能以旧预设名代替。检查不解码素材，不运行渲染器；原作者的配音、下载和自动升级命令不触发 |
| 数据/品牌动效 | 先读 `resources/mg-styles/README.zh-CN.md` 的 15 风格索引，只加载命中的 `prompts/<id>.md` 和 `demos/<id>/` 源码；只借用 `rubric.md` 中按具体时间码描述问题、影响和修法的方式；它面向10秒MG展示，固定10秒、抽帧评分、虚拟评委和9分目标不适用于本项目长叙事，更不能替代同版完整视听或真人认可。缺示例媒体、字体、采样音源时先核清单，不把源码已在当作可直接重渲。`resources/vibe-skills/README.md` 按组件选择模板。商务分类交给工作室 commerce 适配器。Remotion 参考见 `resources/host-skills/remotion-best-practices/SKILL.md`，不能假设所有模板依赖已安装 |
| 歌词 MV、静默故事 | 用 `sources/zh-explainer/skills/vibe-film/SKILL.md` 的原生工程和 `resources/vibe-sound/SKILL.md` 的Freesound音效检索、许可与候选筛选方法；音画组织另按本项目D5核实际音轨。sound不提供音画拍点、配音表演或混音；下载量、描述和评分不能代替实听，其付费版宣传不计已接入能力。`bash scripts/vibe.sh runtime-check` 查固定环境；`inspect <id>` 查工程合同与哈希，`gate <id> --stage plan` 调原生记录检查。状态归 `FILM_STATUS.md`，不能套用工作室 current；记录通过也不等于实际视听通过。先核音乐授权、原音/无声选择和节拍，不强制旁白 |
| 外部生成镜头 | 用 `sources/zh-explainer/skills/ai-video-gen/SKILL.md` 保留起止帧、动作、时长与一致性设计；将能力标记为待授权外部路线。Codex 工作室不自动发外部请求 |

代码路线按镜头选择 `engine`，不能因为独立原生 `continue` 未知就退回共享样片。镜头准备合同见 `docs/制作流程.md` 的引擎表；先 `studio.py plan <brief>`，交回主 Skill 核模式。只有具体生产授权后才经 `studio.py --mode production make <brief>` 进入原生渲染。缺依赖就记录具体文件和对镜头的影响，向主 Skill 返回计划与可用替代。历史 Skill 的模型、网络、制作、付费和安装动作不继承。实际生产须当次授权并经工作室显式模式检查。

计划前按 `docs/制作流程.md` 核声音与素材合同：旁白模式全片须有有效 `cues`，MV/静默故事显式选 `supplied/silent`；媒体 `in` 是有限非负秒数。已有输入 `sha256` 不符时停止，保留源文件与父版，不通过改写哈希或试渲染诊断。新素材另用素材 ID；只读计划不配音、不执行场景。

Nook 用 `python3 scripts/nook.py check` 加载固定引擎，`python3 scripts/nook.py plan <scene.py>` 核对语法和可静态判定的画幅、帧率、时长及镜头起始。`unresolved_constants` 非空时停下补核原生配置；例如猫日常示例的 `mg.Beat` 镜头时间未执行求值。不得通过导入用户场景来绕过只读边界。`host_specific_paths` 列出的 Windows 宿主路径也阻塞交接，应在作品副本显式适配。`check` 通过项目环境使用文楷、Shantell Sans、马善政替代字体，并加载真实字体元数据；原源默认字体保留，直接运行上游渲染器不会自动获得这组适配。

对 Nook、花叔、Lanshu 的原生输入检查，可用 `workflow action=inspect` 并分别提供 `scene/spec/story`，返回同一输入哈希；这不证明旧任务完成。`action=continue` 没有可核验原生任务回执时停在状态检查，不能套用工作室 current 或据输入存在重投制作。
