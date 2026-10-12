# ATOM08 safe documentation candidate — Writer evidence

Parent commit: `08b4fa44292809ce8553849945ee5a1eaf3236fa`.
Parent tree: `c484a92f117a12f30c35e9f31da628630ccdc900`.
This record is not a Controller ACCEPT or a push authorization.

## Scope

- README: bootstrap, explicit DataHome, existing package preparation, and the remaining package-job execution/export gap.
- CLI_COMMANDS: actual PrepareRuns/JobFile parser behavior and pending statuses.
- CNW_MAINTENANCE: explicit project paths, actual authorization boundary, and preserved Audit/Handoff consumer and recovery responsibilities.
- CNW_COST_ACCOUNTING: retain the historical campaign authorization and exact command; distinguish it from new-project authorization and the fixed legacy ledger interface.
- Publish the original ATOM07 Controller ACCEPT verbatim as `ATOM07_CONTROLLER_ACCEPT_08b4fa4_20261013.md`, SHA256 `a41dbb02db5840e60f6ba873040a86d99e25cde6488e5b9485e4057da73e7bd7`.

No production source, policy snapshot, configuration, prompt, test, private data or frozen baseline is changed. This is limited documentation cleanup, not private migration, full legacy separation, default cutover, or package-to-story acceptance.

## Original-byte preservation

Repository-external directory: `D:\CangqiStudio\StoryStudio_R5_Atom08_Docs_08b4fa4_20261013`.
`originals.manifest.json` records all four original paths, byte lengths, SHA256 and backup hashes. Readback verified each backup against the parent's Git blob, byte for byte.

| Document | Original bytes | Original/backup SHA256 |
|---|---:|---|
| README.md | 3433 | `67a794a4565878907c5bad6de75d57af24e88fdc567b23ce8325c5f2df3d9c93` |
| docs/CLI_COMMANDS.md | 7068 | `e3a45f1292e965714e22fe6f12cc6363bfc8b7a9abe9ca0e9b6505f756c17fef` |
| docs/CNW_MAINTENANCE.md | 2952 | `f983d3b0775a545455f909c8e4c50acface080b8ab122f603416f441b2c647c8` |
| docs/CNW_COST_ACCOUNTING.md | 1126 | `e8905b6a8e3a200cc101d8eebab7020b5c421e6a12648c72440afbea1e50657f` |

## Necessary verification

Command, with repository cwd:

```text
C:\Program Files\Python313\python.exe -m pytest tests/test_studio_cli_routes.py::StudioCliRouteTests::test_public_commands_match_registry tests/test_studio_cli_routes.py::StudioCliRouteTests::test_supported_routes_point_to_tracked_implementations -q
```

Exit: `0`; raw output: `2 passed in 7.11s`.
External raw: `atom08_docs_first.raw.txt`, SHA256 `e7403b2d518a88a4b23463d0df717a4401c16865e1c5c67c09d1403eec73d94d`.
External `atom08_docs_first.check.json` records command, exit, document/source hashes, unchanged source check, backup/Git-blob equality, local link targets and parameters matched to the actual PowerShell/Python parsers. The external commit link is marked `EXTERNAL_NOT_FETCHED`; Git remote readback is separate evidence.

No example maintenance/cost command was executed. No story-chain rerun, Provider request, fee reservation, TS resume, migration or cutover was performed for this documentation change. Historical RETURN verdicts remain unchanged.

## Remaining product and production gates

`INPUT_PACK_TO_STORY_GATE=RETURN`: automatic package-job CNW execution and export require ATOM09 work and independent acceptance.
`W10_ATTESTATION_PENDING`; TS Live is not authorized and recovery eligibility is not established.
`GENERIC_LIVE_PRODUCTION=NOT_RUN`; `CUTOVER_BLOCKED=true`.

ATOM08 candidate C/T and verdict must be recorded by the independent Controller after the local normal commit. This record makes no claim that the whole R5 plan is complete.
