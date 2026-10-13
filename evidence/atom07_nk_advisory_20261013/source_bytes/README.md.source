# StoryStudio

StoryStudio is being separated into a reusable writing application that can host multiple independent writing projects and their distinct requirements. The application keeps the upstream CNW workflow as its production core; Narrative Keyframing (NK) and CritiCS remain optional, separate integrations. This repository is in the R5 refactor, so the architecture and migration gates describe planned work until each stage has been implemented and independently accepted.

## Active plan and governance

- Active plan: [`plans/MASTER_PLAN_GENERIC_APP_R5.md`](plans/MASTER_PLAN_GENERIC_APP_R5.md), original approved source SHA256 `5CC22861CE3C0603D6EF89619594CD7CD68642241A20036032B031CB3A8C8ECF`; current owner-amended file SHA256 `408864DEFBE39C7CCD6A113C53614378688B18FD2EB48AC0A58ED6D246B6A247`.
- Read [`AGENTS.md`](AGENTS.md), [`CODEX_START.md`](CODEX_START.md), and [`docs/governance/GOVERNANCE.md`](docs/governance/GOVERNANCE.md) before changing the project.
- The R5 plan advances one Atom at a time, with an independent read-only Controller review for each candidate. Historical P2/P3/J19 plans and records remain historical and do not describe the current product goal.

## Intended application model

The app is intended to keep generic engine code and the pinned CNW method in the repository while storing project identities, contracts, source snapshots, runs, exports, and shared runtime state under an explicitly selected private data home. Different projects must remain isolated. The app must reject project writes when the user has not selected and registered the relevant data and project roots; it must not infer a default Cangqi/J19 project.

The CNW public method includes its eleven ordered stages, source-bound role inputs, layered lint, five independent review lenses, per-finding verification, completeness feedback, refinement, affected-item re-review, canon approval, and sprint gates. The exact invariants and migration checks are in the active plan and source-to-code map. The refactor does not claim these requirements are already satisfied by current runtime behavior.

## Current use and privacy

For a reproducible clean checkout and offline verification environment, follow [the bootstrap guide](docs/BOOTSTRAP_VERIFICATION.md). It includes fixed upstream pins, declared dependencies, offline cache preparation, missing-cache behavior, and source-only versus prepared doctor checks. It does not authorize Live production or select project data.

### Supply a writing package

After bootstrap, give the app a supported writing ZIP and an explicitly selected
absolute DataHome. The package contains the materials and writing requirements;
the application owns the CNW workflow and internal project/contract/Run identities.

```powershell
.\tools\studio.ps1 project-pack -InputFile '<writing-package.zip>' -DataHome '<absolute DataHome>' -PrepareRuns
```

The app discovers declared tasks, preserves their requirements, verifies and
seals the selected sources, creates separate registered project instances and
contracts, then prepares actual offline Runs. The current legacy scene-pack
adapter supports explicitly declared author-designed insertion tasks; its
supported format is documented in [input adaptation](docs/INPUT_PACK_ADAPTATION.md).
Use `-SourceRepository '<local pinned Git repository>' -Offline` for local objects
with no network fallback. Otherwise the package's exact declared public Git source
can be acquired in the chosen DataHome cache. This is source acquisition only.

The command returns a private `job_record`. Recheck or continue that preparation
using the returned path, without supplying a contract, Run ID or SHA:

```powershell
.\tools\studio.ps1 project-pack -JobFile '<returned job record>' -DataHome '<same absolute DataHome>' -Offline
```

`RUNS_PREPARED_PENDING_AUTHORIZATION` means that inputs and actual Runs are ready
for later gates. Atom-09's isolated fixture path has been accepted for offline
simulated production/review/export; this does not prove the supplied owner package
can run through Live production. The exact owner package has not yet been shown to
produce a real story. The generic V2 Live route and project-bound fee/authorization
handoff remain implementation work. Repeating ZIP import creates new instances;
`-JobFile` rechecks the existing job and retains its progress.

### Evidence and remaining work

The current code has offline evidence for source-bound and original contracts,
role consumers, review/revision, recovery and export. Atom-07's operation
and cache repair received an independent limited offline acceptance at
[`08b4fa4`](https://github.com/z443208468/storyStudio/commit/08b4fa44292809ce8553849945ee5a1eaf3236fa),
with a source-only cold clone passing 68 tests and 83 subtests. That scope does
not establish the package-to-story product gate or real model production.

`GENERIC_LIVE_PRODUCTION=NOT_RUN`; trusted production attestation and separate
Live/fee authorization checks remain required by the accepted R5 plan. The owner
has authorized necessary package acceptance after the plan and exact code gates.
Existing private data cutover is blocked. The final user flow must deliver stories
from the actual package through the fixed CNW workflow; internal JSON fields and
manual stage commands belong to diagnostics. Offline acceptance and an available
credential do not substitute for the reviewed production path.

Legacy interfaces and historical engineering records remain available within
their explicit scopes. Keep private drafts, credentials, Provider traffic and
private runtime data outside Git. No real production API call has yet been made
for the generic package flow; private-project migration remains separately blocked.

## Project documentation

- `docs/ARCHITECTURE.md` — engine, project, run, history, and path ownership.
- `docs/PROJECT_CONTRACT.md` — identity and per-project contract boundaries.
- `docs/CLI_COMMANDS.md` — implemented routes, package preparation and current gates.
- `docs/CNW_MAINTENANCE.md` — official Audit/Handoff responsibilities and recovery.
- `docs/CNW_COST_ACCOUNTING.md` — permission boundaries and historical campaign accounting.
- `docs/governance/` — active execution rules and plan authoring guidance.
- `plans/MASTER_PLAN_GENERIC_APP_R5.md` — staged implementation plan and acceptance gates.
- `implementation/` — existing CNW workflow and integration contracts; legacy-specific material remains labeled by its source and scope.
