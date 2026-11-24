# AVS 原生交接

触发：用户指定 AVS Episode，或经创作选路确定需 AVS 原生素材/内容流程。先运行 `python3 -B scripts/studio.py avs-next <Episode>`；也可给 Workflow `route:avs` 或 `avs-render`，后者是同一条链的别名。状态唯一依据是 `runtime/avs/episodes/<目录>/episode.json`，不可用工作室 current 推测阶段。

按返回的 `next_action.reads` 只读当前阶段的实际 Skill/Schema，同时读 Episode、input、work/input-manifest.json 和当前合同。路径相对工作室根目录。`required_artifacts` 沿用上游语义，须区分输入/输出。不存在的内容就是缺项，不能用相似样片或合法空 JSON 补成“完成”。源 Skill 的安装、Provider、自动续跑及授权默认值不继承；仅本机 Codex `gpt-6.1-sol` 判断，脚本不请求模型。

| 当前原生关口 | 工作室入口、产物和停止条件 |
|---|---|
| analyze | Codex 实际读材料后，`avs.sh --mode production adopt-analysis <Episode> <candidate.json>` 验证并写四份 `work/analysis/{asset-intelligence,recording-analysis,document-analysis,transcription}.json`。素材身份/原始哈希/ROI/观察方法/Schema 不符就拒绝；未看或未听不能填真实观察，不调用旧 analyze Provider |
| plan | `avs.sh --mode production plan <Episode> [--platform douyin\|xiaohongshu]` 复用固定 `active_plan`，写六份 `work/content/{creative-brief,reference-selection,hook-selection,script,evidence-map,shot-plan}.json` 及 codex-plan 绑定。先有本机 Codex 脚本、原生创作说明和分析证据；保留创作说明原字节、原参考规则及已确认分段。拒绝 force/regenerate-script，不带交易样例默认值 |
| preview | `avs.sh stage-check preview <Episode>` 只读前置检查；真正执行 `avs.sh --mode production preview <Episode>`。须当前规划八份绑定与素材仍匹配、已有 narration/original_voice；现存时间线须有 voice 轨。没有声音就停，不自动 Edge TTS。无对白/MV 用 code/Vibe/editor 路线 |
| visual-review | Codex 真实观看当前预览后，`adopt-visual-review <Episode> <candidate.json>` 写 `work/qa/visual-review.json`。绑定 manifest/script/evidence-map/shot-plan/timeline 及当前优先预览（motion 优先于 captions）；passed 与 failures 一致。失败按时间码/修法返回，不跳到 final-render |
| final-render | 只读 `stage-check final-render`，实际执行须 `--mode production final-render`；同版本机视觉审查通过、绑定和当前优先预览 SHA 全部一致。新增 motion 预览会使只看过 captions 的审查失效 |
| technical-qa | `stage-check technical-qa` / `--mode production qa` 复用原生机器 QA，不等于观看/听审 |
| creative-review | `stage-check creative-review` / `--mode production creative-review` 仅生成原生审片包、联系表与客观度量。下一环节才是真实审片，不能把包准备或文件存在写成“已评分” |
| creative-gate | 真实播放/听审同版视频后 `adopt-creative-review <Episode> <candidate.json>`。按原生十维分数、findings 和有限返修轮次写回现有 creative-review，保留 deterministic 度量和发现；失败阻塞在 Episode，对应旧观察先归档。不能无限评分循环、不凭文本自评冒听审 |
| approve | 用户确实确认同版产物后 `adopt-approval <Episode> <candidate.json>`；六项 checklist 显式 true、真实 user_message 引用/原文/确认人、当前 QA/审片包/视频指纹均须有效。没有实际消息就停止等待，不由 Codex 自行批准 |
| deliver / export | 对应 `stage-check deliver\|export` 和 `--mode production deliver\|export` 复用 AVS 本地原生包/导出。它们写原生 Episode，遵守 AVS 生产模式，不等于工作室 delivery 复制、更不包含上传/发布 |
| story-mine / direct / pilot-review | 历史 SCREEN_DOCUMENTARY 的 VCI/交易 Pilot 专用链保留来源，但返回未连接，不把旧包/交易事实/评审人迁为新任务。新录屏优先 editor 或通用 AVS；需要该专用链再单列适配 |

