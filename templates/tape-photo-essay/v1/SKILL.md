---
name: studio-template-tape-photo-essay
description: 手账照片短句。用于日常共鸣与回忆，三页短句照片叙事，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/moon-tape-essay-1114/versions/v0001/video.mp4` 和 `/works/moon-tape-essay-1114/inputs/story.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/tape-photo-essay/v1/STYLE.md`。

固定语法：一主题多视角→每页图文互证→手账空间重排→短句落定。

新输入示例：“用手账照片拼贴讲月面工作日，人物完整，不裁掉头脚。”

逐项换稿：照片、事实说明、胶带版位、页内主次、留白、逐页时间。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。从样例故事 JSON 复制新文件，保留模板字段并替换全部语义参数。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/moon-tape-essay-1114/versions/v0001/editable.zip`；确切输入：`works/moon-tape-essay-1114/versions/v0001/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：静态照片转场；不支持连续人物表演；新作品无流量与留存数据

## 市场与类型

分类：音乐与图文。来源关系：保留的制作底座；本轮不计高互动来源对应数量。 原片互动不能证明本片流量、留存或用户认可。
