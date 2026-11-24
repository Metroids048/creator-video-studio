---
name: studio-template-studio-lens-lab
description: 剖面实验与参数演示。用于光线在这里相遇，感光面却在后面。把感光面移到成像位置，就清晰了。物体靠近透镜，成像的位置向后移动。重新让感光面与像重合，就是再次对焦。，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/lens-lab-story-1114/versions/v0001/video.mp4` 和 `/works/lens-lab-story-1114/versions/v0001/shots/native-style/film/engine/story.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/studio-lens-lab/v1/STYLE.md`。

固定语法：失焦结果→观察光线交点→移感光面→物距改变→再对焦。

新输入示例：“用镜头剖面实验讲物体靠近透镜时像距改变，移动感光面重新对焦。”

逐项换稿：可核物理关系、参数域、剖面结构、光线路径、结果对照。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。把新稿项目路径写入 input.json 的 project 字段；native/project.json 同步 template、style、duration、content_promise 与 changed_files 哈希。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/lens-lab-story-1114/versions/v0001/editable.zip`；确切输入：`works/lens-lab-story-1114/versions/v0001/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：仅核16:9；市场指标为2026-09-27历史快照，原片全长已观察；本例光学示意，不替代真实镜头设计。

## 市场与类型

分类：知识与机制。来源关系：直接形式适配，非原作质量认证。 原片：https://x.com/RyanSael/status/2102591147927654847；公开快照赞15510、播放3115565（未知为None）。学习操作：失焦结果→观察光线交点→移感光面→物距改变→再对焦。差异：仅核16:9；市场指标为2026-09-27历史快照，原片全长已观察；本例光学示意，不替代真实镜头设计。。 原片互动不能证明本片流量、留存或用户认可。
