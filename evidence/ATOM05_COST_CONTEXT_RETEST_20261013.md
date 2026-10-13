# ATOM-05 cost-context retest addendum — 2026-10-13

This addendum supplements, and does not replace, `ATOM05_COST_CONTEXT_WIP_20261013.md`.
It records the current offline revalidation after the additional method/cache
identity work. It is not an Atom acceptance or push authorization.

## Base and scope

- Base commit: `4efa7776f4636a4e2a4a92efdf0ba757a57dfd72`
- Base tree: `66ef287d72a52cff00efac0d8d009ad3057b9e17`
- Scope: bind registered import/update/maintenance cost operations to project
  instance, Run, request, source snapshots, model/endpoint, shared cost policy,
  pinned method inputs, and the code that validates and consumes cached output.
- No real project, TS Run, shared production ledger, credential, network
  transport, or Provider was used.

## Added binding and cache checks

`tools/cost_guard.py` now freezes import method-template references and
maintenance method identity, project instruction bytes, and the actual
operation constructors, validation helpers, cache consumers, and publication
helpers. Registered cached operation recovery re-derives this identity and
checks the frozen account snapshot before it can reuse a receipt. Mock receipts
remain subject to the simulation-session verifier. Live receipts must match
the frozen request fingerprint and the shared ledger settlement/account.

The import and maintenance cache paths call this verifier before publishing a
recovered result. Historical legacy accounting and its ledger records are not
rewritten by these changes.

## Verification

- `ATOM05_COST_OPERATION_CONTROLLER_SCOPE_RETEST_20261013.json`: command
  `python -m pytest -q tests/test_cnw_operation_authorization.py
  tests/test_cost_operation_context.py tests/test_cost_context.py`; exit 0;
  **16 passed, 42 subtests**. Raw output SHA-256:
  `27451339d04eaf7290da8136cf17bfffc8e74694dbb52bfe04d5a78253426e83`.
- `ATOM05_FAILURE_AND_PROVIDER_RUN_INDEX_20261013.json`: with
  `PYTHONPATH=tests`, Runner, generation, cost-guard, and Provider regressions;
  exit 0; **86 passed, 17 subtests**. Raw output SHA-256:
  `45ef788f5c1ab6054b7c81862ff19994e589c78df39c924462fc77d790088036`.
- The first Runner/Provider invocation had a collection-only failure because
  `tests` was not on `PYTHONPATH`; its original output and exit code 2 remain
  recorded separately. The operation authorization suite also exposed a
  Windows default-code-page read in a test fixture; its original failure is
  retained, the fixture now explicitly reads UTF-8, and the current 16-test
  combined run passes.
- `git diff --check` and targeted `py_compile` completed with exit 0.

Specific offline negatives now reject changed import method templates, changed
maintenance templates or publication helpers, changed API endpoint, and a
mutated cost-operation snapshot before cached recovery. Restoring the exact
identity permits the already-recorded simulated response to recover without a
second model call.

## State and remaining review

- ATOM-05 code/test work is still local and uncommitted; it has no Controller
  verdict for an exact candidate C/T.
- The independent Controller's earlier `8e5f787` ATOM-09 limited offline
  acceptance remains historical and unchanged. Current ATOM-05 changes still
  need exact-candidate review; applicable package integration evidence must be
  assessed against the resulting candidate before any actual input-pack call.
- `CUTOVER_BLOCKED=true`; no TS resume, migration, or cutover was performed.
- Generic Live story generation remains `NOT_RUN` in this retest. Existing
  paid acceptance authorization does not bypass the exact-candidate review,
  trusted authorization, or cost-policy checks.
