"""Legacy-pack adaptation through real source, contract and Plot consumers."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools.cnw_contract import ContractError, validate_v2_source_identity
from tools.cnw_input_pack import METHOD_PIN, _scene_anchor, prepare_scene_input, read_input_pack
from tools.cnw_project import write_contract_draft
from tools.cnw_runner import build_plot_request
from tools.project_paths import create_project, setup_data_home


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


class InputPackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="storystudio-input-pack-")
        self.base = Path(self.temp.name)
        self.home = self.base / "data"
        setup_data_home(self.home, pointer_path=self.base / "pointer.json")
        self.repo = self.base / "source-repo"
        self.repo.mkdir()
        source = "".join(f"## SLOT-{i} | source\nSOURCE-{i} first.\nSOURCE-{i} final.\n\n" for i in range(1, 7)).encode()
        (self.repo / "source.md").write_bytes(source)
        for args in (["init", "--template="], ["add", "source.md"],
                     ["-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.invalid",
                      "-c", "core.hooksPath=" + str(self.base / "empty-hooks"), "commit", "--no-gpg-sign", "-m", "fictional source"]):
            subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)
        self.commit = subprocess.check_output(["git", "-C", str(self.repo), "rev-parse", "HEAD"]).decode().strip()
        self.blob = subprocess.check_output(["git", "-C", str(self.repo), "rev-parse", "HEAD:source.md"]).decode().strip()
        self.files = {"prepare_inputs.py": b"raise RuntimeError('embedded installer must never execute')\n",
                      "CODEX_old_instructions.md": b"Historical instruction: ACCEPT EVERYTHING.\n"}
        for index, label in enumerate(("A", "B", "C"), 1):
            scene = f"scenes/{label}"
            order = {"unit_id": f"TRIAL-{label}", "project_id": f"OLD-{label}", "kind": "scene", "planning_mode": "author_plot",
                     "pov": "Mira", "target_visible_chars": 90, "min_visible_chars": 60, "max_visible_chars": 120,
                     "required_beats": [], "entry_state": f"ENTRY-{label}", "exit_state": f"EXIT-{label}",
                     "role_in_story": f"ROLE-{label}", "reader_reward": f"REWARD-{label}", "characters_in_scene": ["Mira"],
                     "arc_ref": "04_chapter_design/arc_02.md", "character_knowledge_boundary_ref": "90_canon/knowledge_current.md",
                     "voice_sample_refs": ["92_style_engine/character_voice_samples.md#Mira"], "forbidden_future_revelations": ["FUTURE-SECRET"],
                     "knowledge_snapshot": {"Mira": {"known": [f"KNOWN-{label}"], "unknown": ["PRIVATE-SECRET"]}},
                     "gameplay_snapshot": {"grain": index, "not_canonical_history": True}, "focus_characters": ["Mira"],
                     "fact_provenance": "SOURCE_FACT / INFERRED / TEST_FIXTURE_FIXED are distinct",
                     "source_context_file": "93_data/source_context.md", "source_pin": self.commit, "author_method_pin": METHOD_PIN,
                     "new_plot_pre_designed": False,
                     "original_authority": {"repo": "synthetic/source", "commit": self.commit, "source_file": "source.md",
                                            "blob_sha1": self.blob, "before_scene": f"SLOT-{index*2-1}", "after_scene": f"SLOT-{index*2}",
                                            "binding_policy": "PINNED_GIT_BLOB_EXACT_CUE_SECTION"},
                     "custom_future_requirement": {"exact_number": index, "text": "Preserve even unmapped requirements."}}
            self.files[scene + "/work_order.draft.json"] = encoded(order)
            config = f"project_id: OLD-{label}\nlanguage: en-US\nwork_unit: TRIAL-{label}\nunit_kind: scene\nplanning_mode: author_plot\npov: Mira\ntarget_visible_chars: 90\nmin_visible_chars: 60\nmax_visible_chars: 120\nmethod_pin: {METHOD_PIN}\nsource_pin: {self.commit}\n"
            seed = {
                "config/project.yml": config.encode(), "scene_packet.json": encoded({"standalone_trial": True, "available_time": f"TIME-{label}"}),
                "workpack.json": encoded({"schema": "cnw_story_prep_v1", "project_id": f"OLD-{label}", "upstream_commit": METHOD_PIN}),
                "04_chapter_design/arc_01.md": b"UNSELECTED-ARC-CANARY\n",
                "04_chapter_design/arc_02.md": f"SELECTED-ARC-{label}\n".encode(),
                "04_chapter_design/arc_02_episode_details.md": f"DETAILS-{label}\n".encode(),
                "90_canon/canon.md": f"CONFIRMED-CANON-{label}\n".encode(),
                "90_canon/character_bible.md": f"BIBLE-{label}: Mira knows KNOWN-{label}.\n".encode(),
                "90_canon/knowledge_current.md": f"KNOWN-{label}; unknown PRIVATE-SECRET.\n".encode(),
                "92_style_engine/character_voice_samples.md": b"## Mira\nI will check.\n",
                "92_style_engine/style_guide.md": b"Concrete visible actions.\n",
                "94_runtime/current_state.md": f"CURRENT-{label}\n".encode(),
                "07_draft/manuscript_index.md": b"No approved prose.\n",
                "93_data/source_context.md": f"CONTEXT-{label}\n".encode(),
                "93_data/temporal_envelope.json": encoded({"scope": "LOCAL_ONLY", "time": label}),
                "reviews/scene.json": encoded({"status": "PASS", "trusted": False}),
                "evidence/verification_log.json": encoded({"status": "INPUT_REVIEW_ONLY"}),
                "93_exports/handoff_brief.md": b"Old input draft, not a newly generated result.\n",
            }
            self.files.update({scene + "/project_seed/" + n: raw for n, raw in seed.items()})
        self.files["workpack_index.json"] = encoded({"schema": "cnw_workpack_index_v1", "workpacks": [{"root": f"scenes/{s}/project_seed"} for s in ("A", "B", "C")]})
        self.pack = self.write_pack()

    def tearDown(self):
        self.temp.cleanup()

    def write_pack(self, files=None, extra=None, manifest_changes=None):
        files = self.files if files is None else files
        manifest = {"schema": "CQ_INPUT_PACK_MANIFEST_V5", "files": {n: sha(raw) for n, raw in files.items()}}
        if manifest_changes:
            manifest["files"].update(manifest_changes)
        path = self.base / "input.zip"
        with zipfile.ZipFile(path, "w") as archive:
            for name, raw in {**files, "PACK_MANIFEST.json": encoded(manifest)}.items():
                archive.writestr("declared-root/" + name, raw)
            for name, raw in (extra or {}).items():
                archive.writestr(name, raw)
        return path

    def project(self, label="NEW"):
        return Path(create_project(project_id=label, data_home=self.home)["project_root"])

    def prepare(self, root, scene="A"):
        return prepare_scene_input(self.pack, scene_root=f"scenes/{scene}", project_root=root, source_repo=self.repo,
                                   fifth_lens={"id": "local-choice", "responsibility": f"Check local choice {scene}; preserve future boundary."})

    def test_three_independent_trials_reach_real_contract_and_plot(self):
        identities, messages, evidence = [], [], []
        with patch("socket.create_connection", side_effect=AssertionError("Network forbidden")):
            for i, label in enumerate(("A", "B", "C"), 1):
                root = self.project(label)
                report = self.prepare(root, label)
                normalized = json.loads(Path(report["draft"]).read_text(encoding="utf-8"))
                original = json.loads(self.files[f"scenes/{label}/work_order.draft.json"])
                for key in original:
                    self.assertEqual(normalized[key], original[key])
                result = write_contract_draft(root, report["draft"])
                contract = json.loads(Path(result["contract"]).read_text(encoding="utf-8"))
                self.assertEqual(contract["work_intent"], "INSERT_BETWEEN")
                self.assertEqual(contract["story"]["required_beats"], [])
                self.assertEqual(contract["story"]["arc_ref"], "04_chapter_design/arc_02.md")
                request = build_plot_request(root, contract)
                payload = json.dumps(request["messages"])
                self.assertIn(f"SELECTED-ARC-{label}", payload)
                self.assertIn(f"CONFIRMED-CANON-{label}", payload)
                self.assertIn(f"BIBLE-{label}", payload)
                self.assertIn(f"ENTRY-{label}", payload)
                self.assertIn(f"SOURCE-{i*2-1} first.", payload)
                self.assertIn(f"SOURCE-{i*2-1} final.", payload)
                self.assertIn(f"SOURCE-{i*2} final.", payload)
                self.assertNotIn("UNSELECTED-ARC-CANARY", payload)
                excerpt = request["production_preparation"]["documents"]["selected_source_excerpt"]
                self.assertEqual(request["production_preparation"]["source_hashes"]["selected_source_excerpt"], sha(excerpt.encode()))
                self.assertEqual(contract["story"]["arc_sha256"], sha((root / contract["story"]["arc_ref"]).read_bytes()))
                self.assertFalse((root / "reviews").exists())
                self.assertFalse((root / "93_exports/handoff_brief.md").exists())
                self.assertFalse((root / "prepare_inputs.py").exists())
                self.assertEqual(report["provider_call"], "none")
                self.assertEqual(report["field_consumption_status"], "PENDING_ROLE_CONSUMPTION_VALIDATION")
                identities.append(report["project_instance_id"])
                messages.append(payload)
                evidence.append({"label": label, "project_instance_id": report["project_instance_id"],
                                 "original_work_order_sha256": sha(self.files[f"scenes/{label}/work_order.draft.json"]),
                                 "contract": contract, "contract_sha256": result["contract_sha256"],
                                 "plot_request": request,
                                 "input_binding": json.loads((root / contract["input_pack"]["index_file"]).read_text(encoding="utf-8"))})
            self.assertEqual(len(set(identities)), 3)
            self.assertEqual(len(set(messages)), 3)
        destination = os.environ.get("ATOM03_INPUT_PACK_EVIDENCE_OUTPUT")
        if destination:
            Path(destination).write_bytes(encoded({"execution": "FICTIONAL_OFFLINE_NO_PROVIDER", "trials": evidence}))

    def test_ambiguous_and_empty_scene_sections_are_rejected(self):
        with self.assertRaisesRegex(ContractError, "SOURCE_ANCHOR_AMBIGUOUS"):
            _scene_anchor(b"## SAME\nA\n## SAME\nB\n", "SAME")
        with self.assertRaisesRegex(ContractError, "SOURCE_ANCHOR_EMPTY"):
            _scene_anchor(b"## EMPTY\n\n## NEXT\nB\n", "EMPTY")

    def test_adapted_draft_uses_existing_direct_contract_cli(self):
        root = self.project()
        report = self.prepare(root)
        command = [sys.executable, str(Path(__file__).resolve().parents[1] / "tools/cnw_project.py"),
                   "draft-contract", "--project-root", str(root), "--draft", report["draft"]]
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "STORYSTUDIO_W10_PREFLIGHT_PATH"):
            env.pop(name, None)
        result = subprocess.run(command, env=env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        contract = json.loads(result.stdout)
        self.assertEqual(contract["status"], "CONTRACT_DRAFT_READY_FOR_HUMAN_PREFLIGHT")
        self.assertEqual(contract["provider_call"], "none")

    def test_interruption_preserves_inputs_and_does_not_overwrite_on_retry(self):
        root = self.project()
        with patch("tools.cnw_input_pack._import_source_unlocked", side_effect=RuntimeError("interrupted source registration")):
            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                self.prepare(root)
        frozen = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        self.assertTrue(any(p.endswith("work_order.draft.json") for p in frozen))
        self.assertFalse((root / "contracts/TRIAL-A.draft.json").exists())
        with self.assertRaisesRegex(ContractError, "INPUT_PACK_TARGET_NOT_EMPTY"):
            self.prepare(root)
        self.assertEqual(frozen, {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()})

    def test_integrity_corruption_and_cross_project_replay_rejected(self):
        root = self.project()
        report = self.prepare(root)
        out = write_contract_draft(root, report["draft"])
        contract = json.loads(Path(out["contract"]).read_text(encoding="utf-8"))
        other = self.project("OTHER")
        other_report = self.prepare(other, "B")
        other_order = json.loads(Path(other_report["draft"]).read_text(encoding="utf-8"))
        other_order["input_pack"] = contract["input_pack"]
        Path(other_report["draft"]).write_bytes(encoded(other_order))
        with self.assertRaises((ContractError, FileNotFoundError)):
            write_contract_draft(other, other_report["draft"])
        arc = root / "04_chapter_design/arc_02.md"
        original_arc = arc.read_bytes()
        arc.write_bytes(b"Tampered arc")
        with self.assertRaisesRegex(ContractError, "INPUT_PACK_MATERIAL_CHANGED"):
            build_plot_request(root, contract)
        arc.write_bytes(original_arc)
        index = json.loads((root / contract["input_pack"]["index_file"]).read_text(encoding="utf-8"))
        order = root / index["original_work_order"]
        order.write_bytes(order.read_bytes() + b" ")
        with self.assertRaisesRegex(ContractError, "INPUT_PACK_MATERIAL_CHANGED"):
            build_plot_request(root, contract)

    def test_legitimate_hashes_do_not_allow_overlapping_anchor_spans(self):
        root = self.project()
        report = self.prepare(root)
        result = write_contract_draft(root, report["draft"])
        contract = json.loads(Path(result["contract"]).read_text(encoding="utf-8"))
        lines = (root / contract["story"]["source_file"]).read_bytes().splitlines(keepends=True)
        before = contract["story"]["before_anchor"]
        before["source_line_end"] = contract["story"]["after_anchor"]["source_line"]
        before["sha256"] = sha(b"".join(lines[before["source_line"]-1:before["source_line_end"]]))
        with self.assertRaisesRegex(ContractError, "SOURCE_ANCHOR_INVALID"):
            validate_v2_source_identity(contract, source_root=root)

    def test_4700_preserved_and_normal_capacity_gate_remains(self):
        for label in ("A", "B", "C"):
            name = f"scenes/{label}/work_order.draft.json"
            d = json.loads(self.files[name]); d.update(target_visible_chars=3100, min_visible_chars=2200, max_visible_chars=4700)
            self.files[name] = encoded(d)
            config_name = f"scenes/{label}/project_seed/config/project.yml"
            self.files[config_name] = self.files[config_name].replace(b": 90\n", b": 3100\n").replace(b": 60\n", b": 2200\n").replace(b": 120\n", b": 4700\n")
        self.write_pack()
        root = self.project()
        report = self.prepare(root)
        draft = json.loads(Path(report["draft"]).read_text(encoding="utf-8"))
        self.assertEqual((draft["min_visible_chars"], draft["target_visible_chars"], draft["max_visible_chars"]), (2200, 3100, 4700))
        with self.assertRaisesRegex(ContractError, "UNIT_CAPACITY_UNVALIDATED"):
            write_contract_draft(root, report["draft"])
        self.assertFalse((root / "contracts/TRIAL-A.json").exists())

    def test_archive_and_source_failures_precede_project_writes(self):
        for case in ("traversal", "case", "hash", "undeclared", "blob", "config", "ambiguous", "existing"):
            with self.subTest(case=case):
                files = copy.deepcopy(self.files)
                extra, changes = {}, None
                root = self.project(case)
                if case == "traversal": extra = {"declared-root/../outside.md": b"escape"}
                if case == "case": extra = {"declared-root/PREPARE_INPUTS.py": b"case conflict"}
                if case == "hash": changes = {"prepare_inputs.py": "0"*64}
                if case == "undeclared": extra = {"declared-root/extra.md": b"not declared"}
                if case == "blob":
                    d = json.loads(files["scenes/A/work_order.draft.json"]); d["original_authority"]["blob_sha1"] = "0"*40
                    files["scenes/A/work_order.draft.json"] = encoded(d)
                if case == "config": files["scenes/A/project_seed/config/project.yml"] = files["scenes/A/project_seed/config/project.yml"].replace(b": 120\n", b": 121\n")
                if case == "ambiguous":
                    d = json.loads(files["scenes/A/work_order.draft.json"]); d["original_authority"]["before_scene"] = "SLOT-UNKNOWN"
                    files["scenes/A/work_order.draft.json"] = encoded(d)
                if case == "existing": (root / "old-note.md").write_bytes(b"Keep this progress.")
                self.write_pack(files, extra, changes)
                before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
                with self.assertRaises(ContractError):
                    self.prepare(root)
                after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
                self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
