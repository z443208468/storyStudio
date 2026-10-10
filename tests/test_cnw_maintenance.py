"""Finite offline public Workflow 04/05 coverage; all provider output is mocked."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import cnw_maintenance as maintenance
from tools.cnw_contract import ContractError


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.task_root = Path(self.temporary.name)
        self.root = self.task_root / "workspace/FICT_MAINTENANCE"
        self.root.mkdir(parents=True)
        for name, text in {
            "03_project_design/project_design.md": "# Design\nThe bell marks the day.\n",
            "90_canon/canon.md": "# Canon\nBell rings on day 5.\n",
            "90_canon/timeline.md": "# Timeline\nDay 5: bell.\n",
            "90_canon/unresolved_questions.md": "# Decisions\n- Keep this author decision.\n",
            "06_plot/ep01_plot.md": "# Plot\nBell on day 5.\n",
            "07_draft/episodes/ep01.md": "# Episode 1\nBell on day 6.\n",
            "07_draft/episodes/ep02.md": "# Episode 2\nA quiet day.\n",
            "07_draft/ep01_writing_brief.md": "# Brief\nPLANNING ONLY\n",
            "07_draft/manuscript_index.md": "# Index\nep02 is latest; planned scale unknown.\n",
            "04_chapter_design/arc01.md": "# Arc\nPreserve the fixed main plot.\n",
            "94_runtime/current_sprint.md": "# Current Sprint\nDecisions pending, no new prose authorized.\n",
            "93_exports/handoff_brief.md": "Previous handoff retained verbatim.\r\n",
        }.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode())
        self.patch_root = patch.object(maintenance.runner, "ROOT", self.task_root)
        self.patch_root.start()
        self.requests = []

    def tearDown(self):
        self.patch_root.stop()
        self.temporary.cleanup()

    def provider(self, run, **kwargs):
        self.requests.append(kwargs)
        if kwargs["stage"] == "project_audit":
            value = {"report_markdown": "# MOCK Continuity Audit\nHARD CONFLICT: Source A 90_canon/canon.md:2; Source B 07_draft/episodes/ep01.md:2. Bell dates differ. Ask author.\n",
                "action_items": ["- Decide the bell day; Canon says 5, draft says 6.", "- Decide the bell day; Canon says 5, draft says 6."]}
        else:
            value = {"brief_markdown": "\n\n".join("## " + name + "\nMOCK_ONLY project content."
                for name in (*maintenance.HANDOFF_SECTIONS, "Pipeline Context Pack"))}
        if getattr(self, "zero_findings", False):
            value = {"report_markdown": "# MOCK Report\nNo findings.\n", "action_items": []}
        content = json.dumps(value)
        request = {"messages": kwargs["messages"]}
        request_path = run / "artifacts/mock.request.json"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(json.dumps(request), encoding="utf-8")
        raw_path = run / "artifacts/mock.raw.json"
        raw_path.write_text(json.dumps({"choices": [{"message": {"content": content}}]}), encoding="utf-8")
        receipt = {"provider_request_id": "MOCK_ONLY_RESPONSE", "request_id": "MOCK_ONLY_REQUEST", "status": "SUCCEEDED",
            "request_path": "artifacts/mock.request.json", "request_sha256": maintenance.runner.sha(request_path.read_bytes()),
            "input_sha256": maintenance.runner.sha(json.dumps(kwargs["messages"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()),
            "raw_response_path": "artifacts/mock.raw.json", "raw_response_sha256": maintenance.runner.sha(raw_path.read_bytes()),
            "output_sha256": maintenance.runner.sha(content.encode())}
        state = maintenance.runner.load_state(run)
        state["provider_requests"].append(receipt)
        maintenance.runner.save_state(run, state)
        return content, receipt

    def test_full_audit_real_materials_method_and_canon_protection(self):
        canon = (self.root / "90_canon/canon.md").read_bytes()
        with patch.object(maintenance.runner, "cnw_live_call", side_effect=self.provider):
            result = maintenance.run_maintenance(self.root, "audit")
        payload = json.loads(self.requests[0]["messages"][1]["content"])
        sources = payload["project_sources"]
        self.assertTrue(all(any(n.startswith(folder + "/") for n in sources) for folder in maintenance.AUDIT_FOLDERS))
        self.assertEqual(sources["07_draft/episodes/ep01.md"]["line_count"], 2)
        self.assertEqual(sources["07_draft/ep01_writing_brief.md"]["kind"], "draft_support")
        self.assertIn("Run a canon audit.", self.requests[0]["messages"][0]["content"])
        self.assertEqual(canon, (self.root / "90_canon/canon.md").read_bytes())
        self.assertFalse(result["canon_modified"])
        questions = (self.root / "90_canon/unresolved_questions.md").read_text()
        self.assertIn("Keep this author decision", questions)
        self.assertEqual(questions.count("Decide the bell day"), 1)

    def test_light_targeted_select_sources_without_hiding_baselines(self):
        with patch.object(maintenance.runner, "cnw_live_call", side_effect=self.provider):
            maintenance.run_maintenance(self.root, "audit", scope="light", chapters=["07_draft/episodes/ep02.md"])
            sources = json.loads(self.requests[-1]["messages"][1]["content"])["project_sources"]
            self.assertIn("07_draft/episodes/ep02.md", sources)
            self.assertNotIn("07_draft/episodes/ep01.md", sources)
            self.assertIn("90_canon/canon.md", sources)
            self.assertIn("06_plot/ep01_plot.md", sources)
            maintenance.run_maintenance(self.root, "audit", scope="targeted", target="timeline")
            sources = json.loads(self.requests[-1]["messages"][1]["content"])["project_sources"]
            self.assertIn("07_draft/episodes/ep01.md", sources)
            self.assertIn("03_project_design/project_design.md", sources)
        with self.assertRaisesRegex(ContractError, "AUDIT_TARGET_REQUIRED"):
            maintenance.run_maintenance(self.root, "audit", scope="targeted")

    def test_handoff_eight_sections_statistics_archive_and_reuse(self):
        old = (self.root / "93_exports/handoff_brief.md").read_bytes()
        with patch.object(maintenance.runner, "cnw_live_call", side_effect=self.provider) as call:
            result = maintenance.run_maintenance(self.root, "handoff", pipeline=True)
            log = (self.root / "00_meta/ai_work_log.md").read_bytes()
            repeated = maintenance.run_maintenance(self.root, "handoff", pipeline=True)
        call.assert_called_once()
        self.assertEqual(repeated["provider_call"], "reused")
        self.assertEqual((self.root / result["archive"]).read_bytes(), old)
        self.assertEqual((self.root / "00_meta/ai_work_log.md").read_bytes(), log)
        payload = json.loads(self.requests[0]["messages"][1]["content"])
        self.assertEqual(payload["draft_statistics"]["draft_prose_file_count"], 2)
        self.assertIn("unknown", payload["draft_statistics"]["planned_total_and_completion"])
        self.assertIn("94_runtime/current_sprint.md", payload["project_sources"])
        brief = (self.root / result["path"]).read_text()
        self.assertTrue(all(name in brief for name in maintenance.HANDOFF_SECTIONS))

    def test_zero_findings_does_not_create_questions_or_repay(self):
        (self.root / "90_canon/unresolved_questions.md").unlink()
        self.zero_findings = True
        with patch.object(maintenance.runner, "cnw_live_call", side_effect=self.provider) as call:
            maintenance.run_maintenance(self.root, "audit")
            maintenance.run_maintenance(self.root, "audit")
        call.assert_called_once()
        self.assertFalse((self.root / "90_canon/unresolved_questions.md").exists())

    def test_pending_half_publication_recovers_without_new_call(self):
        apply = maintenance._apply
        def partial(root, run, journal):
            name, row = next(iter(journal["writes"].items()))
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_bytes(row["text"].encode())
            raise OSError("MOCK interruption after first output")
        with patch.object(maintenance.runner, "cnw_live_call", side_effect=self.provider) as call:
            with patch.object(maintenance, "_apply", side_effect=partial):
                with self.assertRaisesRegex(OSError, "MOCK interruption"):
                    maintenance.run_maintenance(self.root, "audit")
            with patch.object(maintenance, "_apply", side_effect=apply):
                result = maintenance.run_maintenance(self.root, "audit")
        call.assert_called_once()
        self.assertTrue(result["recovered"])
        self.assertFalse((self.root / maintenance.PENDING).exists())

    def test_changed_sources_or_outputs_block_recovery_and_invalid_raw(self):
        with patch.object(maintenance.runner, "cnw_live_call", side_effect=self.provider):
            with patch.object(maintenance, "_apply", side_effect=OSError("MOCK interruption")):
                with self.assertRaises(OSError):
                    maintenance.run_maintenance(self.root, "audit")
            (self.root / "90_canon/canon.md").write_text("External changed Canon")
            with self.assertRaisesRegex(ContractError, "MAINTENANCE_SOURCE_CHANGED"):
                maintenance.run_maintenance(self.root, "audit")
        self.assertTrue((self.root / maintenance.PENDING).exists())

    def test_invalid_transport_does_not_publish(self):
        old = (self.root / "93_exports/handoff_brief.md").read_bytes()
        with patch.object(maintenance.runner, "cnw_live_call", return_value=(json.dumps({"brief_markdown": "# MOCK missing sections"}), {"provider_request_id": "MOCK_INVALID"})):
            with self.assertRaisesRegex(ContractError, "HANDOFF_SECTION_MISSING"):
                maintenance.run_maintenance(self.root, "handoff")
        self.assertEqual((self.root / "93_exports/handoff_brief.md").read_bytes(), old)
        self.assertFalse((self.root / maintenance.PENDING).exists())

    def test_cached_receipt_tamper_is_reported_without_new_call(self):
        with patch.object(maintenance.runner, "cnw_live_call", side_effect=self.provider) as call:
            result = maintenance.run_maintenance(self.root, "audit")
            (Path(result["run_dir"]) / "artifacts/mock.request.json").write_text("{}")
            with self.assertRaisesRegex(ContractError, "LIVE_REQUEST_HASH_MISMATCH"):
                maintenance.run_maintenance(self.root, "audit")
        call.assert_called_once()

    def test_pending_request_adapter_change_blocks_recovery(self):
        with patch.object(maintenance.runner, "cnw_live_call", side_effect=self.provider) as call:
            with patch.object(maintenance, "_apply", side_effect=OSError("MOCK interruption")):
                with self.assertRaises(OSError):
                    maintenance.run_maintenance(self.root, "audit")
            with patch.object(maintenance, "_adapter_identity", return_value="changed adapter"):
                with self.assertRaisesRegex(ContractError, "MAINTENANCE_ADAPTER_CHANGED"):
                    maintenance.run_maintenance(self.root, "audit")
        call.assert_called_once()

    def test_completed_result_not_reused_after_output_configuration_change(self):
        with patch.object(maintenance.runner, "cnw_live_call", side_effect=self.provider) as call:
            maintenance.run_maintenance(self.root, "audit")
            with patch.dict(maintenance.OUTPUT_CAPS, {"audit": 6100}):
                maintenance.run_maintenance(self.root, "audit")
        self.assertEqual(call.call_count, 2)
        self.assertEqual(self.requests[-1]["output_cap"], 6100)


if __name__ == "__main__":
    unittest.main()
