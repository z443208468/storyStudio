# ATOM-04 execution-mode handoff evidence (WIP)

Date: 2026-10-13
Base: `357c956461fe9dded1be89a862f557a1ec4be7dc` / `423aa6545c7f689227a8c081a6ae3eb3ba419b73`

This is a working evidence note for the explicit package-job execution-mode change.
It does not sign off ATOM-04, authorize Provider calls, or represent a Live run.

## Change under review

- `-Offline` remains the source-acquisition/network policy.
- `-Mode offline|live` is now required alongside `-ExecuteJob` and is forwarded to
  `cnw_pack_app.execute_package_job`.
- Offline execution retains `SIMULATED`/`MOCK_ONLY` semantics.
- Live intent currently returns `LIVE_ROUTE_NOT_READY` and records zero Provider
  requests and zero fee reservations; it cannot silently fall back to offline.
- Exported resume instructions include the required explicit offline mode.

## Verification record

| Command | Result | Notes |
| --- | --- | --- |
| `python -m pytest tests/test_cnw_pack_app.py -q` | Exit 0; 12 passed in 77.26s | Includes missing-mode rejection and Live-intent/no-call regression cases. |
| `python -m pytest tests/test_cnw_pack_job.py -q` | Exit 1; 2 failed, 4 passed in 303.09s | First run found a regression: offline executor incorrectly conflated the requested mode with the pre-existing `execution.mode` field on repeat/resume. The regression was fixed by recording `requested_execution_mode` separately while preserving the old field semantics. |
| `python -m pytest tests/test_cnw_pack_job.py::PackageJobTests::test_changed_job_contract_and_export_are_rejected_and_old_bytes_retained tests/test_cnw_pack_job.py::PackageJobTests::test_formal_package_entry_automatically_executes_three_chains_export_and_resume -q` | Exit 0; 2 passed in 243.89s | Focused repeat/resume and retained-byte retest after the fix. |
| `python -m pytest tests/test_cnw_native_pack_job.py::NativePackageTests::test_prepare_preserves_actual_execution_failure_without_model_or_fee_calls -q` | Exit 0; 1 passed in 45.16s | Confirms preparation preserves a real recorded execution failure without Provider or fee calls. |
| `python -m pytest tests/test_cnw_native_pack_job.py::NativePackageTests::test_native_five_tasks_use_real_application_and_defer_original_continuation -q` | Interrupted; NOT VERIFIED | Produced no test result after more than 15 minutes; it was stopped to avoid an unbounded oversized suite. This is not a pass. |

The full package-app command and targeted package-job command completed after
the code fix. Test transport was simulated at the existing model boundary; no
production Provider call, key read, or fee reservation was made.

## Working-file SHA-256 before this evidence note was added

These hashes identify the exact tested source/test bytes before adding this note;
they are not Git blob IDs.

| SHA-256 | File |
| --- | --- |
| `32440d0198c67632416a8928921eb7bbc5514268db9038482c4cf26f77e5a836` | `tools/studio.ps1` |
| `f5d42c08364542cc3342bfb362ff89c1dd4ca465d373b91f2980c19aac348a6d` | `tools/cnw_pack_app.py` |
| `7ecde8077036b26251ec3d3eb9d186533949f90559285d77b5140a403e56adfa` | `tools/cnw_export.py` |
| `6545ffde2855744691eb5f122fc5b92b9d2e44298f9b8b9cfbd72640fa3ed69c` | `tests/test_cnw_pack_app.py` |
| `05ed093bcbd28e23f749dbb728092183aebad6c2100c8db35d0c379f049bf7db` | `tests/test_cnw_pack_job.py` |
| `079df433c7bcb960716d011255992094b8f72450ca319118341d9e71afe51a1d` | `tests/test_cnw_native_pack_job.py` |
| `3b85173b4180ca1d68f6441cb65c6ea9ed0a004dc7494dd6606c0191e880d3ee` | `docs/INPUT_PACK_ADAPTATION.md` |

## Remaining gates

This change only makes the execution intent explicit and fail-closed. It does
not implement the project-bound production authorization, trusted-review, fee
adapters, complete package-to-story consumer proof, or Live story acceptance.
Those remain required by the active R5 plan. Project-owner authorization for
the planned input-package paid acceptance is recorded in the active plan; it
does not authorize TS resume, migration, or cutover.
