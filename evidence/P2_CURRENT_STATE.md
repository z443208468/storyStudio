# P2 当前状态

以下字段是 `29dec841a55d78ac843101bdf87c15dfe240a803` 被 Controller 退回后、修正状态指针之前的现场快照；它们不是对随后新候选提交的自引用字段。

```text
PLAN_VERSION=P2
CURRENT_STAGE=P2-00
BRANCH=codex/g00-governance-candidate
LOCAL_HEAD=29dec841a55d78ac843101bdf87c15dfe240a803
WORKTREE=DIRTY_WITH_PATHS（仅 evidence/P2_CURRENT_STATE.md 因 Controller 的状态快照意见待修；此前 P2-00 候选所含文件见下方 P2_00_RETURNED_CANDIDATE）
LAST_CONTROLLER_MESSAGE=同一委任子智能体 /root/g00_reviewer；P2-00 本地候选 RETURN，要求将候选 HEAD/clean 状态与此前快照字段区分；消息身份及摘要见 reviews/P2_ACCEPTANCE_LOG.md
LAST_ACCEPTED_CODE=P1 I01 C=2586d378669b74d4fc9e4460aa80f2cd8a908038 T=5b14e80075811f76f4a1bec10da00b0725bddd69
PRIVATE_ARTIFACT_MANIFEST_SHA256=NOT_RUN
SOURCE_STATUS=CNW 97ad71fe5e5e76a82275c6c63d4add06fb60ab6e clean; NK b857f34b7d371ae82c30e00eb021884c14d08ae9 clean; CritiCS fbf66cbc913012c6f80af1687e27f0ce350475e3 clean. 2.3 ZIP expected SHA256 300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2; current path/content not yet verified in P2
CRITICS_BUILD=NOT_RUN; P1 raw syntax failure preserved; P2 patch not yet created
NK_BUILD=NOT_RUN; P2 patch not yet created
CURRENT_RUN=NOT_RUN
ESTIMATED_CAMPAIGN_SPEND=UNKNOWN
BILLED_SPEND=UNKNOWN
DEPLOYED=NOT_RUN
WORKFLOW_METHOD_REVIEWED=NOT_RUN
LIVE_CHAIN_VERIFIED=NOT_RUN
ONE_SCENE_DELIVERED=NOT_RUN
USER_CREATIVE_ACCEPTED=NOT_REVIEWED
P2_00_RETURNED_CANDIDATE=C=29dec841a55d78ac843101bdf87c15dfe240a803 T=f89362aedfc791d816ca56a2ca74b32321801287; Controller requested only a state-snapshot correction
NEXT_ACTION=Correct this snapshot, freeze a new P2-00 candidate, and resubmit to the delegated Controller
EXTERNAL_INPUT_NEEDED=NONE
```

P2-00 kickoff snapshot: local HEAD and remote candidate branch were `2586d378669b74d4fc9e4460aa80f2cd8a908038`; worktree was clean before P2-00 edits. Remote main was `06c66de7c7f18263039ea19a47e84c29716cde4b`. Package ZIP SHA256: `246C6F233E54CB019BA1FF2C2061F0154AF84C44B152B60CBC8F762F97B2106B`; all 15 listed file hashes matched `MANIFEST_SHA256.txt` before copying. P1 I01 original error is retained at `runtime/build/CritiCS/741b5bd13c8d44dca84f74854ab6bf00/py_compile.stdout-stderr.txt` (SHA256 `3E5E4B0FA7360AD4C793406D0FAF3E1E6062CCD21D0BA40CB1EED273A8ADCBBA`).
