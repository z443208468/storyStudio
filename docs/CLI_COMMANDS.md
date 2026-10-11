# StoryStudio PowerShell command routes

The PowerShell facade requires an explicit project context for project and run
operations. It has no default project path. `doctor` is app-only and performs no
provider request; `setup` persists an explicitly selected DataHome.

`SUPPORTED` means that a generic route resolves to tracked code. It does not
claim a complete workflow result; full command semantics and the 11-stage
offline consumer chain are verified in Atom-09. `LEGACY_ONLY` routes are kept
as explicit compatibility affordances and are not required in a clean clone.
No command in this table performs a real provider call during the Atom-04
entrypoint checks.

| COMMAND | REFERENCED_IMPL | IMPLEMENTATION_TRACKED? | PURE_GENERIC? | STATUS | CLEAN_CLONE_SMOKE_TEST |
|---|---|---:|---:|---|---|
| doctor | `tools/studio.ps1` | YES | YES | SUPPORTED | `test_doctor_app_only_needs_no_project` |
| setup | `tools/cnw_project.py:setup` → `tools/project_paths.py:setup_data_home` | YES | YES | SUPPORTED | `test_registered_project_commands_use_temp_data_home` |
| project-init | `tools/cnw_project.py:registered-init` | YES | YES | SUPPORTED | `test_registered_project_commands_use_temp_data_home` |
| project-import | `tools/cnw_project.py:registered-import` | YES | YES | SUPPORTED | `test_registered_project_commands_use_temp_data_home` |
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
| sprint | `tools/cnw_runner.py:sprint` / `tools/cnw_sprint.py` | YES | YES | SUPPORTED | `test_project_commands_require_explicit_root` |
| prepare | `tools/studio.ps1:Assert-Prepared` | YES | NO | LEGACY_ONLY | `NOT_APPLICABLE` |
| verify | `tools/studio.ps1` (legacy offline patch check; live delegates to run-bound `verify-live`) | YES | NO | LEGACY_ONLY | `NOT_APPLICABLE` |
| prepare-live | `tools/cnw_live_executor.py` | NO (protected local WIP) | NO | LEGACY_ONLY | `NOT_APPLICABLE` |
| live-call | `tools/cnw_live_executor.py` | NO (protected local WIP) | NO | LEGACY_ONLY | `NOT_APPLICABLE` |
| accept-role | `tools/cnw_live_executor.py` | NO (protected local WIP) | NO | LEGACY_ONLY | `NOT_APPLICABLE` |
| w10-nk-live | `tools/cnw_w10_nk_live.ps1` | NO (protected local WIP) | NO | LEGACY_ONLY | `NOT_APPLICABLE` |
| w10-critics-live | `tools/cnw_w10_critics.py` | NO (protected local WIP) | NO | LEGACY_ONLY | `NOT_APPLICABLE` |
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
