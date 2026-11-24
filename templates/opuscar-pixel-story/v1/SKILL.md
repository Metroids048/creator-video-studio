---
name: studio-template-opuscar-pixel-story
description: 像素日常荒诞故事。用于把日常目标写成递进空间障碍与动作反转的完整剧情，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/pixel-last-mile-1114/versions/v0002/video.mp4` 和 `/works/pixel-last-mile-1114/versions/v0002/shots/native-style/film/engine/story.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/opuscar-pixel-story/v1/STYLE.md`。

固定语法：普通目标→空间障碍→判断错误→可见修正→荒诞反转。

新输入示例：“用像素日常故事讲最后一公里，电梯停用、找错楼、终于回家。”

逐项换稿：像素地图、人物状态、碰撞路径、道具、障碍和结尾。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。把新稿项目路径写入 input.json 的 project 字段；native/project.json 同步 template、style、duration、content_promise 与 changed_files 哈希。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/pixel-last-mile-1114/versions/v0002/editable.zip`；确切输入：`works/pixel-last-mile-1114/versions/v0002/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：当前为单人五场景；不声称复杂宿舍人群表演；市场原作者与工程不同。

## 市场与类型

分类：动作与游戏。来源关系：形式／材料迁移，非逐镜复刻。 原片：https://www.douyin.com/video/7600724311846437049；公开快照赞325308、播放None（未知为None）。学习操作：像素地图、可见障碍、行动与荒诞反转。差异：换成末班路程，不复制原作情节。。 原片互动不能证明本片流量、留存或用户认可。
