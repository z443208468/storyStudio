# StoryStudio 计划编制规范 G1 — 禁止AI自行设计创作流程

**效力：仅在 G00 Controller 批准后生效。** 本规范约束包括ChatGPT在内的所有后续方案作者、Codex和它的子智能体。原版工具和原版工作流不受本文件“修改”，本文件只限定我们有权部署、集成和校验的内容。

## A. 计划输入：必须现场读，不接受记忆替代

1. **本仓库活动状态**：实际远端main SHA/tree、本地 HEAD/untracked、当前已接受Atom和最近一条用户约束/委托消息，以及当前有效的 Controller 委托范围。
2. **MVP治理范式**：`z443208468/mvp@perf/r667-migration-20261008` 的根 `AGENTS.md`、`docs/governance/GOVERNANCE.md` 与 R66.9 `MASTER_PLAN.md`、`STRICT_SEQUENCE_AND_BUDGET.md`、`CODEX_START.md`。使用其“规则机制”而非复制EMA业务合同或R66.9的AT号/130检查项/27业务真值到StoryStudio。
3. **原版创作工作流**：`MintoTsukino/claude-novel-workflow@97ad71fe...` 的`docs/ARCHITECTURE.md`、`docs/EXISTING_PROJECT_IMPORT.md`、`docs/GETTING_STARTED.md`、`docs/HOW_TO_ADAPT.md`、`docs/THREE_LAYER_REVIEW.md`，及`templates/_workflows/`和对应`templates/{04_chapter_design,05_scene_cards,06_plot,07_draft,08_review,09_revision,90_canon,92_style_engine}/`文件的原字节。不得用你我之前的总结替代原文。
4. **原版工具**：NK 的README、package.json、`lib/openaiServer.ts`、实际API Route和YAML；CritiCS的README、requirements、`critics/plan/plan.py`、`critics/text/text.py`、`critics/setting/chatsetting/gptsetting.py`和promptDesign。源码中的模型硬编码和坏语法是要先实证的真实部署障碍，不能隐去。
5. **原作唯一源**：由Codex在当前Windows用户的Downloads里实际定位并哈希匹配的`JUN-SINGLE-02.3`，不能把文件名或过去的一份ZIP“好像存在”写成事实。

每个输入都登记 `source_id`, `repository/url`, `source_sha/tree/blob`, `relative_path`, `read_scope`, `observation_time`, `FACT/INFERENCE/UNKNOWN`, `impact`。历史文档必须标 `REFERENCE_ONLY`；没有真下载包时写 `NOT_OBSERVED`。

## B. 三源证明：每一个行动都必须有授权

```text
FOR every imperative sentence, task, tool call, prompt, API parameter,
    output condition, selected model, generator count, reviewer count,
    file overwrite, stage transition, retry, quality rubric:
  determine type:
    IF directly prescribed by pinned upstream actual document/code: UPSTREAM
    ELSE IF directly specified by user/Controller: USER
    ELSE IF forced by immutable I/O contract or safe runtime integration: ADAPTER
    ELSE: UNAUTHORIZED -> REMOVE, or BLOCKED_FOR_CONTROLLER_DECISION
  attach exact source path + meaningful location + actual affected code/diff.
  IF labeled ADAPTER but alters story decisions, plot structure, persona,
     evaluation rubric, generation stages, or hidden model choice:
     B01/B02/B03 -> ABSOLUTE_FAIL.
```

必须输出 `reviews/PLAN_PROVENANCE_MATRIX.md`：每行`item_id, action, source_type, exact_path, source_commit/blob, evidence_excerpt_or_line, requested_change, affected_owned_file, impact, reviewer_verdict`。空来源或“原作者的理念如此”不可当作授权。任何后续新增要求先回查此矩阵的行号；禁止事后补编来源。

## C. 计划不可自定义的项目

- 不创建六固定插槽、`PURE_FUN=3`等配比、24候选或任何新数值作为创作契约；用户只授权首轮**一场完整的小戏**。
- 不自动为每场新增五个Reviewer、每条意见另三次反驳；这套扇出是 CNW 用于其**完整章节/批次**的已定义审稿方法，不是首轮一场试写的必须自动全量执行权。
- 不自行设定 Flash Pro、GPT替代方案、`max_tokens=2400/2500`、文学字数上限/生成轮次/高额预算。原版程序本身写死的参数只如实列作“原版限制”，不得修改也不得擅自照搬到你的自有调用。
- 不能把“把原作者工作流MD落库”视为完整运行证明；不能把“原版源代码Clone成功”视为Flash兼容。
- 不能把旧与新文档同时设为活动。旧S00–S09 / AT00–AT15仅历史分析，**禁止执行**。
- **绝对不准修改第三方原代码、工作流、prompt、锁文件或配置**。即使只有一行语法错误或者模型名不匹配，也必须当事实阻塞报告，不允许叫作无害机械修复。

## D. 真正的因果目标、验证方法、证据独立性

计划编写时每个Atom写清：

```text
ATOM_ID / DEPENDS_ON / SOURCE_PINS / OBJECTIVE / CURRENT_FACTS
INPUT_ARTIFACTS / OWNED_WRITE_SCOPE / IMMUTABLE_READ_SCOPE
EXACT_WORK (commands or close-to-executable pseudocode)
EXPLICIT_FORBIDDEN_CHANGES (B-IDs)
EXPECTED_USER_OBSERVABLE_FUNCTION
RAW_EVIDENCE_PATH / INDEPENDENT_ORACLE / REVIEWER_PROMPT
EXACT_STOP_CONDITION / CONTROLLER_GATE
```

