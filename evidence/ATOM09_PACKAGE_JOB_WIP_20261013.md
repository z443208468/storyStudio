# ATOM09 package job — bounded Writer evidence, not acceptance

Base commit: `728cf4da449a8f9afde6fbf141c2da2cc9e0b1ee`.
Base tree: `69389c0f7b51dc524f7c1e83814b74c05602f0ab`.
This is WIP in ATOM09. No candidate ACCEPT, push authorization, Live or complete ATOM09 acceptance is claimed.

## Actual application path

`studio.ps1 project-pack -ExecuteJob` forwards to the existing package application.
The app imports declared materials, prepares actual normally validated V2 Runs,
then calls `cnw_recovery.execute_checked` for the fixed eleven stages and the real
`cnw_runner.export_run`. The user supplies the package/DataHome or the returned
job path, without hand-entering contracts, Run IDs, SHA or per-stage commands.

Tests call the actual Python application entry; the test does not dispatch the
eleven stages itself. Only the final model function is replaced with deterministic
fixture responses. Every worker checks its live temporary fixture/DataHome
ownership. Direct socket/HTTP, process networking and fee/request boundaries are
blocked. An unmodified real model/authorization path refuses with
`OFFLINE_PROVIDER_FORBIDDEN` before a slot, fee reservation or HTTP request.

The three fictional legacy-format tasks preserve min/target/max `2200/3100/4700`.
Their actual initial and revised mock prose is 3100 visible characters. Project
rules cause distinct actual Layer 1/2 Lint results without modifying prose.
Layer 2 findings also receive three independent counterchecks, alongside Lens
findings; each confirmed item has two `not_refuted` votes out of three.
Completeness omissions enter Refine, and affected Re-review consumes revised text.
All candidates and exports are explicit `MOCK_ONLY / SIMULATED`, never Live.

## Real recovery fixes and negative oracles

- Scene Cards interruption after the mock receipt: same job reuses that receipt,
  preserves Plot, and automatically completes the remaining real stages.
- Export file interruption: complete files and failed write attempts are retained
  in a job-bound staging transaction; same job completes publication without new
  model requests or overwriting old bytes.
- Export completed before job CAS power loss: the real exporter verifies its
  instance/Run/contract/final-stage binding and complete file set, then reuses it.
  Unknown output directories and altered files cannot be adopted or overwritten.
- Bounded Re-review adds a second actual Refine: final job stage records, Run,
  review candidate SHA and exported prose agree; the first content-addressed
  candidate and revision base remain readable.
- Exhaustion: actual Run `REVISION_REQUIRED` plus retained
  `REREVIEW_REQUIRES_REVISION` history keeps the same job awaiting the author.
  Repeated startup does not reset the revision budget or add model requests,
  versions or an export. The CNW revision loop itself is unchanged.
- Changed contract bytes and published export bytes are rejected and retained.

## Original verification evidence

Repository-external directory:
`D:\CangqiStudio\StoryStudio_R5_Atom09_Package_20261013_728cf4d`.
Each `.check.json` stores its exact command, exit code, source SHA map and
unchanged-source check; original `.raw.txt` files are retained separately.

| Label | Actual result | Raw SHA256 |
|---|---|---|
| job_first | 3 failed, 12 passed, 5 subtests; test MagicMock could not be hashed by the real source-identity builder | `9312f8eb2580c50b73dde88722dc357645de0f8615184dfd7d0fe7ac510e34ce` |
| job_scope_retest | 2 failed, 1 passed; fixture counted Markdown underscores as visible characters | `c0dc4479b23aa372fb71cecc9ffab05a01e790b41348dbe882f0720c627062ea` |
| job_diagnostic_retest | 1 failed; actual fixture count 3027 versus requested 3100 | `528f8dbf9213b44a7fa52cb0e3fee694809d506094843611d629fd0330520cfe` |
| job_core_retest | 1 failed; app exported, but test incorrectly fixed request count and ignored real Lint counterchecks | `8286f79ef00ade64165387db0c75f3686628837293bc9f5624fcb5d30baabe8a` |
| job_consumer_retest | 4 passed, 1 failed; test expected an obsolete V1 prose path instead of the real V2 content-addressed candidate | `ce4ce53959e5335cd261602bb06d4da4a929ee68f2310d8d1c42f78b0d06baad` |
| job_final_retest | **19 passed, 5 subtests; exit 0; 304.99s** | `74f3896430f785df84daa907edc08e331f49afe3f374cc0303b0502702e4b550` |

