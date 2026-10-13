# R5 按顺序重新收口准备 — 2026-10-13

性质：项目所有者要求的准备记录；不签实现，不启动施工，不改写历史裁决。

## 1. 最终目标与活动计划

最终目标：用户交付输入包并从正式应用入口启动；程序自行处理格式和内部项目/合同/Run/来源身份，完整保留并匹配要求和材料，交给合法 CNW 岗位，真实生产、审查、必要修订、复审并导出清单中的全部故事任务。更换输入包不得要求改源码；用户不手填 SHA 或逐阶段拼装。工程验收与用户创意接受分开。

活动计划仍为 `plans/MASTER_PLAN_GENERIC_APP_R5.md`，准备版 SHA256：`59459D839780C8B5D729AF81F3805CBFA63E6582F283EC7D725D48C36FDBFF3D`。

- 原 §0.3a 已覆盖实际包生产/交付，新增 §0.3b 将正式入口、逐要求消费者、全部任务、真实回执与导出、已接受功能回归明确列为最终硬门。
- 新增 §1.1 要求逐 Atom 当期全部适用门收口、冻结原始证据、Controller 明确下一 Atom 权限；局部接受不能覆盖其余当期硬门，后续退化须停止推进并修复。
- `AGENTS.md`、`GOVERNANCE.md`、`README.md`、`CODEX_START.md` 的计划 SHA 已同步；`reviews/CONTROLLER_PROMPT.md` 增加 R5 当前规则，旧 P2 内容保留为历史。
- 明确后置的完整集成/实际故事门不提前替代早期 Atom 的当期门。迁移、TS 恢复、Live 与危险切换仍独立受控，不能利用局部签收越界。

## 2. 已发现的真实签收链

核对基线 C=`137e22c8610e4acfb1e97c8d1ad34da6f1c9bc05`，T=`72c71528fdedc0009d885bcd036321cc4a43ade9`；本地 main 与此前远端回读一致。

下表是原始裁决的事实索引，不是 Writer 对当前新增范围的代签。不能仅看仓库内旧 RETURN/WIP 就否定仓库外的后继 ACCEPT。

| Atom/范围 | 原始独立裁决与冻结身份 | 当前准备判断 |
|---|---|---|
| 00 现场基线 | `/root/governance_reader` 2026-10-11 最终 ACCEPT；零代码阶段，基线 `26b72cea` / `535496ba`；ACL 补证后的消息为原会话 line640 | 历史阶段已接受；不把它说成现今功能或迁移已完成 |
| 01 实例/路径基础 | 同一原 Controller ACCEPT：`736b41138f83096637076dfa2c2dcc03455bb202` / `e9d2a2062ef68e2b956d577cb2696a4b1b3ed9e9`，line955 | 历史阶段已接受；按影响范围保留回归门 |
| 02 策略/历史身份 | 同一原 Controller ACCEPT：`a00eb1a625f32dc7f0c527b286cbcef31543b794` / `69d6e9e6c607d82d43382b34b1dcf78bd2ac94db`，line1210 | 历史阶段已接受，仍是影子配置范围 |
| 03 来源/意图 | 原 Controller ACCEPT：`77ab5f7ac401ec5606fee33b76c8ec4e5535cf31` / `2a79432589761afa01310fac6edb4c48095fb357`；后继包修复 `34955bd` / `0e1f5210` 有 ACCEPT_LIMITED | 不能沿用旧 `4ec76a9` RETURN 标题断言修复未接受；新增完整消费者与产品门仍后置 |
| 04 CLI/包入口 | 原 Controller ACCEPT：`bcbc9eff28ce836120e44226d1d744f64f7aa432` / `d4a40b3df27b0ce15afb0e4437e108d7f235cd7b`；包准备入口 `2b4dcd0` / `847cc552` 有限定 ACCEPT；显式模式 `4efa777` / `66ef287d` 有 ACCEPT_LIMITED_FIX | 当期已接受增量有原件；生产包整体完成仍须 05/06/07/09 等门 |
| 05 当前新增工程门 | `137e22c` / `72c71528` 费用缓存修复限定 ACCEPT；同一 Controller 后续明确 `ATOM05_CURRENT_ENGINE_VERDICT=RETURN` | 当前整体当期范围未收口：正文/索引晋升的中断恢复，以及 NK/CritiCS 实例费用、共同槽位和父 Run 结果回读 |
| 06～10 | 各自历史 ACCEPT/RETURN 与离线证据保留，包括旧精确树 `8e5f787` 的限定离线 09 接受 | 此次不施工、不整体重签；新增依赖只能按当前顺序到达后核验，不提前开启 |

原消息提取目录（仓库外，不含密钥或故事原文）：

