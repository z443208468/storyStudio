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
from tools.cnw_revision import (build_revision_plan, build_revision_record, build_rereview_packets, plan_persisted_continuation,
    promote_revision, validate_episode_assembly, validate_revision)


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


def review_evidence_fixture(findings=None,*,candidate_sha="b"*64,contract_sha="c"*64,source_sha="a"*64,fixture=True):
    provider_requests=[{"stage":"lens5","lens_id":name,"provider_request_id":f"P-L-{name}"} for name in ("style","character","plot","canon","story_specific")]
    provider_requests += [{"stage":"verifier3","verifier_id":name,"provider_request_id":f"P-V-{i}"} for i,name in enumerate(("verifier_1","verifier_2","verifier_3"),1)]
    votes=[{"verifier_id":name,"provider_request_id":f"P-V-{i}","verdict":"not_refuted" if i<3 else "uncertain"} for i,name in enumerate(("verifier_1","verifier_2","verifier_3"),1)]
    finding={"issue_id":"I1","severity":"P1","owner":"character","source":"anchor-1","evidence":"quoted source fact","fix":"restore distinct voice","acceptance":"voice distinction present","verifier_votes":votes}
    selected=findings or [finding]
    for receipt in provider_requests:
        if receipt["stage"]!="verifier3": continue
        output={"verifier_id":receipt["verifier_id"],"votes":[{"finding_id":item["issue_id"],"verdict":next(v["verdict"] for v in item["verifier_votes"] if v["verifier_id"]==receipt["verifier_id"])} for item in selected]}
        receipt["response_content"]=json.dumps(output,ensure_ascii=False,sort_keys=True)
        receipt["output_sha256"]=hashlib.sha256(receipt["response_content"].encode()).hexdigest()
    return {"status":"EXTERNAL_ACCEPTED","execution_mode":"TEST_FIXTURE_ONLY" if fixture else "LIVE","fixture_only":fixture,"candidate_sha256":candidate_sha,"contract_sha256":contract_sha,"source_identity_sha256":source_sha,"controller_acceptance_ref":"TEST_FIXTURE_ONLY" if fixture else "EXTERNAL_CONTROLLER_ACCEPTANCE","provider_requests":provider_requests,"source_catalog":{"anchor-1":{"text":"A quoted source fact appears here.","sha256":hashlib.sha256("A quoted source fact appears here.".encode()).hexdigest(),"source_manifest_sha256":source_sha}},"findings":selected}


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

    def _write_accepted_run(self, project, brief, voices):
        run = project / "runs/R1"
        artifacts = run / "artifacts"
        artifacts.mkdir(parents=True)
        contract = copy.deepcopy(self.contract)
        context = self.accepted_context(contract, brief, voices)
        contract_bytes = json.dumps(contract, ensure_ascii=False).encode("utf-8")
        (artifacts / "contract.json").write_bytes(contract_bytes)
        brief_bytes = brief.encode("utf-8")
        (artifacts / "brief.md").write_bytes(brief_bytes)
        approval = {"status": "ACCEPTED", "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(), "reviewer_id": "controller-fixture"}
        approval_path = project / "reviews/contract-acceptance.json"
        approval_path.parent.mkdir(parents=True, exist_ok=True)
        approval_bytes = json.dumps(approval).encode("utf-8")
        approval_path.write_bytes(approval_bytes)
        state = {"run_id": "R1", "fixture_only": False, "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "contract_approval": {"status": "ACCEPTED", "evidence_path": "reviews/contract-acceptance.json", "evidence_sha256": hashlib.sha256(approval_bytes).hexdigest()},
            "stages": {"brief": {"status": "ACCEPTED", "fixture_only": False,
                "artifact": {"path": "artifacts/brief.md", "sha256": hashlib.sha256(brief_bytes).hexdigest()}}}}
        (run / "run_state.json").write_text(json.dumps(state), encoding="utf-8")
        return contract

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

    def accepted_context(self, contract, brief, voices):
        voice_hash = hashlib.sha256(voices.encode("utf-8")).hexdigest()
        reference = f"fixture-voice.md#SHA256={voice_hash}"
        contract["story"]["voice_sample_refs"] = [reference]
        return {"run_id": "RUN-TEST", "contract_sha256": cnw_generate._canonical_sha256(contract),
            "contract_approval_status": "ACCEPTED", "contract_approval_evidence_sha256": "a" * 64,
            "brief_stage_status": "ACCEPTED", "brief_fixture_only": False,
            "brief_sha256": hashlib.sha256(brief.encode("utf-8")).hexdigest(),
            "voice_sample_sha256": voice_hash, "voice_sample_reference": reference}
        self.assertIn("REVISION_REGRESSION", result["failure_codes"])
        self.assertEqual(result["status"], "CONTENT_RETURN")

    def test_c05_shorter_revision_can_pass_in_range(self):
        v1 = self.prose[:int(len(self.prose) * .85)]
        result = validate_revision(self.contract, self.prose, v1, finish_reason="stop",
            v0_beat_evidence=self.evidence, v1_beat_evidence=self.evidence,
            v1_dialogue_evidence=self.dialogue, v1_action_evidence=self.action,
            start_state_evidence="她推开门。", end_state_evidence="他收起信。")
        self.assertGreaterEqual(result["v1_visible_chars"], self.contract["unit"]["min_visible_chars"])
        self.assertNotIn("REVISION_REGRESSION", result["failure_codes"])

    def test_revision_shrink_over_25_percent_needs_reason(self):
        v0=self.prose*2; v1=self.prose[:180]
        result=validate_revision(self.contract,v0,v1,finish_reason="stop",
            v0_beat_evidence=self.evidence,v1_beat_evidence=self.evidence,
            v1_dialogue_evidence=self.dialogue,v1_action_evidence=self.action,
            start_state_evidence="她推开门。",end_state_evidence="他收起信。")
        self.assertEqual(result["status"],"CONTENT_RETURN")
        self.assertIn("REVISION_SHRINK_OVER_25_PERCENT_REQUIRES_REASON",result["failure_codes"])
        explained=validate_revision(self.contract,v0,v1,finish_reason="stop",
            v0_beat_evidence=self.evidence,v1_beat_evidence=self.evidence,
            v1_dialogue_evidence=self.dialogue,v1_action_evidence=self.action,
            start_state_evidence="她推开门。",end_state_evidence="他收起信。",shortening_reason="删除重复对白，保留全部动作与节拍")
        self.assertEqual(explained["status"],"CONTENT_VALID")
        self.assertEqual(explained["shortening_reason"],"删除重复对白，保留全部动作与节拍")

    def test_revision_plan_requires_source_and_acceptance_per_issue(self):
        review=review_evidence_fixture([
            {"issue_id":"I2","severity":"P2","owner":"style","source":"anchor-1","evidence":"quoted source fact","fix":"reduce repetition","acceptance":"repeat removed","verifier_votes":review_evidence_fixture()["findings"][0]["verifier_votes"]},
            {"issue_id":"I1","severity":"P0","owner":"canon","source":"anchor-1","evidence":"quoted source fact","fix":"remove claim","acceptance":"all claims cited","verifier_votes":review_evidence_fixture()["findings"][0]["verifier_votes"]}])
        plan=build_revision_plan(review,allow_fixture=True)
        self.assertEqual([x["issue_id"] for x in plan["issues"]],["I1","I2"])
        self.assertFalse(plan["self_acceptance"])
        with self.assertRaisesRegex(ContractError,"REVISION_ISSUE_INCOMPLETE"):
            build_revision_plan(review_evidence_fixture([{**review["findings"][0],"acceptance":""}]),allow_fixture=True)
        finding={**review["findings"][0],"verifier_votes":[{**v,"verdict":"refuted"} for v in review["findings"][0]["verifier_votes"]]}
        self.assertEqual(build_revision_plan(review_evidence_fixture([finding]),allow_fixture=True)["issues"],[])
        unbound={**review["findings"][0],"verifier_votes":[{**review["findings"][0]["verifier_votes"][0],"provider_request_id":"fake"},*review["findings"][0]["verifier_votes"][1:]]}
        with self.assertRaisesRegex(ContractError,"REVISION_ISSUE_VOTE_UNBOUND"):
            build_revision_plan(review_evidence_fixture([unbound]),allow_fixture=True)
        mismatched=review_evidence_fixture()
        mismatched["findings"][0]["verifier_votes"][0]["verdict"]="refuted"
        with self.assertRaisesRegex(ContractError,"REVISION_ISSUE_VOTE_NOT_IN_RAW_OUTPUT"):
            build_revision_plan(mismatched,allow_fixture=True)
        ungrounded={**review["findings"][0],"evidence":"unsupported evidence text"}
        with self.assertRaisesRegex(ContractError,"REVISION_ISSUE_EVIDENCE_NOT_IN_SOURCE"):
            build_revision_plan(review_evidence_fixture([ungrounded]),allow_fixture=True)
        with self.assertRaisesRegex(ContractError,"MOCK_REVIEW_CANNOT_CREATE_PRODUCTION_PLAN"):
            build_revision_plan(review_evidence_fixture())

    def test_revision_record_preserves_v0_and_records_diff_and_shrink_reason(self):
        plan=build_revision_plan(review_evidence_fixture(),allow_fixture=True)
        with self.assertRaisesRegex(ContractError,"REVISION_SHRINK_OVER_25_PERCENT_REQUIRES_REASON"):
            build_revision_record(self.prose*2,self.prose[:180],plan)
        record=build_revision_record(self.prose*2,self.prose[:180],plan,shortening_reason="删除重复对白，保留两个节拍的动作和回应")
        self.assertTrue(record["original_preserved"])
        self.assertIn("issue_ids",record); self.assertIn("I1",record["issue_ids"])
        self.assertIn("-",record["diff"])
        self.assertEqual(len(record["v0_sha256"]),64)

    def test_revision_plan_cli_writes_into_private_project(self):
        repo=self.base/"revision-cli"; project=repo/"workspace/project"; inputs=project/"inputs"; inputs.mkdir(parents=True)
        issue={"issue_id":"I1","severity":"P1","owner":"character","source":"voice evidence","evidence":"flat response","fix":"restore distinction","acceptance":"distinct voice present","verification_status":"CONFIRMED"}
        review=review_evidence_fixture([{**issue,"source":"anchor-1","evidence":"quoted source fact","verifier_votes":review_evidence_fixture()["findings"][0]["verifier_votes"]}])
        (inputs/"review.json").write_text(json.dumps(review,ensure_ascii=False),encoding="utf-8")
        import tools.cnw_revision as revision
        with patch.object(cnw_generate,"ROOT",repo),redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ContractError,"MOCK_REVIEW_CANNOT_CREATE_PRODUCTION_PLAN"):
                revision.main(["plan","--project-root",str(project),"--review","inputs/review.json","--output","09_revision/revision_plan.json"])

    def test_rereview_only_builds_affected_lenses_with_fresh_full_text(self):
        sources={"style_guide":"style","language_rules":"language"}
        packets=build_rereview_packets("old full text","new complete draft",["style"],sources)
        self.assertEqual(len(packets),1); self.assertEqual(packets[0]["lens_id"],"style")
        self.assertEqual(packets[0]["draft"],"new complete draft")
        self.assertEqual(packets[0]["change_context"]["v0"],"old full text")
        self.assertEqual(packets[0]["provider_request_id"],None)
        with self.assertRaisesRegex(ContractError,"REREVIEW_SOURCES_MISSING"):
            build_rereview_packets("old","new",["character"],sources)

    def test_promotion_requires_external_hash_bound_review_and_archives_old_copy(self):
        temp=Path(tempfile.mkdtemp())
        repo=temp/"repo"; project=repo/"tests/_isolated_workspace/project"; run=project/"runs/R1"
        (run/"artifacts").mkdir(parents=True); (project/"07_draft/scenes").mkdir(parents=True)
        old=project/"07_draft/scenes/SCENE-1.md"; old.write_text("prior accepted copy",encoding="utf-8")
        candidate=run/"artifacts/scene.md"; candidate.write_text(self.prose[:180],encoding="utf-8")
        v0_path=run/"artifacts/v0.md"; v0_path.write_text(self.prose[:180],encoding="utf-8")
        contract=copy.deepcopy(self.contract); contract["unit"]["id"]="SCENE-1"
        if "source_manifest_sha256" in contract["source"]: contract["source"]["source_manifest_sha256"]="a"*64
        else: contract["source"]["local_private_source_manifest_sha256"]="a"*64
        contract_sha=hashlib.sha256(json.dumps(contract,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        candidate_sha=hashlib.sha256(candidate.read_bytes()).hexdigest(); source_sha=contract["source"].get("source_manifest_sha256") or contract["source"].get("local_private_source_manifest_sha256")
        accepted=review_evidence_fixture(candidate_sha=candidate_sha,contract_sha=contract_sha,source_sha=source_sha)
        plan=build_revision_plan(accepted,allow_fixture=True)
        validation={"finish_reason":"stop","v0_beat_evidence":self.evidence,"v1_beat_evidence":self.evidence,"dialogue_evidence":self.dialogue,"action_evidence":self.action,"start_state_evidence":"她推开门。","end_state_evidence":"他收起信。"}
        record=build_revision_record(v0_path.read_text(encoding="utf-8"),candidate.read_text(encoding="utf-8"),plan)
        evidence={"status":"EXTERNAL_ACCEPTED","fixture_only":True,"work_id":"SCENE-1","candidate_sha256":candidate_sha,"source_identity_sha256":source_sha,"contract_sha256":contract_sha,"controller_acceptance_ref":"TEST_FIXTURE_ONLY","accepted_review":accepted,"revision_plan":plan,"v0_path":"artifacts/v0.md","validation_evidence":validation,"revision_record":record,"expected_current_sha":hashlib.sha256(old.read_bytes()).hexdigest()}
        prod_project=repo/"workspace/project"; prod_run=prod_project/"runs/R1"; prod_candidate=prod_run/"artifacts/scene.md"
        prod_candidate.parent.mkdir(parents=True); prod_candidate.write_bytes(candidate.read_bytes())
        prod_evidence={**evidence,"candidate_sha256":hashlib.sha256(prod_candidate.read_bytes()).hexdigest()}
        import tools.cnw_generate as generate
        with patch.object(generate,"ROOT",repo), self.assertRaisesRegex(ContractError,"EXTERNAL_REVIEW_EVIDENCE_REQUIRED"):
            promote_revision(prod_project,prod_run,prod_candidate,contract,prod_evidence)
        # Isolated fixture root is configurable through the module root; it never points at a production workspace.
        import tools.cnw_revision as rev
        with patch.object(rev,"__file__",str(repo/"tools/cnw_revision.py")):
            invalid={**evidence,"validation_evidence":{**validation,"finish_reason":"length"}}
            with self.assertRaisesRegex(ContractError,"REVISION_CONTRACT_VALIDATION_FAILED"):
                promote_revision(project,run,candidate,contract,invalid,test_fixture=True)
            old.write_text("concurrent publication",encoding="utf-8")
            with self.assertRaisesRegex(ContractError,"PUBLISH_CONFLICT"):
                promote_revision(project,run,candidate,contract,evidence,test_fixture=True)
            self.assertEqual(old.read_text(encoding="utf-8"),"concurrent publication")
            old.write_text("prior accepted copy",encoding="utf-8")
            result=promote_revision(project,run,candidate,contract,evidence,test_fixture=True)
        self.assertEqual(result["status"],"PROMOTED")
        self.assertEqual(old.read_text(encoding="utf-8"),self.prose[:180])
        self.assertEqual((project/result["archive_path"]).read_text(encoding="utf-8"),"prior accepted copy")
        index=(project/"07_draft/manuscript_index.md").read_text(encoding="utf-8")
        self.assertIn("# Manuscript Index",index)
        self.assertIn("review=TEST_FIXTURE_ONLY",index)
        self.assertNotIn("fixture_only",index)

    def test_c06_episode_assembly_requires_every_scene(self):
        result = validate_episode_assembly(["S1", "S2", "S3"], {"S1": {"status": "CONTENT_VALID", "finish_reason": "stop"}, "S2": {"status": "CONTENT_VALID", "finish_reason": "stop"}})
        self.assertEqual(result["status"], "CONTENT_RETURN")
        self.assertEqual(result["missing_scene_ids"], ["S3"])
        self.assertEqual(result["failure_codes"], ["TRUNCATED_OR_UNFINISHED"])

    def test_real_receipt_supports_frozen_1500_character_target(self):
        contract = load_contract(CONTRACT_PATH)
        actual = load_capacity_reference(ROOT / "runs/p2-06-draft-20261010")
        plan = plan_output_segments(contract, actual, provider_output_cap=2048, budget_output_cap=2048)
        self.assertFalse(plan["segmented"])
        self.assertEqual(plan["segments"][0]["target_visible_chars"], 1500)
        context = self.accepted_context(contract, "B01 B02 B03 B04", "voice")
        request = build_prose_request(contract, "B01 B02 B03 B04", "voice", actual, accepted_context=context, provider_output_cap=2048, budget_output_cap=2048)
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
        context = self.accepted_context(self.contract, "B01 B02", "voices")
        base = build_prose_request(self.contract, "B01 B02", "voices", CAPACITY, accepted_context=context, provider_output_cap=90, budget_output_cap=90)
        self.assertEqual(len(base["segments"]), 2)
        first_text, second_text = self.prose[:90], self.prose[90:180]
        first = self._segment_receipt(base["segments"][0]["segment_id"], first_text, "R1", "P1")
        second = self._segment_receipt(base["segments"][1]["segment_id"], second_text, "R2", "P2")
        packet = build_segment_request(base, second["segment_id"], [first])
        self.assertTrue(packet["segment"]["requires_previous_context"])
        self.assertTrue(packet["prior_context"].endswith(first_text))
        with self.assertRaisesRegex(ContractError, "SEGMENT_SEQUENCE_INVALID"):
            build_segment_request(base, second["segment_id"], [])
        repo = self._segment_ledger([first, second])
        with patch.object(cnw_generate, "ROOT", repo):
            result = assemble_segment_outputs(self.contract, base, [first, second], beat_evidence=self.evidence,
                cost_ledger_path=repo / "runtime/private/p2-cost-ledger.json",
                dialogue_evidence=self.dialogue, action_evidence=self.action,
                start_state_evidence="她推开门。", end_state_evidence="他收起信。")
        self.assertEqual(result["status"], "DRAFT_CONTENT_AND_COST_VALIDATED")
        self.assertEqual(result["segment_response_ids"], ["P1", "P2"])
        self.assertEqual(result["validation"]["validation_scope"], "CONTENT_ONLY_NO_COST_OR_PROVIDER_AUTHENTICATION")
        with patch.object(cnw_generate, "ROOT", repo), self.assertRaisesRegex(ContractError, "SEGMENT_COST_SETTLEMENT_MISMATCH"):
            mismatched = [dict(first), dict(second)]
            mismatched[0]["cost_cny"] = 0.002
            assemble_segment_outputs(self.contract, base, mismatched, beat_evidence=self.evidence,
                cost_ledger_path=repo / "runtime/private/p2-cost-ledger.json", dialogue_evidence=self.dialogue,
                action_evidence=self.action, start_state_evidence="她推开门。", end_state_evidence="他收起信。")
        with self.assertRaisesRegex(ContractError, "SEGMENT_SEQUENCE_INVALID"):
            assemble_segment_outputs(self.contract, base, [second, first], cost_ledger_path=repo / "runtime/private/p2-cost-ledger.json",
                beat_evidence=self.evidence, dialogue_evidence=self.dialogue, action_evidence=self.action,
                start_state_evidence="她推开门。", end_state_evidence="他收起信。")

    def _segment_receipt(self, segment_id, text, request_id, provider_id):
        return {"segment_id": segment_id, "text": text, "request_id": request_id, "provider_request_id": provider_id,
            "model": "deepseek-flash", "status": "SUCCEEDED", "finish_reason": "stop",
            "usage": {"prompt_tokens": 10, "completion_tokens": 12}, "cost_cny": 0.001,
            "raw_response_sha256": "b" * 64, "output_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "ledger_settlement": {"status": "SETTLED", "request_id": request_id}}

    def _segment_ledger(self, outputs):
        repo = self.base / "repo-ledger"
        ledger_dir = repo / "runtime/private"
        ledger_dir.mkdir(parents=True)
        rows = []
        for output in outputs:
            rows.append({"request_id": output["request_id"], "status": "SETTLED", "provider_request_id": output["provider_request_id"],
                "returned_model": output["model"], "finish_reason": output["finish_reason"],
                "usage": {"input_tokens": output["usage"]["prompt_tokens"], "output_tokens": output["usage"]["completion_tokens"]},
                "estimated_actual_cny": output["cost_cny"]})
        (ledger_dir / "p2-cost-ledger.json").write_text(json.dumps({"requests": rows}), encoding="utf-8")
        return repo

    def test_capacity_reference_requires_raw_response_and_ledger_alignment(self):
        reference = copy.deepcopy(CAPACITY)
        reference["provider_response"]["usage"]["completion_tokens"] = 1
        with self.assertRaisesRegex(ContractError, "CAPACITY_REFERENCE_INVALID"):
            cnw_generate.capacity_ratio(reference)

    def test_prose_request_refuses_unbound_brief_or_voice_sample(self):
        brief, voices = "B01 B02", "approved voice"
        context = self.accepted_context(self.contract, brief, voices)
        with self.assertRaisesRegex(ContractError, "PROSE_INPUTS_NOT_ACCEPTED"):
            build_prose_request(self.contract, brief + " changed", voices, CAPACITY, accepted_context=context,
                provider_output_cap=2048, budget_output_cap=2048)
        with self.assertRaisesRegex(ContractError, "PROSE_INPUTS_NOT_ACCEPTED"):
            build_prose_request(self.contract, brief, "unreferenced voice", CAPACITY, accepted_context=context,
                provider_output_cap=2048, budget_output_cap=2048)

    def test_generation_cli_rejects_inputs_outside_private_project(self):
        repo = self.base / "repo"
        project = repo / "workspace/project"
        project.mkdir(parents=True)
        external = self.base / "outside.md"
        external.write_text("private", encoding="utf-8")
        self._write_accepted_run(project, "B01 B02", "voice samples")
        argv = ["--run-id", "R1", "--voice-samples", str(external),
                "--capacity-run", str(ROOT / "runs/p2-06-draft-20261010"), "--budget-output-cap", "2048",
                "--project-root", str(project), "--output", "runs/requests/prose.json"]
        with patch.object(cnw_generate, "ROOT", repo), self.assertRaisesRegex(ContractError, "PROJECT_INPUT_OUTSIDE_PRIVATE_PROJECT"):
            cnw_generate.main(argv)

    def test_generation_cli_builds_private_request_from_verified_historical_run(self):
        repo = self.base / "repo"
        project = repo / "workspace/project"
        (project / "inputs").mkdir(parents=True)
        self._write_accepted_run(project, "B01 B02", "voice samples")
        voice_path = project / "inputs/voices.md"
        voice_path.write_text("voice samples", encoding="utf-8")
        # The exact voice file hash must be one of the source references frozen in this run's contract.
        run_contract_path = project / "runs/R1/artifacts/contract.json"
        contract = json.loads(run_contract_path.read_text(encoding="utf-8"))
        voice_hash = hashlib.sha256(voice_path.read_bytes()).hexdigest()
        contract["story"]["voice_sample_refs"] = [f"inputs/voices.md#SHA256={voice_hash}"]
        contract_bytes = json.dumps(contract, ensure_ascii=False).encode("utf-8")
        run_contract_path.write_bytes(contract_bytes)
        state_path = project / "runs/R1/run_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["contract_sha256"] = hashlib.sha256(contract_bytes).hexdigest()
        approval_path = project / "reviews/contract-acceptance.json"
        approval = {"status": "ACCEPTED", "contract_sha256": state["contract_sha256"], "reviewer_id": "controller-fixture"}
        approval_bytes = json.dumps(approval).encode("utf-8")
        approval_path.write_bytes(approval_bytes)
        state["contract_approval"]["evidence_sha256"] = hashlib.sha256(approval_bytes).hexdigest()
        state_path.write_text(json.dumps(state), encoding="utf-8")
        capacity_run = self._write_capacity_fixture(repo)
        argv = ["--run-id", "R1", "--voice-samples", "inputs/voices.md",
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
