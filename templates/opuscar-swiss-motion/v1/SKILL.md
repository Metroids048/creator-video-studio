---
name: studio-template-opuscar-swiss-motion
description: 瑞士网格动态海报。用于用一张从拥挤到有空隙的日程海报，演示取舍、对齐和预留缓冲三个实际改变。，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/swiss-calendar-1114/versions/v0002/video.mp4` 和 `/works/swiss-calendar-1114/versions/v0002/shots/native-style/film/engine/story.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/opuscar-swiss-motion/v1/STYLE.md`。

固定语法：网格挤满→删减选择→对齐重要项→空格接住意外→海报。

新输入示例：“用瑞士排版动态海报，把拥挤的日程删到三件并留出缓冲。”

逐项换稿：事项数据、字号层级、网格位置、删减项、缓冲和新文案。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。把新稿项目路径写入 input.json 的 project 字段；native/project.json 同步 template、style、duration、content_promise 与 changed_files 哈希。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/swiss-calendar-1114/versions/v0002/editable.zip`；确切输入：`works/swiss-calendar-1114/versions/v0002/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：仅16:9；新稿与市场原片须分别核验。

## 市场与类型

分类：品牌与产品。来源关系：形式／材料迁移，非逐镜复刻。 原片：https://x.com/deedydas/status/2102787937482252537；公开快照赞3244、播放338541（未知为None）。学习操作：字形层级、量化论点和版面节奏。差异：新稿网格日程删减，不宣称有原作产品投放数据。。 原片互动不能证明本片流量、留存或用户认可。
