# ATOM-08 — modification-before inventory

Status: `INVENTORY_PREPARED; CONTROLLER_REVIEW_PENDING`.
This is not an Atom acceptance, a deletion approval, or a product-completion record.

## Accepted predecessor and allowed work

- Current local `main` and actual remote `main`: commit `b93d0094003ca93428ab18fd5def6d29119543d0`, tree `8c4b97ac61092c9522a674c67625b88df19b8db7`.
- Original independent verdict: `evidence/ATOM07_CONTROLLER_ACCEPT_b93d009_20261014.md`, SHA256 `f847c15d9f9bc07d404faf46c28cacb1f6b04460909ce6f17882551a0c69e852`.
- Freeze and actual push/readback: `evidence/ATOM07_FREEZE_b93d009_20261014.json`.
- Activity: only Atom08 safe engineering. No private deletion, relocation, migration, cutover or Atom09 execution.
- The original predecessor RETURN is preserved. Current07 offline closure is not production trust deployment or Live/input-package delivery acceptance.

## Read-only public inventory and byte-preserving backup

The external evidence directory is `D:\CangqiStudio\StoryStudio_R5_Atom08_20261014`.
No archive has been placed in an application template or project workspace.

| File | SHA256 | Actual scope |
|---|---|---|
| `atom08_readonly_inventory.json` | `987b79260a30f9ac44fad4deda4f8986e1b33f65275101f099bc3f2e8cd25b01` | 193 tracked public source/document identities; 39 candidate/retained routes and string consumers; 53 files with historical markers; 14 historical evidence filenames only |
| `atom08_public_originals_b93d009.zip` | `35e404e3e85cff7700af2dee2cc285e7b016a8cfe5d3aa4c643cf6f7258cb4b8` | Original working bytes of all 193 public files, all members reopened and SHA-matched |
| `atom08_public_originals_manifest.json` | `5213bb2cd0168b142fffaea7600d7d4406887e970b7268378cc253ca4545252a` | Original paths, byte sizes, working SHA and Git blob SHA; actual byte differences remain declared |
| `atom08_protected_before.json` | `d34f341092336d7d166a6966b5e6c301ab8ca0b42c65d3200c711d5507d58c48` | Authorized TS state/real ledger SHA unchanged from07 freeze; frozen pre-R5 clone remains pinned and clean |

Scripts `inventory_atom08.py`, `backup_public_sources.py`, and `freeze_protections.py` are alongside those records. Inventory and backup processes terminated successfully. String references are a candidate consumer inventory, not semantic call-graph proof or approval to remove any file. No private file content was copied into the public inventory/backup.

## Source-only cold clone baseline

An independent new source-only clone was created at `clone_before_b93d009` under the external evidence directory. It contains neither original runtime nor private project data.

Actual command:

```powershell
pwsh -NoLogo -NoProfile -NonInteractive -File tools/studio.ps1 doctor -AppOnly
```

Exit code: `0`. Raw: `atom08_source_only_before.raw.txt`, SHA256 `ff0defb443ba959deea406e618a0d0ba18954b8276b84cc2b6e40ad4261f5a10`. Source identity and command are recorded in `atom08_source_only_before.json`; git status is empty. The child process's Key environment was removed; no Key file was opened.

Actual result: engine/core available, project `NOT_SELECTED`, provider call `none`, author reference `RUNTIME_MISSING`, optional NK/CritiCS `IDENTITY_MISMATCH`, generic Live `NOT_RUN`. This is a source-only baseline, not prepared-bootstrap or production-stage evidence.

## Findings submitted for consolidated Controller classification

