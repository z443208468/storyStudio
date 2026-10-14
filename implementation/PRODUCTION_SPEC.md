# 通用写作生产与交付合同

唯一活动施工计划是 [R5](../plans/MASTER_PLAN_GENERIC_APP_R5.md)。本文描述当前接口和最终验收目标；当期签收以精确C/T、Controller原件、冻结和远端回读为准。原P2单场文档在仓库外原字节备份，不授权任何新项目。

## 用户输入与应用职责

用户提供写作ZIP及明确DataHome。包包含其材料、场景/章节要求、人物/POV、文体、语言、来源选择、目标、创作空间、禁止项和项目第五Lens。应用校验归档/固定来源并封存原字节，建立注册实例、合同、Run及任务依赖；用户无需手抄内部Run ID、合同或SHA。

[包适配](../docs/INPUT_PACK_ADAPTATION.md)说明legacy scene及native V2格式；嵌入执行指令不能改应用方法或授Provider权限。未知/冲突要求保留原位置和类型，不静默删掉、缩小或只选一个任务。不能通过顺手修改原包需求求验收绿。

## 方法与实际生产

CNW pin为 `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`。按 [角色读集](CNW_ROLE_INPUT_OUTPUT.md) 和 [Prompt职责](CNW_PROMPT_CONTRACTS.md)执行全部11阶段，保留双Lint、五Lens独立请求、每Finding三反证与2/3规则、遗漏反馈、另存Refine、新稿受影响复审。Workflow01–05和五话Sprint分别按触发条件/批准计划运行，不替代逐单元生产。

INSERT/ADAPT/ORIGINAL改变合法输入证据，不改变岗位分工。新V2篇幅是ADVISORY：完整保存用户目标，实际事件/遗漏仍验，不按超欠字数增加无关正文或强行重写。传输截断、空产物、token和费用权限仍硬拒绝。旧合同原语义与请求/恢复身份保留。

## 正式入口和恢复

```powershell
.\tools\studio.ps1 project-pack -InputFile '<writing-package.zip>' -DataHome '<absolute DataHome>' -PrepareRuns
.\tools\studio.ps1 project-pack -JobFile '<returned job record>' -DataHome '<same absolute DataHome>' -Mode live -ExecuteJob
```

本节为接口说明，不是此轮真实调用。`-Offline`只选择源取得模式；`-Mode`明确生产意图。PowerShell `studio.ps1 project-pack` 当前没有 `-NewAttempt` 参数；底层 Python `tools/cnw_pack_app.py` 的 `--new-attempt` 仅在 `--execute-job --execution-mode live` 下建立独立 attempt，并保留旧 attempt/账本/失败。生产可信Controller、Owner Live/费用许可、Key与当前请求/预算全部有效才能发送；生产信任未部署时明确拒绝，不落入mock。恢复核实原产物/请求/费用和输入身份，不重放成功或未知请求，不覆盖历史。

## 交付与接受

每个声明任务分别提供可读初稿/修订稿、适用选段/锚连读、修改说明、运行/方法/模拟或Live状态及文件索引。导出只保存候选，不是自动Canon或正式正文晋升。真实审查、作者批准和用户亲读各有单独证据。

最终硬门：实际用户包的全部任务与要求须经过真实CNW生产、审稿/修订、可信Provider回执及分别导出；用户不需手工组织内部阶段。单任务/fixture/Prompt构造/接口接线不能替代全包交付。当前 `INPUT_PACK_TO_STORY_GATE=NOT_COMPLETED`、`GENERIC_LIVE_PRODUCTION=NOT_RUN`；现有旧私有项目迁移/cutover继续阻断。
