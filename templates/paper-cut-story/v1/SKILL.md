---
name: studio-template-paper-cut-story
description: 纸艺定格·日常小仪式。用于低密度、无人物的整理/赠礼/物件动作短故事，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/paper-pocket-1113/versions/v0004/video.mp4` 和 `/works/paper-pocket-1113/versions/v0004/shots/tactile/film/assets/story.json`（路径均相对项目根），核目标画幅 9:16。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/paper-cut-story/v1/STYLE.md`。

固定语法：物件依次归位→纸张折叠遮住→打开或封合→语义结果。

新输入示例：“用纸艺定格让通勤票钥匙耳机依次进纸袋，最后折好出发。”

逐项换稿：纸层路径、物件、遮挡顺序、接触帧、折痕、实录短音。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。从样例故事 JSON 复制新文件，保留模板字段并替换全部语义参数。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 9:16` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/paper-pocket-1113/versions/v0004/editable.zip`；确切输入：`works/paper-pocket-1113/versions/v0004/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：只支持已声明的几何/纸片对象语法，不支持复杂人物表演或写实生成；音效听感待验。

## 市场与类型

分类：教程与过程。来源关系：形式／材料迁移，非逐镜复刻。 原片：https://x.com/pleometric/status/2102572941699354900；公开快照赞3766、播放411706（未知为None）。学习操作：真实纸层的遮挡、纸物件日常动作与收束。差异：原片纸TikTok递归睡前故事，新稿纸袋归位仪式，叙事不同。。 原片互动不能证明本片流量、留存或用户认可。
