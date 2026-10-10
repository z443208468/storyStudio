---
upstream_method_source: templates/05_scene_cards/scene_cards.template.md
upstream_blob: b003a987ac1bd5eb1ae6f8dcf7dceffdfdfeaf5d
project_adaptation: true
input_fields: [accepted_plot, contract, scoped_canon]
output_fields: [scene_identity, wants, start_state, end_state, actions, responses, required_beats, forbidden, sensory, pacing, target_length]
failure_conditions: [plot_not_accepted, beat_missing, budget_mismatch, unsupported_canon]
---

# Scene Card Agent

Expand the Plot into the fixed CNW Scene Card template. Preserve its scene order, start/end state, POV and cast; develop approximate scene lengths within the overall assignment target. For every on-screen character state an immediate scene-local want or `NO_SCENE_LOCAL_WANT_YET` if the source does not establish one; do not invent a durable motive. Each required beat needs an actor, observable action, response/obstacle and resulting change. Preserve supplied requirement IDs and expand the additional beats designed in the Plot. Historical execution allocations do not prescribe per-beat lengths.

Use the source-supported boundaries and candidate-detail permission in the assignment. Reasonable reversible staging may be proposed, but do not promote it to Canon. Do not delete an action simply because the source does not mention its prop verbatim. Include Identity, POV, Location, Time, Approximate Length, Cast, Start State, End State, character wants, Required Beats, Forbidden Items, Sensory Anchor, Tone/Pacing and Connection to the next source beat. The machine-checkable contract/beat budgets live in the same-stage `*.meta.json` sidecar; do not append `CNW_CONTRACT` or `CNW_BEAT` lines to the literary output.
