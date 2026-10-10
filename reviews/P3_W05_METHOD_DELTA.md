# P3 W05 方法到代码增量记录

## 调度与持久化

| CNW / P3 职责 | 实现 | 本阶段证明 | 未证明 |
|---|---|---|---|
| 工作流步骤调度 | `tools/cnw_runner.py`；对应固定 `workflow.template.yml` 的 plot/cards/brief/draft、两层 lint、5 Lens、3 Verifier、completeness、refine、re-review；保留 POV、promote/export、resume、sprint 调度名 | Alias 与 pinned template 对照；阶段按顺序、依赖未接受即阻断 | 尚未实现真实模型 stage executor、Lens/Verifier、晋升和阅读导出 |
| 新 ID 与私有 run | `produce --mode offline --unit --contract --work-id --run-id`；`runs/<id>/run_state.json` 与 `artifacts/` | 两个 fixture work ID 创建隔离 run；实际《苍歧》冻结合同通过 source manifest、脚本及前后锚校验并创建新的离线 run | 未生成《苍歧》新正文；无供应商调用 |
| 依赖与缓存身份 | contract SHA、固定工作流 SHA、每岗 Prompt SHA、前序产物 SHA、provider config SHA、既有 `p2_cost_guard.py` SHA；内容变更时仅失效受影响 stage 与后继，旧 artifacts 留存 | Prompt 局部变更、同 Work ID 合同变更、run-ID 重名和 `..` 负例；相同 fingerprint 的 READY 请求复用 | Provider 请求的真实 retry/reserve/settle 尚未由新 run 执行；仍必须复用旧 `p2_cost_guard.py` |
| 历史与真实调用判断 | `verify-history` 与 `verify-live` 分开；`resume` 只读/恢复；旧 `scene` 显示 `LEGACY_CHECKPOINT_ONLY` | 新离线 run 的历史哈希通过；无 provider receipt 时 `verify-live` 返回 `LIVE_PROVIDER_EVIDENCE_MISSING`；旧 EP001 checkpoint 清楚标为 legacy | 不能用离线 fixture 或旧请求当成本轮新 live 调用 |
| PowerShell 入口 | `tools/studio.ps1` 新增 produce/step/review/promote/show-run/verify-history/verify-live/sprint；export 区分历史 EP001 与指定 run | 语法解析、`doctor`、`legacy-scene`、run create/step/show/history 经 PowerShell 实跑 | Review 的 Controller receipt、promote/export 正文写入及五话 Sprint 仍是 gate/占位状态 |

## 实际离线证据

- `tests.test_cnw_contract`, `tests.test_cnw_adapters`, `tests.test_cnw_runner`：23 项通过；覆盖合同/来源、不同 fixture run ID、角色调度请求、Prompt/合同/workflow 缓存失效、阶段顺序、历史与 live 区分、路径与重复 ID 拒绝、run 内输入 symlink/绝对路径拒绝、同 run 并发写入串行化、既有 NK/CritiCS adapters。
- `py_compile`、`git diff --check` 和 `studio.ps1` PowerShell Parser 均通过；`studio.ps1 doctor` 返回 workspace/private source/Python 均可用，唯一活动分支为 `main`。
- 实际 run `P3-W05-CQ-J19-OFFLINE-20261010` 绑定冻结合同 SHA256 `e5ef4ce8d4468756021b8b7a8e10dd3cff0b9445e25a6a399f3cc683bb0978d0`。Plot 请求首次为 `READY_FOR_EXECUTION`，同 fingerprint 再执行为 `STAGE_REUSED`；`verify-history` 为 `HISTORICAL_EVIDENCE_FOUND`；provider request 数为 0。
- 实际 `verify-live` 在没有 provider receipt 时退出失败，错误为 `LIVE_PROVIDER_EVIDENCE_MISSING`。没有读取或发起新 API 请求；费用账本未由 runner 改写。
- 所有 run 与产物位于 Git ignored `runs/`；只提交调度器、入口与脱敏测试/验收记录。

## 结论边界

W05 候选提供可恢复、来源与内容 hash 绑定的离线 run 状态机和入口骨架。它不等于完整 CNW 生产链或可交付新正文；模型执行、真实 `reserve/settle`、五 Lens、三 Verifier、Completeness、Refine、Re-review、Promote、动态 Export 与 Sprint 仍需后续 Atom 实作和验证。W05 `--mode live` 明确 fail closed，不能提前绕过 W10 准入。
