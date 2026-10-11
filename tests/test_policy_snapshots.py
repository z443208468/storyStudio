"""Offline tests for policy schema boundaries and immutable SHA snapshots."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.policy_snapshots import (
    METHOD_LENSES,
    METHOD_SPRINT,
    METHOD_STAGES,
    METHOD_VERIFIERS,
    CNW_METHOD_REFERENCE,
    WORK_CONTRACT_REQUIREMENTS,
    PolicySnapshotError,
    SnapshotStore,
    compose_policy_bundle,
    project_preflight_missing,
)


def app_policy():
    return {
        "schema_version": "storystudio_app_policy_v1",
        "method": {
            "per_unit_stages": list(METHOD_STAGES),
            "lens_ids": list(METHOD_LENSES),
            "adversarial": dict(METHOD_VERIFIERS),
            "sprint": dict(METHOD_SPRINT),
        },
        "method_reference": dict(CNW_METHOD_REFERENCE),
        "work_contract_requirements": json.loads(json.dumps(WORK_CONTRACT_REQUIREMENTS)),
        "installation_defaults": {"live_authorization": False, "project_required_for_writes": True, "provider_override_requires_registered_adapter": True, "unconfigured_project_fields_are_errors": True},
        "safety": {"max_in_flight": 5, "missing_usage": "UNKNOWN_NOT_ZERO", "reservation_before_send": True, "settlement_after_response": True, "campaign_limit_inheritance": False, "allow_output_without_frozen_work_contract": False, "method_fields_project_override_allowed": False, "method_fields_provider_override_allowed": False},
        "execution_compatibility": {"tested_locales": [], "maximum_validated_visible_characters_per_unit": None},
        "path_policy": {"data_home_must_be_explicit_or_user_selected": True, "project_identity_is_instance_scoped": True, "project_writes_require_registered_project": True},
    }


def provider_policy():
    return {
        "schema_version": "storystudio_provider_policy_v1",
        "adapter_id": "deepseek_flash",
        "model": "deepseek-flash",
        "base_url": "https://api.deepseek.com/v1",
        "key_environment_variable": "DEEPSEEK_API_KEY",
        "request_policy": {"max_in_flight": 5, "sdk_max_retries": 0, "network_extra_attempts": 2, "format_repair_extra_attempts": 1, "thinking": "disabled", "read_timeout_seconds": 180, "output_tokens": "derive_from_provider_capability_and_work_unit_requirements"},
        "pricing": {"currency": "CNY", "price_source": "official_current_pricing_at_execution", "missing_usage": "UNKNOWN_NOT_ZERO"},
        "accounting": {"reserve_before_send": True, "settle_after_response": True, "persist_across_run_ids": True, "auto_top_up": False, "new_project_inherits_historical_campaign_limit": False},
        "supported_project_override_ids": ["deepseek_flash"],
    }


def project_policy(project_id: str, locale: str, target: int, lens_id: str):
    return {
        "schema_version": "storystudio_project_policy_v1",
        "project_id": project_id,
        "display_name": project_id,
        "language": {"locale": locale, "length_unit": "unicode_visible_characters", "length_semantics": "normalized visible Unicode code points"},
        "writing": {"target_length": target, "minimum_length": target - 100, "maximum_length": target + 100},
        "arc": {"status": "CONFIRMED", "reference": "project://arc/revision-1"},
        "canon": {"status": "APPROVED", "reference": "project://canon/approval-1"},
        "characters": [],
        "world": {"status": "CONFIRMED", "reference": "project://world/revision-1"},
        "voice": {"status": "CONFIRMED", "reference": "project://voice/revision-1"},
        "forbidden_phrases": [],
        "review": {"fifth_lens": {"id": lens_id, "responsibility": "Check the project's confirmed reader promise."}},
        "sources": [],
        "integrations": {"jet": None, "nk": None, "critics": None},
        "execution": {"provider_override": None, "live_authorization": False, "authorization_ref": None, "campaign_limit_mode": None, "campaign_limit_cny": None},
    }


def raw_json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


class PolicySnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="storystudio-policy-snapshots-")
        self.store = SnapshotStore(Path(self.temp.name) / "snapshots")

    def tearDown(self):
        self.temp.cleanup()

    def put(self, document, kind, name):
        return self.store.put_bytes(raw_json(document), kind=kind, source_ref=name)

    def test_content_sha_resolves_legacy_policy_configurations_without_rewriting(self):
        cnw = {"schema_version": "cnw_production_policy_v1", "project_adaptation": {"project_id": "historic"}}
        old_provider = {"plan_version": "P2", "provider": {"model": "deepseek-flash"}, "cost_guard": {"estimated_campaign_limit": None}}
        cnw_sha = self.put(cnw, "legacy_project_policy", "config/cnw_production_policy.json")
        provider_sha = self.put(old_provider, "legacy_combined_production_config", "config/production.example.json")
        self.assertEqual(self.store.resolve_policy_by_sha(cnw_sha)["bytes"], raw_json(cnw))
        self.assertEqual(self.store.resolve_policy_by_sha(cnw_sha)["validation"]["compatibility"], "LEGACY_READ_ONLY")
        self.assertEqual(self.store.resolve_policy_by_sha(provider_sha)["document"], old_provider)
        self.assertEqual(self.store.resolve_policy_by_sha(provider_sha)["sha256"], provider_sha)

    def test_committed_snapshot_index_binds_current_active_bytes_and_known_legacy_bytes(self):
        from tools.policy_snapshots import DEFAULT_STORE, ROOT, resolve_policy_by_sha, sha256_bytes
        store = SnapshotStore(DEFAULT_STORE)
        for entry in store._read_index()["entries"]:
            if entry["availability"] == "AVAILABLE":
                resolved = store.resolve_snapshot_by_sha(entry["sha256"])
                self.assertEqual(sha256_bytes(resolved["bytes"]), entry["sha256"])
            else:
                with self.assertRaises(PolicySnapshotError) as missing_entry:
                    store.resolve_snapshot_by_sha(entry["sha256"])
                self.assertEqual(missing_entry.exception.code, "LEGACY_MIGRATION_REQUIRED")
        for relative, kind in (
            ("config/production.example.json", "legacy_combined_production_config"),
            ("config/cnw_production_policy.json", "legacy_project_policy"),
        ):
            raw = (ROOT / relative).read_bytes()
            digest = sha256_bytes(raw)
            self.assertEqual(store.resolve_snapshot_by_sha(digest, expected_kind=kind)["bytes"], raw)

        historic_provider = "b5dc2bebb54f9ee4beca56ad3bf2d9b88f9ab6831d7bd9211bedcd57a3a9e959"
        historic_runner = "ab8a40b15687b8fc35faffbef5c34553649f818f188c7e4cdfa57ba9342c21e3"
        self.assertEqual(sha256_bytes(resolve_policy_by_sha(historic_provider, expected_kind="legacy_production_config")["bytes"]), historic_provider)
        self.assertEqual(sha256_bytes(store.resolve_snapshot_by_sha(historic_runner, expected_kind="tool")["bytes"]), historic_runner)
        with self.assertRaises(PolicySnapshotError) as missing:
            store.resolve_snapshot_by_sha("d5debd560ee2c91ffcb7ca0c08f6dec7014e7436691795e74a23912b715a8d96")
        self.assertEqual(missing.exception.code, "LEGACY_MIGRATION_REQUIRED")

    def test_current_shadow_bundle_matches_the_committed_method_and_contains_no_example_story(self):
        from tools.policy_snapshots import DEFAULT_STORE, ROOT, sha256_bytes
        store = SnapshotStore(DEFAULT_STORE)
        app_raw = (ROOT / "config/policies/app_policy.v1.json").read_bytes()
        provider_raw = (ROOT / "config/policies/provider_policy.deepseek_flash.v1.json").read_bytes()
        project_raw = (ROOT / "config/policies/project_policy.template.v1.json").read_bytes()
        app = store.resolve_policy_by_sha(sha256_bytes(app_raw), expected_kind="app_policy")
        provider = store.resolve_policy_by_sha(sha256_bytes(provider_raw), expected_kind="provider_policy")
        project = store.resolve_policy_by_sha(sha256_bytes(project_raw), expected_kind="project_policy")
        self.assertEqual(app["document"]["method"]["per_unit_stages"], list(METHOD_STAGES))
        self.assertEqual(provider["document"]["adapter_id"], "deepseek_flash")
        self.assertEqual(project["validation"]["kind"], "project_policy")
        self.assertTrue(project["validation"]["missing_project_inputs"])
        app_text = app_raw.decode("utf-8").casefold()
        self.assertNotIn("cangqi", app_text)
        self.assertNotIn("j19", app_text)

    def test_legacy_active_consumers_can_read_the_same_config_without_side_effects(self):
        from tools import critics_bridge, p2_cost_guard
        before = Path("config/production.example.json").read_bytes()
        guard, pricing = p2_cost_guard.load_config()
        bridge_config = critics_bridge.read_json(critics_bridge.CONFIG)
        self.assertEqual(guard["model"], "deepseek-flash")
        self.assertEqual(pricing["requested_model"], "deepseek-flash")
        self.assertEqual(bridge_config["provider"]["model"], "deepseek-flash")
        self.assertEqual(Path("config/production.example.json").read_bytes(), before)

    def test_two_distinct_project_policies_resolve_and_compose_by_sha(self):
        app_sha = self.put(app_policy(), "app_policy", "config/policies/app_policy.v1.json")
        provider_sha = self.put(provider_policy(), "provider_policy", "config/policies/provider_policy.deepseek_flash.v1.json")
        first_doc = project_policy("NOVEL-ALPHA", "en-US", 2400, "reader-promise")
        second_doc = project_policy("ESSAY-BETA", "ja-JP", 900, "argument-clarity")
        first_sha = self.put(first_doc, "project_policy", "fixture/alpha.json")
        second_sha = self.put(second_doc, "project_policy", "fixture/beta.json")

        first = compose_policy_bundle(app_sha, provider_sha, first_sha, store=self.store.root)
        second = compose_policy_bundle(app_sha, provider_sha, second_sha, store=self.store.root)
        self.assertEqual(first["status"], "POLICY_BUNDLE_READY")
        self.assertEqual(first["project_id"], "NOVEL-ALPHA")
        self.assertEqual(second["status"], "POLICY_BUNDLE_READY")
        self.assertEqual(second["project_id"], "ESSAY-BETA")
        self.assertNotEqual(first["project_policy_sha256"], second["project_policy_sha256"])

    def test_unfilled_project_template_returns_specific_missing_inputs_and_keeps_live_closed(self):
        import json as json_module
        from tools.policy_snapshots import ROOT
        template = json.loads((ROOT / "config/policies/project_policy.template.v1.json").read_text(encoding="utf-8"))
        missing = project_preflight_missing(template)
        self.assertIn("project_id", missing)
        self.assertIn("language.locale", missing)
        self.assertIn("review.fifth_lens.actual_duties", missing)
        self.assertFalse(template["execution"]["live_authorization"])

    def test_project_policy_cannot_override_method_or_enable_unbounded_live_use(self):
        app_sha = self.put(app_policy(), "app_policy", "app.json")
        provider_sha = self.put(provider_policy(), "provider_policy", "provider.json")
        weakened = project_policy("P", "en-US", 1000, "custom")
        weakened["method"] = {"verifier_count": 0}
        digest = self.put(weakened, "project_policy", "invalid-project.json")
        with self.assertRaises(PolicySnapshotError) as error:
            compose_policy_bundle(app_sha, provider_sha, digest, store=self.store.root)
        self.assertEqual(error.exception.code, "PROJECT_METHOD_OVERRIDE_FORBIDDEN")

        uncapped = project_policy("P", "en-US", 1000, "custom")
        uncapped["execution"].update(live_authorization=True, authorization_ref="approval-1")
        uncapped_sha = self.put(uncapped, "project_policy", "uncapped-project.json")
        with self.assertRaises(PolicySnapshotError) as unbounded:
            compose_policy_bundle(app_sha, provider_sha, uncapped_sha, store=self.store.root)
        self.assertEqual(unbounded.exception.code, "PROJECT_LIVE_AUTHORIZATION_INCOMPLETE")

        explicitly_unlimited = project_policy("P", "en-US", 1000, "custom")
        explicitly_unlimited["execution"].update(live_authorization=True, authorization_ref="user-approval-1", campaign_limit_mode="unlimited_explicit")
        explicit_sha = self.put(explicitly_unlimited, "project_policy", "explicitly-unlimited-project.json")
        bundle = compose_policy_bundle(app_sha, provider_sha, explicit_sha, store=self.store.root)
        self.assertTrue(bundle["live_authorization"])

    def test_only_implemented_provider_adapter_is_accepted(self):
        unsupported = provider_policy()
        unsupported["adapter_id"] = "arbitrary_http"
        digest = self.put(unsupported, "provider_policy", "unsupported-provider.json")
        with self.assertRaises(PolicySnapshotError) as error:
            self.store.resolve_policy_by_sha(digest)
        self.assertEqual(error.exception.code, "PROVIDER_ADAPTER_UNSUPPORTED")

    def test_provider_policy_cannot_override_author_method(self):
        weakened = provider_policy()
        weakened["verifier_count"] = 0
        digest = self.put(weakened, "provider_policy", "method-override-provider.json")
        with self.assertRaises(PolicySnapshotError) as error:
            self.store.resolve_policy_by_sha(digest)
        self.assertEqual(error.exception.code, "PROVIDER_POLICY_SCOPE_INVALID")

        nested = provider_policy()
        nested["request_policy"]["sprint"] = {"size": 1}
        nested_digest = self.put(nested, "provider_policy", "nested-method-override-provider.json")
        with self.assertRaises(PolicySnapshotError) as nested_error:
            self.store.resolve_policy_by_sha(nested_digest)
        self.assertEqual(nested_error.exception.code, "PROVIDER_POLICY_SCOPE_INVALID")

    def test_fixed_method_constants_cannot_be_weakened_in_app_policy(self):
        weakened = app_policy()
        weakened["method"]["adversarial"]["verifier_count"] = 1
        digest = self.put(weakened, "app_policy", "weakened-app.json")
        with self.assertRaises(PolicySnapshotError) as error:
            self.store.resolve_policy_by_sha(digest)
        self.assertEqual(error.exception.code, "METHOD_CONTRACT_MISMATCH")

    def test_arbitrary_frozen_bytes_are_returned_with_the_original_sha(self):
        manifest_bytes = b'{"sources":[{"id":"A"}]}\r\n'
        digest = self.store.put_bytes(manifest_bytes, kind="source_manifest", source_ref="private://fixture/manifest")
        resolved = self.store.resolve_snapshot_by_sha(digest, expected_kind="source_manifest")
        self.assertEqual(resolved["bytes"], manifest_bytes)
        self.assertEqual(resolved["sha256"], digest)

    def test_mutated_snapshot_is_rejected_without_repair(self):
        raw = b'{"schema_version":"cnw_production_policy_v1"}\n'
        digest = self.store.put_bytes(raw, kind="legacy_project_policy", source_ref="legacy-policy.json")
        object_path = self.store.objects / f"{digest}.blob"
        object_path.write_bytes(b"tampered")
        with self.assertRaises(PolicySnapshotError) as error:
            self.store.resolve_snapshot_by_sha(digest)
        self.assertEqual(error.exception.code, "SNAPSHOT_HASH_MISMATCH")
        self.assertEqual(object_path.read_bytes(), b"tampered")

    def test_known_missing_legacy_hash_returns_migration_required(self):
        digest = "d" * 64
        self.store.mark_legacy_missing(digest, kind="legacy_production_config", source_ref="old-run", reason="exact bytes unavailable")
        with self.assertRaises(PolicySnapshotError) as error:
            self.store.resolve_snapshot_by_sha(digest)
        self.assertEqual(error.exception.code, "LEGACY_MIGRATION_REQUIRED")

    def test_unregistered_and_malformed_hashes_fail_closed(self):
        with self.assertRaises(PolicySnapshotError) as unknown:
            self.store.resolve_snapshot_by_sha("0" * 64)
        self.assertEqual(unknown.exception.code, "SNAPSHOT_NOT_FOUND")
        with self.assertRaises(PolicySnapshotError) as malformed:
            self.store.resolve_snapshot_by_sha("../policy.json")
        self.assertEqual(malformed.exception.code, "SNAPSHOT_SHA_INVALID")

    def test_registered_snapshot_bytes_must_match_declared_identity(self):
        with self.assertRaises(PolicySnapshotError) as mismatch:
            self.store.put_bytes(b"actual", kind="tool", source_ref="tool.py", expected_sha256="0" * 64)
        self.assertEqual(mismatch.exception.code, "SNAPSHOT_SOURCE_HASH_MISMATCH")

    def test_legacy_campaign_null_is_read_only_and_does_not_authorize_project(self):
        old = {"plan_version": "P2", "provider": {"model": "deepseek-flash"}, "cost_guard": {"estimated_campaign_limit": None}}
        old_sha = self.put(old, "legacy_combined_production_config", "historic.json")
        project = project_policy("NEW-PROJECT", "en-US", 1500, "reader-value")
        project_sha = self.put(project, "project_policy", "new-project.json")
        self.assertIsNone(self.store.resolve_policy_by_sha(old_sha)["document"]["cost_guard"]["estimated_campaign_limit"])
        self.assertFalse(self.store.resolve_policy_by_sha(project_sha)["document"]["execution"]["live_authorization"])


if __name__ == "__main__":
    unittest.main()
