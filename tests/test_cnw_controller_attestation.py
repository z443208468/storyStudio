"""Canonical signed payloads retain JSON types; test verifier grants no Live permission."""
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.cnw_contract import ContractError
from tools import cnw_w10_policy as policy


class StrictControllerAttestationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="signed-fixture-")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "mock-controller.json"
        self.payload = {"purpose": "CNW_V2_RUN_PREFLIGHT", "decision": "ACCEPT",
            "provider_call_authorized": False, "bindings": {"project_id": "Fictional", "run_id": "MOCK-RUN",
            "contract_sha256": "a" * 64, "boolean_requirement": True, "nullable_requirement": None}}
        self.calls = []
        owner = self
        class MockOnlyVerifier:
            def verify(self, signer_id, message, signature):
                owner.calls.append(message)
                return (signer_id == "MOCK_ONLY" and signature == b"SIMULATED"
                        and message == policy._canonical_bytes(owner.payload))
        self.verifier = MockOnlyVerifier()

    def write(self, payload):
        self.path.write_text(json.dumps({"schema_version": "cnw_signed_controller_attestation_v1",
            "payload": payload, "signer_id": "MOCK_ONLY",
            "signature_base64": base64.b64encode(b"SIMULATED").decode()}, ensure_ascii=False), encoding="utf-8")

    def test_same_actual_canonical_bytes_are_compared_then_passed_to_verifier(self):
        self.write(self.payload)
        document, digest = policy.verify_controller_attestation_document(self.path,
            expected_payload=self.payload, verifier=self.verifier)
        self.assertIs(document["payload"]["provider_call_authorized"], False)
        self.assertEqual(len(digest), 64)
        self.assertEqual(self.calls, [policy._canonical_bytes(self.payload)])

    def test_type_alias_replay_and_nonfinite_changes_never_reach_signature_verifier(self):
        for field, value in (("provider_call_authorized", 0), ("purpose", "W10_PER_RUN_PREFLIGHT"),
                ("run_id", "OTHER"), ("project_id", "OTHER"), ("contract_sha256", "b" * 64),
                ("boolean_requirement", 1), ("nullable_requirement", float("nan"))):
            altered = copy.deepcopy(self.payload)
            target = altered if field in altered else altered["bindings"]
            target[field] = value
            self.write(altered)
            with self.subTest(field=field), self.assertRaises(ContractError):
                policy.verify_controller_attestation_document(self.path,
                    expected_payload=self.payload, verifier=self.verifier)
            self.assertEqual(self.calls, [])
        self.write(self.payload)
        raw = self.path.read_text(encoding="utf-8").replace('"decision": "ACCEPT"', '"decision": "RETURN", "decision": "ACCEPT"')
        self.path.write_text(raw, encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "EVIDENCE_INVALID"):
            policy.verify_controller_attestation_document(self.path, expected_payload=self.payload, verifier=self.verifier)
        self.assertEqual(self.calls, [])

    def test_pending_deployment_dependency_is_not_misreported_as_signature_failure(self):
        self.write(self.payload)
        class PendingVerifier:
            def verify(self, *args):
                raise ContractError("W10_ATTESTATION_PENDING", "deferred dependency is untrusted")
        with self.assertRaisesRegex(ContractError, "W10_ATTESTATION_PENDING"):
            policy.verify_controller_attestation_document(self.path, expected_payload=self.payload, verifier=PendingVerifier())


if __name__ == "__main__":
    unittest.main()
