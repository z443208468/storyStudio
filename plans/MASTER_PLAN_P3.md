# StoryStudio P3 — 对照原作者完整公开生产方法的逐文件施工与产品验收计划

**状态：当前活动计划；阶段 W02 执行中。**

> **唯一目标**：保留已经部署并接通 DeepSeek Flash 的 Narrative Keyframing 和 CritiCS，把原作者 `MintoTsukino/claude-novel-workflow` 公开的 **全套可见工作方法** 精确落成 StoryStudio 的可重复文学创作生产流。可接收新剧本/新 Scene/新 Episode，自动按照 Arc/Canon → Plot → Scene Cards → Writing Brief → 正文 → CNW 多层审稿 → 反证 → 遗漏检查 → 修订 → 复审 → 索引更新 → 导出执行。第一轮只重新生产一个已经批准的《苍歧》J19 插场，不扩写下一场；但系统本身必须实现可复用的下一场/下一话能力。
>
> 不能以“工具安装成功、跑出一百字、保留旧 EP001、Git hash 全通过、Controller 勾 ACCEPT”冒充完整文学生产线建立。

## 0. 执行前提与不可改动边界

| 部分 | 当前审查事实 | 本次做法 |
|---|---|---|
| StoryStudio 远端 `main` | `939eca90c030cf726b1879e2b1115f0e07ed6f6c`；旧候选分支已不在远端列表 | 先现场 `git status`/HEAD/remote，后续如已有新提交取最新，不强制回退 |
| CNW 作者原版 | Gitlink `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`；本机应已有 `third_party/claude-novel-workflow` | W00 **先把文档+模板+少量方法实例从固定源码按字节复制到本机**，有 manifest 才施工 |
| Narrative Keyframing | 已补丁部署，已真实跑 DeepSeek/Zod | KEEP：provider/schema/YAML 创作方法不重写，编排层调用其已有 HTTP 路由 |
| CritiCS | 已补丁修复、真实跑五次剧情 Critic 和三次文本 Refine | KEEP：继续走 `tools/critics_bridge.py` 和费用捕获路径；不让它取代原 CNW 审稿 |
| 费用账本 | 历史约 17 次真实请求，累计估算 ¥0.123297，已有 ¥10 活动预算 | KEEP：现有 `p2_cost_guard.py`，所有新增请求计入既有可见剩余预算，不擅自重置或扩容 |
| 《苍歧》源稿 | JUN-SINGLE-02.3、ZIP SHA256 `300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2` 已导入 | KEEP：不改源稿/原剧情状态；首次只改写被批准的 J19:555→557 前合法插场 |
| 旧 P2-06/P2-07 | 当时 Controller 的工程签收与纯技术 smoke 成功均是真实历史 | KEEP：作为历史，不删除。另补 `PRODUCT_MILESTONE_REOPENED`，产品验收重新打开 |
| 文学方法 | 作者公开了方法/通用模板/真实案例，**未将私有实际多 agent 程序作为开箱即用执行包完全公布** | 必须依公开阶段合同工程化：来源可核、每个角色是真执行，不伪称是作者原封不动的专用执行器 |

### 四条绝对禁止

1. 不重新初始化空仓、重装已通过环境、清理旧 worktree、reset/force-push 或覆盖先前作品；只增量开发 P3 正式生产层。
2. 不拿作者示例小说的角色/世界/词句当《苍歧》内容；可复制公开的通用模板字段、流程顺序和检验方法。
3. 不把“原作者流程”缩减成“Codex 请求一个 Flash 写几句话”；**正文生成规模由 StoryStudio 项目生产合同在写作前确定，逐场分配并冻结**。
4. 不允许 CNW 的 5 Lens、3 Verifier、Completeness、Refine、Re-review 被 P2 Controller/CritiCS 一条聊天结果顶替。工程 Controller 仍独立签收每 Atom，但自己不是这 9 个文学岗位。

## 1. 先行工具包与资料安排（阅读顺序）

