# P3 当前状态

## 2026-10-11 当前收敛状态（覆盖下方历史时点）

最新有限目标为 `plans/CNW_PUBLIC_REPLICATION_GOAL.md`。余项组1–5已独立限定签收、推送/回读；组6同一J19前10阶段真实完成，Re-review五Lens及20个Verifier成功后预算中止，缺40个Verifier及最终正常处置。当前共享CNY9.874291/10，剩余0.125709；不新增付费、不改票、不手修正文。运行持久化 `EXECUTION_INCOMPLETE`，导出 `UNREVIEWED_CANDIDATE`，verify-live拒绝不完整全链。146项相关离线通过。实证与功能限制见 `evidence/CNW_C04_C10_C15_CURRENT_CHAIN_DIAGNOSTIC.md`；完整方法/全生产仍未验收、Chapter/Sprint Live仍NOT_RUN、用户创意亲读及外部源码/结果审待定。下方W10 NOT_STARTED等保留历史，不描述当前已发生的付费运行。

- 当前唯一分支 `main` 已将 P3.1 差异修复和 Controller ACCEPT 正常推送；远端/本地回读一致。用户明确只保留 main，不创建候选分支；不强推、不 reset/clean、不删除既有工作。
- 唯一活动计划：`plans/MASTER_PLAN_P3_1.md`。P3.1 ZIP SHA256=`2550F43B266BFDCAC324F9C24E4DCC7E86B6AA38462B32310A203F54BD6FFDF3`。P3.1 W04/W05 差异修复及 W06–W09 均已同一独立 Controller ACCEPT；下一阶段为 W10 唯一真实场景复测。
- P3 工单包 SHA256：`E3D4E10B7C876A2F4F53B0BFC5560BB24419F975D4A88445FAED993A66BE3CAD`。CNW pin：`97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`；本地捕获 manifest SHA256：`E9B989C52C66AB9BE8C73F09E84BC5BD7D2ECC92F9F1CBFC61BA300DC6CD3983`，98 项。
- 状态：`ENV_READY=ACCEPTED`; `NK_LIVE=ACCEPTED`; `CRITICS_LIVE=ACCEPTED`; `CNW_FULL_PRODUCTION=NOT_VERIFIED`; `PRODUCT_MILESTONE_REOPENED=YES`; `USER_CREATIVE_ACCEPTED=PENDING_USER_READING`。
- W00 `ACCEPTED` 并已推送；W01 `ACCEPTED` 并已推送。详细 Controller 消息、精确候选 C/T 及远端回读见 `reviews/P2_ACCEPTANCE_LOG.md` 中追加的 P3 W00/W01/W04 记录。
- P2 的旧 EP001 与 `0b40876b` 历史签收标记为 `HISTORIC_SMOKE_SAMPLE`。这保留工程签收事实，但不作为 P3 正文质量或 CNW 全流程证据。
- P3 第一轮只重做同一场《苍歧》J19 插场；不写第二场，不批量生成。W10 之前不进行本轮真实作品生成。
- API 费用：P3 至今无新增调用；仅沿用已批准剩余预算和既有 `p2_cost_guard`。
- P3.1 独立 Controller 已接受 W04/W05 差异补齐，记录见 `reviews/P3_1_DIFF_AUDIT.md`。双原稿 Markdown/JSON 离线链路未调用 provider；Canon 候选均为 `TODO_CONFIRM`，不代表 Canon 已确认或新剧本已完成创作。
- W07 `MOCK_ONLY` 与 W10 真实 DeepSeek 调用验收严格分开；当前无新增真实模型调用。W10 Live 门已逐项校验 receipt 与原始响应、账本结算及完整 5 Lens+3 Verifier 独立 ID 集合，但 W10 本身尚未执行。

- W03 私有候选合同：`workspace/cangqi/contracts/CQ-J19-INSERT-01.work_unit_contract.json`，SHA256=`e5ef4ce8d4468756021b8b7a8e10dd3cff0b9445e25a6a399f3cc683bb0978d0`；《苍歧》source_manifest SHA256=`D3A15ECB58D1ECB01CDB7B97054A274773B146ED46B10E72F05F8EA3117233CF`；CNW 捕获 manifest 单独记录于 policy，为 `E9B989C52C66AB9BE8C73F09E84BC5BD7D2ECC92F9F1CBFC61BA300DC6CD3983`。正文源文件及 J19 前后锚哈希经本机原稿实测。Controller 已按该 SHA 预审接受并冻结；该签收不代表授权生成。

## 阶段记录

