---
name: studio-template-mechanical-cutaway
description: 金属机械剖面与同轴爆炸图，按完整内容换稿。
---

读取native/story.json、main.js、draw.js及project.json。市场原片：https://x.com/konstantinsaifo/status/2104094723887501736。保留连续三维对象→外壳剖开→同轴零件与运动→轴向爆炸→复装对应。换稿必须同时重做实际机械结构或明确示意、零件几何与材质、装配坐标、运动关系与剖面角度、镜头与标注；不只改标题。替换完整分镜，时序连续覆盖全片。需要新动作或新物件时改main.js对应画面，不通过字幕掩盖。更新changed_files，绑定完整同版音轨，经studio.py templates prepare→plan→workflow→授权make。看完整最终MP4，核画面动作、数量、因果和完整声音。修复绑定确切父版；不以技术检查替代视听质量。

## 本轮完整新稿

成片：`works/mechanical-cutaway-fresh-1114/versions/v0001/video.mp4`（28.0秒，16:9），SHA256 `708daa103d1aa570658a90dff3069d5d38ca6772c3d65c6a212196f4568151c8`。完整故事：`works/mechanical-cutaway-fresh-1114/versions/v0001/shots/native-style/film/engine/story.json`。同版可编辑工程：`works/mechanical-cutaway-fresh-1114/versions/v0001/editable.zip`；真实制作输入：`works/mechanical-cutaway-fresh-1114/versions/v0001/brief.json`。

全程1fps实际查看：外壳剖开、固定线圈、旋转轴、同轴分离与重新装合清楚；仅为结构示意。 完整时长本机MiniCPM音频感知；实际结果见 final-audio-jobs-results.json；未观察到尖锐提示音、爆音或突切。 用户尚未审看。

自然请求示例：“用金属机械剖面与同轴爆炸图做一条完整短片：固定外壳与线圈，里面藏着转子。转轴带动叶片，轴承支撑转动。沿轴线拆开，零件仍然一一对应。复装之后，转动关系才完整。” 先调用 `studio.py intent`、`templates match --format 16:9`，由Codex按内容选择；再复制本套native工程、重写全部故事及本类画面字段，更新project.json哈希，通过 `templates prepare → plan → workflow → 已授权make`。不要覆盖本片或父版。

## 市场与类型

分类：知识与机制。来源关系：直接形式适配，非原作质量认证。 原片：https://x.com/konstantinsaifo/status/2104094723887501736；公开快照赞8384、播放1185524（未知为None）。学习操作：连续三维对象→外壳剖开→同轴零件与运动→轴向爆炸→复装对应。差异：市场形式适配，不冒充原作材质、作者工程、留存或新片流量；仅16:9编排。 原片互动不能证明本片流量、留存或用户认可。
