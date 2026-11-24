---
name: studio-template-studio-history-axis
description: 连续空间历史长轴。用于1843年，建设电报线路获得国会拨款。次年5月24日，摩尔斯在华盛顿发报。巴尔的摩，收到点和划写下的消息。一周后，他在信中谈到成功的责任。，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/history-axis-story-1114/versions/v0001/video.mp4` 和 `/works/history-axis-story-1114/versions/v0001/shots/native-style/film/engine/story.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/studio-history-axis/v1/STYLE.md`。

固定语法：沿连续二维轴前进→节点具象变化→时间关联→全景。

新输入示例：“用二维空间历史长轴讲1843拨款到1844电报成功，最后拉远看全程。”

逐项换稿：史实来源、年份、装置图形、轴距、相机、最终关联。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。把新稿项目路径写入 input.json 的 project 字段；native/project.json 同步 template、style、duration、content_promise 与 changed_files 哈希。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/history-axis-story-1114/versions/v0001/editable.zip`；确切输入：`works/history-axis-story-1114/versions/v0001/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：本例为二维连续轴适配；不等同原片三维场景。史实逐项核来源。仅核16:9。

## 市场与类型

分类：知识与机制。来源关系：直接形式适配，非原作质量认证。 原片：https://www.douyin.com/video/7690160210039622946；公开快照赞20120、播放None（未知为None）。学习操作：沿连续二维轴前进→节点具象变化→时间关联→全景。差异：本例为二维连续轴适配；不等同原片三维场景。史实逐项核来源。仅核16:9。。 原片互动不能证明本片流量、留存或用户认可。
