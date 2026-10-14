# ATOM07 精确裁决：RETURN

**审查对象**

- Commit：`f8c72d59b070a3544047189de0fb31f3b138e6df`
- Tree：`ee325b8429aadc8f68e3d6091204dc4e9f997765`
- 父提交及独立远端回读：`84e022de0fee6eb7d7eec4c248703621129491e1`
- 适用活动计划 SHA256：`408864DEFBE39C7CCD6A113C53614378688B18FD2EB48AC0A58ED6D246B6A247`

本裁决依据上述 Git 对象，**不包含 Writer 此后未提交的修复**。本轮只读，未运行测试、修改文件、读取凭证或调用 Provider。

## 裁决结果

| 项目 | 裁决 |
|---|---|
| `CODE_FIX_VERDICT` | **RETURN** |
| `METHOD_FIDELITY_VERDICT` | **RETURN_CURRENT_FULL_SCOPE** |
| `FROZEN_FUNCTION_REGRESSION_VERDICT` | **RETURN**：存在已冻结授权边界退化 |
| `ATOM07_STATUS` | **当期离线工程门尚未完整闭合**；已有组件证据保留 |
| `GIT_GOVERNANCE_VERDICT` | 精确对象、父链与远端身份核对成立；未获得本候选接受 |
| `GIT_PUSH_AUTHORIZATION` | **NO**，不得推送此 C/T |
| `NEXT_ATOM_PERMISSION` | **WITHHELD**，不得进入 ATOM08 |

确认的阻断根因共两项；未确认第三项独立代码阻断。

## RETURN 根因一：旧 revision_apply 无许可路线重新开放

定位：

- [cnw_runner.py](D:/CangqiStudio/StoryStudio/tools/cnw_runner.py:722)，候选对象第 729–735 行；
- 同文件第 509–510 行、第 594 行附近、第 787 行。

候选删除了冻结父提交中的高、低入口 `project_revision_apply` 提前拒绝。现在物理 operation owner 先被识别；对于合法旧 `workspace/.../94_runtime/maintenance/<run>`，注册识别返回 `None`，操作授权函数也返回 `None`，随后提前返回，绕过后面的 revision_apply 拒绝。低入口又新增允许该 stage。

因此，没有新生产许可的旧路线可以到达共享槽位、Key、费用及 HTTP 后续边界。创意批准不能授予这些权限。这是相对于已接受 ATOM06 的真实退化。

**最小修复及复验**

仅允许已验证 `SIGNED_OPERATION_LIVE` 或原有合法 owned simulation 执行 revision_apply；旧路线返回 `None` 必须保持关闭。使用真实临时 V1 operation Run，分别调用 high/low，证明在 Key、slot、reserve、HTTP 前拒绝。同时保留注册签名操作正例、创意批准伪造负例和其他 V1 操作兼容。

## RETURN 根因二：V2 合法辅助调用无法获得费用授权

定位：

- [cnw_live_authorization.py](D:/CangqiStudio/StoryStudio/tools/cnw_live_authorization.py:30)：许可 stage 集合；
- [cost_guard.py](D:/CangqiStudio/StoryStudio/tools/cost_guard.py:237)：按账户 stage 再验许可；
- Runner 第 1600–1624 行：NK 使用 `support_hook` 账户；
- Runner 第 2422–2437 行：CritiCS 使用 `critics_plot`／`critics_text` 账户。

这些辅助账户身份不在合法许可集合内。即使独立部署、合法双签和运行依赖全部具备，实际 reserve 仍会拒绝。因此，纯 NK 回执绑定、缓存消费或 `ENABLED_BUT_UNAVAILABLE` 负例不能证明合法 V2 辅助输送已经接通。

**最小关联规则**

| 辅助调用 | CNW 父执行阶段 | 必须绑定的实际输入 |
|---|---|---|
| NK `support_hook` | `writing_brief` | 当前 Cards、真实 NK payload、角色及请求身份 |
| CritiCS `critics_plot` | `plot` | 本次实际 Plot 产物与 `plan-critique` action |
| CritiCS `critics_text` | `refine` | 当前 Prose 的可定位摘句、Finding／Completeness 上下文与 `text-refine` action |

当前 text hook 在 `execute_refine()` 中调用，却向预检传 `prose`。应区分“输入来自 Prose”和“调用归属于 Refine”，不能用 Prose 许可释放 Refine 辅助调用。

可以保留现有辅助费用 stage，但须在既有签名、真实请求和费用适配器内明确验证上述父阶段与 hook/action；不能仅扩大字符串白名单。

**必要复验**

真实注册 V2 Run、真实签名消费、共享 slot／ledger／reserve／settle，末端模拟：

- NK 新结果与缓存实际进入 Brief；
- CritiCS Plot、Text 实际进入原消费者，含 pending 回读与缓存；
- 错父 Run、父阶段、action、材料 SHA、payload、角色、额度及 token 拒绝；
- 多辅助调用累计费用、UNKNOWN 保留、续签不重置；
- 真实 V1 路线保持原行为；
- 模拟结果始终不能通过 `verify_live`。

## 证据与冻结范围

已核候选全部变更路径清单、相关实际源码差异及原始记录身份；四份主要 manifest 的 Git 字节索引分别核对 **13、73、6、56** 项，无哈希差异。固定 CNW `97ad71…`、旧参考 `26b72cea…/535496…` 身份和干净状态已回读。

章节、签名操作、ADVISORY、NK 绑定及 W10 scoped 证据均保留其实际范围。最后 W10 **4 passed／18 subtests** 不能扩成完整 W10 通过；bounded stop、历史失败和早期 11 阶段模拟回归不能写成 Live PASS。

冻结 00–06 的原接受不撤销。但本候选根因一违反其保护要求；根因二尚缺合法辅助路径。返修还须针对改变的共享授权／builder 对既有 package attempt、旧合同与 Run／导出保留、模拟及跨 attempt 前章拒绝作必要回归，未变模块可按精确身份复用原证据。

## 后续边界

Writer 仅处理上述两个根及必要回归，形成新 C/T 后再审当前 ATOM07 全门。历史 RETURN、失败日志和冻结接受保持原判；此候选不得追认。

所有者计划内必要付费验收授权已经存在，但当前 RETURN 不释放生产调用。可信部署、真实 Live 成功、合法 Live 前章和**实际用户包全部声明任务的真实生产／审查／分别导出**仍未完成。TS 恢复、迁移与 cutover 未解锁，`CUTOVER_BLOCKED=true`。
