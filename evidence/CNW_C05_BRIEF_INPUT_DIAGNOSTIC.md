# C05 Brief 补充读取与 Prose 声线选择：有限真实诊断

日期：2026-10-11。范围：`plans/CNW_PUBLIC_REPLICATION_GOAL.md` C05 输入缺口及必要的 C15 请求身份/运行入口修复。不是完整新链终验，不是创意接受。

## 官方依据与修正

固定来源 `MintoTsukino/claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`。

- `templates/config/ai_roles.template.yml` 的基础读取表继续保留；`templates/07_draft/writing_brief.template.md` 的 Active Canon 要求读取相关 Canon、世界规则和术语，Canon/timeline/world 模板进一步规定当期事实与时间范围。Brief 增补 `canon.md / timeline.md / world_bible.md / glossary.md`，完整固定模板说明进入实际 system 请求。
- 同一 Brief 模板的 Voice References 明确只选本话说话者。正常 Prose API 与 packet 使用同一选择规则，不再以全部出场角色代替实际说话者；实际 API payload 只有 `writing_brief / voice_samples`。
- 官方未规定 Voice References 必须无括注、一行只能一个角色。本次真实原样 Brief 暴露列表解析缺陷，修复说明段落、POV 括注与斜线合列识别；没有改模型输出或重新付费生成 Brief。
- 私有 API request snapshot 保存实际 HTTP JSON，不含授权头或密钥；成功回执绑定其 hash，复用时验证输入和原始响应身份。旧无 snapshot 的回执保留兼容身份，不宣称补出了历史请求原件。

## 实际运行与消费

私有项目：`workspace/cangqi_cnw_brief_diagnostic_20261011`。

运行：`CNW-BRIEF-J19-20261011-01`。仅同一 J19；byte/hash 兼容的历史 Plot/Cards 明确标 diagnostic reuse。旧 NK payload 与当前实际 payload 不同，未伪称可复用；按正常职责执行必要 NK + 一次 Brief。

| 真实职责 | Provider ID | Usage input/output | 保守估算 CNY |
|---|---|---|---|
| Native NK support | `c61f2f57-998a-4f30-98b6-450482a43b1b` | 752 / 130 | 0.002557 |
| CNW Brief | `7b283d0e-862a-401d-aba0-98303f7c622b` | 16586 / 3250 | 0.059468 |

两者均 `deepseek-flash / stop / SETTLED`。新成功调用合计 0.062025 CNY。未调用 Prose API，未生成第二场或新正文。

真实 Brief 进入正常 Prose 请求构建及 packet 构建；两者声线字节相同。四个说话者由原 Brief 列表选择；未发送其他角色样本、完整 Canon 或 contract.story。

- Brief 发布文件 SHA256：`abd28af10feb93ceae4480ef6b53152c447cfd72f3ad1f9a29a9ba109fcc272f`。
- Provider content SHA256：`4f084662ddfd7307e0fbf7b6736ccb79c3d4c9696bfa2b726eee33ca57a841ec`。发布器保留原 content 并按既有规则补终末换行；两个身份不混称。
- 选择声线 SHA256：`80869c5a2c84d4ceab0fce7410242ddbf59275d3491834e482b87ed3be63d6cb`。
- 私有证据：`artifacts/diagnostic_input_identity.json`、`diagnostic_runtime_identity.json`、原 provider request/raw、`brief_consumption_check.json`、`prose_input_preview.json`、`brief_cache_reuse_check.json`。
- 禁止网络、新 reserve、native 服务调用后，当前实际 NK+Brief 输入重复消费成功；相同 provider ID/content，账本字节未变。此项是真实付费身份的本地复用验证，不冒称新 Live 调用。

## 本次发现的运行入口问题

第一次诊断请求 `nk-CNW-BRIEF-J19-20261011-01-2bbcdb0e24a14af598a9a465a33a1113` 没有本轮 capture。查到固定 3179 上的旧 Next PID 6320；旧 capture 增加一条 provider `11ba2684-217b-4d9a-bf17-90645cd30b7d`、usage 752/109，但仍带旧本地 request ID，且无当前请求内容/时间关联。因此只记录可能关联，不制造本轮成功回执。

原护栏将该请求转为 `UNKNOWN_NOT_ZERO`，继续占用 0.028333 CNY。私有对账证据 `artifacts/nk_failed_request_reconciliation.json` 保留。全 campaign committed 为 4.521101 / 10 CNY，包含未知预留；不是实际已确认收费合计。

最小修复：临时独立 localhost 端口、直接 Node/Next CLI、自有 PID 退出检查、捕获 request ID 检查及 native payload snapshot、异常缺 usage 保留预留、只停止本轮服务。成功本轮 PID 57276 / port 56956 退出且无监听；旧服务未被终止。

有限异常边界：进程清理或 manifest 写入自身异常可能留下 `PENDING` 而尚未执行 settle；预留仍占用预算，不得报告已结算或零费用。该边界不被此次正常成功运行覆盖。

## 验证范围

- `test_cnw_role_inputs.py` 11、`test_cnw_adapters.py` 11、`test_cnw_generation.py` 22、`test_cnw_runner.py` 22：最终 66 项通过。
- runner 并行测试首轮发生 Windows 临时 mock ledger `os.replace` WinError 5，保留失败记录；独立复跑 22 通过。未操作 live 账本或手改测试结果，不宣称该偶发原因已被修复。
- `git diff --check` 通过（Windows 正常 LF/CRLF 提示）。

源、真实请求、Brief 实际功能及下一消费者由独立只读 Controller 审阅。此次只关闭上述输入/消费缺口；不代签 C01–C15 完整等价，不证明新全链 Prose/Lens，不证明全部角色×时点×分支状态自动推理，不记 `USER_CREATIVE_ACCEPTED`。

## 独立只读 Controller 结论

2026-10-11：**限定 ACCEPT**。已核实际请求四份补充 Canon 和固定模板、真实 Brief 的当期知识/关系限制/连续时间及行动指令、原样产物解析、两条下游输入与禁网络复用。可关闭本次限定输入/消费缺口；历史 Plot/Cards 的设计限制、新 Prose/全链、全部时点/分支推理不在本次签收范围。运行异常、未知费用和临时账本偶发错误继续保留。
