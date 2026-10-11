# ATOM-07 METHOD FIDELITY DIFF — 2026-10-11

**Status:** Local Writer evidence for an Atom-07 candidate. Controller verdict
and candidate C/T are pending. This document is not an acceptance or a claim
that historical TS recovery eligibility has been established. The sole plan is
`plans/MASTER_PLAN_GENERIC_APP_R5.md`, SHA-256
`5CC22861CE3C0603D6EF89619594CD7CD68642241A20036032B031CB3A8C8ECF`.

## Scope and boundary

Atom-07 work here adds an offline v2 contract preflight and a read-only recovery
plan. Tests use registered synthetic projects under temporary directories. No
DataHome or existing project root was selected, so no private TS/J19 run state
was opened, copied, migrated, or changed. No production API, story generation,
run resume, reference refresh, or invalidation was invoked. `CUTOVER_BLOCKED`
remains in force.

The six protected W10 files remain untracked and were not read or staged:

- `tests/test_cnw_live_provider.py`
- `tools/cnw_live_executor.py`
- `tools/cnw_live_provider.py`
- `tools/cnw_w10_critics.py`
- `tools/cnw_w10_nk_live.ps1`
- `tools/cnw_w10_policy.py`

The tracked `tools/studio.ps1` dispatch was inspected only to locate the existing
preflight/Controller hand-off interface. The local W10 executor implementation
and its private TS evidence remain unverified.

## Mapped behavior

### 07.1 — Hard bindings

The reviewed tracked paths include `cnw_runner.produce`,
`cnw_runner.legacy_source_preflight`, `cnw_recovery.stage_identity`,
`cnw_recovery.execute_checked`, `cnw_recovery.refresh_references`, the v2 source
validator, and the explicit PowerShell dispatch references. The generic tracked
runner validates project instance, contract/source identities, selected
work-intent, frozen policy, support settings, and source freeze before creating
a run; generic live v2 execution remains closed pending authorization.

The existing v1 legacy source preflight continues to require a pinned path map,
exact original contract/source/policy/method identities, and an empty 11-stage
history. It rejects stage failure history without deleting or rewriting it.
No historical TS run was used to claim eligibility.

### 07.2 — Three separate identities

`tools/cnw_project.py:build_contract_preflight` adds a read-only
`contract-preflight` command for one explicitly selected v2 project, contract,
and future run ID. It verifies registered project instance, contract hash,
work-intent, source identity, current application policy, source/context files,
and constructs the real Plot messages offline. The report binds project
instance/project/work/run IDs, contract SHA, intent, immutable source identity,
source-root identity, selected anchor/span/context SHA, policy SHA, Plot-message
SHA, reviewer implementation identity, and a deterministic evidence digest.
An existing run ID is rejected; no run directory or preflight artifact is
created. Its status `READY_FOR_LIVE_PRODUCTION` means only offline contract and
Plot-request preflight. It separately states `provider_call=none`,
`live_evidence_status=NOT_RUN`, and `user_creative_acceptance=PENDING_USER_READING`.

`verify_contract_preflight` recomputes the digest and full current binding.
Synthetic tests show that evidence cannot be reused across project instances,
contracts, source selections, run IDs, or work intents (including ADAPT versus
INSERT). The request consumer verifies the selected B source revision and its
actual excerpt hash after A was imported first.

### 07.3 — Recovery dry run

`cnw_recovery.plan_recovery` and the `recovery-plan` CLI inspect only an
explicitly selected v2 run and project. The read-only plan verifies run and
project contract bytes, the pinned stage set, source freeze, run artifact
hashes, successful provider raw/request receipts, current workflow/application
policy/provider-policy identity, and current stage identities.
It reports reusable, not-started, identity-review, and execution-history states
without calling `resume`, writing state, invalidating an artifact, or making a
provider call. Changed/missing stage identity requires explicit review; legacy
v1 runs are directed to the separately pinned legacy preflight path.

The synthetic recovery test first reports Plot as the next-stage candidate.
After adding one synthetic `execution_failures` record, the planner returns
`RECOVERY_BLOCKED_EXECUTION_HISTORY`; the exact `run_state.json` bytes remain
unchanged. This demonstrates preservation only for the synthetic fixture. The
real TS run's failure records, raw hashes, old contract/source/policy, and
prospective Plot stage identity still require a user-selected project root and
independent Controller review.

## Reproducible evidence

The exact safe test command, raw stdout/stderr bytes and hashes, tested source
hashes, and synthetic evidence trace are archived in
`evidence/ATOM07_RAW_EXECUTION_EVIDENCE_20261011.json`. It records exit `0`,
`66 passed, 10 subtests passed`, stdout SHA-256
`0b5c37508ba18a533b8c0113c50d03ab09e3a7e5086576d7c44f4a56345a8223`, and trace
SHA-256 `dbbf6b341faf0701085176e8a7117aabb29054a8cfd85de7e70aac3a23d24caf`.
The trace is `SYNTHETIC_OFFLINE_ONLY` and contains identity/hash summaries, not
source prose.

The executed test set was:

```text
tests/test_cnw_work_intent_v2.py
tests/test_legacy_source_path_map.py
tests/test_cnw_project_import.py
tests/test_cnw_contract.py
tests/test_cnw_runner.py
```

It does not include `tests/test_cnw_recovery.py`, whose module setup reads an
existing private project. No test read project data outside a self-contained
temporary fixture.

**Controller:** pending review of the exact local candidate C/T. This document
does not claim Atom-07 acceptance or authorize push. The actual protected W10
executor audit and real TS evidence reconciliation remain open; no cutover,
TS resume eligibility, or overall application completion is claimed.

## Atom-07 RETURN repair — 2026-10-12

Added `legacy-recovery-plan` as a separate, read-only v1 assessment route. It
reuses the explicit project/run/source-map bindings and validates the legacy
contract, source freeze, workflow template, and production policy before
summarizing the 11-stage history. It reports failure-history hashes/counts,
computes the next-stage identity offline when available, and reports
provider-receipt status counts plus a canonical
digest. It labels receipts `PRESERVED_UNVERIFIED` and the cost ledger
`NOT_READ_RECONCILIATION_REQUIRED`; it never claims resume eligibility when
history or receipts exist. It hashes the run-state bytes before/after and
returns `V5_RECOVERY_REVIEW_REQUIRED`, without calling resume, a provider, or
the private ledger. The existing stricter `legacy-source-preflight` behavior
is preserved.

The self-contained legacy path-map fixture covers a synthetic
`EXECUTION_INCOMPLETE` Plot stage with an `UNKNOWN_NOT_ZERO` receipt, verifies
that the same stage is proposed, and checks exact run/contract bytes remain
unchanged. It also verifies the existing empty-history preflight still rejects
that run. This does not reconcile the actual TS run, validate actual receipt
payloads against the private cost ledger, or establish
`V5_RESUME_PREFLIGHT_ELIGIBLE_WITHOUT_NETWORK`. No private root was selected or
accessed; `CUTOVER_BLOCKED` remains in force. Exact run output and tested source
hashes are recorded in `ATOM07_LEGACY_RECOVERY_RETEST_20261012.md` and its
adjacent raw-output file.
