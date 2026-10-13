# ATOM-05 project accounting work in progress

Base: `4efa7776f4636a4e2a4a92efdf0ba757a57dfd72`.
No new candidate acceptance or push is claimed by this note.

## Implemented work awaiting complete review

- Optional immutable accounting context on the existing reserve/settle
  primitives; a bound reservation cannot be settled without its same project,
  instance, Run, stage and frozen-input identity.
- New bound reservations retain the pricing and configuration identities used
  for admission. Settlement uses that reserved price, preserving unknown usage
  as `UNKNOWN_NOT_ZERO` and keeping the prior reservation charged.
- `tools/cost_guard.py` derives a Run account from real registration and the
  existing frozen-contract/source preflight. It creates no production grant,
  changes no global ledger/config selector and requires an existing shared
  account before a generic reservation.
- Runner main transport and the W10 Provider entry use the account adapter.
  The Provider entry joins the existing shared slot pool. Generic production
  authorization remains closed before slots/reservations.
- New accounting identity is included in V2 stage identity. Transport code also
  changed: historical execution identities are not claimed to be unchanged.
  No historical Run was executed, rewritten or re-signed.
- Generic NK/CritiCS routes check the existing production authorization before
  reaching their still-legacy auxiliary accounting paths. No new auxiliary
  production capability is accepted by this work.

## Actual validation and unresolved failure

The focused accounting tests passed (9 tests / 14 subtests), registered Run
adapter tests passed (3 tests), and a Runner/Provider/accounting invocation
passed (55 tests / 17 subtests).

An initial compatibility failure came from bypassing the legacy `load_config`
interface. Its raw reproduction is preserved in
`ATOM05_COST_CONTEXT_FAILURE_20261013.json`; legacy reservations now keep that
interface, while bound reservations use the new price snapshot.

The broader invocation initially failed collection because the historical
recovery test requires `tests` on PYTHONPATH. Its output is retained in
`ATOM05_COST_CONTEXT_REGRESSION_WIP_20261013.json`.

With the required module search path, the broader invocation produced **75
passed, 1 failed, 31 subtests passed**. The failure is Windows `WinError 5` at
the shared ledger `os.replace` in the parallel Provider/budget test. Raw bytes,
exit code and unchanged before/after source SHAs are preserved in
`ATOM05_COST_CONTEXT_REGRESSION_RETRY_WIP_20261013.json`. The terminal wrapper
failed to display non-GBK diagnostic text *after saving* that JSON; it does not
alter the subprocess result or its saved bytes.

Five isolated reproduction attempts all passed, recorded in
`ATOM05_COST_LEDGER_REPRO_WIP_20261013.json`. These do **not** resolve the failed
combined run. Root cause / durable failure handling remains under investigation.
The existing Controller was asked for read-only source diagnosis, not acceptance.

## Work still required before a candidate

- Resolve or precisely contain the atomic ledger publication failure with
  meaningful failure-preservation evidence; do not erase the failed run.
- Finish all applicable receipt/verify-live consumer bindings and test shared
  admission, Provider identity drift and cross-instance reuse.
- Reconcile affected execution identities and optional integration tests.
- Complete targeted raw evidence, form a normal local C/T, and obtain the
  independent Controller verdict before pushing.

No real Key, Provider request, real ledger, TS resume or migration was used.
`CUTOVER_BLOCKED=true`. Paid input-package acceptance remains authorized and
still requires the implementation gates to be completed.

## Shared ledger synchronization update

The writer lock is now shared with a read-only snapshot helper. RunAccount,
NK receipt binding, and offline reservation estimates use that helper. The
remaining verify-live reader and full contextual receipt routing still require
completion before an Atom candidate can be submitted.

Atomic publication freezes output bytes and checks both temporary bytes and
target preimage before each attempt. Only Windows error codes 5/32/33 receive
at most three replacement attempts; reserve, HTTP and settlement are not
replayed. Persistent refusal retains the original ledger and pending temporary
file and propagates failure. This is bounded robustness work, not proof of the
original intermittent WinError5 cause.

New deterministic tests cover transient refusal, persistent refusal, changed
preimage, changed temporary payload, and readonly synchronization. Focused
regression: 59 passed / 17 subtests. Combined accounting, Runner, Provider,
recovery, V2 preflight and pre-R5 role regression: 80 passed / 31 subtests,
exit 0. Raw command/output bytes and source hashes are saved in
`ATOM05_COST_LEDGER_LOCK_REGRESSION_20261013.json` and
`ATOM05_COST_LEDGER_COMBINED_20261013.json`. Prior failures remain retained.
No candidate, Controller acceptance, push or real Provider request occurred.

## Receipt-consumer follow-up

Runner verify-live now reads the configured shared account through the same
snapshot lock and rederives the actual Run account for each receipt. Bound
project/instance/Run/stage/input identities must match; a contextual charge
cannot be replayed into a legacy Run. W10 transport rederives its account in
the inner transport before reservation. NK binding validates accounting
ownership. NK over-budget and CritiCS ledger readers use synchronized snapshots.

The receipt consumer regression passed 62 tests / 22 subtests, exit 0;
`ATOM05_COST_CONSUMERS_20261013.json` retains command, raw bytes and source
hashes. Negative cases cover each context identity field at the actual helper
used by verify-live. Additional finite shared-budget and model-drift tests were
added afterward and are awaiting the next recorded result.

