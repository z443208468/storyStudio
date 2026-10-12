# CNW five-episode Sprint

The public reference is `MintoTsukino/claude-novel-workflow` at
`97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`. StoryStudio preserves its five-unit
Sprint review and handoff rules. The public workflow is a method reference, not
the author's unpublished automation.

## Current support boundary

The Sprint commands have two different modes:

- `tools/cnw_sprint.py --mode fixture` is a test-only fixture runner. It requires
  pre-authored fixture outcomes and a `FICT_` project ID; it does not generate
  episode contents or call a Provider. Its artifacts must remain labeled
  `TEST_FIXTURE_ONLY`.
- `--mode live` dispatches to the production Sprint executor and runs each unit
  through the CNW runner. It requires valid project inputs and live evidence for
  every candidate. Generic `cnw_work_unit_v2` live execution currently stops at
  `LIVE_AUTHORIZATION_REQUIRED`; this page does not grant production or cost
  authorization.

A complete generic offline five-unit Sprint, including consumer-verified
carry-forward, pause behavior, recovery, and Arc/Handoff boundaries, remains an
ATOM-09 acceptance item. Fixture-mode results do not satisfy that gate. During
the R5 refactor, do not use this document as permission to run a production
Provider request.

## Method invariants

A Sprint contains exactly five distinct episode contracts from one project.
Each episode after the first must identify its immediate predecessor. The
method review applies the pinned public thresholds: average score at least 75,
zero P0 findings, and at most two P1 findings. Each Finding receives three
independent verifier votes; at least two `not_refuted` votes retain it. A
separate Completeness review checks omissions. Projects may add their own
rubric, but example-novel-specific thresholds must not become global defaults.

A successful review does not automatically accept the user's creative work,
start another Sprint, or promote simulated output into a production manuscript.
Previous handoff material must remain recoverable, and interrupted or changed
inputs require explicit identity validation before continuation.

## Project inputs

For a supported run, the project must provide five distinct episode contracts,
a project-specific rubric, and the prior-episode relationship required by the
contracts. Plan and contract paths are project-relative and must resolve inside
the selected project. The application must use an explicitly selected,
registered project context; this document does not supply a project path or
select a DataHome.

## Evidence and status

Tests that replace the Provider or pre-author fixture outcomes are simulated
evidence only. They cannot be reported as Live generation, cannot satisfy
`verify-live`, and cannot establish literary quality. Current five-unit generic
Sprint acceptance and Live operation remain unverified until their respective
R5 gates pass.
