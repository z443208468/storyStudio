## 精确候选裁决

C=`3a911ab51ca849925e3d526a964b048a4304587b`  
T=`b345d8de42959c5236b297a6071dcbd1852b471a`  
父及当前远端 main=`049b0d26bd4bc6c2c4c1b5662782a4c8b34a8dcb`

```text
CURRENT_ATOM_CLOSURE_VERDICT=RETURN
METHOD_FIDELITY_VERDICT=RETURN_FOR_REGISTERED_COST_BOUNDARY
FREEZE_SCOPE=PRIOR_ACCEPTED_SCOPES_PRESERVED; NEW_CLOSURE_NOT_ACCEPTED
NEXT_ATOM_PERMISSION=DENIED
GIT_PUSH_AUTHORIZATION=NO
```

### 唯一明确阻断根：注册材料仍可降级到 legacy 费用路线

[p2_06_critics_run.main](D:/CangqiStudio/StoryStudio/tools/p2_06_critics_run.py:59) 是否要求父 Run，目前主要取决于**输出目录**是否属于注册项目。

下面组合仍可绕开新增绑定：

- `--run-name <legacy-name>`，或仓库 `ROOT/runs` 下的 `--run-dir`；
- `--input` 指向注册项目材料，或 `--critique` 指向注册项目材料；
- 不提供父 Run。

输出被判为 legacy，遂跳过注册父 Run、通用授权及 RunAccount；随后 [project_path](D:/CangqiStudio/StoryStudio/tools/critics_bridge.py:17) 又允许注册项目输入，`_execute_native` 可以用 `account=None` 的旧费用路线消费它。

**这是实际 CLI 可达的归属缺口，静态调用链可证；本轮未执行该组合。**现有负例只覆盖“注册输出缺父 Run”，没有覆盖“legacy 输出＋注册输入/critique”。

最小修正：

1. main 与下层组件共同核对 input、critique、output 的物理归属；注册材料不得因选择 legacy 输出而降级。
2. 加真实 main 组合负例，在 Key、slot、reserve、native 前拒绝；保留合法父 Run 组合和真正 V1 输入/输出兼容。
3. 保留授权函数真实行为，不 mock 授权求通过。

不扩新平台、不提前实施 ATOM06。

### 已完成的核证

- **晋升恢复组件效果成立**：持久准备、正文发布后恢复索引、无关索引冲突拒绝、相同事务重入、旧正文归档均有实际产物；journal/body/index/archive 的 SHA 与内容绑定一致。
- NK/CritiCS **合法注册组件路线**真实使用 RunAccount、共同账本和槽位；两实例归属不同，SETTLED 与非零 UNKNOWN 保留，原生结果被实际回读。此证据不能覆盖上述 CLI 降级分支。
- 16 份提交记录的 Git 字节、大小及 SHA 全匹配 manifest；13 份实物 hex 非空、SHA 正确，请求/响应/输出、父费用上下文及回读内容绑定均核对一致。
- 原始日志确为 **133/66、后续3例、Python3.11四例、最终16例及3.11单例通过**。已核其源码差异；没有将133例说成最终全部字节同版。
- 当前计划 SHA 保持 `59459D83…FDBFF3D`，固定 CNW `97ad71fe` 未变；旧基线 `26b72cea / 535496ba` clean。保护哈希报告已读，本轮未重新打开私有原件。

### 冻结、复验及顺序

00–04 原接受、既有05限定接受和全部历史 RETURN 保持原判。当前晋升及组件证据原件保留，可在后继候选中按未变身份复用；**不另授本候选局部推送，不把它冻结为 ATOM05 整体接受。**

当前仅允许 ATOM05 最小返修及必要复验。形成新精确 C/T 后，仍须审全部当期适用门，接受、推送并回读后才能许可06。

`CUTOVER_BLOCKED=true` 独立保持，不是本次工程 RETURN 的原因。实际整包生产门仍未通过；本轮无测试、修改或 Provider 调用。