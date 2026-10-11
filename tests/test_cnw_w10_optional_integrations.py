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

        def build_role_packet(role, contract_path, inputs, **kwargs):
            observed["role"] = role
            observed["inputs"] = dict(inputs)
            return {"prompt": "Synthetic brief prompt", "input_names": sorted(inputs)}

        with patch("tools.cnw_roles.build_role_packet", side_effect=build_role_packet), \
             patch("tools.cnw_w10_policy.verify_preflight_file", return_value=({}, "a" * 64)):
            result = cnw_live_executor.prepare_role_request(self.run, self.project,
                role="brief", inputs={}, preflight_path=self.preflight)

        packet = json.loads((self.run / result["packet"]).read_text(encoding="utf-8"))
        self.assertEqual(observed, {"role": "brief", "inputs": {}})
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

    def test_unknown_optional_integration_value_fails_closed(self):
        self.write_contract(nk="AUTO")
        with self.assertRaisesRegex(ContractError, "SUPPORT_INTEGRATION_CONFIG_INVALID"):
            cnw_live_executor._support_integration_mode(
                {"schema_version": "cnw_work_unit_v2", "integrations": {"nk": "AUTO"}}, "nk")

    def test_per_run_preflight_is_consumed_by_request_builder_and_blocks_provider_when_not_authorized(self):
        contract = self.write_contract(nk="DISABLED", critics="DISABLED")
        contract["source"] = {"source_file_sha256": "a" * 64, "source_manifest_sha256": "b" * 64}
        contract["unit"]["policy_sha256"] = hashlib.sha256(
            (ROOT / "config/cnw_production_policy.json").read_bytes()).hexdigest()
        raw_contract = json.dumps(contract, sort_keys=True).encode("utf-8")
        contract_path = self.project / "contracts" / "contract.json"
        run_contract_path = self.run / "artifacts" / "contract.json"
        contract_path.write_bytes(raw_contract)
        run_contract_path.write_bytes(raw_contract)
        state_path = self.run / "run_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.update({"project_id": contract["project_id"], "work_id": contract["unit"]["id"],
            "contract_path": "contracts/contract.json", "contract_sha256": hashlib.sha256(raw_contract).hexdigest(),
            "workflow_template_sha256": hashlib.sha256(cnw_runner.WORKFLOW_PATH.read_bytes()).hexdigest()})
        state["stages"]["plot"] = {"status": "READY_FOR_EXECUTION", "fingerprint": "synthetic-plot-fingerprint"}
        state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")

        identity = {"schema_version": "cnw_project_identity_v1", "project_id": contract["project_id"],
            "project_instance_id": "synthetic-instance-001"}
        identity_raw = json.dumps(identity, sort_keys=True).encode("utf-8")
        (self.project / "project_identity.json").write_bytes(identity_raw)
        controller_ref = "SYNTHETIC-PER-RUN-W10-ACCEPT-01"
        controller = {"schema_version": "cnw_w10_controller_verdict_v1", "status": "ACCEPTED",
            "scope": "W10_SINGLE_SCENE", "controller_acceptance_ref": controller_ref,
            "provider_call_authorized": False, "identity_kind": "NATIVE",
            "project_instance_id": identity["project_instance_id"], "project_id": contract["project_id"],
            "run_id": self.run.name, "work_id": contract["unit"]["id"],
            "contract_sha256": state["contract_sha256"], "source_file_sha256": contract["source"]["source_file_sha256"],
            "source_manifest_sha256": contract["source"]["source_manifest_sha256"],
            "policy_sha256": contract["unit"]["policy_sha256"],
            "workflow_template_sha256": state["workflow_template_sha256"],
            "project_identity_sha256": hashlib.sha256(identity_raw).hexdigest()}
        controller_path = self.project / "controller-review.json"
        controller_path.write_text(json.dumps(controller, sort_keys=True), encoding="utf-8")
        preflight = {"schema_version": cnw_w10_policy.PER_RUN_PREFLIGHT_SCHEMA,
            "status": "ACCEPTED", "scope": "W10_SINGLE_SCENE", "controller_acceptance_ref": controller_ref,
            "controller_evidence_path": str(controller_path),
            "controller_evidence_sha256": hashlib.sha256(controller_path.read_bytes()).hexdigest(),
            "provider_call_authorized": False, "identity_kind": "NATIVE",
            "project_instance_id": identity["project_instance_id"],
            "project_identity_sha256": hashlib.sha256(identity_raw).hexdigest(),
            "project_id": contract["project_id"], "run_id": self.run.name,
            "work_id": contract["unit"]["id"], "contract_sha256": state["contract_sha256"],
            "source_file_sha256": contract["source"]["source_file_sha256"],
            "source_manifest_sha256": contract["source"]["source_manifest_sha256"],
            "policy_sha256": contract["unit"]["policy_sha256"],
            "workflow_template_sha256": state["workflow_template_sha256"]}
        preflight_path = self.project / "w10-preflight.json"
        preflight_path.write_text(json.dumps(preflight, sort_keys=True), encoding="utf-8")
        observed = {}

        def build_packet(role, contract_file, inputs, **kwargs):
            observed["preflight"] = kwargs["w10_preflight"]
            return {"prompt": "Synthetic isolated Plot request", "allowed_inputs": sorted(inputs)}

        with patch("tools.cnw_roles.build_role_packet", side_effect=build_packet):
            result = cnw_live_executor.prepare_role_request(self.run, self.project, role="plot",
                inputs={}, preflight_path=preflight_path)
        packet = json.loads((self.run / result["packet"]).read_text(encoding="utf-8"))
        self.assertEqual(observed["preflight"]["controller_acceptance_ref"], controller_ref)
        self.assertEqual(packet["preflight_evidence_sha256"], hashlib.sha256(preflight_path.read_bytes()).hexdigest())

        messages = [{"role": "user", "content": "synthetic no-cost check"}]
        input_sha = hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode("utf-8")).hexdigest()
        with patch.dict(os.environ, {"STORYSTUDIO_W10_PREFLIGHT_PATH": str(preflight_path)}, clear=True), \
             patch("tools.cnw_live_provider._reserve", side_effect=AssertionError("unauthorized preflight reserved cost")):
            with self.assertRaisesRegex(ContractError, "LIVE_STAGE_NOT_AUTHORIZED_OR_READY"):
                cnw_live_provider.complete(self.run, stage="plot", messages=messages, input_sha256=input_sha,
                    input_token_cap=100, output_token_cap=100)

        mismatched_policy = dict(contract)
        mismatched_policy["unit"] = {**contract["unit"], "policy_sha256": "e" * 64}
        mismatched_raw = json.dumps(mismatched_policy, sort_keys=True).encode("utf-8")
        contract_path.write_bytes(mismatched_raw)
        run_contract_path.write_bytes(mismatched_raw)
        state["contract_sha256"] = hashlib.sha256(mismatched_raw).hexdigest()
        state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "PRODUCTION_POLICY_IDENTITY_MISMATCH"):
            cnw_w10_policy.verify_preflight_file(preflight_path, contract_path,
                run_dir=self.run, project_root=self.project)

        contract_path.write_bytes(raw_contract)
        run_contract_path.write_bytes(raw_contract)
        state["contract_sha256"] = hashlib.sha256(raw_contract).hexdigest()
        state["workflow_template_sha256"] = "f" * 64
        state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "CNW_METHOD_IDENTITY_MISMATCH"):
            cnw_w10_policy.verify_preflight_file(preflight_path, contract_path,
                run_dir=self.run, project_root=self.project)


if __name__ == "__main__":
    unittest.main()
