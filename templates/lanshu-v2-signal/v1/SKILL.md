---
name: studio-template-lanshu-v2-signal
description: 暗色信号台。用于AI、系统状态、科技机制，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/chunk-retry-1114/versions/v0001/video.mp4` 和 `/works/chunk-retry-1114/versions/v0001/shots/native-story/film/scene.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`sources/zh-explainer/vendor/lanshu/explainer/kits/v2-signal/KIT.md`。

固定语法：分块发出→确认缺口→仅重发缺块→完整重组。

新输入示例：“用深色系统信号动画讲四个分块只补第三块，不从零重传。”

逐项换稿：分块数量、确认状态、缺失编号、重试路径、终态。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。蓝叔原生 story.json + beats.js 编排为 brief，镜头 engine=lanshu、style=v2-signal；参考同版 brief。templates prepare 不编译蓝叔。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → plan <新brief> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/chunk-retry-1114/versions/v0001/editable.zip`；确切输入：`works/chunk-retry-1114/versions/v0001/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：仅横屏已适配；新故事的画面编排、字幕与视听必须另验。

## 市场与类型

分类：知识与机制。来源关系：保留的制作底座；本轮不计高互动来源对应数量。 原片互动不能证明本片流量、留存或用户认可。
