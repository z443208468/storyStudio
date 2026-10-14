# StoryStudio PowerShell command routes

The PowerShell facade requires an explicit project context for project and run
operations. It has no default project path. `doctor` is app-only and performs no
provider request; `setup` persists an explicitly selected DataHome.

`SUPPORTED` means that a generic route resolves to tracked code. It does not
claim a complete workflow result; full command semantics and the 11-stage
offline product acceptance remain current Atom-09 gates. `LEGACY_ONLY` routes are kept
as explicit compatibility affordances and are not required in a clean clone.
The refactor's route checks and fictional model simulations perform no real
Provider call. A tracked route or available Key does not authorize production.

| COMMAND | REFERENCED_IMPL | IMPLEMENTATION_TRACKED? | PURE_GENERIC? | STATUS | CLEAN_CLONE_SMOKE_TEST |
|---|---|---:|---:|---|---|
| doctor | `tools/studio.ps1` → `tools/studio_health.py` | YES | YES | SUPPORTED | `test_health_checks_reject_reference_and_build_identity_mismatch` |
| setup | `tools/cnw_project.py:setup` → `tools/project_paths.py:setup_data_home` | YES | YES | SUPPORTED | `test_registered_project_commands_use_temp_data_home` |
| project-init | `tools/cnw_project.py:registered-init` | YES | YES | SUPPORTED | `test_registered_project_commands_use_temp_data_home` |
| project-import | `tools/cnw_project.py:registered-import` | YES | YES | SUPPORTED | `test_registered_project_commands_use_temp_data_home` |
| project-pack | `tools/cnw_pack_app.py:import_package` | YES | YES | SUPPORTED | `test_powershell_package_entry_creates_all_isolated_tasks` |
| import-source | `tools/cnw_project.py:source-import` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| source-list | `tools/cnw_project.py:source-list` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| project-contract | `tools/cnw_project.py:draft-contract` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| project-incremental | `tools/cnw_project.py:registered-incremental` → `semantic_import` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| canon-audit | `tools/cnw_project.py:canon-audit` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| handoff | `tools/cnw_project.py:handoff` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| arc-review | `tools/cnw_arc.py` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| standard-operation | `tools/cnw_project.py:standard-operation` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| support-workflow | `tools/cnw_project.py:support-workflow` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| produce | `tools/cnw_runner.py:produce` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| step | `tools/cnw_runner.py:step` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| resume | `tools/cnw_runner.py:resume` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| refresh-references | `tools/cnw_runner.py:refresh-references` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| review | `tools/cnw_runner.py:review` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| promote | `tools/cnw_runner.py:promote` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| export | `tools/cnw_runner.py:export` → `tools/cnw_export.py` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| show-run | `tools/cnw_runner.py:show-run` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| verify-history | `tools/cnw_runner.py:verify-history` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| verify-live | `tools/cnw_runner.py:verify-live` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| sprint | `tools/cnw_runner.py:sprint` → `tools/cnw_sprint.py` / `tools/cnw_sprint_live.py` | YES | YES | SUPPORTED | `test_live_sprint_accepts_registered_root_before_plan_validation` |
| prepare | `tools/studio.ps1:Assert-Prepared` | YES | NO | LEGACY_ONLY | `NOT_APPLICABLE` |
| verify | `tools/studio.ps1` (legacy offline patch check; live delegates to run-bound `verify-live`) | YES | NO | LEGACY_ONLY | `NOT_APPLICABLE` |
| prepare-live | `tools/cnw_live_executor.py` (V1 packets; V2 checked stage preparation) | YES | V2 branch | SUPPORTED_WITH_AUTHORIZATION_GATES | `test_cnw_w10_v2_consumers.py` |
| live-call | `tools/cnw_live_executor.py` (V1 packets; V2 checked whole-stage execution) | YES | V2 branch | SUPPORTED_WITH_AUTHORIZATION_GATES | `test_cnw_w10_v2_consumers.py` |
| accept-role | `tools/cnw_live_executor.py` (manual legacy output; V2 rejects downgrade) | YES | NO | LEGACY_ONLY; V2_REFUSED | `test_cnw_w10_v2_consumers.py` |
| w10-nk-live | `tools/cnw_w10_nk_live.ps1` | YES | NO | LEGACY_ONLY | `NOT_APPLICABLE` |
| w10-critics-live | `tools/cnw_w10_critics.py` | YES | NO | LEGACY_ONLY | `NOT_APPLICABLE` |
| nk-start | pinned NK build under `runtime/patched/NK` | NO (local runtime build) | NO | LEGACY_ONLY | `NOT_APPLICABLE` |
| nk-stop | pinned NK build under `runtime/patched/NK` | NO (local runtime build) | NO | LEGACY_ONLY | `NOT_APPLICABLE` |
| scene | `tools/studio.ps1` (selected-project, explicit WorkId checkpoint reader) | YES | NO | LEGACY_ONLY | `test_legacy_scene_requires_and_reads_explicit_project` |
| legacy-scene | `tools/studio.ps1:scene` (explicit compatibility alias) | YES | NO | LEGACY_ONLY | `test_legacy_scene_requires_and_reads_explicit_project` |

