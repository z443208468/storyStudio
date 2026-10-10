# P3 原作者资料 → StoryStudio 当前代码 → 逐项施工矩阵

**P3.1 修订映射，取代 P3 原版同名矩阵。** 新增重点：M04 实际剧本导入、M03/W04 与 W06 职责分开、M31 离线章验证、M36 跨项目预算边界和正式用户调用。

**审查基准**：StoryStudio `main@939eca90c030cf726b1879e2b1115f0e07ed6f6c`；上游 CNW `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`。本表的 `Lxx` 是该提交下的行号，若实际本地已经推进，应以**函数名/搜索符号+源码 diff**定位并复用新增工作，不依据行号覆盖新内容。

**类型说明**：`KEEP` 现有正确能力要保留；`REPLACE_IN_PRODUCT` 从正式产品入口消除错误行为、保留原历史文件；`ADD` 新增作者方法对应模块；`INTEGRATE` 复用并接入已有功能。表中未来文件路径为**施工目标**，当前 GitHub 并不存在；未生成前不得称“已开发”。

## 一、当前已核实的代码缺口

| ID | CNW 原方法/源文件 | StoryStudio 当前精确代码 | 缺陷与对策 | 施工对象/验收证据 |
|---|---|---|---|---|
| M01 | 所有 `docs/`、`templates/`、生产手册 | `third_party/claude-novel-workflow` Gitlink 已 pinned | 当前缺少真正的开发用**不可变本地参考清单** | `tools/capture_cnw_reference.py`：复制原文件到 Git 忽略目录，输出 SHA256/blob 身份；`tests/test_source_snapshot.py` |
| M02 | `templates/config/workflow.template.yml` 全 11 阶段 | `tools/studio.ps1:4–9` 只接受 `scene/verify/export/...` | 无通用生产驱动命令、无作者阶段状态机 | 新 `tools/cnw_runner.py`；`studio.ps1` 调度 `produce/step/review/promote/export/resume`，旧命令保留为 `legacy-checkpoint` |
| M03 | `templates/config/ai_roles.template.yml` 四个正文生产岗位 | 现有仅一次性 `tools/p2_06_draft_run.py` | 缺 Plot/Card/Brief 岗位运行与 Prose 岗位合同；W04 完成前三岗执行与 Prose I/O schema，W06 才实现 Prose 真正生成，不在 W04 验收要求未写的 W06 代码 | `tools/cnw_roles.py` + `spec/CNW_ROLE_INPUT_OUTPUT.md`，每岗明确 source_paths、artifact、required fields、provider call ID |
| M04 | `docs/EXISTING_PROJECT_IMPORT.md`、`_workflows/01_first_import.md` | `workspace/cangqi/90_canon` 已私有落地；`studio.ps1:115–119` 只验证特定 ZIP SHA | 已有《苍歧》导入成功；不能为新一部作品默认为 J19 专用根路径 | `tools/cnw_project.py` 实现 `project init/import-source`，从两个不同原始文本/JSON 剧本真正建立 source_manifest、source_index、90_canon 候选；`--ProjectRoot` 为私有工作区而非 Git 根，无法识别的格式明确报需适配；现有《苍歧》原位复用 |
| M05 | 作者 `project/arc/episode` 设计层 | `config/production.example.json:35–44` 仅 Sample ID/POV | 没有 Arc/Chapter/Scene 的生产单位身份与可计划角色 | `tools/cnw_contract.py` 定义 `project, arc, episode, scene`，Scene 可以是单独生产单位但不能伪装成整话 |
| M06 | `episode_production_manual.md:22–28,575–594` | `config/production.example.json:16–17` 中 `literary_word_count_target: null` | 无规模合同；脚本得以临时私设长度 | `config/cnw_production_policy.json` + 每件 `work_unit_contract.json`，默认不允许 null/0 生产；目标在 Plot/Card/Brief 三处传播 |
| M07 | `templates/06_plot/plot.template.md` | `tools/studio.ps1:134–138` 的 Plot 只是硬读 `ep001_plot.v1.md` | 只会读取旧样本，不会生产下一个 Plot | `tools/cnw_runner.py step plot` 读项目 Arc/Canon/源锚，调用独立 Plot Agent，产 `runs/<id>/06_plot/<id>.md`；不依赖 EP001 |
| M08 | `templates/05_scene_cards/scene_cards.template.md` | P2 有私有 `05_scene_cards/ep001_scene_cards.md`，公开 `studio.ps1` 无生产/复验动作 | 一张卡人工形成、无通用 Scene Card Agent | `step cards` 从 Plot 拆出 N 个场景卡，校核 start/end、beats、禁止、每场长度，附可靠来源 |
| M09 | `templates/07_draft/writing_brief.template.md` | P2 只出现已生成 EP001 Brief；公开入口无新 Brief 生成 | Brief 未绑定篇幅/场景节拍的不可改身份 | `step brief` 必须带 Plot+全部 Scene Cards+当前 Canon+项目声音；校验各段预算，记录冻结 hash |
| M10 | `templates/config/ai_roles.template.yml` Prose 的“仅读 Brief+声音” | `tools/p2_06_draft_run.py:10–11,21–24` | 只读 EP001 固定路径，另加临时 `500–700中文字符` 覆盖应由 Brief 确定的长度 | `tools/cnw_generate.py` 参数化 `--contract --run-id`；从冻结 Brief 提取长度/节点；禁止临时脚本硬编码 |
| M11 | 作者分场写作 + 分配长度 | `p2_06_draft_run.py:16–30` 使用单笔 `max_tokens=2048`，只检查 `stop`/非空 | 完整 episode/scene 可被 token 截断或严重欠产量，且没有机制补齐节拍 | `cnw_generate.py` 允许逐 Scene/逐节拍受约束生成＋定点续写；每段校验 char/beats/终点，预算不足明确 UNKNOWN/BLOCKED |
| M12 | Prose 只写完整正文 | `p2_06_draft_run.py:29–30` 检查了返回状态，未判目标分量 | `stop` ≠ 达到 Scene 卡要求 | `tools/cnw_contract.py validate_draft` 返回 `visible_chars/target_range/required_beats_evidence/scene_count`；任一重大欠产量 `RETURN` |
| M13 | CNW 本文与 NK 职责分离 | `tools/p2_06_nk_live_probe.ps1:55–69` 固定 EP001 的一个视角请求 | NK 已可用，但仍是一次性短采样 | `tools/cnw_nk_adapter.py`（薄参数包装）将**当前 Scene Card** 编成原 NK `generate-perspective` 接口，结果必须进入 Brief 对应段 |
| M14 | CNW 源方法允许新增 CritiCS 作为补充 | `tools/critics_bridge.py:99–145` 已提供 `plan-critique/plan-revise/text-refine` | 真实 CritiCS 可用，不要重写；但不能顶替 CNW 五 Lens | `tools/cnw_critics_adapter.py`（薄包装）复用 bridge 和原 `p2_06_critics_run.py` 的成本捕获；Plot 阶段与句段审阅有引用即可 |
| M15 | 独立的 Author Review 层 | `implementation/PRODUCTION_SPEC.md:P6` 只有有限 lint 与 Controller 主观检查；没有 5+3+1 的执行链 | 缺作者的方法实现 | `tools/cnw_review.py` 分出两层 lint、5 lens、3 verifier、completeness、revision、re-review；有真实输入/输出与失败说明 |
| M16 | `THREE_LAYER_REVIEW.md:23–36` L1 表层 lint | 现有 `tools/critics_offline_check.py` 是工具接线测试，不是文学 lint | 不应误用离线接口检查冒充文本审稿 | `tools/cnw_lint.py surface`：占位符、格式、重复标点等《苍歧》已批准中文规则，行号和来源可复验 |
| M17 | `THREE_LAYER_REVIEW.md:40–59` L2 带上下文 lint | 当前无该任务独立持久产物 | 不能只做单词删减或生硬自动修文 | `tools/cnw_lint.py structural`：命中句+邻接句，输出候选 `finding`，不直接删除正文 |
| M18 | Style Lens | 原 `Controller` 混合审查，没有独立 Style Provider 调用 | 不能伪称全套 CNW | `cnw_review.py lens --name style` 读 v0+style guide+语言规范，独立 session，报告节奏/密度/重复 |
| M19 | Character Lens | 原 `Controller` 检查 POV 与 Canon 但不是角色独立 lens | 人物声音、真实对话、关系台阶可能被弱化 | `lens character` 读 v0+character bible+voice samples+称呼表，按人物逐条报出处 |
| M20 | Plot Lens | 原 CritiCS Plot critique ≠ CNW 章 Plot Lens | Scene Card 必须动作/读者所得未逐条落实 | `lens plot` 读 v0+Plot+Card+Brief，逐 beat ID 记录 `present/absent/distorted`，缺关键节拍直接阻断 |
| M21 | Canon Lens | 原 Controller 已查知识边界，缺源引用覆盖标准化结果 | 不能用“剧本整体知道”把君天离不可知写进正文 | `lens canon` 读 v0+Canon+原稿前后锚及可知边界，按 claim 给源锚行号；未经锚定推断不升级事实 |
| M22 | Story-specific Lens | 原 `Controller` 只查安全、没有《苍歧》读者体验目标 lens | 很短、平淡、没有戏剧张力也能通过 | `lens story_specific`：按《苍歧》已定玩法/节奏/人物目标设定本场体验合同，检查具体小冲突、行为差异、读者获得与可演性，禁止照抄作者示例 JET 主角模式 |
| M23 | `THREE_LAYER_REVIEW.md:100–118` 五 Lens 彼此隔离 | 单一 Controller 消息不等同五个隔离审稿调用 | 若 Lens 共用聊天历史，会互相污染观点 | 每个 Lens 独立 API request/上下文，返回带 `lens_id`, `input_sha`, `request_id` 的 JSON；Controller 只汇总后签收 |
| M24 | `THREE_LAYER_REVIEW.md:108–120` 3 反证 verifier | 现有 CritiCS Inspector 不是该 stage | 不能直接把所有审稿意见全部当事实修 | 三个独立 verifier 见同一待判 findings（各有不同反证角度），默认不成立；≥2 个“未能反驳”才进入 Revision 队列；保留证据 |
| M25 | `THREE_LAYER_REVIEW.md:124–136` Completeness | 无遗漏补漏环节 | 审稿可漏掉“没有完整戏”等大问题 | `completeness_critic` 读完整正文+已确认/驳回问题，指出遗漏类型；按来源补入 issue queue，不可自签全链完毕 |
| M26 | `THREE_LAYER_REVIEW.md:140–148` Refine/Re-review | 当前仅 `tools/p2_06_revision_run.py:17–24` 一次无验证的全文修改 | 修订稿可从 993 B 缩成 469 B 仍成功 | `tools/cnw_revision.py` 逐 issue 修，必要时按 Scene 替换；后置 `validate_draft` + touched lenses 再审；不容无原因重大缩短 |
| M27 | `_workflows/03_revision.md` 的保护与晋升 | P2 直接从 `09_revision/ep001_v1.md` 导出 | 未落实“原稿→候选→经过接受→正本”的原机制 | `cnw_revision.py promote` 保留原 v0/v1，接受的修订稿晋升 `07_draft/episodes/<id>.md`，旧正本备份；不得改原作 Canon |
| M28 | `templates/09_revision/revision_plan.template.md` P0–P3 | P2 的 `classification` 只有一次性 EP001 文件 | 没有可复用、按严重性排序的修改队列 | `cnw_revision.py plan` 输出每 issue 的 severity、owner、source、fix、cost/依赖、验收后状态 |
| M29 | `example_project/00_meta/manuscript_review_rubric.md` Pass/revise/rewrite | P2 `implementation/ACCEPTANCE_SPEC.md:V13` 只要“无重大 Canon/POV 错、无占位/截断、有行动落点” | 没有**作品是否具备读者体验和分量**的否决条件 | `tools/cnw_quality.py`：致命伤优先，五 Lens 摘要，分数只作为项目尺度；受影响项须复评 |
| M30 | `docs/ARCHITECTURE.md` 每话正本与 manuscript index | `tools/studio.ps1:46–106` 固定 `deliverables/EP001/`，修改说明/锚点写死 | 只是历史样本重导出 | `tools/cnw_export.py` 从 run manifest 动态读取 ID、前后锚、v0/v1、问题单、成本，生成安全 HTML/TXT/MD |
| M31 | `templates/08_review/batch_review.template.md` + 5 话 Sprint | 当前无 `sprint` 入口 | 不能宣称“生产线按作者方法可批量运营” | `cnw_runner.py sprint` 支持 5 话排产、单话审稿后再 batch review、角色/Canon 分支状态汇总；先用五个不同 source/contract 的离线 fixture 验证，可签 `SPRINT_OFFLINE_ONLY`，不得据此声明批量 Live 成功 |
| M32 | `templates/_workflows/05_handoff.md` | P2 有状态和 acceptance log，但只对一个 EP001 | 无跨新 run 的可恢复状态，不能继承下一话 | `cnw_runner.py resume` 使用各阶段 hash+source identity+ledger，不重播已签收或已付费请求；`handoff.md` 只记当前项目真实成果 |
| M33 | 作者严格“单一正文正本” | P2 v1 路径 `workspace/cangqi/09_revision/ep001_v1.md`，没有通用 promotion | 改了源结果不能把旧审核原样签新稿 | Promotion 引用 approved review outcome 和源身份；写入 manuscript index 的 final_candidate / revised |
| M34 | 正确的工程入口 | `studio.ps1:120–132` 的 `verify -Mode live` 搜旧 ACCEPT 字样 | 把历史证据误当新 API 已调用 | 改为 `verify-history` / `verify-live --run-id`；前者只证历史证据，后者检查当前 run 的实际 provider ID、usage、请求/响应与成本摘要 |
| M35 | source→effect 可观测链 | P2 真正 NK/CritiCS 有证据，但初稿正文质量不达标 | 全链被签收时没有**过程出稿能力**预期值 | 每个 stage 产物含 input_sha、output_sha、source refs、provider request_id（模型阶段）、review grade、failure reason；Controller 不自报“内容成功” |
| M36 | 经费与供应商 | `tools/p2_cost_guard.py:20–22,34–40,125–179` 已建账本 | 不能再做一套账本；新调度必须复用现有预算逻辑 | 所有新增模型角色均 reserve→send→settle；首个 P3 真实场景沿用 P2 总 ledger 余额；将同一 cost_guard 参数化支持未来**经独立批准**的 campaign/ledger，未获新预算不得跨项目发付费请求，保留旧账本字节；同输入已付费优先复用 |
| M37 | HTTP 生成工具接口 | NK 的八条路由已上生产补丁；原 YAML 的 POV 叙事职责仍在 | 不能把 NK 的 200-word reflection 当一整场“正文” | `cnw_nk_adapter.py` 只生成 POV 材料，放入 Brief；Prose 另走 CNW 正文岗位 |
| M38 | 文学评分与用户签收 | `evidence/p2-07-delivery.json` 对小样本曾 `ACCEPTED_BY_CONTROLLER` | 当时的验收事实不改，但产品完成状态错误 | 新增 `PRODUCT_REOPENED`，保留历史 C/T、保留旧 EP001 作 smoke case；新 `PRODUCTION_READY` 必须实测新内容与新入口 |

