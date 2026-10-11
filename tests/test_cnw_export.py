import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import cnw_export
from tools.cnw_contract import ContractError
from tools.cnw_project import import_source, init_registered_project, write_contract_draft
from tools.cnw_roles import read_production_preparation
from tools.project_paths import create_project, setup_data_home


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "runs/TEST"
        (self.run / "artifacts").mkdir(parents=True)
        source = self.root / "original.md"
        source.write_bytes(b"Before <anchor>\r\nFollowing choice\n")
        lines = source.read_bytes().splitlines(keepends=True)
        self.contract = {"project_id": "FICT_EXPORT", "unit": {"id": "TEST", "language": "zh-CN"},
                         "source": {"identity_type": "imported_project", "source_root": "."},
                         "story": {"source_file": source.name, "before_anchor": {
                             "scene": "A", "source_line": 1, "sha256": hashlib.sha256(lines[0]).hexdigest()},
                             "after_anchor": {"scene": "A", "source_line": 2, "sha256": hashlib.sha256(lines[1]).hexdigest()}}}
        (self.run / "artifacts/contract.json").write_text(json.dumps(self.contract), encoding="utf-8")
        (self.run / "artifacts/prose.md").write_text("Actual insert", encoding="utf-8")
        self.state = {"run_id": "TEST", "stages": {"prose": {"artifact": {"path": "artifacts/prose.md"}}}}

    def test_reading_package_contains_verified_real_anchors_in_order(self):
        with patch.object(cnw_export, "ROOT", self.root):
            result = cnw_export.export_reading_package(self.run, self.state, project_root=self.root)
        files = Path(result["deliverables"])
        reading = (files / "03_前后文连读.md").read_text(encoding="utf-8")
        self.assertLess(reading.index("Before <anchor>"), reading.index("Actual insert"))
        self.assertLess(reading.index("Actual insert"), reading.index("Following choice"))
        html = (files / "03_前后文连读.html").read_text(encoding="utf-8")
        self.assertIn("Before &lt;anchor&gt;", html)
        self.assertIn("Following choice", html)
        self.assertIn("show-run -ProjectRoot <project>", (files / "05_复用操作说明.md").read_text(encoding="utf-8"))
        self.assertEqual(result["provider_call"], "none")
        self.assertEqual(result["candidate_status"], "UNREVIEWED_CANDIDATE")
        self.assertIn("UNREVIEWED_CANDIDATE", (files / "00_运行状态.md").read_text(encoding="utf-8"))
        self.assertIn("UNREVIEWED_CANDIDATE", html)

    def test_changed_anchor_refuses_instead_of_exporting_different_context(self):
        (self.root / "original.md").write_text("Changed\nFollowing choice\n", encoding="utf-8")
        with patch.object(cnw_export, "ROOT", self.root), self.assertRaisesRegex(ContractError, "SOURCE_ANCHOR_MISMATCH"):
            cnw_export.export_reading_package(self.run, self.state, project_root=self.root)

    def _registered_project(self, project_id="V2EXPORT"):
        data_home = self.root / ("home-" + str(len(list(self.root.glob("home-*")))))
        setup_data_home(data_home, pointer_path=self.root / (data_home.name + "-config") / "setup.json")
        registered = create_project(project_id=project_id, display_name="Synthetic export fixture", data_home=data_home)
        project = Path(registered["project_root"])
        init_registered_project(project)
        return project

    def _v2_original_contract(self, project, unit_id="ORIGINAL-ONE"):
        identity = json.loads((project / "project_identity.json").read_text(encoding="utf-8"))
        arc = project / "04_chapter_design/arc_01.md"
        arc.parent.mkdir(parents=True, exist_ok=True)
        arc.write_text("Synthetic arc for one opening chapter.\n", encoding="utf-8")
        return {"schema_version": "cnw_work_unit_v2", "project_id": identity["project_id"],
            "project_instance_id": identity["project_instance_id"], "work_intent": "ORIGINAL_EPISODE",
            "source": {"source_origin": "ORIGINAL_PROJECT", "project_instance_id": identity["project_instance_id"]},
            "unit": {"id": unit_id, "kind": "episode", "language": "en-US",
                     "language_locale": "en-US", "pov": "Mira"},
            "story": {"first_episode": True, "arc_ref": "04_chapter_design/arc_01.md",
                      "arc_sha256": hashlib.sha256(arc.read_bytes()).hexdigest()}}

    def _make_v2_run(self, project, run_id, contract, prose="One fictional chapter."):
        run = project / "runs" / run_id
        (run / "artifacts").mkdir(parents=True)
        (run / "artifacts/contract.json").write_text(json.dumps(contract), encoding="utf-8")
        (run / "artifacts/prose.md").write_text(prose, encoding="utf-8")
        state = {"run_id": run_id, "stages": {"prose": {"artifact": {"path": "artifacts/prose.md"}}}}
        return run, state

    def test_anchor_free_adapt_export_uses_selected_source_excerpt(self):
        project = self._registered_project("ADAPTEX")
        source_path = self.root / "selected-one-line.md"
        source_path.write_bytes(b"Selected fictional line.\nIgnored fictional line.\n")
        imported = import_source(input_file=source_path, project_root=project)
        draft = {"schema_version": "cnw_work_unit_draft_v2", "work_intent": "ADAPT_SOURCE",
            "unit_id": "ADAPT-ONE", "kind": "scene", "language_locale": "en-US", "pov": "Mira",
            "target_visible_chars": 90, "min_visible_chars": 60, "max_visible_chars": 120,
            "chapter_context": "Synthetic adaptation exercise.", "role_in_story": "Adapt selected line.",
            "reader_reward": "See one fictional choice.", "entry_state": "Unsettled.", "exit_state": "Chosen.",
            "required_beats": [{"beat_id": "B01", "goal": "Make a choice."}],
            "characters_in_scene": ["Mira"], "character_knowledge_boundary_ref": "90_canon/canon.md",
            "review": {"fifth_lens": {"id": "adaptation-integrity", "responsibility": "Check the synthetic adaptation's reader promise."}},
            "forbidden_future_revelations": ["No later reveal."], "voice_sample_refs": ["Mira"],
            "source_id": imported["source_id"], "source_revision_id": imported["source_revision_id"],
            "source_manifest_revision_sha256": imported["source_manifest_sha256"],
            "source_index_revision_sha256": imported["source_index_sha256"], "start_line": 1, "end_line": 1}
        draft_path = project / "contracts/ADAPT-ONE.draft.json"
        draft_path.write_text(json.dumps(draft), encoding="utf-8")
        write_contract_draft(project, draft_path)
        contract = json.loads((project / "contracts/ADAPT-ONE.json").read_text(encoding="utf-8"))
        preparation = read_production_preparation(project, contract)
        run, state = self._make_v2_run(project, "ADAPT-RUN", contract, "Adapted fictional sentence.")
        (run / "artifacts/production_preparation.json").write_text(json.dumps(preparation), encoding="utf-8")
        result = cnw_export.export_reading_package(run, state, project_root=project)
        reading = Path(result["deliverables"]) / "03_前后文连读.md"
        contents = reading.read_text(encoding="utf-8")
        self.assertIn("Selected fictional line.", contents)
        self.assertIn("Adapted fictional sentence.", contents)
        self.assertNotIn("Ignored fictional line.", contents)

    def test_original_episode_exports_one_chapter_without_fabricated_anchors(self):
        project = self._registered_project("ORIGEX")
        contract = self._v2_original_contract(project)
        run, state = self._make_v2_run(project, "ORIGINAL-RUN", contract, "A single synthetic opening chapter.")
        result = cnw_export.export_reading_package(run, state, project_root=project)
        directory = Path(result["deliverables"])
        reading = (directory / "03_前后文连读.md").read_text(encoding="utf-8")
        self.assertEqual(reading.strip(), "A single synthetic opening chapter.")
        self.assertEqual(directory.parent.parent, project / "deliverables")

    def test_v2_export_requires_explicit_matching_locale(self):
        project = self._registered_project("LOCALEEX")
        contract = self._v2_original_contract(project)
        contract["unit"].pop("language_locale")
        run, state = self._make_v2_run(project, "MISSING-LOCALE", contract)
        with self.assertRaisesRegex(ContractError, "EXPORT_LOCALE_INVALID"):
            cnw_export.export_reading_package(run, state, project_root=project)

    def test_v2_export_rejects_well_formed_but_unsupported_locale(self):
        project = self._registered_project("UNSUPPORTLOCALE")
        contract = self._v2_original_contract(project)
        contract["unit"]["language"] = "eo"
        contract["unit"]["language_locale"] = "eo"
        run, state = self._make_v2_run(project, "UNSUPPORTED-LOCALE", contract)
        with self.assertRaisesRegex(ContractError, "EXPORT_LOCALE_UNSUPPORTED"):
            cnw_export.export_reading_package(run, state, project_root=project)

    def test_v2_exports_for_same_project_id_stay_in_distinct_instances(self):
        first = self._registered_project("SAMEID")
        second = self._registered_project("SAMEID")
        outputs = []
        for project, prose in ((first, "First instance output."), (second, "Second instance output.")):
            contract = self._v2_original_contract(project, "SAME-UNIT")
            run, state = self._make_v2_run(project, "SAME-RUN", contract, prose)
            outputs.append(cnw_export.export_reading_package(run, state, project_root=project))
        first_dir, second_dir = (Path(item["deliverables"]) for item in outputs)
        self.assertNotEqual(first_dir, second_dir)
        self.assertIn("First instance output.", (first_dir / "01_初稿.md").read_text(encoding="utf-8"))
        self.assertIn("Second instance output.", (second_dir / "01_初稿.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
