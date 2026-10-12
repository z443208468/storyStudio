"""Atom-07 pre-run and existing-Run identities; no Provider or history writes."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_cnw_input_pack as packs
from tests import test_cnw_work_intent_v2 as intents
from tools import cnw_runner
from tools.cnw_contract import ContractError
from tools.cnw_project import build_contract_preflight, build_run_contract_preflight, write_contract_draft


def create_run(root, contract_path, run_id):
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    return Path(cnw_runner.produce(SimpleNamespace(mode="offline", unit=contract["unit"]["kind"],
        run_id=run_id, work_id=contract["unit"]["id"], contract=str(contract_path),
        project_root=str(root), create_only=True))["path"])


class ExistingRunBindingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = packs.InputPackTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.project("RUN-BINDINGS")
        prepared = self.fixture.prepare(self.root)
        self.path = Path(write_contract_draft(self.root, prepared["draft"])["contract"])
        self.planned = build_contract_preflight(self.root, self.path, run_id="BOUND-RUN")
        self.run = create_run(self.root, self.path, "BOUND-RUN")

    def report(self):
        with patch.object(cnw_runner, "cnw_live_call", side_effect=AssertionError("No Provider in read-only bindings")):
            return build_run_contract_preflight(self.root, self.path, run_id="BOUND-RUN")

    def test_real_existing_run_reuses_binding_computation_without_reserving_or_rewriting(self):
        before = {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        first, second = self.report(), self.report()
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "OFFLINE_BINDINGS_VALIDATED")
        self.assertIs(first["provider_call_authorized"], False)
        self.assertIs(first["state_mutated"], False)
        self.assertEqual(first["controller_attestation_status"], "ATTESTATION_PENDING")
        self.assertEqual(first["live_authorization_status"], "NOT_AUTHORIZED")
        for key, value in self.planned.items():
            if key in first["bindings"]:
                self.assertEqual(first["bindings"][key], value)
        self.assertEqual(first["observed_run_state_sha256"], packs.sha((self.run / "run_state.json").read_bytes()))
        after = {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(cnw_runner.load_state(self.run)["provider_requests"], [])
        with self.assertRaisesRegex(ContractError, "PREFLIGHT_RUN_ID_COLLISION"):
            build_contract_preflight(self.root, self.path, run_id="BOUND-RUN")
        intents._record_atom07_evidence("existing_run_bindings", {"planned": self.planned, "actual": first})

    def test_cross_instance_run_work_contract_source_and_workflow_changes_reject(self):
        state_path = self.run / "run_state.json"
        original = state_path.read_bytes()
        for field, value in (("project_id", "OTHER"), ("project_instance_id", "OTHER-INSTANCE"),
                ("work_id", "OTHER-WORK"), ("run_id", "OTHER-RUN"), ("contract_sha256", "0" * 64),
                ("source_identity", {"source_origin": "ORIGINAL_PROJECT"}),
                ("workflow_template_sha256", "0" * 64), ("provider_config_sha256", "0" * 64),
                ("fixture_only", 0)):
            state = json.loads(original); state[field] = value
            state_path.write_bytes(packs.encoded(state))
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.report()
            self.assertEqual(state_path.read_bytes(), packs.encoded(state))
            state_path.write_bytes(original)

    def test_changed_contract_snapshot_frozen_task_or_source_never_gets_a_binding_report(self):
        contract = json.loads(self.path.read_text(encoding="utf-8"))
        index = json.loads((self.root / contract["input_pack"]["index_file"]).read_text(encoding="utf-8"))
        for path in (self.run / "artifacts/contract.json", self.root / contract["story"]["source_file"],
                     self.root / index["task_context"]["file"]):
            original = path.read_bytes()
            path.write_bytes(original + b" \n")
            with self.subTest(path=path.name), self.assertRaises(ContractError):
                self.report()
            self.assertEqual(path.read_bytes(), original + b" \n")
            path.write_bytes(original)


class WorkIntentRunBindingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = intents.GenericWorkIntentV2Tests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def fill_project(self, root):
        documents = {"04_chapter_design/arc_01.md": "Mira makes one reversible choice.",
            "04_chapter_design/arc_01_episode_details.md": "The first fictional episode.",
            "94_runtime/current_state.md": "The choice is not yet made.",
            "07_draft/manuscript_index.md": "No previous approved episodes.",
            "90_canon/canon.md": "Mira lives by the fictional courtyard.",
            "90_canon/character_bible.md": "Mira knows public news only.",
            "90_canon/world_bible.md": "An invented courtyard and meeting place.",
            "90_canon/timeline.md": "The first local choice precedes a meeting.",
            "90_canon/glossary.md": "The meeting is a public gathering.",
            "92_style_engine/style_guide.md": "Use concrete visible actions.",
            "92_style_engine/forbidden_patterns.md": "## Layer 1\n\n## Layer 2\n",
            "92_style_engine/character_voice_samples.md": "## Mira\nI will check.\n"}
        for name, text in documents.items():
            (root / name).write_text(text, encoding="utf-8")

    def test_three_intents_bind_real_selected_materials_without_fake_original_source(self):
        rows = []
        for intent in ("INSERT_BETWEEN", "ADAPT_SOURCE", "ORIGINAL_EPISODE"):
            root = self.fixture.project("BIND-" + intent)
            self.fill_project(root)
            if intent == "ORIGINAL_EPISODE":
                source, selection = {}, {"arc_ref": "04_chapter_design/arc_01.md", "canon_ref": "90_canon/canon.md", "first_episode": True}
                kind, work_id = "episode", "ep001"
            else:
                source = self.fixture.import_bytes(root, "source.md", b"Mira arrives.\nA friend makes an offer.\nMira leaves.\n")
                selection = {"before_line": 1, "after_line": 3} if intent == "INSERT_BETWEEN" else {"start_line": 1, "end_line": 3}
                kind, work_id = "scene", "UNIT-ONE"
            contract = self.fixture.draft(root, source, intent=intent, unit_id=work_id, kind=kind, **selection)
            path = root / "contracts" / (work_id + ".json")
            planned = build_contract_preflight(root, path, run_id="INTENT-RUN")
            create_run(root, path, "INTENT-RUN")
            actual = build_run_contract_preflight(root, path, run_id="INTENT-RUN")
            self.assertEqual(actual["bindings"]["selected_scope_sha256"], planned["selected_scope_sha256"])
            self.assertEqual(actual["bindings"]["source_identity"], contract["source"])
            if intent == "ORIGINAL_EPISODE":
                self.assertNotIn("source_revision_id", contract["source"])
                self.assertNotIn("manifest_revision_sha256", contract["source"])
                self.assertFalse((root / "_INBOX/source_manifest.json").exists())
            elif intent == "ADAPT_SOURCE":
                self.assertNotIn("before_anchor", contract["story"])
            rows.append(actual)
        intents._record_atom07_evidence("work_intent_run_bindings", {"reports": rows, "provider_call": "none"})


if __name__ == "__main__":
    unittest.main()
