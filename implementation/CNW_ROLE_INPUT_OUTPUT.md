# P3 生产角色、合同、状态及输出规范（开发用）

本规范根据固定 `CNW templates/config/{workflow,ai_roles}.template.yml`、三份原始 Plot/Card/Brief 模板、`docs/THREE_LAYER_REVIEW.md` 实例化到 StoryStudio。**数据 schema 是本项目适配方案，不声称上游文件本身含有这些 JSON 字段。**

## 1. 三层生产身份：Project → Episode → Scene

- `Project`：输入剧本、Canon、世界与人物、风格、版权/私有保管、源身份、用户批准的目标文体。
- `Episode`：按 CNW `templates/06_plot/plot.template.md` 规划的一个完整章节。它可包含 3–6 个典型 Scene 或符合实际设计所需的其他场数；为它建立 Hook、读者回报、篇幅分配、单话 review 与索引。
- `Scene`：章节中的具体一场，或经过明确独立 Scene 合同批准的一场插戏。它有 start/end state、行动/应对、必需情节点、禁写和规模目标。**即便一场通过，也不等于完成一整话的完整公开生产链测试。**

## 2. 必须保存的 `work_unit_contract.json`

下面是 **schema 示例**，方括号中的值是施工时需从真实《苍歧》原稿取回的占位，不能将其直接发给模型。当 `anchor_sha256`、`beat`、`required_voices` 等必要项缺失，进入 Draft 应当阻断。

```json
{
  "schema_version": "cnw_work_unit_v1",
  "project_id": "cangqi",
  "source": {
    "version": "JUN-SINGLE-02.3",
    "zip_sha256": "300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2",
    "local_private_source_manifest_sha256": "<READ_ACTUAL_SHA256>"
  },
  "unit": {
    "id": "CQ-J19-INSERT-01",
    "kind": "scene",
    "language": "zh-CN",
    "pov": "君天离",
    "target_visible_chars": 1000,
    "min_visible_chars": 700,
    "max_visible_chars": 1400,
    "policy_sha256": "<READ_ACTUAL_SHA256>"
  },
  "story": {
    "chapter_context": "<AS_READ_FROM_CANON_AND_ADJACENT_SCRIPT>",
    "role_in_story": "<SPECIFIC_FUNCTION_NOT_GENERIC_DAILY_FATIGUE>",
    "reader_reward": "<WHAT_READER_GETS_FROM_THIS_SCENE>",
    "entry_state": "<VISIBLE_J19_STATE>",
    "exit_state": "<STATE_THAT_PRESERVES_THE_ORIGINAL_J19_OPTIONS>",
    "before_anchor": {"script": "J19", "source_line": 555, "anchor_sha256": "<READ_ACTUAL_SHA256>"},
    "after_anchor": {"script": "J19", "source_line": 557, "anchor_sha256": "<READ_ACTUAL_SHA256>"},
    "required_beats": [
      {"beat_id": "B01", "goal": "<SCENE_CARD_ACTION>", "min_coverage": "observed_action_and_response", "budget_visible_chars": 350},
      {"beat_id": "B02", "goal": "<SECOND_ACTION_OR_CHANGE>", "min_coverage": "observed_action_and_response", "budget_visible_chars": 350},
      {"beat_id": "B03", "goal": "<EXIT_OR_PAYOFF>", "min_coverage": "confirmed_exit_state", "budget_visible_chars": 300}
    ],
    "characters_in_scene": ["<FROM_CANGQI_ORIGINAL>"],
    "character_knowledge_boundary_ref": "<PRIVATE_CANON_FILE_AND_SHA>",
    "forbidden_future_revelations": ["<SOURCE_REFERENCED_FORBIDDEN_ITEM>"],
    "voice_sample_refs": ["<PRIVATE_VOICE_SAMPLE_WITH_SOURCE_LINE>"],
    "approved_local_detail_scope": "observable_reversible_details_only"
  },
  "review": {
    "workflow_template_git_blob": "146ea01a484cc0578cf290478b3941599ad7fb15",
    "require_cnw_11_stages": true,
    "story_specific_lens_policy_ref": "<FROZEN_CANGQI_POLICY_PATH>",
    "require_3_verifiers": true,
    "require_completeness_critic": true,
    "require_re_review": true
  }
}
```

**长度值的身份**：以上 1,000/700–1,400 是 P3 为《苍歧》本场提出的**生产初始建议**，不是 CNW 作者的中文规则。Controller 在真正生成前必须结合相邻源稿、戏剧任务和对白/动作比例审这三个数字并冻结。建议 target 只代表本场平均完整度，不能掩盖动作/节拍缺失。超过上限且内容必要时，先回 Story/Card 更新合同，不允许自动截断作品。

**Episode 合同**另加 `episode_id`, `arc`, `ordered_scenes[]`, `hook_type`, `promises`, `pov_policy`, `chapter_target_visible_chars`。必须满足 `chapter_target = sum(scene_target)`（或解释有专门留白/章节过渡预算），每个 Scene 持独立 `scene_id/start_state/end_state/target/required_beats`。不能把 Episode 与 Scene 统一编号成固定 EP001。