| 阶段 | 状态 | 说明 |
|---|---|---|
| W00 | ACCEPTED | 固定 CNW 原件安全捕获；98 项 manifest；已推送 |
| W01 | ACCEPTED | M01–M38 实际代码映射与方法覆盖差异；已推送 |
| W02 | ACCEPTED | Controller C/T ACCEPT；治理状态已分离；零 API；远端回读一致 |
| W03 | ACCEPTED | Controller C/T ACCEPT；合同冻结（1500 字符；1200–1800）；6 项离线测试通过；零 API；远端回读一致 |
| W04 | ACCEPTED | Controller C/T ACCEPT；远端 C/T readback 一致；四岗位离线合同与 NK/CritiCS adapters；13 项离线测试通过；无新 run 产物或 API |
| W05 | ACCEPTED | Controller C/T ACCEPT；远端 C/T readback 一致；离线可恢复 run 调度与 hash/invalidation；23 项测试通过；实际 source-bound run/Plot request/history verify；无 provider request |
| P3.1 W04/W05 delta | ACCEPTED | 同一独立 Controller 接受；已正常推送唯一 main；双原稿链路测试覆盖新来源到角色输入；不代表 Canon 人工确认 |
| W06 | ACCEPTED | 同一 Controller ACCEPT C=`a31c91451dc6e67b714dae434ff0a9ebd765a5d2` / T=`7b7a5859bbf06befea8ebad7e4af2ba7ad981de2`；47 项测试通过；仅构造离线请求与验收门，未生成新正文/未调用模型 |
| W07 | ACCEPTED | 同一 Controller ACCEPT C=`366b296392b432b4a0a82643566b5df42b3b50e0` / T=`257148031c2d2ed9b0984132304196e2be86172e`；57 tests 通过；完整必需来源、隔离五 Lens/三 Verifier、真实投票分类后的全文 Completeness、P2 cost guard dry-run 预算接口；未写账本/无 provider ID/零模型调用 |
| W08 | ACCEPTED | 同一 Controller ACCEPT C=`0b9ce210d2d348e2da6dc8a93171611cbdf02123` / T=`fbc317a5333a42e2dea8a5f35d85f3b76da0f81d`；64 tests 通过；修订验收绑定原始 verifier 响应、来源片段与 manifest，晋升前重算 W06 合同验证、差异记录及已接受计划；未进行真实模型调用 |
| W09 | ACCEPTED | 同一 Controller ACCEPT C=`0940668825e95067cc803eaad962b3d603ab5856` / T=`abf18a7a542068d6c97999d7600ff23987ee2718`；71 项全套测试本机通过；双原稿导入、Episode 长度/节拍/知识边界/缺场退回、五份虚构 Episode Sprint 均为离线；无模型调用/无费用 |
| W10–W11 | NOT_STARTED | W10 才允许本轮唯一一场真实模型端到端验收；W07/W09 mock 不能计入 |

## ATOM-CNW-PUBLIC-1TO1-RESTORE（P3.1 定点恢复覆盖条款）

- 施工文件：`plans/ATOM_CNW_PUBLIC_1TO1_RESTORE.md`（原样存档，SHA256=`14E2E0A8B5C2FE2DC39944FF167FA6086283C5B3D08039A9F3996D9F63493846`）。基线 C=`de49ef2760cfe0c6bee36db0582b7cbef67d825b`，T=`038449ca902bd4523728ad13e83761f2c6d0243e`。
- 代码语义恢复：`CNW_STAGES` 改为原作者 11 阶段（plot → scene_cards → writing_brief → prose → lint_layer1 → lint_layer2 → multi_lens_review → adversarial_verify → completeness_critic → refine → re_review）；`pov` 移出 CNW 阶段，NK 作为 `support_hooks.nk_pov` 在 Brief 前消费；`promote/export/resume/sprint` 为后处理动作。移除“每个写作岗位需外部 Controller 单独批准”的额外门；Controller 只在 Atom 结束做一次工程复核。
- 五 Lens 来源按作者公开文档：style=style_guide+forbidden_patterns；character=character_bible+voice_samples；plot=scene_cards+writing_brief；canon=glossary+timeline+world_bible；story_specific=project_specific_canon。三反证 Verifier 身份改为 correctness / character_consistency / continuity_plausibility，按每个真实 finding × 3 独立请求，零问题时保留 `NO_FINDINGS_TO_VERIFY` 空集合。
- 唯一真实单场 Run：`workspace/cangqi/runs/CNW1TO1-CQ-J19-20261010-01`（私有，Git 忽略），合同 SHA256=`e5ef4ce8d4468756021b8b7a8e10dd3cff0b9445e25a6a399f3cc683bb0978d0`。所有 provider 调用经既有 `p2_cost_guard.py` reserve→send→settle，计入同一 ¥10 账本。
- 覆盖声明：`CNW_PUBLIC_WORKFLOW_STAGE_STRUCTURE=implemented_to_11_public_stages`；`CNW_EPISODE_MULTI_SCENE_LIVE=NOT_RUN`；`CNW_FIVE_EPISODE_SPRINT_LIVE=NOT_RUN`；`CNW_PRIVATE_AUTHOR_AUTOMATION_CODE=NOT_PUBLICLY_AVAILABLE`；`USER_CREATIVE_ACCEPTED=PENDING_USER_READING`。
- 未取得的门：本 Atom 尚无独立只读 Controller 的工程 ACCEPT，也未经当前 ChatGPT 对已推送源码/结果的审查；因此不以本文件声称 Atom 终验通过。

