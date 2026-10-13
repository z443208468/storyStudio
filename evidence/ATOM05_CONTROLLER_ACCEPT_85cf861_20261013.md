## ATOM05 当前工程门完整裁决

**C**=`85cf861ad84851fbaaa91c0b95a75ee0fb5b9be6`  
**T**=`48c9b06ec9c5bdd06641759ce0c821558d19856f`  
**适用计划 SHA**=`59459D839780C8B5D729AF81F3805CBFA63E6582F283EC7D725D48C36FDBFF3D`

```text
CURRENT_ATOM_CLOSURE_VERDICT=ACCEPT_ALL_CURRENT_OFFLINE_ENGINE_GATES
METHOD_FIDELITY_VERDICT=ACCEPT_FOR_CURRENT_ATOM05_APPLICABLE_SCOPE
FREEZE_SCOPE=EXACT_C/T_AND_CURRENT_ENGINE_EFFECTS
NEXT_ATOM_PERMISSION=ATOM06_ONLY_AFTER_EXACT_PUSH_AND_REMOTE_READBACK
GIT_PUSH_AUTHORIZATION=YES_EXACT_NORMAL_FAST_FORWARD
CUTOVER_STATUS=BLOCKED_SEPARATE_GATE
```

这是对**全部当期适用工程门**的收口，不是只签 bridge 局部修复，也不包括私有迁移或真实生产接受。

### 当期门对账

| 门 | 核实结论 |
|---|---|
| 候选与正本所有权 | 同 Run 上游消费、两 Run 候选隔离、新 Run 不改旧状态及冲突拒绝，按已有未变实现与原始回归证据保留 |
| 项目写入仲裁 | 当期最小共享锁、竞态及合法提交/拒绝证据成立；完整维护/Sprint 综合并发仍按计划留给09 |
| 晋升事务恢复 | 持久准备、正文发布后补齐索引、旧正文归档、无关索引冲突拒绝、相同事务重入均有实物与绑定证据 |
| 共同费用边界 | 普通 Run、注册 import/maintenance、NK/CritiCS 的实例归属、共同账本/槽位、结算与 UNKNOWN 保留成立 |
| 原生入口与回读 | wrapper 降级入口和直接 bridge 注册入口已闭合；合法内部调用经过真实 bridge 准入、材料读取、写出及费用回读；V1 兼容保留 |

### 最后修复与证据

直接 bridge 对注册参与者要求 typed invocation，并重验当前 RunAccount、父/child、action/stage、材料路径及字节、当前 accounting dispatcher。普通 CLI、布尔及 JSON 无法取得该上下文；拒绝发生在 Key、目录创建和 native 前。

正例没有 mock 掉 bridge.main 或授权门。两个注册实例分别产生 SETTLED 与非零 UNKNOWN，实际原生输入/输出、费用上下文和回读一致。

已独立核对：

- 十份新增记录的 Git 字节、大小、SHA 全匹配。
- 最终 **53 passed / 26 subtests**，raw SHA `0576de6482128b647beed600bcd111bbfd7ab503b45e3888c7d69429623e0dad`。
- 最终 Python3.11 **5例 OK**，raw SHA `2782f3bcf9117826599c158adddaad32e08e62f92c608becf4238ea0802d7e97`。
- 两组最终 source maps 均匹配当前源码；实际产物、请求/响应/输出及费用归属校验一致。
- 早期失败、缺 bridge SHA 的首份记录均保持原范围；没有把旧133例说成测试了最终全部字节。

固定 CNW `97ad71fe` 未变；旧基线 `26b72cea / 535496ba` clean，未跟踪锁哈希保持。私有保护报告按既有范围核证，未重新打开私有原件。

### 冻结与推送许可

冻结上述精确 C/T、计划身份，以及三份 closure/route/native-entry manifest 和其原始记录所定义的当期工程效果。后续修改须回归受影响的已接受功能。

仅当远端仍为 **`049b0d26bd4bc6c2c4c1b5662782a4c8b34a8dcb`**，允许正常快进：

`049b0d2 → 3a911ab → 01d348e → 85cf861`

必须回读最终 C/T；远端变化须复审。**两个父候选的 RETURN/NO_PUSH 原判保留，不追认旧授权。**

回读一致后，仅允许进入 **ATOM06 当期工程范围**，不提前开启07及后继 Atom。实际用户包生产门仍为 `RETURN/NOT_RUN`；必要付费验收授权已有，生产代码、可信签收及费用执行门仍须按后续顺序闭合。TS 恢复、迁移、cutover 和默认切换未解锁。

本轮只读核证，未运行测试、修改文件或调用 Provider。