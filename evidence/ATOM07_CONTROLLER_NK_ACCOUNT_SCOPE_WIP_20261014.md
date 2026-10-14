# Same readonly Controller: actual low-entry account boundary

Writer verbatim transcription of the same independent Controller's actual
reply, `/root/goal_controller_61_restart_20261013`. This is WIP repair scope,
not current Atom acceptance or push permission.

新增差分符合此前限定方向：V2 excerpt 使用 LF UTF-8 字节、V1 保留原写法；预留与 shim 共用 cap；shim 纳入实现身份；三份旧 PS 仅补参数及环境恢复。

**仍发现一个具体费用身份缺口：**

[cnw_runner.py](D:/CangqiStudio/StoryStudio/tools/cnw_runner.py:1645) 的 `_invoke_nk_service_in_slot(run, payload, guard)` 核验 Run 授权后，直接使用调用者传入的 `guard` 预留和结算，未核它是否属于当前 V2 Run 的 `support_hook` 账户。传入 `_p2_guard()` 可走无项目费用上下文的旧账本路径，绕过该 Run 的签名预算检查。

最小修正：

- V2 低入口重新派生当前账户，拒绝不匹配的 legacy guard、项目实例、Run、stage 或 model；随后使用真实派生账户。
- V1 保留原 guard 行为。
- 补低入口错误账户拒绝负例，核零预留、Node、HTTP；合法账户沿现有正例验证。

当前99389继续冻结到终态。已出现的 Owner 组件失败须按实际堆栈判断；我不推测其原因，也不将已输出组件扩大为整批通过。无07 ACCEPT、推送或08许可。
