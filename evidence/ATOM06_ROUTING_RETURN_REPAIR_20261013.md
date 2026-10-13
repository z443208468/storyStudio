# ATOM-06 task-routing RETURN and bounded repair

The independent readonly Controller returned C
`310f21e42e72cd03b824512683b80329ea833048` / T
`063a7aa7f40e984f716b5f2cca19d0e860174b91`.
Its original verdict is `ATOM06_CONTROLLER_RETURN_310f21e_20261013.md`, extracted
from the actual session record at line3907, UTF-8 SHA256
`e160e04f509349b1f8714590d30579bd6e80eb95cbc719d6a071facca4b535ba`.
It remains RETURN / NO_PUSH; old00-05 ACCEPTs were not withdrawn.

## Proven root

The attempt validator checked original source maps and all material SHAs, but
trusted its own work-order/context/index locators and fifth-Lens/integration
choices. A different declared task's already-frozen JSON remained byte-valid.
Recomputing derived requirements, binding SHA and the actual constructed
contract could therefore close hashes around the wrong task material.

The first diagnostic retained two fixture mistakes: no declared context existed
to substitute, and setting an already-null context to null was not an attack.
The corrected oracle uses a real same-group requirements JSON as an illegal
added context and numeric zero as a distinct invalid locator. No rejection
expectation was removed. All original outputs are retained separately.

`native_routing_before_fixed_fixture` executed the real
`build_work_contract_v2` and binding validator. Seven hostile cases were
accepted: different task requirements, added context, zero context, cloned
original-index bytes at a different location, rewritten fifth duty, NK enabled
and CritiCS enabled. Actual forged contracts and their SHAs are recorded.
The run exited1 with seven failed subtests; it is not a functional PASS.
All materials belong to explicit temporary fictional projects; no Live call,
real Run execution or fee request was performed.

## Minimal source repair

Only `native.validate_binding` changes: it reconstructs the static index using
the existing `_task_index` with the verified original task declaration, project
group, package SHA and attempt. It compares canonical JSON values for all fixed
fields, including task/instance, locators, source aliases and adapter choices.
The existing file-set/SHA validation remains. Dynamic derived files and legal
controlled predecessor records retain their existing independent checks.

No new mapper, signer, authorization bypass, workflow or stage is introduced.
V1 binding execution remains on its existing path. The changed validation code
has a new native stage method fingerprint; historical identities are not
rewritten or described as unchanged.

## Revalidation scope

- Seven rehashed hostile choices must be rejected by the actual contract
  constructor before any Model Run, Provider or fee operation.
- Legitimate attempt-v2 preparation, original offline contracts/Runs, waiting
  predecessor and simulated-predecessor rejection must remain valid.
- Old native-v1 contracts must feed actual checked Plot/Cards/Brief/Prose
  consumers and reuse matching stages without additional simulated requests.
- Unchanged method/accounting components retain only their independently
  reviewed original scopes; full06 and frozen-function verdicts still require
  a new exact C/T from the same Controller.

## Recorded component results

`native_routing_repair`: exit0, 3 passed / 10 subtests. The real constructor
rejects all seven consistently rehashed choices; the legitimate attempt reaches
the actual closed Live gate and preserves old contracts/Runs. Waiting and
simulated-predecessor checks also retain their original behavior.

`native_old_v1_consumers_fixed2`: exit0, one case. Four actual checked roles
consume the selected frozen source and project materials, produce nonempty
hash-matching artifacts and reuse matching stages. The first two attempts had
fixture instrumentation/trace failures: MagicMock could not be inspected for
the real method fingerprint, then a Path was not JSON-serializable. Transparent
wrappers retain/delegate the original accounting functions, and trace-only Path
serialization preserves the request file bytes and hashes. All oracles remain.

The separate repair manifest binds original failures, corrected tests, actual
forged-contract evidence before repair, source bytes and current consumer
readback. Previously reviewed06 evidence retains its recorded source identity;
it does not pretend to have executed this new validator body.
`python311_routing`: the same real seven-case rejection oracle also passes on
the existing Python 3.11.15 interpreter, exit0 / one unittest case OK.

`ATOM06=RETURN_REPAIRED_PENDING_EXACT_REVIEW`

`NEXT_ATOM_PERMISSION=ATOM07_WITHHELD; GIT_PUSH_AUTHORIZATION=NO`

`GENERIC_LIVE_PRODUCTION=NOT_RUN; INPUT_PACK_TO_STORY_GATE=NOT_COMPLETED`

`CUTOVER_BLOCKED=true; PRIVATE_MIGRATION=NOT_RUN; TS_RESUME=NOT_RUN`
