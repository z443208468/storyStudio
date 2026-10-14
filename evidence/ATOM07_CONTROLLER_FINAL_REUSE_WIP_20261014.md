# Verbatim readonly Controller WIP guidance

Writer transcription of the same Controller's actual final reply,
`/root/goal_controller_61_restart_20261013`. This records the original WIP
scope; it is not candidate acceptance or push authorization.

## 当前结论

这是 **ATOM07 WIP 证据复用指导**，不是候选 ACCEPT。

只读回读仍为：

- HEAD：`f8c72d59b070a3544047189de0fb31f3b138e6df`
- Tree：`ee325b8429aadc8f68e3d6091204dc4e9f997765`
- origin/main：已冻结的 `84e022de0fee6eb7d7eec4c248703621129491e1`

原 f8 RETURN、NO_PUSH 保留。当前完整 native 链未终态，不能计为成功。

## 已核证及可复用范围

已独立重哈希 15 组终态 raw/check，全部符合元数据索引；49 项当前物理身份输入符合记录，并等于 Git 过滤字节。两个索引 SHA 与所报一致：

- `final_reuse_metadata_20261014.json`：`8cc747eb…f358`
- `method_source_scope_20261014.json`：`5688fe9f…1671`

| 范围 | 可以复用的证据及限制 |
|---|---|
| ADVISORY、W10、包 attempt/来源/旧产物保护、legacy revision 拒绝 | `final_shared_consumers_batch` 的 18 项及 30 子例，按原字节身份和 LF 等价复用。 |
| signed import/update/audit/handoff、缓存与费用重绑定拒绝 | `final_operation_consumers_batch` 的 6 项及 6 子例；新增 revision 测试不改变原六项来源身份。 |
| 合法 signed revision 实际发布与缓存 | 最终 LF 五项中的实际维护消费者；已核批准副本、原稿/Canon/未批准章保护及缓存零追加。 |
| native current/pending/attempt、重标、去重及末端漂移拒绝 | `native_mock_boundaries_action_guard_fixed` 的实际断言可按 LF 等价复用，不能称为最终字节重新执行。 |
| 两项目共享费用 SETTLED/UNKNOWN | `signed_native_shared_account_unknown` 的费用、槽位、归属及保守 UNKNOWN 断言可复用；后来变化的 reader 由新边界测试和待终态完整链核证。 |
| 真正 V1 reader/辅助兼容 | 保留对应通过断言及函数身份。`legacy_native_export_compat_final` 仍是 **exit1 的部分证据**，不能整批标 PASS。 |
| 冻结06方法保护 | 相对 f8 未变不能直接证明相对84e未变。角色、审稿、合同、修订、导出等07变化由当前共享消费者覆盖；纯不变函数继续引用原冻结范围。 |

无需为这些已核范围再增加全矩阵。

## 当前还存在的具体必要缺口

除完整 native 链终态和新精确 C/T 外，**NK 两项缺口仍须收口**：

1. [cnw_runner.py](D:/CangqiStudio/StoryStudio/tools/cnw_runner.py:1653) 固定预留输入 `10000`，实际 [nk-live-fetch.cjs](D:/CangqiStudio/StoryStudio/tools/nk-live-fetch.cjs:29) 尚未在发送前约束实际 messages 输入估计。
2. 该真实发送 shim 尚未进入 [implementation_identity](D:/CangqiStudio/StoryStudio/tools/cnw_live_authorization.py:61)。

你提出的最小修法足够作为施工范围：

- V2 预留及 shim 使用同一上限：现有 `10000` 与已核 Owner 上限的较小者。
- shim 用实际 messages、与 Runner 一致的 Unicode 字符数加256口径，在 `originalFetch` 前校验；覆盖 astral、非法 cap、超预留及超 Owner 限额。
- shim 字节进入实现身份；修改 shim 后旧签名必须失效。
- 保留 V1 原合法路线，补实际 shim 兼容定点。
- 用最终字节、新签名复验合法 NK→映射→Brief/cache，核真实预留 cap 与传输 cap 相等。

**无需另建 NOT_SENT 接口。** 该路线可能已经预留才被 shim 拒绝；应断言零 Provider HTTP，并保持原 UNKNOWN 保守账本，不能宣称零预留或清零费用。

等当前 producer 终态后再改源码。NK DISABLED 的完整 CritiCS 链无需因这个定点修复重新生成一次；其旧实现身份必须明确保存，最终另做新实现签名身份定点。

## 候选需保留

保留原 f8 RETURN 原文、全部失败/停止/过期记录、通过 raw/check/capture/audit、LF 前源码和归一化报告、PS 等价记录、两个复用索引，以及最终完整链原件和冻结保护记录。只纳入非敏感虚构证据，不能改写历史 grant/Run/raw。

当前没有新的整体07签收，也没有推送或08权限。真实用户整包全部任务生产、Live 成功、TS 恢复及 cutover 均未由这些模拟证据完成。
