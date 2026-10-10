import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import cnw_generate
from tools.cnw_contract import ContractError, count_visible_chars, load_contract
from tools.cnw_generate import assemble_segment_outputs, build_prose_request, build_segment_request, plan_output_segments, validate_generated_scene, load_capacity_reference
from tools.cnw_revision import plan_persisted_continuation, validate_episode_assembly, validate_revision


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "workspace/cangqi/contracts/CQ-J19-INSERT-01.work_unit_contract.json"
_capacity_text = "中" * 335
_capacity_response = {"id": "provider-capacity-1", "model": "deepseek-flash", "choices": [{"finish_reason": "stop", "message": {"content": _capacity_text}}], "usage": {"prompt_tokens": 300, "completion_tokens": 259}}
CAPACITY = {"receipt": {"status": "SUCCEEDED", "request_id": "capacity-1", "provider_request_id": "provider-capacity-1", "model": "deepseek-flash", "finish_reason": "stop", "scene_chars": 335, "input_tokens": 300, "output_tokens": 259}, "provider_response": _capacity_response, "ledger_row": {"status": "SETTLED", "request_id": "capacity-1", "provider_request_id": "provider-capacity-1", "returned_model": "deepseek-flash", "finish_reason": "stop", "usage": {"input_tokens": 300, "output_tokens": 259}}, "raw_response_sha256": hashlib.sha256(json.dumps(_capacity_response).encode()).hexdigest()}