## 二、文件级修改合同（最重要的执行入口）

### F01 `tools/studio.ps1`（保留已有 NK 安全管理功能，新增 CLI/Controller 边界）

- **保持** `Assert-Prepared`、`nk-start`、`nk-stop`、原 `doctor` 检查的安全语义，不重写服务生命周期。
- 改 `param` 顶部（旧 L2–10）：新增独立命令 `produce`, `step`, `review`, `promote`, `verify-history`, `verify-live`, `show-run`，及可选 `-Mode offline|live`, `-Unit scene|episode`, `-ProjectRoot`, `-Contract`, `-WorkId`, `-RunId`, `-Stage`、`project-init/project-import`；其中 `-ProjectRoot` 是 `workspace/<project>`，不得误用 Git 仓根。保留旧 `scene` 但输出 `LEGACY_CHECKPOINT_ONLY`，绝不可返回新生产成功。
- 改 L43–108：把 `Export-ReadingPackage` 的固定 `workspace/cangqi`, `deliverables/EP001`, `J19:555`, `J20` 和“纸张/灰尘”的固定说明迁到 `tools/cnw_export.py` 从 run manifest 驱动。旧固定导出可保留为 `legacy-export-ep001`，但不得成为默认 `export`。
- 改 L120–132：历史联调证明改名 `verify-history`；新 `verify-live` 必须按指定 run 的实际 request ID/使用 tokens/响应/资产 hash 检查，不能搜索 Acceptance 文本字符串。
- 改 L134–148：`scene plot|draft|revise` 只旧样本读取，新增独立 `produce` 真正调用 `cnw_runner.py`；已有 `resume` 可以适配新 run 结构，但**不得自行重发**。
- 安全：路径规范化、工作区边界、PowerShell 参数转发使用数组和显式退出码；每个非零退出保留原日志。所有命令在全新无 Key shell 下的非付费分支可复验。
- **完成条件**：离线两个不同 ID 的空 run 都产不同 artifact 身份；旧 EP001 查阅仍工作；NK 启停不退化。

