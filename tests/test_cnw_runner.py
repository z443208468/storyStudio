from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from tools import cnw_runner
from tools.cnw_contract import ContractError


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "workspace/cangqi/contracts/CQ-J19-INSERT-01.work_unit_contract.json"


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cnw-runner-")
        self.base = Path(self.temp.name)
        (self.base / "runs").mkdir()
        self.project = self.base
        (self.base / "config").mkdir()
        (self.base / "tools").mkdir()
        (self.base / "config/production.example.json").write_text(json.dumps({"provider": {"max_in_flight": 1}, "cost_guard": {"persist_across_run_ids": True}}), encoding="utf-8")
        (self.base / "tools/p2_cost_guard.py").write_text("# shared cost guard fixture", encoding="utf-8")
        self.contract_dir = self.project / "contracts"
        self.contract_dir.mkdir()
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.contract["project_id"] = "FICT_CNW_TEST"
        self.root_patch = patch.object(cnw_runner, "ROOT", self.base)
        self.workflow_patch = patch.object(cnw_runner, "WORKFLOW_PATH", ROOT / "runtime/reference/cnw_97ad71fe5e5e/templates/config/workflow.template.yml")
        self.root_patch.start()
        self.workflow_patch.start()
        self._produce_contract(self.contract, "FICT_SCENE_A", "fixture-a.json")

    def tearDown(self):
        self.workflow_patch.stop()
        self.root_patch.stop()
        self.temp.cleanup()

    def _write_contract(self, value, name):
        path = self.contract_dir / name
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _produce_contract(self, value, run_id, name):
        path = self._write_contract(value, name)
        args = argparse.Namespace(run_id=run_id, work_id=value["unit"]["id"], unit="scene", contract=str(path), project_root=str(self.project), mode="offline")
        return cnw_runner.produce(args)

    def _fixture_first_roles(self, run_id):
        contract = json.loads((self.base / "runs" / run_id / "artifacts/contract.json").read_text(encoding="utf-8"))
        for stage in ("plot", "cards", "brief"):
            result = cnw_runner.step(argparse.Namespace(run_id=run_id, work_id=None, stage=stage, input=None))
            fixture = self.base / "runs" / run_id / "artifacts" / f"{stage}-fixture.json"
            fixture.write_text(json.dumps({"fixture_only": True, "stage": stage, "work_id": contract["unit"]["id"], "target_visible_chars": contract["unit"]["target_visible_chars"], "beat_budgets": [beat["budget_visible_chars"] for beat in contract["story"]["required_beats"]]}, ensure_ascii=False), encoding="utf-8")
            cnw_runner.mark_stage(argparse.Namespace(run_id=run_id, stage=stage, accept_fixture=str(fixture)))
        return cnw_runner.show_run(argparse.Namespace(run_id=run_id))

    def test_different_new_ids_create_independent_contract_bound_runs(self):
        first = cnw_runner.show_run(argparse.Namespace(run_id="FICT_SCENE_A"))
        other = json.loads(json.dumps(self.contract))
        other["unit"]["id"] = "FICT_SCENE_B"
        other["unit"]["target_visible_chars"] = 1800
        other["unit"]["min_visible_chars"] = 1500
        other["unit"]["max_visible_chars"] = 2100
        for beat, amount in zip(other["story"]["required_beats"], (300, 500, 600, 400)):
            beat["budget_visible_chars"] = amount
        created = self._produce_contract(other, "FICT_SCENE_B", "fixture-b.json")
        second = cnw_runner.show_run(argparse.Namespace(run_id="FICT_SCENE_B"))
        self.assertEqual(created["status"], "RUN_CREATED")
        self.assertNotEqual(first["contract_sha256"], second["contract_sha256"])
        self.assertTrue((self.base / "runs/FICT_SCENE_A/artifacts/contract.json").is_file())
        self.assertTrue((self.base / "runs/FICT_SCENE_B/artifacts/contract.json").is_file())
        first = self._fixture_first_roles("FICT_SCENE_A")
        second = self._fixture_first_roles("FICT_SCENE_B")
        for stage in ("plot", "cards", "brief"):
            self.assertEqual(first["stages"][stage], "ACCEPTED")
            self.assertEqual(second["stages"][stage], "ACCEPTED")
        self.assertNotEqual((self.base / "runs/FICT_SCENE_A/artifacts/plot-fixture.json").read_bytes(), (self.base / "runs/FICT_SCENE_B/artifacts/plot-fixture.json").read_bytes())

    def test_changed_contract_invalidates_old_cache_without_overwriting_run(self):
        original_hash = cnw_runner.show_run(argparse.Namespace(run_id="FICT_SCENE_A"))["contract_sha256"]
        old_artifact = self.base / "runs/FICT_SCENE_A/artifacts/contract.json"
        original_artifact_hash = cnw_runner.sha(old_artifact.read_bytes())
        cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="plot", input=None))
        changed = json.loads(json.dumps(self.contract))
        changed["story"]["reader_reward"] += " Revised contract."
        self._produce_contract(changed, "FICT_SCENE_A-R2", "fixture-a-revised.json")
        old_state = cnw_runner.load_state(self.base / "runs/FICT_SCENE_A")
        self.assertEqual(old_state["status"], "INVALIDATED")
        self.assertEqual(old_state["stages"]["plot"]["status"], "INVALIDATED")
        self.assertEqual(old_state["contract_sha256"], original_hash)
        self.assertEqual(cnw_runner.sha(old_artifact.read_bytes()), original_artifact_hash)

    def test_stage_requests_are_ordered_resumable_and_history_never_claims_live(self):
        with patch.object(cnw_runner, "ROOT", self.base):
            ready = cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="plot", input=None))
            self.assertEqual(ready["status"], "READY_FOR_EXECUTION")
            with self.assertRaisesRegex(ContractError, "EDITORIAL_CANDIDATE_NOT_READY"):
                cnw_runner.review_run(argparse.Namespace(run_id="FICT_SCENE_A"))
            candidate = self.base / "runs/FICT_SCENE_A/artifacts/mock-draft.md"
            candidate.write_text("MOCK_ONLY draft", encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "MOCK_CANDIDATE_CANNOT_REQUEST_EDITORIAL_REVIEW"):
                cnw_runner.register_editorial_candidate(argparse.Namespace(run_id="FICT_SCENE_A", candidate=str(candidate)))
            resumed = cnw_runner.show_run(argparse.Namespace(run_id="FICT_SCENE_A"))
            self.assertEqual(resumed["stages"]["plot"], "READY_FOR_EXECUTION")
            history = cnw_runner.verify_history(argparse.Namespace(run_id="FICT_SCENE_A"))
            self.assertEqual(history["status"], "HISTORICAL_EVIDENCE_FOUND")
            with self.assertRaisesRegex(ContractError, "LIVE_PROVIDER_EVIDENCE_MISSING"):
                cnw_runner.verify_live(argparse.Namespace(run_id="FICT_SCENE_A"))
            state = cnw_runner.load_state(self.base / "runs/FICT_SCENE_A")
            state["provider_requests"] = [{"stage": "lens5", "mode": "MOCK_ONLY", "provider_request_id": "mock-1"}]
            cnw_runner.save_state(self.base / "runs/FICT_SCENE_A", state)
            with self.assertRaisesRegex(ContractError, "MOCK_RECEIPT_CANNOT_PROVE_LIVE"):
                cnw_runner.verify_live(argparse.Namespace(run_id="FICT_SCENE_A"))
            state["stages"]["re-review"]["status"] = "ACCEPTED"
            cnw_runner.save_state(self.base / "runs/FICT_SCENE_A", state)
            with self.assertRaisesRegex(ContractError, "EXTERNAL_REVIEW_EVIDENCE_REQUIRED"):
                cnw_runner.promote_run(argparse.Namespace(run_id="FICT_SCENE_A"))
            with self.assertRaisesRegex(ContractError, "STAGE_DEPENDENCY_NOT_ACCEPTED"):
                cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="cards", input=None))

    def test_prompt_change_invalidates_only_affected_stage_and_preserves_old_artifact(self):
        prompt_root = self.base / "prompts"
        prompt_root.mkdir()
        prompt = prompt_root / "plot.md"
        prompt.write_text("plot prompt v1", encoding="utf-8")
        with patch.object(cnw_runner, "PROMPT_ROOT", prompt_root):
            first = cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="plot", input=None))
            first_path = self.base / "runs/FICT_SCENE_A" / first["artifact"]
            first_hash = cnw_runner.sha(first_path.read_bytes())
            prompt.write_text("plot prompt v2", encoding="utf-8")
            second = cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="plot", input=None))
            second_path = self.base / "runs/FICT_SCENE_A" / second["artifact"]
            self.assertNotEqual(first["fingerprint"], second["fingerprint"])
            self.assertNotEqual(first_path, second_path)
            self.assertTrue(first_path.is_file())
            self.assertEqual(cnw_runner.sha(first_path.read_bytes()), first_hash)
            record = cnw_runner.load_state(self.base / "runs/FICT_SCENE_A")["stages"]["plot"]
            self.assertEqual(len(record["invalidated_attempts"]), 1)
            self.assertEqual(record["status"], "READY_FOR_EXECUTION")
            self.assertEqual(cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="plot", input=None))["status"], "STAGE_REUSED")

    def test_workflow_template_change_invalidates_stage_and_downstream_only(self):
        self._fixture_first_roles("FICT_SCENE_A")
        run_path = self.base / "runs/FICT_SCENE_A"
        state = cnw_runner.load_state(run_path)
        prior_cards_fingerprint = state["stages"]["cards"]["fingerprint"]
        prior_brief_artifact = state["stages"]["brief"]["artifact"]["path"]
        state["workflow_template_sha256"] = "changed-pinned-workflow-hash"
        cnw_runner.save_state(run_path, state)
        result = cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="cards", input=None))
        refreshed = cnw_runner.load_state(run_path)
        self.assertEqual(refreshed["stages"]["plot"]["status"], "ACCEPTED")
        self.assertEqual(refreshed["stages"]["cards"]["status"], "READY_FOR_EXECUTION")
        self.assertNotEqual(refreshed["stages"]["cards"]["fingerprint"], prior_cards_fingerprint)
        self.assertEqual(refreshed["stages"]["brief"]["status"], "INVALIDATED")
        self.assertTrue((run_path / prior_brief_artifact).is_file())
        self.assertEqual(result["status"], "READY_FOR_EXECUTION")

    def test_run_id_collision_and_path_traversal_fail_closed(self):
        with patch.object(cnw_runner, "ROOT", self.base):
            args = argparse.Namespace(run_id="FICT_SCENE_A", work_id=self.contract["unit"]["id"], unit="scene", contract=str(self.contract_dir / "fixture-a.json"), project_root=str(self.project), mode="offline")
            with self.assertRaisesRegex(ContractError, "RUN_ID_COLLISION"):
                cnw_runner.produce(args)
            with self.assertRaisesRegex(ContractError, "VALID_RUN_ID_REQUIRED"):
                cnw_runner.run_path("../outside")

    def test_live_mode_is_gated_before_creating_a_run(self):
        args = argparse.Namespace(run_id="NO-LIVE-CALL", work_id=self.contract["unit"]["id"], unit="scene", contract=str(self.contract_dir / "fixture-a.json"), project_root=str(self.project), mode="live")
        with self.assertRaisesRegex(ContractError, "LIVE_EXECUTOR_NOT_AVAILABLE"):
            cnw_runner.produce(args)
        self.assertFalse((self.base / "runs/NO-LIVE-CALL").exists())

    def test_live_candidate_requires_complete_contract_pipeline(self):
        run = self.base / "runs/FICT_SCENE_A"
        state = cnw_runner.load_state(run)
        state["mode"] = "live"
        state["fixture_only"] = False
        state["provider_requests"] = [{"stage": "plot", "mode": "live"}]
        cnw_runner.save_state(run, state)
        with self.assertRaisesRegex(ContractError, "LIVE_PIPELINE_INCOMPLETE"):
            cnw_runner.register_editorial_candidate(argparse.Namespace(run_id="FICT_SCENE_A", candidate="draft.md"))

    def test_raw_provider_payload_must_match_receipt_fields(self):
        raw = self.base / "raw.json"
        receipt = {"request_id": "req-1", "provider_request_id": "provider-1", "model": "deepseek-flash", "finish_reason": "stop"}
        usage = {"prompt_tokens": 12, "completion_tokens": 8}
        body = {"id": "provider-1", "model": "deepseek-flash", "choices": [{"finish_reason": "stop"}], "usage": usage}
        raw.write_text(json.dumps({"request_id": "req-1", "status": 200, "requested_model": "deepseek-flash", "response": body}), encoding="utf-8")
        cnw_runner._validate_raw_live_response(raw, receipt, usage, 1)
        body["id"] = "other-provider"
        raw.write_text(json.dumps({"request_id": "req-1", "status": 200, "requested_model": "deepseek-flash", "response": body}), encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "LIVE_RAW_RESPONSE_RECEIPT_MISMATCH"):
            cnw_runner._validate_raw_live_response(raw, receipt, usage, 1)

    def test_live_review_coverage_requires_five_lenses_and_three_verifiers(self):
        lenses = [
            {"stage": "lens5", "lens_id": name}
            for name in ("style", "character", "plot", "canon", "story_specific")
        ]
        verifiers = [
            {"stage": "verifier3", "verifier_id": f"verifier_{number}"}
            for number in range(1, 4)
        ]
        cnw_runner._validate_review_call_coverage(lenses + verifiers)
        with self.assertRaisesRegex(ContractError, "LIVE_REVIEW_CALL_SET_INCOMPLETE"):
            cnw_runner._validate_review_call_coverage(lenses[:-1] + verifiers)
        duplicate = lenses[:-1] + [{"stage": "lens5", "lens_id": "canon"}] + verifiers
        with self.assertRaisesRegex(ContractError, "LIVE_REVIEW_CALL_SET_INCOMPLETE"):
            cnw_runner._validate_review_call_coverage(duplicate)
        with self.assertRaisesRegex(ContractError, "LIVE_REVIEW_CALL_SET_INCOMPLETE"):
            cnw_runner._validate_review_call_coverage(lenses + verifiers[:-1] + [verifiers[-2]])

    def test_accepted_review_votes_must_match_verified_raw_response_content(self):
        run=self.base/"runs/R1"; artifacts=run/"artifacts"; artifacts.mkdir(parents=True)
        review_rows=[]; provider_rows=[]
        for lens in ("style","character","plot","canon","story_specific"):
            pid=f"L-{lens}"; review_rows.append({"stage":"lens5","lens_id":lens,"provider_request_id":pid})
            provider_rows.append({"stage":"lens5","lens_id":lens,"provider_request_id":pid})
        for i,verifier in enumerate(("verifier_1","verifier_2","verifier_3"),1):
            pid=f"V-{i}"; content=json.dumps({"verifier_id":verifier,"votes":[{"finding_id":"I1","verdict":"not_refuted"}]},sort_keys=True)
            raw={"id":pid,"model":"deepseek-flash","choices":[{"finish_reason":"stop","message":{"content":content}}],"usage":{"prompt_tokens":10,"completion_tokens":10}}
            path=artifacts/f"{pid}.json"; path.write_text(json.dumps(raw),encoding="utf-8")
            review_rows.append({"stage":"verifier3","verifier_id":verifier,"provider_request_id":pid,"response_content":content,"output_sha256":hashlib.sha256(content.encode()).hexdigest()})
            provider_rows.append({"stage":"verifier3","verifier_id":verifier,"provider_request_id":pid,"raw_response_path":path.relative_to(run).as_posix()})
        accepted={"provider_requests":review_rows}
        cnw_runner.bind_accepted_review_outputs(accepted,provider_rows,run)
        accepted["provider_requests"][-1]["response_content"]="{\"votes\":[]}"
        with self.assertRaisesRegex(ContractError,"ACCEPTED_VERIFIER_OUTPUT_MISMATCH"):
            cnw_runner.bind_accepted_review_outputs(accepted,provider_rows,run)

    def test_same_run_stage_mutations_are_serialized(self):
        path = self.base / "runs/FICT_SCENE_A"
        active = 0
        maximum = 0
        guard = threading.Lock()

        def update():
            nonlocal active, maximum
            with cnw_runner.locked_run(path):
                with guard:
                    active += 1
                    maximum = max(maximum, active)
                time.sleep(0.03)
                with guard:
                    active -= 1

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: update(), range(2)))
        self.assertEqual(maximum, 1)

    def test_stage_inputs_reject_absolute_escape_and_symlink(self):
        run_dir = self.base / "runs/FICT_SCENE_A"
        outside = self.base / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "STAGE_INPUT_OUTSIDE_RUN"):
            cnw_runner.safe_run_input(outside, run_dir)
        link = run_dir / "artifacts/input-link.md"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable on this host")
        with self.assertRaisesRegex(ContractError, "STAGE_INPUT_UNSAFE"):
            cnw_runner.safe_run_input(link, run_dir)

    def test_stage_aliases_match_pinned_workflow_and_keep_extra_roles_explicit(self):
        workflow = cnw_runner.WORKFLOW_PATH.read_text(encoding="utf-8")
        for source_stage in ("plot", "scene_cards", "writing_brief", "prose", "lint_layer1", "lint_layer2", "multi_lens_review", "adversarial_verify", "completeness_critic", "refine", "re_review"):
            self.assertIn(f"- {source_stage}", workflow)
        for source, target in cnw_runner.STAGE_ALIASES.items():
            self.assertEqual(cnw_runner.normalize_stage(source), target)


if __name__ == "__main__":
    unittest.main()
