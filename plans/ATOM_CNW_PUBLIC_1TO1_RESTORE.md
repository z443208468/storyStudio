# ATOM-CNW-PUBLIC-1TO1-RESTORE — 原作者公开工作流定点恢复执行单

> **施工文件。逐项执行。不要再编写第二份创作流程。不要让 Writer 设计替代方案。只修改已列明的执行路径和与其直接关联的机械故障。**
>
> **本 Atom 施工基线**：`main` 已推进至 W09 远端 ACCEPT（提交 `de49ef2…`）；W08/W09 的 `cnw_revision.py`、`cnw_sprint.py`、runner 和 `studio.ps1` 已有功能直接复用，不重做。
>
> **本 Atom 终点**：原 CNW 公开的逐话 11 阶段在 StoryStudio 中按相同职责、输入、顺序、输出与审稿/修订依赖真实贯通；附加 NK/CritiCS 不替代原阶段；同一《苍歧》J19 合同完成一次**真实**单场 E2E；代码提交并推送 `main`，提交与作品链接/私有路径交回当前 ChatGPT 审查。不得把单场验证声称为五话 Sprint 或完整 Episode 的 Live 验证。
>
> **来源边界**：复现原作者**公开发布的方法、模板、工作流文件**。作者未发布的私有 89-agent 内部源代码没有可复刻的字节实现；不得虚构该实现、虚称私有实现等价。允许用现有工程语言实现公开的 11 阶段语义；不得自行发明新的文学创作阶段或评价理论。

## 0. 锁定版本、执行身份和唯一黑名单

```text
REPOSITORY = D:\CangqiStudio\StoryStudio
REMOTE = z443208468/storyStudio
BRANCH = main
GITHUB_BASELINE_OBSERVED = de49ef2760cfe0c6bee36db0582b7cbef67d825b
CNW_PIN = 97ad71fe5e5e76a82275c6c63d4add06fb60ab6e
CNW_REFERENCE = runtime/reference/cnw_97ad71fe5e5e/
CNW_REFERENCE_MANIFEST = runtime/reference/cnw_97ad71fe5e5e/CNW_LOCAL_REFERENCE_MANIFEST.json
CNW_REFERENCE_MANIFEST_SHA256 = E9B989C52C66AB9BE8C73F09E84BC5BD7D2ECC92F9F1CBFC61BA300DC6CD3983
P3_1_PLAN = plans/MASTER_PLAN_P3_1.md
MODEL = deepseek-flash
BASE_URL = https://api.deepseek.com/v1
FIRST_LIVE_WORK_UNIT = workspace/cangqi/contracts/CQ-J19-INSERT-01.work_unit_contract.json
FIRST_LIVE_SCENE_TARGET = 1500 visible characters
FIRST_LIVE_SCENE_MIN = 1200 visible characters
FIRST_LIVE_SCENE_MAX = 1800 visible characters
ENGINEERING_REVIEWER = 当前已受委任只读 Controller
AFTER_PUSH_REVIEWER = 当前 ChatGPT 会话
```

**唯一禁止清单（BLACKLIST）；只禁止以下行为，不从遗漏的“允许事项”反推禁止，不另建白名单：**

```text
B01 禁止擅自改变 CNW 公开 11 阶段的创作职责、源模板语义、先后依赖、审稿判定方法；禁止以 NK/CritiCS/Controller 自评替换任一 CNW 环节。
B02 禁止修改 CNW 固定参考原件、改上游 pin、抹除参考哈希；只改 StoryStudio 适配层和项目实例。
B03 禁止删除仓库、删除 main、重写 Git 历史、force-push、reset --hard、clean -fd、覆盖现有未提交 W10 或其他 WIP、抹掉历史验收和原始证据。
B04 禁止将 Key、原始《苍歧》稿件、完整供应商 prompt/response、私有运行产物提交到公开 Git 或打印敏感凭据。
B05 禁止超出已有授权费用余额、变更供应商/模型/官方固定 host、绕过既有 reserve→send→settle 费用护栏。
B06 禁止把 mock/fixture/请求包冒充 live 结果，禁止伪造 provider ID、usage、验收签字、作者认可或用户创意认可。
B07 禁止自动将未确认设定、人物知识、分支后文、新情节升级为 Canon；禁止改变 J19 既有玩法和通向 J20 的路由状态。
B08 禁止以本 Atom 为由生产第二个《苍歧》真实场景、批量完整剧本、五话 Live Sprint；本次 Live 仅用已冻结 J19 单场合同。
B09 禁止新增专门为证明代码正确而创建的验证框架、验收服务、测试脚本、监控面板或重复 Reviewer；按现有工程治理、人工源码审查和真实 E2E 结果验收。
B10 禁止为减少阶段工作而降低作品合同字数、删除规定的原作者审稿步骤、把项目示例小说的作者专属主角设定/评分内容移植为《苍歧》创作法。
```

```text
OTHER_ACTIONS := NOT_BLACKLISTED
ON mechanical_error:
    determine failing existing file/function/call
    patch failing code or input in place
    rerun affected normal production step
    preserve previous successful calls/artifacts
    do not request user decision
    do not introduce additional stop/approval gates
ON banned_action:
    do not perform banned action
    select existing safe, non-destructive repair in same area
    continue current Atom
```

执行角色限定：Writer 仅修改与运行；既有 Controller 仅按已有治理审代码差异、上游对照、源/费用/隐私；任何创作质量和最终 Atom 成功均在推送后交当前 ChatGPT 查实际作品；Writer 不自行宣布 Atom 终验通过。

## 1. 逐文件读取原作者公开方法；保留原始来源

### 1.1 直接读取本地参考原件

```powershell
Set-Location 'D:\CangqiStudio\StoryStudio'
git branch --show-current
git rev-parse HEAD
git status --short --untracked-files=all
git -C third_party/claude-novel-workflow rev-parse HEAD
Get-FileHash 'runtime/reference/cnw_97ad71fe5e5e/CNW_LOCAL_REFERENCE_MANIFEST.json' -Algorithm SHA256
```

逐个读取以下路径的**完整正文**，不能仅看 README 摘要，不得修改：

```text
runtime/reference/cnw_97ad71fe5e5e/README.md
runtime/reference/cnw_97ad71fe5e5e/CLAUDE.md
runtime/reference/cnw_97ad71fe5e5e/docs/ARCHITECTURE.md
runtime/reference/cnw_97ad71fe5e5e/docs/GETTING_STARTED.md
runtime/reference/cnw_97ad71fe5e5e/docs/EXISTING_PROJECT_IMPORT.md
runtime/reference/cnw_97ad71fe5e5e/docs/HOW_TO_ADAPT.md
runtime/reference/cnw_97ad71fe5e5e/docs/THREE_LAYER_REVIEW.md
runtime/reference/cnw_97ad71fe5e5e/docs/HANDOFF.md
runtime/reference/cnw_97ad71fe5e5e/templates/CLAUDE.md
runtime/reference/cnw_97ad71fe5e5e/templates/config/ai_roles.template.yml
runtime/reference/cnw_97ad71fe5e5e/templates/config/workflow.template.yml
runtime/reference/cnw_97ad71fe5e5e/templates/06_plot/plot.template.md
runtime/reference/cnw_97ad71fe5e5e/templates/05_scene_cards/scene_cards.template.md
runtime/reference/cnw_97ad71fe5e5e/templates/07_draft/writing_brief.template.md
runtime/reference/cnw_97ad71fe5e5e/templates/08_review/batch_review.template.md
runtime/reference/cnw_97ad71fe5e5e/templates/09_revision/revision_plan.template.md
runtime/reference/cnw_97ad71fe5e5e/templates/09_revision/revision_log.template.md
runtime/reference/cnw_97ad71fe5e5e/templates/_workflows/README.md
runtime/reference/cnw_97ad71fe5e5e/templates/_workflows/01_first_import.md
runtime/reference/cnw_97ad71fe5e5e/templates/_workflows/02_incremental_update.md
runtime/reference/cnw_97ad71fe5e5e/templates/_workflows/03_revision.md
runtime/reference/cnw_97ad71fe5e5e/templates/_workflows/04_canon_audit.md
runtime/reference/cnw_97ad71fe5e5e/templates/_workflows/05_handoff.md
runtime/reference/cnw_97ad71fe5e5e/example_project/00_meta/episode_production_manual.md
runtime/reference/cnw_97ad71fe5e5e/example_project/00_meta/manuscript_review_rubric.md
```

原 `templates/_workflows/01–05` 是**项目维护辅助程序**，不是替代 `workflow.template.yml` 中的逐话 11 阶段；保留二者独立。原作者示例 `episode_production_manual.md` 中普通一话约 5,000 日文字符、弹性约 4,000–8,000 日文字符；不得把该数值直接写成《苍歧》中文单场字符数。本场严格沿用已冻结的 1500/1200–1800 合同。

### 1.2 固定 11 阶段合同（从原 `workflow.template.yml` 抄取）

```yaml
workflow:
  per_chapter:
    stages:
      - plot
      - scene_cards
      - writing_brief
      - prose
      - lint_layer1
      - lint_layer2
      - multi_lens_review
      - adversarial_verify
      - completeness_critic
      - refine
      - re_review
  lenses: [style, character, plot, canon, story_specific]
  adversarial:
    verifier_count: 3
    refute_default: true
    threshold: 2
```

把 `NK perspective`、`CritiCS plot critique`、`CritiCS text refine`、`promote`、`export`、`resume` 记录为**附加工具/产物动作**；不得列为第 12 个 CNW 原创作阶段，不得替代原角色、改变原始 11 阶段的业务顺序。此前 W00–W09 的已签收成果保留为历史，后续只改差异代码。

## 2. 逐项源码映射与唯一修改位置