### F02 `tools/p2_06_draft_run.py`（冻结为 P2 历史；新生产走参数化文件）

- **证据**：L6 `RUN_ID` 写死；L10 EP001 Brief；L24 强塞 `500–700中文字符`；L27 `max_tokens=2048`；L29 只检查 stop/非空；L30 保存 EP001。
- **施工**：不要篡改已通过 P2 的历史样本；新增 `tools/cnw_generate.py`，读取经过 Controller 冻结的 `work_unit_contract.json`、最新 Brief、已核准相关 `NK reflection`/角色声音，只用其中定义的 `target_visible_chars` 与 `scene_budget`，不得另加任意规模。
- 生成前，`validate_contract()` 确认所有 Scene 的分量、start/end、required beats 和稿件源 identity，输出 token 预算需能覆盖合同；不足则分 Scene/节拍定点生成而不是压缩整部故事。
- 实际 API：复用 DeepSeek Chat 模型/费用账本/私有请求记录；模型写作只接当前可知情报，原 `max_in_flight=1` 保留为默认。禁止把整部未披露后文直接进 Prose Agent 输入。
- 生成后：剥离 meta 文本、测 `visible_chars` 与 scene count、核查每个必需 beat 的文本证据位置和衔接，欠产量或缺动作就是 `DRAFT_INCOMPLETE`，不能保存为 PASS。
- **完成条件**：对旧 469 字节样本的合约验证报告拒绝作为 `TARGET_COMPLETE`；离线 2 个不同长度合同能驱动不同长度/节拍的正文模拟。

