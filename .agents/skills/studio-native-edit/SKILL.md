---
name: studio-native-edit
description: 为工作室的录屏、已有素材、AVS Episode、原生时间线或未知状态的旧任务做只读交接和工程恢复。
---

阶段操作统一读取[阶段交接与局部返修](../../../docs/阶段交接与局部返修.md)。已接入阶段交接的代码返修先定位实际失效字段，在候选brief保留父合同，只reopen拥有字段的阶段；补丁入口复核实际消费结果。独立AVS/Vibe和原生锁轨补丁仍按各自门禁，不宣称已统一接线。


最小改动救片先消费[开箱刀失败反例](../../../docs/reviews/2026-11-15-开箱刀阶段复盘.md)：画稿是可删、并、换序的资产，不要求逐张展示；先核每段新后果和选择，再排时间线，不能靠重复拆包装、补帧或停顿填满90–120秒。当前片的Dylan音轨和已否决口吻不得继续拼入，新声音需实际比较后再扩全稿。保留原素材与工程，仅补必要因果缺口，不整片重做；这项指引不是已修好故事或声音的证据。

## 2026-11-15参考方法的实际使用

已有素材先区分“仅修显示字幕”“重做发音”“实际剪音频/画面”；分别维护源时间→成片时间映射，字幕不能假装修好了原音。按同版真实音轨对齐，不继承Fred固定倍速/增益或作者声音。修改前读取当前工程并保留锁定轨、手工调整和原素材。OpenFilm的film.html/frame(t)/独立轨道是源码研究候选，尚无本项目适配器，不得虚构engine或转格式成功。分块缓存恢复先核源文件/参数/版本，取消成功不当然可续跑。

具体证据及边界见[七条参考与源码复盘](../../../docs/research/2026-11-15-原片源码与工作室复盘/研究总览.md)，执行沿现有[P1–P6](../../../docs/research/2026-11-13-后续制作方法与Prompt.md)及[制作流程](../../../docs/制作流程.md)。这些为当前Skill执行指引；除明确列出的CLI检查外，不声称已实现自动质量拦截或新增生产能力。


输入为录屏/素材、受保护操作和音轨、原生包路径或作品/回执 ID。输出素材身份、关键区间、引擎、原生入口、父版与锁定项。

- 录屏先标记关键点击、交互结果与不能裁掉的时间。按需用 `runtime/avs/skills-src/screen-story-miner/SKILL.md`、同级 `mobile-screen-director/SKILL.md` 和 `resources/host-skills/ffmpeg/SKILL.md` 的方法。用 `scripts/studio.py avs-next <Episode>` 核对真实状态；不续跑旧 Agent。
- 原生编辑查 `scripts/studio.py status <id>`。局部修改先比对当前父版和锁轨，用 `native-edit-plan` 查补丁；交接单的 `locked` 沿用补丁轨道名称，与文字 `locks` 对应。漏锁、工程包与原生目录不符时保留现场并停止，不覆盖现版。
- 新录屏编辑方案先用 `python3 scripts/studio.py plan <brief.json>`，或交给 `workflow` 的 editor plan。它以只读 FFprobe 元数据和固定原生时间线规则检查操作、时间范围、画幅与音轨，返回 `editor_timeline`；不准备媒体、不读旧 Provider 配置、不渲染。源元数据不能保证转码后的精确帧边界，实际制作仍须重新校验准备后的素材。失败先修合同，不以制作命令试错；整份操作清单的返修、重建和未完成候选也经过相同预检，锁轨补丁则走 `native-edit-plan`。
- 独立 Vibe 工程用 `bash scripts/vibe.sh inspect <id>`，返回 `works/vibe-<id>/` 的实际合同、模板和哈希，再用 `gate <id> --stage plan` 查原生记录。Workflow 填 `route: "vibe"`；`inspect/continue` 停在 `native_status`。Vibe 仍由 `FILM_STATUS.md` 与原生文件管理阶段，不能把 MP4 存在视为可续做、通过审片或可导出版本。
- 原样恢复先 `inspect-bundle`。只有用户已授权恢复才走 `--mode recovery import-native`；包导入与重渲染为不同动作。绑定现有工件前查哈希、输入、版本和原生时间线。
- 断流或未知任务用已有回执查询。记录 provider、任务 ID、观测状态和下一步；外部请求不自动重投。无回执时停在状态核对。
- 按需读 `resources/host-skills/chatcut-asset-import/SKILL.md` 的素材处理和 `resources/host-skills/chatcut-verification/SKILL.md` 的验收方法。实际插件及云操作独立授权，本地结构验收用现有原生编辑器和 FFmpeg。
