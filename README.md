# StoryStudio

StoryStudio is being separated into a reusable writing application that can host multiple independent writing projects and their distinct requirements. The application keeps the upstream CNW workflow as its production core; Narrative Keyframing (NK) and CritiCS remain optional, separate integrations. This repository is in the R5 refactor, so the architecture and migration gates describe planned work until each stage has been implemented and independently accepted.

## Active plan and governance

- Active plan: [`plans/MASTER_PLAN_GENERIC_APP_R5.md`](plans/MASTER_PLAN_GENERIC_APP_R5.md), original approved source SHA256 `5CC22861CE3C0603D6EF89619594CD7CD68642241A20036032B031CB3A8C8ECF`; current owner-amended file SHA256 `408864DEFBE39C7CCD6A113C53614378688B18FD2EB48AC0A58ED6D246B6A247`.
- Read [`AGENTS.md`](AGENTS.md), [`CODEX_START.md`](CODEX_START.md), and [`docs/governance/GOVERNANCE.md`](docs/governance/GOVERNANCE.md) before changing the project.
- The R5 plan advances one Atom at a time, with an independent read-only Controller review for each candidate. Historical P2/P3/J19 plans and records remain historical and do not describe the current product goal.

## Intended application model

The app keeps generic engine code and the pinned CNW method in the repository. New project identities, contracts, source snapshots, runs and exports use an explicitly selected private DataHome. Provider costs still use the existing shared application ledger at `runtime/private/p2-cost-ledger.json`; request accounting is bound to the selected project instance, but physical ledger relocation has not happened. Project writes require the selected registered instance; there is no default story. Legacy private data remains protected in place until its separate relocation and cutover gates pass.

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
contracts, then prepares actual offline Runs. The legacy scene-pack adapter
supports declared insertion tasks. Native V2 packages declare project groups,
selected sources, INSERT/ADAPT tasks and dependent ORIGINAL episodes; supported
formats are documented in [input adaptation](docs/INPUT_PACK_ADAPTATION.md).
Use `-SourceRepository '<local pinned Git repository>' -Offline` for local objects
with no network fallback. Otherwise the package's exact declared public Git source
can be acquired in the chosen DataHome cache. This is source acquisition only.

The command returns a private `job_record`. Recheck or continue that preparation
using the returned path, without supplying a contract, Run ID or SHA:

```powershell
.\tools\studio.ps1 project-pack -JobFile '<returned job record>' -DataHome '<same absolute DataHome>' -Offline
```

`RUNS_PREPARED_PENDING_AUTHORIZATION` means input and Run preparation only.
Existing V2 Live interfaces require independently trusted Controller attestation
and Owner Live/fee permission for the exact current request. Their offline
engineering acceptance does not deploy production trust or prove this ZIP's
real story output. Repeating ZIP import creates new instances; `-JobFile`
rechecks the existing job and retains its progress. Offline execution requires
an isolated test transport and produces `MOCK_ONLY / SIMULATED` receipts.

### Evidence and remaining work

The current sequential closure is 00–07, within each original frozen scope.
Atom07's complete current offline engineering verdict binds
[`b93d0094`](https://github.com/z443208468/storyStudio/commit/b93d0094003ca93428ab18fd5def6d29119543d0)
and tree `8c4b97ac61092c9522a674c67625b88df19b8db7`;
[the original verdict](evidence/ATOM07_CONTROLLER_ACCEPT_b93d009_20261014.md)
and [freeze/readback record](evidence/ATOM07_FREEZE_b93d009_20261014.json)
are included in the repository tree for clean-clone review. They state the
evidence and limits. Atom08 safe engineering is in progress and has
not been accepted. Atom06's prior exact-candidate ACCEPT and freeze are also
available in [its original verdict](evidence/ATOM06_CONTROLLER_ACCEPT_84e022d_20261013.md)
and [freeze record](evidence/ATOM06_FREEZE_84e022d_20261013.json). Atom09
awaits its current sequential review; historical fixture results do not
constitute a current Atom09 ACCEPT.

`GENERIC_LIVE_PRODUCTION=NOT_RUN`; trusted production attestation and separate
Live/fee authorization checks remain required by the accepted R5 plan. The owner
has authorized necessary package acceptance after the plan and exact code gates.
Existing private data cutover is blocked. The final user flow must deliver stories
from the actual package through the fixed CNW workflow; internal JSON fields and
manual stage commands belong to diagnostics. Offline acceptance and an available
credential do not substitute for the reviewed production path.

Legacy interfaces and historical engineering records retain their original
identities within explicit compatibility scopes. Keep private drafts,
credentials, Provider traffic and private runtime data outside Git. No real
production API call has yet been made for the generic package flow;
private-project migration remains separately blocked. The package-to-story
product gate is not completed and user creative acceptance remains separate.

## Project documentation

- `docs/ARCHITECTURE.md` — engine, project, run, history, and path ownership.
- `docs/PROJECT_CONTRACT.md` — identity and per-project contract boundaries.
- `docs/CLI_COMMANDS.md` — implemented routes, package preparation and current gates.
- `docs/CNW_MAINTENANCE.md` — official Audit/Handoff responsibilities and recovery.
- `docs/CNW_COST_ACCOUNTING.md` — permission boundaries and historical campaign accounting.
- `docs/governance/` — active execution rules and plan authoring guidance.
- `plans/MASTER_PLAN_GENERIC_APP_R5.md` — staged implementation plan and acceptance gates.
- `implementation/` — existing CNW workflow and integration contracts; legacy-specific material remains labeled by its source and scope.
