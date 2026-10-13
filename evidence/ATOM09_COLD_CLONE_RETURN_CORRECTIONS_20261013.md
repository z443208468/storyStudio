# ATOM-09 cold-clone RETURN corrections — 2026-10-13

This records corrections and bounded diagnostics, not an ACCEPT or push grant.
The previous candidate remains in history:

- Commit: `04623b50fbea4fa9e0da7398269d87799767751e`
- Tree: `217374009bd4e4a64306132b0448b8e110d6d113`
- Its full-suite exit code was 1: 3 failed, 403 passed, 232 subtests passed.
- Original full-suite raw SHA256:
  `10c3d75f1bc416eab2004eb456d7d47662956e017a59ceedf460ef669683b9f5`.
- Controller: `RETURN / NO_PUSH`. The original verdict is not changed.

## Three original failures and corrections

| Test | Cause | Correction; retained oracle |
|---|---|---|
| `test_cached_source_transfer_is_pinned_and_offline_reuses_without_transport` | The external offline guard rejected the test's local fictional Git fetch as a network fetch. | Replace only the network transfer with a fixed-commit local transfer. Normalize actual paths, disable inherited Git configuration, hooks, recursion and lazy fetch; enable only file protocol. Retain exact source acquisition, one-transfer, offline reuse and mismatched-cache rejection assertions. |
| `test_semantic_import_accepts_registered_datahome_root` | A hand-made directory plus a mocked identity did not satisfy the real operation registration check. | Use real `setup_data_home` and `create_project`; observe the actual identity function with `wraps`. Keep the existing import-boundary substitute and `FIXTURE_IMPORT` assertion. |
| `test_maintenance_and_fixture_sprint_accept_only_resolved_generic_identity` | The old fixture supplied an identity without a registered, private instance. | Create a real temporary instance and observe actual identity resolution. Retain `MAINTENANCE_OPERATION_INVALID` and `SPRINT_ID_INVALID` assertions. |

No production source or Provider authorization gate is changed by these fixes.
No model simulation session is added to the route tests.

The three original tests plus the first finite guard negative group passed:
11 passed, 25 subtests passed, exit 0. Raw SHA256:
`e4eecbbcfff4dba58450a15f76851ac68347734523f2a73ee93d8a15546bf36e`.

## External verification guard

The guard is outside Git and is never imported by the production application.
Its local-transfer permission is bound to an active, test-owned
`TemporaryDirectory`, the exact physical source/destination paths, the fixed
commit, argv and a minimal system-variable environment. It rechecks repository
configuration and physical paths immediately before process creation.

The continuing Controller required two additional restrictions: reject a
`Popen(executable=...)` override or extra positional options, and enforce an
explicit environment whitelist. Both restrictions have pre-spawn negatives.

Final guard SHA256:
`a94ab14e096f1bcbd7d768e4c2dfb6cdfdc6869701482f2cc000e2bf1f942bd9`.
Final guard/cache-transfer/controlled-ledger-negative scope: 12 passed,
25 subtests passed, exit 0; source and guard unchanged during execution.
Raw SHA256:
`0ab271c1a9cc13fbca0f85028e16c2ba264460b68602c9082717853acc5f55c1`.

The final three-module command was:
`python -m pytest tests/test_cnw_pack_app.py tests/test_cnw_runner.py tests/test_studio_cli_routes.py -q`.
It passed 55 tests and 3 subtests, exit 0, in 58.93 seconds, with source and
final guard unchanged during the run. Raw SHA256:
`403e6f93499c1c4ebc37fe39380db4089c09baf18cb676f39bd049221c83b192`.
The preceding failed concurrency run remains part of the evidence history.

The guard is a process-level verification restriction, not an operating-system
firewall or a proof that every possible child executable is disconnected.
Production-code simulation boundaries retain their separately checked rules.

## Additional concurrency diagnostic — not silently discarded

A subsequent three-module/guard run had 62 passed, 28 subtests passed and one
new failure. The original three failures were absent. The new failure was
`test_parallel_transport_keeps_all_receipts_and_shared_budget`: Windows
`WinError 5` during `p2_cost_guard.locked_ledger()`'s `os.replace` in settlement
of a fictional, temporary ledger. Raw SHA256:
`62ddd9a9f5c88ccfba66a531939086345a9b034dfaac8de46e4d377af98c7669`.

A single isolated execution passed (raw SHA256
`7148718990d7ea797310a566f73839afc086a66a233d8b87a51420dbd3998814`).
This does not establish the cause or erase the failure.

One instrumented execution of the original concurrency oracle also passed:
10 real ledger replacements, no overlapping observed ledger-lock holders.
Raw SHA256:
`9459a7d273f5dc2761dee270a3ace79b1c9eccb1111157c448cdbd69b14743f3`.
The bounded observation does not prove absence of every timing failure.

The continuing Controller permitted one controlled replace-failure negative.
It confirms that a denied settlement write propagates its error, retains the
original ledger bytes and PENDING reservation, keeps the failed temporary
attempt, and releases the lock for a later read-only acquisition. It neither
retries the Provider request nor changes the old production ledger code.
All data for this negative is newly created fiction in a temporary directory.

The first correction diagnostic also exposed inherited authentication fields
in pytest's local-variable traceback. That raw file is retained outside the
repository with a verified independent private file ACL; it must not be
published. Subsequent verification removes credential environment variables,
and the local Git transfer uses a minimal system environment. Public evidence
contains only result summaries and hashes, never the diagnostic contents.

## Protected originals and remaining gates

After these corrections, hash-only checks confirmed unchanged TS state,
run contract, real global ledger and original user ZIP. The frozen pre-R5
reference remains clean at the original exact Commit/Tree.

The already recorded native five-task chain and method evidence remain
components subject to independent review; they do not replace final cold-clone
verification of a new precise candidate.

`ATOM09=RETURN_PENDING_NEW_CANDIDATE_REVIEW`

`GENERIC_LIVE_PRODUCTION=NOT_RUN`

`CUTOVER_BLOCKED=true`

No production grant adapter, live request, fee reservation, TS resume,
private migration, history rewrite or push is authorized by this report.
