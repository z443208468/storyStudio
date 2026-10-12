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

## Independent RETURN and same-Atom correction

The first local candidate `4ec76a98d4c38b00a434792b0e5fe3f3ec858ab3`, tree
`f99816e50da7a5aa108a96574cfd91ca467790d2`, received independent **RETURN / NO PUSH**.
The Controller response is preserved in
`evidence/ATOM03_CONTROLLER_RETURN_4ec76a9_20261013.md`. It is not rewritten as
an earlier ACCEPT. The following corrections remain within this Atom-03 repair:

1. Match the exact scene token, not a prefix followed by `\b`; recognize legal
   tab-separated H2 boundaries. Prefix/duplicate/empty cases are rejected.
2. `cnw_import_workflow._internal_inbox_metadata` excludes the complete
   `_INBOX/input_packs/` namespace. Actual adapted-project inventory contains
   only the genuine original. Archived binding/old PASS cannot confirm a story
   assertion, including through retained Canon ancestry.
3. Freeze archived inputs permanently; record initial active-copy checksums
   separately. Actual official Workflow04 prompt export appends its log without
   changing the Plot request or role identity. Canon changes still change the
   actual Plot role identity. Arc changes and archived-input edits still reject.
4. Compare every original work-order field in normalized drafts, then compare
   mapped contract requirements, locale/config, exact source blob/sections and
   adapter choices with the selected archive. Unauthorized POV, capacity, entry,
   knowledge, language and anchor edits reject before contract output. Ordinary
   surrounding-text trimming follows the existing builder; original bytes stay
   archived unchanged.

Final affected retest `atom03_controller_returns_retest_v3` ran all eleven new
input-pack tests plus the two existing actual Workflow01/02 registry/retained
source tests: exit **0**, **13 passed, 16 subtests passed**, 45.27 seconds.
The earlier three-project eleven-stage and legacy regressions remain applicable
outside these localized input/classification changes; no executor, role prompt,
stage identity or recovery gate implementation changed.

| Latest record | SHA256 |
|---|---|
| `atom03_controller_returns_retest_v3.raw.txt` | `ebb1864f1fbe3cff46e70e9ebfd713e266633a1f0e30da1c09607e2263e13fe4` |
| `atom03_controller_returns_retest_v3.check.json` | `e4f81e22e9adc7010f0013bab67ff78a82d7b54df5521edeef9a009056ef15bc` |
| `atom03_controller_returns_retest_v3.pack_requests.json` | `269ec1c22c8b7adf1fcbfb59ce69ab6da70958a19a8dbf898c32d93102134a87` |
| `python311_controller_returns_final.raw.txt` | `c282c808e22bb5034a8a33b8af53f0682aea1b4eee91b75a4d7993cee2512251` |

The final eleven package tests also ran on Python 3.11.15: exit **0**, **11 tests
OK**, 33.221 seconds, including direct CLI and Workflow01 negatives.

`tools/cnw_import_workflow.py` final worktree SHA256 is
`1a3fdb11bec6e75710fe3404a10050ba90d885490500179ce1810e703bbeb72c`.
The wrapper's four-file SHA table does not include this fifth production file;
its unchanged one-line namespace correction is separately identified here.

Both unsuccessful new-guard retests remain in the sidecar: v1 exit 1 (8 failed,
7 passed, 14 subtests) exposed the builder's established surrounding-text trim
and an invalid negative response with no recognized source; v2 exit 1 (1 failed,
12 passed, 16 subtests) used the wrong newly written Canon oracle. The existing
V2 preparation freeze does not include sourced-work Canon; Canon is a real Plot
message dependency checked by `stage_identity` and recovery. The new test now
checks that actual identity, without changing production gates. The independent
Controller read this code and accepted this oracle correction as appropriate;
it did not sign a future candidate. These tests claim actual role-identity
change, not an unperformed demonstration of old Plot artifact invalidation.

Protected originals were rechecked after the corrections and retain the SHA
values above. Full package-to-story, 4700 capacity and Live remain unaccepted.
