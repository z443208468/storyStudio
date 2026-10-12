# ATOM07 原始候选裁决：RETURN

```text
REVIEWED_COMMIT=550c94a8dfb8ca27cb425fe68198ee10cfc38735
REVIEWED_TREE=26786a877f2abef48aaa8d3af3125038b9c4ed49
PARENT_AND_REMOTE_MAIN=635ed3c0780ecdca57c5837a5a20a6246116598a
REVIEWED_PLAN_SHA=AE5A1959EEAB75AD6A8F41460C38BF9678284C1D51A8D63B25CE37F7CB4F5183
UPSTREAM_METHOD_PIN=97ad71fe5e5e76a82275c6c63d4add06fb60ab6e
GIT_PUSH_AUTHORIZATION=NO_PUSH_AUTHORIZATION
```

本次自行读取 R5 全文、治理、19 路径差异、源码、测试设计、原始输出和私有身份原件。未运行测试、修改文件或调用 Provider。审查结束时 Writer 已开始修改一个 fixture 文件；该 WIP 不属于本裁决对象。

## 唯一硬 RETURN 根因

[tests/test_cnw_w10_optional_integrations.py:21](D:/CangqiStudio/StoryStudio/tests/test_cnw_w10_optional_integrations.py:21) 创建临时目录时依赖已存在的忽略目录 `ROOT/workspace`。干净源码没有该目录，九项必要回归均在 `setUp()` 失败。

已独立核对精确候选冷克隆：

- **9 failed、86 passed、91 subtests，exit 1**；
- raw SHA：`aa61f9a698ac4b5c2fbb415838cac777e4c0f91b94da7ff033b5071477c28768`；
- 冷克隆 C/T 匹配；168 个记录源码哈希未变，工作树干净。

这是必要的可复现验证门失败，不能用本地测试绿替代；也不是缺 Key 或生产信任部署造成的失败。**未定位第二个硬 RETURN 根因。**

拟修为“独立 TemporaryDirectory → 显式临时 DataHome → 真实 create_project 注册”，保留实际 `safe_run`／registry 门和九项原断言，符合最小修正范围。

## 分层裁决

| 项目 | 裁决 |
|---|---|
| `CODE_FIX_VERDICT` | **RETURN**：候选必要冷克隆回归未通过；已定位的生产代码根因修正可保留 |
| `ATOM07_OFFLINE_ENGINE_VERDICT` | **RETURN，等待定点返修复验**；共享身份核验、job→实际离线 Run 准备已有实证 |
| `EARLY_CNW_E2E_GATE_VERDICT` | **ACCEPT_LIMITED / SIMULATED_OFFLINE**：既有单个 ADAPT 场景真实消费者链；不等于 ATOM09 或包全链 |
| `METHOD_FIDELITY_VERDICT` | **未观察到方法漂移；本候选整体签收待返修** |
| `W10_ATTESTATION_VERDICT` | **ATTESTATION_PENDING**：协议与闭锁有离线证据，真实部署权限及独立信任根未验证 |
| `TS_LIVE_AUTHORIZATION_STATUS` | **NOT_AUTHORIZED** |
| `TS_RECOVERY_ELIGIBILITY` | **NOT_ESTABLISHED** |
| `INPUT_PACK_TO_STORY_GATE` | **RETURN**：入口目前准备材料、合同与 Runs，尚未自动完成故事全链 |
| `CUTOVER_STATUS` | **CUTOVER_BLOCKED=true** |
| `GIT_PUSH_AUTHORIZATION` | **NO_PUSH_AUTHORIZATION：禁止推送 550c94a** |

## 实质证据与保护结论

包入口现在内部派生 Run ID，调用真实 `produce(create_only=True, mode="offline")`，再核验既有 Run；重复准备与创建后中断不会重建或改写已有 Run。用户无须填写合同 JSON、SHA 或 Run ID。这仍是**生产前准备能力**。

Early 原件包含同 Run 的 11 个非空产物、16 个模拟请求、五 Lens 独立输入、三票 `2/3`、Completeness 遗漏进入 Refine、新稿进入受影响 Re-review，以及可读导出。已核对嵌入内容与请求哈希，包括 Windows 换行差异。所有回执明确 MOCK_ONLY／SIMULATED。

本差异没有修改四角色读集、Prose 白名单、Lens／Verifier 分工或阈值；M01–M10 的未变消费者证据可复用。M11–M13 的完整 Workflow／Sprint 总验仍属 ATOM09，未提前签收。M14 的冷克隆兼容回归须完成本次 fixture 修复；M16 的工程、签名、Live、费用和用户创意边界保持分离。

直接读取真实 TS 原件后，状态、合同快照、源稿、manifest、V3 映射、旧政策及账本哈希均匹配冻结记录：

- TS：`EXECUTION_INCOMPLETE`，原失败 `DEEPSEEK_API_KEY_REQUIRED`，0 requests／attempts；
- state SHA：`3bae0722506641f1c14840d2f2568f03484cd6b1298c972baf3700d0de42ee0d`；
- ledger SHA：`c8b0705f491ef824db01be0b7991f4db9db7d84e153c26481e93a4fdcd0eab9b`，UNKNOWN 未清；
- 冻结旧基线 C26b72cea／T535496ba 仍 clean。

真实 ZIP SHA 再次匹配 `5d50fa…89196`，372 文件。用户最终目标仍是交包、启动、应用内部处理并交付符合包内要求的故事；本候选未达到该产品门。

## 下一步

**停留 ATOM07。** 仅修上述 fixture，保留失败 raw，追加正常提交形成新 C/T；复验受影响模块和精确候选冷克隆后再审。不要重跑真实 TS或改历史签收。

新候选获得限定 ACCEPT、正常推送及回读后，才可继续 ATOM08 的安全源码／文档整理；不迁移、删除或切换旧私有数据。随后 ATOM09 承担隔离断网的虚构包自动全链。此条描述施工顺序，**本次不授权跳阶段**。

历史 C3／ATOM09 RETURN及后续用户指示推送的事实保持原样，不予追认。
