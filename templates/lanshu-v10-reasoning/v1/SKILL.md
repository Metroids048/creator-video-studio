---
name: studio-template-lanshu-v10-reasoning
description: 连续推导。用于公式、关系与逻辑链，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/stair-sum-1114/versions/v0001/video.mp4` 和 `/works/stair-sum-1114/versions/v0001/shots/native-story/film/scene.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`sources/zh-explainer/vendor/lanshu/explainer/kits/v10-reasoning/KIT.md`。

固定语法：离散数列→空间排布→补一份→整体计算→还原。

新输入示例：“用公式推理动画把一到八排成台阶，补成八行九列再取半。”

逐项换稿：数列范围、点阵布局、复制和翻转、整体计数、约分。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。蓝叔原生 story.json + beats.js 编排为 brief，镜头 engine=lanshu、style=v10-reasoning；参考同版 brief。templates prepare 不编译蓝叔。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → plan <新brief> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/stair-sum-1114/versions/v0001/editable.zip`；确切输入：`works/stair-sum-1114/versions/v0001/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：仅横屏已适配；新故事的画面编排、字幕与视听必须另验。

## 市场与类型

分类：知识与机制。来源关系：形式／材料迁移，非逐镜复刻。 原片：https://x.com/VictorTaelin/status/2104568082169749982；公开快照赞6124、播放392884（未知为None）。学习操作：可追踪对象的连续推导。差异：原片展示Bend证明游戏、归纳、重写、排序与并行运算；新稿为点阵求和，只迁移对象可追踪的连续推导。。 原片互动不能证明本片流量、留存或用户认可。
