# Early CNW gate and blocking repairs — 2026-10-12

## Scope and safety

- R5 plan: `plans/MASTER_PLAN_GENERIC_APP_R5.md`, SHA-256 `5CC22861CE3C0603D6EF89619594CD7CD68642241A20036032B031CB3A8C8ECF`.
- Fixed CNW source: `MintoTsukino/claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`.
- E2E used a self-contained synthetic `TIDELINE` project, an explicit temporary test DataHome, two fictional imports A/B, and selected B. Contract intent was `ADAPT_SOURCE`, scene without before/after anchors, language `en-US`, explicit project-specific fifth Lens duty, and NK/CritiCS `DISABLED`.
- The only test injection was at `runner.cnw_live_call`, the transport edge. Stage execution used actual `runner.produce`, `cnw_recovery.execute_checked`, role read resolution, lint, Lens/verifier/completeness/refine/re-review code, artifact persistence, and `cnw_export.export_reading_package`.
- No production API, user DataHome, private J19 file, actual TS run, W10 source, provider bill, or migration was read or changed. All E2E receipts are `MOCK_ONLY` / `SIMULATED`; the live-verification negative rejects them.

## Repair roots and regression evidence

| Repair | Root cause | Fix and negative/positive evidence |
|---|---|---|
| Anchor-free ADAPT Plot identity | `stage_identity(plot)` treated every V2 scene as an insert scene and dereferenced `before_anchor`. | V1 retains historical scene anchors; V2 inserts use real anchors; ADAPT uses frozen selection identity and ORIGINAL uses its controlled project context. The focused test runs actual Plot identity/execution/reuse without anchors. E2E also runs anchor-free ADAPT through all stages and asserts neither anchor was invented. |
| NK disabled Brief identity | Brief identity unconditionally built and hashed an NK payload even when the actual V2 execution had NK disabled. | V2 `DISABLED` omits NK payload/builders and remains stable when `build_nk_payload` is patched to fail if called. E2E asserts no NK request/hook and successfully runs Brief; a separate `ENABLED_BUT_UNAVAILABLE` negative fails closed. V1 keeps the historical identity path. |
| V1 export locale regression | V2 began requiring an explicit locale, while historical V1 contracts may have `language` without the later `language_locale` field. | V2 requires matching explicit `language_locale` and `language`, and the locale must be in `SUPPORTED_LOCALE_MATRIX`. V1 uses its historical `language_locale` then `language` fallback and does not gain a fabricated default. The V1 export fixture has `language=zh-CN` and no `language_locale`; V2 missing-locale and well-formed-but-unsupported `eo` negatives reject. |
| Private J19 test fixture | `tests/test_cnw_pipeline.py` loaded a private J19 contract from `workspace/cangqi`. | Replaced it with a self-contained fictional V1 fixture and local mock transport receipt while preserving five-episode Sprint, Arc, failure pause, and Handoff assertions. The complete pipeline test runs without that private tree. |

## Necessary test runs

Each command exited `0`. Raw console outputs are kept beside this report.

| Command | Result | Raw output |
|---|---|---|
| `python -m pytest tests/test_cnw_export.py -q` | `7 passed` | [`EARLY_CNW_EXPORT_REPAIR_20261012.raw.txt`](EARLY_CNW_EXPORT_REPAIR_20261012.raw.txt) |
| `python -m pytest tests/test_cnw_pipeline.py -q` | `16 passed` | [`EARLY_CNW_PIPELINE_REPAIR_20261012.raw.txt`](EARLY_CNW_PIPELINE_REPAIR_20261012.raw.txt) |
| `python -m pytest tests/test_cnw_work_intent_v2.py tests/test_cnw_project_import.py -q` | `21 passed, 7 subtests passed` | [`EARLY_CNW_INTENT_NK_REPAIR_20261012.raw.txt`](EARLY_CNW_INTENT_NK_REPAIR_20261012.raw.txt) |
| `python -m pytest tests/test_cnw_early_e2e.py -q` | `2 passed` | [`EARLY_CNW_E2E_GATE_20261012.raw.txt`](EARLY_CNW_E2E_GATE_20261012.raw.txt) |
| `python -m py_compile tools/cnw_recovery.py tools/cnw_export.py tests/test_cnw_pipeline.py tests/test_cnw_work_intent_v2.py tests/test_cnw_early_e2e.py` | `0` | No diagnostic output. |
| `git diff --check` | `0` | Only Git line-ending notices; no whitespace errors. |

Source SHA-256 at the recorded passing runs:

