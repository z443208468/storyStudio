# ATOM-06 RETURN 修复记录 — 2026-10-12

**状态：** Writer 定点修复候选，待独立只读 Controller 对精确 C/T 复核；本文不是 ACCEPT。

**审查基线：** 用户提供的远端 `main` 审查 `67b845d59f8712f9f73a7454e299da21dff592fd`。
权威计划 `plans/MASTER_PLAN_GENERIC_APP_R5.md` SHA-256：
`5CC22861CE3C0603D6EF89619594CD7CD68642241A20036032B031CB3A8C8ECF`。

## 定点变更

1. v2 工作单元草稿现在必须明确给出第五 Lens 的项目配置 ID 和职责。合同冻结 `review.fifth_lens.id`、`responsibility` 与职责 UTF-8 字节的 `responsibility_sha256`。运行器构造审稿来源时验证 SHA；只有 `story_specific` 消费该项目职责及 ID，且二者进入其输入与消息身份。固定五 Lens 方法和其他 Lens 读取集不变。
2. CritiCS 为 `ENABLED` 时，运行时缺失、子进程异常/超时和非零退出均先记录带动作、输入哈希及输入快照的失败 hook，再抛出 `ContractError` 阻断 Plot/Refine 调用链。`DISABLED` 路径保持原样。没有发起付费或生产 API 调用。
3. V1 合同不再从旧 `unit.language` 推断首个 Prose 请求语言；首个请求系统消息恢复到 Atom-06 前构造器在 `659a1bd` 的精确内容（不添加 locale 指令或尾换行）。V1 续写和 Refine 仍按既有中文兼容行为。V2 locale 指令不变。

## 离线验证

- `python -m pytest tests/test_cnw_atom06.py -q`：15 passed，5 subtests passed。
- `python -m pytest tests/test_cnw_work_intent_v2.py tests/test_cnw_project_import.py -q`：20 passed，7 subtests passed。
- `python -m pytest tests/test_cnw_export.py::ExportTests::test_anchor_free_adapt_export_uses_selected_source_excerpt -q`：1 passed。
- `python -m pytest tests/test_cnw_runner.py::RunnerTests::test_native_critics_result_reaches_refine_and_is_verified_on_reuse -q`：1 passed。
- 曾运行包含整个 `tests/test_cnw_export.py` 的探索性组合；其中 4 个既有导出 fixture 的旧合同缺少当前导出器要求的 `unit.language_locale`，因此未通过。新增适配导出 fixture 的定点用例单独通过；上述问题不在本修复改动路径内。

原始合成请求/响应轨迹：`evidence/ATOM06_RETURN_REPAIR_TRACE_20261012.json`，SHA-256
`30a1dd752998b387004083e97984760b33a7ac406b292f855f64722b3e47f8c7`。
轨迹标记 `SYNTHETIC_OFFLINE_ONLY`，只含合成项目标记及注入的离线模拟响应，不含项目私稿或生产请求。

## 边界

未读取 W10 私有文件或现有项目/运行数据；未迁移数据或切换活动指针；未重写历史；未执行生产模型请求。六个 W10 未跟踪文件仍被排除在候选外。Atom-05 的 `CUTOVER_BLOCKED` 保持。

Controller 待核：精确候选 C/T；用户指出的 M05、M07、M14、M16 影响面；五 Lens 来源隔离及合同 SHA 消费；CritiCS ENABLED/DISABLED 失败边界；V1 首次/续写/Refine 请求身份；CNW 上游方法和历史保护边界。