Final command: `python -m pytest tests/test_cnw_pack_job.py tests/test_cnw_pack_runs.py tests/test_cnw_export.py tests/test_studio_cli_routes.py::StudioCliRouteTests::test_public_commands_match_registry tests/test_studio_cli_routes.py::StudioCliRouteTests::test_supported_routes_point_to_tracked_implementations -q`.

`job_final_retest.job.json` SHA256:
`33e7777f7efc961377d2ef0c9ba8ad65f1555d56374ab6c943820c16cc471a08`.
It captures actual materialized stage text, Run state, request/raw model responses
and final export bindings: **3 tasks, 33 stages, 60 simulated model requests**.
`job_final_retest.index.json` independently recomputes all captured stage and
request/raw/content SHA values against those actual records. Temporary fixture
roots are released at test teardown; the captured evidence remains readable.
After this result, the fixture evidence collector was extended to retain actual
export TXT/Markdown/HTML/manifest/transaction-marker UTF-8 bytes and SHA as well.
That collector addition is not covered by the above run; it will execute with
the next already-required ATOM09 matrix run. No prior raw result was rewritten.
One subsequent bounded fix prevents a job with every task `CAPACITY_PENDING`
from claiming mock stories were exported. Its real-entry negative test passed:
`job_capacity_pending`, exit 0, 1 passed in 5.93s; raw SHA
`e8dab3343f7e6a5a7f82c535092c6ec5a535090c110dc0c91f525effb19a83d2`.
No task Run, model request or export was created. This later source state is
recorded separately and is not represented as the source state of the 19-test run.

Python compilation, PowerShell Parser and `git diff --check` passed, exit 0.
`job_syntax_final.check.json` records the five changed Python/PowerShell source
hashes; its raw SHA is `6f201fc5a1d1a7ed90aa9b09ad16a57e9dedb431d8117825a4463c98dd337811`.

Read-only protection check `package_job_20261013` confirms real TS state and
the real shared ledger still match their prior SHA anchors, and the frozen
`26b72cea` baseline retains its original Tree and clean state. No real project
Run, Provider receipt or ledger was rewritten, replayed, migrated or cut over.

## Remaining acceptance scope

The current package adapter supports the declared legacy insertion format.
This batch does not prove ADAPT/JSON or source-free ORIGINAL two-episode jobs
through the same application entry. Those paths and the complete R5 M01–M16,
Workflow01–05/Sprint/isolation/transaction matrix remain required before the
full ATOM09 candidate can be independently accepted.

`ATOM09=NOT_ACCEPTED`; `GENERIC_LIVE_PRODUCTION=NOT_RUN`;
`W10_ATTESTATION_PENDING`; `CUTOVER_BLOCKED=true`.
Previously recorded Controller RETURNs remain unchanged.

## Native package WIP and two bounded recovery repairs

The native adapter declares project groups, source aliases and writing tasks.
The application assigns internal identities and contracts, selects the declared
source, and delays an original continuation's contract until its actual prior
candidate has completed all stages, review and export. Carry-forward remains
`SIMULATED_CARRY_FORWARD`, `promoted=false`; it does not publish to Canon or
the authoritative episode directory. This is an additional input adapter and
uses the same real CNW consumers.

The native fixture has five tasks in the plan's three fictional projects:
Harbor INSERT and anchor-free ADAPT selecting B, Orchard single-line JSON
object-pointer ADAPT in Chinese, and source-free original EP001/EP002 declared
in reverse order. It uses the application entry for orchestration.

Original logs and source SHA maps are outside the repository at
`D:\CangqiStudio\StoryStudio_R5_Atom09_Native_20261013_728cf4d`.

| Label | Actual result | Raw SHA256 |
|---|---|---|
| native_first | **exit 1**, 1 failed / 1 passed / 5 subtests; assertions reached completed stages, export and no-new-model repeat, but final evidence serialization failed on WindowsPath; not a passing E2E result | `dc0bce066afa860d6543a7583a10042e00f5b8ceeecf427bb9c779941a0f314e` |
| native_red | **exit 1**, 4 reported failures including a CON subtest; reproduced reserved-name acceptance, A/TASK-A contract collision and lack of the staged-write boundary | `2ecc28253ba3f0a08f8f5c465913bbe0e498b28e18fc1f997a6d6c98b41c81be` |
| native_root_retest | **exit 0**, 3 passed / 4 subtests; same finite oracles after repair, source unchanged during run | `354ee6287c294e51091f3f374a6feac0e2e21954dcda353715c8e5a0ea5ebd3f` |

The repaired mapping always prefixes task aliases with `TASK-`; distinct
aliases have distinct contract components. Portable-name validation runs before
registration. Native immutable publication writes and verifies a complete
temporary file, then atomically creates the final file exclusively with a hard
link. Failed attempts are retained separately; existing final bytes may only be
verified and reused. The real contract builder and validation are retained;
only native-contract publication uses this path. Historical contract entry
publication keeps its previous text-writing behavior.

