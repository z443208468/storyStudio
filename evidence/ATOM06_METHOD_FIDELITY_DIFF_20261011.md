# ATOM-06 METHOD_FIDELITY_DIFF — 2026-10-11

**Status:** Repair evidence for a new local candidate after the first Atom-06
candidate received an independent Controller `RETURN`; the repaired candidate
C/T is pending review. This document is not an acceptance. The only plan is
`plans/MASTER_PLAN_GENERIC_APP_R5.md`, SHA-256
`5CC22861CE3C0603D6EF89619594CD7CD68642241A20036032B031CB3A8C8ECF`.
The fixed method remains `claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`;
the workflow blob is `146ea01a484cc0578cf290478b3941599ad7fb15` and the author-role
configuration blob is `8ec31cb93cb0be1913579cc5cb05de45460988f8`.

## Atom-06 delta

The eleven CNW stages, their order, role allowlists, and pinned author prompts
remain in place. This Atom adds a bounded `zh-CN`/`en-US` offline locale matrix,
visible Unicode code-point length semantics, a 4,000-character contract ceiling,
and explicit optional `nk`/`critics` integration states. New v2 contracts default
both supplements to `DISABLED`. `ENABLED` components are checked before a live
run is created; unavailable components fail closed. In the Brief stage, disabled
NK contributes no message material and makes no NK call. CritiCS disabled records
`DISABLED` without starting its adapter. The old project-name `FICT_` switch is
removed; an injected test-only context cannot enter live mode.

Plot/Cards/Brief/Prose read boundaries are still defined by the pinned role
contract. Prose still receives only the same-run Brief and selected voice
samples. Its base request, English/Chinese continuation, and over/under-length
recovery now state the project locale. Refine recovery follows the same locale.
HTML export takes `lang` from the frozen contract. `cnw_runner` now rejects a
verifier response unless it contains exactly one vote for the requested finding;
an extra or cross-finding vote cannot be silently ignored.

**Capacity boundary:** 4,000 is a contract/output-validation ceiling for this
offline implementation. Provider maximum output, chars-to-token behavior,
`finish_reason` handling under real provider responses, and writing quality were
not validated here. `GENERIC_LIVE_PRODUCTION=NOT_RUN`; Atom-09 retains provider
adapter and full-chain simulation gates.

## M01–M16 method map

| Method | Current code path and Atom-06 change | Executed evidence and scope |
|---|---|---|
| M01 | `tools/cnw_runner.py:CNW_STAGES`, predecessor validation, and dispatch preserve the pinned 11-stage order. No stage or predecessor changed. | Runner stage-order/alias and request invalidation tests passed. Full eleven-stage input-to-output simulation is `DEFERRED_TO_ATOM_09`. |
| M02 | `tools/cnw_roles.py:AUTHOR_ROLE_READS/resolve_author_reads/build_author_role_messages` and `cnw_runner._role_sources` remain the Plot route. | Two temporary synthetic projects build actual Plot messages from their own Arc, Canon, and character files. Their separate messages and SHA identities are in the request trace. No provider response or production Plot is claimed; full consumer chain is `DEFERRED_TO_ATOM_09`. |
| M03 | `cnw_runner._role_sources("cards", ...)` still replaces the published Plot path only with the hash-checked Plot from that run. | Both synthetic projects' actual Cards messages consume their matching same-run Plot and character file; cross-project canaries are absent. Runner's independent two-run test also passed. |
| M04 | Brief retains same-run Plot/Cards, project Character/Style, and the pinned supplementary Canon/Timeline/World/Glossary reads. NK remains a supplement. | Both project Brief messages and their input keys are recorded. Disabled NK test constructs the Brief request with no NK material and observes no `_nk_pov` call. Full pipeline is `DEFERRED_TO_ATOM_09`. |
| M05 | Prose's actual role message still contains only Writing Brief and selected voice-sample payload fields. | Two-project request trace contains `GUARD_SECRET_CANARY` in upstream Canon and `GUARD_LINT_ONLY_CANARY` in project forbidden patterns, while the Prose messages contain neither. Voice selection tests passed. Full production transport capture is not claimed. |
| M06 | `tools/cnw_lint.py` rules remain project-supplied; Prose role reads do not include `forbidden_patterns.md`; lint remains report-only. | Project-specific format/context regex fixtures, evidence lines, and no-text-mutation checks passed. A zero-regex project is not represented as globally clean. |
| M07 | `cnw_review.build_lens_input/lens_messages` and `cnw_runner.execute_five_lenses` continue to create five isolated calls. | Runner consumer test builds five distinct messages with only each Lens's allowlisted sources, injects five offline responses, and consumes their outputs. Trace includes each exact message, message SHA, response, and response identity. No provider call occurred. |
| M08 | `cnw_review.tally_verifiers` retains the three verifier identities and two-vote threshold. `cnw_runner._single_verifier_vote` now rejects missing, extra, and cross-finding votes at the consumer. | Actual Runner consumer test issues three independent requests for each of two findings; the offline return contains exactly one matching vote. Matrix tests cover 0/1/2/3 `not_refuted`, `uncertain` as refutation, duplicate votes, and cross-finding output rejection. |
| M09 | `execute_completeness` consumes complete draft/prior dispositions and publishes only candidate Lens feedback. | A synthetic omission response is written to the temporary project feedback file and then read by the actual review source resolver. The candidate is also consumed by Refine in the next request. No-finding/capacity tests passed. Full subsequent review loop is `DEFERRED_TO_ATOM_09`. |
| M10 | `execute_refine` still writes a distinct revision candidate and lists affected Lenses; re-review is a later stage. | Synthetic Refine request consumes the new Completeness candidate and saves `affected_lenses=["story_specific"]`; prior prose remains a separate artifact. Same-stage fresh Re-review against changed draft and injected-new-defect gate are `DEFERRED_TO_ATOM_09`. |
| M11 | Import/Incremental workflow code is unchanged by locale/support changes. | Temporary source import/update and conflict-preservation suites passed; no external project source was opened. |
| M12 | Canon Audit, Workflow 03 revision, and Handoff ownership remain existing maintenance/approval boundaries; this Atom does not change publication or Canon rules. | Synthetic maintenance and canon-protection tests passed. Workflow-03 no-author-approval end-to-end publication refusal and next-operation Handoff use remain `DEFERRED_TO_ATOM_09`. |
| M13 | `cnw_sprint_live._criteria()` remains the active threshold consumer of the pinned author workflow. | Consumer test read `{size: 5, min_score: 75, max_p0_findings: 0, max_p1_findings: 2}` from the pinned source. Five-episode batch, pause, and Handoff outcomes are `DEFERRED_TO_ATOM_09`. |
| M14 | NK/CritiCS stay outside the eleven official stages. New contract integrations distinguish `DISABLED` and `ENABLED`; unavailable enabled services fail before dispatch. | Actual Brief/critics hook test records both disabled paths with zero supplement calls. A synthetic enabled-but-missing NK runtime raises `ENABLED_BUT_UNAVAILABLE` before dispatch. Enabled full-chain comparison is `DEFERRED_TO_ATOM_09`. |
| M15 | Atom-06 does not change INSERT/ADAPT/ORIGINAL source identity or source selection contracts. No new work intent was added. | Prior Atom-03 source/intent code remains the source of those guarantees; only current role boundaries and locale consumers were exercised here. Full A→B plus each-intent CNW chain remains `DEFERRED_TO_ATOM_09`; Atom-06 does not assert source-intent completion. |
| M16 | Pinned method identity, project material, local Controller verdict, Canon approval, user acceptance, and Live evidence remain separate. | All captured request/response identities are explicitly synthetic offline identities. No Provider/NK/CritiCS API, story generation, migration, project-data change, or user-creative acceptance occurred. Controller verdict remains pending. |

