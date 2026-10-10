import hashlib
import json
import shutil
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from tools.cnw_contract import ContractError, load_contract, validate_source_identity
from tools.cnw_project import import_source, write_contract_draft
from tools.cnw_roles import build_role_packet
from tools.cnw_runner import produce, step, review_run

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


if __name__ == "__main__":
    unittest.main()
