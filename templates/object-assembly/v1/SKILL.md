---
name: studio-template-object-assembly
description: 小物装配·体积与接触。用于几何可构成的家居小物、结构与装配过程，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/assembly-lamp-1113/versions/v0005/video.mp4` 和 `/works/assembly-lamp-1113/versions/v0005/shots/tactile/film/assets/story.json`（路径均相对项目根），核目标画幅 9:16。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/object-assembly/v1/STYLE.md`。

固定语法：散开的零件→接近→接触落位→功能激活→侧面检查。

新输入示例：“做抖音竖屏桌灯零件装配，底座支杆灯罩依次落位，亮灯，无配乐。”

逐项换稿：零件几何、支撑关系、整数帧事件、接触音、激活、相机。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。从样例故事 JSON 复制新文件，保留模板字段并替换全部语义参数。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 9:16` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/assembly-lamp-1113/versions/v0005/editable.zip`；确切输入：`works/assembly-lamp-1113/versions/v0005/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：只支持已声明的几何/纸片对象语法，不支持复杂人物表演或写实生成；音效听感待验。

## 市场与类型

分类：教程与过程。来源关系：形式／材料迁移，非逐镜复刻。 原片：https://x.com/deedydas/status/2103174501345493197；公开快照赞1037、播放72365（未知为None）。学习操作：零件对应、依序装配与功能落定。差异：借鉴装配的可追踪步骤；不是原作者CAD或实拍声音。。 原片互动不能证明本片流量、留存或用户认可。
