# ATOM-09 consumer repairs — Writer evidence, pending independent review

Base C=`67e7a76d2bf3d748dfb569e925a09c6a82a3828b`, T=`4b5211185c158ce073336c05db53ad3e76908de5`.
R5 remains the sole active plan, SHA256 `AE5A1959EEAB75AD6A8F41460C38BF9678284C1D51A8D63B25CE37F7CB4F5183`.
Fixed CNW source remains `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`.

The user's product requirement is a fixed CNW workflow consuming the selected project's material and writing requirements. This repair does not introduce a dynamic workflow engine or require a native ZIP importer. No private input package, production story, key, Provider request, or cost reservation was used in these tests.

## Roots and actual repairs

- The previous generic E2E had only a limited Harbor source-selection assertion. Its real Plot request now checks B's actual anchors/span and hashes; the actual Writing Brief request consumes the selected information through its same-Run Plot. The simulated role replies read their actual preceding material; Prose receives a Brief and explicitly listed relevant voices.
- Public Workflow 01→02 now has a registered-project consumer chain: a frozen new source revision supplies source-linked classifications, old source bytes and confirmed claims remain, a conflicting claim is withheld from Canon and recorded as `TODO_CONFIRM`.
- Actual Canon Audit consumes a generated candidate with a conflict; Handoff consumes that audit; Workflow 03 consumes the resulting Handoff and writes an unapproved revision plan. Canon and the original candidate stay unchanged.
- The previous Sprint implementation required legacy Live project copies and could not execute source-free V2 continuation contracts. The V2 original-episode coordinator now constructs each later contract from the preceding actual candidate's path/SHA, executes all eleven checked stages, exports each candidate and uses the existing batch review/three-verifier/Completeness criteria. It pauses before creating later Runs when a stage fails.
- Arc review can select explicitly hashed Sprint candidates without publishing them as manuscripts. Its selector refuses Canon files and mismatched candidate hashes. The historical Arc/draft route remains available.
- Completion replay verifies saved Run/contract/artifact/receipt/export/Sprint hashes and reuses the saved result. It does not regenerate completed chapters against newer runtime notes. Unchanged chapters use the existing `NO_CHANGED_TEXT` result rather than manufacturing a revision.
- Generic offline native transport refuses before entering the shared cost guard. The first blanket guard rejected two legacy mocked-transport regressions; the final guard applies to V2 and generic Sprint containers, preserving the V1 transport contract. The two failures and their successful retest remain in the raw archive.

## Necessary verification

The sibling local archive `StoryStudio_R5_Atom09_Repair_20261012_67e7a76` contains the exact command arrays, exit files, raw console bytes, test/source SHA256, embedded real simulated requests and generated file bytes. It is outside Git. The Controller must read these originals; this report is not an ACCEPT.

| Check | Observed result | Raw SHA256 |
|---|---|---|
| `final_atom09_consumers`: `test_cnw_atom09_three_project_e2e.py` + `test_cnw_atom09_review_negatives.py` | exit 0; 10 passed | `08cd4f80ff6e0028557c0d1150173f3fbee09c4091e4e9c05653b1ef5fea1420` |
| `affected_full_chain_retest`: E2E, legacy Sprint/pipeline, chapter/Arc, maintenance, recovery, pre-R5 role requests, export | exit 0; 57 passed, 4 subtests | `b5fae5154e59ce8f432fa158b43c3adaa13defd97a54127611d0bcb643d30de1` |
| `method_and_cli_regression`: method, review, runner, intent, project identity, policy, CLI, standard operations, incremental entry, early gate | 132 passed, 35 subtests; two guard regressions RETURNed | `6a2c2ea3b3228c5324fd2ffe7a43fcdee4bfc4ccba310f9cee30ba1b1d064daf` |
| `final_sprint_and_transport`: E2E plus the two exact legacy transport failures after guard repair | exit 0; 8 passed | `9c9b7883732205de6ed4a5eb0135b8865b418690825ea469e70e225b39ab53a7` |

The final consumer run records `source_unchanged_during_check=true`. Later source differences from older test runs must be assessed by affected function, not treated as blanket acceptance of HEAD. No broad test count substitutes for the following actual consumers.

## Method evidence map

| Scope | Actual evidence |
|---|---|
| M01–M05 | Three registered projects; INSERT, ADAPT, JSON and original EP001/EP002 run through real checked stage functions; actual role read keys, same-Run upstream artifacts and selected voices are checked; B source text and bytes reach Plot and then Brief through Plot. |
| M06 | Two different project rule files produce different outcomes through actual Lint 1/2 stages on identical generated prose; prose bytes and each rules-file hash are checked. |
| M07–M08 | Five actual independent Lens requests; actual verifier consumer matrices for 0/1/2/3 surviving votes; duplicate, missing and wrong Finding tickets stop execution. Existing method/role isolation tests remain applicable within their actual assertion scope. |
| M09–M10 | Completeness omission enters Refine and later Lens feedback; a zero-Finding chain makes no fake Verifier/Refine/Re-review calls; a newly broken Canon rule in Refine receives fresh Re-review and three counterchecks and remains `REVISION_REQUIRED` after the bounded passes. Original prose/Canon are preserved. |
| M11–M12 | Actual source classification/update, Audit→Handoff→revision-plan consumers; conflicts and unapproved plans do not become Canon or published prose. No simulated result is represented as creative acceptance. |
| M13 | Five distinct original chapters, all eleven stages each; chapter three interruption/resume preserves completed chapters and receipts; exact 5/75/0/2 batch criteria; low score, P0, P1 count and project Canon stop branches reject; underproduced prose pauses before the next Run; Arc/Handoff read generated candidates; finished replay and tamper rejection; readable per-Run exports; no automatic next Sprint or manuscript promotion. |
| M14–M16 | The same fixed CNW pipeline handles the different input intents; optional helpers remain disabled in the full generic chain; mock receipts remain `MOCK_ONLY`/`SIMULATED` and fail Live verification. Legacy transport and pre-R5 request regressions are preserved. |

## Protection and remaining boundaries

The real shared ledger SHA256 still equals the preceding TS reconciliation anchor: `C8B0705F491EF824DB01BE0B7991F4DB9DB7D84E153C26481E93A4FDCD0EAB9B`. The real TS run_state SHA256 still equals that anchor: `3BAE0722506641F1C14840D2F2568F03484CD6B1298C972BAF3700D0DE42EE0D`; its recorded Provider count remains zero. These were only hashed, not rewritten. The frozen pre-R5 checkout is clean and unchanged.

- `ATOM09=AWAITING_INDEPENDENT_REVIEW`; prior RETURNs are not rewritten.
- `ATOM07=OFFLINE_ENGINE_ACCEPT_LIMITED`; production attestation is pending, TS Live is unauthorized, recovery eligibility is not established.
- `GENERIC_LIVE_PRODUCTION=NOT_RUN`; the V2 Live authorization integration is still pending. This repair does not unblock it or claim a finished production application.
- `CUTOVER_BLOCKED=true`; `PRIVATE_MIGRATION=NOT_RUN`.
- This normal local candidate requires an independent exact C/T verdict before push. The earlier user-requested push of unaccepted ancestry remains a historical fact, not a retroactive Controller ACCEPT.