| 编号 | 作者原件与章节 | 当前 StoryStudio 位置 | 指定修改动作 |
|---|---|---|---|
| S01 | `templates/config/workflow.template.yml` | `tools/cnw_runner.py:STAGES` | 用 11 个原阶段作为 `CNW_STAGES`；`pov` 移出 CNW 阶段序列；`promote/export` 移到后处理动作 |
| S02 | 同上 + `docs/ARCHITECTURE.md` 阶段顺序 | `tools/cnw_runner.py:stage_predecessors` | 设置 Plot→Cards→Brief→Prose→L1→L2→五 Lens→反证→遗漏→Refine→复审的实际依赖 |
| S03 | `templates/config/ai_roles.template.yml:plot_agent.reads` | `tools/cnw_roles.py:build_role_packet` | Plot 显式读取 `04_chapter_design/arc_*.md`,`90_canon/canon.md`,`90_canon/character_bible.md` |
| S04 | 同上 `scene_card_agent.reads` | 同文件 | Cards 显式读取已核准 Plot、Character Bible；各 Scene 字段按原模板写 |
| S05 | 同上 `brief_agent.reads` | 同文件 | Brief 显式读取 Plot、Cards、Character Bible、Style Guide；NK 输出只能附注 |
| S06 | 同上 `prose_agent.reads` | `cnw_roles.py:build_prose_input_view` + `cnw_generate.py` | Prose 只拿 Brief 与当场参演角色声线；其余依赖不作为写作者自由输入 |
| S07 | `templates/06_plot/plot.template.md` | `prompts/cnw/plot.md`; `cnw_roles.validate_role_output` | 按原模板章节写 Plot；机器记录独立存 sidecar，不把 `CNW_BEAT` 作为文学文本字段 |
| S08 | `templates/05_scene_cards/scene_cards.template.md` | `prompts/cnw/scene_cards.md`; `cnw_roles.py` | 场景逐张列 Identity/Cast/Start/End/Required/Forbidden/Sensory/Tone/Connection |
| S09 | `templates/07_draft/writing_brief.template.md` | `prompts/cnw/brief.md`; `cnw_roles.py` | 把所有 Card 转为逐场 `Goal/Open/Required/Forbidden/End/Approximate length`，并保留 Active Canon/Voice/Hard Constraints |
| S10 | 原 CNW 四岗位输入合同 | `tools/cnw_runner.py` | **先取得 NK Sidecar 后生成 Brief**；避免当前 Brief 在 `pov` 之前但又要求 NK 的倒置 |
| S11 | NK 原 `generate-perspective` 与 CNW Cards | `tools/cnw_nk_adapter.py:build_nk_payload` | 以已接受 Scene Cards 的真实事件/动作/次序构造 NK 请求，不以合同目标语句代替场景卡内容 |
| S12 | 原 `writing_brief` + CNW Prose | `tools/cnw_generate.py` | 从 Brief 合同读 Scene 长度、节拍；沿现有成本护栏完成真实内容，不新增 500–700 字指令 |
| S13 | `THREE_LAYER_REVIEW.md:11–59` | `tools/cnw_lint.py` | 保留两层纯本地脚本、候选报告，不因检测词汇自动删除正文 |
| S14 | `THREE_LAYER_REVIEW.md:69–77` | `tools/cnw_review.py:LENSES/REQUIRED_SOURCES` | Style 显式读取 `style_guide + forbidden_patterns`；Canon 显式读取 `glossary + timeline + world_bible`；其他 Lens 对原角色读取集 |
| S15 | `THREE_LAYER_REVIEW.md:100–116` | `tools/cnw_review.py:verifier_packets/tally_verifiers` | 三种原作者反证角度独立上下文，`>=2/3` 未反驳才进入确认问题 |
| S16 | `THREE_LAYER_REVIEW.md:124–136` | `tools/cnw_review.py:completeness_packet` | 输入全文、存活与被驳回的问题、来源；遗漏补充到同一次修订队列；结果不冒充完成 |
| S17 | `THREE_LAYER_REVIEW.md:140–169` | `tools/cnw_revision.py`; `tools/cnw_runner.py` | 依问题修改同一完整稿，受影响 Lens 复审，保留版本及来源 |
| S18 | 上游 L1/L2 的本地执行属性 | `tools/cnw_runner.py:verify_live` | 把 L1/L2 视为**本地阶段**，不得要求不存在的 provider receipt |
| S19 | 上游 Lens/反证任务数及内容 | `tools/cnw_runner.py:_validate_review_call_coverage` | Lens 5 个；反证按实际 findings × 3 的任务身份；零问题时保留空集合而非伪造三次请求 |
| S20 | `templates/_workflows/01_first_import.md` | `tools/cnw_project.py:import_source` | 补来源清单、章节场景划分、Canon 候选到公开模板结构的映射；不自动确认未知事实 |
| S21 | `templates/_workflows/02_incremental_update.md` | `tools/cnw_project.py` | 在现有导入函数上增加增量更新命令/记录；冲突只写 unresolved，不自行调和 |
| S22 | `templates/_workflows/03_revision.md` | `tools/cnw_revision.py` | 保留 v0、修订候选、P0–P3 修订计划、作者晋升动作；不以安全清单将戏缩成梗概 |
| S23 | `templates/_workflows/04_canon_audit.md` | `tools/cnw_project.py` | 添加人工/模型工作流入口，以原文规定的 source A/B + line 范围输出冲突，不改 Canon |
| S24 | `templates/_workflows/05_handoff.md` | `tools/cnw_project.py` | 生成有原文指针的简短 handoff 到 `93_exports/`，不另造总结理论 |
| S25 | `episode_production_manual.md` + `manuscript_review_rubric.md` | `tools/cnw_revision.py`, 项目 `00_meta/` | 用原作者 `fatal→pass/revise/rewrite→重点修订` 结构；示例小说专属评分项不得复制给《苍歧》 |
| S26 | `batch_review.template.md`, `workflow.template.yml` sprint | `tools/cnw_runner.py:sprint_run` | 按五话一组汇总，包含逐话结果、连贯性与下一 Sprint 交接；本 Atom 不发五话真实调用 |
| S27 | 原作者稿件 `07_draft/episodes/` 与 `09_revision/` | `tools/cnw_runner.py:promote_run/export_run`（复用 W08 已实现的 `bind_accepted_review_outputs`、`cnw_revision.promote_revision`）; `tools/studio.ps1` | 仅在正式复审及作者接受后晋升；完整新稿动态导出，不重用 P2 EP001 写死文案 |
| S28 | 工程事实检查而非 CNW 额外审稿 | `tools/cnw_runner.py:verify_live` | 分离 Provider/Local/Hook 凭据；只核对**正常运行产生的证据**，不另开发审稿测试系统 |
| S29 | 固定模型接入与已有成本治理 | `tools/p2_cost_guard.py`, `tools/cnw_runner.py` | 复用唯一账本和真实 DeepSeek API；不得新建平行计费与自评服务 |
| S30 | 原 CNW 方法与用户治理 | `AGENTS.md`, `evidence/P3_CURRENT_STATE.md` | 将本 Atom 作为 P3.1 的定点恢复覆盖条款；保留全部既有 W00–W09 接受记录及当前 W10／其他 WIP |


## 3. 先保护当前 W10／其他 WIP，再定点施工

```powershell
Set-Location 'D:\CangqiStudio\StoryStudio'
$AtomStart = (git rev-parse HEAD).Trim()
$AtomTree = (git rev-parse 'HEAD^{tree}').Trim()
$StatusBefore = git status --porcelain=v1 --untracked-files=all
$Out = 'runtime/private/atom-cnw-public-1to1'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
[IO.File]::WriteAllText((Join-Path $Out 'baseline.txt'),("BASE_C=$AtomStart`nBASE_T=$AtomTree`n" + ($StatusBefore -join "`n")),[Text.UTF8Encoding]::new($false))
git diff --binary > (Join-Path $Out 'worktree-before.patch')
git diff --cached --binary > (Join-Path $Out 'index-before.patch')
```

```text
read actual worktree files named in §§4–9
preserve current uncommitted W10 or other WIP byte-for-byte
reuse current W08/W09 committed code in place; preserve any uncommitted W10 implementation
never reset/rebase/recreate clean branch
never mark old W00–W09 history undone
append this Atom to current governance/state without replacing P2/P3/P3.1 historical text
```

预计直接涉及下列现有文件；**本表只定位施工点，不构成修改权限白名单，其他黑名单之外的机械修复可直接修改必要文件**。W08/W09 已推送的 `cnw_revision.py` / `cnw_sprint.py` 要复用当前版本；若同名文件存在 W10 WIP 就地修改并保留进度：

```text
AGENTS.md
config/cnw_production_policy.json                # 只改运行/来源字段，不增文学理论
prompts/cnw/{plot,scene_cards,brief,prose}.md
src: tools/cnw_runner.py
src: tools/cnw_roles.py
src: tools/cnw_nk_adapter.py
src: tools/cnw_critics_adapter.py                # 只修必要的 hook 调用，不换 CritiCS 内核
src: tools/cnw_generate.py
src: tools/cnw_review.py
src: tools/cnw_lint.py                           # 仅输入规则/输出候选的必要改动
src: tools/cnw_revision.py
src: tools/cnw_project.py
src: tools/studio.ps1
src: tools/p2_cost_guard.py                     # 保留现有 ledger，除直接接线故障不改算法
tools/cnw_sprint.py                          # 当前 W09 已存在，保持离线 Sprint 成果
reviews/P3_METHOD_COVERAGE.md
reviews/P3_1_DIFF_AUDIT.md                     # 只追加本 Atom 实际差异
reviews/P2_ACCEPTANCE_LOG.md                  # 只追加实际签收与回读
plans/ATOM_CNW_PUBLIC_1TO1_RESTORE.md          # 当前本文件原样存档
```

## 4. `tools/cnw_runner.py`：直接替换阶段依赖和执行器

### 4.1 替换 `STAGES / STAGE_ALIASES / STAGE_PROMPTS`（原第 27–32 行附近）

```python
# CNW 作者 `templates/config/workflow.template.yml` 原有 11 阶段。
CNW_STAGES = (
    "plot", "scene_cards", "writing_brief", "prose",
    "lint_layer1", "lint_layer2", "multi_lens_review",
    "adversarial_verify", "completeness_critic", "refine", "re_review",
)
STAGES = CNW_STAGES  # 兼容已有 produce/step/state 初始化中使用 STAGES 的调用点

# 非 CNW 原创作阶段；仅用于真实附加工具/文件操作。
SUPPORT_HOOKS = ("nk_pov", "critics_plot", "critics_text")
POST_ACTIONS = ("promote", "export", "resume", "sprint")

