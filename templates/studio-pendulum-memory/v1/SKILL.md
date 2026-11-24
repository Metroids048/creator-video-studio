---
name: studio-template-studio-pendulum-memory
description: 摆锤遮挡回忆混剪。用于1969年7月，奥尔德林走下登月舱。镜头留下鞋和月壤中的脚印。阿姆斯特朗，拍下同伴的身影。他们也把实验设备，安放在月面。，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/pendulum-memory-story-1114/versions/v0001/video.mp4` 和 `/works/pendulum-memory-story-1114/versions/v0001/shots/native-style/film/engine/story.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/studio-pendulum-memory/v1/STYLE.md`。

固定语法：照片缓摆→摆板遮住→下一记忆显露→末图落定。

新输入示例：“用摆锤遮挡回忆混剪展示阿波罗11号四张官方照片。”

逐项换稿：照片顺序、摆板几何、遮罩边界、摆角、拍点和事实。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。把新稿项目路径写入 input.json 的 project 字段；native/project.json 同步 template、style、duration、content_promise 与 changed_files 哈希。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/pendulum-memory-story-1114/versions/v0001/editable.zip`；确切输入：`works/pendulum-memory-story-1114/versions/v0001/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：仅核16:9；市场数据来自剪辑教程，摆锤遮挡与照片主题须随新内容重写。

## 市场与类型

分类：音乐与图文。来源关系：直接形式适配，非原作质量认证。 原片：https://www.douyin.com/video/7702684761773840049；公开快照赞49102、播放None（未知为None）。学习操作：照片缓摆→摆板遮住→下一记忆显露→末图落定。差异：仅核16:9；市场数据来自剪辑教程，摆锤遮挡与照片主题须随新内容重写。。 原片互动不能证明本片流量、留存或用户认可。
