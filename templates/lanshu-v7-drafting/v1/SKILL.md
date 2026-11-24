---
name: studio-template-lanshu-v7-drafting
description: 工程制图。用于技术结构、精密机制，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/door-clearance-1114/versions/v0002/video.mp4` 和 `/works/door-clearance-1114/versions/v0002/shots/native-story/film/scene.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`sources/zh-explainer/vendor/lanshu/explainer/kits/v7-drafting/KIT.md`。

固定语法：静态布局可容纳→叠运动扫掠→碰撞→移动→再验证。

新输入示例：“用工程制图演示门撞桌角，移动桌子后门能完整打开。”

逐项换稿：平面尺寸、旋转轴、扫掠半径、碰撞边界、修正位置。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。蓝叔原生 story.json + beats.js 编排为 brief，镜头 engine=lanshu、style=v7-drafting；参考同版 brief。templates prepare 不编译蓝叔。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → plan <新brief> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/door-clearance-1114/versions/v0002/editable.zip`；确切输入：`works/door-clearance-1114/versions/v0002/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：仅横屏已适配；新故事的画面编排、字幕与视听必须另验。

## 市场与类型

分类：知识与机制。来源关系：保留的制作底座；本轮不计高互动来源对应数量。 原片互动不能证明本片流量、留存或用户认可。