The already-required `native_full_retest` ran with frozen source:
native job plus input-pack, package-app, package-run, task-requirements, export
and pre-R5 role compatibility tests. The added fault case targets EP002 contract
publication after EP001 completes, followed by same-job recovery and prior-byte
checks. This command did not reach that fault because of the earlier Chinese
Re-review test assertion. The evidence collector now reads
request/response bytes from actual Run receipts instead of serializing memory
Path objects. No candidate acceptance is claimed. The command ended with exit 1:
3 failed, 45 passed and 42 subtests in 476.00s;
raw SHA `1ae5e752fc5b6b73010670c044f329854bf6b49224dce4f0503d819f5adf2e66`.
The added Chinese Re-review assertion incorrectly inspected the whole request,
including the legitimate old-text diff, instead of the current draft. The two
old archived-source subcases had not entered the owned operation simulation
session and stopped at the real authorization gate. Original logs are retained.
No submission or push has occurred.

## Preparation interruption closure — still WIP

The short `preparation_red` case injected a real exclusive-publication failure
after the original declaration had been sealed. It reproduced the incorrect
`IMPORT_INCOMPLETE` result: exit 1, one failed, raw SHA
`e3947185877c84dca558e207ad00dad4c3f9e992487a88b7958361b85e57431c`.

Preparation now has a separate persistent `JOB_PREPARATION_INCOMPLETE` result
with task, preparation stage, error code and retained interruptions. Both
preparation callers validate the job's ownership before storing a failure.
Same-job recovery validates existing immutable files and leaves the original
archive/origin unchanged. No model call is needed to recover initial preparation.
The real contract builder, source checks and Provider permission gates remain.

`preparation_scope_retest`: exit 0, **5 passed / 6 subtests**, 40.94s,
source unchanged during the command, raw SHA
`0eaa783277bf5485aac474aa7202d74c9c2ecb3798204adfe94ccf17716fc998`.
This also keeps the reserved-name/path-collision/partial-write oracles and the
archive-source rejection. The archive test now uses the existing owned simulation
session and real bound request/raw/receipt files; its original confirmed-source
and unchanged-Canon assertions are retained. Real slot/HTTP calls remain zero.
Chinese Re-review inspects the actual current draft and its candidate SHA;
the old text remains legitimate in the diff.

Current source is frozen for two finite necessary combinations:
`native_final_scope` (native and legacy package jobs plus affected compatibility)
and `method_matrix_current` (existing actual three-project, Workflow 01–05,
five-episode Sprint, review/refutation, recovery and operation gates).
`native_final_scope` remains in progress. The Controller identified one remaining
metadata defect: successful preparation must clear only its own preparation
blocker, preserving an existing execution/author blocker. This awaits terminal
results before editing; no whole-Atom acceptance is claimed.

The current reader independently inspected the real user archive without import,
Run creation, network or subprocess: all **371 payload SHA values** matched,
three tasks preserved min/target/max `2200/3100/4700`, `author_plot`, empty declared
beats and `new_plot_pre_designed=false`. `actual_user_pack_readonly.json` stores
only redacted task identifiers/hashes and non-content requirements outside Git.
Archive SHA remains `5d50fa4395512f74a32f6f8be04cdf98ae40da923a029eaf8ea8d49d5ed89196`.
This is declaration-reading evidence, not real story-generation acceptance.

The sole continuing Controller remains `/root/goal_controller_61_restart_20261013`
(GPT-6.1 Sol). The earlier one-time replacement instruction is already handled;
context restoration must not recreate it. Historical judgments remain unchanged.

## Completed method matrix, not whole-Atom acceptance

`method_matrix_current` ended with exit 0: **80 passed, 54 subtests**, 1221.76s;
172 recorded source files remained unchanged. Original raw SHA256:
`51a71ce415e47aab37820218c216bf915fd1e67aa849aea1c99c94a8b93de517`.

Actual capture files remain outside Git in the same native verification folder:

- `method_matrix_current.public.json`, SHA256
  `cdaef5d5218871580ba5ae62caf828f60d13d6e3f8168e50519d04ab9425e10d`.
- `method_matrix_current.three_projects.json`, SHA256
  `f1ed81a6aec367226aa616cb88acd448b45486c9e5247673d6795db166b311df`.

