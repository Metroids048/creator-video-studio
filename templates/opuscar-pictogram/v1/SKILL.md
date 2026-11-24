---
name: studio-template-opuscar-pictogram
description: 几何图标动作叙事。用于雨天里，一个人把伞偏向另一个人；两人一起走到车站，将自己的晴天分出一半。，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/pictogram-rain-1114/versions/v0002/video.mp4` 和 `/works/pictogram-rain-1114/versions/v0002/shots/native-style/film/engine/story.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/opuscar-pictogram/v1/STYLE.md`。

固定语法：几何人物遇事→共享道具→共同位移→抵达→海报收束。

新输入示例：“用几何图标动作叙事讲雨天两个人分享一把伞走到车站。”

逐项换稿：人物轨迹、道具状态、单色层级、图案节拍、结束句。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。把新稿项目路径写入 input.json 的 project 字段；native/project.json 同步 template、style、duration、content_promise 与 changed_files 哈希。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/pictogram-rain-1114/versions/v0002/editable.zip`；确切输入：`works/pictogram-rain-1114/versions/v0002/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：仅16:9；新稿与市场原片须分别核验。

## 市场与类型

分类：动作与游戏。来源关系：保留的制作底座；本轮不计高互动来源对应数量。 原片互动不能证明本片流量、留存或用户认可。

末段音轨返修v0002：停止继续循环的尾音，加入低位主和弦、自然衰减与半秒安静。画面解码哈希与父版v0001相同；全长音频另按本版感知。