1. `reference/CNW_ORIGINAL_SOURCES.md`：作者固定源文、Git blob、具体行号、不能误解的规则。**先读**。
2. `tools/capture_cnw_reference.py`：真正从本机已经 pinned 的 Git 子模块按字节导出 `docs/`、`templates/`、作者公开生产手册及少量只读示例到 **Git 忽略** `runtime/reference/cnw_97ad71fe5e5e/`；写原件 SHA256 manifest。
3. `mapping/P3_SOURCE_TO_CODE_MATRIX.md`：38 条“作者来源 → 当前函数/行号 → 缺失行为 → 要改文件与证据”与 F01–F07 逐文件改法。
4. `spec/CNW_ROLE_INPUT_OUTPUT.md`：所有模型岗位的精准输入输出、Scene/Episode JSON、规模合同、哈希状态与评审职责。
5. `tests/P3_ACCEPTANCE_TESTS.md`：每 Atom 应进行的正例/负例/付费与非付费测试，拒绝重演 P2 短稿合格的验收错误。
6. `CODEX_START.md`：贴给现有 Codex 会话的唯一开工指令。

## 2. 工作流最终落地形状（公开 CNW 方法，不是临时幻想）

```text
作者公开原方法:
Project / Arc / Canon / Style
    │
    ▼
Plot Agent（明确章节作用 / 场次 / 长度 / 读者报酬）
    │
    ├─【项目附加：CritiCS 原 three_critic + 对合法问题改 Plot】
    ▼
Scene Card Agent（每场目标长度、起止状态、必须动作、禁写）
    │
    ├─【项目附加：NK 视角 reflection，只作 Brief 资料】
    ▼
Writing Brief Agent（压缩的可执行写作合同 / 分场预算）
    │
    ▼
Prose Agent（按 Brief 写完整正文，必要时按场次分段，绝不私自缩短）
    │
    ▼
Layer 1 表层 Lint → Layer 2 结构 Lint
    │
    ▼
5 个相互独立的 Lens：Style / Character / Plot / Canon / Story-specific
    │
    ▼
3 个相互隔离的 Adversarial Verifier（优先证伪）
    │
    ▼
Completeness Critic（发现此前审稿漏项）
    │
    ├─【项目附加：CritiCS 原 Image/Voice/Leader，意见归入同一修改计划】
    ▼
Revision Plan（P0–P3）→ Refine（保留 v0 与被接受动作）
    │
    ▼
Re-review（只重跑真正受影响的 Lens，但必须读修改后上下文）
    │
    ▼
Controller 对文学结构/真实功能逐阶段签收
    │
    ▼
promote → 正本 / manuscript index / current_state / handoff / export
    │
    └─ Episode 模式：每 5 话另走 Batch Review + Canon Audit + Sprint handoff
```

作者标准 `templates/config/workflow.template.yml` 的 11 个环节顺序必须能在真实 `run_state.json` 中看到。增加 NK/CritiCS 可采用 hooks，但不能吞掉已有环节。P3 初始仍遵守 DeepSeek API 单并发/费用护栏：五 Lens 是五个**不同上下文的调用**，串行执行也保持独立判断；以后并发优化不在这次范围。

## 3. 施工序列 — 每阶段都精确到现有代码、做法、验收及接续

### W00 — 固定原作者所有相关工作流原文到本机（零 API 费用）

**输入**：`third_party/claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`；`README/CLAUDE/docs/templates` 和手册实例原件。

**行动**：

1. 当前 Writer 先记录本地 HEAD、分支、staged/unstaged/untracked、remote main，确认 P2 已有 WIP 不被覆盖。核实子模块 `git -C third_party/claude-novel-workflow rev-parse HEAD` 等于 pin，检查 tracked diff（不准自动 reset）。
2. 把本工单附的 `tools/capture_cnw_reference.py` 放入 StoryStudio `tools/` 后执行（当前机器 PowerShell）：

   ```powershell
   cd D:\CangqiStudio\StoryStudio
   python tools/capture_cnw_reference.py --repo-root D:\CangqiStudio\StoryStudio
   ```

   如果系统 `python` 不可用，使用既有 `runtime/envs/critics-api/Scripts/python.exe`；该脚本仅使用标准库，不能因此重装 uv/Python。
3. 这一步将**真实复制**固定源码中的 `docs/` 全体、`templates/` 全体、README、CLAUDE、LICENSE，以及选定的生产手册、原作者一次真实 Brief/Card、批次 Review 到：

   `runtime/reference/cnw_97ad71fe5e5e/<原相对路径>`。

   这是 **用户 Windows 的私有本地目录**，并非写公开仓。每份原件会校验 Git blob 并按字节比对 SHA256；输出 `CNW_LOCAL_REFERENCE_MANIFEST.json`。
