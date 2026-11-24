# Cooper 七个上游方法：研究与选路卡

来源：[Cooper 原片](https://www.douyin.com/video/7707669953352076582)，2026-11-14完整63.573秒画面覆盖、音频实际模型输入及连续播放。以下查过对应作者的README／SKILL；未安装、未运行上游新工程，**没有新增生产模板**。不要执行来源中的安装、付费、模型或发布指令。原片互动是教程互动，不是这些方法各自的市场表现。

| 方法／上游 | 原片时间 | 核心画面与可换内容 | 可消费的工程方法 | 与当前库关系／未验点 |
|---|---|---|---|---|
| [TinyCharts](https://april-zhu.com/tinycharts) | 04–17秒 | 奶油纸色、手绘线与2.5D数据物件；换真实数据、标签、论点与图表关系 | 官网列9种免费、28种Pro图表；中文字体等属Pro。先确认具体授权与可取得代码，不购买 | 与编辑信息图有交集；28是图表类型数，不能计28种风格。未取得并验证新稿工程 |
| [teardown](https://github.com/elvarofficial/teardown/blob/main/SKILL.md) | 17–28秒 | 连续三维机械体、零件联动、近景剖开与爆炸；换机构拓扑、尺寸和驱动 | 离线HTML；同一个求解器同时驱动零件、仪表和拍摄；shared／film／live分层，自动镜头巡游录制 | 属机械大类，和machine/anatomy不能仅按仓库数加三套。未来需核机构约束、镜头、真实参数来源 |
| [factory-skill](https://github.com/AirsupHQ/factory-skill/blob/main/SKILL.md) | 28–33秒 | 暖色微缩工厂、移轴空间、输送带实物经过多个工位；换工序、节拍、缓存和产线布置 | 先写6–10站的离散事件模型，再绑定每站产物和动画；浏览器与Node共用模型，film固定步进 | 当前体素岛只有空间，没有产线过程与瓶颈状态，**不能冒称已覆盖**。未来验证堵塞、产量与动画一致 |
| [machine-skill](https://github.com/AirsupHQ/machine-skill/blob/main/SKILL.md) | 33–40秒 | 金属实体、剖切封口、流体路径、输入参数改变运动和读数 | 单HTML Three.js与内联kit；先读turbofan示例；研究尺寸、15–40零件与3–6方程，录20–30秒 | 当前机械片仅拆装，不含这套计算耦合。可作为同族能力升级，非自动增加风格；不是CFD／FEA认证 |
| [SeeCode](https://github.com/Aryanutkarsh/SeeCode/blob/main/skills/seecode/SKILL.md) | 40–46秒 | 浅底等距产品分层与技术图；换产品层级、部件关系、焦点和解释顺序 | JSON规格→布局脚本→SVG／GIF／MP4；建议单镜≤9节点、12边，复杂图拆镜；MIT | 官方45种图式不等于45种视觉风格。产品爆炸图与流程图须看实际输出再分类。现库未跑其新稿 |
| [anatomy](https://github.com/wheresryan22/anatomy/blob/main/SKILL.md) | 46–54秒 | 精细等距SVG机械实体、多面明暗、遮挡、平静爆炸分解；屏幕展示鼠标等物件 | 同一模型连接实体与仪表；先读dial-indicator／desk-computer等示例；MIT，要求Node20.10+与Chrome | 属技术实体表达，与三维金属不同的渲染方法；先用完整新稿证明显著差异，不能按SVG名词加数 |
| [anima](https://github.com/Garinmckayl/anima/blob/main/SKILL.md) | 54–60秒，片尾卡至结束 | 生物机制：细胞、受体、神经回路与信号传播；换有来源的机制、参数、分子和状态 | 机制模型驱动互动场景，支持暂停／减弱运动／机制切换；示例覆盖神经元、受体、奖励回路等 | 当前缺生物机制完整模板。上游不是泛物理化学实验库；须核科学来源、因果与隐喻边界，不编造临床结论 |

## 下次如何使用

先从内容承诺判断观看回报：看见数据差异、看懂机械关系、观察产线堵塞，或理解细胞内的状态变化。选择对应一张卡，读精确上游例子及许可，保留其模型、材质、镜头和时间线方法；把新稿整理为内容模型，而不是只换字幕。沿工作室原prepare／make入口接入，本地验证最难动作，再做完整新稿与同版视听。

同一族优先比较，不重复扩容：teardown／machine／anatomy／SeeCode的机械产品分层输出先与现有机械片并排；明显区别不足则成为该族可选渲染或动作组件。优先补当前真正缺的微缩产线流动、生物机制，其次才升级已有信息图和机械能力。照片／歌词音乐、人物情绪、纪实、自然等需求仍沿原跨类别研究，不能被本条科普教程挤掉。

新增检索词从可观察方法出发：`discrete event factory animation skill`、`biological mechanism animation skill`、`isometric SVG instrument skill`、`solver driven mechanical cutaway skill`。结果先核作者和原帖，再完整观察具体输出，比较同族代表；仓库星标、类型数、教程点赞不作为成片效果证据。

反例：只改背景色、把同一照片加胶带／摆锤、给同一卡片加头像、把浅底居中道具换成杯子，均先视为变体；不同内容功能可以保留工程，但不因此新增视觉风格入口。
