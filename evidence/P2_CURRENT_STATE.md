# P2 当前状态

本文件是**阶段快照**，所有工作树/提交字段均以快照基准提交为准；候选冻结和远端回读以 `reviews/P2_ACCEPTANCE_LOG.md` 中对应候选记录为准。不要将此历史快照误读为候选提交之后的实时状态。

- SNAPSHOT_BASE_C: `591b979734981fc30a3a3c011cce8aa622239a8c`
- SNAPSHOT_BASE_T: `3de19929b54cea86d9a3aef159884b3087a1a493`
- BRANCH: `codex/g00-governance-candidate`
- SNAPSHOT_WORKTREE: clean after P2-02 remote acceptance; P2-03 candidate files are being assembled.
- CURRENT_STAGE: `P2-03` Narrative Keyframing adapter; local Controller acceptance pending.
- LAST_ACCEPTED: P2-02 local and remote accepted by delegated read-only Controller `/root/g00_reviewer`; P2-01 and P2-00 remain accepted.
- SOURCE_ZIP_SHA256: `300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2`
- SOURCE_VERSION: `JUN-SINGLE-02.3`
- PRIVATE_SOURCE_ROOT: `inputs/private/release/300a829c7524d620ab89177afcf52c03dffea633392c632f69a943f798dad3b2/Cangqi_Jun_Release_2_3/`
- PRIVATE_CNW_PROJECT: `workspace/cangqi/`
- ORIGINAL_FAILURE: P1 `B11 / BLOCKED_UPSTREAM_IMMUTABLE` was a pre-repair fact; P2 permits production-copy repair. Original raw evidence remains at `runtime/build/CritiCS/741b5bd13c8d44dca84f74854ab6bf00/py_compile.stdout-stderr.txt`, SHA256 `3E5E4B0FA7360AD4C793406D0FAF3E1E6062CCD21D0BA40CB1EED273A8ADCBBA`.
- NEXT: freeze P2-03, request Controller local acceptance, push and verify remote readback; then run P2-04 live integration using the existing server key and cost guard.

The private release's `source_manifest.json` and `source_index.json` are stored beside the imported source; the primary script is immutable and read-only. Their candidate SHA256 values are supplied to the Controller at review time and in the acceptance log after verdict.
