# P3 当前状态

- P3.1 纠偏基线：本地/远端唯一分支 `main`，C=`9464165c69825aaa01fefee83f019dd69b52e877`，T=`6eb7cd167ae159608375b28ba5815a4bfa7c79ff`；审查时远端 main 与本地一致。用户此前明确要求只保留 main、不创建分支，因此按用户指令覆盖 P3.1 包内候选分支建议；不强推、不 reset/clean、不删除既有工作。
- 唯一活动计划：`plans/MASTER_PLAN_P3_1.md`。P3.1 ZIP SHA256=`2550F43B266BFDCAC324F9C24E4DCC7E86B6AA38462B32310A203F54BD6FFDF3`。当前阶段：P3.1 对已验收 W04/W05 的差量补齐，等待同一独立 Controller 补验；在补验前不进入 W06 正式签收。
- P3 工单包 SHA256：`E3D4E10B7C876A2F4F53B0BFC5560BB24419F975D4A88445FAED993A66BE3CAD`。CNW pin：`97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`；本地捕获 manifest SHA256：`E9B989C52C66AB9BE8C73F09E84BC5BD7D2ECC92F9F1CBFC61BA300DC6CD3983`，98 项。
- 状态：`ENV_READY=ACCEPTED`; `NK_LIVE=ACCEPTED`; `CRITICS_LIVE=ACCEPTED`; `CNW_FULL_PRODUCTION=NOT_VERIFIED`; `PRODUCT_MILESTONE_REOPENED=YES`; `USER_CREATIVE_ACCEPTED=PENDING_USER_READING`。
- W00 `ACCEPTED` 并已推送；W01 `ACCEPTED` 并已推送。详细 Controller 消息、精确候选 C/T 及远端回读见 `reviews/P2_ACCEPTANCE_LOG.md` 中追加的 P3 W00/W01/W04 记录。
- P2 的旧 EP001 与 `0b40876b` 历史签收标记为 `HISTORIC_SMOKE_SAMPLE`。这保留工程签收事实，但不作为 P3 正文质量或 CNW 全流程证据。
- P3 第一轮只重做同一场《苍歧》J19 插场；不写第二场，不批量生成。W10 之前不进行本轮真实作品生成。
- API 费用：P3 至今无新增调用；仅沿用已批准剩余预算和既有 `p2_cost_guard`。
- P3.1 独立 Controller 差异结论：W00–W03 可复用原签收作为历史；W04 未实现新项目原始导入，W05 仍固定《苍歧》根路径且缺外部编辑签收状态门。Controller 未签 W06。
- 当前私有工作区有 P3.1 导入/数据链修复候选；两份 fixture（Markdown 与 JSON）离线验证未产生 provider 调用。全部 `TODO_CONFIRM` Canon 候选仍需人工确认，不代表真实创作或新项目 Canon 已验收。
- W07 使用 `MOCK_ONLY` 的离线验收与 W10 真实 DeepSeek 调用验收严格分开；当前无新增真实模型调用。现有 live 校验器正在补强 receipt/usage/hash/费用结算核对，不得以模拟记录冒充 W10。

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
| P3.1 W04 delta | IN_PROGRESS | 新剧本原始导入、Canon 候选、source-bound 合同及角色输入贯通；候选待独立 Controller 补验 |
| P3.1 W05 delta | IN_PROGRESS | 项目根路径与通用 runner 接通；CLI 候选状态为 `READY_FOR_EDITORIAL_REVIEW`，缺外部审阅证据不能 promote |
| W06 | NOT_SIGNED | W06 候选文件保留；正式签收须等 W04/W05 P3.1 补验 ACCEPT |
| W07–W11 | NOT_STARTED | W07 仅 MOCK_ONLY；W10 才允许本轮唯一一场真实模型端到端验收 |
