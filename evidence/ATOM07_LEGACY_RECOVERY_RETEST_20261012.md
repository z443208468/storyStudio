# ATOM-07 legacy recovery repair evidence — 2026-10-12

## Candidate under test

- Source candidate C: `4c3b74f9aa641c3d18f5e8bbd1043266ddcf33cd`
- Source candidate T: `74fce9e66f2660a6c7e4beafbd2797daacd7f6e0`
- Parent: `7262978b273fa5c144ec30609dd766206aef66bd`
- Branch: `main`
- The final review candidate will include this record and method mapping as a following evidence-only commit.

## Verification

- `python -m py_compile tools/cnw_runner.py tests/test_legacy_source_path_map.py` — exit 0, stdout/stderr empty.
- `python -m unittest discover -s tests -p test_legacy_source_path_map.py` — exit 0, 8 tests passed in 30.030s.
- Captured test output: `ATOM07_LEGACY_RECOVERY_RETEST_20261012.raw.txt`
- Captured output SHA-256: `c80b8f8bfeab8d3aba4b22b17fb308572d5871d8d2318cae2890e2b0870e6814`
- `tools/cnw_runner.py` SHA-256: `03e45dae590e0a561eef6cc2ba3b4367ae25cb716d334e591114f722520c4eb2`
- `tests/test_legacy_source_path_map.py` SHA-256: `1f91ff0776f562eb63d4e58504390ba99ae3166781a88eb3114b331aefa9745a`
- `git diff --check` — exit 0.

## Scope and limits

The tests use only a self-contained synthetic project, source map, legacy v1
contract, stage state, and receipt. They verify that a failed Plot stage is
identified as the next-stage candidate and its identity is computed offline,
execution failure history and receipt identity are summarized, a synthetic
state change during source validation is rejected, old bytes otherwise remain
unchanged, and the legacy preflight does not call the failed run eligible. No
provider call or resume occurs. The cost ledger is deliberately not opened.
The result does not reconcile actual TS receipts, the private ledger, or the
exact legacy W10 call chain, and does not establish resume eligibility.
`CUTOVER_BLOCKED` remains in force. Provider request delta: 0.