### F03 `tools/p2_06_revision_run.py`（冻结历史，产品修订改新模块）

- **证据**：L5 固定 Run ID；L8–10 固定 EP001；L17–18 禁止加细节的指令过强；L22–24 只检查响应/非空并写 v1，没有验证保留原作品的必要行为和完整性。
- 新 `tools/cnw_revision.py`：输入当前原稿 vN、确认证据的 review findings、P0–P3 队列、修订合同；根据 issue 修改而不是无条件重写、收短。输出 vN+1 与每 issue 对应补丁表。
- 对修改后稿与原合同双向审查：保留 required beats、读者体验节点、话语密度及长度；任何删除原先重要动作的修订必须提供由 Plot/Card 正式改变的证据；否则 `REVISION_REGRESSION`。
- `_workflows/03_revision.md` 原方法：修订稿先存 `09_revision/` 并保留旧稿，不要直接覆盖 `07_draft/episodes/`。Controller 对通过的 vN+1 独立审核，`promote` 才更新单一正本和 `revision_log`。
- **完成条件**：模拟恶意修订丢失 70% 字数/关键节拍时强制 RETURN；对于正当小修不会自动强制扩写、原 v0 不丢。

### F04 `config/production.example.json` + 新 `config/cnw_production_policy.json`

- 现 P2 `provider/cost_guard/nk/upstream` 栏保留身份与约束。旧 `literary_word_count_target:null` 作为历史 P2 模板字段不能再是正式新生产的唯一配置。
- 新 policy 至少：`scope_units:scene|episode`, `language`, `length_unit:visible_chars`, `scene_default_target`, `scene_min/max`, `episode_budget_from_scene_cards`, `require_frozen_card:true`, `require_preflight:true`, `critical_fail_policy:never_pass`, `review_pipeline:all_11_stages`, `sprint:5`, `no_unapproved_new_scene:true`, `quality_threshold`、同版本标记。
- 量化政策**来源性质明确**：原作者 5,000 日文字符是例子；中文《苍歧》试场提议目标 1,000 可见字符、核查 700–1,400 为**本项目初始适配值**，先对源稿邻近场景和可演目标做文件级证据比对再冻结；若与真实文本密度相悖，Controller 在初次写作前调整，不得事后缩小阈值救不合格稿。
- 章节目标由 Chapter Plot 的场数/每场目标**求和得到**；不要自动把作者日文 5,000 机械换成汉字 5,000，也不要把单个 Scene 冒充 Episode。
- **完成条件**：同一合同和 policy 计算唯一目标长度/输出路径；`null/0/missing` 立即失败。

