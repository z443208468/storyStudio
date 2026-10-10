"""Finite offline coverage of public triggered operations and ordinary reviews."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_cnw_maintenance as fixture
from tests.test_cnw_chapter_arc import mock_receipt
from tools import cnw_maintenance as m, cnw_operations as op
from tools.cnw_contract import ContractError


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.MaintenanceTests("test_full_audit_real_materials_method_and_canon_protection")
        self.case.setUp()
        self.addCleanup(self.case.tearDown)
        self.root = self.case.root
        self.write("_INBOX/source.md", "# Chapter A\nMira hides her own portrait.\n# Chapter B\nPlayer learns it later.\n")
        self.write("90_canon/character_bible.md", "# Unlocked derived summary\nMira does not know who painted it.\n")
        self.write("08_review/beta.md", "# Ordinary beta\nSlow dialogue. Core-change suggestion needs author decision.\n")
        self.requests = []
        self.response = None

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode())

    def value(self, documents):
        return {"documents": documents, "report_markdown": "# MOCK report\nSource processed; unknown motives retained.",
            "assumptions": [], "unresolved_questions": ["TODO_CONFIRM: motive unknown"], "next_action": "Read scoped extraction."}

    def provider(self, run, **request):
        self.requests.append(request)
        return mock_receipt(run, request, json.dumps(self.response), "OP-MOCK-" + str(len(self.requests)))

    def run_operation(self, operation, **kwargs):
        with patch.object(m.runner, "cnw_live_call", side_effect=self.provider):
            return m.run_maintenance(self.root, operation, **kwargs)

    def test_all_four_commands_read_complete_methods_sources_and_publish(self):
        original = (self.root / "_INBOX/source.md").read_bytes()
        cases = {"decompose": {"04_chapter_design/source_index.md": "CONFIRMED: two source chapters.",
                "05_scene_cards/source_cards.md": "CONFIRMED: hiding portrait / later reader disclosure.",
                "07_draft/decomposition/part_a.md": "Mira hides her own portrait."},
            "extract_canon": {"90_canon/source_extraction.md": "CONFIRMED: Mira painted it; _INBOX/source.md:2. Reader disclosure is later. Motive TODO_CONFIRM."},
            "jet_diagnostic": {"91_jet_engine/diagnostics/source.md": "INFERRED: delayed disclosure. Selected OS TODO_CONFIRM.", "08_review/jet_source.md": "MOCK emotion audit."},
            "character_os": {"03_project_design/characters/Mira.md": "CONFIRMED: Mira hides portrait. INFERRED: embarrassment. Scope Chapter A."}}
        for operation, documents in cases.items():
            with self.subTest(operation=operation):
                self.response = self.value(documents)
                result = self.run_operation(operation, sources=["_INBOX/source.md"], target="Chapter A")
                system = self.requests[-1]["messages"][0]["content"]
                self.assertIn("Standard Commands", system)
                self.assertIn("Canon-promoted decisions", system)
                for path in op.OPERATIONS[operation]["method"]:
                    self.assertIn("Source: " + path, system)
                payload = json.loads(self.requests[-1]["messages"][1]["content"])
                self.assertEqual(payload["project_sources"]["_INBOX/source.md"]["text"].encode(), original)
                for name, text in documents.items():
                    self.assertEqual((self.root / name).read_text(encoding="utf-8"), text)
                count = len(self.requests)
                self.run_operation(operation, sources=["_INBOX/source.md"], target="Chapter A")
                self.assertEqual(len(self.requests), count)
                self.assertEqual(result["status"], "STANDARD_OPERATION_RECORDED")
        self.assertEqual((self.root / "_INBOX/source.md").read_bytes(), original)
        self.assertIn("Next:", (self.root / "00_meta/ai_work_log.md").read_text(encoding="utf-8"))

    def test_unlocked_correction_preserves_old_bytes_history_and_labels(self):
        name = "90_canon/character_bible.md"
        old = (self.root / name).read_bytes()
        text = old.decode() + "\n## Correction 2026-10-11\nCONFIRMED: old derived ignorance claim superseded; actor hides own portrait (_INBOX/source.md:2).\nINFERRED: motive unclear. TODO_CONFIRM: why hide.\n"
        self.response = self.value({name: text})
        result = self.run_operation("extract_canon", sources=["_INBOX/source.md"])
        self.assertTrue((self.root / name).read_bytes().startswith(old))
        archives = list((self.root / "94_runtime/maintenance_history/extract_canon").rglob("character_bible.md"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(archives[0].read_bytes(), old)
        self.assertFalse(result["revision_approved"])
        count = len(self.requests)
        self.run_operation("extract_canon", sources=["_INBOX/source.md"])
        self.assertEqual(len(self.requests), count)

    def test_append_sections_preserve_mixed_line_endings_without_transcription(self):
        name = "90_canon/character_bible.md"
        path = self.root / name
        old = b"# Derived\r\nOld record.\n"
        path.write_bytes(old)
        self.response = self.value({})
        self.response["append_sections"] = {name: "## Correction 2026-10-11\nCONFIRMED: actor knows own history (_INBOX/source.md:2)."}
        self.run_operation("extract_canon", sources=["_INBOX/source.md"])
        self.assertEqual(path.read_bytes(), old + b"\n\n" + self.response["append_sections"][name].encode())
        archives = list((self.root / "94_runtime/maintenance_history/extract_canon").rglob("character_bible.md"))
        self.assertEqual(archives[0].read_bytes(), old)

    def test_lock_states_follow_author_table_without_locking_policy_prose(self):
        from tools.cnw_operations import has_locked_record
        for value in ("# Canon-promoted\nFact", "## **LOCKED**\nFact", "Status: LOCKED",
                      "- Canon Status: **Canon**", "## Canon Status\nCanon",
                      "| Name | Canon Status |\n|---|---|\n| Alice | **Canon** |",
                      "| Topic | 状态 |\n|---|---|\n| item | 锁定 |"):
            with self.subTest(value=value):
                self.assertTrue(has_locked_record(value))
        for value in ("Do not override locked Canon. Never override Canon-promoted decisions.",
                      "不得覆盖锁定决定。", "| Name | Canon Status |\n|---|---|\n| Alice | Provisional |",
                      "Status: Deprecated", "# Canon\nSpecialized derived observations."):
            with self.subTest(value=value):
                self.assertFalse(has_locked_record(value))
        name = "90_canon/character_bible.md"
        self.write(name, "# Derived\nDo not override locked Canon.\n")
        self.response = self.value({})
        self.response["append_sections"] = {name: "## Correction\nCONFIRMED: source action (_INBOX/source.md:2)."}
        self.run_operation("extract_canon", sources=["_INBOX/source.md"])

    def test_generic_revision_accepts_beta_without_receipts_and_does_not_edit_story(self):
        canon = (self.root / "90_canon/canon.md").read_bytes()
        prose = (self.root / "07_draft/episodes/ep01.md").read_bytes()
        self.response = self.value({"09_revision/revision_plan.md": "# Plan\nP0 REQUIRES AUTHOR DECISION: core change. Source beta.md; Canon protected.\nP2: ep01 pacing; shorten repetitions; no Canon change.\nP1/P3: none."})
        result = self.run_operation("revision_plan")
        payload = json.loads(self.requests[-1]["messages"][1]["content"])
        self.assertIn("08_review/beta.md", payload["project_sources"])
        self.assertIn("Generate a revision plan.", self.requests[-1]["messages"][0]["content"])
        self.assertEqual((self.root / "90_canon/canon.md").read_bytes(), canon)
        self.assertEqual((self.root / "07_draft/episodes/ep01.md").read_bytes(), prose)
        self.assertFalse(result["revision_approved"])

    def test_cross_operation_log_append_reuses_but_log_replacement_refuses(self):
        self.response = self.value({"90_canon/source_extraction.md": "CONFIRMED: source portrait action."})
        self.run_operation("extract_canon", sources=["_INBOX/source.md"])
        self.response = self.value({"09_revision/revision_plan.md": "P0 REQUIRES AUTHOR DECISION: beta core change. P2 ep01 pacing. P1/P3 none."})
        self.run_operation("revision_plan")
        count = len(self.requests)
        repeated = self.run_operation("extract_canon", sources=["_INBOX/source.md"])
        self.assertEqual(repeated["provider_call"], "reused")
        self.assertEqual(len(self.requests), count)
        sources = json.loads(self.requests[0]["messages"][1]["content"])["project_sources"]
        self.assertNotIn("00_meta/ai_work_log.md", sources)
        self.write("00_meta/ai_work_log.md", "old entry deleted")
        with self.assertRaisesRegex(ContractError, "MAINTENANCE_COMMITTED_OUTPUT_CHANGED"):
            self.run_operation("extract_canon", sources=["_INBOX/source.md"])
        self.assertEqual(len(self.requests), count)

    def test_output_escape_sources_master_canon_and_locked_record_refused(self):
        for name in ("../escape.md", "_INBOX/source.md", "07_draft/episodes/ep01.md", "90_canon/canon.md", "91_jet_engine/selected_os.md"):
            with self.subTest(name=name):
                self.response = self.value({name: "forbidden"})
                with self.assertRaises(ContractError):
                    self.run_operation("extract_canon", sources=["_INBOX/source.md"])
        self.write("90_canon/character_bible.md", "# Canon-promoted\nLocked fact.\n")
        self.response = self.value({"90_canon/character_bible.md": "# Canon-promoted\nLocked fact.\nnew conflict"})
        with self.assertRaisesRegex(ContractError, "STANDARD_LOCKED_RECORD"):
            self.run_operation("extract_canon", sources=["_INBOX/source.md"])
        self.assertFalse((self.root / m.PENDING).exists())

    def test_overwriting_old_summary_is_refused(self):
        self.response = self.value({"90_canon/character_bible.md": "replace old summary silently"})
        with self.assertRaisesRegex(ContractError, "STANDARD_PRIOR_RECORD_PROTECTED"):
            self.run_operation("extract_canon", sources=["_INBOX/source.md"])

    def test_source_aliases_and_automatic_report_log_are_protected(self):
        name = "04_chapter_design/arc01.md"
        original = (self.root / name).read_bytes()
        for alias in (name, "./" + name, name.replace("/", "\\"), str((self.root / name).resolve())):
            self.response = self.value({name: "overwrite selected original"})
            with self.subTest(alias=alias), self.assertRaisesRegex(ContractError, "STANDARD_OUTPUT_FORBIDDEN"):
                self.run_operation("decompose", sources=[alias])
            self.assertEqual((self.root / name).read_bytes(), original)
        for name in ("08_review/decompose_report.md", "00_meta/ai_work_log.md"):
            self.write(name, "selected original; preserve it")
            with patch.object(m.runner, "cnw_live_call", side_effect=AssertionError("no provider")):
                with self.assertRaisesRegex(ContractError, "STANDARD_SOURCE_OUTPUT_COLLISION"):
                    m.run_maintenance(self.root, "decompose", sources=[str((self.root / name).resolve())])

    def test_pending_half_publication_recovers_and_changed_source_blocks(self):
        self.response = self.value({"90_canon/source_extraction.md": "CONFIRMED: actor knows own painting."})
        apply = m._apply
        def partial(root, run, journal):
            name, row = next(iter(journal["writes"].items()))
            self.write(name, row["text"])
            raise OSError("MOCK half publication")
        with patch.object(m.runner, "cnw_live_call", side_effect=self.provider):
            with patch.object(m, "_apply", side_effect=partial):
                with self.assertRaises(OSError):
                    m.run_maintenance(self.root, "extract_canon", sources=["_INBOX/source.md"])
            count = len(self.requests)
            with patch.object(m, "_apply", side_effect=apply):
                result = m.run_maintenance(self.root, "extract_canon", sources=["_INBOX/source.md"])
            self.assertTrue(result["recovered"])
            self.assertEqual(len(self.requests), count)
        (self.root / "_INBOX/source.md").write_text("external source changed", encoding="utf-8")
        self.response = self.value({"90_canon/new.md": "CONFIRMED: new extraction"})
        with patch.object(m, "_apply", side_effect=OSError("MOCK before apply")):
            with self.assertRaises(OSError):
                self.run_operation("extract_canon", sources=["_INBOX/source.md"])
        self.write("_INBOX/source.md", "second concurrent change")
        with self.assertRaisesRegex(ContractError, "MAINTENANCE_SOURCE_CHANGED"):
            self.run_operation("extract_canon", sources=["_INBOX/source.md"])

    def test_missing_sources_or_reviews_refused_before_provider(self):
        with patch.object(m.runner, "cnw_live_call", side_effect=AssertionError("no provider")):
            with self.assertRaisesRegex(ContractError, "STANDARD_SOURCE_REQUIRED"):
                m.run_maintenance(self.root, "decompose")
            (self.root / "08_review/beta.md").unlink()
            with self.assertRaisesRegex(ContractError, "REVISION_REVIEW_MISSING"):
                m.run_maintenance(self.root, "revision_plan")


if __name__ == "__main__":
    unittest.main()