4. 重点阅读并列举：原 `episode_production_manual.md`、`templates/config/{ai_roles,workflow}.template.yml`、Plot/Card/Brief 三个模板、`docs/THREE_LAYER_REVIEW.md`、`templates/_workflows/03_revision.md`、质量手册和 5 话 Sprint 示例。必须读取**完整原文**，不能只摘 README 的介绍。
5. 对每项方法建立 `reviews/P3_METHOD_COVERAGE.md`：源路径/Pin Blob/原文职责/项目映射代码/实施状态。首先全部标 `NOT_IMPLEMENTED` 或 `ALREADY_IMPLEMENTED_WITH_EVIDENCE`，不能在未执行时提前标 PASS。

**实际验收**：固定原件路径可读；复制/原件 hash 一致；manifest 包含数十份真实文件；Git ignored；源码 submodule tracked diff 未改变；Controller 看得见真正文件，不接受“我读过作者方法”的口述代替原件。

**失败处理**：若 submodule 丢失，确认本地 Gitlink 后仅恢复原已固定项目的 `git submodule update --init -- third_party/claude-novel-workflow`；网络失败时不要编造本地文件已复制，保留所有已验证源记录并报告确切缺少的对象。除此不下载不同版本。

### W01 — 再对照 StoryStudio 最新源码，冻结行级差异（零 API 费用）

**输入**：W00 本地 manifest；`mapping/P3_SOURCE_TO_CODE_MATRIX.md`；当前 StoryStudio `main` + WIP。

**行动**：

1. Writer 不依赖记忆，逐一完整打开 `tools/studio.ps1`, `tools/p2_06_draft_run.py`, `tools/p2_06_revision_run.py`, `tools/p2_06_critics_run.py`, `tools/critics_bridge.py`, `tools/p2_cost_guard.py`, `config/production.example.json`, `implementation/{PRODUCTION,ACCEPTANCE,TECHNICAL}_SPEC.md`, `patches/{nk,critics}/PATCH_INDEX.json`。
2. 对矩阵中 M01–M38 的每项在本机定位精确函数/行号、源 byte hash，实际 diff 与本工单断言逐条比对；如果现有工作树已新增相同实现，标 `PRESENT_AND_TESTED` 并复用，不再重复创建。
3. 执行 `rg -n '500–700|literary_word_count_target|CHECKPOINT_REUSED|EP001|J19:555|verify -Mode live|two_refinement|p2_06' tools config implementation`；记录这些**仅样本阶段应存在的硬编码**。不把文档历史里出现相关词当作活代码失效。
4. 确认 NK 生产补丁、CritiCS patched source、原 Run/C/T 均仍可读；任何已签收源身份保持，无必要不得动 Vendor/NK/CritiCS 源。
5. 创建 `reviews/P3_CODE_CROSSWALK_ACTUAL.md`：每个 `source file@blob` → `current file:line@hash` → `new file/function` → `test-id`，再由 Controller 检查独立依据；进入修改后只维护差异，避免复制全篇表格。

**验收**：M01–M38 全部有真实实现状态；W00 原文可定位；遗漏了原创作主岗位审稿链的事实不得用 P2 acceptance 遮掩。

### W02 — 把“环境已部署”与“真正可生产”分开治理（零 API 费用）

**修改目标**：`AGENTS.md`, `docs/governance/GOVERNANCE.md`, `plans/MASTER_PLAN_P2.md` 的活动计划入口，以及 `evidence/P2_CURRENT_STATE.md`/新增 P3 状态文件。旧 P2 计划和验收原文不可改写历史事实。

**行动**：

- 新建 `plans/MASTER_PLAN_P3.md` 的本地活动副本，根入口指向 P3 当前产物，保留 P2 实际已验证节点为历史前置：`ENV_READY=ACCEPTED`, `NK_LIVE=ACCEPTED`, `CRITICS_LIVE=ACCEPTED`, `CNW_FULL_PRODUCTION=NOT_VERIFIED`, `PRODUCT_MILESTONE_REOPENED=YES`。
- Controller 仍为受委任独立验收子智能体；每个 W 阶段只审本阶段影响与原作者方法一致性，明确修复对象、不增无关验收制度；但不能因工程成功代签最终故事质量。
- 原来的 P2 `0b40876b`/主线实际日志及短稿继续保存为 `HISTORIC_SMOKE_SAMPLE`；不得将其当前 `ACCEPT` 清除或宣称 P2 文本曾满足全套作者生产规模。

