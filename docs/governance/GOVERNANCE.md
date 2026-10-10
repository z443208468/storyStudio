# StoryStudio 工程治理 G1 — 黑名单、不可变上游、逐 Atom 独立接受

## 00. 生效与证据性质

- 当前：`PROPOSED_NOT_ADOPTED`。必须经过 G00 的独立 Reviewer 与 Controller 后才能变成活动治理。Controller 默认是用户；用户可在本任务中明确委托专用验收子智能体逐 Atom 签收和要求纠偏。没有事后补签。
- 用户目标：**从真正空仓库开始**，先建立治理，再取得原版开源工作流与原版工具，安装/核实并用于《苍歧》真实的**一场**最小日常质量实验。原版第三方程序和工作流**一行一字节均不得改**。最终判断不是“接线成功”，而是用户可读到内容并判断是否达到效果。
- 项目治理参考：MVP 活动分支 `perf/r667-migration-20261008` 的根 `AGENTS.md`（标注 R66.9）、`plans/packages/G3BB_R66_9_ARCHITECTURE_EXECUTION_20261009/{MASTER_PLAN,STRICT_SEQUENCE_AND_BUDGET,CODEX_START,REACCEPTANCE_RUNBOOK,FUNCTIONAL_ACCEPTANCE}.md`、`docs/governance/GOVERNANCE.md`。该仓库业务专属的 EMA/Host/PFValueKernel 等条款**不移植**。移植的是黑名单原则、作者与验收权分离、原始证据、Atom 顺序和远端读回；所有新增禁令由本次用户明确授权，不冒称 MVP 原有原文。
- 源状态以当前本地和远端现场核对为准。2026-10-10 查询 `z443208468/storyStudio/main` 为提交 `06c66de7c7f18263039ea19a47e84c29716cde4b`、**empty Git tree** `4b825dc642cb6eb9a060e54bf8d69288fbee4904`。这是远端事实，**不能据此声称本地 D 盘无未跟踪数据**。若用户继续调整 main，以现场值为准，任何基线变化只报告，不自动重绑定。

## 01. 五层权威 / 唯一可写责任

| 层级 | 权威来源 | 谁能修改 | 禁止误用 |
|---|---|---|---|
| H：用户约束 | 用户当前显式要求和 Controller 消息 | 只有用户改变 | 不得以“工程需要”解释成授权了新创作步骤、昂贵模型、调用数量、预算或第三方修改 |
| U：原作 Canon | 经 SHA 确认的 `JUN-SINGLE-02.3` ZIP 的场景、玩法执行合同和公开/私有角色知识 | 本项目不得修改输入；用户另授权版本变更才更新输入指针 | 不能把生成推断或新想法写成原著事实；J19–J32不能被强制线性化 |
| V：第三方权威 | 3个原仓库按 Git SHA 固定的源码、原版说明、配置、模板和 Prompt | **所有角色均不可改** | 不能在拷贝版修补原函数/参数、改Prompt或“换个新服务”冒称原项目原样运行 |
| O：自有工程 | 本仓库治理、计划、仅输入输出/协议/路径转换的适配、测试、作品私有工作区 | 唯一 Writer 在当前 Atom 与精确写范围内；Reviewer 只读 | 自有适配不能成为第二套创作算法或改变原版调用语义 |
| E：证据/签收 | 原始请求响应、Git树、源码哈希、命令退出码、用户认可 | Writer只追加记录原始事实；Reviewer消息独立判断；Controller拥有接受权 | 不改写失败、不合并不同身份样本、不自签、不把截图/HTTP200/评分冒充读者效果 |

权威冲突顺序：`H > U > V > O`；E 只记录事实，不得反过来授权行为。U 不是 V 的许可：原作者CNW的示例小说另受著作权保护，禁止公开复制入库；可引用上游链接核对结构。

## 02. 角色与权限（与MVP R66.9实际机制对齐）