| File | SHA-256 |
|---|---|
| `tools/cnw_recovery.py` | `E634BDBD1D73A430F56895537F3EB2E560C1FB56946B470413CBF0EB0E348E43` |
| `tools/cnw_export.py` | `6B1115A0B22D30EFAC9EE6E139F74CD8146567205B872396BED66DBAC0D8A396` |
| `tests/test_cnw_work_intent_v2.py` | `C5F8E65E7B28F34119494EABC44DD5A28D8E3C493C42A4DF294DE0B7A9C22244` |
| `tests/test_cnw_export.py` | `8616EDCD5F683DF8D205AC06FF7D91205D56305D0C1FC63C3598F9242CF75482` |
| `tests/test_cnw_pipeline.py` | `01464C65846AFC0BDACEE255ED1C0EE7ABA57A2B058596A1E4ADE1762A685195` |
| `tests/test_cnw_early_e2e.py` | `6D10FEC0BB5F9FB11BC292426AA15ABBEC1DD48AF8A44ACACD7AB5472CB31B7B` |

## `EARLY_CNW_E2E_GATE` evidence

The machine-readable evidence at [`EARLY_CNW_E2E_GATE_20261012.json`](EARLY_CNW_E2E_GATE_20261012.json) includes each actual mocked provider request message, every persisted stage artifact body and SHA, request/raw-response/output hashes, export deliverables and hashes, and test-only negative results. Its SHA-256 after the locale-gate repair rerun is `A421D50839E072CC887D51F83D49FD867306F58D13A17C31C794C5FDBDA70B87`.

Observed execution order:

`plot → scene_cards → writing_brief → prose → lint_layer1 → lint_layer2 → multi_lens_review → adversarial_verify → completeness_critic → refine → re_review → export`

All 11 CNW stages materialized nonempty outputs through the production executor. The source selection was B: the Plot message contains B's selected excerpt/revision hash and excludes A's unique canary. Role request summaries record the expected material keys, including Prose restricted to Brief and relevant voice samples. Brief's V2 identity excludes NK and remains stable without calling the NK payload builder.

The chain produced five independent Lens requests and an actual Canon Finding; three distinct verifier requests were consumed with two `not_refuted` votes and one `refuted`, yielding `CONFIRMED` at 2/3. Completeness returned `OMITTED-READER-PAYOFF`; Refine checked that it consumed both that issue and the confirmed finding. Re-review issued fresh Canon and story-specific requests against the revised artifact SHA and returned `CLEAN`. Export read the run artifacts and left the project Canon hash unchanged.

The transport interruption occurred at Scene Cards. The execution failure record was retained; recovery planning stayed read-only and reported `RECOVERY_BLOCKED_EXECUTION_HISTORY`; Plot remained byte-identical and was reused rather than rerun. The interrupted stage was then completed by retrying the actual checked executor. Invalid-input negatives cover cross-project Prose data exclusion, forbidden-word detection, unsupported invented relationship removed without Canon mutation, duplicate Finding IDs, mismatched verifier ticket, unavailable enabled NK, and rejection of simulated receipts as Live.

This is a synthetic offline result only. It cannot establish Live model quality or make a prior private TS/J19 run executable. For the unavailable private legacy baseline, status is `BASELINE_EXECUTION_UNAVAILABLE`; the fixed public source and M01–M16 method contract remain available for the Controller's limited source/code comparison.

## Governance state

The prior ATOM-06 and ATOM-07 RETURN records remain unchanged. See [`GIT_GOVERNANCE_ANOMALY_20261012.md`](GIT_GOVERNANCE_ANOMALY_20261012.md) and [`ATOM07_EXTERNAL_INPUT_NEEDED_20261012.md`](ATOM07_EXTERNAL_INPUT_NEEDED_20261012.md). ATOM-07 is still `RETURN`; `CUTOVER_BLOCKED=true`; `PRIVATE_MIGRATION=NOT_RUN`. ATOM-09 remains `NOT_RUN`; generic Live production remains `NOT_RUN`.

The independent Controller accepted the synthetic early E2E and limited method-fidelity scope, but returned the first repair candidate because V2 export did not reject locales outside `SUPPORTED_LOCALE_MATRIX`; see [`EARLY_CNW_CONTROLLER_RETURN_20261012.md`](EARLY_CNW_CONTROLLER_RETURN_20261012.md). The exact unsupported-locale fix and rejection test are now present and the affected export and E2E tests were rerun. The new candidate still requires fresh independent review; no push is authorized by the prior verdict.
