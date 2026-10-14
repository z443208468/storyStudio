# Same readonly Controller: NK input-boundary WIP scope

This file is Writer's verbatim transcription of the actual existing readonly
Controller `/root/goal_controller_61_restart_20261013` message. It is scope
guidance, not overall ATOM-07 ACCEPT, C/T acceptance or push permission.

## Original finding

准备全门清单时确认一个仍未覆盖的具体NK费用/发送边界：runner._invoke_nk_service_in_slot在1652行固定预留input_token_cap=10000；_verify_current_nk_payload只比当前Cards payload，未估算输入；nk-live-fetch.cjs实际originalFetch前只查endpoint/model/json模式/max_tokens=512，没有按实际messages核输入上界。合法但大的Cards/角色payload因此可能按10000预留却发送更大输入。旧20文件NK小样例与当前完整链(NK DISABLED)不能覆盖此条件。另同shim是实际HTTP消费者，却不在implementation_identity的.py/studio/prompts清单中。请先核这两个事实；最小补原生NK实际消息上界（≤预留且≤Owner限制）并把该实际shim字节纳入原实现身份，不新增平台/不改正在运行源码。我继续按原范围整理既有证据复用。

## Original bounded repair / reuse guidance

你提出的NK最小收口方向可用：Runner真实_in_slot取已核Owner输入上限，实际reserve cap与传给shim的cap一致；shim对实际messages按Runner现行Unicode字符+256口径在originalFetch前拒绝超限/缺失/非法值，测试含astral及两种限额（预留/Owner较小者）。实际shim加入implementation_identity。V1不增Owner要求，保留原10000路线；共享shim新增门须给真实V1合法输入兼容定点。失败无capture继续原UNKNOWN保守结算，不需另造NOT_SENT接口。当前源保持冻结；这些新增身份字节会使旧grant失效，最终用新签名做合法NK（含真实reserve/cap/映射/Brief缓存）与身份拒绝定点即可，不重跑NK DISABLED的完整CritiCS链。正在核最后复用清单。
