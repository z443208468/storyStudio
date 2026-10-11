# StoryStudio architecture and path ownership

This document defines the target ownership boundary for the R5 generic-app refactor. Existing code and legacy paths are not claimed to have migrated merely because this document names their target owner. The active plan and Atom records determine what is implemented.

## Ownership

```text
StoryStudio/                         # tracked engine and pinned methods
  tools/                             # project-independent CLI, orchestration, adapters
  config/                            # generic schemas, policy examples, provider settings
  prompts/cnw/                       # method/role mapping, without project facts
  templates/                         # blank project and contract templates
  tests/                             # synthetic fixtures and temporary roots only
  docs/                              # active generic product and method documentation
  third_party/                       # upstream pins and license/BOM records

<explicit DataHome>/                 # private, outside the source repository
  setup/                             # optional; the setup pointer itself is user-level config
  projects/<project_instance_id>/    # one immutable internal identity per project instance
    project_identity.json
    contracts/
    runs/<run_id>/
    exports/
  shared/                            # unique writable cost ledger, locks, tool state
  tool_cache/                        # rebuildable, version- and pin-verified runtime dependencies
  archives/                          # optional restricted local run archives

<StoryStudio parent>/StoryStudio_Legacy_Archive/  # preserved source/history snapshot
```

## Path vocabulary and resolution

- `app_root` is the installed application and pinned method code. It never selects a project or stores mutable project data.
- `data_home` is chosen explicitly by `setup --data-home`, `-DataHome`, or `STORYSTUDIO_DATA_HOME`. A small machine-local pointer may persist the user choice. On Windows the pointer belongs under `%LOCALAPPDATA%\StoryStudio\setup.json`; other systems use the platform user config location. The pointer stores only the selected path and format version. It is not a fallback project/data location. Missing selection returns `DATA_HOME_REQUIRED`; malformed or unreachable pointer data fails closed.
- `project_root` is explicit via `-ProjectRoot` or `STORYSTUDIO_PROJECT_ROOT`, or resolved from a registered project instance. Project commands without it return `PROJECT_REQUIRED`. A writable project root must be registered under the selected DataHome and match its identity record. Restricted, read-only legacy mounts are a separate future capability.
- `project_id` and display name are mutable metadata and may repeat. `project_instance_id` is an immutable generated identifier used by contracts, runs, review records, costs, and exports.
- `run_root` is `<project_root>/runs/<run_id>`. New run identity includes the project instance and frozen contract/source identity; old receipts are read as legacy without rewriting them.
- `source_root` is derived from a project source manifest and its verified stored snapshots. A selected external source is imported once, read-only, hashed, and copied into the project before normal production reads it.
- `export_root` is the registered project’s private `exports/` directory or a separately selected, validated output path.
- `cost_ledger` is a single shared writable ledger. Migration must not create multiple writable copies of one actual spend history.

## Identity lifecycle

Registration creates one internal instance ID and one canonical writable project root. Moving a project (`relocate`) preserves the ID and must leave exactly one active writable location. Creating a new work from a copy (`fork`/`clone-as-new`) generates a new ID and requires new project approval and contract; active runs, cost ownership, and Controller ACCEPT do not transfer. Two active writable roots presenting the same instance ID fail with `PROJECT_INSTANCE_COLLISION`. A path difference alone never creates a new identity.

The setup pointer is persisted atomically and resolved in a fresh process. A damaged pointer fails closed. A newly created DataHome receives a protected ACL for the current user, Administrators, and SYSTEM; an existing root must already have an independent private ACL or setup is rejected without changing that existing ACL. The chosen DataHome is checked for canonical containment, reparse points, writability, independent access, and volume capacity before project registration. Do not infer a DataHome from the current directory, source checkout, old workspace, project name, or system drive.

## Filesystem safety

All user-controlled paths are normalized against an explicit root. Reject traversal, unexpected canonical escape, symbolic links and Windows reparse-point ancestors (including junctions), cross-project access, and time-of-check/time-of-use path replacement. Validation and write/migration occur under the relevant lock with a second path check. The Python 3.11 target cannot depend on `Path.is_junction()`; detect Windows reparse attributes compatibly. Windows same-volume replacement, locking and crash recovery must be tested separately from cross-volume behavior; one successful `os.replace()` call does not promise a multi-file or cross-volume transaction.

## Runtime readiness and optional tools

Cold start distinguishes `ENGINE_SOURCE_READY`, `CORE_RUNTIME_READY`, `PROJECT_READY`, optional NK and CritiCS states (`ENABLED`, `DISABLED`, or `UNAVAILABLE`), and `LIVE_PROVIDER_READY`. Missing project material does not make the engine unavailable. Disabled optional tools do not block CNW; an enabled but unavailable integration fails before that integration is run. Tool caches are validated against frozen upstream pins, patches, and dependency locks; an old workspace reference path is not a clean-clone bootstrap dependency.

## Legacy transition

The entrance states are `legacy_explicit_only`, `generic_shadow`, and `generic_active`. Before the plan’s final offline gates, generic behavior may run only through explicit shadow/testing entry points. Existing explicit legacy entry points, data, histories, toolchains, and the unique cost ledger remain in place until the corresponding Controller-reviewed gate. No project-specific history is a generic default or fixture. See the active R5 plan for the atom-by-atom transition and release gates.
