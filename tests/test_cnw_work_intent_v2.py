"""Offline acceptance tests for generic source revisions and work intents."""
from __future__ import annotations

import hashlib
import json
import copy
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.project_paths import create_project, setup_data_home
from tools.cnw_contract import ContractError, validate_source_identity
from tools.cnw_project import (build_contract_preflight, import_source, init_registered_project,
                               verify_contract_preflight, write_contract_draft)
from tools.cnw_roles import build_author_role_messages, read_production_preparation
from tools.cnw_runner import build_plot_request, load_state, produce, validate_literary_source_freeze
from tools.cnw_runner import save_state
from tools.cnw_recovery import plan_recovery
from tools.cnw_generate import _project_root


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _record_atom07_evidence(group: str, evidence: dict) -> None:
    destination = os.environ.get("ATOM07_EVIDENCE_OUTPUT")
    if not destination:
        return
    path = Path(destination)
    document = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
        "schema_version": "atom07_synthetic_offline_evidence_v1",
        "execution": "SYNTHETIC_OFFLINE_ONLY", "groups": {}}
    document["groups"][group] = evidence
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class GenericWorkIntentV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="storystudio-work-intent-v2-"))
        self.data_home = self.temp / "private-data"
        self.pointer = self.temp / "user-config" / "StoryStudio" / "setup.json"
        setup_data_home(self.data_home, pointer_path=self.pointer)
        self.counter = 0

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def project(self, label="NOVEL"):
        self.counter += 1
        registered = create_project(project_id=label, display_name=label,
                                   data_home=self.data_home)
        root = Path(registered["project_root"])
        init_registered_project(root)
        return root

    def import_bytes(self, root: Path, name: str, raw: bytes):
        source = self.temp / f"{self.counter}-{name}"
        source.write_bytes(raw)
        return import_source(input_file=source, project_root=root)

    def draft(self, root: Path, result: dict, *, intent: str, unit_id: str,
              kind="scene", **selection):
        data = {"schema_version": "cnw_work_unit_draft_v2", "work_intent": intent,
                "unit_id": unit_id, "kind": kind, "language_locale": "en-US", "pov": "Mira",
                "target_visible_chars": 90, "min_visible_chars": 60, "max_visible_chars": 120,
                "chapter_context": "A fictional test assignment.",
                "role_in_story": "Show one source-supported choice.",
                "reader_reward": "A clear change in trust.", "entry_state": "The issue is unsettled.",
                "exit_state": "The characters have chosen a next step.",
                "required_beats": [{"beat_id": "B01", "goal": "Make the choice visible."}],
                "characters_in_scene": ["Mira"], "character_knowledge_boundary_ref": "90_canon/canon.md",
                "forbidden_future_revelations": ["Do not reveal later events."],
                "voice_sample_refs": ["Mira"],
                "review": {"fifth_lens": {"id": "reader-promise",
                    "responsibility": "Check the synthetic project's confirmed reader promise."}}, **selection}
        if intent != "ORIGINAL_EPISODE":
            data.update(source_id=result["source_id"], source_revision_id=result["source_revision_id"],
                        source_manifest_revision_sha256=result["source_manifest_sha256"],
                        source_index_revision_sha256=result["source_index_sha256"])
        path = root / "contracts" / f"{unit_id}.draft.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        write_contract_draft(root, path)
        contract = json.loads((root / "contracts" / f"{unit_id}.json").read_text(encoding="utf-8"))
        duty = data["review"]["fifth_lens"]["responsibility"]
        self.assertEqual(contract["review"]["fifth_lens"]["id"], "reader-promise")
        self.assertEqual(contract["review"]["fifth_lens"]["responsibility"], duty)
        self.assertEqual(contract["review"]["fifth_lens"]["responsibility_sha256"], sha(duty.encode("utf-8")))
        return contract

    def test_import_order_never_selects_first_source_and_old_manifest_identity_survives_append(self):
        root = self.project("ORDERED")
        a = self.import_bytes(root, "a.md", b"A begins.\nA ends.\n")
        legacy_manifest = (root / "_INBOX/source_manifest.json").read_bytes()
        old_v1 = {"schema_version": "cnw_work_unit_v1", "project_id": "ORDERED",
                  "source": {"identity_type": "imported_project", "version": "IMPORTED-SOURCE-v1",
                             "import_id": json.loads(legacy_manifest)["import_id"],
                             "source_file_sha256": a["source_revision_id"],
                             "source_manifest_sha256": sha(legacy_manifest),
                             "manifest_file": "_INBOX/source_manifest.json", "source_root": "."},
                  "unit": {"id": "OLD-UNIT"},
                  "story": {"source_file": json.loads(legacy_manifest)["sources"][0]["stored_path"],
                            "before_anchor": {"source_line": 1, "sha256": sha(b"A begins.\n")},
                            "after_anchor": {"source_line": 2, "sha256": sha(b"A ends.\n")}}}
        old_contract_sha = sha(json.dumps(old_v1, sort_keys=True).encode())

        b = self.import_bytes(root, "b.md", b"B begins.\nB middle.\nB ends.\n")
        selected = self.draft(root, b, intent="INSERT_BETWEEN", unit_id="SELECT-B",
                              before_line=1, after_line=3)
        selected_manifest = json.loads((root / b["source_manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(selected["story"]["source_file"], selected_manifest["sources"][1]["stored_path"])
        self.assertEqual(selected["source"]["source_id"], b["source_id"])
        self.assertEqual(selected["source"]["manifest_revision_sha256"], b["source_manifest_sha256"])
        self.assertEqual(selected["source"]["source_index_sha256"], b["source_index_sha256"])
        validate_source_identity(old_v1, source_root=root, expected_version="IMPORTED-SOURCE-v1",
                                 expected_zip_sha256=json.loads(legacy_manifest)["import_id"],
                                 expected_manifest_sha256=sha(legacy_manifest))

        c = self.import_bytes(root, "c.md", b"C begins.\nC ends.\n")
        self.assertNotEqual(c["source_manifest_sha256"], b["source_manifest_sha256"])
        validate_source_identity(selected, source_root=root, expected_version="", expected_zip_sha256="",
                                 expected_manifest_sha256="")
        validate_source_identity(old_v1, source_root=root, expected_version="IMPORTED-SOURCE-v1",
                                 expected_zip_sha256=json.loads(legacy_manifest)["import_id"],
                                 expected_manifest_sha256=sha(legacy_manifest))
        self.assertEqual(sha(json.dumps(old_v1, sort_keys=True).encode()), old_contract_sha)

        reverse = self.project("REVERSE")
        b_first = self.import_bytes(reverse, "b-first.md", b"B begins.\nB middle.\nB ends.\n")
        self.import_bytes(reverse, "a-second.md", b"A begins.\nA ends.\n")
        reverse_b = self.draft(reverse, b_first, intent="INSERT_BETWEEN", unit_id="REVERSE-B",
                               before_line=1, after_line=3)
        self.assertEqual(reverse_b["source"]["source_revision_id"], b_first["source_revision_id"])

    def test_single_line_json_pointer_adaptation_without_fabricated_anchors(self):
        root = self.project("JSONWORK")
        raw = b'{"episodes":[{"title":"A","text":"A traveler chooses a road."},{"title":"B","text":"A friend answers."}]}'
        imported = self.import_bytes(root, "one-line.json", raw)
        contract = self.draft(root, imported, intent="ADAPT_SOURCE", unit_id="JSON-ADAPT",
                              json_pointer="/episodes/1/text")
        self.assertNotIn("before_anchor", contract["story"])
        self.assertNotIn("after_anchor", contract["story"])
        preparation = read_production_preparation(root, contract)
        self.assertEqual(preparation["documents"]["selected_source_excerpt"], '"A friend answers."')
        self.assertEqual(preparation["source_hashes"]["selected_source_excerpt"],
                         contract["story"]["source_selection"]["selected_sha256"])
        request = build_plot_request(root, contract)
        self.assertEqual(request["provider_call"], "none")
        self.assertIn("A friend answers.", json.dumps(request["messages"], ensure_ascii=False))
        bad = json.loads((root / "contracts/JSON-ADAPT.draft.json").read_text(encoding="utf-8"))
        bad["unit_id"] = "MISSING-POINTER"
        bad["json_pointer"] = "/episodes/20/text"
        path = root / "contracts/MISSING-POINTER.draft.json"
        path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "SOURCE_JSON_POINTER_MISSING"):
            write_contract_draft(root, path)

        duplicate = self.temp / "duplicate.json"
        duplicate.write_text('{"same":1,"same":2}', encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "IMPORT_JSON_DUPLICATE_KEY"):
            import_source(input_file=duplicate, project_root=root)

    def test_json_object_and_array_keep_canonical_and_plot_wire_hashes_separate(self):
        root = self.project("JSON-NODES")
        raw = b'{"episodes":[{"text":"A friend answers.","emotion":"calm"},{"text":"Mira listens.","emotion":"wary"}]}'
        imported = self.import_bytes(root, "nodes.json", raw)
        parsed = json.loads(raw)
        for suffix, pointer in (("OBJECT", "/episodes/0"), ("ARRAY", "/episodes")):
            with self.subTest(pointer=pointer):
                contract = self.draft(root, imported, intent="ADAPT_SOURCE", unit_id=f"JSON-{suffix}",
                                      json_pointer=pointer)
                value = parsed["episodes"][0] if suffix == "OBJECT" else parsed["episodes"]
                selection = contract["story"]["source_selection"]
                canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                wire_excerpt = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
                canonical_sha, wire_sha = sha(canonical), sha(wire_excerpt.encode("utf-8"))
                self.assertEqual(selection["canonical_selected_value_sha256"], canonical_sha)
                self.assertEqual(selection["selected_sha256"], canonical_sha)
                self.assertEqual(selection["wire_excerpt_sha256"], wire_sha)
                self.assertNotEqual(canonical_sha, wire_sha)
                preparation = read_production_preparation(root, contract)
                self.assertEqual(preparation["documents"]["selected_source_excerpt"], wire_excerpt)
                self.assertEqual(preparation["source_hashes"]["selected_source_excerpt"], wire_sha)
                identity = json.loads(preparation["documents"]["selected_source_identity"])
                self.assertEqual(identity["canonical_selected_value_sha256"], canonical_sha)
                self.assertEqual(identity["wire_excerpt_sha256"], wire_sha)
                request = build_plot_request(root, contract)
                request_payload = json.loads(request["messages"][1]["content"])
                consumed_preparation = request_payload["support"]["production_preparation"]
                self.assertEqual(consumed_preparation["documents"]["selected_source_excerpt"], wire_excerpt)
                self.assertEqual(consumed_preparation["source_hashes"]["selected_source_excerpt"], wire_sha)
                tampered = copy.deepcopy(contract)
                tampered["story"]["source_selection"]["wire_excerpt_sha256"] = "0" * 64
                with self.assertRaisesRegex(ContractError, "SOURCE_WIRE_EXCERPT_HASH_MISMATCH"):
                    build_plot_request(root, tampered)

    def test_selected_source_and_prose_messages_exclude_unselected_source_canary(self):
        root = self.project("CANARY")
        unselected_text = "UNAUTHORIZED_SOURCE_CANARY: Mira secretly owns the lighthouse."
        unselected_source = self.import_bytes(root, "a-unselected.md", unselected_text.encode("utf-8"))
        selected_text = "B_SOURCE_CANARY: Mira offers one small repair."
        selected_source = self.import_bytes(root, "b-selected.md", selected_text.encode("utf-8"))
        contract = self.draft(root, selected_source, intent="ADAPT_SOURCE", unit_id="CANARY-ADAPT",
                              start_line=1, end_line=1)
        plot_request = build_plot_request(root, contract)
        plot_messages = json.dumps(plot_request["messages"], ensure_ascii=False)
        self.assertIn(selected_text, plot_messages)
        self.assertNotIn("UNAUTHORIZED_SOURCE_CANARY", plot_messages)
        prepared = plot_request["production_preparation"]
        self.assertEqual(prepared["documents"]["selected_source_excerpt"], selected_text)
        self.assertEqual(prepared["source_hashes"]["selected_source_excerpt"],
                         selected_source["source_revision_id"])
        selected_identity = json.loads(prepared["documents"]["selected_source_identity"])
        self.assertEqual(selected_identity["source_id"], selected_source["source_id"])
        self.assertEqual(selected_identity["source_revision_id"], selected_source["source_revision_id"])

        brief = ("# Writing Brief\n## Voice References\n- Mira — use her sample\n"
                 "## Hard Constraints\nKeep to the selected source.\n")
        voices = ("## Mira\n'I can repair the hinge.'\n"
                  "## Unselected Source\nUNRELATED_VOICE_CANARY: sample not referenced by the Brief\n")
        prose_messages = build_author_role_messages("prose", contract, {
            "07_draft/<work_id>_writing_brief.md": brief,
            "92_style_engine/character_voice_samples.md": voices,
            "unselected_source_excerpt": unselected_text,
        })
        prose_wire = json.dumps(prose_messages, ensure_ascii=False)
        self.assertNotIn("UNAUTHORIZED_SOURCE_CANARY", prose_wire)
        self.assertNotIn("UNRELATED_VOICE_CANARY", prose_wire)
        payload = json.loads(prose_messages[1]["content"])
        self.assertEqual(set(payload), {"writing_brief", "voice_samples"})
        self.assertIn("'I can repair the hinge.'", payload["voice_samples"])
        self.assertNotIn("Unselected Source", payload["voice_samples"])

    def test_original_first_episode_requires_real_canon_arc_and_style_then_builds_plot_offline(self):
        root = self.project("ORIGINAL")
        self.assertEqual(_project_root(root), root.resolve())
        self.assertFalse((root / "_INBOX/source_manifest.json").exists())
        (root / "04_chapter_design/arc_01.md").write_text(
            "Mira arrives at the coast and chooses whether to accept help.", encoding="utf-8")
        empty_contract = self.draft(root, None, intent="ORIGINAL_EPISODE", unit_id="EMPTY-PREFLIGHT",
                                    first_episode=True, arc_ref="04_chapter_design/arc_01.md")
        with self.assertRaisesRegex(ContractError, "PRE_FLIGHT_MISSING_PROJECT_INPUT"):
            read_production_preparation(root, empty_contract)
        filled = {
            "94_runtime/current_state.md": "Opening premise: Mira is deciding whether to trust the lighthouse keeper.",
            "07_draft/manuscript_index.md": "No chapters published yet; this assignment is the first episode.",
            "04_chapter_design/arc_index.md": "| Arc | Title | Episodes | Purpose |\n|---|---|---|---|\n| 01 | Arrival | 1 | Establish the choice. |\n",
            "04_chapter_design/arc_01.md": "Mira arrives at the coast and chooses whether to accept help.",
            "04_chapter_design/arc_01_episode_details.md": "Opening episode: establish the harbor, offer, choice, and response.",
            "90_canon/canon.md": "Mira has just arrived in a coastal town and has no established allies.",
            "90_canon/character_bible.md": "Mira is observant and cautious. The keeper is patient but private.",
            "90_canon/world_bible.md": "The town depends on a lighthouse maintained by one family.",
            "90_canon/timeline.md": "The story opens on Mira's first evening in town.",
            "90_canon/glossary.md": "Harbor Bell: the town's dusk signal.",
            "92_style_engine/style_guide.md": "Use close third person, concrete sensory details, and restrained warmth.",
            "92_style_engine/forbidden_patterns.md": "Do not resolve the town mystery in the opening episode.",
            "92_style_engine/character_voice_samples.md": "## Mira\n'I would rather ask twice than assume once.'\n",
        }
        for relative, text in filled.items():
            (root / relative).write_text(text, encoding="utf-8")
        data = {"schema_version": "cnw_work_unit_draft_v2", "work_intent": "ORIGINAL_EPISODE",
                "unit_id": "BOOK-OPENING", "kind": "episode", "language_locale": "en-US",
                "pov": "Close third person", "target_visible_chars": 90, "min_visible_chars": 60,
                "max_visible_chars": 120, "chapter_context": "Mira's first evening in town.",
                "role_in_story": "Introduce Mira's first consequential choice.",
                "reader_reward": "See cautious trust begin through action.", "entry_state": "Mira knows no one.",
                "exit_state": "Mira accepts one limited offer of help.", "required_beats": [],
                "characters_in_scene": ["Mira", "Keeper"],
                "character_knowledge_boundary_ref": "90_canon/canon.md",
                "forbidden_future_revelations": ["Do not reveal the lighthouse secret."],
                "voice_sample_refs": ["Mira"], "first_episode": True,
                "review": {"fifth_lens": {"id": "reader-promise",
                    "responsibility": "Check the synthetic opening's reader promise."}},
                "arc_ref": "04_chapter_design/arc_01.md"}
        path = root / "contracts/BOOK-OPENING.draft.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        write_contract_draft(root, path)
        contract = json.loads((root / "contracts/BOOK-OPENING.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["work_intent"], "ORIGINAL_EPISODE")
        self.assertEqual(contract["source"]["source_origin"], "ORIGINAL_PROJECT")
        self.assertNotIn("source_file", contract["story"])
        self.assertNotIn("before_anchor", contract["story"])
        preparation = read_production_preparation(root, contract)
        self.assertIn("90_canon/canon.md", preparation["documents"])
        run = produce(type("Args", (), {"mode": "offline", "unit": None, "run_id": "ORIGINAL-PLOT",
                                         "work_id": "BOOK-OPENING", "contract": str(root / "contracts/BOOK-OPENING.json"),
                                         "project_root": str(root)})())
        self.assertEqual(run["provider_call"], "none")
        state = load_state(Path(run["path"]))
        self.assertEqual(state["literary_source_freeze_version"], "literary_source_freeze_v2")
        validate_literary_source_freeze(state, root)
        altered_version = {**state, "literary_source_freeze_version": "legacy_v1"}
        with self.assertRaisesRegex(ContractError, "LITERARY_SOURCE_FREEZE_VERSION_UNSUPPORTED"):
            validate_literary_source_freeze(altered_version, root)
        request = build_plot_request(root, contract)
        self.assertEqual(request["provider_call"], "none")
        joined = json.dumps(request["messages"], ensure_ascii=False)
        self.assertIn("Mira accepts one limited offer of help", joined)
        self.assertIn("这是无导入来源的原创工作", request["messages"][0]["content"])
        self.assertNotIn("与所给前后原文连续", request["messages"][0]["content"])
        self.assertIn("The story opens on Mira's first evening", joined)
        self.assertNotIn("Cangqi", joined)

    def test_contract_preflight_binds_project_intent_source_and_plot_without_writes(self):
        project_a = self.project("PREFLIGHTA")
        project_b = self.project("PREFLIGHTB")
        a = self.import_bytes(project_a, "a.md", b"A source begins.\nA source ends.\n")
        a_unselected = self.import_bytes(project_b, "a-unselected.md", b"UNSELECTED_A_CANARY\n")
        b = self.import_bytes(project_b, "b-selected.md", b"B selected source begins.\nB selected source ends.\n")
        insert_contract = self.draft(project_a, a, intent="INSERT_BETWEEN", unit_id="INSERT-PREFLIGHT",
                                     before_line=1, after_line=2)
        adapt_contract = self.draft(project_b, b, intent="ADAPT_SOURCE", unit_id="ADAPT-PREFLIGHT",
                                    start_line=1, end_line=1)
        adapt_a_contract = self.draft(project_b, a_unselected, intent="ADAPT_SOURCE",
            unit_id="ADAPT-A-PREFLIGHT", start_line=1, end_line=1)
        preflight_reports = []
        for root, contract, run_id in ((project_a, insert_contract, "PREFLIGHT-INSERT"),
                                       (project_b, adapt_contract, "PREFLIGHT-ADAPT")):
            contract_path = root / "contracts" / f"{contract['unit']['id']}.json"
            before = contract_path.read_bytes()
            report = build_contract_preflight(root, contract_path, run_id=run_id)
            self.assertEqual(report["status"], "READY_FOR_LIVE_PRODUCTION")
            self.assertEqual(report["contract_sha256"], sha(before))
            self.assertEqual(report["work_intent"], contract["work_intent"])
            self.assertEqual(report["provider_call"], "none")
            self.assertEqual(report["live_evidence_status"], "NOT_RUN")
            self.assertEqual(report["user_creative_acceptance"], "PENDING_USER_READING")
            self.assertFalse((root / "runs" / run_id).exists())
            digest_input = {key: value for key, value in report.items() if key != "evidence_digest"}
            self.assertEqual(report["evidence_digest"], sha(json.dumps(digest_input, ensure_ascii=False,
                sort_keys=True, separators=(",", ":")).encode("utf-8")))
            self.assertEqual(contract_path.read_bytes(), before)
            preflight_reports.append(report)
        b_report = build_contract_preflight(project_b, project_b / "contracts/ADAPT-PREFLIGHT.json",
                                            run_id="PREFLIGHT-ADAPT-RECHECK")
        self.assertEqual(b_report["source_identity"]["source_id"], b["source_id"])
        self.assertEqual(b_report["source_identity"]["source_revision_id"], b["source_revision_id"])
        self.assertEqual(b_report["selected_scope_sha256"], b_report["production_preparation_hashes"]["selected_source_excerpt"])
        self.assertEqual(verify_contract_preflight(project_b, project_b / "contracts/ADAPT-PREFLIGHT.json",
            run_id="PREFLIGHT-ADAPT-RECHECK", evidence=b_report)["status"],
            "CONTRACT_PREFLIGHT_EVIDENCE_VERIFIED")
        with self.assertRaisesRegex(ContractError, "PREFLIGHT_EVIDENCE_IDENTITY_MISMATCH"):
            verify_contract_preflight(project_b, project_b / "contracts/ADAPT-A-PREFLIGHT.json",
                run_id="PREFLIGHT-ADAPT-RECHECK", evidence=b_report)
        with self.assertRaisesRegex(ContractError, "PREFLIGHT_EVIDENCE_IDENTITY_MISMATCH"):
            verify_contract_preflight(project_b, project_b / "contracts/ADAPT-PREFLIGHT.json",
                run_id="PREFLIGHT-ADAPT-OTHER-RUN", evidence=b_report)
        with self.assertRaisesRegex(ContractError, "PREFLIGHT_EVIDENCE_IDENTITY_MISMATCH"):
            verify_contract_preflight(project_a, project_a / "contracts/INSERT-PREFLIGHT.json",
                run_id="PREFLIGHT-INSERT", evidence=b_report)
        altered_intent_evidence = dict(b_report, work_intent="INSERT_BETWEEN")
        altered_unsigned = {key: value for key, value in altered_intent_evidence.items() if key != "evidence_digest"}
        altered_intent_evidence["evidence_digest"] = sha(json.dumps(altered_unsigned, ensure_ascii=False,
            sort_keys=True, separators=(",", ":")).encode("utf-8"))
        with self.assertRaisesRegex(ContractError, "PREFLIGHT_EVIDENCE_IDENTITY_MISMATCH"):
            verify_contract_preflight(project_b, project_b / "contracts/ADAPT-PREFLIGHT.json",
                run_id="PREFLIGHT-ADAPT-RECHECK", evidence=altered_intent_evidence)
        self.assertNotEqual(b_report["project_instance_id"],
                            build_contract_preflight(project_a, project_a / "contracts/INSERT-PREFLIGHT.json",
                                                     run_id="PREFLIGHT-INSERT-RECHECK")["project_instance_id"])
        with self.assertRaisesRegex(ContractError, "CONTRACT_PATH_OUTSIDE_PROJECT"):
            build_contract_preflight(project_a, project_b / "contracts/ADAPT-PREFLIGHT.json",
                                     run_id="PREFLIGHT-CROSS-PROJECT-PATH")
        cross_contract = project_a / "contracts/CROSS-PROJECT.json"
        cross_contract.write_bytes((project_b / "contracts/ADAPT-PREFLIGHT.json").read_bytes())
        with self.assertRaisesRegex(ContractError, "PROJECT_INSTANCE_IDENTITY_MISMATCH"):
            build_contract_preflight(project_a, cross_contract, run_id="PREFLIGHT-CROSS-PROJECT")
        (project_b / "runs/PREFLIGHT-COLLISION").mkdir(parents=True)
        with self.assertRaisesRegex(ContractError, "PREFLIGHT_RUN_ID_COLLISION"):
            build_contract_preflight(project_b, project_b / "contracts/ADAPT-PREFLIGHT.json",
                                     run_id="PREFLIGHT-COLLISION")

        original = self.project("PREFLIGHTORIG")
        original_files = {
            "94_runtime/current_state.md": "Mira arrives at the coast.",
            "07_draft/manuscript_index.md": "No episodes published; this is the first.",
            "04_chapter_design/arc_01.md": "Mira chooses whether to accept help.",
            "04_chapter_design/arc_01_episode_details.md": "Establish the harbor and the offer.",
            "04_chapter_design/arc_index.md": "Arc 01: arrival and trust.",
            "90_canon/canon.md": "Mira has just arrived in town.",
            "90_canon/character_bible.md": "Mira is observant and cautious.",
            "90_canon/world_bible.md": "The town depends on a lighthouse.",
            "90_canon/timeline.md": "The story opens on Mira's first evening.",
            "90_canon/glossary.md": "Harbor Bell: the dusk signal.",
            "92_style_engine/style_guide.md": "Use close third person and restrained warmth.",
            "92_style_engine/forbidden_patterns.md": "Do not reveal the lighthouse secret.",
            "92_style_engine/character_voice_samples.md": "## Mira\n'I ask before I assume.'\n",
        }
        for relative, text in original_files.items():
            target = original / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        original_contract = self.draft(original, None, intent="ORIGINAL_EPISODE",
            unit_id="ORIGINAL-PREFLIGHT", first_episode=True, arc_ref="04_chapter_design/arc_01.md")
        original_report = build_contract_preflight(original,
            original / "contracts/ORIGINAL-PREFLIGHT.json", run_id="PREFLIGHT-ORIGINAL")
        self.assertEqual(original_report["source_identity"]["source_origin"], "ORIGINAL_PROJECT")
        self.assertEqual(original_report["work_intent"], "ORIGINAL_EPISODE")
        self.assertNotIn("source_file", original_contract["story"])
        self.assertNotIn("before_anchor", original_contract["story"])
        self.assertNotIn("after_anchor", original_contract["story"])
        self.assertEqual(original_report["status"], "READY_FOR_LIVE_PRODUCTION")
        args = type("OfflineProduceArgs", (), {"mode": "offline", "unit": None,
            "run_id": "RECOVERY-PLAN", "work_id": original_contract["unit"]["id"],
            "contract": str(original / "contracts/ORIGINAL-PREFLIGHT.json"),
            "project_root": str(original)})()
        run = produce(args)
        run_dir = Path(run["path"])
        state_path = run_dir / "run_state.json"
        state_raw = state_path.read_bytes()
        recovery = plan_recovery(run_dir, original)
        self.assertEqual(recovery["status"], "RECOVERY_PLAN_READY")
        self.assertEqual(recovery["next_stage_candidate"], "plot")
        self.assertEqual(recovery["provider_call"], "none")
        self.assertFalse(recovery["resume_executed"])
        self.assertFalse(recovery["state_mutated"])
        self.assertEqual(state_path.read_bytes(), state_raw)
        state = load_state(run_dir)
        state["stages"]["plot"]["execution_failures"] = [{"error_code": "SYNTHETIC_FAILURE"}]
        save_state(run_dir, state)
        failed_state = state_path.read_bytes()
        blocked_recovery = plan_recovery(run_dir, original)
        self.assertEqual(blocked_recovery["status"], "RECOVERY_BLOCKED_EXECUTION_HISTORY")
        self.assertEqual(blocked_recovery["execution_failures"], [{"stage": "plot",
            "status": "NOT_RUN", "execution_failure_count": 1}])
        self.assertEqual(state_path.read_bytes(), failed_state)
        _record_atom07_evidence("contract_preflight_and_recovery", {
            "preflight_reports": preflight_reports + [b_report, original_report],
            "cross_project_rejection": "PROJECT_INSTANCE_IDENTITY_MISMATCH",
            "cross_path_rejection": "CONTRACT_PATH_OUTSIDE_PROJECT",
            "cross_intent_rejection": "PREFLIGHT_EVIDENCE_IDENTITY_MISMATCH",
            "cross_source_revision_rejection": "PREFLIGHT_EVIDENCE_IDENTITY_MISMATCH",
            "cross_run_id_rejection": "PREFLIGHT_EVIDENCE_IDENTITY_MISMATCH",
            "run_id_collision_rejection": "PREFLIGHT_RUN_ID_COLLISION",
            "offline_recovery_ready": recovery,
            "failure_history_recovery_blocked": blocked_recovery,
            "run_state_sha256_before_failure_plan": sha(state_raw),
            "run_state_sha256_after_failure_plan": sha(failed_state),
            "run_state_mutated": state_path.read_bytes() != failed_state,
        })


if __name__ == "__main__":
    unittest.main()
