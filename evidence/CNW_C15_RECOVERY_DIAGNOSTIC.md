# C15 恢复与参考资料重开：有限工程验证

日期：2026-10-11。方法源固定 CNW `97ad71fe5e5e`；施工范围为 `CNW_REMAINING_SCOPE_20261011.md` 第 1 组。没有生产第二场，没有付费请求，没有改诊断正文。完整 C15/同一 J19 终验仍未闭合。

## 修复与来源

官方 `templates/CLAUDE.md` 的 Always log work、生产手册状态/索引、四岗位及 Lens 阅读职责映射到正式恢复入口。原作者没有规定本地缓存算法。`tools/cnw_recovery.py` 核 actual consumption，`cnw_runner.py` 的 produce/live step/resume 共用；studio 正式路由到项目 run。

- resume 由仅显示状态改为验证后继续；缺旧执行身份不得仅按 MATERIALIZED 跳过。
- actual messages、实际 builder、固定完整模板、相关来源/上游内容纳入身份；Prose 范围未扩大。
- 原稿、manifest、原合同/副本改变拒绝；合法参考变更显式记录原因/旧新哈希。
- 直接消费者先重开，输出内容改变后再传播；无关职责保留，相同请求核 raw 后复用。
- 阶段旧字节及索引内部文件归档；历史回执从当前覆盖移出但仍可精确缓存。篡改停止，不自动再付费“修好”。

## 验证方式

`tests/test_cnw_recovery.py` 使用临时虚构项目、真实普通阶段 dispatcher、实际四岗位 builder 和固定模板，实际读写项目/产物。仅模型 transport、NK 与 CritiCS 支持用明确 MOCK；外层 resume/execute/普通 stage 没有 mock。网络和新 reserve 禁止。此证据不冒称 Live 小说产出。

12 个测试覆盖：全阶段恢复/相同输入复用；Style 显式重开、Plot 保留、同字节下游复用；Brief 改变传播；实际 builder 变而独立 prompt 不变；产物/raw 篡改拒绝；原稿/manifest/合同拒绝重冻；成功 transport 后中断恢复；显式 invalidate 的字节归档与真实 transport 精确历史缓存；step 防越过已变上游；某 Lens 反馈只影响相关请求并归档内文件；完成状态必须有 artifact、export renderer 变化不影响生成身份；新 Plot/新 excerpt 已落盘但旧成功 CritiCS hook 仍在的恢复反例。

最终命令：

```powershell
.\runtime\envs\critics-api\Scripts\python.exe -m unittest tests.test_cnw_recovery tests.test_cnw_role_inputs tests.test_cnw_maintenance tests.test_cnw_pipeline -q
.\runtime\envs\critics-api\Scripts\python.exe -m unittest tests.test_cnw_runner -q
```

PowerShell `studio.ps1` AST 解析通过；最终恢复/岗位/维护/编排合计 43 项、runner 22 项、generation/adapters/import 42 项，均通过（共 107 项）。第一次 runner 合跑曾出现既有并行临时账本 `os.replace` WinError 5；runner 独立复跑 22 项通过，没有将此偶发问题记录为已修复。

本轮账本保守 committed 仍为 CNY `4.615061 / 10`（含已有 UNKNOWN_NOT_ZERO 预留）。没有追加预算或新增结算；不是实际发票总额。

## 收敛限制

Controller 初审限定 ACCEPT 后，在新增支持核验复核中 RETURN：旧成功 CritiCS 回执不能绑定新 Plot/新 excerpt。最小修复为成功支持绑定实际输入的不可变快照/哈希，核验历史输入与当前消费适用性分别判断；旧 hook 保留 support_hook_attempts。新增受控反例验证旧输入核验成功，篡改快照拒绝。Controller 对该 RETURN 修复给最终限定 ACCEPT；最终 43 项随后完成并通过。提交精确 C/T 仍由独立 Controller 复核，不由 Writer 自签。

多轮 Refine/Re-review 中断、最终同 J19 真实身份组合和导出仍依 C10/C14 及第 6 组验证。既有付费证据按兼容身份复用；未触发的条件分支不用付费制造问题。`PUBLIC_METHOD_EQUIVALENCE_VERIFIED=NO`，`USER_CREATIVE_ACCEPTED=PENDING_USER_READING`。