```text
ROLE_CONTROLLER = USER_OR_EXPLICITLY_DELEGATED_ACCEPTANCE_SUBAGENT
ROLE_WRITER = CODEX_ROOT_ONLY
ROLE_REVIEWER = ONE_DEDICATED_INDEPENDENT_MESSAGE_ONLY_READ_ONLY_SUBAGENT
REVIEWER_CAN_WRITE = NO
REVIEWER_CAN_EXECUTE_TEST = NO
REVIEWER_CAN_DELEGATE = NO
DELEGATED_REVIEWER_CAN_SIGN_FOR_CONTROLLER_WITHIN_EXPLICIT_SCOPE = YES
WRITER_CAN_SELF_SIGN = NO
ONE_ATOM_FULLY_ACCEPTED_BEFORE_NEXT = YES
OVER_NIGHT_AUTORUN_ACROSS_CONTROLLER_GATE = NO
```

- Writer 负责所有命令、文件、实现、测试、普通提交和远端读回。Reviewer 根据 Writer 提供的**精确源文件、实际 diff、raw 和远端响应**独立判断，不能照搬 Writer 自评，也不能伪称亲自执行。
- Controller 批准/驳回 **每一个 Atom** 的具体候选和证据。默认由用户签收；用户明确委托的专用验收子智能体可在委托范围内以 `ACCEPT` 解锁下一 Atom，或以 `RETURN` 要求当前 Atom 纠偏。委托不授权扩大用户给定的创作、模型、版本、预算、第三方不变性或样本范围；用户保留最高权威并可改变约束或撤销委托。
- 若Codex不能实际建立独立只读子智能体，则当前任务不得假装已经分离；报告 `B09_REVIEWER_UNAVAILABLE`，不进入下个 Atom。不得用同一主执行AI的另一个聊天窗口“自我复核”充数。

## 03. 唯一硬停黑名单（B01–B14）

**这是仅有的正式硬停归类。普通机械错误和可逆接线故障不另立停止规则，不制造白名单/成功清单来反向限制合法修复。触发任何 B 条后，只允许保存 raw、给出原因与最小复核输入；不得调用另一个“更聪明模型”、修改原版、绕过审查或悄悄继续。**

