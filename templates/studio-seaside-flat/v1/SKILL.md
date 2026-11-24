---
name: studio-template-seaside-flat
description: 海边扁平插画音乐短叙事，按完整内容换稿。
---

读取native/story.json、main.js、draw.js及project.json。市场原片：https://www.douyin.com/video/7694337242181399922。保留固定双人关系→物件承载心意→海面与水下转场→昼夜推进→回信动作收束。换稿必须同时重做双人关系与完整情节、承载物、海岸构图、水下转场和昼夜、回信内容与音乐；不只改标题。替换完整分镜，时序连续覆盖全片。需要新动作或新物件时改main.js对应画面，不通过字幕掩盖。更新changed_files，绑定完整同版音轨，经studio.py templates prepare→plan→workflow→授权make。看完整最终MP4，核画面动作、数量、因果和完整声音。修复绑定确切父版；不以技术检查替代视听质量。

## 本轮完整新稿

成片：`works/seaside-flat-fresh-1114/versions/v0001/video.mp4`（32.0秒，16:9），SHA256 `cd6c48064c16354b711ed9885aa9472c7320e4363b6a322020949377d4132cef`。完整故事：`works/seaside-flat-fresh-1114/versions/v0001/shots/native-style/film/engine/story.json`。同版可编辑工程：`works/seaside-flat-fresh-1114/versions/v0001/editable.zip`；真实制作输入：`works/seaside-flat-fresh-1114/versions/v0001/brief.json`。

全程1fps实际查看：放船、担心、海底切换、夜间带回回复四段完整；无潮汐科普误标。 完整时长本机MiniCPM音频感知；实际结果见 final-audio-jobs-results.json；未观察到尖锐提示音、爆音或突切。 用户尚未审看。

自然请求示例：“用海边扁平插画音乐短叙事做一条完整短片：他们把下一次的约定，折进同一只纸船。漂远一点，会不会就回不来了？海没有回答，只替他们绕过了一段路。风把它送回来：下一次，还是和你。” 先调用 `studio.py intent`、`templates match --format 16:9`，由Codex按内容选择；再复制本套native工程、重写全部故事及本类画面字段，更新project.json哈希，通过 `templates prepare → plan → workflow → 已授权make`。不要覆盖本片或父版。

## 市场与类型

分类：音乐与图文。来源关系：直接形式适配，非原作质量认证。 原片：https://www.douyin.com/video/7694337242181399922；公开快照赞23864、播放None（未知为None）。学习操作：固定双人关系→物件承载心意→海面与水下转场→昼夜推进→回信动作收束。差异：市场形式适配，不冒充原作材质、作者工程、留存或新片流量；仅16:9编排。 原片互动不能证明本片流量、留存或用户认可。
