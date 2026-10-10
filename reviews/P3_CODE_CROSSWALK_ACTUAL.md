# P3 源码对照实况（W01 基线）

W01 实地基线：StoryStudio 本地/远端 `main` C=`d0c723831d6086533ce4a4f61e817f43e2f589fa`，T=`aef07c313384076a00132906c2b9f44d1a8e23a0`；该 C 包含 W00 的捕获工具、安全检查和 P3 工单。WIP 包含本 crosswalk 与 `P3_METHOD_COVERAGE.md` 的来源差异补充。CNW 固定源 `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`；P3 本机原文 manifest SHA256=`E9B989C52C66AB9BE8C73F09E84BC5BD7D2ECC92F9F1CBFC61BA300DC6CD3983`。除 W00 工具外，下述 P2 源码 blob 与 939eca 基线相同。候选目标尚未存在时明确标缺，不伪造新实现。文件 blob 身份见文末。

`PRESENT` 仅表示当前可复用能力；不表示相关 P3 全链已完成。`PARTIAL` 表示固定 EP001/单功能有既有实现，尚无新 ID 泛化；`MISSING` 表示无满足本方法的实现。

| ID | CNW 固定来源（path@blob） | 当前 StoryStudio 定位（基线） | 实情 / 差异 | 目标实现 / 验证 |
|---|---|---|---|---|
| M01 | `docs/`,`templates/`,生产手册 | `tools/capture_cnw_reference.py:21-227`；`tests/test_source_snapshot.py:1-93` | `PRESENT_AND_TESTED`：W00 独立 ACCEPT；固定 98 项捕获成功；隔离首捕获/污染快照/嵌套链接负例均成功 | A01/A02；已由 W00 覆盖 |
| M02 | `templates/config/workflow.template.yml@146ea01a484cc0578cf290478b3941599ad7fb15` | `tools/studio.ps1:4-9` 命令 dispatch | `MISSING`：无作者阶段状态机 | `tools/cnw_runner.py`；B07 |
| M03 | `templates/config/ai_roles.template.yml@8ec31cb93cb0be1913579cc5cb05de45460988f8` | `tools/p2_06_draft_run.py:6-30` | `MISSING`：单次固定 prose，无 Plot/Card/Brief 四岗位 I/O | `tools/cnw_roles.py`；B01 |
| M04 | `docs/EXISTING_PROJECT_IMPORT.md@25a28031c203f716fcb9c9e7b174acb445e66c94`; `_workflows/01_first_import.md` | `tools/studio.ps1:115-119`；`tools/critics_bridge.py:17-35` | `PARTIAL`：校验固定《苍歧》ZIP/安全路径，非任意 project root | `tools/cnw_project.py`；A04/B01 |
| M05 | Plot 模板 `@8eb22fa6221351c2b614a3ae7d5dc4a53d3e8688` | `config/production.example.json:35-44` | `MISSING`：只有样本 ID/POV，无 Project/Arc/Episode/Scene 合同 | `tools/cnw_contract.py`；B01/B04 |
| M06 | `episode_production_manual.md@fbc51bd35b347ee864d0ac938353e2ff524d0e55`；Card 模板 `@b003a987ac1bd5eb1ae6f8dcf7dceffdfdfeaf5d` | `config/production.example.json:16-17` | `MISSING`：`literary_word_count_target=null`，无冻结单位预算 | `config/cnw_production_policy.json` + 合同；B03/B04 |
| M07 | `plot.template.md@8eb22fa6221351c2b614a3ae7d5dc4a53d3e8688` | `tools/studio.ps1:134-138` 固定读 `ep001_plot.v1.md` | `MISSING`：不生成新 Plot | `cnw_runner step plot`；B01 |
| M08 | `scene_cards.template.md@b003a987ac1bd5eb1ae6f8dcf7dceffdfdfeaf5d` | 私有 `workspace/cangqi/05_scene_cards/ep001_scene_cards.md`；无新生产命令 | `PARTIAL`：有一次性卡，无卡岗位/预算验证 | `scene_card_agent`；B01/B04/B05 |
| M09 | `writing_brief.template.md@d67e3c4539eaea5bbcce904f3eb3ee42ff1e2fc5` | `tools/p2_06_draft_run.py:10-11` 固定读 EP001 Brief | `PARTIAL`：已有固定 Brief，无冻结预算和新 ID 输送 | `brief_agent`；B01/B06 |
| M10 | `ai_roles.template.yml@8ec31cb93cb0be1913579cc5cb05de45460988f8` | `tools/p2_06_draft_run.py:6-11,24` | `MISSING`：固定 EP001，并硬编码“500–700中文字符” | `tools/cnw_generate.py`；C01/B06 |
| M11 | `episode_production_manual.md@fbc51bd35b347ee864d0ac938353e2ff524d0e55` | `tools/p2_06_draft_run.py:27-40` | `MISSING`：单笔 `max_tokens=2048`，无分场/节拍续写或目标检查 | `cnw_generate.py`；C01/C06 |
| M12 | `writing_brief.template.md@d67e3c4539eaea5bbcce904f3eb3ee42ff1e2fc5` | 同上，尤其 `p2_06_draft_run.py:29-40` | `MISSING`：stop/non-empty 仅为接口成功检查 | `cnw_contract.validate_draft`；C01/C02 |
| M13 | NK 路由和 `ai_roles.template.yml` | `tools/p2_06_nk_live_probe.ps1:55-69` | `PARTIAL`：固定样本真实请求；无通用 Card adapter | `tools/cnw_nk_adapter.py`；B06/E09 |
| M14 | `THREE_LAYER_REVIEW.md@d03488d15f1a7841f442119237aff6d6148020df`；CritiCS bridge | `tools/critics_bridge.py:80-168`; `tools/p2_06_critics_run.py:34-179` | `PARTIAL`：真实三 critic/refine 桥与 ledger 已有；无 P3 薄适配；不能替五 Lens | `tools/cnw_critics_adapter.py`；D04 |
| M15 | `THREE_LAYER_REVIEW.md@d03488d15f1a7841f442119237aff6d6148020df` | `implementation/PRODUCTION_SPEC.md:162` 仅规范；无独立 stage runner | `MISSING`：没有真实 5+3+completeness/re-review 执行链 | `tools/cnw_review.py`；D01-D10 |
| M16 | `THREE_LAYER_REVIEW.md` L1 | `tools/critics_offline_check.py` 是协议接线检查 | `MISSING`：无中文正文 surface lint | `tools/cnw_lint.py surface`；C09 |
| M17 | `THREE_LAYER_REVIEW.md` L2 | 无结构上下文 lint | `MISSING` | `tools/cnw_lint.py structural`；C03/C09 |
| M18 | `THREE_LAYER_REVIEW.md` Style Lens | 无独立 Style API job | `MISSING`：Controller 混合阅读不等价 | `cnw_review lens style`；D01/D02 |
| M19 | 同上 Character Lens | 人物资料在 `workspace/cangqi/90_canon/character_bible.md`；没有 Lens job | `MISSING` | `cnw_review lens character`；C07/D02 |
| M20 | 同上 Plot Lens | `tools/critics_bridge.py` Plot CritiCS 不等同 CNW Plot Lens | `MISSING` | `cnw_review lens plot`；C02/D02 |
| M21 | 同上 Canon Lens | `implementation/PRODUCTION_SPEC.md` 有知识边界要求；无标准化 claim 输出 | `PARTIAL`：人工有查边界，未独立调用/引用 | `cnw_review lens canon`；C08/D02 |
| M22 | 同上 Story-specific Lens | 无体验/趣味/冲突独立审查 | `MISSING`：此次短稿已证实风险 | `cnw_review lens story_specific`；C03/D02/D09 |
| M23 | `workflow.template.yml@146ea01a484cc0578cf290478b3941599ad7fb15` | 单 Controller / CritiCS 批次 | `MISSING`：无五请求隔离身份与输入关系 | `lens_id/request_id/input_sha`；D01/D10 |
| M24 | `THREE_LAYER_REVIEW.md` verifier 部分 | 无三路 verifier；CritiCS Inspector 在不同方法链 | `MISSING` | 3 独立 verifier/2-of-3 规则；D03/D10 |
| M25 | `THREE_LAYER_REVIEW.md` completeness | 无独立遗漏检查 | `MISSING` | `completeness_critic`；D05/D09 |
| M26 | `_workflows/03_revision.md@cae774e2582b09bdeaa7e80e6a7831ab4053dce5` | `tools/p2_06_revision_run.py:5-30` | `MISSING`：固定 v0→v1 全文重写，不校验完整度；469 B 结果回归 | `tools/cnw_revision.py`；C04/C05/D06/D07 |
| M27 | 同上 | `studio.ps1:46-106,134-138` | `MISSING`：固定 EP001 导出/读 checkpoint，无审核后 promote | `cnw_revision promote`；D08 |
| M28 | `revision_plan.template.md@759f418a3b89e2040e4228931ee81aa8baf365b8` | `workspace/cangqi/09_revision/revision_plan.md` 仅一次样本（若路径存在） | `PARTIAL`：没有通用 issue 状态机/按等级依赖 | `cnw_revision plan`；D06 |
| M29 | `manuscript_review_rubric.md@c4dfc2c2e43e869d2be3da90661054efcd6bc2f0` | `implementation/ACCEPTANCE_SPEC.md:29` V13 工程/连续性条件 | `MISSING`：没有正式读者体验质量否决层 | `tools/cnw_quality.py`；C03/D09 |
| M30 | `docs/ARCHITECTURE.md@89bdf2d8e4dabc223fcf91969ebaa5596ad51864` | `tools/studio.ps1:43-106` | `MISSING`：固定 `deliverables/EP001`、J19 anchors | `tools/cnw_export.py`；E07/E08 |
| M31 | `batch_review.template.md@24ba804c4807e0e535eee07a00c46d58ff10fd5a` | 没有 sprint 入口 | `MISSING` | 离线 5 话 sprint fixture；E02 |
| M32 | `_workflows/05_handoff.md` | `evidence/P2_CURRENT_STATE.md` 固定 P2 状态记录 | `PARTIAL`：有历史交接，无可恢复新 run state | `cnw_runner resume/handoff`；B02/E04/E05 |
| M33 | `templates/07_draft/episodes/README.md`；`_workflows/03_revision.md` | v1 存 `workspace/cangqi/09_revision/ep001_v1.md`，无泛化 promote | `MISSING` | 单一正本/manuscript index 更新；D08 |
| M34 | P2 studio runtime history | `tools/studio.ps1:120-148` | `MISSING`：verify 搜旧验收文案/只读旧 checkpoint | 分开 `verify-history/live`；B08 |
| M35 | `workflow.template.yml` 11 stage | P2 evidence 记外部结果，但缺通用 artifact/input SHA 依赖状态 | `PARTIAL`：固定 P2 阶段证据存在；无新 run 可观察链 | `cnw_runner` stage manifest；E04/E05 |
| M36 | 成本守卫是 P2 工程能力 | `tools/p2_cost_guard.py:34-202`; `tools/p2_06_critics_run.py:75-139` | `PRESENT`：持久 ledger、reserve/settle；新 CNW 岗位尚未接入 | 复用现账本；E03/E04 |
| M37 | NK `/api/generate-perspective` | `tools/p2_06_nk_live_probe.ps1:55-69`; `patches/nk/PATCH_INDEX.json` | `PARTIAL`：P2 实时路由适配已签收，非通用 scene adapter | `tools/cnw_nk_adapter.py`；B06/E09 |
| M38 | `workflow.template.yml` + rubric | `evidence/p2-07-delivery.json` / `evidence/P2_CURRENT_STATE.md` | `PARTIAL`：P2 工程 ACCEPT 是历史事实；原短稿不能证明产品准备 | 明确 reopen，W10/W11 新生产 gate；E09/E10 |

