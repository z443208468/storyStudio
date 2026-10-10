# CNW 费用记录与金额上限

2026-10-11用户明确授权“取消预算上限”。`config/production.example.json` 中 `cost_guard.estimated_campaign_limit=null` 表示不设共享campaign金额上限。既有有限账本不会被配置自动改写；当前账本经正式命令记录10→null的授权变更。

```powershell
.\runtime\envs\critics-api\Scripts\python.exe -m tools.p2_cost_guard set-limit --unlimited --reason USER_AUTHORIZATION_2026_10_11_CANCEL_BUDGET_CAP
```

该操作保留全部请求、费用、未知非零占用及旧限额变更历史。仍执行reserve→send→settle、模型限制、并发控制、token/截断检查和重复请求检查；没有用巨大金额假装无限额。`set-limit --limit-cny <positive-number> --reason <reason>` 可按后续明确授权恢复有限模式，非法数值拒绝。

取消金额上限不改变 `plans/CNW_PUBLIC_REPLICATION_GOAL.md` 的有限功能清单与停止条件。同一J19的完整复审证据和后续有界处置可证明方法职责；候选仍待修订时如实保留，不重开调用追求CLEAN，不以费用授权增加场数。