### F05 `tools/cnw_runner.py`（新增生产主调度器，不做新的文学理论）

- 命令：`plan, cards, brief, pov, draft, lint, lenses, verify-findings, completeness, review, refine, re-review, promote, export, resume, report, sprint, run`，均明确所需输入。
- 唯一 Writer 顺序执行状态机；审稿 Lens/Verifier 是**彼此独立的模型任务**，不是额外拥有项目写权限的工程代理。文档源约定可按原作者配置使用并行；当前 P2 API `max_in_flight=1` 下采用**独立上下文的串行请求**，待统一费用并发锁能证明安全时再提升并发，不声称复刻了原作者的 96 分钟性能。
- 每个节点以 `run_id, step, input_sha256, method_ref_sha, config_sha, model, output_sha256` 生成缓存身份；已成功并符合 identity 的节点复用；旧结果必须因依赖变化而精准失效，禁止只用文件名判断缓存。
- 持久化 `runs/<id>/state.json` 和私有命令/原始响应；`step` 不得靠打印“已完成”而无产物。下一步只在自动合同 gate 通过后触发；正式 promote 还需独立 Controller/编辑者的具体审阅证据，脱离 Codex 执行时只能输出 READY_FOR_EDITORIAL_REVIEW，不得假装可以自动调用 `/root/g00_reviewer`。
- 用户最终的 `USER_CREATIVE_ACCEPTED` 独立于工程 Controller，绝不由模型代签。

