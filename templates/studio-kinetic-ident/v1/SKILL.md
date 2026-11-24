---
name: studio-template-studio-kinetic-ident
description: 几何与动态排版短片。用于把太大的想法，压成一个小问题。把缠在一起的步骤，一点点拉开。写下一行，让它有个可以修改的形状。删掉犹豫。从一行开始。，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/kinetic-ident-story-1114/versions/v0001/video.mp4` 和 `/works/kinetic-ident-story-1114/versions/v0001/shots/native-style/film/engine/story.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/studio-kinetic-ident/v1/STYLE.md`。

固定语法：压缩大想法→拉开纠结步骤→写一行→删犹豫→落版。

新输入示例：“用动态排版文字编舞把压拉写删变成动作，鼓励从一行开始。”

逐项换稿：语义动词、字形变形、几何母题、字体许可、节拍。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。把新稿项目路径写入 input.json 的 project 字段；native/project.json 同步 template、style、duration、content_promise 与 changed_files 哈希。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/kinetic-ident-story-1114/versions/v0001/editable.zip`；确切输入：`works/kinetic-ident-story-1114/versions/v0001/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：仅核16:9；原片全长已观察；文字含义必须决定几何动作，不能只替换文字内容。

## 市场与类型

分类：品牌与产品。来源关系：直接形式适配，非原作质量认证。 原片：https://x.com/stephanlivera/status/2103315922098470926；公开快照赞17242、播放2322214（未知为None）。学习操作：压缩大想法→拉开纠结步骤→写一行→删犹豫→落版。差异：仅核16:9；原片全长已观察；文字含义必须决定几何动作，不能只替换文字内容。。 原片互动不能证明本片流量、留存或用户认可。
