# P3.1 对既有 W00–W05 的差异审计

状态：**P3.1 W04/W05 差异纠偏已由同一独立 Controller 接受；W06 仍未签收。**

## 基线与权限

- P3.1 工单包 SHA256：`2550F43B266BFDCAC324F9C24E4DCC7E86B6AA38462B32310A203F54BD6FFDF3`；包内 12 项 manifest 校验全部通过。
- 审计基线本地 `main` C=`9464165c69825aaa01fefee83f019dd69b52e877`、T=`6eb7cd167ae159608375b28ba5815a4bfa7c79ff`；远端 `origin/main` 同 C。CNW、CritiCS、NK pins 与既有状态记录一致。
- 独立 Controller 首轮差异审查确认：W00–W03 可沿用历史验收；P3.1 W04/W05 不能沿用为新剧本导入已完成的证据。Controller 未审 W06 文件。
- Controller 对首个 P3.1 候选提交 `fd0a83975f8514dbf16b1449dc0c433c74a87c55` / 树 `a06bd11c3fedc43f488275bc4d86072e78d050e5` 给出 `RETURN`：指出实时校验未将 receipt 字段与原始响应 JSON 内容交叉核验，且候选登记未强制完整岗位链。以下补丁只修这两项边界，待同一 Controller 按新 C/T 复验。
- Controller 对第二候选 `91ccf13e2da95fc70e8725fac765e875c2b0c99d` / 树 `869fc05d3c41542c72cffcc368cf96ae89ca693f` 确认前述两项已修，但指出 W10 未验证 5 个不同 Lens 和 3 个不同 Verifier 的独立请求身份。现补上角色 ID 集合门和缺失/重复负例；二次修复仍待复验。
- 同一 Controller 最终接受候选 `e7fcac6c0372ddca670f12c10ac86704064e22b9` / 树 `3d25ee789c7d5f8bac6477d685f5751200fe7dad`。接受范围为 P3.1 对 W04/W05 的差异补齐与 Live 验收边界代码；Controller 明确未运行测试，也未检查或签收 W06。
- P3.1 包内要求创建候选分支，与用户此前明确的“只要一个 main、不要分支”冲突。本工程继续只在 `main` 上增量工作，既不创建分支，也不强推、reset、clean 或删改既有历史。
- P3.1 作为当前活动施工合同，旧 `plans/MASTER_PLAN_P3.md` 保留为旧版历史；包内活动文件已逐字节复制并保留原 SHA，见 `AGENTS.md`。

## 差异与本次候选修复

| P3.1 项 | 原 W00–W05 事实 | 候选修复 / 当前证据 | 状态 |
|---|---|---|---|
| W04 / M04 新剧本导入 | `studio.ps1 import-source` 只验证固定《苍歧》包；不存在通用 `cnw_project.py`；角色输入限于 `workspace/cangqi` | 新增 `tools/cnw_project.py`：初始化私有项目、导入 UTF-8 `.md/.txt/.json`、保存原文件 SHA/字节/路径、行号或 JSON Pointer、source manifest/index、Canon 候选均为 `TODO_CONFIRM`；由显式人工输入生成 source-bound 合同草案 | Controller ACCEPT；新源候选仍需人确认 |
| W04 → W05 数据贯通 | runner 固定按《苍歧》 release 目录验源；Studio 把 `ProjectRoot` 当代码根 | runner/角色包支持项目内 imported source identity；`studio.ps1` 从脚本位置推导仓库根、将 `ProjectRoot` 限定于 `workspace/<project>`，新增 `project-init/project-import/project-contract`，`produce` 使用导入项目合同和项目私有 runs 目录 | Controller ACCEPT；双原稿链路与 PowerShell CLI 通过 |
| 两个原始剧本 | 旧测试从预制《苍歧》合同开始，不能证明导入器 | `tests/test_cnw_project_import.py` 实际导入不同 `.md` 与 `.json` 原件，核对独立 source SHA、索引定位、Canon 候选、source anchor、合同 hash、Plot/Brief role input hash，再从 Studio runner 创建各自 offline run | Controller ACCEPT；`MOCK_ONLY`、零模型调用 |
| 外部 Controller / promote | W05 的阶段 fixture 可记为 ACCEPTED，`review` 只回 `REVIEW_REQUIRED`，promote 没有明确外审证据门 | 离线阶段请求不能注册为 editorial candidate；非 fixture live run 必须有完整阶段回执、每阶段 ACCEPTED，五个 Lens ID 与三个 Verifier ID 各自齐全且独立；promote 另要求外部审阅证据，CLI 不自签 | Controller ACCEPT；真实 W10 未运行 |
| W07 与 W10 | W05 live fail-closed；`verify_live` 曾只校验 raw 文件 hash，没有核对 raw 内容，也未数清 5+3 独立调用 | receipt 逐请求与原始响应 request/provider ID、DeepSeek Flash、HTTP 状态、finish reason、prompt/completion tokens 比较；分别要求 `style/character/plot/canon/story_specific` 与 `verifier_1..3` 八个 ID；仍与唯一 SETTLED 账本行核对。W07 `MOCK_ONLY` 明确不计 Live | Controller ACCEPT 代码边界；真实 W10 未运行，须按 P3.1 后续阶段验收 |
| 分支治理 | 当前唯一 branch 是 `main`，本地/远端一致 | 遵循用户明确授权；不按 P3.1 包内规则创建候选分支 | 已按用户权限确定，不是 P3.1 候选分支流程已执行 |

