# ATOM-04 execution-mode handoff evidence (WIP)

Date: 2026-10-13
Base: `357c956461fe9dded1be89a862f557a1ec4be7dc` / `423aa6545c7f689227a8c081a6ae3eb3ba419b73`

This is a working evidence note for the explicit package-job execution-mode change.
It does not sign off ATOM-04, authorize Provider calls, or represent a Live run.

## Change under review

- `-Offline` remains the source-acquisition/network policy.
- `-Mode offline|live` is now required alongside `-ExecuteJob` and is forwarded to
  `cnw_pack_app.execute_package_job`.
- Offline execution makes no Provider authorization grant. The normal CLI has
  no user-selectable mock-response switch; generic V2 Provider stages fail
  closed without a permitted test fixture transport. Tests replace only the
  existing final model boundary with a simulated transport and verify its
  receipts as `SIMULATED`/`MOCK_ONLY`.
- Live intent currently returns `LIVE_ROUTE_NOT_READY` and records zero Provider
  requests and zero fee reservations; it cannot silently fall back to offline.
- Exported resume instructions include the required explicit offline mode.

## Verification record

| Command | Result | Notes |
| --- | --- | --- |
| `python -m pytest tests/test_cnw_pack_app.py -q` | Exit 0; 12 passed in 99.14s | Includes missing-mode rejection and Live-intent/no-call regression cases. Raw merged output: `evidence/atom04_execution_mode_logs/pack_app_pytest.txt`; SHA-256 `AC717D64F7BEAF889D769DDA4C05150793BCC5A34D3BEC031020C08D23EE0F19`. |
| `python -m pytest tests/test_cnw_pack_job.py -q` (initial run) | Exit 1; 2 failed, 4 passed in 303.09s | Found a regression: offline executor conflated requested mode with pre-existing `execution.mode` on repeat/resume. Fixed by recording `requested_execution_mode` separately while preserving old field semantics. The original full terminal output was not persisted; this limitation is retained and not reconstructed. |
| `python -m pytest tests/test_cnw_pack_job.py -q` (after fix) | Exit 0; 6 passed in 331.83s | Covers package execution, retained artifacts and resume. Raw merged output: `evidence/atom04_execution_mode_logs/pack_job_postfix_full_pytest.txt`; SHA-256 `0B1C8911F53EBE849FBF3F94F510B970C1F2CA91BE51463CEF622A7A2C7FDA87`. |
| Focused package-job repeat/resume tests (initial post-fix run) | Exit 0; 2 passed in 243.89s | Retested retained bytes and formal multi-task resume. This earlier run's raw terminal output was not persisted; the post-fix full suite above reran these tests. |
| `python -m pytest tests/test_cnw_native_pack_job.py::NativePackageTests::test_prepare_preserves_actual_execution_failure_without_model_or_fee_calls -q` (captured rerun) | Exit 0; 1 passed in 102.08s | Confirms preparation preserves a real recorded execution failure without Provider or fee calls. Raw merged output: `evidence/atom04_execution_mode_logs/native_failure_preservation_pytest.txt`; SHA-256 `8492B445818C01F69EE7C80BA3E2F865EDADA2609B62FEB9953C1DC0DA7E1F6F`. |
| `python -m pytest tests/test_cnw_native_pack_job.py::NativePackageTests::test_native_five_tasks_use_real_application_and_defer_original_continuation -q` | Interrupted; NOT VERIFIED | Produced no test result after more than 15 minutes; it was stopped. No output was available to persist. This is not a pass. |

The full package-app command and targeted package-job command completed after
the code fix. Test transport was simulated at the existing model boundary; no
production Provider call, key read, or fee reservation was made.

## Source identity for captured reruns

The captured reruns used the executable and test file bytes committed in
`dcf24a7bfcaeefcdb79f30852058fe6986d20d4b`; docs/evidence corrections made
after that candidate did not change these executable/test files. These are
working-file SHA-256 values, not Git blob IDs.

| SHA-256 | File |
| --- | --- |
| `32440d0198c67632416a8928921eb7bbc5514268db9038482c4cf26f77e5a836` | `tools/studio.ps1` |
| `f5d42c08364542cc3342bfb362ff89c1dd4ca465d373b91f2980c19aac348a6d` | `tools/cnw_pack_app.py` |
| `7ecde8077036b26251ec3d3eb9d186533949f90559285d77b5140a403e56adfa` | `tools/cnw_export.py` |
| `6545ffde2855744691eb5f122fc5b92b9d2e44298f9b8b9cfbd72640fa3ed69c` | `tests/test_cnw_pack_app.py` |
| `05ed093bcbd28e23f749dbb728092183aebad6c2100c8db35d0c379f049bf7db` | `tests/test_cnw_pack_job.py` |
| `079df433c7bcb960716d011255992094b8f72450ca319118341d9e71afe51a1d` | `tests/test_cnw_native_pack_job.py` |
| `30d9d05f9e06a4443270456fcdd823d7fc129e41ba07e77b2ad603c3d68acc1f` | `docs/INPUT_PACK_ADAPTATION.md` (corrected after controller return; not part of captured test code) |

## Raw-record limitations

Captured output files contain merged pytest stdout/stderr. The wrapper's
`EXIT_CODE` line was printed separately by PowerShell and is recorded in the
table above; it is not part of each pytest output file. The initial two-failure
full-suite output and the first focused rerun output were not persisted at
execution time, so they are reported as historical results without invented
raw logs. The interrupted long native test emitted no output before stopping.

## Remaining gates

This change only makes the execution intent explicit and fail-closed. It does
not implement the project-bound production authorization, trusted-review, fee
adapters, complete package-to-story consumer proof, or Live story acceptance.
Those remain required by the active R5 plan. Project-owner authorization for
the planned input-package paid acceptance is recorded in the active plan; it
does not authorize TS resume, migration, or cutover.
