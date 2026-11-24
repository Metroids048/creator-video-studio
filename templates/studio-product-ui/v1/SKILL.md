---
name: studio-template-studio-product-ui
description: 产品界面流程发布片。用于事情很多，先放进同一个地方。只看今天，留给眼前的三件事。完成一件，就把它移到右边。两项完成。给下午，减一点重量。，读取本套完整新稿并按画面语法换内容。
---

先看 `/works/product-ui-story-1114/versions/v0001/video.mp4` 和 `/works/product-ui-story-1114/versions/v0001/shots/native-style/film/engine/story.json`（路径均相对项目根），核目标画幅 16:9。样片是本轮完整新稿，用户尚未验收；不能承诺流量。原工程规范：`templates/studio-product-ui/v1/STYLE.md`。

固定语法：任务过多→收拢输入→筛选今天→完成迁移→总结结果。

新输入示例：“用产品界面动效演示虚构轻签便签，把今天三件事完成两件。”

逐项换稿：产品状态、数据、操作轨迹、结果数量、标识和事实边界。先把新稿每一段写成“原因→动作→可见结果”，再改几何、物件、数据和动作；只换标题不成立。把新稿项目路径写入 input.json 的 project 字段；native/project.json 同步 template、style、duration、content_promise 与 changed_files 哈希。

制作入口：`studio.py intent '<自然输入>'` → `templates match '<自然输入>' --format 16:9` → Codex选择本套 → 复制可编辑工程到新工作目录 → --mode development templates prepare <新输入> --to <新目录> → plan <新目录/brief.json> → `workflow <任务>` → 已授权的 `--mode production make <brief>`。不要覆盖本例或父版。完整可编辑包：`works/product-ui-story-1114/versions/v0001/editable.zip`；确切输入：`works/product-ui-story-1114/versions/v0001/brief.json`。

验收本片：逐段核实际结果与字幕时点；观看完整最终导出、听完整实际音轨；接触音核每个事件而非只测峰值。查到缺陷用本作品实际父版 revise-picture / revise-audio，复用未变输入。不把导出成功、模型评分或自动检查当成用户认可。限制：本例为虚构轻签界面；真实产品须换成同版本录屏或正确界面状态，不宣称已验证其功能。仅核16:9。

## 市场与类型

分类：品牌与产品。来源关系：直接形式适配，非原作质量认证。 原片：https://x.com/Miguel07Code/status/2102441708395041170；公开快照赞1315、播放150893（未知为None）。学习操作：任务过多→收拢输入→筛选今天→完成迁移→总结结果。差异：本例为虚构轻签界面；真实产品须换成同版本录屏或正确界面状态，不宣称已验证其功能。仅核16:9。。 原片互动不能证明本片流量、留存或用户认可。