LEGACY_ALIASES = {
    "cards": "scene_cards", "brief": "writing_brief", "draft": "prose",
    "lint1": "lint_layer1", "lint2": "lint_layer2",
    "lens5": "multi_lens_review", "verifier3": "adversarial_verify",
    "completeness": "completeness_critic", "re-review": "re_review",
}
STAGE_PROMPTS = {
    "plot": "plot.md", "scene_cards": "scene_cards.md",
    "writing_brief": "brief.md", "prose": "prose.md",
}
PROVIDER_STAGES = {
    "plot", "scene_cards", "writing_brief", "prose",
    "multi_lens_review", "adversarial_verify",
    "completeness_critic", "refine", "re_review",
}
LOCAL_STAGES = {"lint_layer1", "lint_layer2"}
```

```python
# 修改 normalize_stage(value)：
if value in CNW_STAGES: return value
if value in LEGACY_ALIASES: return LEGACY_ALIASES[value]
# 仅在读取旧 run 时识别旧 `pov` 记录：迁入 state['support_hooks']['nk_pov']。
# 不把 `pov` 输出为当前新 run 的 CNW 阶段。
```

### 4.2 替换 `stage_predecessors(stage, unit_kind)`（原第 166–175 行附近）

```python
def stage_predecessors(stage, unit_kind):
    stage = normalize_stage(stage)
    order = CNW_STAGES
    index = order.index(stage)
    # 原作者全顺序不因 Scene/Episode 改动；Scene 只是本次 E2E 的单位。
    return tuple(order[:index])

# 在 step/runner 中另记内容依赖，不新增阶段：
# plot reads arc/canon/characters
# scene_cards reads plot/characters
# writing_brief reads plot/cards/character_bible/style_guide
# prose reads writing_brief/voice_samples
# lint_layer1 & lint_layer2 read full prose
# multi_lens_review reads full prose and lens-specific sources
# adversarial_verify reads actual reviewer findings + relevant evidence
# completeness_critic reads entire prose + all prior finding dispositions
# refine reads full draft + confirmed findings
# re_review reads complete revised draft + changed portions and affected lenses
```

迁移旧 `run_state.json` 时仅**新增兼容读取层**：

```python
legacy_keys = dict(old_state.get("stages", {}))
for old_name, record in legacy_keys.items():
    if old_name == "pov":
        state["support_hooks"]["nk_pov"] = copy(record)
    elif old_name in LEGACY_ALIASES:
        state["stages"][LEGACY_ALIASES[old_name]] = copy(record)
    else:
        state["stages"][old_name] = copy(record)
# 保留 old_state 原始副本；不把旧 mock ACCEPT 晋升为新的 LIVE 完成。
```

### 4.3 修改 `_step_locked / step / _mark_stage_locked`（原第 330–406 行附近）

```python
def step(args):
    run = open_locked_existing_run(args.run_id, args.project_root)
    stage = normalize_stage(args.stage)
    required_artifacts = stage_input_artifacts(run, stage)
    # 从原角色文件/本场契约/真实前序产物生成输入；不写空白通用占位符。
    fp = sha256(stage + contract_sha + source_sha + prompt_sha + input_hashes)
    if existing stage has identical fp and completed real artifact:
        return existing real artifact and receipt  # 不重复收费
    repair_invalidated_consumers_only(stage)
    out = execute_cnw_stage(run, stage, required_artifacts)
    persist(out, raw, stage_input_hash, stage_output_hash, provider_receipts_if_any)
    advance_to_next_author_stage(stage)
    return out

# `mark_stage` 仅供读取历史或离线 fixture；真实运行用 execute_cnw_stage
# 记录 `STAGE_MATERIALIZED` 表示正常生成完成；不得记 `USER_CREATIVE_ACCEPTED`。
# 不为每个 Plot/Card/Brief 的创作步骤新增 Codex Controller 单独批准。
```

### 4.3A 移除现有每岗位外审才能前进的额外创作门（`_step_locked / cnw_roles.verify_stage_chain`）

```python
# 当前 `_step_locked` 第 343–345 行的 `dependency.status != "ACCEPTED"`
# 改为核对已经落地的真实前序产物；本 Atom 只保留工程 Controller 一次审源码与真实结果。
def has_materialized_dependency(stage_record, run):
    path = private_artifact_path(stage_record["artifact"]["path"])
    return (
        stage_record["status"] == "STAGE_MATERIALIZED"
        and path.is_file()
        and sha256_file(path) == stage_record["artifact"]["sha256"]
        and stage_record["contract_sha256"] == run["contract_sha256"]
    )

# `tools/cnw_roles.py:verify_stage_chain` 中，生产版用已落地 Plot/Card/Brief
# 与其源和模型回执代替 `CONTROLLER_ACCEPTED` 字段；
# `CONTROLLER_ACCEPTED` 仍可作为既有历史兼容记录，但不能强制逐创作岗位再等审批。
# `tools/cnw_generate.py:validate_accepted_prose_inputs` 的 brief_stage_status
# 读取 `STAGE_MATERIALIZED` 和 hash，而不依赖 Codex Controller 对文学正文预签。
# `verify_live` 也检查 STAGE_MATERIALIZED + 真正原文/回执，不检查个人自评 ACCEPT。
```

### 4.4 实装当前 `produce(... mode='live')`（原第 228–230 行）

```python
def produce(args):
    contract = load_current_source_bound_contract(args.contract)
    project = existing_private_project(args.project_root)
    run = create_or_resume_unique_run(project, args.run_id, contract)
    run["cnw_method_source"] = {
        "commit": "97ad71fe5e5e76a82275c6c63d4add06fb60ab6e",
        "workflow_blob": "146ea01a484cc0578cf290478b3941599ad7fb15",
    }
    run["cnw_stages"] = list(CNW_STAGES)
    run["support_hooks"] = {}
    run["mode"] = args.mode
    run["next_stage"] = first_unfinished(CNW_STAGES)
    save_state(run)
    if args.mode == "live":
        run_remaining_cnw_stages(run)   # 在现有 runner 实装，禁止空结果 `READY` 冒充执行
    return run_summary(run)
```

### 4.5 在本文件补 `execute_cnw_stage` 的精确分发

```python
def execute_cnw_stage(run, stage, inputs):
    if stage == "plot":               return execute_plot(run, inputs)
    if stage == "scene_cards":        return execute_scene_cards(run, inputs)
    if stage == "writing_brief":      return execute_writing_brief(run, inputs)
    if stage == "prose":              return execute_prose(run, inputs)
    if stage == "lint_layer1":        return execute_lint(run, "surface")
    if stage == "lint_layer2":        return execute_lint(run, "structural")
    if stage == "multi_lens_review":  return execute_five_lenses(run, inputs)
    if stage == "adversarial_verify": return execute_three_verifiers(run, inputs)
    if stage == "completeness_critic":return execute_completeness(run, inputs)
    if stage == "refine":             return execute_refine(run, inputs)
    if stage == "re_review":          return execute_targeted_re_review(run, inputs)
```

### 4.6 复用当前 `p2_cost_guard.py` 实装统一真实模型调用（放入现有 runner 内，不新建模型代理平台）

```python
def cnw_live_call(run, *, stage, role_id, prompt_messages, output_cap):
    request_id = unique_uuid()
    input_sha = sha256(canonical_json(prompt_messages))
    reserve = p2_cost_guard.command_reserve(Namespace(
        request_id=request_id,
        run_id=run.id,
        purpose=f"CNW {stage}/{role_id}",
        input_token_cap=known_prompt_token_cap(prompt_messages),
        output_token_cap=output_cap,
    ))
    # 原始 ledger 写入当前既有 runtime/private/p2-cost-ledger.json。
    # 不额外创建计费数据库，不为单次请求增加多个内层 SDK 重试。
    try:
        result = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url="https://api.deepseek.com/v1",
            max_retries=0,
            timeout=180,
        ).chat.completions.create(
            model="deepseek-flash", messages=prompt_messages,
            max_tokens=output_cap,
            extra_body={"thinking": {"type": "disabled"}},
        )
        raw = result.model_dump(mode="json")
        remove_secret_fields_and_reasoning_content(raw)
        raw_path = PRIVATE_RUN / "provider" / f"{request_id}.json"
        atomic_write_utf8(raw_path, json.dumps(raw, ensure_ascii=False))
        p2_cost_guard.command_settle(Namespace(
            request_id=request_id, provider_request_id=result.id,
            returned_model=result.model,
            finish_reason=result.choices[0].finish_reason,
            input_tokens=result.usage.prompt_tokens,
            output_tokens=result.usage.completion_tokens,
        ))
        content = result.choices[0].message.content or ""
        receipt = {
            "stage": stage, "role_id": role_id, "request_id": request_id,
            "provider_request_id": result.id, "model": result.model,
            "finish_reason": result.choices[0].finish_reason,
            "usage": result.usage.model_dump(),
            "input_sha256": input_sha, "output_sha256": sha256(content),
            "raw_response_path": relative_to_run(raw_path),
            "raw_response_sha256": sha256_file(raw_path),
            "ledger_settlement": find_settled_ledger_row(request_id),
        }
        append_receipt_to_existing_run_state_under_locked_run(receipt)
        return content, receipt
    except Exception as exc:
        reconcile_or_keep_existing_reserved_amount_as_UNKNOWN_NOT_ZERO(request_id)
        record_mechanical_failure_without_faking_success(exc)
        repair_this_failed_stage_and_retry_using_existing_identity_if_billed()
        # 不取消本 Atom，不越过黑名单边界。
