# CNW 费用记录与金额上限

## 当前通用应用权限

新注册项目不继承历史项目的 Live、Key 或费用授权。合同/来源离线核验、工程 Controller ACCEPT、可信生产签收与用户 Live/费用授权分别核对；预算设置本身不授予模型调用权限。当前通用生产路径仍未授权，本轮只运行隔离的虚构模型输送和确定性工程验证，不调用真实 Provider、不 reserve、不重放请求。

历史请求、费用、限额变更、`PENDING` 和 `UNKNOWN_NOT_ZERO` 按原记录保留。未知费用不能清零、当成零费用或重新计费来通过工程门。真实私有数据切换仍保持 `CUTOVER_BLOCKED=true`。

当前 `tools.p2_cost_guard set-limit` 操作固定的旧共享账本；没有项目/DataHome 选择接口，不能用它为任意通用项目配置独立账本。原配置和费用快照仍有实际消费者，本轮文档整理不修改它们。

## 历史 J19 campaign 取消上限记录

2026-10-11 用户为当时旧 campaign 明确授权“取消预算上限”。`config/production.example.json` 中 `cost_guard.estimated_campaign_limit=null` 表示该共享 campaign 不设金额上限；当时账本通过正式命令记录 10→null 的授权变更。既有有限账本不会因配置值自动改写。

以下保存当时的命令记录，文档验证不执行它：

```powershell
.\runtime\envs\critics-api\Scripts\python.exe -m tools.p2_cost_guard set-limit --unlimited --reason USER_AUTHORIZATION_2026_10_11_CANCEL_BUDGET_CAP
```

该历史操作保留全部请求、费用、未知非零占用及旧限额变更历史。原执行器仍执行 reserve→send→settle、模型限制、并发控制、token/截断检查和重复请求检查。`set-limit --limit-cny <positive-number> --reason <reason>` 是同一旧账本的设置接口；后续实际更改仍须相应用户授权，非法数值拒绝。

这次旧 campaign 授权不扩大历史 J19 的作品/方法验收范围，也不授权新项目生成。历史复审和待修订状态保持原结论。当前施工范围和停止条件以 `plans/MASTER_PLAN_GENERIC_APP_R5.md` 及用户追加条款为准。
