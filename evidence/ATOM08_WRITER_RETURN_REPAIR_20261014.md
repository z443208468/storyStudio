# ATOM08 Writer 修复记录（Controller RETURN 后）

本记录回应 `ATOM08_CONTROLLER_INVENTORY_20261014.md` 的精确候选 `136df64de8105d237cee023c530eed5e61ca964a` / Tree `397f21db6c5ba4cc74726a3853b5dad6a80d18e3` 的整体 `RETURN`。原始 Controller 报告和裁决未修改。所有四项均在 ATOM08 范围内定点修复；本记录不构成 ACCEPT。

## 集中修复

1. 三份文档不再把不存在的 PowerShell `-NewAttempt` 当作正式参数。明确 `studio.ps1 project-pack` 没有该开关；只有底层 `tools/cnw_pack_app.py --new-attempt`，且须与 `--execute-job --execution-mode live` 同用。
2. README 如实说明项目绑定的费用上下文仍写入应用根 `runtime/private/p2-cost-ledger.json` 共同账本；物理账本迁移与 cutover 未发生。
3. 将 Atom06、Atom07 原始 ACCEPT 与冻结/回读记录列入后继 Git 树，修复 README 冷克隆链接失效，不改写原裁决。
4. 将 `plans/ATOM_CNW_PUBLIC_1TO1_RESTORE.md` 替换为同路径停用索引；原完整文本留在外部归档，当前 C01–C15 与 R5 M01–M16 保留公开方法映射。对十份旧 P2/P3 顶层证据逐项分类，备份原始工作树字节和精确 Git blob 字节后，在原路径放置非执行指针。静态消费者搜索没有找到活动应用、测试、配置或当前 R5 文档的引用；遗留的旧计划自引用位于已停用历史内容中。四份当前 R5 `source_bytes` 证据原位保留。

## 原始证据保护

旧计划和十份证据共 11 项已双份封存：

- ZIP：`D:\CangqiStudio\StoryStudio_R5_Atom08_20261014\atom08_legacy_evidence_and_plan_sources_b93d009.zip`
- ZIP SHA-256：`005e11b1826a7e1d938723070c7a2c27aa650bd6ab2fbe728032b72fe9acc9a1`
- 清单 SHA-256：`6f77c0e0d7c1b75c899f407fe2f603bd6901a13bcd20992548f34ea165c3c5dd`
- 候选映射：`evidence/ATOM08_TOPLEVEL_HISTORY_ARCHIVE_MAP_20261014.json`
- 原始 193 文件来源映射的物理 SHA-256 为 `543946cfd2b49ba66353f97324e5e45bf7c092405c96af89aa7c16780e898f70`；Git 规范化 blob 内容 SHA-256 为 `75cd0f9a0edc14b0eb7bd576a43a1626282700a50f407903042daa9faf7044e5`。

Git 历史没有重写。本次只整理当前 HEAD 中的历史入口；不声称旧 Git 对象已擦除。

## 修复后验证

- 相关导出、活动文档、真实 Live 导出拒绝和错实现签名负例：13 项通过，退出码 0。此次工作树完整复测 `13 passed in 17.69s`；原始记录 `atom08_export_regression_after_return_20261014.txt`，SHA-256 `ced94784aeb85cbc01b841940e71a6830b5188971056162488ca995d0c22e0f4`。代码和测试 SHA 记在该记录中。
- 修改文档本地链接复核：11 份文档、25 个本地链接、0 缺失；原始报告 SHA-256 `803ffb32a665bb46805af97598265b302b7b94f71464752794b0b374081de210`。不验证外链、锚点或命令语义。
- 活动工具/测试/配置/current-R5 文档对十个历史证据文件名的消费者搜索：`ACTIVE_CONSUMER_SEARCH=NO_MATCH`。旧计划自身提及 P3 状态路径，但该计划现有醒目标记为非活动历史资料。
- 已复核代码/bootstrap 输入没有改变；冷克隆的固定上游离线 bootstrap 在前一候选完成。新候选仍需按精确 C/T 冷克隆复核链接与工作树清洁度。
- 活动 R5 计划、冻结基线、TS run_state 和费用账本未更改；没有 Provider 请求、迁移或历史 Run 恢复。

精确后继 C/T 与其 Controller 裁决另行记录。提交和推送均等待该裁决；Atom09 未开始。