```

实装 `stage_input_artifacts` 时使用相邻产物的实际 UTF-8 内容及路径，不把 `run_state.json` 元数据当正文。各阶段输出至少保存：

```text
runs/<run-id>/run_state.json
runs/<run-id>/artifacts/plot.md
runs/<run-id>/artifacts/scene_cards.md
runs/<run-id>/artifacts/writing_brief.md
runs/<run-id>/artifacts/prose.v0.md
runs/<run-id>/artifacts/lint_layer1.json
runs/<run-id>/artifacts/lint_layer2.json
runs/<run-id>/artifacts/multi_lens_review.json
runs/<run-id>/artifacts/adversarial_verify.json
runs/<run-id>/artifacts/completeness_critic.json
runs/<run-id>/artifacts/refine.v1.md
runs/<run-id>/artifacts/re_review.json
runs/<run-id>/provider/<request_id>.json
```

### 4.7 修改 `verify_live`（原第 479–557 行附近）

```python
def verify_live(args):
    state = load_current_run(args.run_id)
    for stage in CNW_STAGES:
        assert actual stage artifact exists and content hash equals state record
        assert normal stage execution result corresponds to this input hash

    # 本地阶段：仅检查其本来就有的命中/上下文/全文哈希；绝不要求 API 回执。
    for stage in ("lint_layer1", "lint_layer2"):
        assert stage result identifies local deterministic runner and source text SHA
        assert stage not counted among supplier-request stages

    # 模型阶段：按真实调用数逐条校对，不强行每阶段恰好只发 1 次。
    for receipt in state.provider_requests:
        assert status and model and request ID and response ID and input/output hashes
        assert original provider JSON matches receipt ID/model/finish reason/usage
        assert existing p2 ledger has matching SETTLED record (usage absent preserves held amount)
        assert receipt.role belongs to its author stage

    assert {r.role_id for r in receipts_of("multi_lens_review")} == {
        "style", "character", "plot", "canon", "story_specific"
    }
    actual_findings = collect_findings_from_live_lenses_and_contextual_lint()
    for finding_id in ids(actual_findings):
        assert {r.role_id for r in receipts_of("adversarial_verify", finding_id)} == {
            "correctness", "character_consistency", "continuity_plausibility"
        }
    if not actual_findings:
        assert stage_artifact("adversarial_verify").status == "NO_FINDINGS_TO_VERIFY"
        assert receipts_of("adversarial_verify") == []
    assert stage_artifact("completeness_critic") incorporates actual confirmed and rejected findings
    assert final revision and re_review come from current draft, not prior EP001
    return REAL_STAGE_CHAIN_COMPLETE_WITH_PRIVATE_ARTIFACT_POINTERS