## 验证

- `python -m unittest discover -s tests -v`：47 tests，全部通过；W06 另由同一 Controller 接受，记录见 `evidence/P3_CURRENT_STATE.md`。
- PowerShell parser 检查 `tools/studio.ps1`：无语法错误。
- 实际 PowerShell：`project-init`、`project-import`、`project-contract` 与新项目 `produce -Mode offline -ProjectRoot workspace/P31CLI` 成功；run 位于该项目私有 `runs/`，返回 `provider_call=none`。测试工作区已移除。
- 未调用 DeepSeek/NK/CritiCS API；无新增费用；真实 W10 `NOT_RUN`。
- `python -m py_compile tools/cnw_runner.py` 通过；`git diff --check` 仅报测试文件 EOF 多空行，已识别待清除后复核；最终候选 C/T 将在 Controller 补验包中更新。

## 阶段决定

历史 W00–W05 ACCEPT 记录不变。P3.1 对 W04/W05 的新增差异与 W06 已由 Controller 分别签收；双源离线链路不代表 Canon 获确认、不代表模型写作或生产系统完成。现继续 W07，且之后阶段仍须分别验收；不得把 W07 mock 或代码门称作 W10 Live。

## ATOM-CNW-PUBLIC-1TO1-RESTORE 差异（2026-10-10）

本节只追加本 Atom 的实际差异；不改写上文历史。状态：**已施工并完成一次真实单场 Run，但独立 Controller 工程复核与当前 ChatGPT 审查尚未进行**，因此不记 Atom ACCEPT。

