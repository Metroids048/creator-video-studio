---
name: studio-template-recipe-pour
description: 用同一刻度杯完整演示饮品配方，材料计量、倒入动作与累计液面一致。
---

读native/story.json、main.js、project.json。先列完整材料及计量口径，再重写steps和容器几何，ml与液面映射、累计总量、加入时序与倒液段都需随新稿变化。每步需有动作、落点和成品结果；禁止只换标题。新容器不是线性截面积时按截面积积分映射体积。更换原生9:16构图须重新核字与安全区。更新changed_files，templates prepare→plan→workflow→已获授权的make。全片实际查看每个加入动作、冰和配料关系、刻度和合计；完整听同版音轨。源帖仅为语法参考，不复制原歌或媒体。

## 本轮完整新稿

成片：`works/recipe-lemon-tea-1114/versions/v0004/video.mp4`（30.0秒，9:16），SHA256 `52212331371e9b768d11bb6ef652f9b63bea12fac0e979394bb39114d7e03ec8`。完整故事：`works/recipe-lemon-tea-1114/versions/v0004/shots/native-style/film/engine/story.json`。同版可编辑工程：`works/recipe-lemon-tea-1114/versions/v0004/editable.zip`；真实制作输入：`works/recipe-lemon-tea-1114/versions/v0004/brief.json`。

v4全程1fps实际查看：空杯0mL后加冰，四液80+80+20+10累计190mL，装饰与搅拌完整；无初始负液面。 v4与已感知完整音轨的v2解码PCM一致；复用recipe-and-three-audio-results.json中原音轨观察。 用户尚未审看。

自然请求示例：“用刻度杯连续倒液配方，做一杯柠檬气泡茶，按步骤显示每项用量，从空杯到搅拌完成。” 先调用 `studio.py intent`、`templates match --format 9:16`，由Codex按内容选择；再复制本套native工程、重写全部故事及本类画面字段，更新project.json哈希，通过 `templates prepare → plan → workflow → 已授权make`。不要覆盖本片或父版。

## 市场与类型

分类：教程与过程。来源关系：直接形式适配，非原作质量认证。 原片：https://x.com/Ror_Fly/status/2102853258582880547；公开快照赞1049、播放81370（未知为None）。学习操作：同一容器贯穿→材料量与倒入动作同步→液面准确累积→点缀搅拌→成品。差异：二维配方图解；非实拍；体积不含冰和点缀；不可把自拟配方说成名家标准。。 原片互动不能证明本片流量、留存或用户认可。