## 2026-10-11 最新目标收敛与实际状态

- 本文件以上记录保留为对应时点历史，不作为当前每项功能已完成的声明。最新目标和停止准则为 `plans/CNW_PUBLIC_REPLICATION_GOAL.md` 的 C01–C15。
- 用户要求完整复现官方公开方法，用于既定主线与情感节点之间的有意义日常事件；时间位置、逐角色当前处境/知情/关系限制须有来源并传至正确岗位。测试用于找实现差异，不手工打磨诊断样本，不以故事零 bug 延长工程。
- 导入方法增量已由独立 Controller 限定 ACCEPT，正常推送 main 并回读一致：C=`fe3733ea208b243755a35c730d5a4c34da7253d3`；T=`0b7abfee3ac7fc72cf3fcfef9e9d975585c0bda6`。不等于整个工作流终验。
- 独立来源研究确认至少仍有方法缺口：C12 跨项目 AI Canon Audit，C13 真实当前项目 Handoff，C05 Brief 相关 Canon/时间/世界/术语读取及按实际说话者选择声线。逐角色当前状态的完整传递仍未验证。
- 当前原稿有相对时间、分支和知情资料，不能声称所有时点/所有分支已自动推导；源缺失保留待确认。官方公开方法不保证玩家喜欢角色或情绪落点。
- `CNW_FULL_PRODUCTION=NOT_VERIFIED`；`PUBLIC_METHOD_EQUIVALENCE_VERIFIED=NO`；Episode/Sprint Live 未运行；`USER_CREATIVE_ACCEPTED=PENDING_USER_READING`。
- 本次目标研究及落盘未新增付费调用或小说正文。完整方法实现与必要证据闭合后停止工程整改，创意亲读和规模 Live 如实另列。

## 2026-10-11 C05 有限输入诊断

- `evidence/CNW_C05_BRIEF_INPUT_DIAGNOSTIC.md` 记录本次修正和独立只读 Controller 限定 ACCEPT：Brief 四份补充 Canon 与完整模板进入真实请求；原样真实 Brief 提取当期知识/关系/时间和行动指令；Prose API/packet 依 Brief 四位说话者选择同一声线，API 只消费 Brief+voice。
- 仅同一 J19 兼容历史 Plot/Cards + 必要正常 NK/Brief，未调用新 Prose，未冒称新全链。66 项相关离线最终通过；已付费 NK/Brief 身份禁网络复用成功，账本未变。
- 修复真实发现的固定 NK 端口误连旧服务：独立端口、直接自有 Node PID、退出及 capture ID 检查。本轮新服务已停止；旧服务未被终止。首笔缺身份结果 `UNKNOWN_NOT_ZERO` 留存 0.028333 CNY；成功两笔 0.062025 CNY，campaign committed 4.521101/10 CNY（含未知预留）。
- 保留清理/manifest 自身异常的 pending 恢复边界及 Windows 临时 mock ledger 偶发 WinError 5；不宣称它们已修复。C12/C13、当前状态全链及完整等价终验仍未完成。

## 2026-10-11 C12/C13 有限维护验证

- 前次 C05 限定签收提交已推送/远端回读一致：C=`f135e4e8b52915bf24fc661a77c48df76dfd96ee`，T=`ac9672c2b7010d5cd9b3116828558d7b952b831c`。
- `evidence/CNW_C12_C13_MAINTENANCE_DIAGNOSTIC.md`：真正 full Canon Audit 与 pipeline Handoff 各一次正常调用，在静态虚构维护 fixture 上完成；原 request/raw/产物/消费/归档与独立 Controller 限定 ACCEPT 均保留。锁定 Canon/设计/正文未修改；旧作者问题保留；Handoff 消费审计新增行动项。
- 原模型报告过度判定及 Handoff 旧路径措辞原样记录，不手修、不重复付费、不宣称模型准确率。文本去重与语义去重区分；light/targeted/异常恢复为离线覆盖。
- 新两笔保守估算共 0.093960 CNY，campaign committed 4.615061/10 CNY（含前次 UNKNOWN_NOT_ZERO）；无新小说正文、无第二场、无扩预算。入口与恢复/禁网络重入证据见维护文档与诊断。
- 可关闭本次 C12/C13 有限实现缺口。仍须完成其余 C-ID 的总表兼容身份审计、逐角色当期状态通过 J19 全链的消费验证及最终源码/结果审查，完整等价和用户创意接受未签收。
