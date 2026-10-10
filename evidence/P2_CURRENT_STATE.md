# P2 当前状态

本文件是**阶段快照**，所有工作树/提交字段均以快照基准提交为准；候选冻结和远端回读以 `reviews/P2_ACCEPTANCE_LOG.md` 中对应候选记录为准。不要将此历史快照误读为候选提交之后的实时状态。

- SNAPSHOT_BASE_C: `675d2b6b26ccbb9bd913cc435266748769a7a918`
- SNAPSHOT_BASE_T: `a6c8b171c760391e6bee4a72fd0868d90d53062d`
- BRANCH: `codex/g00-governance-candidate`
- SNAPSHOT_WORKTREE: clean after P2-01 remote acceptance; P2-02 candidate changes are being assembled.
- CURRENT_STAGE: `P2-02` CritiCS patch, locked dependencies, offline contract and scoped security review; local Controller acceptance pending.
- LAST_ACCEPTED: P2-01 local and remote accepted by delegated read-only Controller `/root/g00_reviewer`; see acceptance log. P2-00 remains accepted.
- SOURCE_ZIP_SHA256: `300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2`
- SOURCE_VERSION: `JUN-SINGLE-02.3`
- PRIVATE_SOURCE_ROOT: `inputs/private/release/300a829c7524d620ab89177afcf52c03dffea633392c632f69a943f798dad3b2/Cangqi_Jun_Release_2_3/`
- PRIVATE_CNW_PROJECT: `workspace/cangqi/`
- ORIGINAL_FAILURE: P1 `B11 / BLOCKED_UPSTREAM_IMMUTABLE` was a pre-repair fact; P2 permits production-copy repair. Original raw evidence remains at `runtime/build/CritiCS/741b5bd13c8d44dca84f74854ab6bf00/py_compile.stdout-stderr.txt`, SHA256 `3E5E4B0FA7360AD4C793406D0FAF3E1E6062CCD21D0BA40CB1EED273A8ADCBBA`.
- NEXT: freeze P2-02, request Controller local acceptance, push and verify remote readback; then start P2-03 NK adapter and P2-04 live integration as prerequisites permit.

The private release's `source_manifest.json` and `source_index.json` are stored beside the imported source; the primary script is immutable and read-only. Their candidate SHA256 values are supplied to the Controller at review time and in the acceptance log after verdict.