**成果优先于基础设施**：必须说明“用户能够看到什么真实效果”，否则不得设新Atom。例如 `npm build success`只能证明构建，不证明 NK 真写出对当前Scene Card忠实的可用视角；`CritiCS`计划提纲不能证明日常喜剧有趣；Flash返回字数/用量不能证明文本感情成立。

独立校验不能从被测Generator自产“正确答案”再用它自己打分；Canon正确性必须对照2.3源文、原始人物已知/未知时间线和合法可观察行动。好不好看是用户最终裁定。审查记录中分开：`FACT`（见源/实际响应）、`INFERENCE`（有依据推导）、`UNKNOWN`（缺原件）；风险要明示条件、成本与其他可能解释。

## E. 只锁定当期目标，单一Atom逐步交付

采用 MVP R66.9 的严序机制，但不照抄它的Atom内容。每个Atom：

```text
LOAD_CURRENT_STATE_AND_ACCEPTED_PARENT()
VERIFY_GIT_WORKTREE_NO_UNAUTHORIZED_CHANGES()
VERIFY_CURRENT_ATOM_ONLY()
CHECK_B01_B14()
IMPLEMENT_ONLY_OWNED_CHANGED_FILES()
RUN_ACTUAL_PRODUCER_AND_CONSUMER_RELEVANT_TO_CURRENT_GOAL()
PRESERVE_FIRST_FAILED_RAW_AND_SUCCESS_RAW()
FREEZE_PRODUCT_INPUT_OUTPUT_PLAN_SHA()
READ_ONLY_REVIEWER_MESSAGE()
NORMAL_PUSH_AND_REMOTE_READBACK()
CONTROLLER_ACCEPTS_EXACT_COMMIT_TREE()
SET_NEXT_ATOM_ACTIVE()
```

计划制定完成仅意味着有“施工合同”，不是 Atom接受。Reviewer不能改写代码、运行测试或者自行成为 Controller；仅用户明确委托的本任务专用验收子智能体可在委托范围内签收 Atom 并要求纠偏，用户保留最高权威。

当已发生的真实缺陷能在当前Atom以自有代码、可逆且不修改第三方的纯传输修复闭合时，允许Writer当场修复，不需每次向用户追问路径问题；越过用户禁令、引入新故事方法或必须改第三方时 B01/B02/B10/B11 当场停。**不增加额外通用异常恢复框架、工作流引擎、黑盒自动签收平台。**

## F. 一次性策划审计的高影响面

独立Reviewer签发计划前至少核查以下重要面（适用时报告，非业务不适用项标`NOT_APPLICABLE_WITH_REASON`）：

1. 目标与原作者方法的同一性；原版MD有无实际可执行程序；适配是否已另造工作流。
2. 版本身份：远端真正空仓库、MVP活动治理分支、三上游 pinned commit、下载包字节和用户Key路径。
3. 所有权与目录隔离：upstream只读、owned代码、输入原件、临时运行、证据、公开Git；不能双权威/影子Canon。
4. 模型/Endpoint/API：原版硬编码是否真的能在不改源的环境下连接Flash，服务端返回型号可否证明；不能臆测SDK环境参数生效。
5. 平台和依赖：Windows/Node/npm/Python版本、Linux/WSL/CUDA、原版代码能否编译启动；缺哪个原硬依赖，缺证据则不可宣称兼容。
6. 输入与知识：32锚点、前后位置、J19–J32玩法、君天离唯一POV、秘密揭露、原设定延续与推测不自动升Canon。
7. 创作效果：原版Plot/Scene Cards/Brief是否实际喂给生成；工具返回内容是否在样本起作用，是否是可演出的完整一场。
8. 工程安全：读写权限、原始失败保留、API Key只在进程、无公开原稿、无网络监听公网、子智能体只读。
9. 成本控制：单场样本与完整章节扇出不是一回事；真实请求量、retry、在途结算与预留可分清；不把旧$12当授权。
10. 验收身份：Reviewer的独立证据、用户的明确 Controller 委托及其范围是否真实可查；Controller 是否对精确 commit/tree 签收；有没有脚本自签或自动下一阶段。
11. 法律与来源：CNW CC BY 4.0许可范围和故事示例非授权；NK/CritiCS MIT归属；用户原作版权状态不能凭存有ZIP自动认定可商业发行。
12. 失败归因：原版技术障碍 vs 自有适配错误 vs 无需代理的环境问题 vs 故事质量不达标，分开给证据。

只报告导致错误工程判断、版权泄漏、费用超支或创作效果无法成立的大问题；可逆路径/编码/格式机械问题在当前Atom修即可，不要求Controller批准每一个拼写。

## G. 规划结果必须经过独立审查才能执行

Reviewer应直接读上游原文与所有现行计划，抽样不是完整覆盖；逐条给：`SUPPORTED / UNSUPPORTED / UNVERIFIED`，附具体行与反例。若发现B01–B14任一条，报告 `ABSOLUTE_FAIL`；计划作者不能修改Reviewer标准来求通过。

**首次质量阶段只允许一次独立完整小场景**，写完样本就停。不得自动运行原作者的多话批量生产。技术结果和用户审稿分别验收，用户还没读样本时质量为 `CONTROLLER_REVIEW_REQUIRED`。