### F06 `tools/cnw_review.py` + `tools/cnw_lint.py` + `tools/cnw_quality.py`

- 当前没有完整实现。按 `docs/THREE_LAYER_REVIEW.md` 逐个新增明确的 API/纯函数，**所有岗位都有真实独立输出**：
  `lint_surface(text,project_rules)`；`lint_structural(text,context_rules)`；
  `run_lens(name,draft,role_sources)` 五种 name；
  `adversarial_verify(findings, three_isolated_prompts)`；
  `completeness_critic(draft,survivors)`；
  `build_revision_plan(survivors)`；`re_review(touched_lenses, revised_draft)`。
- 每个语义审稿问题字段：`finding_id`, `lens`, `severity`, `line_start/end`, `quote_or_hash`, `claim`, `source_ref`, `reason`, `suggested_fix`, `model_id`, `request_id`, `raw_response_sha`。
- 分离文学结构性 fatal / char constraints / POV/Canon / style cosmetic，不能因文体偏好误删强相关可演动作。反证 2/3 阈值由真实三个独立 verifier 的输出统计；不凭 Writer 手填决定。
- 质量评分不能盲套作者特定主人公指标；为《苍歧》维护 `genre_reward`, `scene_causality`, `character_distinctiveness`, `performance_ready`, `pov_canon`, `hook/transition` 等可核查项，review 附**文本证据**；分数不能覆盖关键节拍/长度 fatal。

### F06B `tools/p2_cost_guard.py`（在原费用守卫上做最小、兼容性可验证的多项目参数化）

