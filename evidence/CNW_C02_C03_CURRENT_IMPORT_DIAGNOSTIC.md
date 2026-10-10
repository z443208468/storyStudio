# C02/C03 当前完整导入与普通增量

日期：2026-10-11；固定方法与正式入口见 `docs/CNW_INCREMENTAL_INBOX.md`。同一私有虚构维护项目 `workspace/FICT_CNW_MAINTENANCE_20261011`，两份静态原材料；不是苍歧新小说。

## 实际调用与消费

| 操作 | Private run | Provider ID | Usage input/output | 估算 CNY |
|---|---|---|---|---|
| 当前完整 Workflow01 | `9ba6ecbd767c8ca5843b0f0f` | `46af0c65-6782-4b36-8125-e7fcbd9451c8` | 21748 / 3407 | 0.071106 |
| Workflow02 新资料 | `1dd886d954bc2ed978f667a9` | `19eddc05-1acf-4789-b7a6-7e05954b9c60` | 28858 / 1539 | 0.070379 |

均正常 `deepseek-flash / stop / SETTLED`，合计 0.141485；保守 campaign 占用 4.902803 / 10 CNY（含历史未知预留）。

初始首次发布被机械校验阻塞：交接同时引用已读原件/项目文档和未绑定路径；还返回了官方 source_log，旧目录白名单不接受。对照官方后修消费器：项目上下文真实绑定、未核实引用显式保留而不作支持、允许两官方日志并保留模型正文。日志白名单变化之外，原请求方法、正文及其他数据相同。核 request/raw 后重消费**同一成功响应**，禁 HTTP/新 reserve 下发布 `INITIAL_IMPORT_COMPLETE`，账本字节未变；独立 `response_reconsume` 记录差异，原收据未改。未手改模型内容，没有付费重试。

增量输入仅 `_INBOX/incremental_review_note.md`，原两材料未重送；没有 required_initial_documents。实际追加既有 beta、Arc、project design、character bible、待决项和两日志。旧材料、旧正文不变，已更新文件保留完整旧前缀。九个规定文档与操作日志均有实际内容。三标签/来源/问题及后续文件消费保存在 private request/raw、source snapshot、classification、journal、import_state 和 result。

`diagnostic_current_import_consumption_check.json` 实核全为 true：旧原件/正文不变、只新增源、无 bootstrap 要求、旧 prefix 保留、无 legacy manifest、九产物齐全、正常无变化重入 `NO_NEW_OR_CHANGED_SOURCES`、禁网络和 reserve 下账本不变。

## 模型局限及独立范围

本次增量 `conflicts=0` **不是正确识别全部矛盾的证明**。Controller 指出旧 Arc 第三章揭信与 glossary 第三章开信，而新增“整 Arc 未拆信”的范围可能冲突或含糊，却被直接追加；记录为未识别冲突/范围歧义。当前完整来源及官方冲突指令已提供，未发现新的接线缺口。输出原样保留，不手改或重付费追零错；冲突处理机制仍由离线反例证明。

Controller 运行前、消费修复及本组真实执行/旧资料保护/增量消费者分别限定 ACCEPT；上述观察按要求补入。不代表 J19 全链、总体工程或创意亲读已通过。

新增 10 项覆盖：普通无 manifest、两旧源+新源、变源冲突双方、无变化不复制/不调模型、外部原字节 staging/候选保留、场卡/Plot/评稿追加及正文拒绝、pending 先恢复、初始前置、已读上下文与未知引用区别、官方日志保留、只日志路由扩展的窄重消费及系统/正文/模型/容量/端点/非日志变更和 request/raw 篡改反例。

```powershell
.\runtime\envs\critics-api\Scripts\python.exe -m unittest tests.test_cnw_operations tests.test_cnw_chapter_arc tests.test_cnw_pipeline tests.test_cnw_maintenance tests.test_cnw_recovery tests.test_cnw_role_inputs -q
# 62 tests / OK
.\runtime\envs\critics-api\Scripts\python.exe -m unittest tests.test_cnw_runner tests.test_cnw_generation tests.test_cnw_adapters tests.test_cnw_project_import tests.test_cnw_incremental_entry -q
# 74 tests / OK
```

合计 136 项离线。精确 C/T 签收及远端回读仍须完成；没有新增正文、预算或 `USER_CREATIVE_ACCEPTED`。
