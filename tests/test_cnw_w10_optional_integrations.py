"""Synthetic offline regressions for optional W10 support integrations."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from tools import cnw_live_executor, cnw_live_provider, cnw_runner, cnw_w10_critics, cnw_w10_policy
from tools.cnw_contract import ContractError

ROOT = Path(__file__).resolve().parents[1]


class W10OptionalIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".w10-optional-", dir=ROOT / "workspace")
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name).resolve()
        self.run = self.project / "runs" / f"SYNTHETIC-{uuid.uuid4().hex[:8]}"
        self.run.mkdir(parents=True)
        self.preflight = self.project / "review.json"
        self.preflight.write_text("{}", encoding="utf-8")

    def write_contract(self, *, schema="cnw_work_unit_v2", nk="DISABLED", critics="DISABLED"):
        contract = {"schema_version": schema, "project_id": "SYNTHETIC-W10",
            "unit": {"id": "SYNTHETIC-UNIT", "kind": "scene"},
            "integrations": {"nk": nk, "critics": critics}}
        raw = json.dumps(contract, sort_keys=True).encode("utf-8")
        contract_path = self.project / "contracts" / "contract.json"
        contract_path.parent.mkdir(parents=True, exist_ok=True)
        contract_path.write_bytes(raw)
        run_contract = self.run / "artifacts" / "contract.json"
        run_contract.parent.mkdir(parents=True, exist_ok=True)
        run_contract.write_bytes(raw)
        state = {"run_id": self.run.name, "mode": "live", "fixture_only": False,
            "project_id": contract["project_id"], "work_id": "SYNTHETIC-UNIT",
            "contract_path": "contracts/contract.json",
            "contract_sha256": hashlib.sha256(raw).hexdigest(),
            "provider_requests": [], "stages": {"brief": {"status": "READY_FOR_EXECUTION",
                "fingerprint": "synthetic-fingerprint"}}}
        (self.run / "run_state.json").write_text(json.dumps(state), encoding="utf-8")
        return contract

    def test_nk_disabled_builds_brief_without_a_pov_stage_or_input(self):
        self.write_contract(nk="DISABLED")
        observed = {}

        def build_role_packet(role, contract_path, inputs, *, accepted_receipts, mode):
            observed["role"] = role
            observed["inputs"] = dict(inputs)
            observed["mode"] = mode
            return {"prompt": "Synthetic brief prompt", "input_names": sorted(inputs)}

        with patch("tools.cnw_roles.build_role_packet", side_effect=build_role_packet), \
             patch("tools.cnw_w10_policy.verify_preflight_file", return_value=({}, "a" * 64)):
            result = cnw_live_executor.prepare_role_request(self.run, self.project,
                role="brief", inputs={}, preflight_path=self.preflight)

        packet = json.loads((self.run / result["packet"]).read_text(encoding="utf-8"))
        self.assertEqual(observed, {"role": "brief", "inputs": {}, "mode": "live"})
        self.assertEqual(packet["messages"][1]["content"], '{"input_names": []}')
        self.assertNotIn("nk_reflection", packet["input_paths"])

    def test_nk_disabled_rejects_supplied_nk_material(self):
        self.write_contract(nk="DISABLED")
        with self.assertRaisesRegex(ContractError, "LIVE_NK_DISABLED_INPUT_FORBIDDEN"):
            cnw_live_executor.prepare_role_request(self.run, self.project, role="brief",
                inputs={"nk_reflection": self.preflight}, preflight_path=self.preflight)

    def test_enabled_or_v1_brief_keeps_historical_pov_requirement(self):
        for schema, nk in (("cnw_work_unit_v2", "ENABLED"), ("cnw_work_unit_v1", "DISABLED")):
            with self.subTest(schema=schema, nk=nk):
                self.write_contract(schema=schema, nk=nk)
                with self.assertRaisesRegex(ContractError, "LIVE_BRIEF_POV_NOT_ACCEPTED"):
                    cnw_live_executor.prepare_role_request(self.run, self.project,
                        role="brief", inputs={}, preflight_path=self.preflight)

    def test_disabled_critics_command_returns_before_stage_or_provider(self):
        self.write_contract(critics="DISABLED")
        with patch("tools.cnw_w10_critics.subprocess.run",
                   side_effect=AssertionError("disabled CritiCS must not spawn")):
            result = cnw_w10_critics.run_action(self.run, "plan-critique")
        self.assertEqual(result, {"status": "DISABLED", "action": "plan-critique",
            "provider_call_count": 0, "provider_call": "none"})
        self.assertFalse((ROOT / "runs" / f"{self.run.name}-critics-plan-critique").exists())

    def test_enabled_critics_requires_run_preflight_before_any_action(self):
        self.write_contract(critics="ENABLED")
        with patch("tools.cnw_w10_critics.subprocess.run",
                   side_effect=AssertionError("unpreflighted CritiCS must not spawn")):
            with self.assertRaisesRegex(ContractError, "LIVE_STAGE_NOT_AUTHORIZED_OR_READY"):
                cnw_w10_critics.run_action(self.run, "plan-critique")

    def test_critics_passes_explicit_per_run_preflight_to_shared_gate(self):
        self.write_contract(critics="ENABLED")
        observed = {}
        def capture_preflight(run, state, *, preflight_path=None):
            observed["run"] = run
            observed["preflight_path"] = preflight_path
            raise ContractError("LIVE_STAGE_NOT_AUTHORIZED_OR_READY", "synthetic preflight denied")
        with patch("tools.cnw_w10_critics.verify_run_preflight", side_effect=capture_preflight):
            with self.assertRaisesRegex(ContractError, "LIVE_STAGE_NOT_AUTHORIZED_OR_READY"):
                cnw_w10_critics.run_action(self.run, "plan-critique", preflight_path=self.preflight)
        self.assertEqual(observed, {"run": self.run, "preflight_path": self.preflight})

    def test_unknown_optional_integration_value_fails_closed(self):
        self.write_contract(nk="AUTO")
        with self.assertRaisesRegex(ContractError, "SUPPORT_INTEGRATION_CONFIG_INVALID"):
            cnw_live_executor._support_integration_mode(
                {"schema_version": "cnw_work_unit_v2", "integrations": {"nk": "AUTO"}}, "nk")

    def test_per_run_json_without_trusted_controller_attestation_is_blocked(self):
        self.write_contract(nk="DISABLED", critics="DISABLED")
        state_path = self.run / "run_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["stages"]["plot"] = {"status": "READY_FOR_EXECUTION", "fingerprint": "synthetic-plot"}
        state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
        preflight_path = self.project / "w10-preflight.json"
        observed = {"builder_called": False}

        def build_packet(*args, **kwargs):
            observed["builder_called"] = True
            raise AssertionError("unattested review must not reach request construction")

        for status in ("ACCEPTED", "UNREVIEWED"):
            preflight_path.write_text(json.dumps({
                "schema_version": cnw_w10_policy.PER_RUN_PREFLIGHT_SCHEMA,
                "status": status,
                "provider_call_authorized": False,
            }), encoding="utf-8")
            with patch("tools.cnw_roles.build_role_packet", side_effect=build_packet):
                with self.assertRaises(ContractError):
                    cnw_live_executor.prepare_role_request(
                        self.run, self.project, role="plot", inputs={}, preflight_path=preflight_path)
            self.assertFalse(observed["builder_called"])
            self.assertFalse((self.run / "artifacts/requests").exists())

            messages = [{"role": "user", "content": "synthetic no-cost check"}]
            input_sha = hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")).hexdigest()
            with patch.dict(os.environ, {"STORYSTUDIO_W10_PREFLIGHT_PATH": str(preflight_path)}, clear=True), \
                 patch("tools.cnw_live_provider._reserve", side_effect=AssertionError("unattested review reserved cost")):
                with self.assertRaises(ContractError):
                    cnw_live_provider.complete(self.run, stage="plot", messages=messages,
                        input_sha256=input_sha, input_token_cap=100, output_token_cap=100)

    def test_stage_self_asserted_acceptance_json_is_not_trusted(self):
        self.write_contract()
        state = {"run_id": self.run.name, "contract_sha256": "a" * 64,
            "contract_path": "contracts/contract.json",
            "stages": {"plot": {"fingerprint": "f" * 64}},
            "pending_role_outputs": {"plot": {"content": "synthetic prose",
                "content_sha256": hashlib.sha256(b"synthetic prose").hexdigest(),
                "artifact_content": "synthetic artifact",
                "artifact_content_sha256": hashlib.sha256(b"synthetic artifact").hexdigest(),
                "packet_path": "artifacts/requests/plot.json", "request_id": "req-1",
                "provider_request_id": "provider-1", "validation": {}}},
            "provider_requests": [{"request_id": "req-1", "provider_request_id": "provider-1",
                "mode": "LIVE", "fixture_only": False,  # Fictional shape only; never a Live receipt.
                "stage": "plot", "output_sha256": hashlib.sha256(b"synthetic prose").hexdigest(),
                "input_sha256": "b" * 64, "stage_fingerprint": "f" * 64}]}
        packet_path = self.run / "artifacts/requests/plot.json"
        packet_path.parent.mkdir(parents=True)
        packet_path.write_text(json.dumps({"role": "plot", "project_root": str(self.project),
            "preflight_path": str(self.preflight), "input_paths": {}, "input_sha256": "b" * 64}),
            encoding="utf-8")
        review = self.project / "08_review" / "stage.json"
        review.parent.mkdir(parents=True)
        review.write_text(json.dumps({"schema_version": "cnw_controller_stage_acceptance_v1",
            "decision": "ACCEPT", "controller": "P3.1_W10_INDEPENDENT_CONTROLLER",
            "run_id": self.run.name, "stage": "plot", "controller_acceptance_ref": "SELF-CLAIM"}),
            encoding="utf-8")
        offline_report = {"status": "OFFLINE_BINDINGS_VALIDATED", "bindings": {"run_id": self.run.name},
            "identity_sha256": "c" * 64}
        with patch("tools.cnw_live_executor.safe_run", return_value=self.run), \
             patch("tools.cnw_live_executor.load_state", return_value=state), \
             patch("tools.cnw_w10_policy.validate_per_run_bindings", return_value=(offline_report, "d" * 64)):
            with self.assertRaisesRegex(ContractError, "W10_ATTESTATION_PENDING"):
                cnw_live_executor.accept_controller_role_output(
                    self.run, stage="plot", evidence_path=review)
        self.assertFalse((self.run / "artifacts/stages/plot.md").exists())


if __name__ == "__main__":
    unittest.main()
