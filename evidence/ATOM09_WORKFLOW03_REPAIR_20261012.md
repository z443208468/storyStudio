# ATOM-09 Workflow 03 定点修复施工证据

本记录是 Writer 的候选前施工快照，不是 Controller ACCEPT。活动计划保持 R5 原字节；不进入 Atom-10，不调用 Provider，不迁移私有数据。

## 真实退回与修复范围

独立 Controller `/root/atom09_final_controller` 对候选 `32bca249a815448f47be7662a80eb1a85f8e121f` / Tree `1ac9877d63cff8aa059ee39c6005e48ede506ff5` 的原始结论：`CODE_FIX_VERDICT=ACCEPT_LIMITED`、`METHOD_FIDELITY_VERDICT=LIMITED_PASS`、`ATOM09_STATUS=RETURN`、`GIT_PUSH_AUTHORIZATION=NOT_AUTHORIZED`。根因是 §09.2a(4)/C11 的普通 Workflow03 只执行未批准的计划分支，CNW Refine/promote 单测不能代替用户批准后修订另存的消费者。该历史裁决保留，不追认为通过。

本次沿现有 standard-operation/maintenance 添加 `revision_apply`：

- 用户显式选择 project-local author_decisions JSON，绑定项目实例、计划字节 SHA、所选原章 SHA、主题/Logline/Canon 文件清单与 SHA、具体批准项；模型响应不能授予批准、生产或晋升权限。
- 在请求快照读取后再次核对批准绑定；覆盖“批准核验通过后、inventory读取前”的原章/计划/保护资料/批准文件/实例身份变更。缺项、错配、重复条目或未批准状态在请求前拒绝。
- 仅接受精确目标章稿副本，保存于 `09_revision/approved/<approval-sha>/`；保存批准快照、original/revision SHA、实际 diff 和工作日志，原章与 Canon 不修改、不自动晋升。涉及核心的 `REQUIRES AUTHOR DECISION` 不由普通修订入口执行。
- 正常执行维护事务；真实文件 replace 边界中断后，复用原模拟回执恢复；重复执行不重新调用模型，不覆盖已有候选。
- 独立只读接口反馈发现 Author 批准不能授予 Provider 权限。原生 `cnw_live_call` 在 state/费用 guard/slot 前拒绝该新路径，只有测试传输边界注入确定性回复。新接口仍 `LIVE_NOT_RUN`，生产授权接入不冒称完成。
- M11 另发现内部 `_INBOX/revisions/` 被扫描成 original_sources 的真实根因。排除整个保留注册表命名空间及两个活动指针，保留实际 originals 与普通用户材料；元数据引用不能作为 CONFIRMED story_fact 来源，旧元数据派生的 Canon 来源链不能重新取得事实权限。旧文件与旧 claim 记录不改写。

## 已执行验证

原始命令、退出码、源码 SHA、请求/raw/落盘产物及字节 SHA 保存在仓库外 `StoryStudio_R5_Atom09_Repair_20261012_67e7a76/`。全部 Provider 模拟记录标 `MOCK_ONLY / SIMULATED`；仅测试传输边界注入内容，阶段和公开工作流执行函数真实运行。

| 记录 | 命令范围 | 实际结果 | 原始输出 SHA256 |
|---|---|---|---|
| `workflow03_full_offline_suite` | `python -m pytest tests -q` | 中间源码 304 passed、82 subtests，exit 0；**后续又修复快照时间差及 M11，不能冒称此记录覆盖最终候选** | `7b2286ba76136f413f06d00cc44cf8e1d5c5e308d2d4bc956baf79d468c8dc62` |
| `workflow03_snapshot_binding_retest` | 三个 Workflow03 消费者/负例、operations、maintenance | 24 passed、37 subtests，exit 0 | `e01fd09856555e2c2b7bb60d1ebea6047efb5b2e43b60193d981a3d7cdba7988` |
| `final_workflow_repair_scoped` | 五个 Workflow01/02/03 消费者及 operations、maintenance、project_import、incremental_entry | 50 passed、42 subtests，exit 0；检查期间源码不变 | `51c2472c7383689198756fc8e446f8e00d3c3a8fed0237b1774cd83ad8b8426a` |

此前测试注入 MagicMock 时影响 `inspect.getsource` 的失败，以及非法来源在更早 schema 门被拒绝的测试构造错误，原始失败输出均保留；修复测试注入方式/反例材料后复验，不删保护断言、不放宽消费门。

`py_compile`、PowerShell Parser 和 `git diff --check` 实际退出码为 0。最终精确候选还须在干净克隆中跑完整离线套件，重新核查请求及产物 hash，并由独立 Controller 检查 C/T。此前 32bca24 的干净克隆结果不能代替新候选验证。

## 历史保护与治理边界

真实费用账本 SHA 保持 `c8b0705f491ef824db01be0b7991f4db9db7d84e153c26481e93a4fdcd0eab9b`；真实 TS 状态 SHA 保持 `3bae0722506641f1c14840d2f2568f03484cd6b1298c972baf3700d0de42ee0d`。冻结旧版 HEAD=`26b72cea21dce45eede21cffddd4e75307d75652`、Tree=`535496ba3b8a331e12d0e5e161b15bf21a25393e`、状态为空。仅记录脱敏 hash，不提交私有数据、原始历史回执或账本。

`ATOM07=OFFLINE_ENGINE_ACCEPT_LIMITED`；可信 W10 生产签收仍待定，真实 TS Live/恢复未授权，`CUTOVER_BLOCKED=true`、`PRIVATE_MIGRATION=NOT_RUN`。已有 RETURN 与用户曾直接要求推送的历史事实均保留。本候选最终验收及推送授权必须来自独立 Controller 的精确原始裁决；Writer 不代签。
