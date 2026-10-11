# Configuration and Identity Compatibility

This document defines the Atom-02 shadow configuration boundary. The R5 plan is the active contract; this table records the observed pre-migration identities and what the new resolver can safely do with them.

## Immutable legacy inputs

| Identity | SHA-256 | Status | Compatibility rule |
|---|---|---|---|
| `config/production.example.json` current legacy combined config | `A7B5E8284264BFF0BD8C40960EDA1A8F073BFB5E11E395F5C329C7D2B8BDEF8A` | Exact bytes available | Remains active for every unconverted consumer. |
| Earlier provider config referenced by retained runs | `B5DC2BEBB54F9EE4BECA56AD3BF2D9B88F9AB6831D7BD9211BEDCD57A3A9E959` | Exact CRLF bytes recovered from Git revision `29dec841a55d78ac843101bdf87c15dfe240a803`, verified against the recorded SHA | Read by content SHA only; never substituted for the current active file. |
| Historical provider config referenced by retained runs | `D5DEBD560EE2C91FFCB7CA0C08F6DEC7014E7436691795E74A23912B715A8D96` | Exact bytes unavailable after checking the Atom-00 archive and Git path history | `LEGACY_MIGRATION_REQUIRED`; retain the run and do not infer bytes from the current config. |
| `config/cnw_production_policy.json` legacy project policy | `D4C4FE2B877D4BBADB33A39D6378E2769FD6D9DE449EDDBB5A17A203CC56854D` | Exact bytes available | Legacy contracts carrying this `policy_sha256` keep their original value. |
| `config/p2_cost_pricing_2026-10-10.json` | `7CD8F0DB82D122BF212FADE5EC42C03D158C77FEE6AB1C0025FB0C6A3EF20CD7` | Exact bytes available | Historical ledger pricing snapshots stay authoritative for old requests. |
| `tools/p2_cost_guard.py` current | `302ED5AE378C9BDF49DBEEB3505CCD0EFC690FCC1969A651D1062A128F2075F5` | Exact bytes available | Existing run state remains unchanged. |
| `tools/p2_cost_guard.py` earlier | `AB8A40B15687B8FC35FAFFBEF5C34553649F818F188C7E4CDFA57BA9342C21E3` | Exact CRLF bytes recovered from Git revision `3c0d8c23e251ccf76d80ac72fce2b9f18515bc7d`, verified against the run identity | Read by content SHA only. |
| Historical cost guard runner | `7A650695452B549F431325A14A690C51238D880B6D117388E0FA144EB8470E28` | Exact bytes unavailable | `LEGACY_MIGRATION_REQUIRED`; do not replace with the current runner. |
| Historical cost guard runner | `EAD9B205791EA7E96BCDBA475B7C9D92A117710949CB82C9C33B6441C8712815` | Exact bytes unavailable | `LEGACY_MIGRATION_REQUIRED`; do not replace with the current runner. |
| CNW workflow template | `613770163A03EE9C6F00063B6B284D75636F48D662420967EE6189D1E473F68F` | Exact bytes available; upstream method pin is `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e` | Fixed method identity, not project or provider policy. |

The two unavailable runner/configuration identities above are not synthesized. A request to resolve one fails with `LEGACY_MIGRATION_REQUIRED`. Existing contracts, run states, manifests, receipts, and the campaign ledger are retained byte-for-byte; the Atom-00 restricted archive remains the pre-refactor recovery source. It verified 1,791 source/archive pairs with zero mismatches and captured the private run, source, and ledger files outside Git.

## Policy layers