| 条款 | 必须阻断的事实 | 当场留下的原件 |
|---|---|---|
| **B01 未授权架构/创作决定** | 加入原作者与用户都未授权的新阶段、Story Agent、叙事配比、6槽、24候选、创作算法、评分标准、自动多轮审稿、额外基础设施；假借适配名义重写故事生成逻辑 | 代码/Prompt具体行、USER/UPSTREAM来源对照、diff |
| **B02 第三方被改** | 第三方 Git 跟踪源、配置、依赖锁、Prompt、工作流文档有任何字节变化；替换函数运行实现、动态monkeypatch改变原库创作算法、自己维护“兼容 fork”作为生产工具 | 原Git SHA、`git status`、blob/hash差异、发现时的原命令 |
| **B03 第三方方法冒名** | 只克隆不执行却写“使用成功”；本地另写同名批评器冒称 CritiCS；修改结构/结尾/原创性维度；只用人工总结代替原工作流 | 实际调用栈、源代码入口、请求输出与声明对照 |
| **B04 原作事实/身份错用** | 找错ZIP、擅自用旧仓库正文代替2.3、偷改Canon、NPC读心、提前泄露秘密、把固定场景和行动驱动分支混淆 | ZIP完整SHA、场景依据、越界文本与定位 |
| **B05 模型/供应商越权** | 任何外部请求出现非用户批准的DeepSeek模型（只允许 `deepseek-flash`）；使用GPT-4/3.5或Pro作为创作付费后端；暗加2400等模型调用输出上限；修改Endpoint/密钥安全策略无证据与授权 | 发往供应商的请求实际字段、返回 `model`、finish_reason、用量 |
| **B06 阶段/规模越权** | 未获Controller当前 Atom 接受就施工下一 Atom；第一次验证从1场扩大为Episode、第二场、多篇Sprint或批量多透镜审核；自动恢复旧计划 | 计划实际指针、执行命令、运行次数、未签阶段 |
| **B07 禁止破坏Git/用户数据** | reset --hard、git clean、rebase、force-push、未经许可删除C盘旧目录、覆盖现有WIP/输入/已保存raw、改变历史签收 | Git状态、差异、完整操作对象 |
| **B08 证据伪造/污染** | 把成本预留写成费用；旧历史绿点冒充新运行；删除失败；把工程HTTP200/单测通过冒充故事好玩；原始收据字段回填想象值；制造自签报告 | receipt、provider字段、时间/身份/sha、未经验证项 |
| **B09 审核身份失效** | Reviewer可写、运行测试、委派、付费、与Writer同体自签；Reader不读实际源码和原始结果直接放行 | 审核者身份与消息、输入快照、可读证据 |
| **B10 来源冲突/缺口需授权** | 精确原版 Git commit/2.3 SHA 不一致，或需更换上游版本、允许第三方修改、改变User要求才能继续；原版不支持Flash却擅自改它 | 仓库/包实际SHA、冲突代码、原版合同与可选方案 |
| **B11 兼容性无法原版运行** | 原版程序无法解析、安装/运行依赖不满足、硬编码目标模型/Endpoint而现有未经修改的接口机制无法使用Flash；故障需改第三方代码/语义才能修 | 原版文件与行号、实际启动错误、最小失败命令、设备/网络条件 |
| **B12 隐私与许可** | 密钥原文或《苍歧》整包进入公开Git、外发未授权文本、把CNW受保护示例小说复制公开或并入产品、生成含密钥日志 | 脱敏路径、泄漏影响边界、检验记录，禁止传播密钥值 |
| **B13 真实功能效果无法证明却宣布完成** | 明知工具未实际进入样本调用链、故事缺开端/角色行动/事件落点或前后连读、跳过Controller真实阅读却宣称创作质量合格 | 样本路径、上下游链路、实际未执行字段 |
| **B14 不可消解的计划事实前提错误** | 实际源码否定重要前提，继续只能自行发明缺失事实、设备能力、价格/参数或未经批准的适配权 | 来源代码/官方说明、FACT/INFERENCE/UNKNOWN划分、阻塞的具体结论 |

`B11` 是本项目新增的明确工程事实冲突，不是授权修复开源源码。一次检测发现确实有原生不兼容，就可以结论 `BLOCKED_UPSTREAM_IMMUTABLE` 并结束**当前 Atom**；不能拿技术替代品悄悄消解。

## 04. 黑名单处理与机械恢复

```text
ON_ISSUE(issue, atom):
    SAVE_RAW_ONCE(issue.command, issue.input_identity, issue.stderr, issue.exit_code, issue.source_refs)
    match = MATCH_B01_TO_B14_WITH_FILE_LINE_AND_EVIDENCE(issue)
    IF match:
        APPEND_BLACKLIST_EVENT(atom, match, exact_paths, ref_shas, raw_ids)
        FREEZE_CURRENT_CANDIDATE()
        SEND_TO_REVIEWER_MESSAGE_ONLY()
        HANDOFF_TO_CONTROLLER(); RETURN_STOP
    ELSE:
        IF mechanical_reversible_and_owned_within_current_atom(issue):
            FIX_CAUSAL_DEFECT_ONLY(); KEEP_OLD_FAILED_RAW(); RETEST_AFFECTED_STEP_ONLY()
        ELSE:
            CLASSIFY_B01_OR_B10_OR_B14_WITH_EVIDENCE(); RETURN_STOP

END_ATOM(atom):
    FREEZE(own_code, active_plan, source_pins, input_hashes, test_commands, raw, candidate_commit_C, tree_T)
    SEND_TO_READ_ONLY_REVIEWER()
    IF reviewer_not_accept: RETURN_TO_SAME_ATOM
    NORMAL_NONFORCE_PUSH(candidate_C)
    WRITER_FETCH_REMOTE_SHA_TREE_AND_SOURCE(); SEND_RAW_READBACK_TO_SAME_REVIEWER()
    IF reviewer_not_accept_remote: RETURN_TO_SAME_ATOM
    REQUEST_CONTROLLER_ACCEPT(atom, C, T, evidence_ids)
    IF controller_not_accept: RETURN_TO_SAME_ATOM
    APPEND_CONTROLLER_ACCEPTANCE_POINTER_WITH_EXACT_USER_MESSAGE_REFERENCE()
    UNLOCK_NEXT_ATOM()
```