## Reproducible evidence

The final command and exact stdout/stderr bytes, SHA-256 values, exit code, base
commit, and tested source-file SHA values are archived in
`evidence/ATOM06_RETURN_RAW_20261011.json`. It records exit `0`, stdout SHA-256
`997ed26c6ced510151f3ff68d6cbf2d17221857332bac9e2d296752995e790f6`, empty
stderr SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`,
and `102 passed, 13 subtests passed`. The raw stdout is retained as Base64, not
paraphrased.

Exact synthetic requests, input field lists, source/message hashes, offline
responses, and downstream outcomes are archived in
`evidence/ATOM06_SYNTHETIC_REQUEST_TRACE_20261011.json`, SHA-256
`0b83dc40618ee95403781f678b88e4e31271dad61b0ef04352b9dedf94a803b1`. The trace
includes two projects × four author roles, English and Chinese continuation
messages, five isolated Lens messages, six verifier messages for two findings,
the Completeness→Refine→Lens-feedback chain, disabled/unavailable supplement
cases, the `FICT_BAD` pre-Provider rejection, and legacy v1 Chinese continuation
and Refine compatibility requests. Its schema marks the complete
trace `SYNTHETIC_OFFLINE_ONLY`.

The test set also covers policy snapshots, source import, maintenance, contract
validation, two-layer Lint, verifier vote constraints, locale-aware export, and
legacy runner behavior with self-contained temporary fixtures. Six protected
untracked W10 files were neither read nor staged. `CUTOVER_BLOCKED` remains in
force: no DataHome or project root was selected, and no project migration or
activity-pointer change occurred.

## Controller RETURN and minimum repair

The first local Atom-06 candidate `53ad1043604ce194b1bb7d3c6b206b172b0e01c8`
(`78b99aface15a59cde75625dd60457710d7ce3e2`) received an independent `RETURN`
for M14 / §06.1 compatibility: the locale update treated legacy v1 contracts
without an explicit locale as English. This could change existing CNW Chinese
continuation and Refine requests. That rejected candidate was not pushed.

The minimum repair makes `cnw_runner.execute_prose` and `execute_refine` preserve
their historical Chinese instructions for every non-v2 contract; v2 continues
to follow its explicitly validated `zh-CN`/`en-US` locale. A temporary synthetic
v1 contract with no locale and legacy `language="en-US"` now exercises the actual
under-length continuation and Refine request builders. Both captured requests
contain the historical Chinese instructions and no English switch. This repair
does not alter CNW stages, roles, data, or project state.

**Controller:** pending review of the exact local candidate C/T. This document
does not claim Atom-06 acceptance or authorize push; normal push and remote
read-back follow only a Controller `ACCEPT` for the reviewed C/T.
