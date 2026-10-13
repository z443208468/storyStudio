# ATOM-05 current closure candidate: actual component effects

Base C=`049b0d26bd4bc6c2c4c1b5662782a4c8b34a8dcb`, T=`0554196d3ea6341184b77b5416807bf3a125573f`.
Active R5 SHA256=`59459D839780C8B5D729AF81F3805CBFA63E6582F283EC7D725D48C36FDBFF3D`.
Writer evidence only; full current ATOM-05 verdict awaits independent exact-C/T review.

## Scope and actual effects

This candidate addresses the two roots in the Controller's current ATOM-05
RETURN for `137e22c`. It does not start ATOM-06, migrate private data, resume TS,
deploy production authorization, or claim the actual input-package story gate.

| Returned root | Production change | Observed effect in fictional fixtures |
|---|---|---|
| Manuscript replaced before independent index publication; accepted retry then conflicts | Durable preparation files and a journal are published as one transaction directory; subsequent manuscript/index publication revalidates preimages and resumes the same accepted transaction | Preparation interruption preserves the old manuscript; interruption after body publication recovers the missing index; an unrelated index edit rejects without overwriting it; the identical accepted transaction is idempotent; archived old body remains byte-identical |
| NK/CritiCS directly use global accounting without registered ownership/common slots | Derive the actual RunAccount; use the existing shared ledger and slot; preserve native hook/parent identity and verify native results through the same accounting receipt verifier | Two real registered fictional instances share one synthetic account; each component generates a SETTLED and an UNKNOWN_NOT_ZERO row under the correct instance/Run/stage; both use the common slot; failure retains its nonzero reservation; result readback verifies hashes and rejects a foreign parent |

NK retains its historical `support_hook` receipt stage and derives the matching
cost context. Registered NK uses its settled charge rather than calling methods
not provided by RunAccount. Legacy pricing calculation remains the original
path. Native CritiCS stores the full child Run path before result validation,
including NATIVE_RESULT_PENDING, so a later readback can locate that same result.
The package import path uses one accounting module; direct-script mode keeps its
fallback imports. Registered native CLI requests require a parent/hook and the
existing real authorization check before key/slot/reservation/transport.

The successful native CritiCS cost-component fixture uses the pinned applyQA
template and one plan-revise exchange. This is not a claim that all optional
CritiCS method actions have now completed new live acceptance. CNW role prompts,
the eleven-stage DAG, Lens/Verifier duties, voting threshold, Canon approval and
Sprint thresholds were not edited. NK/CritiCS remain optional support.

## Verification and provenance

External original execution directory:
`D:/CangqiStudio/StoryStudio_R5_Atom05_Close_20261013`.

Public fictional-only raw records and hashes:
`evidence/atom05_closure_20261013/` and
`evidence/ATOM05_CLOSURE_MANIFEST_20261013.json`.
The evidence directory is exempt from EOL normalization so original record SHA
matches Git bytes. Production source remains governed by the existing LF rule;
working-file SHA and Git blob identity are distinct and compared accordingly.

| Record | Result and scope |
|---|---|
| `first_roots` | Exit 1: 3 passed, 1 failed. Broad Node/Popen substitutes accidentally intercepted real Windows ACL inspection. Original failure is retained. |
| `nk_real_account_retest` | Exit 0: 1 passed. Substitutes now intercept only the Node launch, leaving actual registration/ACL checks intact. No authorization helper is mocked to admit a generic production request. |
| `current_scope` | Exit 0: 133 passed, 66 subtests. Eleven affected modules cover generation, roles, adapters, accounting, operations, legacy role compatibility, Runner and Recovery. Three production files match final bytes; the subsequent reader guard is covered below. |
| `final_effect_capture` | Exit 0: 3 passed. After the broad run, only three recorder expressions were extended to retain actual artifact bytes. This covers those modified methods; the later native-reader guard is independently covered below. |
| `python311_final` | Exit 0: 4 unittest tests OK under the existing Python 3.11 runtime: the three actual component effects and real pre-R5 four-role request comparison. This precedes the final reader guard below. |
| `final_native_readback` | Exit 0: 16 passed. After identifying that absolute registered results could omit the parent argument, the reader now explicitly rejects that omission; both legacy adapters and registered native components were retested with final source bytes. |
| `python311_native_readback` | Exit 0: 1 unittest OK. Final reader positive/missing-parent/context-mismatch cases also pass on Python 3.11. Final source map matches the candidate. |

The wrapper removes Provider credentials from its child environment and installs
a socket audit denial for connect/sendto/getaddrinfo. Model/native transport is
deterministic and synthetic. Component tests use actual registration, contract
bindings, RunAccount, ledger primitives, file locks, settlement and readback;
their admitted lower components grant no CLI production permission. Actual
generic entry negatives keep authorization intact and prove no additional
native/fee activity. No real Provider request occurred.

`final_effect_capture.effects.json` preserves thirteen nonempty actual artifact
byte snapshots, their SHA256 and parsed effect records. Promotion includes body,
index, archived preimage and COMMITTED journal. NK includes native request/raw
response plus its marked MOCK_ONLY receipt and actual synthetic ledger rows.
CritiCS includes input, critique, output, marked MOCK_ONLY native receipt, calls,
scoped ledger and failed-call evidence. `effect_artifact_readback.json` records
byte/hash agreement, journal/body/index consistency and native input/output/
parent-cost binding. The existing fixture recorder's legacy Atom07 schema name
does not grant Atom07 execution or acceptance scope.

## Method and history boundaries

- M03/M10/M12: same-Run candidate ownership and prior Runner/Recovery regressions
  remain covered; actual promotion recovery adds no creative/Canon authority.
- M14: only ownership/accounting/native readback interfaces change; original
  support duties and method templates remain intact.
- M16: mock evidence is explicitly scoped; normal registered production remains
  denied. Lower-component success cannot pass the final actual-story gate.
- The real shared ledger remains SHA256
  `c8b0705f491ef824db01be0b7991f4db9db7d84e153c26481e93a4fdcd0eab9b`.
  The real TS state remains
  `3bae0722506641f1c14840d2f2568f03484cd6b1298c972baf3700d0de42ee0d`.
  Neither was rewritten; UNKNOWN history was not cleared.
- The pre-R5 clone remains clean at `26b72cea` / `535496ba`; fixed CNW remains
  `97ad71fe`. The protected untracked slot lock remains the original empty bytes.
  Previous failures and RETURNs remain unchanged.

`CURRENT_ATOM=ATOM05`

`CURRENT_ATOM_CLOSURE_VERDICT=AWAITING_INDEPENDENT_EXACT_CANDIDATE_REVIEW`

`NEXT_ATOM_PERMISSION=DENIED_UNTIL_FULL_CURRENT_GATE_ACCEPT`

`INPUT_PACK_TO_STORY_GATE=RETURN/NOT_RUN`

`GENERIC_LIVE_PRODUCTION=NOT_RUN`

`CUTOVER_BLOCKED=true; PRIVATE_MIGRATION=NOT_RUN; TS_RESUME=NOT_RUN`
