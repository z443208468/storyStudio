# StoryStudio 当前 Codex 执行入口

开始或恢复任务前，先读取 `AGENTS.md`、`docs/governance/GOVERNANCE.md` 与唯一活动计划 `plans/MASTER_PLAN_GENERIC_APP_R5.md`（原批准源 SHA256 `5CC22861CE3C0603D6EF89619594CD7CD68642241A20036032B031CB3A8C8ECF`；当前补充版 SHA256 `757F8D7CF7458697B5CC97AA4764583512AAB45E9CC04F78B3B7703E8F5BF773`），然后读取该 Atom 指定的来源、实现和验收材料。只做当前 Atom 授权的工作。

当前目标是把 StoryStudio 建成能隔离承载多类写作要求的通用应用，并保留 CNW 原始方法及其读集、审稿、Canon 和 Sprint 职责。J19/Cangqi、P2、P3、P3.1 内容均为历史，不是默认项目或当前生产任务。

Writer 在唯一 `main` 上实现并按 R5 先形成当前 Atom 的本地候选提交 C/T（不推送）；独立只读 Controller 审查该精确提交/树。仅 ACCEPT 后按计划推送并核对远端。Controller 不可用时停止而不自签。保留所有旧入口、WIP、私有数据、费用记录和历史，直至明确门禁。通用化阶段不调用生产 API，不生成正文。`README.md` 介绍应用；本文件只作为执行入口。
