# C02 / C08 外部 RETURN 定点修复

2026-10-11。官方基准仍为 CNW `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`。外部源码审查对工程对象 `bcc73679db9d3c270591ae812ec22b85344db571` 返回两项问题，本轮只修这两项；不修改历史私有正文、审稿票或原始响应，不新增生产 API 调用。

## 外部证据限制

用户回传的审查反馈确认：外部可审公开提交源码与提供的v2全文，但尚无法读取私有ZIP并独立核验包SHA256、219笔账本、全部raw及v0→v3消费。它们保持“本机核验 / 外部未核验”，不升级为外部已接受。此前限定Controller工程接受不替代外部审查。本次源码修复也不证明历史导入实际受到模板污染，或历史Lens实际发生重复ID。

## C02 — CONFIRMED 事实来源

官方依据：`templates/_workflows/01_first_import.md`，CONFIRMED 为原稿直接陈述；仅确认事实进入Canon，不发明事实。

修复位置：`tools/cnw_import_workflow.py::_run_import/_confirmed_canon_sources`。

- CONFIRMED 至少绑定一个 `original` 或 `confirmed_canon` 事实来源。public_method、project_instructions、普通project_context不能单独支持。
- 已确认Canon按既有来源支撑的CONFIRMED记录提供专用引用；须仍存在于对应Canon的确认段中。混合Canon文件整体仅为context，TODO、冲突及方法说明不自动晋升为事实源。
- 保留三类确定性与现有导入步骤。薄传输字段 `source_role` 默认story_fact，方法说明显式method_metadata；非Canon方法元数据可由public_method/project_instructions支持CONFIRMED，不能进入90_canon。来源资格说明进入每次请求；未核实引用仍保留为未核实，不能充当事实支持。
- `story_fact_sources` 明示本条实际事实依据，`source_kinds`保留其他引用类型。来源门不保证模型的语义解释正确，也不要求新正文逐字复制原稿。

离线反例/正例：模板单独支持Canon拒绝；项目指令及未确认context拒绝；整个混合Canon拒绝；专用已确认Canon记录成功且不带TODO内容；旧方法-only或已移除确认段不能再支持；方法元数据仍在非Canon日志中保存。

## C08 — 每条 Finding 的独立身份

官方依据：`docs/THREE_LAYER_REVIEW.md` Adversarial Verify，每项真实Finding独立三路反证，至少2/3未反驳才进入修订。

修复位置：`tools/cnw_runner.py::execute_five_lenses/_validate_finding_identities/execute_three_verifiers/execute_completeness/_confirmed_findings/verify_live`。

- 聚合身份改为 `lens_id + 响应内条目序号`，相同Lens的两个F1仍成为两项意见；不同Lens亦互不冲突。
- 保留 `lens_finding_id`、`lens_finding_index`、`lens_provider_request_id`，能对应原始模型标签、位置与响应；不手工修改raw。
- 同一原响应重入产生同一映射。三反证的职责和2/3判定不变。
- 历史materialized索引或反证报告中若仍存在重复/空聚合身份，在下一次反证/Completeness/Refine消费前明确拒绝；verify-live同样检查，不能覆盖裁决或声称通过。历史文件不自动改写。

离线反例：同一Style两条F1和另一个Character F1共三条意见，各有三个独立请求，合计九个mock请求；第二条驳回不会覆盖第一条确认；下游只消费各自真实存活结果。歧义历史索引拒绝且provider未调用。

## 验证及收尾范围

命令：

```powershell
.\runtime\envs\critics-api\Scripts\python.exe -m unittest tests.test_cnw_project_import tests.test_cnw_incremental_entry tests.test_cnw_runner tests.test_cnw_review tests.test_cnw_pipeline tests.test_cnw_recovery tests.test_cnw_operations tests.test_cnw_chapter_arc
```

106项相关离线测试通过（31.116秒）；新添七项定点回归，并纠正一项原先允许模板进入Canon的错误正例。方法说明正例保持CONFIRMED，仅记录在非Canon且显式为method_metadata；日志中的故事断言不能因目录而绕过事实来源门。测试使用mock，不是新Live或模型质量验收。

独立只读Controller对本次C02/C08源码修正限定ACCEPT；精确提交签收、推送与回读随本轮交付核验。外部两项源码RETURN须在推送后重新审查。当前候选仍 `REVISION_REQUIRED`，15项pending；Chapter/Sprint Live仍未跑，整体Atom及用户创意接受未通过。此记录不回溯签收原私有运行包。
