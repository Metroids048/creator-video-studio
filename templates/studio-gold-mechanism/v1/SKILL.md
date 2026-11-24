---
name: studio-template-gold-mechanism
description: 黑金粒子与可数机制图解，按完整内容换稿。
---

读取native/story.json、main.js、draw.js及project.json。市场原片：https://www.douyin.com/video/7693248909879212362。保留反直觉问题→同一组可追踪对象→枚举对照→条件概率解释→前提与结论。换稿必须同时重做核实的问题与前提、对象和数量、可枚举状态、参数方程、反例及边界、字幕；不只改标题。替换完整分镜，时序连续覆盖全片。需要新动作或新物件时改main.js对应画面，不通过字幕掩盖。更新changed_files，绑定完整同版音轨，经studio.py templates prepare→plan→workflow→授权make。看完整最终MP4，核画面动作、数量、因果和完整声音。修复绑定确切父版；不以技术检查替代视听质量。

## 本轮完整新稿

成片：`works/gold-mechanism-fresh-1114/versions/v0001/video.mp4`（28.0秒，16:9），SHA256 `e608675a376de1d93fed6917f4c1006b841a39e23eadb1dc11d5fbd8a950e4fc`。完整故事：`works/gold-mechanism-fresh-1114/versions/v0001/shots/native-style/film/engine/story.json`。同版可编辑工程：`works/gold-mechanism-fresh-1114/versions/v0001/editable.zip`；真实制作输入：`works/gold-mechanism-fresh-1114/versions/v0001/brief.json`。

全程1fps实际查看：16组四币序列，前三正面对应两组；公平独立前提与50/50相符。 完整时长本机MiniCPM音频感知；实际结果见 final-audio-jobs-results.json；未观察到尖锐提示音、爆音或突切。 用户尚未审看。

自然请求示例：“用黑金粒子与可数机制图解做一条完整短片：连着三次正面，下一次更该反面吗？公平且独立的抛掷，每次仍然各占一半。16种四次序列里，前三次正面的两种，最后一面各一种。独立事件，不欠你一个反转。” 先调用 `studio.py intent`、`templates match --format 16:9`，由Codex按内容选择；再复制本套native工程、重写全部故事及本类画面字段，更新project.json哈希，通过 `templates prepare → plan → workflow → 已授权make`。不要覆盖本片或父版。

## 市场与类型

分类：知识与机制。来源关系：直接形式适配，非原作质量认证。 原片：https://www.douyin.com/video/7693248909879212362；公开快照赞11338、播放None（未知为None）。学习操作：反直觉问题→同一组可追踪对象→枚举对照→条件概率解释→前提与结论。差异：市场形式适配，不冒充原作材质、作者工程、留存或新片流量；仅16:9编排。 原片互动不能证明本片流量、留存或用户认可。
