# Historical originals and current generic routes

Only [R5](../plans/MASTER_PLAN_GENERIC_APP_R5.md) is the active plan.
Historical plans, reviewer instructions, diagnostics and one-off commands retain
their original bytes and verdicts. Their former story-specific instructions
cannot authorize current application work or a Provider request.

## Original bytes, paths and identities

Before Atom08 modifications, 193 tracked public source/document files were copied
byte-for-byte into an independent external archive:

- Directory: `D:\CangqiStudio\StoryStudio_R5_Atom08_20261014`.
- Archive: `atom08_public_originals_b93d009.zip`.
- Archive SHA256: `35e404e3e85cff7700af2dee2cc285e7b016a8cfe5d3aa4c643cf6f7258cb4b8`.
- Manifest: `atom08_public_originals_manifest.json`, SHA256 `5213bb2cd0168b142fffaea7600d7d4406887e970b7268378cc253ca4545252a`.
- Source commit: `b93d0094003ca93428ab18fd5def6d29119543d0`, tree `8c4b97ac61092c9522a674c67625b88df19b8db7`.

All members were reopened and SHA-verified. The manifest distinguishes physical
working bytes from Git blob bytes where historical newline conversion differed.
Git history remains intact. Original canonical bytes can also be retrieved
read-only with `git show <source-commit>:<original-path>`; that does not restore,
execute or activate old files in the working tree.

The [per-file source map](../evidence/ATOM08_HISTORY_SOURCE_MAP_20261014.json)
records original paths/SHA, archive members, original consumer locations,
replacement SHA and current routes for 24 inactive history indexes and seven
retired one-off commands. Static imports and executable references were checked
before retirement. Old commands' outgoing calls/data paths remain in original
archived source; they are not executed to verify current routing.

## Current consumers and replacements

| Historical role | Current route |
|---|---|
| Old engineering plans | R5; same-path inactive indexes preserve provenance without activating another plan |
| Old Controller instructions / acceptance criteria | [Current Controller](../reviews/CONTROLLER_PROMPT.md), [AGENTS](../AGENTS.md), [acceptance](../implementation/ACCEPTANCE_SPEC.md) |
| Old single-story production / role / Prompt / technical contracts | Current generic documents at their original `implementation/` paths; originals remain archive members |
| One-off draft / revision / live probes | Non-executing retired entries; use [documented current CLI](CLI_COMMANDS.md), selected package/project and reviewed authorization gates |
| Original source / CNW method references | [Fixed sources](../reviews/CNW_ORIGINAL_SOURCES.md), C01–C15 and R5 M01–M16 remain current method evidence |

Keeping a historical reference path as an index avoids breaking the R5 pointer
to its protection requirements. It does not rewrite the original verdict as an
ACCEPT. Archived internal cross-references remain together under their original
paths inside the ZIP. A fresh clone can use current code/docs without this
external history archive; historical recovery requires that explicitly selected
archive or exact Git object.

## Production dependencies preserved

`p2_cost_guard.py`, price snapshots, `p2_06_critics_run.py`, `critics_bridge.py`,
the fixed historical Policy/snapshots, W10 old identities and the restricted
legacy source-map code still have current generic or compatibility consumers.
They were not renamed, removed or rewritten to erase an old identifier.
Names do not decide whether a component is historical. New projects do not
inherit their historical story facts, authorizations or budget exceptions.

Current R5 Controller verdicts, freeze records and tests remain accessible;
historical evidence files have not been silently removed. This inventory does
not claim every historical evidence artifact has been archived or every
possible dynamic consumer has been executed. The exact candidate and complete
current08 evidence must receive independent review before closure.

## Separate private-data boundary

No private project, input original, Provider raw, Run state, manuscript, ledger
or deliverable was moved/deleted by this work. Old private data remains protected
in place. No TS resume, paid Provider call, production trust installation or
cutover was executed. Permission to index public history does not authorize
private relocation or historical request replay.

```text
ATOM08_SAFE_ENGINEERING=IN_PROGRESS; NOT_ACCEPTED
LEGACY_PRIVATE_RELOCATION=BLOCKED/NOT_RUN
PRIVATE_MIGRATION=NOT_RUN
CUTOVER_BLOCKED=true
CURRENT_HEAD_FULLY_SEPARATED=NOT_ESTABLISHED
GIT_HISTORY_PRIVATE_SCRUBBED=NOT_CLAIMED
INPUT_PACK_TO_STORY_GATE=NOT_COMPLETED
```
