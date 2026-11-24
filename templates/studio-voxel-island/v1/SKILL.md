---
name: studio-template-voxel-island
description: 体素浮岛昼夜微缩故事，按完整内容换稿。
---

读取native/story.json、main.js、draw.js及project.json。市场原片：https://x.com/blueemi99/status/2105804692811137242。保留有空间层次的体素场景→贯穿角色与任务→昼夜灯光变化→环绕镜头→任务完成。换稿必须同时重做体素地图与场景物件、角色和完整行动、灯光事件、摄像机路径、结尾状态；不只改标题。替换完整分镜，时序连续覆盖全片。需要新动作或新物件时改main.js对应画面，不通过字幕掩盖。更新changed_files，绑定完整同版音轨，经studio.py templates prepare→plan→workflow→授权make。看完整最终MP4，核画面动作、数量、因果和完整声音。修复绑定确切父版；不以技术检查替代视听质量。

## 本轮完整新稿

成片：`works/voxel-island-fresh-1114/versions/v0002/video.mp4`（28.0秒，16:9），SHA256 `c214d97723e1fec68841212f635bb29b426fa65110cc10ebb696e6afa98cd20d`。完整故事：`works/voxel-island-fresh-1114/versions/v0002/shots/native-style/film/engine/story.json`。同版可编辑工程：`works/voxel-island-fresh-1114/versions/v0002/editable.zip`；真实制作输入：`works/voxel-island-fresh-1114/versions/v0002/brief.json`。

v2全程1fps实际查看：屋顶已改为中间高的双坡，角色沿小径到门口，亮灯、昼夜与抬屋顶回落完整。 完整时长本机MiniCPM音频感知；实际结果见 final-audio-jobs-results.json；未观察到尖锐提示音、爆音或突切。 用户尚未审看。

自然请求示例：“用体素浮岛昼夜微缩故事做一条完整短片：一座小岛，也可以有自己的节奏。把最后一点亮光，带回家。天色暗下来，窗户先亮起来。原来，回家的路一直亮着。” 先调用 `studio.py intent`、`templates match --format 16:9`，由Codex按内容选择；再复制本套native工程、重写全部故事及本类画面字段，更新project.json哈希，通过 `templates prepare → plan → workflow → 已授权make`。不要覆盖本片或父版。

## 市场与类型

分类：自然与空间。来源关系：直接形式适配，非原作质量认证。 原片：https://x.com/blueemi99/status/2105804692811137242；公开快照赞1392、播放147288（未知为None）。学习操作：有空间层次的体素场景→贯穿角色与任务→昼夜灯光变化→环绕镜头→任务完成。差异：市场形式适配，不冒充原作材质、作者工程、留存或新片流量；仅16:9编排。 原片互动不能证明本片流量、留存或用户认可。
