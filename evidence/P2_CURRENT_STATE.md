# P2 当前状态

本文件是**阶段快照**，所有工作树/提交字段均以快照基准提交为准；候选冻结和远端回读以 `reviews/P2_ACCEPTANCE_LOG.md` 中对应候选记录为准。不要将此历史快照误读为候选提交之后的实时状态。

- SNAPSHOT_BASE_C: `bbdfbc6b477e0c800a2b7bd02cf6a181b880a266`
- SNAPSHOT_BASE_T: `5a7128f437713a03e730d95a4a40a78b51891baf`
- BRANCH: `codex/g00-governance-candidate`
- SNAPSHOT_WORKTREE: P2-04 live integration artifacts and route correction are assembled for Controller review.
- CURRENT_STAGE: `P2-06` production/revision; P2-05 single-scene Plot received Controller boundary-limited ACCEPT after one continuity correction. P2-04/P2-05 acceptances are recorded in `reviews/P2_ACCEPTANCE_LOG.md`.
- LAST_ACCEPTED: P2-05 Controller boundary-limited local ACCEPT; P2-04 remote readback ACCEPT; P2-03/02/01/00 remain accepted.
- SOURCE_ZIP_SHA256: `300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2`
- SOURCE_VERSION: `JUN-SINGLE-02.3`
- PRIVATE_SOURCE_ROOT: `inputs/private/release/300a829c7524d620ab89177afcf52c03dffea633392c632f69a943f798dad3b2/Cangqi_Jun_Release_2_3/`
- PRIVATE_CNW_PROJECT: `workspace/cangqi/`
- ORIGINAL_FAILURE: P1 `B11 / BLOCKED_UPSTREAM_IMMUTABLE` was a pre-repair fact; P2 permits production-copy repair. Original raw evidence remains at `runtime/build/CritiCS/741b5bd13c8d44dca84f74854ab6bf00/py_compile.stdout-stderr.txt`, SHA256 `3E5E4B0FA7360AD4C793406D0FAF3E1E6062CCD21D0BA40CB1EED273A8ADCBBA`.
- NEXT: continue P2-06 using the accepted single-scene Plot and sample contract; reuse successful P2-05 provider result.

The private release's `source_manifest.json` and `source_index.json` are stored beside the imported source; the primary script is immutable and read-only. Their candidate SHA256 values are supplied to the Controller at review time and in the acceptance log after verdict.
