# P3 W04 方法到代码增量记录

## 固定来源与实现

| CNW 方法来源（W00 捕获 manifest） | 上游 blob | 项目实现 | 当前可证明状态 |
|---|---|---|---|
| `templates/06_plot/plot.template.md` | `8eb22fa6221351c2b614a3ae7d5dc4a53d3e8688` | `prompts/cnw/plot.md`; `tools/cnw_roles.py:build_role_packet/validate_role_output` | Prompt、contract/source/policy hash、依赖和 beat/长度 gate 已离线验证；尚未执行新的模型岗位 |
| `templates/05_scene_cards/scene_cards.template.md` | `b003a987ac1bd5eb1ae6f8dcf7dceffdfdfeaf5d` | `prompts/cnw/scene_cards.md`; `tools/cnw_roles.py` | 只接受 Plot 产物依赖；beat ID 与 beat 分量不能丢失；尚无新 run 的 Card 产物 |
| `templates/07_draft/writing_brief.template.md` | `d67e3c4539eaea5bbcce904f3eb3ee42ff1e2fc5` | `prompts/cnw/brief.md`; `tools/cnw_roles.py`; `tools/cnw_nk_adapter.py` | Brief 保留全节拍/范围；NK reflection 仅作为带 receipt/hash 的支持段；本轮合同未调用 NK |
| `templates/config/ai_roles.template.yml` | `8ec31cb93cb0be1913579cc5cb05de45460988f8` | `prompts/cnw/prose.md`; `tools/cnw_roles.py:build_prose_input_view` | Prose 输入视图只有 Brief 与声线样本，加最小 POV/长度/beat 执行值；需前三岗位有真实 Provider request 与 Controller ACCEPT 后才可构造 Prose packet |
| NK `/api/generate-perspective` + 本机 P2 live runner | StoryStudio 当前锁定 NK pin；P2 真实调用可复用作端点事实 | `tools/cnw_nk_adapter.py` | ordered `eventSequence` 来自 Beats；POV 是合同 narrator；reflection 到 Brief 的映射要求 `LIVE_ACCEPTED` receipt 或明确 `FIXTURE_ONLY`，无 receipt 不通过 |
| CritiCS `three_critic` → `modifiedStoryline` | P2 固定 patched runtime 与 `tools/p2_06_critics_run.py` | `tools/cnw_critics_adapter.py` | 构造器仅调用现有有成本守卫的 runner；`plan-critique` 使用原生 CritiCS 方法，修订动作保留给下一阶段显式审查；本轮未发 API |

## 限制与验收证据

- 该代码提供角色边界、输入/输出哈希与结构 gate；它不把离线 fixture 冒充为实际 Plot/Card/Brief/Prose 或模型质量证据。
- Prompt frontmatter 中四个 CNW blob 已与本机 `CNW_LOCAL_REFERENCE_MANIFEST.json` 逐项比较；差异为 0。
- `tests.test_cnw_contract` 与 `tests.test_cnw_adapters`：13 项通过。覆盖 B03/B04/C01 合同 gate、Prose 输入隔离与未验收阶段阻断、Plot/Card/Brief beat ID 与逐 beat 预算 marker、NK 事件序列/response receipt 映射、CritiCS 成本守卫 runner/版本回执、Prompt 原 blob 对齐。
- `py_compile` 通过。当前没有真实 provider request、没有新作品岗位输出、没有新增费用。真实 Plot/Card/Brief/Prose 参与证据必须在后续 run 中产生。
