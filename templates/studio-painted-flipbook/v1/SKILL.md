---
name: studio-template-painted-flipbook
description: 整页彩绘旅行翻页书，按完整内容换稿。
---

读取native/story.json、main.js、draw.js及project.json。市场原片：https://x.com/ann_nnng/status/2102573127192727704。保留封面主题→整页插画的地点变化→页卷翻转连接→人物贯穿→回家收束。换稿必须同时重做完整旅程与地点、各页场景和人物动作、全页绘画、页序与卷页时点、配乐与记忆短句；不只改标题。替换完整分镜，时序连续覆盖全片。需要新动作或新物件时改main.js对应画面，不通过字幕掩盖。更新changed_files，绑定完整同版音轨，经studio.py templates prepare→plan→workflow→授权make。看完整最终MP4，核画面动作、数量、因果和完整声音。修复绑定确切父版；不以技术检查替代视听质量。

## 本轮完整新稿

成片：`works/painted-flipbook-fresh-1114/versions/v0001/video.mp4`（30.0秒，16:9），SHA256 `cb491ee01b13dff672019cc5e9dbc60262620f1f387c8fad32db4dd68dad2d70`。完整故事：`works/painted-flipbook-fresh-1114/versions/v0001/shots/native-style/film/engine/story.json`。同版可编辑工程：`works/painted-flipbook-fresh-1114/versions/v0001/editable.zip`；真实制作输入：`works/painted-flipbook-fresh-1114/versions/v0001/brief.json`。

全程1fps实际查看：六个全页地点、人物贯穿、卷页与回家收束；不是照片画册复刻。 完整时长本机MiniCPM音频感知；实际结果见 final-audio-jobs-results.json；未观察到尖锐提示音、爆音或突切。 用户尚未审看。

自然请求示例：“用整页彩绘旅行翻页书做一条完整短片：一起出发，也不必走得一样快。雨来的那天，我们坐同一列车。到了海边，才记得慢一点走。上坡的时候，轮流等对方一下。夜里，星星把沉默也照亮了。回到家，翻开这一页，还在一起。” 先调用 `studio.py intent`、`templates match --format 16:9`，由Codex按内容选择；再复制本套native工程、重写全部故事及本类画面字段，更新project.json哈希，通过 `templates prepare → plan → workflow → 已授权make`。不要覆盖本片或父版。

## 市场与类型

分类：音乐与图文。来源关系：直接形式适配，非原作质量认证。 原片：https://x.com/ann_nnng/status/2102573127192727704；公开快照赞1924、播放134106（未知为None）。学习操作：封面主题→整页插画的地点变化→页卷翻转连接→人物贯穿→回家收束。差异：市场形式适配，不冒充原作材质、作者工程、留存或新片流量；仅16:9编排。 原片互动不能证明本片流量、留存或用户认可。