**验收**：当前合法阶段 W02，原项目工具恢复能力没有被治理文件变更意外锁定，历史/新产品两种状态分开。

### W03 — 把原作者 Scene/Episode 规模预算落到生产前合同（零 API 费用）

**原文锚**：`episode_production_manual.md:22–28,575–594,635–648`; `plot.template.md:99–105`; `scene_cards.template.md:10–58`; `writing_brief.template.md:11–18,49–65`。

**修改目标**：`config/production.example.json` 加明示 `cnw_method_reference` 和新生产 policy 路径；新建 `config/cnw_production_policy.json`, `tools/cnw_contract.py`, `spec/...` 在项目对应位置；不篡改旧样本配置用于历史重放。

**行动**：

1. 从《苍歧》真实相邻段落/角色声音样本估计当场可读规模，不凭空把作者的日文 5,000 字设为中文固定字数；本工单提供**项目试场建议** `target 1000, min 700, max 1400` 中文可见字符，执行前 Controller 依据 Scene Card 的内容目标做一次源依据复核并冻结。若确实要更长，在生成前书面确定，不得见到短稿再把标准下调。
2. `work_unit_contract.json` 必填 `project/source_version/source_sha/unit kind & ID/POV/前后锚及原字节 hash/角色可知/情节职能/reader reward/required beats/每节拍分量/禁写/长度单位/总目标`；缺关键字段无法启动供应商请求。
3. Episode 模式：Plot 应先确定章作用与 3–6 个通常场次，每 Scene Card 各有分量，总和形成 Episode 目标；Scene 模式：明确它是一场独立插戏，不冠以作者完整一话的 5,000 日文字规模。
4. `tools/cnw_contract.py` 实现 `load_contract`, `validate_source_identity`, `validate_scene_budget`, `validate_episode_budget`, `check_required_fields`, `count_visible_chars`, `check_required_beats`, `assert_output_within_root`。`visible_chars` 精确定义按 `spec/CNW_ROLE_INPUT_OUTPUT.md`，报告 Markdown 字节数不同于汉字数。
5. 长度数据必须**写进 Scene Card 和 Writing Brief**，并在最终 API 的输入里保留；任何剧本/项目需要的例外须基于事前场景合同、记录原因并由 Controller 检查。

**验收**：T-B03 null/0/missing 失败；T-B04 分 Scene 求和正确；T-C01 百字稿判欠产量；不做模型调用。

### W04 — 实现原作者的四岗位计划生产，而不是 Codex 随手补正文（可先全离线）

**原文锚**：`templates/config/ai_roles.template.yml`；`plot.template.md`、`scene_cards.template.md`、`writing_brief.template.md`。

**新代码**：`tools/cnw_roles.py`（命名可等价，职责不能省），`prompts/cnw/{plot,scene_cards,brief,prose}.md`，`tools/cnw_nk_adapter.py`, `tools/cnw_critics_adapter.py`。

**行动**：

1. `plot_agent`: 以 Arc/Canon/原场合法锚/项目生产合同为输入，生成 Plot 的 Role、Key Scenes、Required Story Beats、Forbidden、Hook、Target Length。不得在生成后临时改 Scene 数和长度。已有 P2-05/06 Plot 可复用**剧情事实和源锚**，但必须补正式规模、scene mapping、reader reward。
2. `critics_plan_hook`: 通过已有 `critics_bridge.py plan-critique` 真走原生 `three_critic()`，结合 `plan-revise` 提案修 Plot；新情节建议须经 Canon/单场限制审查，不自动扩大 J19/J20 route。原调用证据在输入未变时可复用，不强制为装样再次计费。
3. `scene_card_agent`: 从已核准 Plot 生成 Scene 1..N；每张卡必须有 start/end、各角色 WANT、行动与回应、必需/禁止 beats、可演细节与分量预算；不能把“没有设定来源”扩大为“不能出现任何合理的生活动作”。
4. `nk_pov_hook`: 用 Scene Card 导出 NK 现有 `/api/generate-perspective` 请求，明确 `eventSequence`, `perspectives[].{id,narrator,eventLabel,eventObjective,characterSnapshots}`；现有生产补丁实际返回 `perspectives[].reflection`。检验“NK 原结果→ Brief 的对应点”，不得把 NK 的短 reflection 当整场正文。
5. `brief_agent`: 从 Plot/Cards/当前可知 Canon/声线取材生成唯一 Writing Brief。把所有 Scene 目标与必须节拍逐项带入，正文写作者**只接 Brief+相关声音样本**，不把全章未来秘密变成输出可用素材。
6. 设置每岗位的来源引用、输入 SHA、输出 SHA；离线只使用不同 fixture 验证内容穿透，不能把 mock 当真实创作质量。

