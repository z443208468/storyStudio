# Atom-03 input-package and source-binding repair

Parent: `014241723366e866a8d385f31d9af8705e8d3afa`.
This is a return to existing Atom-03 roots identified by the user's new
independent Controller. It does not sign the package-to-story product gate.

## Code and behavior

- `tools/cnw_input_pack.py`: declared legacy V5 ZIP adapter; verifies complete
  manifest/file set, safe paths, hashes, scene index, flat configuration and
  exact pinned Git source. Installs only into a fresh registered instance under
  the shared project lock. No package script or historic instruction executes.
- `tools/cnw_project.py`: V2 full-span before/after anchors, named scenes,
  explicit source-work Arc and SHA, immutable input binding in new contracts.
- `tools/cnw_contract.py`: rejects overlapping V2 spans using before-end versus
  after-start; verifies explicit Arc and frozen private pack-material identity.
- `tests/test_cnw_input_pack.py`: self-contained three-trial input package, local
  fictional Git history and registered temporary DataHome. Actual source import,
  contract construction and Plot consumers are exercised without a Provider.
- `docs/INPUT_PACK_ADAPTATION.md`: API, provenance, interruption and remaining
  consumer/capacity/CLI gates.

Old contracts and original project records are not rewritten. New V2 contracts
without an explicit Arc or input-pack binding retain their applicable behavior.
Package original draft/packet/seed bytes are preserved, with original display ID
and new UUID separately recorded. Active material paths are explicit. Old review
PASS declarations and historic handoffs remain inactive input evidence.

## Verification records

Raw process stdout/stderr and request artifacts are outside the repository at
`D:\CangqiStudio\StoryStudio_R5_InputPack_20261013`.

Scoped regression command:

```text
python verify_atom03.py atom03_final_scoped_v2
  tests/test_cnw_input_pack.py
  tests/test_cnw_work_intent_v2.py
  tests/test_cnw_contract.py
  tests/test_cnw_project_import.py
  tests/test_cnw_pre_r5_role_compat.py
  tests/test_cnw_export.py
  tests/test_cnw_atom09_three_project_e2e.py::ThreeProjectOfflineE2E::test_two_source_projects_and_source_free_original_run_real_11_stage_consumers
```

The wrapper invokes Python 3.13 pytest with the listed targets and `-q`, removes
Provider keys from the child environment, records source SHA before/after, and
captures original process bytes. Exit **0**: **43 passed, 19 subtests passed**,
124.46 seconds. Sources were unchanged during execution.

The same new seven input-package tests also ran with the prepared **Python
3.11.15** runtime via `-m unittest tests.test_cnw_input_pack -v`. Exit **0**:
**7 tests OK**, 63.523 seconds. No dependency was installed for this check.

After that run, inspection found that the existing direct-script contract CLI
needed the new module's relative-import fallback. Only that import wrapper and
an additional CLI test were added; contract/source/role executor behavior was
unchanged. Final `atom03_direct_cli_final` executed all eight package tests on
the candidate code: exit **0**, **8 passed, 8 subtests passed**, 26.52 seconds.
The additional real `draft-contract` CLI test also passed under Python 3.11.15:
exit **0**, **1 test OK**, 1.850 seconds. The scoped regressions above remain
applicable to the unchanged code outside this import wrapper and test addition.

| Original record | SHA256 |
|---|---|
| `atom03_final_scoped_v2.raw.txt` | `87efd79d74284d23c3308b39651d954174f2e1ca4a7ce029cf454a2e12428135` |
| `atom03_final_scoped_v2.check.json` | `e6fd0d87533131aee1660421d4082015ef23cb4b076c7117512d0f9a81e94de0` |
| `atom03_final_scoped_v2.pack_requests.json` | `1a21e38ba0fd5b03924b64f8832cd451252c0b011f7f4dcd4994dca74b6e450e` |
| `atom03_final_scoped_v2.e2e.json` | `42f2ae7028727382dd952d6e418b25aa98405d3097a3032b0d5ddeea53b56e88` |
| `python311_inputpack.raw.txt` | `593fc358897d9ca2de78449b49c9dcd765cf138ea53df499fd47e6a09f76b039` |
| `atom03_direct_cli_final.raw.txt` | `322d14a7fea4f62337d91fbb04dd0acffabf2a0dc358644815c0a4a8157ea2c3` |
| `python311_direct_cli.raw.txt` | `087efe383bbb6173c2f2cdd4488ca5aa75a4b63ac05d92041e9b1f53dac7e1e7` |

Three pack-shaped fictional trials preserve all original work-order fields and
produce three distinct Plot requests with three independent instances. Actual
consumers read only their intended source sections (1/2, 3/4, 5/6), complete
section bodies, their selected Arc, Canon/Bible and entry/exit requirements. The
recorded wire excerpt SHA matches actual message text. The unselected Arc is
absent. The request artifacts include contracts, their input indexes and messages.

The inherited three-project E2E was rerun for this implementation: three
non-FICT projects, five Runs, all eleven actual stage executors, simulated
receipts, recovery without unnecessary request replay and actual export. This
is a regression check of that existing fictional chain; it does not assert that
the newly adapted pack has completed the entire production chain.

Negatives cover traversal, conflicting ZIP names, undeclared files, bad hashes,
wrong source blob, source/config ambiguity, mismatched writing bounds, existing
project refusal, legitimate-hash overlapping anchors, changed Arc/original draft,
cross-project replay, empty/duplicate scene headings and interrupted installation.
An interrupted new installation preserves its files and refuses overwrite.

The first direct tool regression reported an empty lock file left on rejection
of a nonempty target (1 failed, 33 passed, 18 subtests passed). The implementation
was corrected to check before locking and repeat inside the transaction. Those
original tool results are not represented as successful results. An archived
first final command had the wrong test class selector, exit 4 and no tests; its
raw/check records remain alongside the correctly selected final run.

## Real input inspection and remaining work

Read-only parsing of the user's actual ZIP verified **372 files**, including its
371 declared payload entries, and three declared scenes. Package SHA256:
`5d50fa4395512f74a32f6f8be04cdf98ae40da923a029eaf8ea8d49d5ed89196`.
No private package text is copied into Git or test fixtures.

The exact `2200 / 3100 / 4700` requirement is preserved in a same-shape fictional
negative; normal V2 contract validation still rejects 4700 with
`UNIT_CAPACITY_UNVALIDATED`. This repair does not lower the requirement or
silently claim a usable real production contract. Full knowledge/gameplay/time/
focus/medium field consumption is still pending the existing Atom-06 consumer
gate; frozen input bytes are evidence of preservation, not of consumption.
Atom-04 must connect this API to the formal app entry. Atom-07 must provide the
legal production authorization route. Atom-09 must validate the complete
package-shaped chain before product acceptance.

Protected originals were checked read-only: TS run_state remains
`3bae0722506641f1c14840d2f2568f03484cd6b1298c972baf3700d0de42ee0d`;
shared ledger remains
`c8b0705f491ef824db01be0b7991f4db9db7d84e153c26481e93a4fdcd0eab9b`.
Frozen pre-R5 reference remains clean at commit `26b72cea21dce45eede21cffddd4e75307d75652`,
tree `535496ba3b8a331e12d0e5e161b15bf21a25393e`.

`INPUT_PACK_TO_STORY_GATE=RETURN`; `GENERIC_LIVE_PRODUCTION=NOT_RUN`;
`CUTOVER_BLOCKED=true`; `PRIVATE_MIGRATION=NOT_RUN`.
Independent exact-candidate review and push authorization are still required.
