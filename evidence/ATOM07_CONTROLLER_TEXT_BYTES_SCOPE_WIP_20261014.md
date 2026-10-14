# Same readonly Controller: actual text input failure

Writer verbatim transcription of the same independent Controller's actual
reply, `/root/goal_controller_61_restart_20261013`. The failure remains a
failure; this scope guidance grants no acceptance or push permission.

已独立核实根因及失败原件：

- raw SHA 与记录一致，exit1，源码前后相同。
- 捕获60文件 UTF-8 字节 SHA 全匹配。
- 实际九阶段已物化；Refine 为 `EXECUTION_INCOMPLETE`，Re-review 未运行。
- excerpt 实际 SHA 为 `84aa1b51…82202d3`；从 selected_sentences 重算 canonical LF 为 `bd681dec…28c587a`，两者仅 Windows 换行不同。

最小修复成立：[cnw_runner.py](D:/CangqiStudio/StoryStudio/tools/cnw_runner.py:2461) 对**已核 V2 合同**使用 `write_bytes(excerpt.encode("utf-8"))`；V1 保留原 `write_text`。保留授权端精确字节比较，不放宽为换行归一化接受，也不重写失败 Run/快照。

必要定点验证：

- 真实 producer→metadata→input snapshot→`verify_auxiliary_native_input` 字节一致。
- 篡改正文、来源选择或字节仍拒绝；V1 原字节行为保留。
- 合并 NK 修复形成统一最终身份后，再用新签名完成实际全链复验。

本失败不能签收；原件保留。07、推送及08仍未获许可。
