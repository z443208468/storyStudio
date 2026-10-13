# ATOM-07 registered operation authorization: WIP evidence

This is a bounded current-Atom engineering record, not ATOM-07 ACCEPT, Live
authorization, a story-delivery result, or permission to start ATOM-08.

## Base and scope

- Parent accepted ATOM-06: Commit `84e022de0fee6eb7d7eec4c248703621129491e1`, Tree `40399e2b5832798522ec6fa1945cd6605c75c32f`.
- Current changes remain an uncommitted `main` working candidate. No current
  ATOM-07 candidate C/T exists at the time of this record.
- The existing registered import/update/audit/handoff and revision_apply
  constructors now publish unsigned, immutable authorization requests without
  making a Provider call or publishing model output. A detached independent
  Controller signature and distinct Owner Live/fee signature are required for
  actual registered operation execution. The original shared account ledger
  lock, Provider slot and request/raw receipt consumers remain in use.
- A unique successful receipt matching the frozen operation fingerprint,
  stage, role, message bytes, original fee row, request file and raw response
  is required for postimage cache reuse. An unrelated success cannot skip the
  actual constructor/Run identity.
- The revision_apply low-level path reconsumes the actual selected author
  decision. A signed Owner fee grant does not authorize an unapproved creative
  revision.
- All HTTP responses in these tests are `MOCK_ONLY` / `SIMULATED`, injected
  only at the final transport boundary. The harness rejects network socket
  calls and strips inherited API keys. `real_provider_calls=0`.

## Original offline runs

Original raw output and before/after source hashes are under
`D:\CangqiStudio\StoryStudio_R5_Atom07_Current_20261013`. A row with exit 0
only covers the explicitly listed test version in its `.check.json`.

| Label | Result | Raw SHA256 |
|---|---|---|
| `operation_controller_three_gaps_v2` | exit 0; 3 passed, 2 subtests | `b57e90cf71e33221f8855fa4bf96b0fc43ae200dd57e1f889546e978dd661efe` |
| `operation_revision_signed_forgery` | exit 0; 1 passed, 4 subtests | `452d3af058437b3da75aa344d5232d92ec3558ff22ab68e09e66b69d93949145` |
| `operation_signed_full_final` | exit 0; 7 passed, 14 subtests | `3fe76b0a207ee3d7430e58f08c37ea2c3be1016bf151752597b22618d1d469a9` |
| `operation_legacy_full_final` | exit 0; 24 passed, 37 subtests | `090a1082c85f24a830de0190a21fb5ee65dd05bc36abf758d916b2ee1c928930` |
| `operation_early_e2e_regression` | exit 0; 2 passed, actual 11-stage simulated chain and NK unavailable rejection | `9df70718f89f51f5358e9e8ab66fc5bf33b085b8ae2f5fd43bd33b95617ae90c` |
| `operation_signed_chain_exact_bytes` | exit 0; real import/update/audit/handoff consumers, 1 passed | `6ef0b0972c38bdb73156909be6052c385bfd0a237a8192ee9c6ef1ecf2670dfa` |
| `operation_w10_scoped_final` | exit 0; four actual W10 entry and identity tests passed, 18 subtests; five other tests deselected | `63d3e7a7d6c23dea87b111402423f0364caa3a13631feca96e5c296d854a0b29` |

The last chain's `operation_signed_chain_exact_bytes.consumers.json` contains
four actual Run states, four simulated HTTP requests, their original mock
ledger rows and 54 run files. The separate
`operation_signed_chain_exact_bytes.byte_audit.json` recomputes SHA256 from
the captured original UTF-8 bytes; all 54 equal their stored file SHA.
Its source JSON reports `simulation_status=SIMULATED` and
`real_provider_calls=0`. An earlier chain capture used `Path.read_text()`
and normalized CRLF in 20 displayed text fields. Its raw evidence remains
unchanged; the exact-byte rerun above supersedes only that display defect.

The test fixtures cover interruption with pending pointer, transaction without
pointer, unchanged old outputs, same-Run recovery, UNKNOWN_NOT_ZERO budget,
and renewed signatures that do not reset spending. Two forged revision
subjects preserve the true approval file/SHA but alter approved_items or
revision_destinations, recompute the frozen Run and fee request, and carry
distinct test-only Controller/Owner signatures. High and low actual Runner
entries all reject before Provider slot, reservation, HTTP or protected file
change. The test keys are generated in temporary fictional directories and
are not production trust roots.

## Failures and boundaries retained

- `signed_operation_legacy_first`: 30 failures before the operation module
  source-path and missing-grant error fixes; raw result remains in the external
  evidence directory.
- `signed_operation_targeted_retest` and `signed_operation_legacy_retest`:
  explicitly terminated after preserving partial logs because Controller
  identified still-open code bypasses. Exit `4294967295`, not PASS.
- `operation_signed_remaining`: one test failed because its interruption mock
  replaced `_apply` and thereby changed the inspected implementation identity.
  The test now interrupts the original filesystem publication boundary;
  `operation_pending_recovery_no_faulthandler` passed (raw SHA
  `eba790aca949aff34eaba6446c3636f41da6daf471326f3de6500830342dcd8d`).
- `operation_pending_recovery_fixed`: Windows Python access violation while
  pytest faulthandler sampled a live subprocess; exit `3221225477`, not PASS.
  The same test passed without faulthandler in the run above.
- `operation_chapter_authorization_regression`: bounded stop after five
  completed passing tests while a sixth repeatedly invoked Windows ACL
  inspection; exit `4294967295`, not a full-suite PASS. The changed archived
  simulated-receipt case has a separate exit-0 result in
  `operation_controller_three_gaps_v2`, and the actual early 11-stage chain
  has its own exit-0 result.
- `operation_w10_affected`: bounded stop after four completed passing tests
  while the unscoped W10 suite continued through repeated Windows ACL
  inspection; exit `4294967295`, not a full-suite PASS. The same four selected
  tests completed in `operation_w10_scoped_final` with exit 0 and 18 passing
  subtests. Its five deselected cases have no claim of passing in that run.

Read-only protection check after these changes: the private TS original
`run_state.json` remains SHA256
`3bae0722506641f1c14840d2f2568f03484cd6b1298c972baf3700d0de42ee0d`;
the original shared fee ledger remains SHA256
`c8b0705f491ef824db01be0b7991f4db9db7d84e153c26481e93a4fdcd0eab9b`;
the frozen pre-R5 clone remains Commit
`26b72cea21dce45eede21cffddd4e75307d75652`, Tree
`535496ba3b8a331e12d0e5e161b15bf21a25393e`, clean.

The same independent read-only GPT-6.1 Sol Controller has checked the three
repair paths and the four signed revision-forgery subcases as WIP, found no
new concrete defect in that bounded range, and explicitly withheld ATOM-07
ACCEPT and push authorization. Its final candidate verdict remains pending.
