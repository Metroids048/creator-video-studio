---
name: studio-template-halftone-mascot
description: 半色调角色产品发布，按完整内容换稿。
---

读取native/story.json、main.js、draw.js及project.json。市场原片：https://x.com/achxvi/status/2103918792845963545。保留网点材质角色提出用户问题→同一角色带出产品界面→操作产生可见结果→品牌落定。换稿必须同时重做角色造型与网点映射、用户问题、真实或明确虚构的产品界面、操作状态、结果数量、品牌；不只改标题。替换完整分镜，时序连续覆盖全片。需要新动作或新物件时改main.js对应画面，不通过字幕掩盖。更新changed_files，绑定完整同版音轨，经studio.py templates prepare→plan→workflow→授权make。看完整最终MP4，核画面动作、数量、因果和完整声音。修复绑定确切父版；不以技术检查替代视听质量。

## 本轮完整新稿

成片：`works/halftone-mascot-fresh-1114/versions/v0001/video.mp4`（24.0秒，16:9），SHA256 `cf21c38eddf15654a79a52fa47bb7c7a470a68d36a788173b4e16b6b0e3696b6`。完整故事：`works/halftone-mascot-fresh-1114/versions/v0001/shots/native-style/film/engine/story.json`。同版可编辑工程：`works/halftone-mascot-fresh-1114/versions/v0001/editable.zip`；真实制作输入：`works/halftone-mascot-fresh-1114/versions/v0001/brief.json`。

全程1fps实际查看：三项收集、海边搜索两项、结果3/2与字幕一致，角色贯穿。 完整时长本机MiniCPM音频感知；实际结果见 final-audio-jobs-results.json；未观察到尖锐提示音、爆音或突切。 用户尚未审看。

自然请求示例：“用半色调角色产品发布做一条完整短片：想留下的文章、照片、链接，总散在各处。一起收好，三个入口放进同一个收藏。搜索“海边”，找到两条相关内容。留下来，才找得回来。” 先调用 `studio.py intent`、`templates match --format 16:9`，由Codex按内容选择；再复制本套native工程、重写全部故事及本类画面字段，更新project.json哈希，通过 `templates prepare → plan → workflow → 已授权make`。不要覆盖本片或父版。

## 市场与类型

分类：品牌与产品。来源关系：直接形式适配，非原作质量认证。 原片：https://x.com/achxvi/status/2103918792845963545；公开快照赞9179、播放1147282（未知为None）。学习操作：网点材质角色提出用户问题→同一角色带出产品界面→操作产生可见结果→品牌落定。差异：市场形式适配，不冒充原作材质、作者工程、留存或新片流量；仅16:9编排。 原片互动不能证明本片流量、留存或用户认可。
