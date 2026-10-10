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
from tools.cnw_roles import build_role_packet, REFERENCE_ROOT
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
        self.assertEqual((project / "AGENTS.md").read_bytes(), (REFERENCE_ROOT / "templates/CLAUDE.md").read_bytes())
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
        WORKSPACE.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix=".semantic-import-test-", dir=WORKSPACE)
        self.root = Path(self.temp.name)
        (self.root / "_INBOX").mkdir()
        self.source = self.root / "_INBOX/notes.md"
        self.source.write_text("A has blue eyes.", encoding="utf-8")
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def provider(self, run_dir, *, messages, **kwargs):
        self.assertEqual(kwargs["role_id"], "project_organization")
        payload = json.loads(messages[-1]["content"])
        self.calls.append(payload)
        source = payload["original_sources"]["_INBOX/notes.md"]["text"]
        conflicts = []
        old = payload["existing_documents"].get("90_canon/canon.md", "")
        if "A has blue eyes." in old and "gray" in source:
            conflicts = [{"old_file": "90_canon/canon.md", "old_quote": "A has blue eyes.",
                          "new_file": "90_canon/canon.md", "new_entry": 0,
                          "reason": "The same character's eye color is stated as blue and gray."}]
        result = {"source_notes": {name: "Character notes" for name in payload["original_sources"]},
                  "documents": {name: [{"status": "CONFIRMED", "text": "## Character facts\n" + source,
                                       "source_refs": ["_INBOX/notes.md"]}] for name in workflow.DOCUMENTS},
                  "conflicts": conflicts, "next_action": "Review the character's eye color."}
        return json.dumps(result), {"status": "MOCK_ONLY"}

    def test_semantic_import_update_preserves_old_conclusions_and_skips_unchanged(self):
        with patch.object(workflow, "cnw_live_call", side_effect=self.provider):
            result = workflow.run_import(self.root)
            self.assertEqual(result["status"], "INITIAL_IMPORT_COMPLETE")
            for name in (*workflow.DOCUMENTS, "00_meta/source_log.md", "00_meta/ai_work_log.md"):
                self.assertTrue((self.root / name).is_file(), name)
            canon = (self.root / "90_canon/canon.md").read_bytes()
            self.assertIn(b"A has blue eyes.", canon)
            self.assertIn(b"## Character facts", canon)
            self.assertEqual(workflow.run_import(self.root, incremental=True)["provider_call"], "none")
            self.assertEqual(len(self.calls), 1)
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
            self.assertEqual(len(self.calls), 1)
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
            self.assertEqual(payload["existing_documents"]["90_canon/world_bible.md"], "A has blue eyes.")
            self.assertIn("04_chapter_design/arc_01.md", payload["allowed_existing_documents"])
            return json.dumps({"source_notes": {"_INBOX/notes.md": "Updated notes"}, "documents": {
                "04_chapter_design/arc_01.md": [{"status": "CONFIRMED", "text": "## Direction\nThe chapter goes north.", "source_refs": ["_INBOX/notes.md"]}],
                "90_canon/canon.md": [{"status": "CONFIRMED", "text": "A has gray eyes.", "source_refs": ["_INBOX/notes.md"]}]},
                "conflicts": [{"old_file": "90_canon/world_bible.md", "old_quote": "A has blue eyes.",
                               "new_file": "90_canon/canon.md", "new_entry": 0, "reason": "Incompatible eye colors."}],
                "next_action": "Resolve eye color."}), {}
        with patch.object(workflow, "cnw_live_call", side_effect=provider):
            workflow.run_import(self.root, incremental=True)
        self.assertEqual(world.read_text(encoding="utf-8"), "A has blue eyes.")
        self.assertTrue(arc.read_text(encoding="utf-8").startswith("Existing chapter plan."))
        self.assertIn("The chapter goes north.", arc.read_text(encoding="utf-8"))

    def test_organization_receives_all_originals_and_preserves_supported_paraphrase(self):
        second = self.root / "_INBOX/calling.md"
        second.write_text("B calls A Captain.", encoding="utf-8")
        def provider(run_dir, *, messages, **kwargs):
            payload = json.loads(messages[-1]["content"])
            instructions = (REFERENCE_ROOT / "templates/CLAUDE.md").read_text(encoding="utf-8-sig")
            self.assertIn(instructions, messages[0]["content"])
            self.assertEqual(set(payload["original_sources"]), {"_INBOX/notes.md", "_INBOX/calling.md"})
            self.assertEqual(payload["original_sources"]["_INBOX/calling.md"]["text"], "B calls A Captain.")
            self.assertNotIn("new_claims", payload)
            return json.dumps({"source_notes": {name: "Source notes" for name in payload["original_sources"]},
                "documents": {name: [{"status": "CONFIRMED", "text": "A's eyes are blue. B addresses A as Captain.",
                                     "source_refs": list(payload["original_sources"])}] for name in workflow.DOCUMENTS},
                "conflicts": [], "next_action": "Review character notes."}), {}
        with patch.object(workflow, "cnw_live_call", side_effect=provider):
            result = workflow.run_import(self.root)
        self.assertIn("A's eyes are blue.", (self.root / "90_canon/canon.md").read_text(encoding="utf-8"))
        active = json.loads((self.root / workflow.STATE).read_text(encoding="utf-8"))["claims"]
        self.assertTrue(all(len(row["sources"]) == 2 for row in active.values()))
        self.assertTrue(list((Path(result["run_dir"]) / "artifacts").glob("classification_organized-*.json")))

    def test_method_metadata_has_official_provenance_separate_from_story_sources(self):
        def provider(run_dir, *, messages, **kwargs):
            raw, receipt = self.provider(run_dir, messages=messages, **kwargs)
            obj = json.loads(raw)
            obj["documents"]["90_canon/canon.md"].append({"status": "CONFIRMED",
                "text": "## Policy\nSource material must be preserved.", "source_refs": ["author:templates/CLAUDE.md"]})
            return json.dumps(obj), receipt
        with patch.object(workflow, "cnw_live_call", side_effect=provider):
            result = workflow.run_import(self.root)
        state = json.loads((self.root / workflow.STATE).read_text(encoding="utf-8"))
        policy = next(row for row in state["claims"].values() if row["text"].startswith("## Policy"))
        self.assertEqual(policy["source_kinds"], {"author:templates/CLAUDE.md": "public_method"})
        self.assertTrue(list((Path(result["run_dir"]) / "artifacts").glob("import_request-*.json")))

    def test_unknown_source_reference_cannot_commit(self):
        def provider(run_dir, *, messages, **kwargs):
            raw, receipt = self.provider(run_dir, messages=messages, **kwargs)
            obj = json.loads(raw)
            obj["documents"]["90_canon/canon.md"][0]["source_refs"] = ["_INBOX/nonexistent.md"]
            return json.dumps(obj), receipt
        with patch.object(workflow, "cnw_live_call", side_effect=provider):
            with self.assertRaisesRegex(ContractError, "IMPORT_ENTRY_INVALID"):
                workflow.run_import(self.root)
        self.assertFalse((self.root / workflow.STATE).exists())

    def test_conflict_between_new_sections_withholds_both_bound_versions(self):
        self.source.write_text("A has blue eyes.\nA has gray eyes.", encoding="utf-8")
        def provider(run_dir, *, messages, **kwargs):
            raw, receipt = self.provider(run_dir, messages=messages, **kwargs)
            obj = json.loads(raw)
            obj["documents"]["90_canon/canon.md"] = [
                {"status": "CONFIRMED", "text": text, "source_refs": ["_INBOX/notes.md"]}
                for text in self.source.read_text(encoding="utf-8").splitlines()]
            obj["conflicts"] = [{"old_file": "90_canon/canon.md", "old_entry": 0, "old_quote": "A has blue eyes.",
                                 "new_file": "90_canon/canon.md", "new_entry": 1, "reason": "Incompatible eye colors."}]
            return json.dumps(obj), receipt
        with patch.object(workflow, "cnw_live_call", side_effect=provider):
            self.assertEqual(workflow.run_import(self.root)["conflicts"], 1)
        canon = (self.root / "90_canon/canon.md").read_text(encoding="utf-8")
        self.assertNotIn("A has blue eyes.", canon)
        self.assertNotIn("A has gray eyes.", canon)
        questions = (self.root / "90_canon/unresolved_questions.md").read_text(encoding="utf-8")
        self.assertIn("A has blue eyes.", questions)
        self.assertIn("A has gray eyes.", questions)


if __name__ == "__main__":
    unittest.main()