| S 项 | 实际改动 | 证据 |
|---|---|---|
| S01/S02 | `tools/cnw_runner.py`：`CNW_STAGES` 改为作者 11 阶段；`pov` 移出阶段序列成为 `support_hooks.nk_pov`；`promote/export/resume/sprint` 为后处理动作；`stage_predecessors` 按作者全顺序 |
| S03–S06 | `tools/cnw_roles.py`：新增 `AUTHOR_ROLE_READS`，四岗位按作者 `ai_roles.template.yml` 读取 `04_chapter_design/arc_*.md`、`90_canon/*`、`06_plot/*`、`05_scene_cards/*`、`92_style_engine/*`；实测四个岗位材料均可解析 |
| S07–S09 | `prompts/cnw/{plot,scene_cards,brief}.md`：机器预算标记移入同阶段 `*.meta.json` sidecar，文学 Markdown 不再内嵌 `CNW_CONTRACT/CNW_BEAT` |
| S10/S11 | `tools/cnw_nk_adapter.py`：NK `eventSequence` 从已接受 Scene Cards 的 Required beats 构造；`cnw_runner.execute_writing_brief` 在 Brief 冻结前真实调用本地 NK 并映射 reflection |
| S12 | `tools/cnw_runner.py:execute_prose`：按合同长度生成并允许最多两次有界续写；实测 v0=1261 可见字符 |
| S13 | `tools/cnw_lint.py` 两层纯本地 regex；本轮 L1/L2 命中 0，未删除正文 |
| S14/S15/S16 | `tools/cnw_review.py`：五 Lens 来源按作者文档；`VERIFIERS=(correctness,character_consistency,continuity_plausibility)`；每个真实 finding×3 独立反证；Completeness 读全文与处置 |
| S17/S22 | `tools/cnw_runner.py:execute_refine/execute_re_review`：按确认 finding 修订并保留 v0；受影响的 Lens 复审；有界恢复避免缩水 |
| S18/S19 | `verify_live` 分离本地 lint 与供应商阶段；不要求每阶段 Controller 个人签收；零 finding 时保留空集合 |
| S20–S24 | `tools/cnw_project.py`：01 导入、02 增量更新、04 Canon 审计、05 handoff、support-workflow 提示导出；`tools/studio.ps1` 增加对应命令 |
| S25/S26 | 复用 W08/W09 `cnw_revision.py`/`cnw_sprint.py`；sprint 仍为离线 fixture，本 Atom 不发五话 Live |
| S27 | 新增 `tools/cnw_export.py`：从 run manifest 动态导出初稿/修订稿/连读 HTML/MD/TXT，无 EP001 硬编码 |
| S29 | 复用唯一 `p2_cost_guard.py` 与同一账本；本轮真实 Run 152 次 provider 呼叫全部 reserve→send→settle |
| S30 | `AGENTS.md`、`evidence/P3_CURRENT_STATE.md`、`plans/ATOM_CNW_PUBLIC_1TO1_RESTORE.md` 记录本 Atom 为 P3.1 覆盖条款 |

真实 Run：`CNW1TO1-CQ-J19-20261010-01`，11 阶段全部 `STAGE_MATERIALIZED`，`verify-live` 返回 `LIVE_EVIDENCE_VALIDATED`（83 receipts，全部 SETTLED）。`EPISODE_LIVE_NOT_RUN`、`SPRINT_LIVE_NOT_RUN`、`USER_CREATIVE_ACCEPTED=PENDING_USER_READING`。

## 原作者源码重新研究：首批修复（2026-10-11）

用户要求自行研究并实现原作者公开工作流，不再将旧施工单作为实施方案。本节记录当前实际代码增量；上文历史记录不构成新实现完成证明。

- 对照固定参考 `templates/_workflows/02_incremental_update.md`：导入追加来源、索引及候选，保留既有确认状态；相同内容重复导入不重写项目。信息分类、设计文件维护及语义冲突处理尚待完成。
- 对照 `templates/config/ai_roles.template.yml`：主生产 Prose 消息仅包含 Brief 和参与人物声音分节，删除完整剧情合同注入；共享 Prose 包构建也筛选声音。旧 executor 兼容问题尚未修复。
- 对照 `docs/THREE_LAYER_REVIEW.md`：Completeness 遗漏带所属 Lens 与后续检查指令，项目持久保存并由对应 Lens 读取。写入前检查全部条目类型。
- 对照 `templates/92_style_engine/forbidden_patterns.template.md`：本地 Lint 从项目 Markdown Pattern/Cap 列读取确定性规则；非正则描述保留为语义审查项。无可执行规则明确返回 `NO_EXECUTABLE_RULES`，不报告 clean。
- 验证：现有导入 2 项、适配 8 项、审稿 10 项测试通过；直接执行验证了累计来源、确认状态不变、唯一候选 ID、重复导入文件字节不变、Prose 无关声音隔离、原作者模板正则读取与次数上限。`git diff --check` 无空白错误。
- 唯一独立只读 Controller `/root/controller` 复核结论：**ACCEPT，仅限本轮代码增量**。不是整项工作流验收、真实生产证明或用户创意接受。
- 本轮无新增模型调用。只读账本显示累计占用 ¥3.663326/¥10，后续仍沿用同一费用护栏。
- 尚待继续：项目导入语义产物、创作前资料准备、Plot 结构职责、当前修订协议、受影响复审与继续修订、并行调度及真实作品生产。不得以本次增量声称完整完成。