## 3. 角色 I/O 合同（按作者模板，不额外引入创作理论）

| Role/stage | 最小读取材料 | 严格产物 | 结构性判退 |
|---|---|---|---|
| `plot_agent` | 现存 Arc/Chapter design、活动 Canon、source contract、上一话状态 | `06_plot/<unit>.md`（Role/Key Scenes/required beats/forbidden/Hook/target length/connections） | 无章作用、无明确事件、无长度、违反原稿首尾 |
| `scene_card_agent` | 通过的 Plot + 有关 Canon | `05_scene_cards/<unit>.md`（每场 identity/长度/起止状态/行动/受阻/禁写/感官/节奏） | 只写概念、无行动/回应、无起止状态、分量加总不合法 |
| `brief_agent` | Plot、所有 Cards、当前可见 Canon、style guide、声音样本 | `07_draft/<unit>_writing_brief.md`（精简执行包，所有 scenes 所需信息） | 目标规模丢失、缺 beat、把秘密原文交给主视角、混用另一个作品 |
| `nk_pov_adapter`（项目新增） | 当场 Card + 人物当期表现/可知边界 | NK 原路由 response `{perspectives:[{reflection:"..."}]}` + Brief 映射清单 | NK 输出未被 Brief 消费、把短 reflection 当完整正文、故事秘密泄漏 |
| `prose_agent` | 通过的 Brief + 当前参与角色的声音样本（**不读**全文隐秘 Canon） | `07_draft/episodes/<unit>.v0.md` 或每场分段汇总稿 | 文本欠产量、场景 beat 缺失、总结代对白动作、未写完、只有标题 |
| `lint_layer1` | 完整正文 + 当前语言表层约束 | `08_review/<unit>/lint_l1.json`（规则 ID/行号/触发） | 把英日标点禁则直接搬到中文、偷偷自动删句 |
| `lint_layer2` | 完整正文 + 中文结构模式 | `08_review/<unit>/lint_l2.json`（原句及周边上下文） | 没上下文、只靠词表判恶意情绪词 |
| `lens_style` | Draft + 本项目 style guide | `08_review/<unit>/lens_style.json` | 没独立模型返回、没指出具体文本问题 |
| `lens_character` | Draft + character bible + voice samples/calling table | `lens_character.json` | 仅给泛化情绪标签，未评声音/目的/关系 |
| `lens_plot` | Draft + Plot/Cards/Brief | `lens_plot.json`（逐 beat 落地证据） | 必须 beat 漏掉却判 PASS |
| `lens_canon` | Draft + allowed Canon + before/after source | `lens_canon.json`（断言及原稿出处） | 角色提前知晓未披露秘密、引用缺失 |
| `lens_story_specific` | Draft + 用户已批准的本场体感目标 | `lens_story_specific.json` | 无具体小事件/人物互动/阅读回报仍过关 |
| `verifier_correctness` | 审稿 findings + 对应 source/draft | `verify_correctness.json` | 把假设当事实，默认同意 reviewer |
| `verifier_character` | 同一 findings + 人物声音与边界 | `verify_character.json` | 没独立证据或与其他 verifier 共享上下文 |
| `verifier_continuity` | 同一 findings + 前后锚/因果 | `verify_continuity.json` | 为纠偏引入新重大设定 |
| `completeness_critic` | 全部 Draft + surviving findings | `review_completeness.json` | 忽略“场景基本没写”的大缺口 |
| `refine_agent` | 原稿、经过验证的 issue 队列、冻结 Brief | `09_revision/<unit>.v1.md` + revision log | 原 v0 被覆盖，剧本行动被削减造成欠产量 |
| `re_review` | 修订后的完整稿 + 前次 findings/affected lenses | `<unit>_rereview.json` | 只看 patch 忽略受影响上下文，复评缺失 |
| `episode_index` | 全部通过的阶段记录/最终候选 | `07_draft/manuscript_index.md` + `94_runtime` 状态 | 未被接受就写 final/published 或自动扩下一话 |

**预审 gate**：一个正式 `scene` 的 Plot/Card/Brief 仍按 CNW 身份和场景职责执行，但只为该 scene 建一个卡，不冒充完成整话 3–6 场。`episode` 的 Plot/Brief 实际描述所有分场，并由逐 Scene 出稿组成完整正文。

## 4. 最小一份 Lens JSON（项目实现 schema）

```json
{
  "lens": "plot",
  "stage": "multi_lens_review",
  "work_id": "CQ-J19-INSERT-01",
  "draft_sha256": "<REAL_SHA>",
  "input_source_hashes": ["<REAL_SHA>"],
  "provider_request_id": "<REAL_ID>",
  "model": "deepseek-flash",
  "findings": [
    {
      "finding_id": "PLOT-001",
      "severity": "high",
      "line_start": 6,
      "line_end": 8,
      "claim": "<MISSING_OR_DISTORTED_REQUIRED_BEAT>",
      "required_beat_id": "B02",
      "evidence": "<DRAFT_LOCATION_OR_PRECISE_ABSENCE_CHECK>",
      "source_ref": "05_scene_cards/<unit>.md#B02",
      "suggested_fix": "<ADD_MISSING_ACTION_RESPONSE_IN_SCENE_SCOPE>"
    }
  ]
}
```

