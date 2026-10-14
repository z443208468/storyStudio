## 合并判断

诊断原件与摘要已核对，报告SHA为 `30d08b5a…de19fb2`。**现在已证实重复计算负载；仍未复现或解释原10秒超时。** 不建议继续盲目提高上限跑整链。

### 1. 实际计数说明什么

- 2000次真实CLI全部成功，累计39.017秒；最大1.984秒，同时在途最多1次。
- 触发的是诊断安全上限，发生在Plot首次预留完成前。
- 没有Provider回执或费用请求，未到native/Lens目标。
- `stack_outer_functions`统计的是**CLI事件归属**，不是函数调用次数；不能把740解释成740次完整预检。
- 句柄312→323、线程始终1，仅两端快照不足以证明泄漏。

源码中的重复结构已可定位：

[build_request](D:/CangqiStudio/StoryStudio/tools/cnw_live_authorization.py:80) 对已有Run先完整计算一次，再调用 [build_run_contract_preflight](D:/CangqiStudio/StoryStudio/tools/cnw_project.py:862)；后者又在开始、结束完整计算两次。一次已有Run请求构造因此执行三遍完整预检；签名验证末尾的 `rebuild()`又重复这一结构。高入口、槽内、预留、发送前继续分别核验。

这是有限的重复调用，尚未找到无限递归。它是07授权接线放大的实际负载，不能直接认定为Windows超时原因。

### 2. 可批准的最小结构修正

**先消除 `build_request()` 内已有Run的额外完整预检，不缓存权限、不改 `project_paths`。**

已有Run直接调用一次真实 `build_run_contract_preflight()`并使用其已验证bindings；保留该函数现有开始/结束重算、Run/合同/来源/权限/TOCTOU检查。仍须比较当前Provider/Workflow与报告绑定，保证pre-run与existing-Run签名身份完全相同。

保持：

- 新Run原预检路线；
- `_verify_bundle`末端重新构造比较；
- 各次入口、锁内预留及发送前独立核验；
- 原额度、槽位、UNKNOWN和模拟边界。

本轮先不批准删除其他层的校验或引入“已验证”参数/跨调用缓存。机械消除这一重复已具备源码依据，无需先提高诊断上限证明。

### 3. 同轮必须补齐的期限末端检查

[ `_verify_bundle`](D:/CangqiStudio/StoryStudio/tools/cnw_live_authorization.py:182) 目前只在开始调用 `_terms()`检查时间，之后才进行签名验证和可能较慢的完整重建，返回前没有再查期限。

因此许可可能在验证期间到期却被返回为有效。这一窗口现在随已测重复负载变得不可忽略；它属于07原授权实现，不是最新NK ready补丁引入。

最小修正：全部字节/身份稳定性检查结束后、返回许可前，再按真实当前时间检查同一terms。章节和operation共用此边界。不要改变期限或预算规则。

### 4. 共同有限复验范围

集中完成上述两处后：

1. pre-run/existing bindings相等、合法签名实际消费者，以及错误来源/Run/Provider/实现身份拒绝。
2. 验证过程中到期的许可在末端拒绝；保留before-reserve/before-send效果。
3. 重跑**同一有界诊断一次**，记录优化前后CLI数量与时间；必要时给这个诊断一次明确较高计数界限和总时长界限，首个失败立即停止，不多轮抬上限。
4. 诊断达到前六阶段/native5及一项合法Lens后，才安排最终完整链。诊断本身不标全链PASS。

两根集中修复的6/27证据继续按原范围保留；优化改变授权实现身份后须用新签名验证，不能重标旧grant。原超时、2000上限停止及所有失败记录保留。

**当前无新C/T整体ACCEPT、推送或08许可。** 完整链、资源超时原因及最终候选仍待闭合。