The original Controller is reviewing WIP gaps read-only. No exact candidate
acceptance is claimed. Optional/legacy/EARLY E2E regression is in progress.

The optional/legacy/EARLY E2E invocation completed: 39 passed / 20 subtests,
exit 0, source before/after unchanged. Raw evidence is
`ATOM05_COST_COMPAT_E2E_20261013.json`. It covers the two added shared finite
budget/model mismatch negatives. The EARLY E2E remains simulated, not Live.

## Publication failure at the actual transport entry

A new fictional Runner test calls the real cnw_live_call and accounting core
with atomic replace forced to fail. It proves one reserve invocation, three
bounded publish attempts, zero HTTP calls, zero settlement calls, no successful
receipt, no published ledger, and one retained temporary file. First invocation
failed because the test omitted the required role_id argument; raw failure is
retained in `ATOM05_PUBLISH_NO_SEND_20261013.json`. After fixing that test call,
`ATOM05_PUBLISH_NO_SEND_RETEST_20261013.json` records 1 passed, exit 0. This
strengthens failure containment evidence without claiming an intermittent OS
root cause or touching a real ledger.

## Controller-directed WIP corrections

The existing read-only Controller identified process-global stdout redirection
in W10 fee wrappers and two remaining unsynchronized CritiCS ledger readers.
The wrappers now consume primitive return dictionaries with emit=False.
CritiCS uses the shared snapshot reader and exact locked bytes for its evidence
copy. V2 cost code identity includes the raw snapshot helper.

A concurrent real-accounting wrapper test verifies separate request/settlement
results and unchanged sys.stdout; a raw-byte test verifies no ledger rewrite.
Accounting/Provider/W10/Runner regression passed 73 tests / 19 subtests, exit 0,
with unchanged source before/after in `ATOM05_ACCOUNT_WRAPPERS_20261013.json`.

Controller also confirmed that registered import/update/maintenance operation
accounting is still missing. Keeping production blocked is not ATOM05 full
completion. This adapter remains required in the current Atom, using real
operation snapshots and registration rather than manufacturing chapter
contracts or future receipts. Production authorization remains a separate
ATOM07 boundary. No candidate or push is authorized yet.

## Registered operation adapter first implementation

Import/update and maintenance now freeze their actual request and existing
input snapshots before the model boundary. The accounting adapter detects the
physical operation namespace before legacy routing; it binds registration,
DataHome, Run/schema, stage/role, request fingerprint, model/endpoint/cap/extra,
source snapshot hashes, workflow/constructor/transport identities and current
cost policy hashes. No chapter contract or future model classification is used.
Registered operation production authorization remains closed.

`ATOM05_OPERATION_COST_WIP_20261013.json` records 1 passed, exit 0: actual
import/update/audit over two registered fictional projects with simulated
transport and an isolated accounting ledger. It verifies original ownership
after publication, context settlement/receipt consumption, foreign replay,
role mismatch, schema relabel and mutated input rejection.
`ATOM05_OPERATION_FREEZE_WIP_20261013.json` records original operation gate
regression: 8 passed / 37 subtests, exit 0. Both source snapshots are unchanged.

The default active ledger reader in segment assembly now uses locked raw bytes;
explicit historical snapshot reads retain their old semantics. Its targeted
regression is still pending. Controller is reviewing the new operation WIP for
remaining exact identity/consumer/test gaps. No candidate acceptance or push.

## Segment-reader regression

The segment generation suite passed 22 tests. A new assertion compares default
active-ledger assembly (using the shared locked raw-byte helper) with explicit
historical-snapshot assembly, and verifies identical results and ledger bytes.
`ATOM05_SEGMENT_LEDGER_RETEST_20261013.json` preserves raw evidence. The first
collection failure due to the required tests PYTHONPATH is retained separately
in `ATOM05_SEGMENT_LEDGER_REGRESSION_20261013.json`.

Operation shared-account regression now additionally checks two registered
owners using the same finite account cap and same Provider slot pool, foreign
settlement rejection, and settlement of a previously reserved charge after
input mutation. This expanded invocation is pending at the time of this note.

## Additional operation review and bounded repairs

The expanded two-project budget/slot/foreign-settlement test passed (1 test,
51.75s), recorded in `ATOM05_OPERATION_SHARED_ACCOUNT_20261013.json`.
Controller then identified remaining method/template identity, cache consumption,
partial snapshot publication and namespace-case gaps. These are not signed off.

Snapshot publication now writes a unique temporary attempt and publishes the
complete file exclusively, preserving failed attempts and existing snapshots.
Canonical operation kind uses casefold. Tests of uppercase IMPORTS plus state
save failure recovery, and partial-write preservation/no overwrite passed;
raw evidence is `ATOM05_OPERATION_RECOVERY_WIP_20261013.json` and
`ATOM05_OPERATION_PARTIAL_WRITE_20261013.json`.

After those tests, current endpoint validation and frozen request fingerprint
recomputation were added following Controller feedback; their targeted tests
remain pending. Method/template dependency and cached-consumer closure also
remain pending. Earlier passing source hashes do not certify these later edits.
