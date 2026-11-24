---
name: studio-template-paper-question
description: 撕纸拼贴多场景问答故事，按完整内容换稿。
---

读取native/story.json、main.js、draw.js及project.json。市场原片：https://x.com/kevin_t_ngo/status/2102437977435893771。保留主角提出一个情感问题→纸张承载问题移动→多个生活场景回应→答案回到主角→动作结尾。换稿必须同时重做问题与答案、主角与信使、连续场景、纸张纹理与拼贴物件、传递动作及收束；不只改标题。替换完整分镜，时序连续覆盖全片。需要新动作或新物件时改main.js对应画面，不通过字幕掩盖。更新changed_files，绑定完整同版音轨，经studio.py templates prepare→plan→workflow→授权make。看完整最终MP4，核画面动作、数量、因果和完整声音。修复绑定确切父版；不以技术检查替代视听质量。

## 本轮完整新稿

成片：`works/paper-question-fresh-1114/versions/v0002/video.mp4`（28.0秒，16:9），SHA256 `1b1df2e156a47a8e7a72c5ef8cf237887252bf96c584bccc908d8aa99923f922`。完整故事：`works/paper-question-fresh-1114/versions/v0002/shots/native-style/film/engine/story.json`。同版可编辑工程：`works/paper-question-fresh-1114/versions/v0002/editable.zip`；真实制作输入：`works/paper-question-fresh-1114/versions/v0002/brief.json`。

v2全程1fps实际查看：开场问题已移出信封遮挡，纸鸟过四户、回复与晚归点灯闭环。 完整时长本机MiniCPM音频感知；实际结果见 final-audio-jobs-results.json；未观察到尖锐提示音、爆音或突切。 用户尚未审看。

自然请求示例：“用撕纸拼贴多场景问答故事做一条完整短片：她写下一句话，折成小小的信。小鸟把它带过，仍然亮着的窗。回信只有一句：给晚归的你。有人留灯，路就有了尽头。” 先调用 `studio.py intent`、`templates match --format 16:9`，由Codex按内容选择；再复制本套native工程、重写全部故事及本类画面字段，更新project.json哈希，通过 `templates prepare → plan → workflow → 已授权make`。不要覆盖本片或父版。

## 市场与类型

分类：情绪与剧情。来源关系：直接形式适配，非原作质量认证。 原片：https://x.com/kevin_t_ngo/status/2102437977435893771；公开快照赞6184、播放675294（未知为None）。学习操作：主角提出一个情感问题→纸张承载问题移动→多个生活场景回应→答案回到主角→动作结尾。差异：市场形式适配，不冒充原作材质、作者工程、留存或新片流量；仅16:9编排。 原片互动不能证明本片流量、留存或用户认可。
