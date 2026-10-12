# ATOM-09 bootstrap cold-clone evidence — 2026-10-13

## Scope

This evidence covers the R5 §09.2 clean-checkout/bootstrap RETURN only. It does not accept the input-pack-to-story path, authorize Live production or fees, accept Atom 10, or authorize a push. The prior Controller RETURN for `bda010d33489bab280ab31702f3f7d530056fe1c` remains unchanged; this is a later repair candidate awaiting independent review.

## Exact tested source

- Commit: `86fb0ac95208888418c9d37d49e40f0558a0bd41`
- Tree: `4a1dd3c8aa09e727de8bd6a360d4b465a9d5ed50`
- Branch: `main`
- R5 plan SHA-256: `AE5A1959EEAB75AD6A8F41460C38BF9678284C1D51A8D63B25CE37F7CB4F5183`
- Fresh checkout: `D:\CangqiStudio\StoryStudio_coldclone_86fb0ac`
- The checkout was created without recursive submodules, then each declared local cache was configured and Git initialized the recorded submodules with `--no-fetch`. `git submodule status` returned all three exact gitlink SHAs without `-`, `+`, or `U` markers.

| File | SHA-256 |
|---|---|
| `README.md` | `67A794A4565878907C5BAD6DE75D57AF24E88FDC567B23CE8325C5F2DF3D9C93` |
| `tests/test_studio_cli_routes.py` | `D85CEAB3F69FD50D0044E43FB304A74765A7B08D2262B74D866ACE5D732AE1A6` |
| `tools/studio.ps1` | `E0F6AA867E505127EB8F403A90139B19D642B8D02331737D8FF2A350C0550BD9` |
| `tools/bootstrap_verification.ps1` | `47977FC6C244BFA2281E2A9BE1219806FFC17C35E90DE972AB81AAD976AC4CD6` |
| `docs/BOOTSTRAP_VERIFICATION.md` | `9C09DEE01C8EFB3AC8C47BC461DDEFF3909D8C1E35F4E0F0EA6384EC48B29DB9` |

## Bootstrap execution

Before bootstrap, the fresh checkout's `doctor -AppOnly` returned `ENGINE_READY`, `project=NOT_SELECTED`, `provider_call=none`, `generic_live_production=NOT_RUN`, `author_reference=RUNTIME_MISSING`, and optional CritiCS/NK unavailable by identity.

Command, from the fresh checkout root:

```powershell
pwsh -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File tools/bootstrap_verification.ps1 -Offline -Python313 'C:\Program Files\Python313\python.exe' -Python311 'C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe'
```

Exit code: `0`.

Observed output: `REFERENCE_CAPTURE_VERIFIED` for CNW commit `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e` with 98 files and manifest SHA-256 `E9B989C52C66AB9BE8C73F09E84BC5BD7D2ECC92F9F1CBFC61BA300DC6CD3983`; CritiCS build source/patched/lock identities matched; 44 locked dependencies installed in the isolated Python 3.11 environment; `uv pip check --offline` reported all installed packages compatible. Final doctor returned `ENGINE_READY`, `core_runtime=READY`, `author_reference=PINNED_REFERENCE_VERIFIED`, `optional_critics=AVAILABLE_PINNED`, `project=NOT_SELECTED`, `provider_call=none`, `generic_live_production=NOT_RUN`. Bootstrap ended with `VERIFICATION_BOOTSTRAP_READY`, `offline=true`, and NK not built or started.

## Full offline suite

Command (Python 3.13; test-only API key variables removed from the process environment):

```powershell
python -m pytest tests -q
```

Environment: `PYTHONUTF8=1`, `PYTHONPATH=<fresh-checkout>; <fresh-checkout>\tests`. Provider API key variables were absent; no real Provider call occurred.

Exit code: `0`.

Raw final result: `306 passed, 87 subtests passed in 252.48s (0:04:12)`.

After tests, the main checkout reported clean `git status`; all three initialized submodules still matched the listed commits and were clean. This proves the bootstrap instructions and offline verification environment for this candidate only. Simulated CNW results remain `MOCK_ONLY`/`SIMULATED` and do not establish live production or creative acceptance.
