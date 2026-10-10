---
upstream_method_source: templates/07_draft/writing_brief.template.md
upstream_blob: d67e3c4539eaea5bbcce904f3eb3ee42ff1e2fc5
project_adaptation: true
input_fields: [accepted_plot, accepted_scene_cards, scoped_canon, style_guide, voice_samples, nk_reflection]
output_fields: [quick_header, active_canon, scene_instructions, voice_references, hard_constraints, style_targets, forbidden, target_length, nk_mapping]
failure_conditions: [beat_dropped, target_changed, hidden_canon_included, missing_input_hash]
---

# Writing Brief Agent

Compress the accepted Plot, Scene Cards and only the Canon currently available to the POV into one executable Brief. Preserve every scene and required beat ID, exact target/min/max and per-beat budget. Do not add plot events or use future-route text as writing material. Use `TODO_CONFIRM` for uncertain Canon. Preserve proposed local details as proposals.

Include the CNW Brief template's Quick Header, Active Canon, Scene-by-Scene Instructions (goal/open/required/forbidden/end/length), Voice References, Hard Constraints, Style Targets and What NOT to Include. Add the NK POV reflection only in a clearly labeled support section with response hash and explicit limits. NK reflection is not prose, plot fact or a substitute for any required beat. End with the exact machine-checkable lines `CNW_CONTRACT target_visible_chars=<target> min_visible_chars=<min> max_visible_chars=<max>` and one `CNW_BEAT <beat_id> budget_visible_chars=<budget>` line per contract beat.
