import hashlib
import json
import shutil
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from tools.cnw_contract import ContractError, load_contract, validate_source_identity
from tools.cnw_project import import_source, write_contract_draft
from tools.cnw_roles import build_role_packet
from tools.cnw_runner import produce, step, review_run
from tools import cnw_import_workflow as workflow

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "workspace"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class NewProjectImportTests(unittest.TestCase):
    def setUp(self):
        WORKSPACE.mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(prefix=".p31-import-", dir=WORKSPACE))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def import_case(self, project_id, source_name, raw, source_format, anchor_lines):
        incoming = self.tmp / source_name
        incoming.write_bytes(raw)
        result = import_source(self.tmp, project_id, incoming)
        project = self.tmp / project_id
        manifest_path = project / result["source_manifest"]
        index_path = project / result["source_index"]
        canon_path = project / result["canon_candidates"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        index = json.loads(index_path.read_text(encoding="utf-8"))
        canon = json.loads(canon_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["sources"][0]["sha256"], sha(raw))
        self.assertEqual(index["source_sha256"], sha(raw))
        self.assertTrue(canon["candidates"])
        self.assertTrue(all(item["status"] == "TODO_CONFIRM" for item in canon["candidates"]))
        target = 120
        draft_path = project / "contracts" / "scene-draft.json"
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(json.dumps({"unit_id":f"{project_id}-SCENE","pov":"First-person","target_visible_chars":target,"min_visible_chars":80,"max_visible_chars":160,
            "before_line":anchor_lines[0],"after_line":anchor_lines[1],"required_beats":[{"beat_id":"B01","goal":"Use the source-supported opening event.","budget_visible_chars":60},{"beat_id":"B02","goal":"Reach the source-supported next state.","budget_visible_chars":60}],
            "entry_state":"Source-backed opening.","exit_state":"Source-backed next event.","role_in_story":"Connect source events.","reader_reward":"A clear character choice.","characters_in_scene":["Source character"]}, ensure_ascii=False), encoding="utf-8")
        drafted = write_contract_draft(project, draft_path)
        self.assertEqual(drafted["status"], "CONTRACT_DRAFT_READY_FOR_HUMAN_PREFLIGHT")
        contract_path = project / "contracts" / f"{project_id}-SCENE.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        loaded = load_contract(contract_path)
        validate_source_identity(loaded, source_root=project, expected_version="IMPORTED-SOURCE-v1", expected_zip_sha256=manifest["import_id"], expected_manifest_sha256=sha(manifest_path.read_bytes()))
        source_original = project / manifest["sources"][0]["stored_path"]
        plot_path = project / "06_plot/plot.md"
        plot_path.write_text(f"Source SHA256: {sha(raw)}\nCandidate facts: {canon_path.read_text(encoding='utf-8')}\n", encoding="utf-8")
        card_path = project / "05_scene_cards/card.md"
        card_path.write_text(f"Source SHA256: {sha(raw)}\nPlot SHA256: {sha(plot_path.read_bytes())}\nB01 B02\n", encoding="utf-8")
        common_hash = sha(contract_path.read_bytes())
        receipts = [
            {"role":"plot","work_id":contract["unit"]["id"],"status":"FIXTURE_ONLY","contract_sha256":common_hash,"output_sha256":sha(plot_path.read_bytes()),"provider_request_ids":[]},
            {"role":"cards","work_id":contract["unit"]["id"],"status":"FIXTURE_ONLY","contract_sha256":common_hash,"output_sha256":sha(card_path.read_bytes()),"provider_request_ids":[]},
        ]
        plot_packet = build_role_packet("plot", contract_path, {"canon_scope":canon_path, "source_anchors":index_path})
        brief_path = project / "07_draft/brief.md"
        brief_path.write_text(f"Source SHA256: {sha(raw)}\nCanon candidates: {canon_path.read_text(encoding='utf-8')}\nB01 B02; target_visible_chars=120", encoding="utf-8")
        brief_packet = build_role_packet("brief", contract_path, {"plot":plot_path,"cards":card_path,"canon_scope":canon_path,"style_guide":index_path,"voice_samples":source_original,"nk_reflection":index_path}, accepted_receipts=receipts)
        self.assertEqual(plot_packet["execution_mode"], "MOCK_ONLY")
        self.assertEqual(brief_packet["execution_mode"], "MOCK_ONLY")
        self.assertIn(raw.decode("utf-8").splitlines()[1], brief_packet["inputs"]["voice_samples"])
        self.assertIn("TODO_CONFIRM", brief_packet["inputs"]["canon_scope"])
        run_args = Namespace(mode="offline", unit=None, run_id=f"run-{project_id}", work_id=contract["unit"]["id"], contract=str(contract_path), project_root=str(project))
        produce_result = produce(run_args)
        step_args = Namespace(run_id=run_args.run_id, stage="plot", work_id=None, input=None, project_root=str(project))
        step(step_args)
        with self.assertRaisesRegex(ContractError, "EDITORIAL_CANDIDATE_NOT_READY"):
            review_run(Namespace(run_id=run_args.run_id, project_root=str(project)))
        self.assertEqual(produce_result["provider_call"], "none")
        return {"manifest": manifest, "contract": contract, "brief_packet": brief_packet, "project": project}

    def test_two_different_raw_scripts_reach_distinct_contracts_and_role_inputs(self):
        fixtures = ROOT / "tests" / "fixtures"
        md = (fixtures / "pipeline_script_harbor.md").read_bytes()
        structured = (fixtures / "pipeline_script_orchard.json").read_bytes()
        first = self.import_case("FICT_HARBOR", "harbor.md", md, "md", (1, 4))
        second = self.import_case("FICT_ORCHARD", "orchard.json", structured, "json", (1, 6))
        self.assertNotEqual(first["manifest"]["import_id"], second["manifest"]["import_id"])
        self.assertNotEqual(first["contract"]["unit"]["id"], second["contract"]["unit"]["id"])
        self.assertNotEqual(first["brief_packet"]["input_hashes"], second["brief_packet"]["input_hashes"])

    def test_importer_rejects_workspace_root_outside_private_workspace(self):
        with self.assertRaisesRegex(ContractError, "WORKSPACE_ROOT_OUTSIDE_PRIVATE_AREA"):
            import_source(tempfile.gettempdir(), "FICT_ESCAPE", self.tmp / "not-created.md")


class SemanticImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".semantic-import-test-", dir=WORKSPACE)
        self.root = Path(self.temp.name)
        (self.root / "_INBOX").mkdir()
        self.source = self.root / "_INBOX/notes.md"
        self.source.write_text("A has blue eyes.", encoding="utf-8")
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def provider(self, run_dir, *, messages, **kwargs):
        payload = json.loads(messages[-1]["content"])
        self.calls.append(payload)
        if "source" in payload:
            result = {"source_summary": "Character notes", "claims": [{"status": "CONFIRMED", "text": payload["text"],
                                  "quote": payload["text"], "subject": "A", "property": "eye_color"}]}
        else:
            ids = [row["id"] for row in payload["new_claims"]]
            result = {"documents": {name: [{"status": "CONFIRMED", "text": "ignored paraphrase", "claim_ids": ids}]
                                    for name in workflow.DOCUMENTS}, "conflicts": [], "next_action": "Review the character's eye color."}
        return json.dumps(result), {"status": "MOCK_ONLY"}

    def test_semantic_import_update_preserves_old_conclusions_and_skips_unchanged(self):
        with patch.object(workflow, "cnw_live_call", side_effect=self.provider):
            result = workflow.run_import(self.root)
            self.assertEqual(result["status"], "INITIAL_IMPORT_COMPLETE")
            for name in (*workflow.DOCUMENTS, "00_meta/source_log.md", "00_meta/ai_work_log.md"):
                self.assertTrue((self.root / name).is_file(), name)
            canon = (self.root / "90_canon/canon.md").read_bytes()
            self.assertIn(b"A has blue eyes.", canon)
            self.assertNotIn(b"ignored paraphrase", canon)
            self.assertEqual(workflow.run_import(self.root, incremental=True)["provider_call"], "none")
            self.assertEqual(len(self.calls), 2)
            self.source.write_text("A has gray eyes.", encoding="utf-8")
            result = workflow.run_import(self.root, incremental=True)
            self.assertGreater(result["conflicts"], 0)
            self.assertEqual((self.root / "90_canon/canon.md").read_bytes(), canon)
            conflicts = (self.root / "90_canon/unresolved_questions.md").read_text(encoding="utf-8")
            self.assertIn("A has blue eyes.", conflicts)
            self.assertIn("A has gray eyes.", conflicts)
            self.assertIn("TODO_CONFIRM", conflicts)
            self.assertEqual(self.source.read_text(encoding="utf-8"), "A has gray eyes.")

    def test_transaction_recovery_does_not_repeat_model_calls(self):
        original_replace = Path.replace
        writes = []
        def interrupted(path, target):
            if path.name.endswith(".import-tmp"):
                writes.append(str(path))
                if len(writes) == 3:
                    raise OSError("simulated interruption")
            return original_replace(path, target)
        with patch.object(workflow, "cnw_live_call", side_effect=self.provider):
            with patch.object(Path, "replace", interrupted):
                with self.assertRaisesRegex(OSError, "simulated interruption"):
                    workflow.run_import(self.root)
            self.assertTrue((self.root / workflow.PENDING).is_file())
            result = workflow.run_import(self.root)
            self.assertEqual(result["status"], "INITIAL_IMPORT_COMPLETE")
            self.assertEqual(len(self.calls), 2)
            self.assertFalse((self.root / workflow.PENDING).exists())

    def test_update_reads_world_bible_and_appends_existing_arc(self):
        world = self.root / "90_canon/world_bible.md"
        arc = self.root / "04_chapter_design/arc_01.md"
        for path, text in ((world, "A has blue eyes."), (arc, "Existing chapter plan.")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        with patch.object(workflow, "cnw_live_call", side_effect=self.provider):
            workflow.run_import(self.root)
        self.source.write_text("A has gray eyes.\nThe chapter goes north.", encoding="utf-8")
        def provider(run_dir, *, messages, **kwargs):
            payload = json.loads(messages[-1]["content"])
            if "source" in payload:
                rows = [{"status": "CONFIRMED", "text": text, "quote": text, "subject": subject, "property": prop}
                        for text, subject, prop in (("A has gray eyes.", "A", "eye_color"), ("The chapter goes north.", "chapter", "direction"))]
                return json.dumps({"source_summary": "Updated character and chapter notes", "claims": rows}), {}
            self.assertEqual(payload["existing_documents"]["90_canon/world_bible.md"], "A has blue eyes.")
            self.assertIn("04_chapter_design/arc_01.md", payload["allowed_existing_documents"])
            ids = {row["subject"]: row["id"] for row in payload["new_claims"]}
            return json.dumps({"documents": {"04_chapter_design/arc_01.md": [{"status": "CONFIRMED", "text": "ignored", "claim_ids": [ids["chapter"]]}]},
                               "conflicts": [{"old_file": "90_canon/world_bible.md", "old_quote": "A has blue eyes.", "new_claim_id": ids["A"]}],
                               "next_action": "Resolve eye color."}), {}
        with patch.object(workflow, "cnw_live_call", side_effect=provider):
            workflow.run_import(self.root, incremental=True)
        self.assertEqual(world.read_text(encoding="utf-8"), "A has blue eyes.")
        self.assertTrue(arc.read_text(encoding="utf-8").startswith("Existing chapter plan."))
        self.assertIn("The chapter goes north.", arc.read_text(encoding="utf-8"))
        self.assertIn("90_canon/world_bible.md", (self.root / "90_canon/unresolved_questions.md").read_text(encoding="utf-8"))

    def test_direct_confirmation_requires_exact_source_statement(self):
        with self.assertRaisesRegex(ContractError, "IMPORT_CONFIRMED_NOT_DIRECT"):
            workflow._claim({"status": "CONFIRMED", "quote": "A has blue eyes.",
                             "text": "A is immortal.", "subject": "A", "property": "life"},
                            "notes.md", "A has blue eyes.", "digest")


if __name__ == "__main__":
    unittest.main()
