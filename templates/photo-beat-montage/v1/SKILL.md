---
name: studio-template-photo-beat-montage
description: 图片音乐卡点。用于照片主体与音乐节拍，风景/花卉/回忆，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/moon-photo-beat-1114/versions/v0001/video.mp4` 和 `/works/moon-photo-beat-1114/inputs/story.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/photo-beat-montage/v1/STYLE.md`。

固定语法：同一主题四张图→拍点换主图→反问被逐步回答→末图收束。

新输入示例：“做图片卡点短片，用阿波罗11号四张真实照片讲脚印之外的工作。”

逐项换稿：有许可照片、主体焦点、节拍、换图窗口、短句、音乐。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。从样例故事 JSON 复制新文件，保留模板字段并替换全部语义参数。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/moon-photo-beat-1114/versions/v0001/editable.zip`；确切输入：`works/moon-photo-beat-1114/versions/v0001/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：静态照片转场；不支持连续人物表演；新作品无流量与留存数据

## 市场与类型

分类：音乐与图文。来源关系：形式／材料迁移，非逐镜复刻。 原片：https://www.douyin.com/video/7702634704625619429；公开快照赞33739、播放None（未知为None）。学习操作：同主题照片的中心聚焦与拍点换主图。差异：花卉原片转成NASA照片，使用合法官方图片，照片事实与构图另核。。 原片互动不能证明本片流量、留存或用户认可。