## 当前差异与限制

- 本轮 W00 新捕获工具在工作树新增但未提交；本 crosswalk 是 P3 基线判断，不把它等同于已有 main 实现。
- 离线 P3 验收测试尚未实现/运行；除 A01 的实际捕获结果外，表中测试 ID 是待实现的验收目标，不是 PASS。
- `tools/p2_06_draft_run.py` 的 500–700 字 hard-code 和 2048 token 上限是明确根因；P2 历史文件保留，正式入口必须避开它。
- 文件 SHA256 与 Git blob 区分：以下为当前基线的 Git blob ID；后续一旦修改该文件，应更新本 crosswalk 的候选 C/T 与新文件 hash。

## 当前基线相关代码 Git blob

| 文件 | 行数 | Git blob |
|---|---:|---|
| `tools/studio.ps1` | 202 | `6511e1594f6b1bc939fd24d6cf6e8a259d114e70` |
| `tools/p2_06_draft_run.py` | 45 | `1cd510f02346d0a473b8ebd6cbbc30d32ceff86a` |
| `tools/p2_06_revision_run.py` | 33 | `c38ad4a62b53b243ecec10f234dd36643ae80922` |
| `tools/p2_06_critics_run.py` | 179 | `c1ae981d25e172cf9ac51b35d08c42e77d8b3633` |
| `tools/critics_bridge.py` | 168 | `ef02815ce93c046c610d8c04e6f1982a46574543` |
| `tools/p2_cost_guard.py` | 215 | `bd6a72cb3f85b0e5c9324b655af1eb259ca21ec6` |
| `config/production.example.json` | 62 | `1bb58a75ae1540b7dab4159e4be6d83087613236` |
| `implementation/PRODUCTION_SPEC.md` | 214 | `95e39d95113fdb094e6bbe9a84d42fc654e008fb` |
| `implementation/ACCEPTANCE_SPEC.md` | 94 | `81dadc5cb18d6890c1365b116c33986ef0f0ed73` |
| `implementation/TECHNICAL_SPEC.md` | 260 | `4a1fa6d0f477f36901285f2dcb58f5febb56eca3` |
| `patches/nk/PATCH_INDEX.json` | 36 | `a0b672e2d88b81e03da342fbe6db40fb22e2b342` |
| `patches/critics/PATCH_INDEX.json` | 71 | `016530e6d2a27aebe578b8d90e40d0f428dd2682` |
| `tools/capture_cnw_reference.py` | 227 | `73ab9fe09d9dd8c01670f5b0f255ce53814d2fb3` |
| `tests/test_source_snapshot.py` | 93 | `fc91f0583b6235d6810aab444a526af741948037` |

