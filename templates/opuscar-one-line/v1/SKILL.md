---
name: studio-template-opuscar-one-line
description: 连续墨线叙事。用于以物件和一条旅程表达想念、成长、选择等情绪，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/one-line-home-1114/versions/v0003/video.mp4` 和 `/works/one-line-home-1114/versions/v0003/shots/native-style/film/engine/story.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/opuscar-one-line/v1/STYLE.md`。

固定语法：一条线连接语义物件→镜头跟随→物件承接→拉远见归途。

新输入示例：“用一笔画连续墨线连接日历车票火车和家门，讲一次归途。”

逐项换稿：SVG路径、物件连接点、线速和笔压、镜头、字幕和全景。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。把新稿项目路径写入 input.json 的 project 字段；native/project.json 同步 template、style、duration、content_promise 与 changed_files 哈希。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/one-line-home-1114/versions/v0003/editable.zip`；确切输入：`works/one-line-home-1114/versions/v0003/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：只接横屏；不承载复杂人物表演或歌词口型；市场原片与工程来源不同。

## 市场与类型

分类：情绪与剧情。来源关系：保留的制作底座；本轮不计高互动来源对应数量。 原片互动不能证明本片流量、留存或用户认可。
