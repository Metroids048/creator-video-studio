---
name: studio-template-opuscar-silent-comedy
description: 手摇默片喜剧。用于角色翻桌、找沙发，最后在镜子里发现眼镜一直架在头顶；用实际动作完成反转。，读取本套完整新稿并按画面语法换内容。
---

2026-11-15默认复用方式：先看市场参考、本地样片及其完整可编辑表演，保留已成立的角色、构图、动作段、镜头关系与节拍，只替换用户内容需要的物件、情境和揭晓。具体执行见[观众视角与制作避坑](../../../docs/观众视角与制作避坑.md)。本套与Simon’s Cat只共享部分喜剧机制，并未复现其角色表演与形式；不能将其作为已成熟同款推荐。

开箱刀失败记录：`works/boxcutter-1114-rig-trial-03/versions/v0011/shots/native-style/film/engine/`实际消费了figure/OTTO/pose、rig-contact.js及acting.js/main.js，但仍blocked。v0004误放行已撤回，v0005至v0011未通过。该目录只供定位具体技术与失败，不是下一片握持、转身、受力的默认成熟源。原上游完整持物、放下、转向、分物段在`resources/lemo-opuscar/mit-8814b84/styles/silent-film/demo/shots.js`；本次已观察BAKERY/TENDER全段样帧，其细长关节和舞台木偶感仍不能解决本题材投诉。具体证据见`productions/boxcutter-1114/rig-trial-03/source-observation/record.json`；不把源代码存在或原段可播放当成质量证明。最新要求只修代表段，不扩完整片。

当前没有已通过本题材质量验证的表演方法。以下为技术子能力：手目标先在身体局部空间定义再随yaw变换，避免屏幕上看似可达却落在身体后方；落脚前由实际骨长和双脚距离限制root高度，避免腿伸不够；支撑、身体、视线和道具虽分轨安排，仍有木偶感，不能按结构存在推断表演成功。实际编辑时钟曾因每个结点smoothstep重复刹停，v0010改分段线性映射并用固定父版反例复验；复用时核实际时间映射。不能仅核IK残差。该骨架近脸表现有已知木偶边界，信息优先用物件镜头和中景反应。此处是下次Codex选源及适配要求，未将新源自动替换到所有旧输入或宣称CLI能自动导演；后续新稿仍须实际验证最难段。

先看 `/works/silent-glasses-1114/versions/v0001/video.mp4` 和 `/works/silent-glasses-1114/versions/v0001/shots/native-style/film/engine/story.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/opuscar-silent-comedy/v1/STYLE.md`。

眼镜样片使用“寻找→失败→镜中揭晓→动作兑现→虹膜收束”；这是该样片内容，不是所有新内容的固定剧情。新稿沿选定原段的形式适配，保留其有效表演与观看回报。

新输入示例：“做黑白默片喜剧，翻桌找眼镜，最后照镜发现一直戴在头顶。”

逐项适配：在已有计划写清原段来源、保留的形式、必须换的内容和未验证能力。先保留完整表演，再改物件、情境和揭晓；不要默认重写角色动作、镜头时序或钢琴。内容变化确实要求新动作时，先用原始最难输入验证该能力，失败不扩片。把新稿项目路径写入 input.json 的 project 字段；native/project.json 同步 template、style、duration、content_promise 与 changed_files 哈希。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/silent-glasses-1114/versions/v0001/editable.zip`；确切输入：`works/silent-glasses-1114/versions/v0001/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：仅16:9；新稿与市场原片须分别核验。

## 市场与类型

分类：情绪与剧情。来源关系：保留的制作底座；本轮不计高互动来源对应数量。 原片互动不能证明本片流量、留存或用户认可。


历史原帖指标：TV Dinner https://www.youtube.com/watch?v=s13dLaTIHSg 约229,000赞；Double Trouble https://www.youtube.com/watch?v=3VLcLH97eRw 约240,000赞（2026-11-14近似值，非实时）。2026-11-15发现TV Dinner旧“偷三明治/空盘结尾”完整拆解错误，已连同运行完整观察资格撤回；不能继续说双市场依据已齐。纠正、旧错误及原指标均在 productions/template-rollout-20261114/simons-pair-evidence.json 保留。动物线描与本地人形舞台材质不同，互动数不证明本地形式已复现或动作质量成立。