上述文件的当前工作树原始字节 SHA256（便于复核；Git blob 另列，以保留 Git 换行清理前后的身份区别）：

| 文件 | 工作树 SHA256 |
|---|---|
| `tools/studio.ps1` | `832016ADB49B9281989EA8CAFAAE385CB7BA800B90B2ABFEFDDB46EBB5B0538F` |
| `tools/p2_06_draft_run.py` | `BD16B2D763CB3A6A599DA29F49AE89B3956BB337073D0729958673DAD66C04C0` |
| `tools/p2_06_revision_run.py` | `0BAC00D04902B926262423CE1BF2DECD3EF98FF16AE3B5F9F28AF726050CB4A7` |
| `tools/p2_06_critics_run.py` | `975D8B987598C07066D74F7545437728E463275AF9F6C6A74D16162E760774C3` |
| `tools/critics_bridge.py` | `7A4EDB2A3A05BA8E1FC0A16256EF63C90B535B38806B8E9D120CD35B1320D1A3` |
| `tools/p2_cost_guard.py` | `AB8A40B15687B8FC35FAFFBEF5C34553649F818F188C7E4CDFA57BA9342C21E3` |
| `config/production.example.json` | `B5DC2BEBB54F9EE4BECA56AD3BF2D9B88F9AB6831D7BD9211BEDCD57A3A9E959` |
| `implementation/PRODUCTION_SPEC.md` | `4CBDABB51C44F6912EC77C582A7B7965023D8236B6C511A7F3881CC26DDCC51C` |
| `implementation/ACCEPTANCE_SPEC.md` | `075D475DA3B203D088D0BDD306C8DD1AB4CB3E37C878B81996EBACAB2DEA48F1` |
| `implementation/TECHNICAL_SPEC.md` | `B3679CA39B18860B0E9B25135AB3A28C523DBC30EEDCEA10F89E151EE521918A` |
| `patches/nk/PATCH_INDEX.json` | `2BA6CF61A6405352BDDAB1F228304986EB60093BE25B160D81F3FB44D596CACB` |
| `patches/critics/PATCH_INDEX.json` | `3032B3662304C51033353F2B087577A98B3C8CE0CE44C83705588A2554708457` |
| `tools/capture_cnw_reference.py` | `F7EFE75E9671D9DF62FD876876F828B40AEC90C1BAAF653B23CD93590E30A6E5` |
| `tests/test_source_snapshot.py` | `F329A8581B1C48AC380A7891FA0C3A5A9284617FA670EC3434EC001282B6E4D7` |

Vendor identities and status: `third_party/claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`, `third_party/narrative-keyframing@b857f34b7d371ae82c30e00eb021884c14d08ae9`, `third_party/CritiCS@fbf66cbc913012c6f80af1687e27f0ce350475e3`; all three submodule worktrees report no tracked modifications.
