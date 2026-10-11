# R5 Git governance anomaly and current boundary — 2026-10-12

## Immutable prior verdicts

- `evidence/ATOM07_CONTROLLER_RETURN_20261012.md` records the original ATOM-07 `RETURN` for `f92ac33f35367f331b4719708e6719367a836696` / tree `75c6e0a099e4c968024e7164deb622ee29f5cf72`. It says actual W10/TS evidence was unavailable and explicitly says ATOM-07 was not accepted.
- `evidence/ATOM06_CONTROLLER_RETURN_20261012.md` records the original ATOM-06 `RETURN` for `a41b9e0cc47ab6843c7a8579214b1f8c2c5ecd89` / tree `2ad6a96916b7f2c336ab5aca1c36ffe65dbb3633`, because its ancestry contained the unaccepted ATOM-07 work. It explicitly did not authorize pushing that candidate.
- These records and verdicts have not been edited or reclassified.

## Present remote and inherited changes

At the start of this repair, local `main` and `origin/main` both pointed to `8c05e9c0de7b21b6193db1c7c7ea4ab211228f7f`, tree `ffb14b43632d46b5de37abad1d9eb989d12e60df`. This published history contains the ATOM-07 implementation/repair commits `13ef076`, `3f97803`, `7262978`, `9dac869`, `4c3b74f`, `332edf4`, `f92ac33`, followed by the preserved ATOM-07 RETURN archive `5b0d4c8`; it also contains ATOM-06 implementation/repair commits `5204ce4`, `a41b9e0`, followed by the preserved ATOM-06 RETURN archive `8c05e9c`.

The prior user instruction requested the then-current source be pushed so the remote could review it. The resulting remote state is a governance sequencing anomaly relative to the recorded Controller RETURN/no-push verdict: the remote contains changes whose ATOM-07 gate remains RETURN. That historical push is recorded as fact; it is not retroactive acceptance, does not alter either original verdict, and does not authorize another push. The current safety repair is a separate local candidate and needs a fresh independent Controller verdict on its exact commit/tree and inherited ancestry before any further push.

## Current repository safeguards

- Only `main` is used. No reset, clean, force push, history rewrite, or branch creation was performed.
- The six untracked W10 files remain unmodified, unstaged, and excluded from the candidate.
- No actual TS run, project root, user DataHome, private manuscript, provider receipt, or cost ledger was opened or changed.
- The synthetic temporary DataHome used by the E2E test is test-only; it is not a cutover choice.
- ATOM-07 remains `RETURN`; `CUTOVER_BLOCKED=true`; `PRIVATE_MIGRATION=NOT_RUN`.
