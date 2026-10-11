"""Synthetic offline regressions for optional W10 support integrations."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from tools import cnw_live_executor, cnw_w10_critics
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


if __name__ == "__main__":
    unittest.main()
