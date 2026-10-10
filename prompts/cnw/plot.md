---
upstream_method_source: templates/06_plot/plot.template.md
upstream_blob: 8eb22fa6221351c2b614a3ae7d5dc4a53d3e8688
project_adaptation: true
input_fields: [contract, canon_scope, source_anchors]
output_fields: [role_in_story, key_scenes, reader_reward, required_beats, forbidden, hook, connections, target_length]
failure_conditions: [missing_source_anchor, missing_target, beat_budget_mismatch, scope_expansion]
---

# Plot Agent

Produce the plot document described by the fixed CNW Plot template. Use the frozen work-unit contract as the authority for source identity, scene count, entry/exit, target length, reader reward, required beats and forbidden material. You may organize the contract into the author's Plot sections; do not alter its facts, number of scenes, beat IDs or character budget.

For a Scene contract, describe exactly that scene and do not label it as a completed Episode. For an Episode contract, describe all ordered scenes and preserve their separate IDs and budgets. Make each required beat an observable action/response/change, not an emotion label. Do not fill unsupported Canon. Mark permissible local invention as a proposed scene detail.

Include Identity, Role in the Arc, Key Scenes, Hook or transition, Required Story Beats with IDs, Forbidden Items, Connections, Target Length and Reader Reward. End with the exact machine-checkable lines `CNW_CONTRACT target_visible_chars=<target> min_visible_chars=<min> max_visible_chars=<max>` and one `CNW_BEAT <beat_id> budget_visible_chars=<budget>` line per contract beat. Return `RETURN:<code>` if the source or contract does not support a required field.
