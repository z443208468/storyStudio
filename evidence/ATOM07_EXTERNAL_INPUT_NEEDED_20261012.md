# ATOM-07 external evidence still required — 2026-10-12

## Read-only tracked call-chain findings

The tracked `tools/studio.ps1` dispatch shows `prepare-live` and `live-call` delegating to `tools/cnw_live_executor.py`; role preparation requires explicit `InputFile` and `W10Preflight`. The same tracked entry has separate `w10-nk-live` and `w10-critics-live` routes. The referenced live executor/provider/W10 scripts are among the six untracked files and were not opened, hashed, changed, staged, or included in Git.

Tracked `tools/cnw_runner.py` exposes `legacy-source-preflight` and `legacy-recovery-plan`. The preflight requires an explicitly supplied project root, run ID, legacy source map, and source-map SHA. Its read-only validation checks the run's `run_state.json`, run contract snapshot, matching project contract, `project_identity.json`, frozen source and manifest, imported source identity, workflow template SHA, policy SHA, full 11-stage history, provider request/attempt records, and prospective identities. The recovery assessment preserves history, reports the cost ledger as `NOT_READ_RECONCILIATION_REQUIRED`, makes no provider call, and explicitly does not establish resume eligibility.

## `EXTERNAL_INPUT_NEEDED`

No actual private TS project or run was selected or opened. The following are required from the user/local owner before ATOM-07 can be re-reviewed against real state:

1. An explicit absolute DataHome path and the exact project root containing the selected TS project. Do not infer either from `workspace/cangqi`, old J19 paths, drive layout, or repository defaults.
2. The selected TS `run_id`, `runs/<run_id>/run_state.json`, its byte SHA-256, and read-only access to its stage statuses, `execution_failures`, provider request/attempt and raw-receipt identities.
3. The matching project contract path and SHA-256, the immutable run contract snapshot and SHA-256, `project_identity.json` and SHA-256, and the TS project ID/instance ID.
4. The exact frozen source-map path and SHA-256, original source/archive identity, source manifest path and SHA-256, and the source-map entries resolving both frozen source and manifest bytes. The corresponding source version/import/archive hashes must match the contract and run state.
5. The TS policy SHA recorded in its contract and the exact historical policy bytes it refers to; the frozen workflow-template SHA; plus the project-specific W10 preflight evidence and reviewer/evidence digest used by its real caller.
6. The six existing untracked W10 files and their SHA-256/byte sizes for read-only Controller review. They must remain unedited, undeleted, unstaged, and unpushed absent separate explicit authorization.
7. The real cost-ledger reconciliation for this run, including any `PENDING` or `UNKNOWN_NOT_ZERO` state and associated provider receipts. No migration or resume is authorized by providing these inputs alone.

Until these inputs are explicitly identified and independently checked:

```text
ATOM07=RETURN
CUTOVER_BLOCKED=true
PRIVATE_MIGRATION=NOT_RUN
```

This inventory does not assert that the real TS is at a particular path, that its state is recoverable, or that any private evidence was examined.