**验收**：每个阶段只有它自己的职责；同一 Beat ID 在 Plot→Card→Brief 全程存在且场次预算一致；没有跑完整的四阶段不允许进入真正 Prose。

### W05 — 写出能生产新内容的通用调度与断点，而不是旧 EP001 查看器

**必改旧文件**：`tools/studio.ps1:2–10,43–108,120–148`。**新建** `tools/cnw_runner.py`，使用现有 `tools/p2_cost_guard.py`，不再开发第二套计费系统。

**行动**：

1. PowerShell 新增 `produce/step/review/promote/export/show-run/verify-history/verify-live`；`-ProjectRoot`, `-Unit`, `-Contract`, `-WorkId`, `-RunId`。现有 `scene` 返回历史 checkpoint 的能力保留，但明确显示 `LEGACY_CHECKPOINT_ONLY`；不要把它重命名成新生成。
2. `cnw_runner.py` 做**薄编排**：`plot, cards, brief, pov, draft, lint1, lint2, lens5, verifier3, completeness, refine, re-review, promote, export, resume, sprint`。每步唯一输入/输出，步骤名称与原作者 `workflow.template.yml` 可直接交叉核对。
3. 输出置于 `runs/<run-id>/`（Git ignored），`run_state.json`/`artifacts/*` 持久化、hash 依赖明确、已通过同输入不重发供应商。拒绝新 run-ID 重名覆盖、绝对路径穿越、泄露原稿到 Git。
4. provider 层继续用现在已通过的 DeepSeek 官方 Chat、当前配置和 `p2_cost_guard.py reserve/settle`；每个模型岗位均要有 request ID/usage/原始私有响应。`max_in_flight=1` 默认不变；同一个文学 Lens 单独 API 调用，并非共用工程 Controller 会话。
5. 需要多场章节时由状态机逐场发请求、逐场验证，再组装 Episode；如果输出 tokens 上限不足、角色不知、原稿未知或预算不够，报告**当前阶段失败**，不将整个 Episode 压缩成几句话。

**验收**：T-B01/B02/B07/B08/E04/E05；不同新 ID 确实会新生成，历史样本 `export` 不自动重新请求 API。

### W06 — 彻底修正正文短稿根因：篇幅来自 Brief，后校验且有有限续写

**已证实旧缺陷**：`tools/p2_06_draft_run.py:6,10–11,24,27–30`，其中 L24 写死“约500–700中文字符”；`p2_06_revision_run.py:5,8–10,17–24` 有修订缩水问题。二者保留为 P2 历史样本 runner，正式入口使用新增 `tools/cnw_generate.py` / `tools/cnw_revision.py`。

**行动**：

1. `cnw_generate.py` 从已冻结合同的每 Scene `min,target,max,required_beats` 构造任务，明确“全部动作/回应/节奏/对白实际写成正文，不是 Outline，不是两句总结”。正文只能根据 CNW Brief 写，系统消息不擅设新 500–700 限额。
2. 先为一个 Scene 计算可用 token cap：使用之前已记录的本模型 token/中文字符实际产出作为容量参考；在预算与供应商限制内，无法一次容纳内容时**分场/节拍**输出、保留局部连续上下文再按顺序合稿。不得因 cap=2048 就自动缩短故事。
3. 原稿视角和未披露秘密保持单 POV 限知，合法的感官与动作细节可以自然写；禁写的是越过 Plot/Card 的新重大事实，而非任何新颖词汇。写作后保存 v0，不覆盖历史 EP001。
4. 统一后置验证 `actual_visible_chars`, `required_beats_evidence`, `dialogue/action_presence`, `start/end`, `finish_reason`, `cost`；`stop` 只证明供应商完成本次返回，不能证明文本达标。
5. 如少许长度或节拍不足，基于**明确缺失节点**定点续写/修订；连续两次内容无改善应回 Plot/Card/Brief 修根因，而不是无限重抽。每一笔调用仍通过成本护栏。