上表简写均为 `bash scripts/avs.sh ...`。所有 `adopt-*` 与执行命令必须先有具体制作授权，调用时在子命令前加 `--mode production`；本轮框架授权不能据此推进真实 Episode。`stage-check`、`runtime-check`、`validate-script` 只读，不创建视频。工作室 `workflow` 也只读；`review` 仅允许审查关口，`export` 仅原生下一步 export，`revise` 返回原生 findings/副本手工修改的停止点，不自动 reset。

## 候选观察合同与实际读取

复用原生格式，不注册新 Schema。写回器实现为 `scripts/avs-adopt.py`；分析字段参考 `runtime/avs/schemas/{input-manifest,asset-intelligence,recording-analysis}.schema.json`，文档/转写结构沿原生分析文件。规划读 `runtime/avs/schemas/{active-script,creative-brief,reference-selection,evidence-map,shot-plan}.schema.json`，hook 输出仍用原生格式。审查与确认沿 `runtime/avs/src/avs/qa/{creative_review,approval}.py` 和 `delivery/package.py`。具体读取由 `avs-next` 返回，不能把本文列表全量塞入每轮。

候选通用信封示意（未填写，不是已发生的观察，也不可直接批准）：

```json
{
  "episode_id": "本次实际 Episode ID",
  "reviewed_by": "codex:gpt-6.1-sol",
  "bindings": {"Episode 内实际相对路径": "该次读取的 SHA-256"},
  "observations": [{"asset_id": "实际素材 ID", "method": "document_read", "observation": "实际读到的事实与范围"}],
  "contracts": {"当前关口合同名": {"按原生格式填写": "仅填写真实结果"}}
}
```

- analyze 的 bindings 必须精确包含 manifest 和全部 ok 素材（working_path 优先）；观察按类型为 document_read、actual_view/actual_playback 或 actual_listening/verified_transcript。不能把“文件存在”写成理解成功；真实转写缺能力就停。
- visual-review 的 bindings 是 manifest、script、evidence-map、shot-plan、timeline 和当前优先预览；contracts 仅 visual-review，至少显式 passed/failures；发现含 failure_code/timestamp/required_fix，observations 是实际画面观察。
- creative-gate 的 contracts 仅 creative-score；scores 十维名称从原生 SCORE_WEIGHTS 读取，0–10，reviewed_artifacts 包含当前最终视频；bindings 另含 QA、原生审片包及实际查阅附件。observations 需 actual_playback 与 actual_listening，repair_round 保持原生 0–3、再次提交逐次加一。字幕/声音不适用时不能谎填，先选兼容路线。
- approve 的 contracts 仅 visual-approval；human_evidence 包含 source=user_message、reference、text、reviewer。checklist 六项名称用原生 approval.py；程序只核来源字段/一致性，不能替代 Codex 核实消息确属该用户和该版。回执始终 accepted=false，不伪造额外用户认可。

## 原生状态、失败与恢复

`episode.json` 最后提交，Codex 观察回执记录 `validated_here=native_contract_and_provenance_only` 与 model_session_verified=false。合同成立只说明结构与绑定，不证明模型/观察真的发生。失败审核设置 blocked_stage；只读查询把 analyze/visual-review/creative-gate 恢复关口解释回对应写回路径，绝不绕过失败。

同 Episode 的规划/写回/阶段包装共用 `.studio/avs-locks/<身份哈希>.lock`。旧源命令不共享此锁，不并行操作原工程。写回前重新比对输入；已有 Codex 审查及原合同/旧 Episode 保存到 `work/codex-history/<stage>/<旧回执哈希>/`，保留首次失败。跨文件不承诺数据库事务，中断后先核 Episode、当前合同、历史回执和产物，再恢复；不盲重投渲染或未知任务。

实际 `EP-STUDIO-FOCUS` 本轮保持 INGESTED/analyze，新增阶段/写回只在隔离合同夹具检查，没有生成视频或执行原生媒体阶段。原 `run/resume/analyze/visual Provider`、自动 TTS 和旧默认 approve 均不开放。查询结束报告 Episode、原生阶段、已验范围、缺项及下一允许动作。
