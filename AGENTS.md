# StoryStudio 执行入口 P3

本文件是当前执行规则，不是成果已通过声明。唯一活动计划为 `plans/MASTER_PLAN_P3.md`；当前阶段与验收凭据见 `evidence/P3_CURRENT_STATE.md` 和 `reviews/P2_ACCEPTANCE_LOG.md`（其中续记 P3 W00/W01）。P2 计划及签收保留为历史记录；其中 P2-06/07 的 ACCEPT 不代表 CNW 全流程或文学成品已完成。

## 目标

完成 CNW 固定公开方法映射到 StoryStudio 的可重复生产流水线，按 W00–W11 推进。当前只重做同一场 J19 插场，不扩写第二场；最终交付可运行入口和可读成果。NK 与 CritiCS 的已验证能力作为历史前置复用，CNW 全生产状态目前未验证。

## 执行角色

Writer 负责改代码、运行必要验证、调用已授权的生产 API、提交和推送。独立只读验收子智能体是 Controller：逐阶段审原作者来源、当前实现、真实证据和候选 C/T，给出 ACCEPT/RETURN 并指出最小修正。Writer 不得自签。Controller 的工程 ACCEPT 不等于用户创意接受。

## 约束

- 先读 `reviews/P3_CODEX_START.md`、`reviews/P3_CONTROLLER.md`、P3 全计划和相关实现合同，再按阶段依赖推进。
- 修复当前阶段可自行处理的机械问题；只扩大处理实际影响安全或功能的缺陷。已验证事项按身份复用，不重复证明。
- 保留 CNW 的 Plot → Scene Cards → Writing Brief → Prose → 三层审稿、五 Lens、三 Verifier、Completeness、Refine、Re-review；NK/CritiCS 各按自身职责接入，不能相互冒充。
- 不得以旧 EP001/checkpoint、合规短稿或历史 ACCEPT 声称新生产线完成；旧 P2 样本标为 `HISTORIC_SMOKE_SAMPLE`。
- 用户亲读前不得记录 `USER_CREATIVE_ACCEPTED`。不生产第二场或批量正文。
- 仅使用已授权 DeepSeek Flash 与剩余预算，复用既有成本护栏；密钥和私有稿件不得进入 Git。
- 当前分支只有 `main`。沿 main 正常提交并推送，每阶段 Controller ACCEPT 后核对远端回读；不创建分支、不强推、不 reset/clean。
