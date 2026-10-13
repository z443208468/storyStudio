# ATOM07 current authorization work — WIP, not acceptance

Base and independently accepted remote: C `84e022de0fee6eb7d7eec4c248703621129491e1`,
T `40399e2b5832798522ec6fa1945cd6605c75c32f`.
ATOM06 normal push completed with exit 0; fetch, ls-remote and origin/main Tree
matched the exact accepted C/T. Its freeze and original verdict are retained.
This ATOM07 work has no candidate commit, no ACCEPT and no push permission.

## Current component and actual effects

- Shared real pre-run/existing-Run bindings let independent authorities review a
  request before Run creation. No future Cards/prose receipts are required.
- Controller preflight keeps `provider_call_authorized=false`. A distinct
  deployment-owned Owner verifier checks a separate Live/fee grant, including
  Provider/model/endpoint, fee/pricing policy, code/plan identity, lifetime,
  finite Run budget, request/token limits and stage/role scope.
- The application automatically publishes an unsigned request; its existence
  never grants production. Request publication reuses the accepted immutable
  temporary-write/exclusive-publication helper and retains failed attempts.
- V2 Runner creation, high/low request boundaries and W10 V2 preflight consume
  the grant. Actual Plot messages are recomputed from the selected source and
  legal role materials. Wrong messages, roles and caps are rejected before HTTP.
- Reservations enforce cumulative instance/Run spending and attempts inside the
  original shared ledger lock. Re-signing cannot reset spending. After-reserve
  rejection records NOT_SENT and preserves conservative UNKNOWN_NOT_ZERO under
  the original accounting context; it does not resend or clear historical fees.
- A real checked Plot uses selected B and excludes unselected A. Its request,
  raw response and nonempty stage artifact were captured and byte-hash checked;
  same-identity execution reused the artifact without another request.
- HTTP fixtures explicitly mark their raw responses SIMULATED. Real receipt
  persistence records MOCK_ONLY/fixture_only=true. Real verify-live rejects them;
  relabeling their receipt to Live is rejected by the raw-response consumer.

The test trust verifier is a temporary cryptographic MAC fixture. It is not a
deployed production signing authority. No credentials were read and no real
Provider request or real-account reservation was made.

## Original results and source scope

External original directory: `D:\CangqiStudio\StoryStudio_R5_Atom07_Current_20261013`.
Public raw/check/fictional-consumer copies and hashes are indexed in
`ATOM07_CURRENT_AUTHORIZATION_WIP_MANIFEST_20261013.json`.
Each run's check records its exact argv, terminal exit and the explicitly listed
source before/after hashes. Later source changes are not assigned to older runs.

| Label | Actual terminal result | Raw SHA256 |
|---|---|---|
| authorization_first | exit 1; 1 failed, 3 passed, 5 subtests | `50e643d417e119844dcdf43b2b3a472d4f020e03e940a9f7ddab03b62ba0bbb8` |
| authorization_plot_retest | exit 0; 1 passed | `087a0e48ec077139d6d459a4fe51cc231bbd675e5a4aebcc68c682272d393cb1` |
| authorization_simulated_retest | exit 0; 1 passed | `9de02f114d8e6e16c90dc24ee096a116283281940335964092e66db3a8f576d4` |
| authorization_scoped | exit 0; 29 passed, 40 subtests | `b9898bd3c31f39002731c45b92bbfadc83f3db2226e6ede43f4e17ccbbd63116` |
| authorization_bound_retest | exit 0; 4 passed | `cefdc6e7418f3b7dafe9b9eaa79998605bfe13e8f62681ccc9f3ce725d0b9044` |

The first failure was a new test passing a third argument to the actual
two-argument execute_checked API. The test now calls the real API without
replacing its executor; original failure output is retained.

The 29-test command covered authorization, original V2 preflight, registered
cost contexts and original P2 accounting regressions. It precedes the final
request-publication/code-binding/send-boundary repairs. The final four tests
cover those changed paths and the actual checked Plot on the final listed
source bytes; they are not a rerun of the entire 29-test command.

The W10 Provider source preimage was copied and hashed before editing, outside
Git: `cnw_live_provider.before.py.source`, SHA256
`6a645512c84a941b9f71308cd633957913ea8be0c1603ac555fc737dd1f875f7`.
Protected actual ledger and TS state byte hashes still match their frozen
anchors, including the existing unresolved cost history. Neither was executed
or rewritten. Old reference and historical verdicts are retained.

## Same independent Controller and remaining work

Controller remains `/root/goal_controller_61_restart_20261013` (GPT-6.1 Sol).
Its actual scope and WIP replies are preserved verbatim in
`ATOM07_CURRENT_SCOPE_CONTROLLER_20261013.md` (SHA `27bd03018727d2686b88de367e5ccaf6f083ce3e567b32b94b2f8b61761b082d`)
and `ATOM07_CURRENT_WIP_CONTROLLER_20261013.md`
(SHA `3e96ccfcaf1ac393b4b21b292f25ace4473e7772d177373970f34a23b3423da2`).
Actual session source records are outside Git. Neither message signs this WIP.

Remaining current-Atom gates include full non-Plot message/role/extra validation
through existing pure constructors and lawful continuation/refinement variants;
W10 high/low request consumers and old mapped paths; registered operation and
auxiliary consumers; necessary affected frozen-function regressions and recovery
identity plan; exact local candidate C/T and independent full current07 review.
Production trust deployment is still unverified. It is distinct from completing
the offline engineering interface and from actual input-package production.

```text
CURRENT_ATOM=07
ATOM07_CURRENT_CLOSURE=NOT_ACCEPTED
NEXT_ATOM_PERMISSION=WITHHELD
GIT_PUSH_AUTHORIZATION=NONE_FOR_CURRENT_WIP
GENERIC_LIVE_PRODUCTION=NOT_RUN
INPUT_PACK_TO_STORY_GATE=NOT_COMPLETED
TS_RESUME=NOT_RUN
PRIVATE_MIGRATION=NOT_RUN
CUTOVER_BLOCKED=true
```

No ATOM08/09 implementation or verification was started in this work.