The snapshot index recomputed 1681 explicit captured-file SHA values and 275
explicit hashes in the original three-project capture, with no mismatches.
It explicitly does not claim the five text fields without associated SHA keys
were checked by that small indexer. The independent Controller separately read
the real artifacts, 42 Run snapshots and 296 request/raw/content receipts and
checked their simulated markers; it also checked all 55 stages in the original
three-project method capture. Its verbatim WIP message is outside Git:
`D:\CangqiStudio\StoryStudio_Controller_Restart_20261013\WIP_METHOD_EVIDENCE_REVIEW_20261013.md`,
SHA256 `306525964dfacdb8a2b81958251e999db838f32092d8de3aa3220e6c8342a096`.

These are current component-method results. The native automatic package chain,
the pending preparation-blocker cleanup and exact C/T review still precede any
complete ATOM09 acceptance or push authorization.

## Native/legacy combination terminal and final bounded repairs

`native_final_scope` ended with exit 0: **53 passed / 44 subtests**,
2464.60s; all 172 recorded source files stayed unchanged. Raw SHA256:
`caea89a58fb75a1dd2fe176ad2f915b92be32a9cedf8633c9ac00a76a7be37a7`.
Native capture SHA256:
`90cfbae1015618b2415ef4b3133f4f308059ef4f6d6634b947f99168d9c07b32`.
The continuing independent Controller checked its 55 stages, 60 export files,
80 actual simulated requests/responses and deferred EP002 publication recovery.
This passing command predates the final repairs below; it is not claimed as
evidence for later source bytes.

The Controller identified three bounded closure items: preparation must retain
execution/author blockers; managed exports must document the package-job entry
instead of manual-contract Live commands; deterministic replies must produce
distinguishable intent and continuation results. No new role or production
permission is introduced by these repairs.

The actual no-harness application entry refused at `OFFLINE_PROVIDER_FORBIDDEN`.
Re-preparing the same job then discarded its blocking reason. A first negative
had an incorrect exit-code expectation (the existing failed job correctly exits
2); its raw is preserved as `execution_blocker_red`, exit 1, SHA256
`f5f2c0c0eaa96b0db75ada65b94a1a35ba39a5650b6e4c5da8e0ea4c9e975d5f`.
After correcting only that expectation, `execution_blocker_red2` reproduced
the actual missing reason: exit 1, SHA256
`5243778bac789061f438fd233add5b1d871056250d7f646d6035bd9a678de57b`.

Cleanup now applies only to a previously interrupted preparation that actually
completed preparation recovery. Managed export instructions use `project-pack`
with the same job file and selected DataHome, state simulation/Live boundaries,
and require no user-supplied contract/WorkId/RunId. Non-managed instructions keep
their previous bytes. The final native fixture distinguishes INSERT, ADAPT,
original first chapter and continuation across Plot/Cards/Brief/Prose/Refine and
checks the actual final exported text. These are pending final-byte validation
and exact local candidate C/T review. No ATOM09 ACCEPT or push is claimed.

`final_repairs_scope` preserved a test snapshot lookup error: the actual
execution-failure report did not have an `interrupted_task` key. Exit 1,
9 passed / 4 subtests, raw SHA256
`73bd3c161dda82c11294bebe5dab678e250329238cd732a0476306d4b87f0f6b`.
The assertion now compares both original key presence and value, rather than
inventing a field in the actual report. `final_repairs_scope2` ended with exit 0:
**10 passed / 4 subtests**, 59.95s, source unchanged; raw SHA256
`8a12f1ae9d07bb3ee95f4d9dfc51979e693acb5e2984cb54a7a7c4925118b95a`.
It covered real Provider refusal followed by preparation, unchanged Run bytes,
initial preparation-fault recovery, original export tests and pre-R5 role
compatibility. The full distinguishable native-chain fixture and managed
instructions remain subject to final-candidate clean-clone execution and
independent review; this is not a full Atom verdict.

Final source compile/config JSON/PowerShell Parser and `git diff --check` passed
with source unchanged (`final_syntax_retest`, raw SHA256
`abcb16fe883febbc5e1c94c71d345e58959e6ae3b1d7c9f08cc6608e74d55356`).
The preceding syntax wrapper had a PowerShell argument-passing error and is
retained as `final_syntax`, exit 1, raw SHA256
`2c435600e01f1843c15b7dccefe14880d35deb2a16465811b89a2f2bf8d026cd`;
the repaired wrapper uses an explicit parameterized `.ps1` parser script.

A local main candidate is now being frozen for exact-commit clean-clone tests.
No installed application runtime or private project will be copied into the
clone. Source-only verification and prepared-runtime offline verification will
be recorded separately, with explicit dependency/pin and environment evidence.
The immutable old reference remains read-only. Whole-Atom review and push
authorization remain pending the actual final-byte evidence.
