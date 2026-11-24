---
name: studio-template-paper-ink-landscape
description: 纸墨山形·微人物叙事。用于把选择、练习、反馈等因果转成空间路径的低密度叙事，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/paperink-pause-1114/versions/v0001/video.mp4` 和 `/works/paperink-pause-1114/inputs/story-85c04d7ee7b8334e.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/paper-ink-landscape/v1/STYLE.md`。

固定语法：人物前行→有理由停下→镜头一起驻足→继续→留白。

新输入示例：“用纸墨山形讲一个总催自己快一点的人，停下后继续前行。”

逐项换稿：地形、世界宽度、人物路径、相机关键帧、停顿和四句新稿。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。从样例故事 JSON 复制新文件，保留模板字段并替换全部语义参数。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/paperink-pause-1114/versions/v0001/editable.zip`；确切输入：`works/paperink-pause-1114/versions/v0001/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：1280×720、30fps、单段不超过120秒；本轮32秒横屏新稿含原创器乐，无配音；完整画面与模型音轨观察已记录，真人听审及竖屏未验。

## 市场与类型

分类：自然与空间。来源关系：保留的制作底座；本轮不计高互动来源对应数量。 原片互动不能证明本片流量、留存或用户认可。
