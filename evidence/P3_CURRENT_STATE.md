# P3 当前状态

- 当前唯一分支 `main` 已将 P3.1 差异修复和 Controller ACCEPT 正常推送；远端/本地回读一致。用户明确只保留 main，不创建候选分支；不强推、不 reset/clean、不删除既有工作。
- 唯一活动计划：`plans/MASTER_PLAN_P3_1.md`。P3.1 ZIP SHA256=`2550F43B266BFDCAC324F9C24E4DCC7E86B6AA38462B32310A203F54BD6FFDF3`。P3.1 的 W04/W05 差异修复已同一独立 Controller ACCEPT；当前在 W06 纠偏候选审查中。
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
| W07 | IN_PROGRESS | 仅实现和验收 MOCK_ONLY 独立上下文五 Lens、三 Verifier、Completeness；不得冒充 W10 |
| W08–W11 | NOT_STARTED | W10 才允许本轮唯一一场真实模型端到端验收 |