## 原作者源码重新研究：修订与复审闭环（2026-10-11）

- `cnw_revision.build_revision_plan` 兼容当前 `multi_lens_review/adversarial_verify`，逐 Finding 三种反证身份与原始票值绑定；保留历史旧协议的读取兼容。零 Finding 不要求三条虚构调用。
- `cnw_runner.execute_refine/execute_re_review` 保存逐版计划、修订前正文和修订稿；复审附真实 diff，只请求受影响 Lens。新发现经三种反证后进入下一版修订并再次复审。一次执行最多三轮，仍有确认问题时保存 `REVISION_REQUIRED`，不得作为最终完成。
- `verify_live` 将最终修订正文 hash、Lens 原始 findings 全集和 Verifier 原始票值与报告逐项绑定；不接受只有 `REVIEWED` 的旧报告作为最终 clean 证明。
- 成功供应商调用按完整请求身份复用，并核对原始响应及正文 hash；未完成 Refine 保存输入身份与版本号，恢复相同输入不更换版本号。新修订单调分配版本，按 run 隔离项目修订文件。
- 验证：既有 generation 22 项、runner 17 项通过。执行过明确 `MOCK_ONLY` 闭环：style 复审发现问题、三个独立反证模拟响应、v2 修订、干净复审，旧稿和两轮报告保留。另验证 5+6 当前协议、零 Finding、重复任务拒绝；网络 transport 模拟验证成功响应重用且 raw 篡改后拒绝发送。
- 独立只读 Controller `/root/controller` 在修正中断恢复、原始结果绑定、版本覆盖问题后给出本批 **ACCEPT**；未把该结论记为新 Live 或全项目完成。本批无新增真实供应商调用。

## 原作者源码重新研究：创作前资料与 Arc 定位（2026-10-11）

- 对照 `example_project/00_meta/episode_production_manual.md` 的生产读取顺序，Plot 前读取当前状态、手稿索引、所属 Arc/详细规划、人物资料及前话正文；Scene 插场以前文来源锚适配，不冒充前一完整 Episode。
- `resolve_arc` 通过原作者 Arc Index 的话数范围或明确 Arc 引用选择文件；排除索引及详细规划被误选为 Arc。缺少前话或准备文件时明确指出资料缺失。
- 准备材料实际进入 Plot 请求并保存逐文件 hash；来源冻结另包含完整文件集合和索引存在性，Live 阶段前重新核对。新增索引改变 Arc 选择而旧文件不变的反例已确认被拒绝。
- 当前私有《苍歧》项目根据既有合同、Arc 和历史状态补齐三份缺失准备资料并追加工作日志；未改变原稿或 Canon，未调用模型。
- 验证：adapters 9 项、runner 17 项通过；多 Arc ep007 定位至第二 Arc、读取 ep006、话数越界/前话缺失均已覆盖。真实 J19 准备文件集合读取及冻结通过。
- 独立只读 Controller `/root/controller` 修复来源集合变更缺口后给出 **ACCEPT，仅限本轮准备资料与 Arc 定位改动**。完整工作流及新作品仍未验收。


## 2026-10-11 — Plot design instructions and planning input separation

- Compared pinned author `templates/06_plot/plot.template.md`: Key Scenes, Required Story Beats, Hook, Foreshadowing and Connections belong to Plot design.
- Plot now explicitly designs structure, actions and additional beats while preserving source facts, required outcomes, overall length and the authorized single-scene scope.
- Plot/Cards/Brief live requests and role packets use a deep-copied creative assignment without historical scene allocations, per-beat budgets or model-side accounting metadata. Original contracts and provenance hashes remain intact. Cards/Brief prompts no longer prescribe historical beat budgets.
- Validation: existing adapter 9 tests and generation 22 tests PASS; direct MOCK_ONLY request checks for all three planning roles confirm preserved required outcomes/disclosure boundaries, removed allocations, and unchanged original contract. No paid API call.
- Independent read-only Controller: ACCEPT for this input/prompt increment; checked known packet consumers. This does not accept full Plot autonomy, preflight, full Episode production or new Live results.
- Still open: preflight currently requires predefined beats/scenes; execution sidecars retain historical allocations. Full author-equivalent planning must remove that prerequisite and consume actual Plot structure before claiming completion. USER_CREATIVE_ACCEPTED remains PENDING_USER_READING.