Every remaining project/run route checks for `-ProjectRoot` before dispatch.
`project-init` and `project-import` require an explicit `-DataHome`; source
revision listing returns source IDs and immutable manifest/index SHA256 values
without exposing source text. `project-contract -InputFile` consumes explicit
source ID, source revision, manifest revision, index revision, and adaptation
range fields; it never selects the first imported source implicitly. Setup can
also receive an explicit `-DataHomePointer` for isolated, testable setup state.
`review` includes the SHA of the project output that was current when the
candidate entered external review. Promotion evidence must preserve that
`expected_current_sha` (or explicit `null` for a new output); a concurrent
publish returns `PUBLISH_CONFLICT` and leaves the candidate unpromoted.

`project-pack -InputFile <ZIP> -DataHome <absolute-path>` reads all declared tasks,
uses a new registered instance for each, derives the explicit fifth Lens duties,
and builds V2 drafts/contracts. It can obtain exact pinned public GitHub source
objects in the selected DataHome's private cache. Use `-SourceRepository <path>
-Offline` for a strictly local source; `-Offline` never fetches missing objects.
It does not persist a setup pointer or start a Provider. Repeating the command
creates new independent instances. An unknown occupied DataHome/cache is refused.
`CAPACITY_PENDING / UNIT_CAPACITY_UNVALIDATED` preserves the original requested
bound and draft; it is not story readiness. Partial failure keeps its job record
and all instances. Full field consumption and production authorization remain
separate R5 gates.

## Package-owned Run preparation

Import and prepare all declared tasks:

```powershell
.\tools\studio.ps1 project-pack -InputFile '<writing-package.zip>' -DataHome '<absolute DataHome>' -PrepareRuns
```

For a fully local source, add `-SourceRepository '<local pinned Git repository>'
-Offline`. The default without `-PrepareRuns` imports inputs and contracts only.
Preparation calls `tools/cnw_pack_app.py:prepare_package_runs` and the actual
`cnw_runner.produce(create_only=True, mode="offline")`; the app derives Run IDs
and validates contract, instance, source, policy and existing-Run identities.
It does not run the writing stages or call a Provider.

The returned `job_record` identifies this job. Recheck it or resume interrupted
Run preparation:

```powershell
.\tools\studio.ps1 project-pack -JobFile '<returned job record>' -DataHome '<same absolute DataHome>' -Offline
```

`-JobFile` performs Run preparation/revalidation itself; it does not require
`-PrepareRuns`, reimport the ZIP, fetch sources or reset completed progress.
`-InputFile` and `-JobFile` are mutually exclusive. A stored job rejects
`-SourceRepository`. Repeating `-InputFile` creates a new job and independent
instances; it is not a shortcut for resuming an existing job.

`RUNS_PREPARED_PENDING_AUTHORIZATION` records actual offline Runs, with Provider
permission false. Identity conflicts retain prior progress. Old capacity-pending
records are not rewritten; new V2 contracts freeze ADVISORY length semantics.
Current Atom07 offline engineering is closed at `b93d0094`; Atom08 safe engineering
is in progress and current Atom09 acceptance is pending. V2 checked execution,
request-bound authorization and shared accounting are implemented interfaces;
production trust deployment and the actual package-to-real-story acceptance
have not run. Simulated receipts cannot satisfy Live gates.
The final application flow must handle internal identities and stages from the
supplied package; low-level diagnostic commands do not complete that flow.

## Explicit execution mode and independent Live attempts

```powershell
.\tools\studio.ps1 project-pack -JobFile '<job record>' -DataHome '<same absolute DataHome>' -Offline -Mode offline -ExecuteJob
.\tools\studio.ps1 project-pack -JobFile '<job record>' -DataHome '<same absolute DataHome>' -Mode live -ExecuteJob
```

`-Offline` controls Git source acquisition. `-Mode` controls execution intent;
Live never falls back to simulated output. A Live job uses an independent bound
attempt and real reviewed request grants; it does not relabel an offline Run.
`-NewAttempt` requires `-ExecuteJob -Mode live`, preserves old attempts and their
fees, and does not itself grant a Provider call. Existing jobs keep their
contracts, requests, stage artifacts and failures on interruption.

The V2 `prepare-live/live-call` branches use actual `execute_checked` stages.
The manual `accept-role` path cannot supply a substitute V2 stage receipt.
Maintenance's `prepare_only=True` is a Python API; no matching PowerShell
parameter is declared. Source preparation, creative approval, Controller
attestation, Owner Live/fee permission and Key availability remain separate.
