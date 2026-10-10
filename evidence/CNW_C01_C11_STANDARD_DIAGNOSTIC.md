# C01/C11 标准操作与普通计划有限验证

日期：2026-10-11；固定来源及输入/产物见 `docs/CNW_STANDARD_OPERATIONS.md`。`cnw_operations.py` 承担五种触发操作，`cnw_project.py`/PowerShell 正式转发，复用维护执行器；没有改变 11 阶段顺序。

## 真实代表

沿用私有虚构项目 `workspace/FICT_CNW_MAINTENANCE_20261011`，静态补充源和 beta fixture 明确标注诊断，不是新模型小说。

| 操作 | Private run | Provider ID | Usage input/output | 估算 CNY |
|---|---|---|---|---|
| Canon Extraction | `9963a4f98871b7484a645d18` | `0cc6de81-71ce-4ffa-8d39-130893c52a09` | 16775 / 4141 | 0.067012 |
| Generic Revision Plan | `54f1abeb104afc1a3e6f9434` | `5dea71d5-a0bd-4323-bb48-3b0e09d546ee` | 21277 / 4537 | 0.079245 |

均正常 `deepseek-flash / stop / SETTLED`，合计 0.146257；保守 campaign 占用 4.761318 / 10 CNY，包括历史未知预留，不等于确认实收。

- 提取实际写 `90_canon/extraction_ch02_actor_vs_player_knowledge.md`：角色已知自己绘画/藏画与玩家第三章后知分开；未采纳提前读信设想标不曾发生；动机缺项保留。Section F 将旧派生误读的更正建议保存在新文件，**未实际追加到旧摘要**，不能声称旧资料已纠正。
- 普通计划实际写 `09_revision/revision_plan.md`，消费真实 C12 Audit、静态普通 beta 和新提取资料。普通意见与 CNW 已确认 Finding 分开；保护固定第四章转折的建议列 P0 作者决策，P1/P3 无证据不凑项。未改正文、锁定 Canon 或批准晋升。
- private `standard_fixture_identity.json`、两个 result、run request/raw/source_snapshot/journal 保存完整身份；模型输出未手改。日期未知、部分源行号不准、沿用旧 Audit 过判等局限原样保留，非故事零错误证明。
- 普通计划完成后，正常入口在禁网络下重复返回 `reused`，账本字节未变。提取在另一操作追加日志后原适配身份失效，禁网络检查在缺 key 时停止，没有付费/reserve。最小修复：两处 selector 排除工作日志作为标准操作故事输入，缓存输出检查允许完整旧日志前缀后的合法追加；其他改动仍核验。旧调用不改身份，不冒充修复后 exact request；当前跨操作复用用受控离线证明，真实代表无需再付费。

## 独立审查与离线范围

Controller 最初 RETURN 路径别名可能绕过原文保护；输入统一解析身份，自动报告/日志碰撞提前拒绝，最终全部 writes 再核实际路径；绝对/相对/反斜线及报告自身作为源的反例通过。修复后运行前限定 ACCEPT。真实结果的岗位执行与下游消费限定 ACCEPT；其他三标准命令继续 `LIVE_NOT_RUN`。

新增 9 项覆盖四命令完整方法/文件消费、三标签/原稿保护、未锁定更正原字节及历史、普通 beta 计划、越界/master/锁定记录拒绝、无来源/无 review、半写恢复/源并发变化、路径别名/自动输出冲突、跨操作日志追加复用与替换拒绝。没有逐句 claims、自评 PASS 或新创作阶段前置门。

```powershell
.\runtime\envs\critics-api\Scripts\python.exe -m unittest tests.test_cnw_operations tests.test_cnw_chapter_arc tests.test_cnw_pipeline tests.test_cnw_maintenance tests.test_cnw_recovery tests.test_cnw_role_inputs -q
# 62 tests / OK
.\runtime\envs\critics-api\Scripts\python.exe -m unittest tests.test_cnw_runner tests.test_cnw_generation tests.test_cnw_adapters tests.test_cnw_project_import -q
# 64 tests / OK
```

合计 126 项离线；PowerShell AST 通过。精确 C/T 仍待独立签收及正常推送。不是 J19 完整终验、整体复刻通过或 `USER_CREATIVE_ACCEPTED`。
