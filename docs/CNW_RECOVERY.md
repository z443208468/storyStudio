# CNW Run Recovery

Recovery operates on one explicitly selected project and Run. It does not choose a project, DataHome, contract, or source for the user.

## Inspect before resuming

```powershell
$ProjectRoot = (Resolve-Path -LiteralPath '<ABSOLUTE_PROJECT_ROOT>').Path
$RunId = '<EXISTING_RUN_ID>'
pwsh -NoLogo -NoProfile -NonInteractive -File tools/studio.ps1 show-run -ProjectRoot $ProjectRoot -RunId $RunId
pwsh -NoLogo -NoProfile -NonInteractive -File tools/studio.ps1 verify-history -ProjectRoot $ProjectRoot -RunId $RunId
```

Confirm the Run, contract snapshot, source/manifest revisions, workflow and policy identities, stage outputs, and retained failure/receipt history before requesting any continuation. `verify-history` is read-only. A failure, missing identity, changed source, or unresolved receipt must stay visible; do not edit `run_state.json`, replace a historical contract, recreate source bytes, or clear a cost record to make recovery pass.

## Resume gate

Resume only after the selected Run has a reviewed recovery plan and its required execution identity and authorization are available. V1 and legacy Runs keep their original identity semantics and may require a restricted external identity map; never write a synthetic native identity into an old project. An offline identity report is not a Controller receipt or Provider permission. Live continuation separately requires the trusted per-Run Controller attestation, explicit user Live authorization, valid credentials, and the applicable cost policy.

When those gates are satisfied, use the same explicit project and Run:

```powershell
pwsh -NoLogo -NoProfile -NonInteractive -File tools/studio.ps1 resume -ProjectRoot $ProjectRoot -RunId $RunId
```

If authorization or identity is pending, stop after the read-only review. Offline simulations belong in isolated synthetic projects with a temporary DataHome; their receipts cannot be treated as Live.

## Reopen changed references

Use `refresh-references` only when an authorized change to a consumed reference is intentional and its propagation plan has been reviewed. It records the old and new identities and reopens affected consumers; it does not re-freeze changed source, replace a contract, or authorize canon decisions. Preserve prior artifacts, requests, receipts, failures, and cost rows. Exact matching requests may be reused only after their actual inputs and output bytes have been verified.