**验收**：T-C01～C06；用旧 469 字节修订稿的字节 manifest 作为不合格烟测反例，**但实际字符数须读文本后再算**。任何欠产量必须写 `RETURN_UNDERPRODUCED`，不能降标签收。

### W07 — 按 CNW 原文落地三层审稿、五 Lens、三反证和遗漏核查

**原文锚**：`THREE_LAYER_REVIEW.md:11–19,40–77,100–136,140–170`; `templates/config/workflow.template.yml:4–26`。

**新代码**：`tools/cnw_lint.py`, `tools/cnw_review.py`, `tools/cnw_quality.py`；细节见 `spec/CNW_ROLE_INPUT_OUTPUT.md`。

**行动**：

1. Layer 1 **纯脚本**：中文常见排版/占位/残留指令/重复非文学格式；记录 rule ID、行、文本，不自动删除。
2. Layer 2 **纯脚本+上下文**：模板句型、空泛总结、重复、机械化转折、未演出的情绪抽象。只给候选，避开简单看见“愤怒/悲伤”等词就删。与作者英文 regex 示例一一对应**职责**而非照抄不适合中文的表达。
3. Layer 3 **五个相互独立的 DeepSeek 审稿请求**：Style/Character/Plot/Canon/Story-specific，每个只读相应 source 与本次完整 Draft。`story_specific` 从《苍歧》具体剧本设计/当前情节目的构造，不能复制示例小说“弱者被认作幕后黑手”的专用目标。
4. **三路对抗复核**：三个各自隔离 verifier 读同一待判问题和必要原稿，默认质疑；一项问题至少 2/3 复核未能反驳才进入修改队列。保留未通过的问题及其被证伪的理由；不能伪造“独立审查”。
5. **遗漏检查**：Completeness Critic 读全文+已确认/驳回问题，寻找整体缺漏，如连一整场戏都没有、Scene Card 的动作不见、完整对白丢失。问题要有具体来源和处理，不可仅输出 `none` 并宣布结束。
6. CritiCS 原 Image/Voice/Leader 对**本场实际引用的关键句段**继续执行，结果进 P0–P3 Revision Plan；不能用它抵销五个 CNW lens。文学问题以具体剧情功能为因；角色差异、对话趣味和叙事节奏都纳入 Story-specific/Character/Style 评价。

**验收**：T-D01～D05/D10；五个 lens 真实隔离 request ID；负例能各自发现相应缺陷，3 Verifier 的保留阈值明确；成本 reserve/settle 可追溯。不能靠 Writer 写 JSON 冒充模型响应。

### W08 — 修订完整度、再审、正式晋升及 Manuscript Index

**原文锚**：`templates/_workflows/03_revision.md:8–57`, `revision_plan.template.md`, `revision_log.template.md`、`THREE_LAYER_REVIEW.md:140–170`。

**行动**：

1. `tools/cnw_revision.py` 根据已确认的 issue 生成 P0/P1/P2/P3 修改计划；P0 Canon/因果、P1 阅读体验、P2 风格、P3 选项。未获合法来源支持的设定修改标 `NEEDS_AUTHOR_DECISION`，不得自动写进 Canon。
2. 修改时保留 original v0 + revision proposal v1 分别放 `07_draft` 与 `09_revision`，逐问题记从哪句修改到哪句。不是把全文缩成更短却“安全”的简述；对于批准在本场出现的合理观察细节不要只因未列明某个物件就全部删除。
3. v1 严格跑 `validate_contract`: 起止/POV/所有 beats/字符范围/人物区分/正文连续，修订缩短超过建议 25% 必须有削减理由且不得跨过最低合同；不用无意义扩写填字数。
4. `re-review` 只对改动牵涉的 Lens 运行新请求并检查全文必要上下文；没有影响的 NK、CritiCS/Plot 不重跑。原作者强调 Refine 引入新违规的风险，新旧文本必有 diff 与 `re_review` 实际结果。
5. Controller 对新版本接受后，`promote` 将已通过稿晋升到项目 `07_draft/episodes/<id>.md`（或 Scene 正本文档索引），先归档旧版本、更新 revision log、`manuscript_index`, current state，形成下一阶段正确输入；**不将候选文学内容反写为既定原剧本 Canon**。