## 2026-10-11 — Author Plot planning mode and imported episode entry

- Added `unit.planning_mode=author_plot`: preflight validates total length, source identity, scope and any explicitly supplied required outcomes, without requiring a predesigned scene list or beat allocations. Existing contracts without this mode retain historical validation. New imported assignment drafts default to author_plot and may omit required_beats; scene and episode units are supported.
- Plot output must supply actual Key Scenes and Required Story Beats lists. The runner stores those lists and the Plot hash in its sidecar without inventing character allocations. A scene assignment must remain one Key Scene. Downstream roles read the generated Markdown. NK uses actual Cards events, including numbered lists and case-insensitive headings; author_plot never falls back to contract goals as fictional executed events.
- Independent Controller initially RETURNed two entry defects: single-line anchor freeze assumed source_line_end, and draft conversion lost Arc/previous-episode references. Both corrected; relative Markdown references, first_episode boolean and contradictory prior-reference fields are validated. Controller subsequently ACCEPTed this increment after read-only source review.
- Validation: adapters 10, contract 6, import 2 and runner 18 tests PASS (36 total); runner includes MOCK_ONLY episode production setup and generated two-scene Plot materialization with hash-bound index, no prefilled beats/scenes. Private `workspace/.author-entry-check-f9jxl3tz/AUTHOR_ENTRY_CHECK` exercises imported custom episode with explicit Arc/previous text, no predefined design, single-line anchors and real source-freeze validation in offline mode. No paid API calls or live literary acceptance.
- Scope limits: generic capability increment only; complete live Episode/Sprint, source-equivalent import, parallel review and final same-J19 readable output remain unproven. USER_CREATIVE_ACCEPTED=PENDING_USER_READING.


## 2026-10-11 — Executable author Workflow 01/02 import

- Added `cnw_import_workflow.py` and `cnw_project.py initial-import/update-inbox` entries. Initial import reads all supported inbox originals, preserves byte snapshots, uses pinned Workflow 01 in source-classification and organization passes, creates the required author documents, source inventory notes, work log and next action. CONFIRMED output is rendered from exact source statements; inference and uncertainty remain labeled. Raw staging remains distinct from semantic completion.
- Incremental processing compares committed source hashes, extracts only new/changed files, supplies existing Markdown from theme/logline/project/chapter/Canon directories, and appends dated conclusions. Model-reported or matching-attribute conflicts retain both versions in unresolved questions; conflicting claims are withheld from new Canon additions. Different wording of one attribute can conservatively trigger a question, so this is not proof of semantic contradiction accuracy.
- Uses existing DeepSeek Flash transport, shared campaign ledger, raw-response receipts and request fingerprint cache under separate project_import/project_update support roles. The author 11 production stages remain unchanged. No real paid call was made during this increment.
- Pre/post-image transaction journal supports interrupted writes and rejects concurrent edits or unrelated temporary files. Source bytes and existing conclusions are checked before commit; journals and private content remain outside Git.
- Independent Controller initially RETURNed fixed-document scope omitting world_bible/timeline/glossary/concrete Arc files. Directory-scoped existing Markdown and safe append targets fixed this. Controller then ACCEPTed the increment and reviewed final source-summary/doc/temp-file adjustments; read-only review, not API or creative acceptance.
- Validation: import 6 tests and runner 18 tests PASS. Mock cases cover required outputs, direct-source confirmation rejection, unchanged input/no calls, changed source conflict/old Canon preservation, world_bible-only old evidence, existing Arc append, and interrupted transaction recovery without duplicate model calls. CLI help and diff checks pass.
- Real manuscript classification quality, complete live output and full public-workflow equivalence remain open. USER_CREATIVE_ACCEPTED=PENDING_USER_READING.