```

删去旧实现 `pipeline.append('pov')`、`if stage not in receipts_by_stage => missing` 对本地 lint 的判断、`_validate_review_call_coverage` 固定恰好三条 verifier 全局回执的假设。保留原有原始响应对账、费用对账代码，不重建第二套校验框架。

### 4.8 修改 `register_editorial_candidate / promote_run / export_run`（原第 415–462 行）

```python
# review_run：输出正常作品的待审预览、真实来源与 11 阶段产物路径；不自签。
# export_run：读取当前 run 的 v0/v1 和前后文，直接导出候选 HTML/MD/TXT，
#             不把 promote 当作“用户尚未读到候选稿”的先决条件。
# promote_run：必须保留原作者 `_workflows/03_revision.md` 所规定的人工批准。
#              已有 Controller 工程审核不能伪称用户阅读后批准。
#              只允许作者真正接受后更新 07_draft/episodes 正本和 manuscript_index。
# sprint_run：直接复用 W09 已提交的 tools/cnw_sprint.py:run_fixture_sprint，
#             读取恰好五个现有章节完成稿与批评结果，
#             输出 08_review/epXXX-epYYY_batch_review.md 与下期 handoff。
#             `templates/config/workflow.template.yml` 默认 size=5, min_score=75,
#             max_p0_findings=0, max_p1_findings=2；示例作者自己作品手册里
#             `>=80` 的标准只属于其示例小说，不覆盖本项目的模板默认参数。
#             本 Atom 不自动对五篇发起 Live 创作。
```


## 5. `tools/cnw_roles.py` + `prompts/cnw/*.md`：恢复四岗位的原文件读取合同

### 5.1 改 `ROLE_FILES / UPSTREAM_METHOD / build_role_packet`（原第 17–18、65–171 行）

```python
AUTHOR_ROLE_READS = {
    "plot": (
        "04_chapter_design/arc_<NN>.md",
        "90_canon/canon.md",
        "90_canon/character_bible.md",
    ),
    "cards": (
        "06_plot/<work_id>_plot.md",
        "90_canon/character_bible.md",
    ),
    "brief": (
        "06_plot/<work_id>_plot.md",
        "05_scene_cards/<work_id>_scene_cards.md",
        "90_canon/character_bible.md",
        "92_style_engine/style_guide.md",
    ),
    "prose": (
        "07_draft/<work_id>_writing_brief.md",
        "92_style_engine/character_voice_samples.md",  # 只选当场发声人物
    ),
}

# 须实际读取上述文件正文；不能仅发送其 SHA 或一个未证实覆盖完整内容的 canon_scope。
# `source_anchors`/合同/policy 只能作为工程身份或《苍歧》额外事实，不可替换原作者必读文件。
# 没有单独 Arc 文件的现有《苍歧》单场，从既有 Act/已签收 Plot 与源锚
# 填写项目 `04_chapter_design/arc_*.md`，只写已经有来源的角色、位置、剧情功能；不添新 Canon。

def build_role_packet(role, contract_path, inputs, accepted_receipts=None, mode="offline"):
    source = load_source_bound_contract(contract_path)
    required = AUTHOR_ROLE_READS[role]
    materials = read_actual_texts(project_root, required, work_id=source.unit.id)
    compare_chapter_and_scene_identity(materials, source)
    original_template = read_pinned_upstream_template(ROLE_TO_AUTHOR_TEMPLATE[role])
    return {
        "role": role,
        "author_template_source": pinned_file_and_blob(role),
        "author_template_text": original_template,
        "materials": materials, "materials_sha256": per_file_actual_hash(materials),
        "source_contract": source.minimal_execution_metadata,
        "candidate_extra": optional_project_source_anchors_and_NK_support(role),
    }
```

### 5.2 改 `validate_role_output`（原第 172–206 行）

```python
def validate_role_output(role, contract, markdown, metadata):
    # 原作 Markdown 模板完整保留；machine 元数据存同阶段 `*.meta.json`。
    if role == "plot":
        required_sections = [
            "Identity", "Role in the Arc", "Key Scenes", "Hook",
            "Required Story Beats", "Forbidden Items", "Connections", "Target Length"
        ]
    if role == "cards":
        required_sections = [
            "Identity", "Cast", "Start state", "End state", "Required beats",
            "Forbidden items for this scene", "Sensory anchor", "Tone / pacing",
            "Connection to next scene"
        ]
    if role == "brief":
        required_sections = [
            "Quick Header", "Active Canon", "Scene-by-Scene Instructions",
            "Voice References", "Hard Constraints", "Style Targets",
            "What NOT to include in the prose"
        ]
    check_original_markdown_sections(markdown, required_sections)
    match_source_beat_ids_and_length(contract, metadata)
    preserve_markdown_prose_without_machine_footer()
    write_same_stage_sidecar_metadata(metadata)
```

下列现有机器标志不再作为 Plot/Card/Brief **原作者正文模板中的一部分**：

```text
CNW_CONTRACT target_visible_chars=...
CNW_BEAT B01 budget_visible_chars=...
```

这些机器标志移入 `artifacts/<stage>.meta.json`；当前已有 Markdown 中的标志作为历史输入兼容读取，但新生产 Markdown 不再插入。机器元数据只传工程校验，不传 Prose 文学正文。由 `contract + meta` 核对预算/beat，不因为漏机器标记要求文学模型重写一场已经完整的戏。

### 5.3 修改 `prompts/cnw/*.md`：以**原模板原文**为主提示词

```python
AUTHOR_TEMPLATE = {
  "plot": "templates/06_plot/plot.template.md",
  "cards": "templates/05_scene_cards/scene_cards.template.md",
  "brief": "templates/07_draft/writing_brief.template.md",
  "prose": "templates/config/ai_roles.template.yml",
}

def assemble_author_prompt(role, project_values):
    original = read_from_pinned_local_reference(AUTHOR_TEMPLATE[role])
    role_reading_list = read_from_pinned_local_reference(
        "templates/config/ai_roles.template.yml"
    )
    return original + "\n" + role_reading_list + "\n" + serialize_project_values(project_values)
```

`prompts/cnw/{plot,scene_cards,brief,prose}.md` 只保留上游源路径、blob、必要的中文项目输入字段映射；撤销任何自行发明的额外“几槽、特定情绪规则、固定 500–700 字、不得使用某类普通描写”等创作指令。原作者 Scene Card 的感官锚、人物即时欲求、情绪节奏**照原模板保留**；Canon 中没有的可逆舞台细节标注 `PROPOSED`，不因 Canon 没明文写物件就整段删除。

### 5.4 明确四岗位的真实输出文件

```text
plot agent       -> project/06_plot/<id>_plot.md
scene card agent -> project/05_scene_cards/<id>_scene_cards.md
brief agent      -> project/07_draft/<id>_writing_brief.md
prose agent      -> run/artifacts/prose.v0.md
```

输入相同且已有成功产物时复用现有 hash；输入变更只重跑受影响岗位。实现四岗位的真实模型调用时，统一从 §4.6 `cnw_live_call` 发送。上游模板章节列明的字段全部写出，不准以仅有机器字段的 JSON 伪装成作者的 Markdown 产物。

## 6. `tools/cnw_nk_adapter.py`：把 NK 从核心顺序移到 Brief 前的附加读取

### 6.1 改 `build_nk_payload`（原第 14–51 行）

```python
def build_nk_payload(contract, accepted_cards_markdown, accepted_cards_metadata):
    # 拿到真实 Scene Card 后才构造；禁止仅从 contract.required_beats[*].goal
    # 生造一份与已经写出的卡片无关的事件序列。
    ordered_scenes = extract_ordered_scenes_from_card_sections(accepted_cards_markdown)
    event_sequence = []
    for scene in ordered_scenes:
        for beat in scene.required_beats_in_document_order:
            event_sequence.append({
                "label": beat.beat_id,
                "description": compose_existing_card_text(
                    scene.start_state, beat.observable_action,
                    beat.response_or_obstacle, beat.resulting_change
                ),
            })
    return {
        "eventSequence": event_sequence,
        "perspectives": [{
            "id": f"{contract['unit']['id']}-pov-01",
            "narrator": contract["unit"]["pov"],
            "eventLabel": first_scene_label(ordered_scenes),
            "eventObjective": exact_scene_objective_from_card(ordered_scenes),
            "characterSnapshots": confirmed_current_stage_traits(ordered_scenes),
        }],
        "customPrompt": "只在指定 POV、当前来源与原 NK 任务范围内生成第一人称视角材料。",
    }

# 读取的 Scene Card source_sha256 随 NK request 同写在私有 run。
# 按 NK 原接口取得 `perspectives[].reflection`，原结果与 receipt 绑定。
```

### 6.2 改 `map_reflection_to_brief`（原第 53–93 行）

```python
def map_reflection_to_brief(brief_markdown, response, receipt):
    check_nk_original_schema(response)
    bind_nk_response_to_actual_card_hash(receipt)
    # `reflection` 只进 Brief 的支持附注，不修改 Plot、Scene Card、Canon。
    return append_support_note_to_brief(
        brief_markdown,
        section="NK Perspective Reflection (support only)",
        value=response["perspectives"][0]["reflection"],
        source_response_sha256=hash(response),
    )

# 执行位置固定：
# complete Scene Cards -> call NK -> generate Writing Brief (or append NK support note before freezing Brief)
# 绝不运行：complete Brief -> call NK -> pretend NK was already inside Brief
# NK 不是 CNW 原作者创作阶段，不进入 CNW_STAGES。
```

把 `cnw_runner.py` 中原 `pov` stage 的消费者指向 `support_hooks.nk_pov`，在 `execute_writing_brief()` 内完成 NK 输入、供应商调用、映射与 Brief 冻结；不另造第十二个“视角写作岗位”。Episode 单位每张 Card 各获取必要 POV 支持片段，依原卡逐项插入相应 Brief Scene；不得因 Episode 没 `pov` 阶段而丢失支持材料，也不得让它阻止 CNW 原作者仅凭四岗位原数据写作。

### 6.3 把既有 CritiCS 两个调用落在本来就有的 CNW 岗位内

```python
def execute_plot(run, inputs):
    plot_markdown, plot_receipt = cnw_live_call(
        run, stage="plot", role_id="plot_agent",
        prompt_messages=author_template_plus_actual_sources("plot", inputs),
        output_cap=existing_plot_budget_cap(),
    )
    persist_actual_author_plot_markdown(plot_markdown, plot_receipt)
    # 附加 CritiCS 原桥；不改 CNW 原始 plot_agent 的任务与产物。
    python = ROOT / "runtime/envs/critics-api/Scripts/python.exe"
    command = cnw_critics_adapter.build_plan_critique_command(
        python, current_plot_private_path(), f"{run.id}-critics-plot"
    )
    critique = invoke_existing_p2_06_critics_run_and_read_original_receipts(command)
    save_to(run.support_hooks["critics_plot"], critique)
    if critique_contains_actionable_original_plot_feedback(critique):
        proposal_command = cnw_critics_adapter.build_plan_revise_command(
            python, current_plot_private_path(), critique.original_json_path,
            f"{run.id}-critics-proposal"
        )
        proposed_plot = invoke_existing_p2_06_critics_run(proposal_command)
        save_proposal_separately_without_promoting_new_canon(proposed_plot)
        plot_markdown = apply_only_same_scene_source_bound_plot_fixes(
            plot_markdown, proposed_plot, original_card_constraints()
        )
    return plot_markdown

def supplemental_critics_text(run, full_v0, actual_review_findings):
    excerpt = select_source_referenced_excerpt_from_actual_findings(full_v0, actual_review_findings)
    if not excerpt:
        return persist_hook_result("NO_RELEVANT_EXCERPT")
    command = ["tools/p2_06_critics_run.py", "--action", "text-refine",
               "--input", private_excerpt_path(excerpt),
               "--run-name", f"{run.id}-critics-text"]
    result = invoke_existing_cost_guarded_critics_runner(command)
    save_to(run.support_hooks["critics_text"], result)
    append_as_supplementary_source_to_existing_revision_plan(result)
    # 原作者五 Lens/三反证/Completeness 不因它已运行而省略。
```

仅通过已部署 `tools/critics_bridge.py` 与 `tools/p2_06_critics_run.py` 真走原生 CritiCS 方法；保留原始返回、计费和拒用意见的事实。CritiCS 提出的额外场、新秘密及路线变化保留为被拒候选，不写进 CNW Plot 正本或 Canon。`supplemental_critics_text()` 放在 CNW 反证/Completeness 之后、`refine` 生成修改计划之前；其结果仅作补充材料，不作为 CNW 原作者审稿完成的替代凭据。

## 7. `tools/cnw_review.py`：完整恢复作者三层审稿与反证/遗漏顺序

### 7.1 替换 `LENSES / REQUIRED_SOURCES / VERIFIERS`（原第 11–18 行）

```python
LENSES = {
    "style": ("style_guide", "forbidden_patterns"),
    "character": ("character_bible", "voice_samples"),
    "plot": ("scene_cards", "writing_brief"),
    "canon": ("glossary", "timeline", "world_bible"),
    "story_specific": ("project_specific_canon",),
}
# 《苍歧》附加材料 source_anchors / knowledge_boundaries / chapter_contract
# 可随相应 Lens 一并提供；不能代替上述作者明确列出的原件。
VERIFIERS = (
    "correctness",
    "character_consistency",
    "continuity_plausibility",
)
```

每个 Lens 单独保存 `raw_prompt`, `input_source_hashes`, `raw_response`, `findings`, `request_id`, `provider_request_id`。各 Lens 使用独立会话，不接收其他 Lens 历史。按原作者 `THREE_LAYER_REVIEW.md` **五个 Lens 并行 fan-out**，同一问题的三个 Verifier 并行；在每笔请求出站前使用已有带文件锁的费用护栏独立预留，在已有 `locked_run` 内串行落盘状态。只把 CNW 文学审稿角色的实际在途上限设置为 Lens=5、同问题 Verifier=3，不更改 P2 已部署 NK/CritiCS 的在途策略，也不另建计费器。未能预留到现有预算的任务仍保留原队列，先完成不收费的机械修复/费用对账。

### 7.2 修改现有 `lens_packet`，不用 `mock_lens` 做真实生产

```python
def build_lens_input(lens_id, full_draft, project_paths):
    author_sources = load_each_actual_source_text(LENSES[lens_id])
    extra = load_project_specific_constraints_without_future_plot_leakage(lens_id)
    return {
        "lens_id": lens_id, "draft": full_draft,
        "sources": author_sources, "project_extra": extra,
        "author_lens_definition": read_pinned_THREE_LAYER_REVIEW_lens(lens_id),
    }

def execute_five_lenses(run, inputs):
    draft = read_full_current_v0(run)
    def call_one_lens(lens_id):
        packet = build_lens_input(lens_id, draft, current_project_paths(run))
        response, receipt = cnw_live_call(
            run, stage="multi_lens_review", role_id=lens_id,
            prompt_messages=two_messages(author_lens_prompt(lens_id), packet),
            output_cap=existing_safe_cap_for_this_run(),
        )
        return lens_id, normalize_original_finding_shape(response, receipt)
    # 原作者五个彼此独立、并行的 Lens；统一受既有费用锁与 run 状态锁管理。
    with ThreadPoolExecutor(max_workers=5) as pool:
        pairs = list(pool.map(call_one_lens, (
            "style", "character", "plot", "canon", "story_specific"
        )))
    results = dict(pairs)
    persist_original_lens_results_without_inventing_findings(results)
    return results
```

### 7.3 保留 L1/L2 本地脚本，不给 Writer “自动删情绪词”的权限

```python
def execute_lint(run, layer):
    text = read_full_current_draft(run)
    report = cnw_lint.lint(text, "surface" if layer == "surface" else "structural")
    persist_existing_local_report(report, hash(text))
    return report

# cnw_lint.py 保留两层 regex + 必要上下文；
# 命中“感到悲伤/仿佛/不是……而是……”只输出疑点、行号和语境；
# 不调用 OpenAI/DeepSeek、不自动删除/替换正文。
```

### 7.4 改 `verifier_packets / tally_verifiers`（原第 47–65 行）

```python
def verifier_packets(findings, full_draft, evidence_by_finding):
    packets = []
    for finding in findings:    # 每项审稿意见逐条对应三种反证角度
        for verifier in VERIFIERS:
            packets.append({
                "finding_id": finding["finding_id"],
                "verifier_id": verifier,
                "full_draft": full_draft,
                "claim": finding,
                "counter_evidence": evidence_by_finding[finding["finding_id"]],
                "instruction": "Try to refute the claim; under uncertainty choose refuted.",
            })
    return packets

def execute_three_verifiers(run, inputs):
    candidate_findings = gather_actual_lens_findings_and_contextual_candidates(run)
    if not candidate_findings:
        return persist_stage_result("NO_FINDINGS_TO_VERIFY", provider_requests=[])
    packets = verifier_packets(candidate_findings, full_draft(run), source_evidence(run))
    def call_one_verifier(packet):
        response, receipt = cnw_live_call(
            run, stage="adversarial_verify",
            role_id=packet["verifier_id"],
            prompt_messages=two_messages(author_verifier_prompt(packet["verifier_id"]), packet),
            output_cap=existing_safe_cap_for_this_run(),
        )
        return packet["finding_id"], packet["verifier_id"], response, receipt
    for finding in candidate_findings:
        group = [p for p in packets if p["finding_id"] == finding["finding_id"]]
        with ThreadPoolExecutor(max_workers=3) as pool:
            outcomes = list(pool.map(call_one_verifier, group))
        for finding_id, verifier_id, response, receipt in outcomes:
            record_vote_for_one_finding(finding_id, verifier_id, response, receipt)
    for finding in candidate_findings:
        votes = get_three_distinct_votes(finding.id)
        finding.status = "CONFIRMED" if count(v == "not_refuted" for v in votes) >= 2 else "REFUTED_OR_UNCERTAIN"
    persist_all_original_findings_votes_and_rejected_reason()
    return verified_vote_table
```

不要使用当前固定 `len(verdicts)==3` 作为**所有 findings 总共只能三个调用**的前提；这里 `len(verdicts)==3*len(findings)`。以实际 `finding_id + verifier_id` 对应请求，禁止用三条不对应具体问题的汇总 receipt 冒充 3×N 次反证。若原作者文档中某次对同一问题合并发送材料，保证每个 finding 仍各自具有三份独立反证和可核实输入；不能省略任何问题。

### 7.5 改 `completeness_packet` / 完整性模型步骤（原第 66–69、93–98 行）

```python
def execute_completeness(run, inputs):
    full_text = read_full_current_v0(run)
    confirmed, rejected = read_actual_adversarial_dispositions(run)
    payload = {
        "draft": full_text,
        "confirmed_findings": confirmed,
        "rejected_findings": rejected,
        "source_materials": read_project_specific_canon_and_cards(run),
    }
    response, receipt = cnw_live_call(
        run, stage="completeness_critic", role_id="completeness",
        prompt_messages=two_messages(author_completeness_prompt(), payload),
        output_cap=existing_safe_cap_for_this_run(),
    )
    extra_findings = extract_original_omission_findings(response)
    append_to_refine_queue(extra_findings)
    for finding in extra_findings:
        add_future_lens_prompt_note_to_project_style_or_review_material(finding.category)
        # 记录是项目特定审稿经验，不改 CNW 原公开模板、不改确认 Canon。
    return original_response_with_receipt
```

### 7.6 `review_offline` 与真实审稿分离

```python
review_offline(...):
    keep existing W07 MOCK_ONLY evidence and code paths
    never call it in production live runner
    never write provider ID or claim literary semantic output

review_live(...):
    return execute_lint1 -> execute_lint2 -> execute_five_lenses \
           -> execute_three_verifiers -> execute_completeness
```

## 8. `tools/cnw_generate.py` + `tools/cnw_revision.py`：实际完整正文、定向修改与再审

### 8.1 保留已有 W06 容量与分段修复，不再改作者创作理论

```python
def execute_prose(run, inputs):
    contract = read_frozen_work_unit_contract(run)
    brief = read_actual_accepted_writing_brief(run)
    voice_samples = select_only_characters_who_speak(brief)
    prose_request = cnw_generate.build_prose_request(
        contract, brief, voice_samples, verified_p2_capacity_receipt(),
        accepted_context=current_source_and_stage_receipts(),
        provider_output_cap=existing_deepseek_call_limit(),
        budget_output_cap=available_estimated_budget_tokens(),
    )
    previous_parts = []
    for segment in prose_request["segments"]:
        request = cnw_generate.build_segment_request(
            prose_request, segment["segment_id"], previous_parts
        )
        text, receipt = cnw_live_call(
            run, stage="prose", role_id=segment["segment_id"],
            prompt_messages=only_brief_voices_and_previous_text(request),
            output_cap=segment["output_token_cap"],
        )
        previous_parts.append(append_actual_segment_text_and_receipt(text, receipt))
    merged = cnw_generate.assemble_segment_outputs(
        contract, prose_request, previous_parts,
        cost_ledger_path=existing_p2_private_ledger(),
        beat_evidence=trace_actual_visible_action_quotes(),
        dialogue_evidence=trace_actual_dialogue_quotes(),
        action_evidence=trace_actual_action_quotes(),
        start_state_evidence=trace_actual_start_quote(),
        end_state_evidence=trace_actual_end_quote(),
    )
    save_v0_without_overwriting_old_EP001(merged.prose)
    if underproduced_or_missing_required_beats(merged):
        call_existing_persisted_continuation_limited_to_two_attempts()
        if repeated_failure:
            repair_specific_plot_card_brief_or_prose_input_that_caused_it()
            rerun_affected_normal_production_step_without_blank_rewrite()
    return finished_v0_and_actual_character_count
```

`trace_actual_*` 必须引用生成文本中可见原句与位置；不得由 Writer/同一个模型填写虚构“已经做到”的自证。篇幅满足只是必要事实，不等于文学优秀。分段按原顺序合稿，不丢中间段，不因 `max_tokens` 调小而接受短稿。当前 Scene 是一场，不扩成三场；Episode 多场模式保持作者 3–6 典型 Key Scenes 的规划方式，按真正的本项目 Arc 合同决定具体场数。

### 8.2 修改现有 `cnw_revision.py`，直接消费作者审稿结果

```python
def execute_refine(run, inputs):
    # 复用 W08 已提交的 build_revision_plan / build_revision_record / build_rereview_packets。
    v0 = read_original_full_prose(run)
    feedback = read_confirmed_verifier_findings_plus_completeness(run)
    materialized_review = read_true_current_review_artifacts_from_existing_run(run)
    revision_plan_data = cnw_revision.build_revision_plan(
        materialized_review, allow_fixture=False
    )
    revision_plan = render_original_template(
        "templates/09_revision/revision_plan.template.md", revision_plan_data
    )
    save(project/"09_revision/<id>_revision_plan.md", revision_plan)
    if len(feedback) == 0:
        persist_no_change_revision_with_original_v0_untouched()
        return v0
    v1, receipt = cnw_live_call(
        run, stage="refine", role_id="refine",
        prompt_messages=two_messages(
            original_author_refine_task(),
            {"v0": v0, "confirmed_findings": feedback, "brief": brief_only_for_constraints}
        ),
        output_cap=budgeted_output_for_full_existing_scene(),
    )
    cnw_revision.validate_revision(
        contract, v0, v1, finish_reason=receipt.finish_reason,
        evidence=actual_evidence_from_v0_and_v1(),
    )
    save(project/"09_revision/<id>_v1.md", v1)
    append_to_original_revision_log_template()
    return v1
```

```python
def execute_targeted_re_review(run, inputs):
    old_text = read_v0(run)
    new_text = read_v1_or_v0_if_unmodified(run)
    changed_hunks = textual_diff(old_text, new_text)
    affected_lenses = map_actual_changed_hunks_to_the_five_original_lenses(changed_hunks)
    if not changed_hunks:
        return persist_stage_result("NO_CHANGED_TEXT", receipt_count=0)
    for lens in affected_lenses:
        current_result, receipt = cnw_live_call(
            run, stage="re_review", role_id=lens,
            prompt_messages=two_messages(author_lens_prompt(lens), {
                "complete_revised_draft": new_text,
                "changed_hunks": changed_hunks,
                "original_issue_and_fix": relevant_revision_plan_entries(lens),
                "original_lens_sources": load_original_lens_sources(lens),
            }),
            output_cap=existing_safe_cap_for_this_run(),
        )
        save_re_review_result_for_this_lens(current_result, receipt)
    check_full_scene_still_has_all_required_story_beats_and_context()
    # 新发现问题写回既有 Revision Plan 定点修，并只重跑受影响的正常原步骤。
    return revised_scene_and_targeted_review_results
```

原作者 `templates/_workflows/03_revision.md` 的版本分离动作照办：原稿在 `07_draft/`；修订候选在 `09_revision/`；未获作者同意，不自动覆盖公开正本。相邻剧情、角色口吻、对话、感官、动作按已有《苍歧》 Canon 与 Scene Cards 检查；不能以“未在 Canon 明写家具”作为自动删除正常场景描写的创作规则。


### 8.3 复用 W08 已有的审稿绑定代码，但删除“每个写作步骤都等外部审批”的额外创作门

精确修改 `tools/cnw_runner.py:bind_accepted_review_outputs`（W08 当前约第 228–248 行）和 `tools/cnw_revision.py:build_revision_plan`（W08 当前约第 45–99 行）。

```python
# W08 原代码当前强制：
#   accepted_review.status == "EXTERNAL_ACCEPTED"
#   len(verifier_rows) == 3
#   globally verifier_1/2/3 exactly once
#   every issue's three votes must reference same global 3 request IDs
# 这会把“工程 Controller 的阶段签收”混入原作者的创作流程，
# 也不允许按每个 finding 的三路独立反证。

def bind_accepted_review_outputs(review, receipts, run_root):
    match_review_to_same_actual_current_v0_and_source_manifest(review, run_root)
    lens_rows = select_receipts_by_stage(receipts, "multi_lens_review")
    match_exact_lenses_and_independent_raw_responses(lens_rows, count=5)
    all_findings = actual_semantic_findings_plus_L2_candidates(review)
    verifier_rows = select_receipts_by_stage(receipts, "adversarial_verify")
    for finding in all_findings:
        selected = [x for x in verifier_rows if x["finding_id"] == finding["finding_id"]]
        assert {x["verifier_id"] for x in selected} == {
            "correctness", "character_consistency", "continuity_plausibility"
        }
        for row in selected:
            assert original_provider_response_content(row, run_root) == row["response_content"]
            assert receipt_and_ledger_match(row)
    if not all_findings:
        assert not verifier_rows
    record_real_review_stage_as_MATERIALIZED_not_human_creative_approval()

def build_revision_plan(materialized_review, allow_fixture=False):
    verify_current_prose_and_source_hash(materialized_review)
    verify_actual_five_lenses_and_verifier_vote_sources(materialized_review)
    issues = []
    for item in materialized_review.get("findings", []):
        if count_actual_votes(item, "not_refuted") < 2:
            continue
        check_issue_quotes_in_the_original_source()
        priority = original_author_P0_P1_P2_P3_category(item)
        issues.append({
            "issue_id": item["issue_id"],
            "priority": priority,
            "source_ref": item["source"],
            "fix": item["fix"],
            "status": "NEEDS_AUTHOR_DECISION" if item.get("canon_change") else "OPEN",
        })
    return preserve_existing_W08_plan_schema_and_return(issues)

# 不要求 `controller_acceptance_ref` 作为 Refine 的事前文学审查票据。
# 用户/作者批准只作用于 `promote_revision()` 晋升已审定稿，不作用于正常 Draft->Review->Refine。
# 工程 Controller 按原仓库治理在这整个 Atom 代码候选上签一次工程意见。
```

原 W08 `build_revision_record`、`build_rereview_packets`、`promote_revision` 的已有实装保留；只改它们对上述 `materialized_review` 新字段名的直接消费者接线，保留原有修订 diff、证据源定位和晋升前版本归档。

## 9. `tools/cnw_project.py`：严格实现作者公开的五个辅助 Workflows

仅复用现有 `cnw_project.py`、`cnw_revision.py`、`cnw_runner.py`；不建立新的创作理论层。按作者 `templates/_workflows/README.md`，01–05 是**触发式项目维护程序**，不是逐话主流程新增的五个创作阶段。

### 9.1 Workflow 01 — `First Import`（原 `_workflows/01_first_import.md`）

```python
def init_project(...):
    copy_directory_layout_from_pinned("templates/")
    instantiate_blank_project_files_under_workspace_only()
    # 只复制作者模板结构，不复制 example_project 的小说、人物和 Canon。

def import_source(...):
    original_bytes = read_existing_utf8_md_txt_json_source()
    preserve_original_file_bytes_and_original_path()
    save("_INBOX/<original-name>", original_bytes)
    save("00_meta/source_log.md", file_list_with_origin_and_source_refs())
    detect_chapters_and_scenes_with_actual_offsets_or_json_pointers()
    save("_INBOX/source_index.json", ordered_locations_with_hashes())
    extract_directly_attested_canon_and_character_claims_with_quote_refs()
    save("90_canon/canon_candidates.json", confirmed_or_TODO_CONFIRM_candidates())
    update("90_canon/canon.md", only_existing_author_confirmed_facts())
    update("90_canon/character_bible.md", only_existing_author_confirmed_character_facts())
    create("93_exports/handoff_brief.md", pointers_to_current_sources_and_open_questions())
    return imported_project_files_and_real_source_identity
```

### 9.2 Workflow 02 — `Incremental Update`（原 `_workflows/02_incremental_update.md`）

```python
def incremental_update(existing_project, new_source):
    import_new_original_bytes_without_overwriting_previous_original()
    compare_new_claims_with_existing_confirmed_canon()
    for claim in new_claims:
        if direct_source_statement_and_no_conflict(claim):
            append_source_backed_canon_candidate_or_confirmed_user_fact(claim)
        else:
            append("90_canon/unresolved_questions.md", both_source_refs_and_conflict)
    append("00_meta/source_log.md", new_import_metadata)
    append("00_meta/ai_work_log.md", actual_updated_files)
    return source_bound_change_artifacts
```

### 9.3 Workflow 03 — `Revision`（原 `_workflows/03_revision.md`）

```python
def author_revision_workflow(review_material, draft, canon):
    write("09_revision/revision_plan.md", categorize_existing_findings_P0_P1_P2_P3())
    write("09_revision/<id>_candidate.md", apply_only_source_supported_fixes_to_full_draft())
    preserve("07_draft/<id>", original_bytes=True)
    append("00_meta/ai_work_log.md", candidate_revision_fact)
    # 作者真实接受晋升后再替换 07_draft/episodes 正本。
```

### 9.4 Workflow 04 — `Canon Audit`（原 `_workflows/04_canon_audit.md`）

```python
def canon_audit(project):
    read("07_draft/", "03_project_design/", "90_canon/", "06_plot/")
    for actual_contradiction in observed_source_conflicts:
        record = {
          "severity": "HARD CONFLICT|SOFT AMBIGUITY|MISSING INFO",
          "source_a": original_path_and_lines,
          "source_b": original_path_and_lines,
          "description": cited_conflict,
          "suggested_resolution": a_suggestion_not_an_autofix,
        }
        append_to("08_review/continuity_audit.md", record)
        append_deduplicated("90_canon/unresolved_questions.md", record)
    append("00_meta/ai_work_log.md", actual_audit_fact)
    # 禁止自动修改/调和已确认 Canon。
```

### 9.5 Workflow 05 — `AI Handoff`（原 `_workflows/05_handoff.md`）

```python
def handoff(project):
    read_existing("90_canon/", "03_project_design/", "04_chapter_design/",
                  "07_draft/recent", "90_canon/unresolved_questions.md")
    write("93_exports/handoff_brief.md", {
       "project_premise": confirmed_project_summary,
       "current_arc": verified_arc_source_ref,
       "latest_manuscript_position": actual_manuscript_index,
       "confirmed_canon_warnings": short_source_pointers,
       "open_questions": unresolved_questions_source_pointers,
       "next_best_action": next_source_backed_project_action,
       "file_index": references_not_full_canon_duplicate,
    })
    append("00_meta/ai_work_log.md", true_handoff_fact)
```

### 9.6 直接复用五份上游流程提示词（不得由项目代码重写这五套 AI 流程）

```python
SUPPORT_WORKFLOW_SOURCE = {
    "01": "templates/_workflows/01_first_import.md",
    "02": "templates/_workflows/02_incremental_update.md",
    "03": "templates/_workflows/03_revision.md",
    "04": "templates/_workflows/04_canon_audit.md",
    "05": "templates/_workflows/05_handoff.md",
}

def execute_original_support_workflow(workflow_number, actual_project_inputs):
    workflow_text = read_pinned_local_reference(SUPPORT_WORKFLOW_SOURCE[workflow_number])
    author_prompt = extract_original_prompt_block_without_rewriting_task(workflow_text)
    content, receipt = cnw_live_call(
        current_project_run, stage="support_workflow", role_id=workflow_number,
        prompt_messages=two_messages(author_prompt, actual_project_inputs),
        output_cap=available_source_bound_output_tokens(),
    )
    persist_author_named_outputs_from_the_original_workflow(content, actual_project_inputs)
    return receipt

# 项目初始化、输入入库、编码索引和来源 SHA 是工程输入行为，不冒充 Workflow 01 的 AI 资料整理结果。
# CNW 公开 Workflow 01–05 若需要 AI 归纳/审读，真实调用的提示内容直接来自上游五份 Markdown。
# 原作者未公开的 AI 调度私有代码不自行仿造；这里只为公开 prompt 提供薄调用与文件保存。
# `support_workflow` 的 receipt 放到独立的项目维护 run；不要混入 CNW 11 核心阶段的 provider_requests。
```

### 9.7 触发规则仅采用原作者现有文本

```text
project-init + project-import       -> Workflow 01
import into already initialized project -> Workflow 02
actual review findings needing fixes -> Workflow 03
explicit canon-drift / new arc / pre-handoff audit -> Workflow 04
project handoff or end of an arc -> Workflow 05
```

在 `tools/studio.ps1` 上仅增加相应 CLI 到现有 `cnw_project.py`，不另建按钮式工作台；这些辅助工作流运行结果仍位于项目 CNW 原目录结构。现有《苍歧》既有导入不重新覆盖，复用 W00/W01/W03 已确认来源和版本。

## 10. `tools/studio.ps1`：修改现有命令分发，不重建应用

### 10.1 修改当前 `param / switch`（原第 2–18、179–210 行附近）

```powershell
# 保留全部已发布命令。
# 现有 -Command produce -Mode live 传入实际源约束合同后应运行 CNW 全 11 阶段。
# 现有 -Command step -StepName <stage> 调用实际 stage executor，而非仅建立请求包。
# 新增的项目维护命令映射进已有 tools/cnw_project.py；原版仓和模型路由不改。
# 现有 -Command verify-live -RunId 读取现有正常 run 产物并对账；不重跑供应商。
# 现有 -Command export -RunId 直接导出当前 run 的阅读候选，不硬编码旧 EP001。
# 无 -RunId 的旧 export 保留 P2 历史输出，不得作为本 Atom 证据。
```

```powershell
# 真实运行 PowerShell 例子；改造后按以下精确形式执行。
$Studio = 'D:\CangqiStudio\StoryStudio\tools\studio.ps1'
$Project = 'D:\CangqiStudio\StoryStudio\workspace\cangqi'
$Contract = 'contracts\CQ-J19-INSERT-01.work_unit_contract.json'
$WorkId = 'CQ-J19-INSERT-01'
$RunId = 'CNW1TO1-CQ-J19-20261010-01' # 若已存在，脚本按整数尾缀找新且未占用的 ID
& $Studio -Command doctor
& $Studio -Command prepare
& $Studio -Command produce -Mode live -ProjectRoot $Project -Unit scene -Contract $Contract -WorkId $WorkId -RunId $RunId
& $Studio -Command show-run -ProjectRoot $Project -RunId $RunId
& $Studio -Command verify-live -ProjectRoot $Project -RunId $RunId
& $Studio -Command export -ProjectRoot $Project -RunId $RunId
```

在新 `produce` 命令中，`step` 按 `CNW_STAGES` 顺序执行；某一岗位发生正常的代码、格式、供应商或内容长度问题，只修受影响的现有函数并继续该岗位，不因此要求用户另立设计审核、添加套娃验收 Agent 或倒退已通过的步骤。模型调用重复只在实际响应不存在或输入已变时发生；已计费但服务端状态不明确时保持既有 ledger 预留，先对账再采取下一次正常请求。

### 10.2 设置现有 DeepSeek Key 的进程范围（原位置已由用户提供）

```powershell
$KeyPath = 'C:\Users\Administrator\Desktop\skill资产\deepseek kye.txt'
$Secret = (Get-Content -LiteralPath $KeyPath -Raw -Encoding UTF8).Trim()
$env:DEEPSEEK_API_KEY = $Secret
Remove-Variable Secret
try {
    # 执行上面的 `produce` / `show-run` / `verify-live` / `export` 命令。
} finally {
    Remove-Item Env:\DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
}
```

不要把 Key、`$Secret`、完整 prompt/raw response 或原始《苍歧》剧本文本写入 stdout、公开 Markdown、提交文件。正常产物留在现有 Git-ignored `workspace/`, `runtime/`, `runs/`, `deliverables/`。

## 11. 本 Atom 只做一次真实端到端产品运行

### 11.1 使用已冻结的唯一真实工作单

```text
source_version: JUN-SINGLE-02.3
source_zip_sha256: 300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2
scene_contract: workspace/cangqi/contracts/CQ-J19-INSERT-01.work_unit_contract.json
contract_sha256: e5ef4ce8d4468756021b8b7a8e10dd3cff0b9445e25a6a399f3cc683bb0978d0
pov: 君天离
scene_position: J19 已确认对白后 / 原玩法交互入口前
reader_scope: J19 当前可见事实；不得穿越 J20 任一分支
scene_visible_chars: target=1500, min=1200, max=1800
scene_beats: 读取原合同四节拍，不自行换题/改变节拍数量和原目标
scene_count: 1
```

### 11.2 严格按原作者步骤逐项保存真实产物

```python
contract = load_existing_frozen_Cangqi_J19_contract()
run = produce_one_new_live_run(contract)

# 先运行四岗位链（NK/CritiCS 仅在所属岗位内作为附加服务）。
plot       = execute("plot", source=actual_arc_canon_character_bible)
cards      = execute("scene_cards", plot=plot, character_bible=actual_character_bible)
nk_support = call_existing_NK_on_accepted_cards(cards)        # 非作者核心 stage
brief      = execute("writing_brief", plot=plot, cards=cards,
                     character_bible=actual_character_bible,
                     style_guide=actual_style_guide, nk_support=nk_support)
prose_v0   = execute("prose", brief=brief, voice_samples=relevant_actual_samples)

# 再运行作者完整审稿环节。
lint1       = local_lint_layer1(prose_v0)
lint2       = local_lint_layer2(prose_v0)
lenses      = five_independent_provider_lenses(prose_v0, author_sources)
verifications = three_counterargument_votes_per_actual_finding(lenses, lint2)
complete    = independent_completeness_critic(prose_v0, verifications)
critics_addendum = supplemental_critics_text(run, prose_v0, verified_findings)
prose_v1    = revise_full_prose_using_surviving_findings(prose_v0, complete, critics_addendum)
re_review   = rerun_lenses_for_actual_changed_hunks(prose_v1)

candidate = export_reading_preview(prose_v0, prose_v1, source_adjacent_context)
write_existing_run_receipts_and_ledger_no_duplicate_charge()
submit_candidate_for_engineering_and_effect_review()
```

### 11.3 检视正常作品产物，不新增专门的验收脚本

```text
实际打开 `runs/<id>/artifacts/plot.md`；核对 Arc、Hook、Required/Forbidden、Target length 来自冻结源。
实际打开 `runs/<id>/artifacts/scene_cards.md`；核对四节拍、人物欲求、起止、动作与回应、感官锚/节奏。
实际打开 `runs/<id>/artifacts/writing_brief.md`；核对每项必要事件进入对应场景，存在 NK 正确支持段，且来源不越界。
实际完整阅读 `runs/<id>/artifacts/prose.v0.md`；核对确有事件、台词、动作、回应与结尾，不是概述。
实际打开两个本地 lint 报告；核对其只给行号/候选，没有擅自删除正文。
实际打开五份独立 Lens 原始意见；核对五份真实身份、职责、不同来源和具体文本位置。
实际打开各 finding 的三份反证、投票处置；核对存在原始批评和被驳回意见，不是一份泛泛评价。
实际打开 Completeness 原始结果、Revision Plan、v1 和 Re-review；核对采纳项实际改变了文字且没有删除必须动作。
实际打开 v0/v1/连读 HTML；检查新场与 J19 原入口自然接回、不改后续分支。
实际核对 v1 可见字符属于 1200–1800（目标1500），但不以数字代替“有趣、完整、有节奏”。
实际核对本轮新 supplier request/usage/估算费与 P2 旧账本一致，绝无重放旧 EP001 冒充新作。
```

**实际作品审读关注的自然阅读结果**：开场能知道人物处境；至少有一项清楚的具体行动目标；存在阻力或分歧与回应；角色说话能区分；细节对行动有贡献；单场事件有落点；衔接原文无卡顿；正常读者读完能感知本场的人物差别及其情绪结果。没有这些效果时继续修改受影响的 CNW Plot/Card/Brief/Prose 或作者审稿/修订环节，**不能另造作品评价流程，也不能仅凭调用次数宣布文学效果成功**。

### 11.4 标记未覆盖的运行范围；不得冒称全覆盖

```text
CNW_PUBLIC_WORKFLOW_STAGE_STRUCTURE = implemented_to_11_public_stages
CNW_FIRST_J19_SCENE_LIVE_E2E = actual result after running
CNW_EPISODE_MULTI_SCENE_LIVE = NOT_RUN
CNW_FIVE_EPISODE_SPRINT_LIVE = NOT_RUN
CNW_PRIVATE_AUTHOR_AUTOMATION_CODE = NOT_PUBLICLY_AVAILABLE
USER_CREATIVE_ACCEPTED = PENDING_USER_READING
```

## 12. 两种原有验收治理：工程对照 + 真实效果；不编写新的验收程序

### 12.1 工程治理 — 复用原 Controller

```text
1. Writer 展示当前 main HEAD、TREE、当前 W10／其他未提交文件及本 Atom 实际 diff。
2. 同一既有只读 Controller 对照 W00 固定原文：11 阶段及其职责、四岗位的实际源文件、Lens 来源、三反证/遗漏/复审、五个辅助 Workflows。
3. Controller 只审实际代码与真实运行产物；不要新建测试系统，不要求额外形式表格和重复 C/T 签名。
4. Controller 对真实越出黑名单的修改明确指出动作；对黑名单外编译/参数/依赖/JSON/顺序/输出错误交 Writer 直接修改，再看受影响最终行为。
5. Controller 给出当前 Atom 工程复核记录；Writer 保留当前未提交 W10／其他成果，按现有 main 单分支治理正常提交。
6. Writer 普通 `git push origin main`，回读远端真实 SHA/tree；不改历史，不强推。
7. Writer 在 `reviews/P2_ACCEPTANCE_LOG.md` 末尾追加本 Atom 的真实工程结论；历史记录一字不删。
```

```powershell
Set-Location 'D:\CangqiStudio\StoryStudio'
git diff --check
git status --short --untracked-files=all
git diff --stat
git diff --name-status
# 在当前既有 Controller 完成工程差异复核后，只显式暂存以下已施工的源码/文档；
# 未施工、未修改的路径会被跳过，不等于“代码修改权限白名单”。
$AtomFiles = @(
 'AGENTS.md', 'config/cnw_production_policy.json',
 'prompts/cnw/plot.md','prompts/cnw/scene_cards.md','prompts/cnw/brief.md','prompts/cnw/prose.md',
 'tools/cnw_runner.py','tools/cnw_roles.py','tools/cnw_nk_adapter.py','tools/cnw_critics_adapter.py',
 'tools/cnw_generate.py','tools/cnw_review.py','tools/cnw_lint.py','tools/cnw_revision.py',
 'tools/cnw_project.py','tools/studio.ps1','tools/p2_cost_guard.py',
 'reviews/P3_METHOD_COVERAGE.md','reviews/P3_1_DIFF_AUDIT.md',
 'reviews/P2_ACCEPTANCE_LOG.md','evidence/P3_CURRENT_STATE.md',
 'plans/ATOM_CNW_PUBLIC_1TO1_RESTORE.md'
)
foreach ($File in $AtomFiles) {
  if (Test-Path -LiteralPath $File -PathType Leaf) { git add -- $File }
}
# 任何额外机械修复文件须依据本轮实际改动、显式路径 git add；不使用 git add -A。
git diff --cached --name-status
git diff --cached --check
git commit -m "fix: restore published CNW workflow semantics"
git push origin main
git ls-remote origin refs/heads/main
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git status --short --untracked-files=all
```

### 12.2 实际端到端结果验收 — 回当前 ChatGPT 审查

```text
提交后给出：
  1) GitHub 仓库、main 提交完整 C 和 T；
  2) 被改的实际文件名/函数名与原作者对应源路径；
  3) 本轮一场真实 E2E 的 Run ID、真实 API request 数、usage 与增量预估费用；
  4) 本轮 v0、v1、J19 前后文连读 HTML/MD 的本机路径及实际长度；
     因 `workspace/runs/deliverables` 属于 Git 忽略目录，需将阅读版作为当前对话的附件/直接内容提供；
     仅报告 D:\ 路径不足以让 ChatGPT 远程读取，严禁为方便审查而把私有剧本推至公开 Git。
  5) 五 Lens、实际 findings×3 反证、Completeness、Refine、Re-review 的私有产物路径；
  6) 原作者 11 阶段所用的实际数据来源路径；
  7) 新增历史之外确实未实跑的作者方法分支，不冒充已运行；
  8) Git staged 文件中无密钥与私有稿件，且现有唯一 main 无破坏历史。
```

```text
对外声明顺序：
  ENGINEERING_CONTROLLER_REVIEWED -> GIT_PUSHED_AND_REMOTE_READBACK -> CHATGPT_SOURCE_AND_RESULT_REVIEW
  -> READY_FOR_USER_CREATIVE_READING

绝不由 Writer/Controller 自行填 USER_CREATIVE_ACCEPTED。
没有当前 ChatGPT 对已推送真实源码和结果的审查结论，不把本 Atom 写成最终文学完成。
```

## 13. 施工收尾操作

```text
[ ] 现有未提交 W10 等 WIP 保留；旧 P2/P3/P3.1 已签收对象保留。
[ ] 原作者本地文件和 blob 身份使用 W00 已捕获 98 项；上游 pin 未动。
[ ] CNW 11 主阶段顺序与角色依赖一一对应；NK/CritiCS 未替换原方法。
[ ] 实际四岗位输出都具有原模板 Markdown 内容，不是请求包/机器日志冒充。
[ ] 两层 lint 保持本地脚本身份；Live receipt 门只核对有供应商调用的阶段。
[ ] 五 Lens 来源覆盖作者原四类基础材料 + 项目特定源，均真实独立调用。
[ ] 有真实发现的问题均有三种独立反证及相应表决；没有问题不造回执。
[ ] Completeness 读全文和问题处置；Refine 后只有受影响范围复审。
[ ] Workflow 01–05 的辅助维护职责与核心 11 阶段分离。
[ ] 本轮同一《苍歧》 J19 单场满足前后事实、动作/对白/起止及合同字符量。
[ ] 新单场原始调用/账本/项目私有文件未混入公开 git；没有二场 Live。
[ ] 现有工程 Controller 已看真实代码/差异与功能；main 正常推送回读。
[ ] 提交完整 C/T、Run ID、修订全文及前后文读本路径，供当前 ChatGPT 审实际结果。
```

**全文其他字段校验均用于修复既有实现并继续执行，不能被增列为黑名单外的人工审批或硬停条件。**

**执行结束语固定为**：`ATOM_CNW_PUBLIC_1TO1_RESTORE: SUBMITTED_FOR_CHATGPT_REVIEW`。只有收到外部源码和实际作品审查结论后，才能把该 Atom 记录为真正关闭；未公开的原作者私有实现与未实跑的完整 Episode/Sprint 另行如实标记，不得替换为“全部一模一样”之类无证据表述。
