# ATOM-07 legacy recovery repair evidence — 2026-10-12

## Candidate under test

- Source candidate C: `7262978b273fa5c144ec30609dd766206aef66bd`
- Source candidate T: `a3f2d64d15248adece6a36785139d676653a1443`
- Parent: `3f97803e335e182d0d8ec7006a1144802d3722c7`
- Branch: `main`
- The final review candidate will include this evidence record and method mapping as a following evidence-only commit.

## Verification

- `python -m py_compile tools/cnw_runner.py tests/test_legacy_source_path_map.py` — exit 0, stdout/stderr empty.
- `python -m unittest discover -s tests -p test_legacy_source_path_map.py` — exit 0, 7 tests passed in 22.463s.
- Captured test output: `ATOM07_LEGACY_RECOVERY_RETEST_20261012.raw.txt`
- Captured output SHA-256: `fa04f9fe7425cf785b4e06a463cbc365ec152b7a3af4cc8320105666cfffb106`
- `tools/cnw_runner.py` SHA-256: `d9614c583286c37b6ae931c7f5ab0f70cd32ca5364a10a3bef2e34858c75a581`
- `tests/test_legacy_source_path_map.py` SHA-256: `dafd7fbfb2f3f3fb27cce77342756ceaaff54b43154a9e7c12199572081cffdf`
- `git diff --check` — exit 0.

## Scope and limits

The test uses only a self-contained synthetic project, source map, legacy v1
contract, stage state, and receipt. It verifies that a failed Plot stage is
identified as the next-stage candidate and its identity is computed offline,
execution failure history and receipt identity are summarized, old bytes remain
unchanged, the legacy preflight does not call the run eligible, no provider is
called, and no resume occurs. The cost ledger is deliberately not opened. The
result does not reconcile the actual TS receipts, private ledger, exact legacy
W10 call chain, or establish resume eligibility. `CUTOVER_BLOCKED` remains in
force. Provider request delta: 0.
