# P2 当前状态模板（不是已发生的状态）

执行时将真实值写入 `evidence/P2_CURRENT_STATE.md`，不要直接把模板当成果。

```text
PLAN_VERSION=P2
CURRENT_STAGE=<actual P2-xx>
BRANCH=<actual>
LOCAL_HEAD=<actual>
WORKTREE=<actual modified paths and ownership>
LAST_CONTROLLER_MESSAGE=<actual reference/text location>
LAST_ACCEPTED_CODE=<actual commit/tree>
PRIVATE_ARTIFACT_MANIFEST_SHA256=<actual or NOT_RUN>
SOURCE_STATUS=<actual identity and status>
CRITICS_BUILD=<actual source+patch+lock identity or NOT_RUN>
NK_BUILD=<actual source+patch+lock identity or NOT_RUN>
CURRENT_RUN=<actual or NOT_RUN>
ESTIMATED_CAMPAIGN_SPEND=<actual estimate or UNKNOWN>
BILLED_SPEND=<actual receipt or UNKNOWN>
DEPLOYED=<NOT_RUN|IN_PROGRESS|VERIFIED>
WORKFLOW_METHOD_REVIEWED=<NOT_RUN|RETURN|ACCEPTED>
LIVE_CHAIN_VERIFIED=<NOT_RUN|IN_PROGRESS|VERIFIED>
ONE_SCENE_DELIVERED=<NOT_RUN|IN_PROGRESS|DELIVERED>
USER_CREATIVE_ACCEPTED=<NOT_REVIEWED|ACCEPTED|REVISION_REQUESTED>
NEXT_ACTION=<specific action>
EXTERNAL_INPUT_NEEDED=<specific true missing item or NONE>
```

状态反映真实结果，不因复制 P2 包就全部变为 VERIFIED。当前状态文件只保存一份，历史签收追加到独立日志；不创建多份互相矛盾的活动状态。