| Layer | New shadow file | Owns | Must not own |
|---|---|---|---|
| App and author method | `config/policies/app_policy.v1.json` | Pinned CNW stages, five lens identities, three verifiers, refute default, threshold, five-unit sprint rule, path and accounting safety | Story, source, character, length, or campaign identity |
| Provider adapter | `config/policies/provider_policy.deepseek_flash.v1.json` | Implemented DeepSeek Flash endpoint/model/key environment name, transport bounds, price source, reserve/send/settle protocol | Story/project identity, live authorization, method overrides |
| Project | `config/policies/project_policy.template.v1.json` | Explicit project language, length, Arc/Canon/characters/world/voice/forbidden phrases, fifth-lens duties, sources, optional integrations and execution authorization | Author method changes or implicit inheritance from another project |
| Work contract | Per-project immutable contract and SHA | Work unit, source revision/range, anchors, required beats, output target, review choice | Defaults silently inherited from the old fixed-scene contract |

## Field and method-value crosswalk

This crosswalk records the concrete legacy JSON paths and their shadow destination. Values in the new project template are deliberately unconfigured until supplied for a particular project.

| Legacy path | Legacy value or role | Shadow destination | Shadow value/rule |
|---|---|---|---|
| `production.example.json.plan_version`, `.template_status` | `P2`; example-only marker | Retained only in the legacy file | No new-run meaning; the new policy schemas have explicit `schema_version`. |
| `production.example.json.project_root` | Repository absolute path | `tools/project_paths.py` DataHome + registered project identity | No project root in app, Provider, or project policy. |
| `.provider.name`, `.base_url`, `.model`, `.key_environment_variable`, `.thinking`, `.max_in_flight`, retry and timeout keys | DeepSeek Flash transport defaults | `provider_policy.deepseek_flash.v1.json` | Exact implemented DeepSeek Flash adapter values; unsupported adapters reject. |
| `.cost_guard.currency`, `.persist_across_run_ids`, `.auto_top_up`, `.price_source`, `.missing_usage`, `.is_hard_billing_guarantee` | CNY; persistent; no auto top-up; unknown usage is nonzero-risk; estimate is not a hard guarantee | Provider policy `pricing` and `accounting` | Same reserve/send/settle meaning; unknown usage remains `UNKNOWN_NOT_ZERO`. |
| `.cost_guard.estimated_campaign_limit = null` | Existing campaign's explicit no-limit authorization | Legacy snapshot only; new project `execution.live_authorization=false`, budget mode `null` | No inheritance. A new explicit authorization can later choose its own bounded or `unlimited_explicit` mode. |
| `.source.expected_version`, `.expected_zip_sha256`, `.private_output` | One fixed source and repository-relative output | Project policy `.sources = null`; source identity lives in the future work contract | No source or output root is inferred from an example project. |
| `.sample.id`, `.pov`, `.language`, `.literary_word_count_target` | Fixed example project and language | Project policy `.project_id`, `.language`, `.writing` | All unset in the template; length unit and semantics must be explicit. |
| `.sample.max_distinct_scenes_before_user_review`, `.blind_regeneration`, `.content_revision_rounds_before_root_cause_review`, `.critic_text_scope`, `.full_scene_review` | Single-sample review and regeneration rules | Work contract and project review policy | No global project default; each work unit must freeze its scope and review choice. |
| `.nk.listen_host`, `.preferred_port`, `.selected_live_route`, `.structured_outputs`, `.client_key_persistence` | One local NK adapter setup | Project policy `.integrations.nk = null` | Optional; disabled/unconfigured in a new project. The repository pin remains in dependency metadata. |
| `.upstream.cnw` | `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e` | App policy `.method_reference.commit` | Same pinned method commit. |
| `cnw_production_policy.json.method_reference.commit`, `.workflow_template_blob` | CNW source and workflow blob pin | App policy `.method_reference` | Exact same source and workflow identities, plus the captured local reference manifest SHA. |
| `cnw_production_policy.json.local_reference_manifest_sha256` | Captured CNW public method-reference tree identity | App policy `.method_reference.local_reference_manifest_sha256` | Same value `E9B989C52C66AB9BE8C73F09E84BC5BD7D2ECC92F9F1CBFC61BA300DC6CD3983`. |
| `cnw_production_policy.json.project_adaptation.project_id`, `.language`, `.length_unit`, `.length_algorithm` | `cangqi`, `zh-CN`, Unicode visible characters, old algorithm text | Project policy `.project_id`, `.language` | Template values null; no story or locale defaults are copied. |
| `cnw_production_policy.json.project_adaptation.allow_output_without_frozen_contract` | `false` | App safety `.allow_output_without_frozen_work_contract` | Remains `false`. |
| `cnw_production_policy.json.project_adaptation.required_scene_fields`, `.required_story_fields`, `.require_exact_beat_budget_sum` | Frozen CNW contract structure | App `.work_contract_requirements` | Same actual key sets and `true` budget-sum requirement; validators reject changes. |
| `production.example.json.acceptance.*` | Independent Controller and final human creative review | Repository governance | Not a project preference and not a self-acceptance switch. |