- 现有守卫 `load_config()`/`locked_ledger()`/`command_reserve()`/`command_settle()` 必须保持旧 P2 默认路径的旧行为；历史 17 次请求与旧账本不得改动、归零或搬迁。
- 为未来新项目真实请求增加**显式获批** campaign policy 的读取入口（例如可选的 `--campaign-config`，以及由该 policy 唯一绑定的 private ledger），拒绝任意用户输入决定预算上限。policy 必填授权身份、project_id、limit_cny、scope、model 和 approval_ref，若缺授权或试图给新项目自动继承 ¥10 则拒绝。首次 P3 的 J19 实测仍继续使用 P2 同一 ledger 与旧余额。
- 修改 `load_config()` 优先解析已批准 policy，`locked_ledger()` 使用验证在 `runtime/private/` 内的账本路径；`command_reserve/settle/report` 始终锁住同一当前 campaign，拒绝同 request ID 混用不同 campaign；拒绝错误路径、symbolic link 和未经授权增额。每个独立 unit 的 provider 调用仍先 reserve 再 send 再 settle；若 usage 缺失继续占预留。
- 对旧 P2 账本进行只读 hash 前后比较并按原配置完成非付费 report，确保改接口后老样本不变；用两个新的隔离 fictional fixture 检查未经授权创建 campaign 必须拒绝、批准 campaign 在**模拟**账本中才可创建，不提供自动充值或推断用户批准。

### F07 `tools/cnw_export.py`（新增动态交付）

- 输入 manifest 指向当前受审 run 的已接受稿、前后锚、章节/场次身份，生成 `初稿/修订稿/前后文连读/修改说明/源码身份/费用信息/运行复用说明`。不能让 `studio.ps1` 继续写死 J19、书案和思柔作为所有新项目的导出说明。
- 审稿和供应商证据中的秘密不输出；HTML 本机打开、不含脚本/外部资源，源码核对需工作树忽略的 `deliverables/<project>/<run_id>/`；导出重复运行不得向供应商发送任何调用。
- 新产品入口复用之前已经验收的 `nk-start/nk-stop`，不更换网络服务实现。

## 三、新建代码边界（缩小工程膨胀）

| 文件 | 职责 | 不准做的事 |
|---|---|---|
| `tools/capture_cnw_reference.py` | 原作者已批准固定快照的真实文件复制与 hash 清单 | 修改上游、猜测丢失源码、复制示例小说进公开 Git |
| `tools/cnw_contract.py` | 生产单位和长度/剧情节拍不变式 | 自己写故事、凭模型自评补足长度 |
| `tools/cnw_roles.py` | 作者 Plot/Card/Brief/Prose 输入输出编排/格式约束 | 创造一套替代文学理论、擅加情绪量表 |
| `tools/cnw_generate.py` | 本项目的 Flash 正文执行，费用账本、版本控制 | 重写已有 NK/CritiCS 内部算法、临时设定 500–700 字 |
| `tools/cnw_nk_adapter.py` | 当前 Card → NK perspective → Brief 的可追溯映射 | 用 NK 的简短 reflection 充当全文 |
| `tools/cnw_critics_adapter.py` | CritiCS 原批评/改写桥的实际调用 | 让 CritiCS 替代 CNW 的五种 lens |
| `tools/cnw_lint.py` | 中文 L1/L2 确定性找问题 | 自动删除文学文本、英文规则不适配硬套 |
| `tools/cnw_review.py` | 五 Lens、三 Verifier、Completeness 和再审 | 以一条 Writer 自评消息冒充多个独立审稿 |
| `tools/cnw_quality.py` | 判 fatal、产量、节拍、文本效果及 pass/revise/rewrite | 分数美化取代未满足的必要剧情 |
| `tools/cnw_revision.py` | 根据已确认 issues 生成和保护修订版本、晋升 | 覆盖 v0、纯删减充作改稿 |
| `tools/cnw_export.py` | 动态、无付费的阅读与交付产物 | 只复制旧 EP001 目录冒充新生产 |
| `tools/cnw_project.py` | 新剧本原始文件导入、源索引、未确认 Canon 标记、来源验证 | 把任何新剧本直接解释成《苍歧》、仅替换 ID 不读原文 |
| `tools/cnw_runner.py` | 严格顺序和依赖状态，复用既有费用/上游脚本 | 再造通用平台、增加不必要 GUI/消息队列/数据库 |
| `tools/studio.ps1` | 统一人用命令入口，传参/展示/旧运行状态 | `scene -Stage draft` 返回 CHECKPOINT_REUSED 却报告新生产 |

Writer 可在不扩大方法与产物合同的前提下合并以上小模块，但不能省略任何责任或验收例子。原生 CNW 是公开 prompt/procedure 方法；新脚本是本项目的**明确工程实现**，不是冒称上游原有脚本。
