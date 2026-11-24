---
name: studio-template-studio-rain-ripples
description: 春雨落点与水面涟漪。用于雨落下，每一滴都有回声。碰见另一圈，就一起走远。有些事，急也急不来。等雨停，水面会把月亮还给你。，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/rain-ripples-story-1114/versions/v0003/video.mp4` 和 `/works/rain-ripples-story-1114/versions/v0003/shots/native-style/film/engine/story.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/studio-rain-ripples/v1/STYLE.md`。

固定语法：雨滴落点→对应波纹扩散相遇→雨停→水面显月。

新输入示例：“做落雨涟漪自然氛围片，雨滴落在水面扩散，雨停后月亮倒映。”

逐项换稿：落点表、雨量、波纹寿命、花瓣漂移、雨停和倒影时间。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。把新稿项目路径写入 input.json 的 project 字段；native/project.json 同步 template、style、duration、content_promise 与 changed_files 哈希。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/rain-ripples-story-1114/versions/v0003/editable.zip`；确切输入：`works/rain-ripples-story-1114/versions/v0003/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：仅核16:9；新片为程序雨滴与波纹、原创器乐。完整原片观察不代表达到原作质感或本片获得流量。

## 市场与类型

分类：自然与空间。来源关系：直接形式适配，非原作质量认证。 原片：https://www.douyin.com/video/7680133191813926171；公开快照赞496884、播放None（未知为None）。学习操作：雨滴落点→对应波纹扩散相遇→雨停→水面显月。差异：仅核16:9；新片为程序雨滴与波纹、原创器乐。完整原片观察不代表达到原作质感或本片获得流量。。 原片互动不能证明本片流量、留存或用户认可。

末段音轨返修v0002：停止继续循环的尾音，加入低位主和弦、自然衰减与半秒安静。画面解码哈希与父版v0001相同；全长音频另按本版感知。

末段再次返修v0003：沿v0002替换19.4秒后的颤音琴乐句为低位钢琴，29.5秒后留静。模型对“提示音”的描述不稳定，原始结果全部保留；不把回答措辞当真人听感。
