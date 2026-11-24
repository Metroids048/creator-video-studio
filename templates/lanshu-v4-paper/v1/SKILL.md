---
name: studio-template-lanshu-v4-paper
description: 纸艺弹出书。用于温暖的流程、成长与解释，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/paper-bridge-1114/versions/v0002/video.mp4` 和 `/works/paper-bridge-1114/versions/v0002/shots/native-story/film/scene.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`sources/zh-explainer/vendor/lanshu/explainer/kits/v4-paper/KIT.md`。

固定语法：空间被隔开→折纸结构建立连接→物件越过→交付结果。

新输入示例：“用纸艺弹出小镇讲一份礼物跨过纸桥送到家门口。”

逐项换稿：两岸布局、折叠几何、桥梁高度、物件路径、到达时点。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。蓝叔原生 story.json + beats.js 编排为 brief，镜头 engine=lanshu、style=v4-paper；参考同版 brief。templates prepare 不编译蓝叔。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → plan <新brief> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/paper-bridge-1114/versions/v0002/editable.zip`；确切输入：`works/paper-bridge-1114/versions/v0002/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：仅横屏已适配；新故事的画面编排、字幕与视听必须另验。

## 市场与类型

分类：教程与过程。来源关系：形式／材料迁移，非逐镜复刻。 原片：https://www.douyin.com/video/7659692677034061169；公开快照赞23143、播放None（未知为None）。学习操作：纸张层叠与成品揭晓。差异：原片真实手工，新稿为程序折纸弹出桥，不具备手工过程实拍。。 原片互动不能证明本片流量、留存或用户认可。
