"""Offline guards for multi-scene episode assembly and contract budgeting."""
from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path

from tools.cnw_contract import ContractError, validate_episode_budget
from tools.cnw_revision import validate_episode_assembly
from tools.cnw_sprint import run_fixture_sprint
from tools.cnw_runner import ROOT


class EpisodePipelineTests(unittest.TestCase):
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

    def test_five_episode_sprint_fixture_produces_batch_summary_and_handoff(self):
        workspace = ROOT / "workspace"
        workspace.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".p31-sprint-", dir=workspace) as tmp:
            project = Path(tmp)
            rows = []
            for index in range(1, 6):
                episode_id = f"FICT_EP{index}"
                contract = {"schema_version": "cnw_work_unit_v1", "project_id": "FICT_SPRINT",
                    "source": {}, "unit": {"id": episode_id, "kind": "scene", "language": "zh-CN",
                    "pov": "Mira", "target_visible_chars": 10, "min_visible_chars": 8,
                    "max_visible_chars": 12, "policy_sha256": "fixture",},
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
