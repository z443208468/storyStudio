# CNW five-episode Sprint

The public reference is `MintoTsukino/claude-novel-workflow` at
`97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`. The implementation reads its
workflow configuration, batch review template and Workflow 05 handoff prompt
from the pinned local reference. This is an implementation of the public
method, not the author's unpublished automation.

## Entry

```powershell
python tools/cnw_sprint.py --project-root workspace/my_project --sprint-id SPRINT-01 --plan contracts/sprint01.json --mode live
```

The equivalent runner command is:

```powershell
python tools/cnw_runner.py sprint --project-root workspace/my_project --run-id SPRINT-01 --sprint-plan contracts/sprint01.json --mode live
```
Without `--mode live`, the existing fixture-only mode remains selected.
Live mode uses the existing shared provider budget and request receipts; it
does not create a new allowance. Use live mode only within authorized
production scope. The current Cangqi authorization remains the same J19
insert, so five real Cangqi chapters have **not** been run.

## Inputs

The private project must be under `workspace/` and contain the ordinary
production preparation files, source-bound episode contracts and
`00_meta/manuscript_review_rubric.md`. Plan paths are project-relative:

```json
{
  "episodes": [
    {"episode_id": "ep001", "contract": "contracts/ep001.json"},
    {"episode_id": "ep002", "contract": "contracts/ep002.json"},
    {"episode_id": "ep003", "contract": "contracts/ep003.json"},
    {"episode_id": "ep004", "contract": "contracts/ep004.json"},
    {"episode_id": "ep005", "contract": "contracts/ep005.json"}
  ]
}
```

Exactly five distinct episode contracts from one project are required.
Scene contracts and canned fixture results are rejected. Each episode after
the first must refer to its immediate predecessor, either using the standard
ep/ch numbering or an explicit `story.previous_episode_ref`. Modern contracts
use `unit.planning_mode: author_plot` so Plot designs the structure.

## Execution and evidence

Each episode runs the complete production pipeline in an isolated project
snapshot. The next episode receives the preceding candidates and accumulated
Lens feedback. Successful `verify_live` verification is required for each
candidate before batch review. Snapshot inputs and feedback seeds are checked
on continuation.

The batch reviewer receives all five actual candidates, their reviews and the
project rubric. Each reported finding receives three independent verifier
votes; at least two `not_refuted` votes retain it. A separate Completeness
request checks omissions and supplies reusable Lens feedback. The batch gate
uses the pinned public configuration (average score at least 75, zero P0,
at most two P1), readiness, and no outstanding Completeness omissions. It also
requires `project_rubric_status: pass` and an empty `stop_reasons` list.
The project's optional `00_meta/episode_production_manual.md` is frozen with
the rubric. Its project-specific thresholds are assessed by the reviewer;
the example novel's 64/80 thresholds are not hardcoded for other projects.

Private results include `sprints/<id>/batch_review.json`, a readable Markdown
report, candidate manuscripts, provider receipts and a next-Sprint handoff.
The canonical `93_exports/handoff_brief.md` is updated, preserving any previous
brief verbatim in `93_exports/archive/` under its content hash. A handoff changed
externally during production is preserved and blocks that publication.
Project indexes, runtime status and Lens feedback receive the results.
`REVISION_REQUIRED` retains the reports and unresolved issues. The command
does not automatically start another Sprint or assert user creative acceptance.

Rerun the same command to continue the same Sprint. Changed plan identities,
project context, pinned snapshot inputs or conflicting published manuscripts
are rejected. Existing different manuscript output is rejected before new
episode execution. Successful identical provider requests reuse receipts.

Current automated coverage mocks episode production, live verification and
provider responses: it exercises five-episode orchestration, feedback,
continuation and collision checks. It is **not** evidence of real five-episode
API production or of the literary quality of generated chapters.
