---
name: studio-template-lanshu-v9-clay
description: 黏土小镇。用于用生活类比解释抽象概念，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/clay-seed-1114/versions/v0001/video.mp4` 和 `/works/clay-seed-1114/versions/v0001/shots/native-story/film/scene.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`sources/zh-explainer/vendor/lanshu/explainer/kits/v9-clay/KIT.md`。

固定语法：种子静置→浇水→跨时间发芽→叶片→开花。

新输入示例：“用黏土小盆栽讲种子浇水后慢慢发芽开花，不催促成长。”

逐项换稿：有机几何、状态生长、因果动作、时间跨越、材料色。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。蓝叔原生 story.json + beats.js 编排为 brief，镜头 engine=lanshu、style=v9-clay；参考同版 brief。templates prepare 不编译蓝叔。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → plan <新brief> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/clay-seed-1114/versions/v0001/editable.zip`；确切输入：`works/clay-seed-1114/versions/v0001/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：仅横屏已适配；新故事的画面编排、字幕与视听必须另验。

## 市场与类型

分类：教程与过程。来源关系：形式／材料迁移，非逐镜复刻。 原片：https://www.douyin.com/video/7572923536638020918；公开快照赞26493、播放None（未知为None）。学习操作：黏土材质、状态变化与场景连续。差异：原片为黏土人物长剧情；新稿只验证盆栽成长，未验证复杂人物剧情。。 原片互动不能证明本片流量、留存或用户认可。
