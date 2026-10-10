# StoryStudio 执行入口 P3.1

本文件是当前执行规则，不是成果已通过声明。活动计划为 `plans/MASTER_PLAN_P3_1.md`，源包 SHA256=`2550F43B266BFDCAC324F9C24E4DCC7E86B6AA38462B32310A203F54BD6FFDF3`；旧 `plans/MASTER_PLAN_P3.md` 是 P3 历史版，不再作为活动施工合同。阶段与验收凭据见 `evidence/P3_CURRENT_STATE.md` 与 `reviews/P2_ACCEPTANCE_LOG.md`。P2 和 P3 既有签收保留历史，不代表 P3.1 新增功能已验收。

## 目标

完成 CNW 固定公开方法映射到 StoryStudio 的可重复生产流水线，按 W00–W11 推进。当前只重做同一场 J19 插场，不扩写第二场；最终交付可运行入口和可读成果。NK 与 CritiCS 的已验证能力作为历史前置复用，CNW 全生产状态目前未验证。

## 执行角色

Writer 负责改代码、运行必要验证、调用已授权的生产 API、提交和推送。独立只读验收子智能体是 Controller：逐阶段审原作者来源、当前实现、真实证据和候选 C/T，给出 ACCEPT/RETURN 并指出最小修正。Writer 不得自签。Controller 的工程 ACCEPT 不等于用户创意接受。

## 约束

- 先读 `plans/P3_1_AUDIT_FIXES.md`、`reviews/P3_1_CONTROLLER.md`、`reviews/P3_1_SOURCE_TO_CODE_MATRIX.md`、`tests/P3_1_ACCEPTANCE_TESTS.md` 和相关实现合同，再按 P3.1 阶段依赖推进。
- 修复当前阶段可自行处理的机械问题；只扩大处理实际影响安全或功能的缺陷。已验证事项按身份复用，不重复证明。
- 保留 CNW 的 Plot → Scene Cards → Writing Brief → Prose → 三层审稿、五 Lens、三 Verifier、Completeness、Refine、Re-review；NK/CritiCS 各按自身职责接入，不能相互冒充。
- 不得以旧 EP001/checkpoint、合规短稿或历史 ACCEPT 声称新生产线完成；旧 P2 样本标为 `HISTORIC_SMOKE_SAMPLE`。
- 用户亲读前不得记录 `USER_CREATIVE_ACCEPTED`。不生产第二场或批量正文。
- 仅使用已授权 DeepSeek Flash 与剩余预算，复用既有成本护栏；密钥和私有稿件不得进入 Git。
- 用户已明确授权仓库只保留 `main`，不要创建候选分支。P3.1 包内候选分支流程与该授权冲突，以用户指令为准；沿 `main` 增量提交，每阶段 Controller ACCEPT 后正常推送并核对远端回读；不强推、不 reset/clean、不删已有进度。

## ATOM-CNW-PUBLIC-1TO1-RESTORE 覆盖条款（2026-10-10）

- 定点恢复施工单已原样存档为 `plans/ATOM_CNW_PUBLIC_1TO1_RESTORE.md`（SHA256=`14E2E0A8B5C2FE2DC39944FF167FA6086283C5B3D08039A9F3996D9F63493846`）。它作为 P3.1 的定点恢复覆盖条款，替代 P3.1 包内候选分支流程；既有 W00–W09 接受记录与 W10/WIP 一律保留。
- CNW 公开 11 阶段、四岗位作者读取合同、五 Lens/三反证/Completeness/Refine/Re-review、NK 与 CritiCS 职责分离，按该 Atom 的 S01–S30 落地。旧 P2 样本仍为 `HISTORIC_SMOKE_SAMPLE`。
- 独立只读 Controller 的工程 ACCEPT 与当前 ChatGPT 的源码/结果审查仍为必经门；在其完成前，不得记录 Atom 终验通过，也不得填 `USER_CREATIVE_ACCEPTED`。

## 用户最新目标与收敛覆盖（2026-10-11）

- 最终目标、有限清单与停止准则见 `plans/CNW_PUBLIC_REPLICATION_GOAL.md`。完整复现固定官方公开方法的输入、职责、步骤、产物、反馈；不把诊断样本修到零 bug，不手改输出冒充效果。
- 用途：保留已定主线和关键情感转折，补符合当前时间人物状态、通过行动/选择/回应塑造人物的日常事件。逐角色处境、已知/未知信息、关系阶段须有来源；缺失留待确认，不挪用后续阶段。
- Controller 按 C01–C15 对官方来源、实际功能和必要真实产物审查；RETURN 须说明实现差异及最小复验范围。兼容身份证据复用，样本随机瑕疵不自动触发全链付费重试。
- 全部方法职责可执行、有限必要证据及独立源码/结果审查完成、无未闭合实现差异、C/T 推送回读后，停止工程整改。创意亲读和所有规模 Live 另列，不以 Offline 冒充 Live，不以文学优化无限延长工程。
- main-only、同一 J19、不生产第二场/批量正文、剩余预算及私有材料保护继续有效；旧计划和历史不删除，冲突的质量门解释以用户最新目标覆盖。

## 用户预算授权覆盖（2026-10-11）

- 用户最新明确指令“取消预算上限”：取消共享campaign金额上限，以配置/账本 `null` 表示无金额上限；上述剩余预算限制及旧CNY10停止条件按此覆盖，旧费用和失败历史保留。
- 继续同一J19的必要验证，复用已付费身份；仍用DeepSeek Flash、记录reserve/send/settle与未知非零费用、保持并发和有界复审，不扩大场数，不手改诊断正文或票。