`D:/CangqiStudio/StoryStudio_R5_Restart_Preparation_20261013/controller_originals/`

源文件、记录行号、时间、原 JSON 和消息文本 SHA 见同目录上级 `controller_source_index.json`。每份提取保留原文，不修饰裁决。独立子智能体来源由原始 session metadata 识别。

后继包修复原件另外位于：

- `D:/CangqiStudio/StoryStudio_R5_InputPack_20261013/controller_34955bd_accept_transcript.md`
- `D:/CangqiStudio/StoryStudio_R5_Atom04_Pack_20261013/controller_2b4dcd0_accept_transcript.md`

## 3. WIP 保留与重启边界

现有 8 个未提交源码/测试文件属于 ATOM-05 WIP，尚未接受，均保留原位，并逐字节复制到上述准备目录的 `before/`；路径、大小和 SHA 见 `before_manifest.json`。六份本轮 ATOM-05 原始测试输出一起保留；最新为 49 passed、1 failed、3 subtests passed，失败是适配器引用 `critics_bridge` 未定义，不能声称该 WIP 测试通过。受保护未跟踪 slot 锁只读取哈希，不改写、不暂存、不删除。

此次只修改计划/执行入口/准备记录。不修上述源码错误，不继续任何 Atom 的实现测试；不提交、不推送、不读 Key、不调用 Provider、不迁移或恢复私有项目，不修改冻结旧基线。

正式重新开始时，先由 Controller 确认前序当期范围和冻结基线均有适用证据，再执行它明确批准的最早未收口范围。每个 Atom 的全部当期门通过、独立精确 C/T 接受及需要的推送回读完成后，才申请开启下一 Atom。不能把准备 ACK 当作实现 ACCEPT。

## 4. 独立准备复核

`PLAN_PREPARATION_VERDICT=ACCEPT_PREPARATION_ONLY`

`FINAL_PRODUCT_GATE_VERDICT=HARD_GATE_DEFINED; IMPLEMENTATION_NOT_ACCEPTED`

`SEQUENTIAL_FREEZE_ACK=ACK`

`PRIOR_ATOM_EVIDENCE_STATUS=VERIFIED_HISTORICAL_ACCEPT_FOR_RESTART_REFERENCE`

`EARLIEST_UNCLOSED_ATOM=ATOM05`

`CURRENT_ATOM_CLOSURE_VERDICT=RETURN`

`NEXT_ATOM_PERMISSION=WITHHELD_PENDING_USER_START`

`SUBSEQUENT_ATOM_PERMISSION=DENIED_UNTIL_CURRENT_ATOM_CLOSED`

`GIT_PUSH_AUTHORIZATION=NO`

`GIT_STATE=PREPARATION_NOT_COMMITTED_NOT_PUSHED`

`INPUT_PACK_TO_STORY_GATE=RETURN/NOT_RUN`

`GENERIC_LIVE_PRODUCTION=NOT_RUN`

`CUTOVER_BLOCKED=true`

原始独立裁决：`D:/CangqiStudio/StoryStudio_R5_Restart_Preparation_20261013/CONTROLLER_PREPARATION_VERDICT_VERBATIM.md`，SHA256=`7cf9195de8026462d8698c45260022ae5f794622ff7b976129d4500d863762dc`。原始消息 JSON、时间和记录位置见 `controller_preparation_reference.json`。

Controller 接受计划 SHA `59459D839780C8B5D729AF81F3805CBFA63E6582F283EC7D725D48C36FDBFF3D` 的准备文本，核实前序原签收可作为重启参考，确认当前最早未收口为 ATOM-05 的上述两项工程门。它没有接受源码 WIP、当前全部产品功能或推送，也没有授权继续施工。

独立复核时的七份文档原字节与检查表保存在准备目录的 `as_reviewed/` 和 `preparation_check_v2_as_reviewed.json`。本节是收到裁决后填写的结果索引，不能冒充 Controller 对新源码候选的签收。

准备完成。Writer 现在停止并向用户报告“已准备好”，等待明确开始指令；不得自动开始源码施工。

## 5. 准备停止后的用户重新开始指令

项目所有者随后明确指示“现在按照顺序继续执行”，并再次要求 Controller 完全验收当前 Atom 后才能开启下一 Atom、必须证明实际预期效果。上节停止已履行，原准备裁决保持不变。现只恢复 ATOM-05 的授权返修范围；先将准备文档形成单独精确候选并交 Controller 审查，再修复、验证和独立验收 ATOM-05。这不解除后续 Atom、Live、TS 恢复或 cutover 门。

准备阶段原始裁决的公共脱敏原文副本：`evidence/R5_RESTART_PREPARATION_CONTROLLER_20261013.md`；其内容仍是准备接受，不冒充此后候选的推送许可。