def tiny_contract(minimum=120, target=160, maximum=220):
    value = copy.deepcopy(load_contract(CONTRACT_PATH))
    value["unit"].update(min_visible_chars=minimum, target_visible_chars=target, max_visible_chars=maximum)
    value["story"]["required_beats"] = [
        {"beat_id": "B01", "budget_visible_chars": target // 2},
        {"beat_id": "B02", "budget_visible_chars": target - target // 2},
    ]
    return value


class CnwGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cnw-generation-")
        self.base = Path(self.temp.name)
        self.contract = tiny_contract()
        self.evidence = {"B01": "她推开门。", "B02": "他收起信。"}
        self.prose = ("她推开门。" + "「你来了。」" + "他收起信。" + "她走到窗边。") * 16
        self.dialogue = ["「你来了。」"]
        self.action = ["她走到窗边。"]

    def _write_capacity_fixture(self, repo):
        run = repo / "runs/historical-draft"
        run.mkdir(parents=True)
        receipt = dict(CAPACITY["receipt"])
        raw = {"request_id": receipt["request_id"], "run_id": run.name, "response": CAPACITY["provider_response"]}
        (run / "run_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        (run / "provider-call.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        ledger = dict(CAPACITY["ledger_row"])
        ledger.update(requested_model="deepseek-flash", estimated_actual_cny="0.001")
        ledger_dir = repo / "runtime/private"
        ledger_dir.mkdir(parents=True)
        (ledger_dir / "p2-cost-ledger.json").write_text(json.dumps({"requests": [ledger]}), encoding="utf-8")
        return run

    def tearDown(self):
        self.temp.cleanup()

    def validate(self, prose=None, evidence=None, finish="stop"):
        return validate_generated_scene(self.contract, prose or self.prose, finish_reason=finish,
            beat_evidence=evidence or self.evidence, dialogue_evidence=self.dialogue,
            action_evidence=self.action, start_state_evidence="她推开门。", end_state_evidence="他收起信。")

    def test_c01_short_stop_is_underproduced(self):
        result = self.validate("她推开门。", {"B01": "她推开门。"})
        self.assertIn("RETURN_UNDERPRODUCED", result["failure_codes"])

    def test_c02_missing_beat_is_returned(self):
        result = self.validate(evidence={"B01": "她推开门。"})
        self.assertIn("RETURN_MISSING_BEAT", result["failure_codes"])
        self.assertEqual(result["missing_beat_ids"], ["B02"])

    def test_c03_dialogue_action_and_end_state_are_explicit(self):
        result = validate_generated_scene(self.contract, self.prose, finish_reason="stop", beat_evidence=self.evidence,
            dialogue_evidence=[], action_evidence=[], start_state_evidence="她推开门。", end_state_evidence="不存在")
        self.assertTrue({"RETURN_MISSING_DIALOGUE", "RETURN_MISSING_ACTION", "RETURN_END_STATE_UNPROVEN"}.issubset(result["failure_codes"]))

    def test_c04_revision_cannot_collapse_scene(self):
        result = validate_revision(self.contract, self.prose, "她推开门。", finish_reason="stop",
            v0_beat_evidence=self.evidence, v1_beat_evidence={"B01": "她推开门。"},
            v1_dialogue_evidence=self.dialogue, v1_action_evidence=self.action,
            start_state_evidence="她推开门。", end_state_evidence="他收起信。")
        self.assertIn("REVISION_REGRESSION", result["failure_codes"])
        self.assertEqual(result["status"], "RETURN")

    def test_c05_shorter_revision_can_pass_in_range(self):
        v1 = self.prose[:int(len(self.prose) * .85)]
        result = validate_revision(self.contract, self.prose, v1, finish_reason="stop",
            v0_beat_evidence=self.evidence, v1_beat_evidence=self.evidence,
            v1_dialogue_evidence=self.dialogue, v1_action_evidence=self.action,
            start_state_evidence="她推开门。", end_state_evidence="他收起信。")
        self.assertGreaterEqual(result["v1_visible_chars"], self.contract["unit"]["min_visible_chars"])
        self.assertNotIn("REVISION_REGRESSION", result["failure_codes"])

    def test_c06_episode_assembly_requires_every_scene(self):
        result = validate_episode_assembly(["S1", "S2", "S3"], {"S1": {"status": "PASS", "finish_reason": "stop"}, "S2": {"status": "PASS", "finish_reason": "stop"}})
        self.assertEqual(result["missing_scene_ids"], ["S3"])
        self.assertEqual(result["failure_codes"], ["TRUNCATED_OR_UNFINISHED"])

    def test_real_receipt_supports_frozen_1500_character_target(self):
        contract = load_contract(CONTRACT_PATH)
        actual = load_capacity_reference(ROOT / "runs/p2-06-draft-20261010")
        plan = plan_output_segments(contract, actual, provider_output_cap=2048, budget_output_cap=2048)
        self.assertFalse(plan["segmented"])
        self.assertEqual(plan["segments"][0]["target_visible_chars"], 1500)
        request = build_prose_request(contract, "B01 B02 B03 B04", "voice", actual, provider_output_cap=2048, budget_output_cap=2048)
        self.assertEqual(request["execution_contract"]["target_visible_chars"], 1500)
        self.assertIn("do not impose an additional 500–700-character limit", request["system"].lower())

    def test_insufficient_cap_segments_on_beat_boundaries(self):
        plan = plan_output_segments(self.contract, CAPACITY, provider_output_cap=90, budget_output_cap=90)
        self.assertTrue(plan["segmented"])
        self.assertEqual([beat for part in plan["segments"] for beat in part["beat_ids"]], ["B01", "B02"])

    def test_continuation_limit_is_fixed_at_two(self):
        repo = self.base / "repo"
        project = repo / "workspace/project"
        project.mkdir(parents=True)
        with patch.object(cnw_generate, "ROOT", repo), self.assertRaisesRegex(ContractError, "CONTINUATION_LIMIT_FIXED"):
            plan_persisted_continuation(project, "RUN1", self.contract, "short", {"status": "RETURN"}, max_attempts=3)

    def test_persisted_continuation_limit_cannot_reset_by_repassing_empty_attempts(self):
        repo = self.base / "repo"
        project = repo / "workspace/project"
        project.mkdir(parents=True)
        validation = {"status": "RETURN", "actual_visible_chars": 40, "missing_beat_ids": ["B02"], "failure_codes": ["RETURN_UNDERPRODUCED"]}
        with patch.object(cnw_generate, "ROOT", repo):
            first = plan_persisted_continuation(project, "RUN1", self.contract, "short one", validation)
            second = plan_persisted_continuation(project, "RUN1", self.contract, "short two", validation)
            third = plan_persisted_continuation(project, "RUN1", self.contract, "short three", validation)
        self.assertEqual(first["attempts_used"], 1)
        self.assertEqual(second["status"], "RETURN_ROOT_CAUSE_REVIEW_REQUIRED")
        self.assertEqual(third["attempts_used"], 2)
        self.assertEqual(len((project / "runs/RUN1/continuation.jsonl").read_text(encoding="utf-8").splitlines()), 2)

    def test_segment_requests_carry_prior_context_and_assembly_is_ordered(self):
        base = build_prose_request(self.contract, "B01 B02", "voices", CAPACITY, provider_output_cap=90, budget_output_cap=90)
        self.assertEqual(len(base["segments"]), 2)
        first_text, second_text = self.prose[:90], self.prose[90:180]
        first = {"segment_id": base["segments"][0]["segment_id"], "text": first_text, "finish_reason": "stop", "provider_request_id": "P1"}
        second = {"segment_id": base["segments"][1]["segment_id"], "text": second_text, "finish_reason": "stop", "provider_request_id": "P2"}
        packet = build_segment_request(base, second["segment_id"], [first])
        self.assertTrue(packet["segment"]["requires_previous_context"])
        self.assertTrue(packet["prior_context"].endswith(first_text))
        with self.assertRaisesRegex(ContractError, "SEGMENT_SEQUENCE_INVALID"):
            build_segment_request(base, second["segment_id"], [])
        result = assemble_segment_outputs(self.contract, base, [first, second], beat_evidence=self.evidence,
            dialogue_evidence=self.dialogue, action_evidence=self.action,
            start_state_evidence="她推开门。", end_state_evidence="他收起信。")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["segment_response_ids"], ["P1", "P2"])
        with self.assertRaisesRegex(ContractError, "SEGMENT_SEQUENCE_INVALID"):
            assemble_segment_outputs(self.contract, base, [second, first], beat_evidence=self.evidence,
                dialogue_evidence=self.dialogue, action_evidence=self.action,
                start_state_evidence="她推开门。", end_state_evidence="他收起信。")

    def test_capacity_reference_requires_raw_response_and_ledger_alignment(self):
        reference = copy.deepcopy(CAPACITY)
        reference["provider_response"]["usage"]["completion_tokens"] = 1
        with self.assertRaisesRegex(ContractError, "CAPACITY_REFERENCE_INVALID"):
            cnw_generate.capacity_ratio(reference)

    def test_generation_cli_rejects_inputs_outside_private_project(self):
        repo = self.base / "repo"
        project = repo / "workspace/project"
        project.mkdir(parents=True)
        external = self.base / "outside.md"
        external.write_text("private", encoding="utf-8")
        argv = ["--contract", str(external), "--brief", "brief.md", "--voice-samples", "voices.md",
                "--capacity-run", str(ROOT / "runs/p2-06-draft-20261010"), "--budget-output-cap", "2048",
                "--project-root", str(project), "--output", "runs/requests/prose.json"]
        with patch.object(cnw_generate, "ROOT", repo), self.assertRaisesRegex(ContractError, "PROJECT_INPUT_OUTSIDE_PRIVATE_PROJECT"):
            cnw_generate.main(argv)

    def test_generation_cli_builds_private_request_from_verified_historical_run(self):
        repo = self.base / "repo"
        project = repo / "workspace/project"
        (project / "contracts").mkdir(parents=True)
        (project / "inputs").mkdir()
        (project / "contracts/scene.json").write_text(json.dumps(self.contract), encoding="utf-8")
        (project / "inputs/brief.md").write_text("B01 B02", encoding="utf-8")
        (project / "inputs/voices.md").write_text("voice samples", encoding="utf-8")
        capacity_run = self._write_capacity_fixture(repo)
        argv = ["--contract", "contracts/scene.json", "--brief", "inputs/brief.md", "--voice-samples", "inputs/voices.md",
                "--capacity-run", str(capacity_run), "--budget-output-cap", "2048", "--project-root", str(project),
                "--output", "runs/R1/artifacts/prose-request.json"]
        stdout = io.StringIO()
        with patch.object(cnw_generate, "ROOT", repo), redirect_stdout(stdout):
            self.assertEqual(cnw_generate.main(argv), 0)
        result = json.loads(stdout.getvalue())
        saved = json.loads((project / "runs/R1/artifacts/prose-request.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "REQUEST_BUILT_OFFLINE")
        self.assertIn("capacity_receipt_id", saved["capacity_plan"])
        self.assertEqual(saved["provider_call"], "not_performed_by_W06_offline_builder")

    def test_historical_469_byte_revision_is_not_mistaken_for_full_scene(self):
        old = (ROOT / "deliverables/EP001/02_修订稿.md").read_text(encoding="utf-8-sig")
        self.assertEqual(count_visible_chars(old), 153)
        self.assertLess(count_visible_chars(old), 1200)


if __name__ == "__main__":
    unittest.main()
