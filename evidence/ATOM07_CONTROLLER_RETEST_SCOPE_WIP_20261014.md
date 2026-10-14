# ATOM-07 readonly Controller retest scope — WIP

Provenance: verbatim final message from independent readonly Controller
`/root/goal_controller_61_restart_20261013`, received 2026-10-14.
Writer transcribed the message below; this is not an ACCEPT or candidate verdict.
Original f8c72d5 RETURN remains unchanged.

---

## 本次最小复验清单

范围限定为 f8 RETURN 返修及其实际影响。**不要求重跑所有 Atom，也不把性能优化加入验收前置。** 当前 CritiCS 原进程继续等终态，保留原源码身份和输出。

### 必须在最终返修源码上验证

| 范围 | 最小实际验证 | 依赖原因 |
|---|---|---|
| 旧 revision_apply 拒绝 | 新 V1 workspace high／low 负例；注册签名 revision 正例、真实创意批准伪造负例 | `_require_generic_provider_authorization()` 改变了操作路由 |
| 注册操作及恢复 | 现有签名 import→update→audit→handoff、缓存重入；旧 owned operation 的中断／缓存拒绝、重绑定费用快照拒绝 | 共用授权、费用和实现身份读取；不能只测 revision |
| NK 合法输送 | 已有真实 Plot→Cards→NK→Brief、缓存／篡改、共同费用，以及无 scope／错 payload 拒绝 | 新辅助许可、NK payload 校验和模拟映射 |
| CritiCS 合法输送 | 正在运行的真实 native Plot/Text→CNW Refine 链终态；pending／缓存零重复调用 | 新父阶段、action、输入、账户及 native reader |
| Native 防 Live | current／attempt／pending、receipt+hook 同步重标、context 退出；拒绝定位 native 原始证据 | 新 shared 枚举、模拟标记、`verify_live()` |
| Native 输入额度 | 已有两种真实 capture 超界负例，零 slot／reserve／HTTP | 新实际输入估计及签名上界 |
| W10 共享边界 | 实际 high／low及缓存、非法请求零输送；实际 CLI prepare→checked Plot→重入；旧 packet 拒绝／新 packet 消费 | 委托同一授权与 checked recovery；不要求再跑整个 bounded-stop 集合 |

shared 枚举若只是等价提取循环，**不必因此再生成一次完整 native 故事链**：原链证明生产者与实际方法效果；最终小范围消费者测试证明新枚举的 current／attempt／pending 行为。须分别记录两批源码身份，不能冒称同版全链。

### ADVISORY 长度：保留效果，不遗漏共享输送影响

- **可沿用：**未变的 builder、长度 validator、旧无字段语义、角色／审稿政策注入、revision 真正丢 beat 拒绝、原文 export 的已核证据。
- **最终源码需定点验证：**现有三个实际授权消费者：
  - 欠产 Prose：一次请求，无补写；
  - 超限 Prose：一次请求，无重写；
  - Refine 消费真实 Finding，长度不触发补字，`NO_CHANGE` 零追加。

原因是这些执行路径经过本轮修改的授权及历史消费门。无需重跑已被所有者明确废止的严格长度变体测试。

### 受影响冻结06：定点保护

使用现有小范围测试，证明：

- 旧格式／原生格式实际入口达到当前真实关闭门，零 Provider／费用；
- 同 attempt 重用、发布中断恢复、pointer／mode／contract 篡改拒绝；
- 原 offline 合同、Run、导出字节保留；
- 模拟及不完整 Live 前章不得物化为合法前章；
- 生产 export 在 `verify_live()` 未通过时拒绝；
- 06 routing 修复的重算 locator／adapter 伪造仍被拒绝。

对应依赖分别是 `publish_request()`、`produce()`、共享授权、`verify_live()`及 native 前章验证。**不是重新施工06，也不要求重跑三任务／五任务全部故事链。**

### 旧 V1 与 export

本轮改动了 NK 映射、CritiCS native 捕获／reader 和 recovery，必须保留真实 V1：

- NK→Brief 新结果／缓存；
- CritiCS wrapper／direct bridge 的原注册拒绝与真正 V1 兼容；
- 旧 native evidence 回读；
- 旧合同长度语义及原文导出。

已有当前链未覆盖的旧分支做定点回归；未变的四角色、双 Lint、五 Lens、Verifier、Completeness、Sprint 等原方法证据按精确函数／模板身份复用，不重新全矩阵求数量。

## 复用规则与停止边界

已完成证据可以复用，但须列出**原 C/T或源码 SHA、原命令／raw SHA、未变函数与当前差分**。旧签名材料不是新实现的生产许可。

所有失败、bounded stop、所有者停止的长度测试、旧 RETURN、冻结05／06原判及保护锁保持原件；不重置、不抹除、不为采集重复运行已证逻辑。

最终仍须新精确 C/T 的完整07审查。本清单不构成 WIP ACCEPT、推送或08许可。