The author-method value comparison is also checked by `validate_policy_document`: the 11 stages, all five lens IDs, the 3-verifier/refute/threshold tuple, the 5-unit sprint thresholds, work-contract required-field paths, and all three CNW method pins must match the pinned values exactly. Project and Provider documents cannot carry these override keys.

The template deliberately has null project inputs. Its resolver result is `PRE_FLIGHT_MISSING_PROJECT_INPUT` with the missing field paths. Empty sample data is never treated as an approved Canon, source registry, style profile, or fifth lens. If a new project later enables live work, it must carry its own authorization reference and an explicit budget decision (`bounded` with a positive cap, or `unlimited_explicit`); the historical global `null` cap does not flow into it.

Only the implemented `deepseek_flash` adapter is accepted. No multi-provider support or execution compatibility is claimed here. `tested_locales` is empty and the validated maximum work-unit length is null; Atom-02 creates no unsupported language or length claim.

## Method lock

The app policy preserves the pinned template values exactly:

- Stages, in order: `plot`, `scene_cards`, `writing_brief`, `prose`, `lint_layer1`, `lint_layer2`, `multi_lens_review`, `adversarial_verify`, `completeness_critic`, `refine`, `re_review`.
- Lenses: `style`, `character`, `plot`, `canon`, `story_specific`. A project fills the last lens's actual duties; it cannot remove the lens.
- Adversarial verification: 3 verifiers, refutation on by default, threshold 2.
- Sprint: 5 units; minimum score 75; maximum P0 findings 0; maximum P1 findings 2.

Project and Provider validators reject method/workflow override fields. The old active configs and their existing readers remain in place through Atom-02. Atom-03/04 move consumers one at a time; Atom-05 may switch data only after all consumers are adapted and validated.

## Run and source identities

Observed retained state includes J19/v5 and diagnostic runs with original contract hashes, provider-config hashes, cost-runner hashes, workflow hashes, and in one execution record, per-stage builder/transport identities. Atom-02 does not edit those run directories. Full private run/state/source manifests and source indexes are retained in the external Atom-00 archive; its manifest binds their original paths and content hashes. Before any later operation overwrites or imports a referenced manifest, that file must first be copied to a content-addressed private snapshot. If an exact old source snapshot is missing, report `LEGACY_SOURCE_SNAPSHOT_MISSING`; never rebuild an old SHA from the current source list.

Historical hashes not backed by exact bytes are not compatible execution identities. Existing J19 stages with code-identity mismatches are only eligible for frozen-history read-only verification. An incomplete v5 run may be considered for future continuation only through an explicitly reviewed migration sidecar and network-free preflight; no contract, state, stage identity, or receipt is rewritten by Atom-02.

## Activation and rollback

Atom-02 only writes shadow policies and content-addressed snapshots. It does not rename or replace either old active config. Each new snapshot is selected by its content SHA; the index is descriptive, while each resolved object is independently re-hashed. Until a later Atom records that every named consumer is compatible, rollback is simply to the unchanged legacy file path. After a consumer migration, rollback must select an explicit compatible policy SHA and preserve all run-bound identities; never edit the old contract SHA to make a different policy appear compatible.