**验收**：T-C04/C05/D06–D09，格式 pass/revise/rewrite 不是 Writer 自签。

### W09 — 新生产系统的非付费、跨 ID、完整 Episode 离线验收

**施工与测试**：为 `tools/cnw_runner.py` 和合同 validator 建 `tests/test_cnw_pipeline.py` + `tests/fixtures/`：

1. 两个完全虚构 scene，使用不同 ID、人物、目标字符和源锚，输出内容/路径/manifest 不得从旧 `EP001` 文件复制，不能只改标题。
2. 一个 Episode 有三张不同 Scene Card，合计长度由分场预算计算；对抗样本分别缺中间场景、缺结尾、只写摘要、角色提前泄密，都要 RETURN。
3. `render/promote/export` 在无 API key 下使用缓存完成（全新 PowerShell），HTML 安全离线可读，不含第三方脚本，导出不能硬编码思柔/J19/“腾空书案”。
4. 模拟五话 Sprint 的五份虚构合同，从 Plot→Review→Batch Summary→Next Sprint Handoff 验证状态机与批次汇总；仅此阶段做**非付费**模拟，不为证明“支持 Sprint”直接生成《苍歧》五话。
5. 运行 T-A01～E08 规定的反例；源 hash/合同 hash 变化后依赖正确失效；没有预算/Key 时自动拒绝；旧 `nk-start/nk-stop` 测试继续 PASS。

**验收**：每个被标“可复用”的入口至少两个不同项目 ID/作品单位的 dry-run 证据，不得拿旧 EP001 读取代替。此步只证明新工作流的执行基础，不宣称中国文学生产效果已通过。

### W10 — 唯一一次真实《苍歧》复测：相同 J19 插场，不越界扩量

**准入**：W00–W09 全部功能门已经 ACCEPT；现有 DeepSeek Key 在进程环境可用、当前活动预算保留空间；实际源稿锚能再次核对；未发第二场真实内容。

**行动**：

1. 按旧 P2-05 已确定插点 J19 第 555 行后、557 行玩法/坦白选项前再次读源稿，冻结完整场景合同，保证出场人物、台词称谓、知识边界、路线状态、J20 不变。旧 Plot/Scene Card 是受审参考，不盲重新给“怎么编剧”任务。
2. 用 CNW Plot、Card、Brief 确定本场**真实写作目标长度和动作分量**，Controller **先检查合同再发请求**；不复写原作者日文 5,000 为中文 5,000，也不准脚本私加 500–700。
3. NK 真实 POV 输出进入 Brief；CritiCS 如源身份和输入未变可复用以前合法批评证据，否则按差异有限执行。P3 的 11 阶段真实执行，出 v0、五个 Lens、三 verifier、completeness、CritiCS 实际结果、Revision v1 和 Re-review。
4. 审查有无小目标/行动/阻碍/回应/结果、人物语言能否区分、情节冲突是否成立、读者有无体验和下一锚是否严丝合缝；真实失败要写 `RETURN` 并定点修，而不是因为之前已经耗时过多降低标准。
5. 成本按供应商真实 usage 和现有价格快照估算，报告新增请求数；已成功的相同请求 ID 仅在实际输入/型号/模板相同条件下复用。不能编造一场“模型多次调用”等于高质量。

**验收**：新的修订稿必须按提前签收的字符/节拍合同完成；长度是必要非充分条件，必须同时通过 Canon、角色、演出、文学节奏和 CNW Review/Revision/re-review。旧百字 smoke 文本保留，但不能冒充本轮成果。

### W11 — 正式生产入口、不同 ID 验证、用户交付

**交付的最低结构**：

```text
runs/<run-id>/run_state.json                        # 私有断点/模型调用/费用
workspace/cangqi/07_draft/episodes/<id>.md           # 验收后章节正本（如对应 Episode）
workspace/cangqi/09_revision/<id>_revision_plan.md  # 分级修订计划
workspace/cangqi/08_review/<id>/*                   # 5 Lens/三 verifier/遗漏/复审
workspace/cangqi/07_draft/manuscript_index.md      # 持续写作索引
runtime/reference/cnw_97ad71fe5e5e/...             # 原作者本地逐字节参考

deliverables/cangqi/<run-id>/
  01_初稿.md
  02_修订稿.md
  03_前后文连读.md
  03_前后文连读.html
  04_修改说明.md
  05_复用操作说明.md
  06_原作者方法覆盖报告.md
  manifest.json
```

