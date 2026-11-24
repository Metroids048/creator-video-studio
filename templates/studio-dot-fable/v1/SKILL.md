---
name: studio-template-dot-fable
description: 圆点角色微冒险，按完整内容换稿。
---

读取native/story.json、main.js、draw.js及project.json。市场原片：https://x.com/cherry_mx_reds/status/2105825930799432073。保留同一有表情圆点角色→跳跃障碍→昼夜空间变化→接近星星→角色触发收束。换稿必须同时重做角色外形与表情、障碍及动作轨迹、场景状态、追逐目标、结尾动作；不只改标题。替换完整分镜，时序连续覆盖全片。需要新动作或新物件时改main.js对应画面，不通过字幕掩盖。更新changed_files，绑定完整同版音轨，经studio.py templates prepare→plan→workflow→授权make。看完整最终MP4，核画面动作、数量、因果和完整声音。修复绑定确切父版；不以技术检查替代视听质量。

## 本轮完整新稿

成片：`works/dot-fable-fresh-1114/versions/v0001/video.mp4`（18.0秒，16:9），SHA256 `f0ccb7494404f8df30a906d32bad284a24bd82782190339d5618e7da4e117261`。完整故事：`works/dot-fable-fresh-1114/versions/v0001/shots/native-style/film/engine/story.json`。同版可编辑工程：`works/dot-fable-fresh-1114/versions/v0001/editable.zip`；真实制作输入：`works/dot-fable-fresh-1114/versions/v0001/brief.json`。

全程1fps实际查看：圆点受挫、越障、入夜、触星与结尾完整；沿同一角色发展。 完整时长本机MiniCPM音频感知；实际结果见 final-audio-jobs-results.json；未观察到尖锐提示音、爆音或突切。 用户尚未审看。

自然请求示例：“用圆点角色微冒险做一条完整短片：第一次跳起来，落地也算进步。挡在前面的，可以一步步越过。天暗了，才看见远处的星星。朝它走近一点，再近一点。小小一步，也算出发。” 先调用 `studio.py intent`、`templates match --format 16:9`，由Codex按内容选择；再复制本套native工程、重写全部故事及本类画面字段，更新project.json哈希，通过 `templates prepare → plan → workflow → 已授权make`。不要覆盖本片或父版。

## 市场与类型

分类：情绪与剧情。来源关系：直接形式适配，非原作质量认证。 原片：https://x.com/cherry_mx_reds/status/2105825930799432073；公开快照赞6293、播放859822（未知为None）。学习操作：同一有表情圆点角色→跳跃障碍→昼夜空间变化→接近星星→角色触发收束。差异：市场形式适配，不冒充原作材质、作者工程、留存或新片流量；仅16:9编排。 原片互动不能证明本片流量、留存或用户认可。