- `REVIEW_READY` != `REVIEWER_ACCEPTED` != `CONTROLLER_ACCEPTED` != `CREATIVE_EFFECT_ACCEPTED`。
- 报告中的字段不得用名为 `pass` 的真假键；记录 `status`, `raw_sha256`, `reviewer_message_ref`, `controller_message_ref` 和 `limitations`。未知为 `NOT_VERIFIED`，未发生为 `NOT_RUN`。
- 接受历史保存在**新增不可变记录**；若改动影响此前依据，按真实依赖回到最早受影响Atom重验，保留已失败/已接受证据，不把新证据覆盖到旧身份。

## 05. 计划编制者也是受限角色

- 规划 AI 不是 Controller，不得创造缺失的需求事实。所有设计行必须用 `UPSTREAM / USER / ADAPTER` 精确归属；如不属于这三类则删掉或标 `UNRESOLVED_CONTROLLER_DECISION`。
- 输出计划前，必须做 `docs/governance/PLAN_AUTHORING_STANDARD.md` 自检；自检仅表示“文档已检查”，**不能自己签独立审核通过**。
- 上游文档、Prompt、源码的拷贝/引用必须保持原字节与明确许可证；自有 `AGENTS.md` 不能作为“修改CNW工作流”的借口。Codex读原CNW模板执行创作，StoryStudio治理只约束工程、授权和不可变边界。

## 06. 提交和隐私

- 原版三仓通过**锁SHA Git子模块**引入，只提交 Git link / `.gitmodules` 与已授权许可材料；原版所在目录不写项目文件。子模块 checkout 必须干净；原版`git status --porcelain`任何更改皆 B02。
- 编译时：可从子模块 Git `archive` 复制**相同字节**到 Git 忽略的 `runtime/build/<tool>/<run-id>/`，仅这个独立工作区可产生 `node_modules`、`.next`、`__pycache__`、缓存；复制后必须以 Git 树文件身份对照，不能在测试镜像改业务源码。一切适配逻辑必须在本项目自有 `adapters/`，且满足纯传输。
- `inputs/private/`、`workspace/`、`runtime/`、`runs/`、API key/原始响应禁止提交；公开仓库存 `治理、source pins、可复现命令、脱敏结果、接受记录`。任何未经许可发到公网上的游戏原文，禁止因“验证方便”而提交。
- 下载目录只作为候选只读搜索路径；不得修改、清空或重命名Downloads内资源包。匹配包提取到私有工作区，保原始SHA和文件清单。

## 07. 真正的成果验收（不得缩成工程接线）

最终只有在全部必需工具的真实调用路径可证明**原版语义且零上游改动**时，才进行一场合法日常：前后原稿 → 原作者Plot/Scene Card/Brief → 君天离单POV完整对话/表演 → 实际NK与CritiCS结果 → 同场修改前后 → 独立Canon审查 → Controller亲读。每项用原始请求/供应商回复/代码与文字来源定位；若某原版工具不可达，**报告不兼容，不能降级成自己写的“等价”伪工具后声称全栈效果成立**。

最后的接受必须如实分别记：`ENVIRONMENT_VERIFIED`（环境）、`UPSTREAM_UNMODIFIED_VERIFIED`（原版未改）、`NATIVE_COMPATIBILITY_VERIFIED`（原程序真实运行）、`ONE_SCENE_DELIVERED`（作品）、`CREATIVE_EFFECT_ACCEPTED_BY_CONTROLLER`（用户认可）。在用户读前，最后一项必须 `NOT_RUN`。