1. README/CLI claim prior Atom09 acceptance and old limited07 state; bootstrap documentation claims V2 production routes remain absent. Those statements need current exact evidence and status rather than historical component results.
2. Active role/prompt mappings and production/technical/acceptance documents still describe a historical single-story scope. Method consumers must be preserved in any generic replacement; old bytes are backed up.
3. Historical plans/reviews and one-off tools need per-file classification and source-to-new-route mapping before any normal deletion/replacement candidate.
4. `p2_06_critics_run.py`, `p2_cost_guard.py`, fixed historical Policy and W10/source-map identity code have actual generic/compatibility consumers. Filename or an old identity string alone is not a removal criterion.
5. Managed export's fixed simulated wording is the already-reported later product issue; its correct current08/09 scope awaits consolidated classification.

Writer has not changed production code, archived historical evidence files, or started09. The existing independent Controller is reviewing the full current08 scope and affected frozen functions and will report all discovered issues together. This preliminary Writer inventory cannot substitute for that review.

## Subsequent actual work in the same Atom (not a closure)

The preceding paragraph records the initial inventory boundary. The independent
Controller has since returned a consolidated nine-category list, saved verbatim
in `ATOM08_CONTROLLER_INVENTORY_20261014.md`. Writer is implementing that one
list; no partial ACCEPT or next-stage permission has been requested.

- Seventeen active documents/method contracts were updated against current
  parser, role reads, real request/authorization consumers and exact07 status.
- Twenty-four old public history documents now contain inactive same-path
  indexes; seven one-off entries refuse execution. Original bytes are in the
  verified external archive. The per-file source/consumer map is
  `ATOM08_HISTORY_SOURCE_MAP_20261014.json`, SHA256
  `543946cfd2b49ba66353f97324e5e45bf7c092405c96af89aa7c16780e898f70`.
- `tools/cnw_export.py` was minimally changed to describe receipt markings and
  requested mode accurately. Live mode alone is `LIVE_REQUESTED` with
  `NOT_CHECKED_BY_EXPORT`; simulation remains simulated even if mode says live.
  Recovery instructions use the corresponding mode without granting permission.
  This changes a signed implementation input: old grants cannot be reused as
  signatures for the new bytes.
- Existing V1/V2 exports plus three formatting/label negatives, the real
  managed Live-evidence rejection and mismatched-implementation signature test
  terminated with exit0, **13 passed**. Raw external file:
  `atom08_export_regression.raw.txt`, SHA256
  `c4c71be4eb3d0161c05229c409e5c26bc0a744b8debc9effdef5ff141e47be13`.
  `atom08_export_regression.json` records command and source hashes, unchanged
  during that run. This is affected export/authorization-negative evidence, not
  a new full CNW Run or actual Live delivery. Final common document/archive and
  cold-clone checks are still pending.
- The inventory's fourteen historical-looking evidence paths include four
  **current R5 source-byte records**, which remain protected. The ten old
  top-level public P2/P3 records have not been edited or moved; they need explicit
  classification, rather than retirement by a `p2` filename match.

An unrelated concurrent change to `AGENTS.md` appeared during this work: four
workspace/project-directory rules, file timestamp 2026-10-14 09:42:28 JST. Writer's
scripts did not write AGENTS. Its current SHA is
`11f15061153c63570ef68b8a67f7addcc6c72cb8cef7421c1d71433ba36d67f1`, compared with
the backed-up original `f6bffbc9cf442fbc67a5f94024c7b5a0df2f719a9bff39f7d3b3a2bdc7cc7f13`.
The actual bytes/diff were separately preserved externally and sent to the same
readonly Controller for scope reconciliation with frozen registered DataHome
ownership. They are not automatically included in Writer's candidate.

No08 candidate has been committed or pushed. Private migration/cutover, real
Provider calls,09 execution and final input-package delivery have not occurred.

```text
ATOM08=INVENTORY_PREPARED; NOT_ACCEPTED
ATOM09=NOT_RUN_IN_CURRENT_SEQUENTIAL_EXECUTION
GENERIC_LIVE_PRODUCTION=NOT_RUN
INPUT_PACK_TO_STORY_GATE=NOT_COMPLETED
PRIVATE_MIGRATION=NOT_RUN
CUTOVER_BLOCKED=true
```
