"""Offline guards for multi-scene episode assembly and contract budgeting."""
from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from tools.cnw_contract import ContractError, validate_episode_budget
from tools.cnw_generate import validate_generated_scene
from tools.cnw_revision import validate_episode_assembly
from tools.cnw_sprint import run_fixture_sprint
from tools.cnw_runner import ROOT
from tools import cnw_sprint_live as live_sprint


class EpisodePipelineTests(unittest.TestCase):
    def test_live_sprint_orchestration_with_mocked_production_and_provider(self):
        self._exercise_live_sprint()

    def test_live_sprint_project_low_score_rule_blocks_passing_average(self):
        self._exercise_live_sprint(project_status="rewrite", low_score=True)

    def test_live_sprint_project_stop_reason_blocks_passing_scores(self):
        self._exercise_live_sprint(stop_reasons=["Mock project Canon contradiction requires decision"])

    def _exercise_live_sprint(self, project_status="pass", low_score=False, stop_reasons=None):
        with tempfile.TemporaryDirectory(prefix=".sprint-orchestration-", dir=ROOT / "workspace") as temp:
            root = Path(temp)
            (root / "contracts").mkdir()
            (root / "00_meta").mkdir()
            (root / "93_exports").mkdir()
            old_handoff = b"Previous handoff retained verbatim.\r\n"
            (root / "93_exports/handoff_brief.md").write_bytes(old_handoff)
            (root / "00_meta/manuscript_review_rubric.md").write_text("MOCK_ONLY project rubric: evaluate continuity and reward. Any episode score <=64 requires rewrite; this is a mock project rule, not a universal threshold.", encoding="utf-8")
            base = json.loads((ROOT / "workspace/cangqi/contracts/CQ-J19-INSERT-01.work_unit_contract.json").read_text(encoding="utf-8"))
            episodes = []
            for index in range(1, 6):
                contract = json.loads(json.dumps(base))
                contract["project_id"] = "MOCK_ORCHESTRATION"
                contract["unit"].update(id=f"ep{index:03d}", kind="episode", planning_mode="author_plot")
                contract["story"]["required_beats"] = []
                name = f"contracts/ep{index:03d}.json"
                (root / name).write_text(json.dumps(contract), encoding="utf-8")
                episodes.append({"episode_id": f"ep{index:03d}", "contract": name})
            plan = root / "plan.json"
            plan.write_text(json.dumps({"episodes": episodes}), encoding="utf-8")
            produced, executed, verified = [], [], []
            cache = {}
            def produce(args):
                project = Path(args.project_root)
                path = project / "runs" / args.run_id
                path.mkdir(parents=True)
                produced.append(args.work_id)
                if len(produced) > 1:
                    self.assertIn("Check cross-chapter continuity", json.dumps(live_sprint._feedback(project)))
                    self.assertTrue((project / f"07_draft/episodes/ep{len(produced)-1:03d}.md").is_file())
                live_sprint.runner.save_state(path, {"run_id": args.run_id, "mode": "live", "fixture_only": False,
                    "contract_sha256": live_sprint.runner.sha(Path(args.contract).read_bytes()), "work_id": args.work_id, "stages": {}})
            def execute(path):
                state = live_sprint.runner.load_state(path)
                executed.append(state["work_id"])
                for stage, text in (("refine", "MOCK_ONLY prose " + state["work_id"]), ("adversarial_verify", "{}"), ("completeness_critic", '{"candidate_findings":[]}'), ("re_review", '{"status":"CLEAN"}')):
                    artifact = path / (stage + ".txt")
                    artifact.write_text(text, encoding="utf-8")
                    state["stages"][stage] = {"artifact": {"path": artifact.name, "sha256": live_sprint.runner.sha(artifact.read_bytes())}}
                live_sprint.runner.save_state(path, state)
                live_sprint._merge_feedback(path.parent.parent, {"plot": [{"instruction": "Check cross-chapter continuity", "provider_request_id": "MOCK_ONLY"}]})
            def provider(path, *, stage, role_id, messages, **kwargs):
                key = json.dumps([stage, role_id, messages], sort_keys=True)
                if key in cache:
                    return cache[key]
                if role_id == "batch_review":
                    result = {"episode_scores": [{"episode_id": row["episode_id"], "score": (60 if row["episode_id"] == "ep001" else 90) if low_score else 80} for row in episodes],
                        "lens_scores": [{"lens_id": lens, "score": 80} for lens in live_sprint.runner.LENS_IDS],
                        "findings": [{"finding_id": "B1", "severity": "P1", "episode_id": "ep001", "evidence": "MOCK_ONLY prose", "issue": "Mock continuity issue", "recommendation": "Check it"}],
                        "arc_advance_ready": True, "completeness_notes": "Mock overview", "carry_forward": ["Mock continuity issue"], "project_rubric_status": project_status, "stop_reasons": stop_reasons or []}
                elif role_id in live_sprint.VERIFIER_IDS:
                    result = {"verifier_id": role_id, "votes": [{"finding_id": "B1", "verdict": "not_refuted"}]}
                elif role_id == "batch_completeness":
                    result = {"candidate_findings": []}
                else:
                    result = "\n".join("## " + name + "\nMOCK_ONLY handoff" for name in ("Project pitch", "Creative goal", "Protected core", "Draft state", "Canon warnings", "Open questions", "Next best action", "File index", "Pipeline-Ready Context Pack"))
                cache[key] = (result if isinstance(result, str) else json.dumps(result), {"provider_request_id": f"MOCK-{len(cache)}"})
                return cache[key]
            with patch.object(live_sprint.runner, "produce", side_effect=produce), \
                    patch.object(live_sprint.runner, "run_remaining_stages", side_effect=execute), \
                    patch.object(live_sprint.runner, "verify_live", side_effect=lambda args: verified.append(args.work_id)), \
                    patch.object(live_sprint.runner, "cnw_live_call", side_effect=provider):
                result = live_sprint.run_live_sprint(root, "MOCK-SPRINT", plan)
                self.assertEqual(result["status"], "PASS" if project_status == "pass" and not stop_reasons else "REVISION_REQUIRED")
                if low_score:
                    self.assertEqual(result["average_score"], 84)
                self.assertEqual(result["confirmed_counts"]["P1"], 1)
                self.assertEqual(len(produced), 5)
                self.assertEqual(len(verified), 5)
                self.assertFalse(result["user_creative_accepted"])
                self.assertFalse(result["next_sprint_started"])
                self.assertIn("## Pipeline-Ready Context Pack", (root / "93_exports/handoff_brief.md").read_text(encoding="utf-8"))
                self.assertEqual((root / f"93_exports/archive/handoff_{live_sprint.runner.sha(old_handoff)}.md").read_bytes(), old_handoff)
                self.assertIn("Check cross-chapter continuity", json.dumps(live_sprint._feedback(root)))
                count = len(cache)
                live_sprint.run_live_sprint(root, "MOCK-SPRINT", plan)
                self.assertEqual(len(produced), 5)
                self.assertEqual(len(cache), count)
                published = root / "07_draft/episodes/ep005.md"
                original = published.read_bytes()
                published.write_text("existing different manuscript", encoding="utf-8")
                executed_count = len(executed)
                with self.assertRaisesRegex(ContractError, "SPRINT_OUTPUT_COLLISION"):
                    live_sprint.run_live_sprint(root, "MOCK-SPRINT", plan)
                self.assertEqual(len(executed), executed_count)
                self.assertEqual(len(cache), count)
                published.write_bytes(original)
                snapshot = root / "sprints/MOCK-SPRINT/projects/ep003/07_draft/episodes/ep002.md"
                snapshot.write_text("tampered", encoding="utf-8")
                with self.assertRaisesRegex(ContractError, "SPRINT_SNAPSHOT_CHANGED"):
                    live_sprint.run_live_sprint(root, "MOCK-SPRINT", plan)

    def setUp(self):
        self.unit = {"chapter_target_visible_chars": 3200, "scenes": [
            {"id": "S1", "target_visible_chars": 900},
            {"id": "S2", "target_visible_chars": 1100},
            {"id": "S3", "target_visible_chars": 1200},
        ]}

    def test_episode_budget_is_sum_of_three_distinct_scene_budgets(self):
        validate_episode_budget(self.unit)
        self.unit["scenes"][1]["target_visible_chars"] = 1000
        with self.assertRaisesRegex(ContractError, "EPISODE_BUDGET_SUM_MISMATCH"):
            validate_episode_budget(self.unit)

    def test_missing_middle_scene_is_truncated(self):
        result = validate_episode_assembly(["S1", "S2", "S3"], {
            "S1": {"status": "CONTENT_VALID", "finish_reason": "stop"},
            "S3": {"status": "CONTENT_VALID", "finish_reason": "stop"},
        })
        self.assertEqual(result["status"], "CONTENT_RETURN")
        self.assertEqual(result["missing_scene_ids"], ["S2"])

    def test_missing_ending_is_truncated(self):
        result = validate_episode_assembly(["S1", "S2", "S3"], {
            "S1": {"status": "CONTENT_VALID", "finish_reason": "stop"},
            "S2": {"status": "CONTENT_VALID", "finish_reason": "stop"},
        })
        self.assertEqual(result["failure_codes"], ["TRUNCATED_OR_UNFINISHED"])
        self.assertEqual(result["missing_scene_ids"], ["S3"])

    def test_scene_with_failed_content_is_not_episode_completion(self):
        result = validate_episode_assembly(["S1", "S2", "S3"], {
            "S1": {"status": "CONTENT_VALID", "finish_reason": "stop"},
            "S2": {"status": "RETURN_UNDERPRODUCED", "finish_reason": "stop"},
            "S3": {"status": "CONTENT_VALID", "finish_reason": "stop"},
        })
        self.assertEqual(result["status"], "CONTENT_RETURN")
        self.assertEqual(result["missing_scene_ids"], ["S2"])

    def test_summary_only_scene_is_returned_by_length_and_beat_gates(self):
        contract = {"unit": {"min_visible_chars": 700, "max_visible_chars": 1400},
                    "story": {"required_beats": [{"beat_id": "B01"}, {"beat_id": "B02"}],
                              "forbidden_future_revelations": []}}
        beat1 = "港门在黄昏时打开"
        beat2 = "渡船在天亮前离开"
        prose = ("本场梗概：" + beat1 + "；随后钟声响起，众人决定等待；最后" + beat2 + "。") + "背景与经过的概述。" * 110
        result = validate_generated_scene(contract, prose, finish_reason="stop", beat_evidence={"B01": beat1, "B02": beat2},
            dialogue_evidence=[], action_evidence=[], start_state_evidence="", end_state_evidence="")
        self.assertEqual(result["status"], "CONTENT_RETURN")
        self.assertGreaterEqual(result["actual_visible_chars"], 700)
        self.assertNotIn("RETURN_UNDERPRODUCED", result["failure_codes"])
        self.assertNotIn("RETURN_MISSING_BEAT", result["failure_codes"])
        self.assertIn("RETURN_MISSING_DIALOGUE", result["failure_codes"])
        self.assertIn("RETURN_MISSING_ACTION", result["failure_codes"])

    def test_forbidden_future_revelation_is_a_hard_episode_return(self):
        contract = {"unit": {"min_visible_chars": 1, "max_visible_chars": 1000},
                    "story": {"required_beats": [],
                              "forbidden_future_revelations": ["阿岚其实是失踪船长的女儿"]}}
        prose = "阿岚其实是失踪船长的女儿。"
        scene = validate_generated_scene(contract, prose, finish_reason="stop", beat_evidence={},
            dialogue_evidence=[prose], action_evidence=[prose], start_state_evidence=prose,
            end_state_evidence=prose)
        result = validate_episode_assembly(["S1"], {"S1": scene})
        self.assertEqual(scene["failure_codes"], ["RETURN_KNOWLEDGE_BOUNDARY"])
        self.assertEqual(result["status"], "CONTENT_RETURN")
        self.assertEqual(result["missing_scene_ids"], ["S1"])

    def test_five_episode_sprint_fixture_produces_batch_summary_and_handoff(self):
        workspace = ROOT / "workspace"
        workspace.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".p31-sprint-", dir=workspace) as tmp:
            project = Path(tmp)
            rows = []
            for index in range(1, 6):
                episode_id = f"FICT_EP{index}"
                contract = {"schema_version": "cnw_work_unit_v1", "project_id": "FICT_SPRINT",
                    "source": {}, "unit": {"id": episode_id, "kind": "episode", "language": "zh-CN",
                    "pov": "Mira", "target_visible_chars": 300, "min_visible_chars": 200,
                    "max_visible_chars": 400, "policy_sha256": "fixture",
                    "chapter_target_visible_chars": 300, "scenes": [
                        {"id": f"{episode_id}_S1", "target_visible_chars": 100},
                        {"id": f"{episode_id}_S2", "target_visible_chars": 100},
                        {"id": f"{episode_id}_S3", "target_visible_chars": 100}]},
                    "story": {"required_beats": [{"beat_id": "B1", "budget_visible_chars": 10}]}, "review": {}}
                contract_path = project / f"{episode_id}.json"
                contract_path.write_text(json.dumps(contract), encoding="utf-8")
                rows.append({"episode_id": episode_id, "contract": contract_path.name,
                    "plot_fixture": f"Plot fixture for {episode_id}",
                    "review_fixture": "RETURN" if index == 3 else "ACCEPTED",
                    "review_notes": "repair beat" if index == 3 else ""})
            plan_path = project / "sprint-plan.json"
            plan_path.write_text(json.dumps({"episodes": rows}), encoding="utf-8")
            result = run_fixture_sprint(project, "FICT_SPRINT_01", plan_path)
            self.assertEqual(result["status"], "SPRINT_FIXTURE_COMPLETE")
            batch = json.loads((project / result["output_dir"] / "batch_review.json").read_text(encoding="utf-8"))
            handoff = json.loads((project / result["output_dir"] / "next_sprint_handoff.json").read_text(encoding="utf-8"))
            self.assertEqual(batch["episode_count"], 5)
            self.assertEqual(batch["returned"], ["FICT_EP3"])
            self.assertEqual(handoff["carry_forward"][0]["episode_id"], "FICT_EP3")
            self.assertEqual(result["provider_call"], "none")


if __name__ == "__main__":
    unittest.main()
