# StoryStudio

StoryStudio is being separated into a reusable writing application that can host multiple independent writing projects and their distinct requirements. The application keeps the upstream CNW workflow as its production core; Narrative Keyframing (NK) and CritiCS remain optional, separate integrations. This repository is in the R5 refactor, so the architecture and migration gates describe planned work until each stage has been implemented and independently accepted.

## Active plan and governance

- Active plan: [`plans/MASTER_PLAN_GENERIC_APP_R5.md`](plans/MASTER_PLAN_GENERIC_APP_R5.md), copied byte-for-byte from the approved R5 plan, SHA256 `5CC22861CE3C0603D6EF89619594CD7CD68642241A20036032B031CB3A8C8ECF`.
- Read [`AGENTS.md`](AGENTS.md), [`CODEX_START.md`](CODEX_START.md), and [`docs/governance/GOVERNANCE.md`](docs/governance/GOVERNANCE.md) before changing the project.
- The R5 plan advances one Atom at a time, with an independent read-only Controller review for each candidate. Historical P2/P3/J19 plans and records remain historical and do not describe the current product goal.

## Intended application model

The app is intended to keep generic engine code and the pinned CNW method in the repository while storing project identities, contracts, source snapshots, runs, exports, and shared runtime state under an explicitly selected private data home. Different projects must remain isolated. The app must reject project writes when the user has not selected and registered the relevant data and project roots; it must not infer a default Cangqi/J19 project.

The CNW public method includes its eleven ordered stages, source-bound role inputs, layered lint, five independent review lenses, per-finding verification, completeness feedback, refinement, affected-item re-review, canon approval, and sprint gates. The exact invariants and migration checks are in the active plan and source-to-code map. The refactor does not claim these requirements are already satisfied by current runtime behavior.

## Current use and privacy

The generic app is under construction; consult the active plan for the current Atom and verified capabilities before using commands. This repository still contains legacy interfaces and historical engineering records. They are not a safe default for a new project. Do not place private drafts, credentials, provider traffic, or private runtime data in Git. The current genericization work does not call production APIs or generate story content.

## Project documentation

- `docs/ARCHITECTURE.md` — engine, project, run, history, and path ownership.
- `docs/PROJECT_CONTRACT.md` — identity and per-project contract boundaries.
- `docs/governance/` — active execution rules and plan authoring guidance.
- `plans/MASTER_PLAN_GENERIC_APP_R5.md` — staged implementation plan and acceptance gates.
- `implementation/` — existing CNW workflow and integration contracts; legacy-specific material remains labeled by its source and scope.
