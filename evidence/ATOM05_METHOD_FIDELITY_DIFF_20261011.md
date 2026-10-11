# Atom-05 method fidelity diff — 2026-10-11

**Candidate scope:** current local Atom-05 engine changes; `C/T` pending. This
is a Writer mapping, not Controller acceptance. Fixed normative method source
is the R5-pinned upstream `claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`.

| Method | Normative responsibility | Atom-05 code/consumer change | Evidence and current limit |
|---|---|---|---|
| M01 | Preserve the 11 author stages and their order; support services never replace a stage. | `CNW_STAGES` and stage dispatch are unchanged. `_persist_stage` changes only the run-scoped artifact identity and atomic state pointer. | `test_cnw_runner` plus `test_cnw_recovery` pass. Full actual 11-stage trace remains Atom-09 work. |
| M02 | Plot reads current Arc, Canon and character material plus only legal intent-specific context. | Plot's allowed reads and message builder are unchanged. Its output is kept in its run; no project Plot alias is written during generation. | Atom-05 does not rerun Plot or alter the Atom-03 intent contract. Full request evidence remains bounded to prior accepted Atom-03 evidence and Atom-09 integration. |
| M03 | Cards consumes its same-run Plot and character material. | `_role_sources` maps the author template's Plot path to `_read_stage_text(run, state, "plot")`, which verifies the registered SHA before use. | Synthetic two-run test captures the actual Cards builder materials: each request receives its own run's Plot, while a frozen project Plot remains unchanged. |
| M04 | Brief consumes same-run Plot/Cards plus character, style and required Canon context; NK remains supplementary. | `_role_sources` maps Plot and Cards to their verified same-run candidates; project-frozen character/style/Canon reads retain the published author allowlist. | Code path implemented; complete Brief/NK route and real message-chain evidence remains assigned to Atoms 06/09. No NK/API call here. |
| M05 | Prose directly receives only the accepted Brief and relevant voice samples. | `_role_sources` maps the Brief template path to this run's hash-verified Brief; other declared voice inputs remain project-frozen. | No Prose allowlist expansion. Full sensitive-canary boundary proof remains an Atom-06/09 gate. |
| M10 / M12 | Refine is a separate candidate; author/Controller approval gates public promotion and Canon remains human-owned. | Plot/Cards/Brief/Refine stage outputs are content-addressed run candidates. `promote_revision` takes the common project lock and rejects a changed manuscript target unless the review evidence's `expected_current_sha` matches the candidate-registration snapshot. | Synthetic interruption and conflict tests pass. No candidate was promoted; no Canon or manuscript project bytes were read or changed. |
| M13 | Sprint remains a five-episode review/gate/handoff workflow with fixed thresholds. | The existing live and fixture Sprint methods are wrapped by the shared project-write lock; their stage, rubric, threshold, and publication content are unchanged. | No Sprint was run. Full five-episode behavior is reserved for Atom-09. |
| M15 | INSERT / ADAPT / ORIGINAL preserve real source identity and do not fabricate provenance. | Atom-05 does not alter work-intent validation or source selection; generic semantic import now accepts only a registered DataHome root outside legacy workspace. | Registered-root routing has a synthetic identity test. Three-intent/source-consumption evidence remains at accepted Atom-03 and the later Atom-09 chain gate. |
| M16 | Keep offline evidence, independent engineering review, canon approval, user acceptance and Live evidence distinct. | New evidence labels tests as local Writer evidence and explicitly leaves private cutover, Controller verdict, and Live production separate. | No production API, story generation, migration, Canon approval, or user creative acceptance occurred. |

**Explicitly not established here:** complete role-chain semantics, NK/CritiCS enabled/disabled end-to-end behavior, five-Lens/three-Verifier/Completeness/Refine/Re-review real-consumer chain, Sprint live output, private V5/J19 migration, cost-ledger relocation, or Live writing quality. These remain later Atom gates or are blocked pending an explicitly selected DataHome and read-only cutover review.

## Atom-05 RETURN repair scope — 2026-10-11

The independent Controller returned two §05.1b write paths. The minimal repair
keeps their existing authority semantics and serializes them with the established
project lock:

| Returned path | Repair | Focused evidence |
|---|---|---|
| `execute_completeness()` Lens feedback | Read/de-duplicate/update now runs under `project_write_lock`; it re-reads the locked preimage and atomically replaces the feedback file. | Two concurrent synthetic updates to one Lens preserve both instructions while revision publication uses the same critical section (`test_lens_feedback_publication_serializes_concurrent_feedback_and_publish`). |
| `incremental_update()` source staging + semantic import | The public Workflow 02 operation acquires the project lock before state recovery/checks and raw `_INBOX/originals` staging, and runs both supported source/semantic import bodies without nested acquisition. | Fixture races the actual incremental staging entrypoint and revision publication, checking the staged source exists before semantic import, one active writer, and no lost authority updates (`test_incremental_staging_and_publish_share_one_project_lock`). |

Focused retest results are recorded in `ATOM05_ENGINE_RETEST_20261011.txt`.
These new results are Writer evidence only. Exact repaired C/T remains subject
to independent Controller review; nothing here authorizes private-data cutover.
