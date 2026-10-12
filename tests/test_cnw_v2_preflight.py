"""V2 deterministic identity and signed review remain separate from Live/fees."""
import base64
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_cnw_run_bindings as fixtures
from tests.test_cnw_input_pack import encoded, sha
from tools import cnw_runner as runner, cnw_w10_policy as policy, cnw_live_provider as provider
from tools.cnw_contract import ContractError


class GenericRunPreflightTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ExistingRunBindingTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.record = self.fixture.root / "08_review/run-preflight.json"
        self.report = self.fixture.report()
        self.record.write_bytes(encoded(self.report))

    def test_real_v2_report_passes_identity_but_self_accept_never_grants_authority(self):
        report, digest = policy.validate_per_run_bindings(self.record, self.fixture.path,
            self.fixture.run, self.fixture.root)
        self.assertEqual(report["bindings"], self.report["bindings"])
        self.assertEqual(digest, sha(self.record.read_bytes()))
        self.assertIs(report["provider_call_authorized"], False)
        self.report.update(status="ACCEPTED", reviewer="SELF", controller_acceptance_ref="OLD-J19")
        self.record.write_bytes(encoded(self.report))
        with self.assertRaisesRegex(ContractError, "W10_ATTESTATION_PENDING"):
            policy.verify_per_run_preflight_file(self.record, self.fixture.path,
                self.fixture.run, self.fixture.root)

    def signed_record(self):
        payload = {"purpose": "CNW_V2_RUN_PREFLIGHT", "decision": "ACCEPT",
            "bindings": self.report["bindings"], "identity_sha256": self.report["identity_sha256"],
            "provider_call_authorized": False}
        signature = self.fixture.root / "08_review/mock-controller.json"
        signature.write_bytes(encoded({"schema_version": "cnw_signed_controller_attestation_v1",
            "payload": payload, "signer_id": "MOCK_ONLY", "signature_base64": base64.b64encode(b"SIMULATED").decode()}))
        value = copy.deepcopy(self.report)
        value.update(controller_attestation_path=str(signature), controller_attestation_sha256=sha(signature.read_bytes()))
        self.record.write_bytes(encoded(value))
        expected = policy._canonical_bytes(payload)
        class MockOnlyVerifier:
            def verify(self, signer_id, message, signature_bytes):
                return signer_id == "MOCK_ONLY" and message == expected and signature_bytes == b"SIMULATED"
        return signature, MockOnlyVerifier()

    def test_simulated_signed_review_is_attested_with_provider_flag_still_false(self):
        signature, verifier = self.signed_record()
        attested, digest = policy.verify_per_run_preflight_file(self.record, self.fixture.path,
            self.fixture.run, self.fixture.root, verifier=verifier)
        self.assertEqual(attested["status"], "ATTESTED")
        self.assertIs(attested["provider_call_authorized"], False)
        self.assertEqual(digest, sha(signature.read_bytes()))
        # Exercise the real Provider review consumer with its separate Live
        # boundary closed. A test verifier cannot turn review into a fee grant.
        state = runner.load_state(self.fixture.run); state["mode"] = "live"
        with patch.object(policy, "verify_preflight_file", return_value=(attested, digest)), \
             patch.object(provider, "_reserve", side_effect=AssertionError("Review cannot reserve fees")):
            with self.assertRaisesRegex(ContractError, "LIVE_AUTHORIZATION_REQUIRED"):
                provider.verify_run_preflight(self.fixture.run, state, preflight_path=self.record)
        self.assertEqual(runner.load_state(self.fixture.run)["mode"], "offline")

    def test_wrong_run_project_policy_source_and_legacy_schema_replay_reject(self):
        for key, value in (("run_id", "FOREIGN-RUN"), ("project_instance_id", "FOREIGN-INSTANCE"),
                ("contract_sha256", "0" * 64), ("policy_version", "0" * 64),
                ("source_identity", {"unselected_source": True}), ("workflow_template_sha256", "0" * 64)):
            changed = copy.deepcopy(self.report); changed["bindings"][key] = value
            changed["identity_sha256"] = policy._canonical_sha256(changed["bindings"])
            self.record.write_bytes(encoded(changed))
            with self.subTest(key=key), self.assertRaises(ContractError):
                policy.validate_per_run_bindings(self.record, self.fixture.path, self.fixture.run, self.fixture.root)
        old = copy.deepcopy(self.report); old["schema_version"] = policy.PER_RUN_PREFLIGHT_SCHEMA
        self.record.write_bytes(encoded(old))
        with self.assertRaisesRegex(ContractError, "REVIEW_INVALID"):
            policy.validate_per_run_bindings(self.record, self.fixture.path, self.fixture.run, self.fixture.root)

    def test_offline_or_mode_changed_v2_rejects_before_slot_reserve_and_http(self):
        state_file = self.fixture.run / "run_state.json"
        original = state_file.read_bytes()
        for mode, error in (("offline", "OFFLINE_PROVIDER_FORBIDDEN"), ("live", "LIVE_AUTHORIZATION_REQUIRED")):
            state = json.loads(original); state["mode"] = mode
            state["provider_call_authorized"] = True  # A self-claim is never a user grant.
            state_file.write_bytes(encoded(state))
            unchanged = {str(path): path.read_bytes() for path in self.fixture.run.rglob("*") if path.is_file()}
            with patch.object(runner, "_p2_guard", side_effect=AssertionError("No slot or cost reservation")), \
                 patch.object(runner.httpx, "post", side_effect=AssertionError("No HTTP")):
                for entry in (runner.cnw_live_call, runner._cnw_live_call_in_slot):
                    with self.subTest(mode=mode, entry=entry.__name__), self.assertRaisesRegex(ContractError, error):
                        entry(self.fixture.run, stage="plot", role_id="plot_agent", messages=[], output_cap=100)
            self.assertEqual(unchanged, {str(path): path.read_bytes() for path in self.fixture.run.rglob("*") if path.is_file()})


if __name__ == "__main__":
    unittest.main()