- **各 Lens 使用不同、隔离的请求**；同一原稿可共享只读文件 ID，但不得在审稿输入中包含其他 lens 输出。
- **Verifier 投票**：每条 issue 三份独立决定。`refuted=true` 代表已反驳；`refuted=false` 代表经核对尚未反驳。至少 2 份 `refuted=false` 才保留进入 Revision；不确定时按上游默认优先证伪、交 Controller 看 raw。
- **Completeness** 原方法是在汇总后独立检查有没有完全漏掉的审稿类别，新增 issue 要保留自身来源和 Controller 复核状态。
- **Re-review** 必须针对修改触及的 Lens 重新计算，不允许拿修改前 lens PASS 给新稿沿用。

## 5. `run_state.json` 与缓存身份

```json
{
  "project_id": "cangqi",
  "work_id": "CQ-J19-INSERT-01",
  "run_id": "CQ-J19-REBUILD-P3-01",
  "work_unit_contract_sha256": "<REAL_SHA>",
  "cnw_reference_commit": "97ad71fe5e5e76a82275c6c63d4add06fb60ab6e",
  "source_manifest_sha256": "<REAL_SHA>",
  "steps": [
    {
      "name": "plot",
      "status": "ACCEPTED",
      "input_hashes": ["<REAL_SHA>"],
      "config_sha256": "<REAL_SHA>",
      "output_path": "runs/<run-id>/06_plot/<work-id>.md",
      "output_sha256": "<REAL_SHA>",
      "real_request_ids": ["<REAL_ID>"],
      "actual_used_cny": "<COST_ESTIMATE_AS_STRING>",
      "controller_accept_ref": "<REAL_ACCEPT_MESSAGE_OR_LOG_ENTRY>"
    }
  ]
}
```

真实实现不得预先将任何示例 `ACCEPTED`、`REAL_ID` 或稿件 SHA 当事实。状态写在 Git 忽略的 `runs/<run-id>/`；公开仓只收脱敏摘要和签收索引。缓存复用必须同时核对 **输入哈希、模型配置、prompt 模板、review policy、项目 contract、上游来源**，否则重新计算真正受影响下游。缓存失效不等于自动可以付费，要先走费用预留与权限。

## 6. 质量 / 长度 / 演出 三重检查

- `visible_chars`: 对正文进行 Unicode NFC 归一化，排除 Markdown 控制符与空白，报告普通汉字数/标点数/对白段落数/动作段落数。**必须报告具体算法与局限**，文件字节数不能直接称汉字数。
- `target_length_gate`: 正文要落在写作前冻结的 `min..max` 内；超/欠标返回 `RETURN_LENGTH`，不靠删除读者有益内容或加废话强凑。特殊短场例外必须写在 **生成前** 的合同并附理由。
- `required_beats_gate`: Plot/Card 中每个必需节拍均有可定位文本证据，不让模型单凭“我已经写到”标签自签。至少出现有目标→行动→他人/环境回应→变化或落点。
- `reader_experience_gate`: 有明确人物差异、动机、现场细节、对话/反应、场景作用，且与上下文自然连接；单纯“他们心情更好”不是行为戏。
- `canon_pov_gate`: 原稿知识分界不能错，但**不会因为无脑删掉所有动作就被算作通过**。
- `revision_regression_gate`: 修订稿比前稿明显缩短（建议超过 25%）必须列出每个被删节拍与保留证据；若跌出长度合同或丢失节拍直接 RETURN。修订中真实冗余被压缩且仍在合同内可通过。
- `quality_rubric`: 原作者示例以致命问题先行，其作品 80/65 分界并不自动是《苍歧》的文学品质“科学标准”。StoryStudio 采用**可解释的项目量表**作为支持证据，不能自动代签最终文学满意度。

## 7. 费用和模型范围

- 保留 DeepSeek `deepseek-flash` 和现有只读上游/补丁结果；阶段 11 条不等于必须每步使用模型：L1/L2 是纯本地校验，其他文学岗位使用真实隔离模型调用。NK 和 CritiCS 已修复并可真实调用，作为 CNW 补充节点。
- 复用现有 `tools/p2_cost_guard.py` 中的 reserve/settle；**不新建第二套计费系统**。之前 17 次请求/约 ¥0.123297 是历史估计，与新 run 分开记录，总预算上限由**现有账本与当前批准政策**决定，不能在计划里自动充值或重新归零。
- 首次 Live 只重做同一个获准的《苍歧》插场。用户亲读验收前，不得真实生成第二场/下一话/5 话批量。
