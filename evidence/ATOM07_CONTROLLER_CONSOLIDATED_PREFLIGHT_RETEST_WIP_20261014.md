## 本轮合并复核结论

**两处授权修正及受影响回归未发现新的已确认生产源码问题。当前仍缺单Lens诊断目标、完整11阶段终态和精确新C/T验收；不是07 ACCEPT。**

### 已核证

- 统一批次 exit0，**7 passed / 8 subtests**；raw SHA `3222b354…71c89d`匹配，源码前后及当前文件一致。
- [build_request](D:/CangqiStudio/StoryStudio/tools/cnw_live_authorization.py:80) 的existing-Run分支使用真实预检报告，保留前后两次完整重算及当前Provider/Workflow比较，没有权限缓存。
- `_verify_bundle`完成签名和重建后再次检查期限；章节、operation高低入口到期拒绝及撤销后的UNKNOWN保护有实际证据。
- provenance SHA `df0d3ff4…9454f3`匹配，记录本轮生产变化仅上述两函数。
- Plot三文件证据只能作为 **SUBSET** 核证，不能冒充含合同的whole-Run捕获；报告限制正确保留。

### 诊断与当前全部剩余项

| 项目 | 已确认事实、来源及影响 |
|---|---|
| 外部driver选择错误 | 正式 `expected_requests()`返回五项合法Lens候选；driver错误要求列表长度1。这是本轮诊断脚本错误，未发现生产builder错误。 |
| 单Lens目标缺失 | 前六阶段实际物化，native Plot五调用、九条SETTLED行成立；30文件SHA及合同匹配。但尚未发送Lens。 |
| 原ACL超时原因未解释 | 26877次真实CLI均成功，最大0.641秒，同时1次；不能因此追认旧超时已解决。不同停止点也不能据总时长宣称等工作量提速。 |
| 完整链仍缺终态 | native Text三调用、Refine真实消费、新稿复审和完整链收口尚待最终运行证明。 |
| 后续Live导出说明差异 | 旧managed导出仍无条件写模拟/offline说明。属于后续08/09相应产品范围，原问题保留，不提前施工。 |

句柄增长至780的端点记录**不足以确认泄漏或排除泄漏**；本轮没有据此新增源码修复要求。

### 允许的最小下一步

仅修外部driver：从真实五项候选中筛出 `stage=multi_lens_review`、`role_id=style` 的唯一项，再调用真实消费者。**不改生产 `expected_requests()`。**

保留60000命令/1200秒边界、原失败及新标签，编译生成文件文本以保证行号对应。只补一次该诊断目标；不提高上限、重试、缓存权限或改10秒timeout。

若这一次达到合法Lens终态，再进行最终完整链。若失败，按实际证据集中判断，不能直接循环重跑。

旧两根6/27、已有费用/操作/冻结功能证据按原限定身份复用；最终候选仍须核完整差分、字节身份、受影响回归、保护清单和原始裁决链。

**f8 RETURN保持；NO_PUSH；ATOM08_PERMISSION=WITHHELD。** 本结论限于本轮授权修正与已核调用链，不保证未遍历代码绝无其他问题。
