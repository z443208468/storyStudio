"""Rejected stage signatures/receipts must not write official draft artifacts."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests import test_cnw_live_provider as provider_fixtures
from tests.test_cnw_input_pack import encoded, sha
from tools import cnw_live_executor as executor, cnw_live_provider as provider
from tools.cnw_contract import ContractError


class StageReceiptBoundaries(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="stage-attestation-fictional-")
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name).resolve()
        self.run = self.project / "runs/MOCK-STAGE"
        self.run.mkdir(parents=True)
        content, output = "SIMULATED_PROVIDER_TEXT", "SIMULATED_DRAFT_TEXT"
        self.pending = {"content": content, "content_sha256": sha(content.encode()),
            "artifact_content": output, "artifact_content_sha256": sha(output.encode()),
            "packet_path": "artifacts/requests/draft.json", "request_id": "MOCK-REQ",
            "provider_request_id": "SIMULATED-PROVIDER", "validation": {"status": "CONTENT_VALID"}}
        self.receipt = {"request_id": "MOCK-REQ", "provider_request_id": "SIMULATED-PROVIDER", "stage": "draft",
            "output_sha256": self.pending["content_sha256"], "input_sha256": "b" * 64,
            "stage_fingerprint": "f" * 64, "mode": "LIVE", "fixture_only": False}
        self.state = {"run_id": "MOCK-STAGE", "contract_sha256": "a" * 64,
            "contract_path": "contracts/mock.json", "stages": {"draft": {"fingerprint": "f" * 64}},
            "pending_role_outputs": {"draft": self.pending}, "provider_requests": [self.receipt]}
        (self.run / "run_state.json").write_bytes(encoded(self.state))
        packet = self.run / self.pending["packet_path"]
        packet.parent.mkdir(parents=True)
        packet.write_bytes(encoded({"role": "draft", "project_root": str(self.project),
            "preflight_path": str(self.project / "preflight.json"), "input_paths": {}, "input_sha256": "b" * 64}))
        self.evidence = self.project / "08_review/mock-signed.json"
        self.evidence.parent.mkdir()
        self.evidence.write_bytes(b"SIMULATED_SIGNATURE_FIXTURE")
        (self.run / "artifacts/stages").mkdir()

    def bytes(self):
        return {str(path): path.read_bytes() for path in self.project.rglob("*") if path.is_file()}

    def invoke(self):
        # This narrow stage boundary fixture substitutes identity/signature
        # services. It never materializes a successful stage or claims Live.
        with patch.object(executor, "safe_run", return_value=self.run), \
             patch("tools.cnw_w10_policy.validate_per_run_bindings", return_value=({"bindings": {}, "identity_sha256": "c" * 64}, "d" * 64)):
            return executor.accept_controller_role_output(self.run, stage="draft", evidence_path=self.evidence)

    def test_mock_missing_and_numeric_fixture_flags_block_before_signature_or_any_write(self):
        for fields in ({"mode": "MOCK_ONLY", "fixture_only": True}, {"mode": "LIVE", "fixture_only": 0},
                {"mode": "LIVE", "fixture_only": None}, {"mode": "SIMULATED", "fixture_only": False}, {}):
            state = copy.deepcopy(self.state)
            state["provider_requests"][0].pop("mode")
            state["provider_requests"][0].pop("fixture_only")
            state["provider_requests"][0].update(fields)
            (self.run / "run_state.json").write_bytes(encoded(state))
            before = self.bytes()
            with self.subTest(fields=fields), \
                 patch("tools.cnw_w10_policy.verify_controller_attestation_document", side_effect=AssertionError("No signature evaluation for simulated receipt")), \
                 self.assertRaisesRegex(ContractError, "LIVE_MOCK_PROVIDER_ACCEPTANCE_FORBIDDEN"):
                self.invoke()
            self.assertEqual(self.bytes(), before)

    def test_lower_rejection_does_not_prewrite_draft_and_collision_preserves_bytes(self):
        before = self.bytes()
        with patch("tools.cnw_w10_policy.verify_controller_attestation_document", return_value=({"signer_id": "MOCK_ONLY"}, "e" * 64)), \
             patch("tools.cnw_roles.build_role_packet", return_value={}), \
             patch.object(executor, "accept_validated_stage", side_effect=ContractError("SIMULATED_LOWER_REJECTION", "fixture")), \
             self.assertRaisesRegex(ContractError, "SIMULATED_LOWER_REJECTION"):
            self.invoke()
        self.assertEqual(self.bytes(), before)
        target = self.run / "artifacts/stages/draft-prose.md"
        target.write_bytes(b"PRESERVE_ORIGINAL_FICTIONAL_ARTIFACT")
        before = self.bytes()
        with patch("tools.cnw_w10_policy.verify_controller_attestation_document", return_value=({"signer_id": "MOCK_ONLY"}, "e" * 64)), \
             patch("tools.cnw_roles.build_role_packet", return_value={}), \
             patch.object(executor, "accept_validated_stage", side_effect=AssertionError("Collision must reject first")), \
             self.assertRaisesRegex(ContractError, "LIVE_STAGE_ARTIFACT_COLLISION"):
            self.invoke()
        self.assertEqual(self.bytes(), before)


class LowerStageReceiptBoundaries(unittest.TestCase):
    def test_direct_lower_acceptance_rejects_missing_numeric_or_mock_flags(self):
        fixture = provider_fixtures.LiveProviderTransportTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        state_path = fixture.run / "run_state.json"
        original = json.loads(state_path.read_bytes())
        content = "SIMULATED_OUTPUT"
        for fields in ({}, {"mode": "LIVE", "fixture_only": 0}, {"mode": "MOCK_ONLY", "fixture_only": True}):
            state = copy.deepcopy(original)
            state["provider_requests"] = [{"stage": "plot", "output_sha256": sha(content.encode()), **fields}]
            state_path.write_bytes(encoded(state))
            before = state_path.read_bytes()
            with self.subTest(fields=fields), self.assertRaisesRegex(ContractError, "LIVE_MOCK_PROVIDER_ACCEPTANCE_FORBIDDEN"):
                provider.accept_validated_stage(fixture.run, stage="plot", content=content,
                    validation={"status": "ROLE_OUTPUT_VALID"})
            self.assertEqual(state_path.read_bytes(), before)
            self.assertFalse((fixture.run / "artifacts/stages/plot.json").exists())


if __name__ == "__main__":
    unittest.main()