**最终冷启动验收**：全新 PowerShell 不带 Key 执行 `doctor/capture-reference/prepare/show-run/resume/export` 真实成功，文件 hash、状态、输入来源一致；只有 `produce --mode live` 在用户已允许的费用和目标内才执行真实 API。真实不同 ID 的新输入功能至少在两个离线 fixture 中被证明，且有本次《苍歧》新正式正文的真实供应商证据。

**产品完成的五个条件**：

1. 本机可读原作者固定源码与模板，`METHOD_COVERAGE` 每个必需环节从 `NOT_IMPLEMENTED` 变为 `TESTED`, 或明确因作者公开范围限制不能复制的项。
2. 真正能从新的 `contract` 生产新 Plot/Card/Brief/Prose/Review/Revision，不是只返回旧 `CHECKPOINT_REUSED`。
3. 原作者全流程文书与 5 Lens/3 Verifier/Completeness/Refine/Re-review 有运行证据；NK/CritiCS 各按自己的角色进入消费链。
4. 本轮的**唯一**《苍歧》场景在规模、行动、人物、节奏、前后连读上真实完整，且复用入口可再次执行。
5. Key/稿件不会进公开仓；新增费用没超过已批准剩余预算；所有 Controller 签收含真实源码 C/T、私有产物 hash 与审查范围。

W11 通过可以记录 `ENGINEERED_WORKFLOW_READY_FOR_USER_READING`；但在用户读过正文之前，**不能**记录 `USER_CREATIVE_ACCEPTED`。五话 Sprint 只跑过离线时，应写 `SPRINT_LIVE_NOT_RUN`，不把它伪装为真实五章生产业绩。

## 4. 逐阶段 Controller 判退重点（不滥增验收系统）

| 阶段 | 准入 → 离开条件 | Controller 必须重点审查 |
|---|---|---|
| W00 | 子模块 pinned → 原件 manifest | 真复制了，SHA/BLOB 对，没改上游 |
| W01 | 原件齐全 → 源码实际映射 | `M01–M38` 每项有函数/行号/缺口/测试，没复用错误证据 |
| W02 | W01 → P3 活动入口 | P2 历史状态没有被改写，产品未完成状态如实 |
| W03 | W02 → 合同冻结 | 中文规模、Scene/Episode、每场节拍、前后锚不是模型临时决定 |
| W04 | 合同 → 四岗位产物 | Plot/Card/Brief/Prose 的职责能从源码和文件一一追到原模板 |
| W05 | 四岗位合同 → 新可复用入口 | 新 ID 真执行，成本守卫/状态与缓存身份正确 |
| W06 | 新入口 → 正文生产 | 没 `500–700`、不以 stop 冒充正文完整、截断/欠产量能报错 |
| W07 | 正文 → 三层审稿 | 五 Lens、三 Verifier、Completeness 各真实独立，CritiCS 没顶替 |
| W08 | 审稿 → 修改+复审+晋升 | v0 不丢，v1 不得删掉关键戏，promotion 可追溯 |
| W09 | 实现完成 → 离线正负例全通过 | 第二 ID、多场 Episode、五话模拟、匿名源不污染实际《苍歧》 |
| W10 | 既有方法和费用准入 → 新正文 | 真正“一场戏”、规模/事件/风格都有，前后路线不变 |
| W11 | W10 → 可继续生产系统 | 真正新入口、动态导出、人能读，用户满意仍待用户 |

不得因为行号变化、文档标题、Meta 风格问题停工；应只为事实错误、源码逻辑错误、版权泄露、重要创作缺陷或无法恢复的费用风险退回。修 bug 只重验受影响的下游，已经通过的供应商请求不重放。

## 5. 本版不是“全部做完”的声明

此包**已经**完成：远端固定源资料研究、Git blob/源码位置核查、逐行缺口映射、可运行的本机资料提取器、完整施工/角色/测试合同。

此包的 P3 W00/W01 已在本地完成、经 Controller 接受并推送；W02–W11 仍按 `evidence/P3_CURRENT_STATE.md` 记录的状态执行。已下载工单不等价于“已部署原作者全套生产流”。
