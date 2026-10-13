"""Synthetic, offline evidence for the R5 Atom-06 method boundary."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import cnw_contract, cnw_export, cnw_review, cnw_runner, cnw_sprint_live
from tools import cnw_roles


def _record_trace(group: str, evidence: dict) -> None:
    destination = os.environ.get("ATOM06_EVIDENCE_OUTPUT")
    if not destination:
        return
    path = Path(destination)
    document = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
        "schema_version": "atom06_synthetic_request_trace_v1", "execution": "SYNTHETIC_OFFLINE_ONLY", "groups": {}}
    document["groups"][group] = evidence
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _artifact_record(run: Path, stage: str, text: str) -> dict:
    path = _write(run, f"artifacts/{stage}.md", text)
    return {"status": "STAGE_MATERIALIZED", "artifact": {
        "path": path.relative_to(run).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }}


class Atom06Tests(unittest.TestCase):
    def test_actual_v2_live_gate_precedes_enabled_support_key_and_fee_checks(self):
        from types import SimpleNamespace
        from tests.test_cnw_work_intent_v2 import GenericWorkIntentV2Tests
        from tools import p2_cost_guard
        fixture = GenericWorkIntentV2Tests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        root = fixture.project('LIVE-GATE-ORDER')
        source = fixture.import_bytes(root, 'source.md', b'A fictional offer.\nA neighbor accepts.\n')
        original_get = os.environ.get
        def environment_get(key, *defaults):
            if key == 'DEEPSEEK_API_KEY':
                self.fail('closed V2 gate queried a Provider key')
            return original_get(key, *defaults)
        for number, mode in enumerate(('DISABLED', 'ENABLED')):
            unit_id = f'CLOSED-{number}'
            fixture.draft(root, source, intent='ADAPT_SOURCE', unit_id=unit_id,
                start_line=1, end_line=2, integrations={'nk': mode, 'critics': mode})
            with patch.object(os.environ, 'get', side_effect=environment_get), \
                 patch.object(cnw_runner, '_assert_support_components_available',
                     wraps=cnw_runner._assert_support_components_available) as support, \
                 patch.object(p2_cost_guard, 'provider_slot') as slot, \
                 patch.object(p2_cost_guard, 'command_reserve') as reserve, \
                 patch.object(cnw_runner.httpx, 'post') as http:
                with self.assertRaisesRegex(cnw_contract.ContractError, 'LIVE_AUTHORIZATION_REQUIRED'):
                    cnw_runner.produce(SimpleNamespace(mode='live', unit='scene', run_id=unit_id,
                        work_id=unit_id, project_root=str(root), contract=str(root/'contracts'/f'{unit_id}.json'),
                        create_only=True))
                support.assert_not_called()
                slot.assert_not_called()
                reserve.assert_not_called()
                http.assert_not_called()
            self.assertFalse((root/'runs'/unit_id).exists())
        _record_trace('actual_closed_live_gate_order', {'registered_project': 'LIVE-GATE-ORDER',
            'modes_tested': ['DISABLED', 'ENABLED'], 'blocking_code': 'LIVE_AUTHORIZATION_REQUIRED',
            'key_reads': 0, 'slots': 0, 'reservations': 0, 'http_calls': 0, 'runs_created': 0})

    def test_two_projects_use_their_own_four_role_sources_and_same_run_plot(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for suffix, marker in (("a", "PROJECT_A_CANARY"), ("b", "PROJECT_B_CANARY")):
                project = base / suffix
                run = project / "runs" / f"RUN_{suffix.upper()}"
                (run / "artifacts").mkdir(parents=True)
                files = {
                    "04_chapter_design/arc_01.md": f"ARC:{marker}",
                    "90_canon/canon.md": f"CANON:{marker} GUARD_SECRET_CANARY",
                    "90_canon/character_bible.md": f"CHARACTER:{marker}",
                    "90_canon/timeline.md": f"TIMELINE:{marker}",
                    "90_canon/world_bible.md": f"WORLD:{marker}",
                    "90_canon/glossary.md": f"GLOSSARY:{marker}",
                    "92_style_engine/style_guide.md": f"STYLE:{marker}",
                    "92_style_engine/forbidden_patterns.md": "GUARD_LINT_ONLY_CANARY",
                    "92_style_engine/character_voice_samples.md": "## Speaker\nVOICE_SAMPLE_ONLY",
                }
                for relative, text in files.items():
                    _write(project, relative, text)
                plot = f"PLOT_FROM_THIS_RUN:{marker}"
                cards = f"CARDS_FROM_THIS_RUN:{marker}"
                brief = (f"BRIEF_FOR_THIS_PROJECT:{marker}\n## Voice References\n"
                         "- Speaker — approved sample\n## Hard Constraints\nStay within the fixture.")
                state = {"stages": {
                    "plot": _artifact_record(run, "plot", plot),
                    "scene_cards": _artifact_record(run, "scene_cards", cards),
                    "writing_brief": _artifact_record(run, "writing_brief", brief),
                }}
                contract = {"project_id": f"FICT_{suffix.upper()}", "unit": {"id": "ep01", "kind": "episode",
                    "language": "zh-CN", "language_locale": "zh-CN", "pov": "Speaker",
                    "target_visible_chars": 20, "min_visible_chars": 10, "max_visible_chars": 30},
                    "story": {"arc_ref": "04_chapter_design/arc_01.md", "required_beats": []}}
                messages_by_role = {}
                for role in ("plot", "cards", "brief", "prose"):
                    sources = cnw_runner._role_sources(role, run, state, contract, project)
                    messages = cnw_roles.build_author_role_messages(role, contract, sources)
                    messages_by_role[role] = json.dumps(messages, ensure_ascii=False)

                self.assertIn(f"ARC:{marker}", messages_by_role["plot"])
                self.assertIn(f"CANON:{marker}", messages_by_role["plot"])
                self.assertIn(f"PLOT_FROM_THIS_RUN:{marker}", messages_by_role["cards"])
                self.assertIn(f"PLOT_FROM_THIS_RUN:{marker}", messages_by_role["brief"])
                self.assertIn(f"CARDS_FROM_THIS_RUN:{marker}", messages_by_role["brief"])
                self.assertIn(f"BRIEF_FOR_THIS_PROJECT:{marker}", messages_by_role["prose"])
                self.assertIn("VOICE_SAMPLE_ONLY", messages_by_role["prose"])
                self.assertNotIn("GUARD_SECRET_CANARY", messages_by_role["prose"])
                self.assertNotIn("GUARD_LINT_ONLY_CANARY", messages_by_role["prose"])
                other_marker = "PROJECT_B_CANARY" if suffix == "a" else "PROJECT_A_CANARY"
                for role, request in messages_by_role.items():
                    self.assertNotIn(other_marker, request, (suffix, role))
                _record_trace(f"role_requests_{suffix.upper()}", {"project": f"FICT_{suffix.upper()}", "work_id": "ep01",
                        "role_requests": [{"project": suffix.upper(), "role": role,
                            "allowed_input_keys": sorted(cnw_runner._role_sources(role, run, state, contract, project)),
                            "messages": json.loads(messages_by_role[role]),
                            "messages_sha256": hashlib.sha256(messages_by_role[role].encode("utf-8")).hexdigest(),
                            "consumer": "Plot->Cards same-run Plot; Plot+Cards->Brief; Brief+selected voice->Prose",
                            "guard_secret_in_prose": "GUARD_SECRET_CANARY" in messages_by_role["prose"],
                            "lint_only_canary_in_prose": "GUARD_LINT_ONLY_CANARY" in messages_by_role["prose"]}
                            for role in messages_by_role]})

    def test_english_and_chinese_prose_continuations_are_real_localized_messages(self):
        for locale, continuation_phrase in (("en-US", "Continue the same chapter in English"),
                                            ("zh-CN", "续写同一章简体中文正文")):
            with self.subTest(locale=locale), tempfile.TemporaryDirectory() as tmp:
                run = Path(tmp) / "project" / "runs" / "RUN"
                (run / "artifacts").mkdir(parents=True)
                contract = {"schema_version": "cnw_work_unit_v2", "project_id": "FICT_LANGUAGE",
                    "unit": {"id": "ep01", "kind": "episode", "language": locale,
                        "language_locale": locale, "length_metric": "unicode_visible_code_points",
                        "planning_mode": "author_plot", "target_visible_chars": 8,
                        "min_visible_chars": 6, "max_visible_chars": 12, "pov": "Speaker"},
                    "story": {"required_beats": []}}
                _write(run, "artifacts/contract.json", json.dumps(contract))
                state = {"run_id": "RUN", "stages": {"prose": {"status": "NOT_RUN"}}}
                messages = []
                responses = iter(("abc", "def"))
                def dispatch(*args, **kwargs):
                    messages.append(kwargs["messages"])
                    return next(responses), {"request_id": f"OFFLINE_{len(messages)}"}
                source = {
                    "07_draft/<work_id>_writing_brief.md": "## Voice References\n- Speaker\n## Hard Constraints\nFixture only.",
                    "92_style_engine/character_voice_samples.md": "## Speaker\nSynthetic voice.",
                }
                with patch.object(cnw_runner, "load_state", return_value=state), \
                     patch.object(cnw_runner, "_role_sources", return_value=source), \
                     patch.object(cnw_runner, "cnw_live_call", side_effect=dispatch), \
                     patch.object(cnw_runner, "_persist_stage"):
                    cnw_runner.execute_prose(run)
                self.assertEqual(len(messages), 2)
                self.assertIn(continuation_phrase, messages[1][0]["content"])
                joined = json.dumps(messages, ensure_ascii=False)
                if locale == "en-US":
                    self.assertNotIn("中文正文", joined)
                    self.assertIn("not a word count", joined)
                else:
                    self.assertIn("可见 Unicode 码点", joined)
                _record_trace(f"continuation_{locale}", {"locale": locale,
                    "messages": messages, "response_texts": ["abc", "def"], "consumer_result": "length accepted",
                    "message_sha256": [hashlib.sha256(json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest() for item in messages]})

    def test_legacy_v1_without_locale_keeps_historical_chinese_prose_and_refine(self):
        # v1 had no locale contract. Even when its legacy display-language field
        # says en-US, the historical CNW continuation and Refine prompts are Chinese.
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "project" / "runs" / "RUN"
            (run / "artifacts/revisions").mkdir(parents=True)
            contract = {"schema_version": "cnw_work_unit_v1", "project_id": "FICT_LEGACY",
                "unit": {"id": "ep01", "kind": "episode", "language": "en-US",
                    "target_visible_chars": 5, "min_visible_chars": 4, "max_visible_chars": 20,
                    "pov": "Speaker"}, "story": {"required_beats": []}}
            prose_state = {"run_id": "RUN", "stages": {"prose": {"status": "NOT_RUN"}}}
            prose_messages = []
            prose_responses = iter(("短", "这是正文"))
            def prose_dispatch(*args, **kwargs):
                prose_messages.append(kwargs["messages"])
                return next(prose_responses), {"request_id": f"OFFLINE_LEGACY_PROSE_{len(prose_messages)}"}
            with patch.object(cnw_runner, "_contract_for", return_value=contract), \
                 patch.object(cnw_runner, "load_state", return_value=prose_state), \
                 patch.object(cnw_runner, "_role_sources", return_value={
                     "07_draft/<work_id>_writing_brief.md": "## Voice References\n- Speaker\n## Hard Constraints\nFixture only.",
                     "92_style_engine/character_voice_samples.md": "## Speaker\nSynthetic voice."}), \
                 patch.object(cnw_runner, "cnw_live_call", side_effect=prose_dispatch), \
                 patch.object(cnw_runner, "_persist_stage"):
                cnw_runner.execute_prose(run)
            self.assertEqual(len(prose_messages), 2)
            self.assertEqual(prose_messages[0][0], {"role": "system", "content":
                "Write the complete story prose specified by the Writing Brief, using the voice samples selected by its Voice References. Output only the prose, without planning notes or commentary."})
            self.assertIn("续写同一章简体中文正文", prose_messages[1][0]["content"])
            self.assertNotIn("Continue the same chapter in English", prose_messages[1][0]["content"])

            state = {"run_id": "RUN", "stages": {
                stage: {"status": "NOT_RUN", "dependencies": [], "artifact": None}
                for stage in cnw_runner.CNW_STAGES}}
            cnw_runner.save_state(run, state)
            cnw_runner._persist_stage(run, "prose", "artifacts/prose.md", "这是原始正文")
            cnw_runner._persist_stage(run, "writing_brief", "artifacts/writing_brief.md", "保留合成节拍")
            cnw_runner._persist_stage(run, "adversarial_verify", "artifacts/verify.json",
                json.dumps({"findings": [], "verdicts": {}}))
            cnw_runner._persist_stage(run, "completeness_critic", "artifacts/completeness.json",
                json.dumps({"candidate_findings": [{"finding_id": "SYNTHETIC-1",
                    "lens_id": "story_specific", "issue": "synthetic omission", "evidence": "fixture"}]}))
            refine_messages = []
            def refine_dispatch(*args, **kwargs):
                refine_messages.append(kwargs["messages"])
                return "修订后的正文", {"request_id": "OFFLINE_LEGACY_REFINE"}
            with patch.object(cnw_runner, "_contract_for", return_value=contract), \
                 patch.object(cnw_runner, "_critics_hook", return_value={"status": "DISABLED"}), \
                 patch.object(cnw_runner, "cnw_live_call", side_effect=refine_dispatch):
                cnw_runner.execute_refine(run)
            self.assertEqual(len(refine_messages), 1)
            self.assertIn("你是 CNW Refine Agent", refine_messages[0][0]["content"])
            self.assertIn("按合同语言简体中文（zh-CN）修订", refine_messages[0][0]["content"])
            self.assertNotIn("You are the CNW Refine Agent", refine_messages[0][0]["content"])
            _record_trace("legacy_v1_chinese_compatibility", {
                "contract": contract, "locale_field": "absent", "legacy_language_field": "en-US",
                "historical_first_prose_prompt": "exact match to pre-Atom-06 builder at 659a1bd",
                "prose_requests": prose_messages, "prose_responses": ["短", "这是正文"],
                "refine_requests": refine_messages, "refine_response": "修订后的正文",
                "consumer_result": "actual v1 first Prose builder retained historical prompt identity; continuation and Refine retained Chinese instructions",
                "message_sha256": [hashlib.sha256(json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
                    for item in prose_messages + refine_messages]})

    def test_disabled_support_hooks_do_not_call_supplemental_components(self):
        contract = {"schema_version": "cnw_work_unit_v2", "integrations": {"nk": "DISABLED", "critics": "DISABLED"},
                    "unit": {"id": "ep01", "kind": "episode", "language": "en-US", "language_locale": "en-US",
                             "length_metric": "unicode_visible_code_points", "target_visible_chars": 20,
                             "min_visible_chars": 10, "max_visible_chars": 30}, "story": {"required_beats": []}}
        state = {"stages": {}}
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            run.mkdir()
            messages = []
            with patch.object(cnw_runner, "_contract_for", return_value=contract), \
                 patch.object(cnw_runner, "load_state", return_value=state), \
                 patch.object(cnw_runner, "_role_sources", return_value={"fixture": "only"}), \
                 patch.object(cnw_runner, "_author_messages", side_effect=lambda *a, **k: [{"role": "user", "content": "safe brief"}]), \
                 patch.object(cnw_runner, "cnw_live_call", side_effect=lambda *args, **kw: (messages.append(kw["messages"]) or "brief", {"request_id": "OFFLINE"})), \
                 patch.object(cnw_runner, "_validate_role"), patch.object(cnw_runner, "_persist_stage"), \
                 patch.object(cnw_runner, "_nk_pov") as nk, patch.object(cnw_runner, "_record_hook") as record:
                cnw_runner.execute_writing_brief(run)
                self.assertEqual(cnw_runner._critics_hook(run, "plot")["status"], "DISABLED")
                nk.assert_not_called()
                record.assert_called_once()
            self.assertNotIn("nk_perspective_reflection_support_only", json.dumps(messages))
            _record_trace("support_disabled", {"integrations": contract["integrations"],
                "writing_brief_messages": messages, "nk_call": "not_called", "critics_call": "not_called",
                "consumer_results": ["Brief request constructed without NK material", "CritiCS hook DISABLED"]})

    def test_enabled_unavailable_support_is_rejected_before_provider_work(self):
        contract = {"schema_version": "cnw_work_unit_v2", "integrations": {"nk": "ENABLED", "critics": "DISABLED"}}
        with tempfile.TemporaryDirectory() as tmp, patch.object(cnw_runner, "ROOT", Path(tmp)):
            with self.assertRaisesRegex(cnw_contract.ContractError, "ENABLED_BUT_UNAVAILABLE"):
                cnw_runner._assert_support_components_available(contract)
        _record_trace("support_enabled_unavailable", {"integrations": contract["integrations"],
            "result": "ENABLED_BUT_UNAVAILABLE", "provider_dispatch": "not reached"})

    def test_enabled_critics_runtime_failures_are_recorded_and_blocking(self):
        for failure_kind in ("missing", "timeout", "nonzero"):
            with self.subTest(failure_kind=failure_kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                # This legacy native-component fixture uses the real supported
                # runs namespace; a fake registered project is not authorization.
                run = root / "runs" / "RUN"
                input_path = _write(run, "artifacts/plot.md", "SYNTHETIC PLOT")
                state = {"stages": {"plot": {"artifact": {"path": "artifacts/plot.md"}}},
                         "support_hooks": {}}
                _write(run, "run_state.json", json.dumps(state))
                contract = {"schema_version": "cnw_work_unit_v2", "integrations": {"critics": "ENABLED"}}
                runtime = root / "runtime/envs/critics-api/Scripts/python.exe"
                if failure_kind != "missing":
                    runtime.parent.mkdir(parents=True)
                    runtime.write_text("fixture executable placeholder", encoding="utf-8")
                records = []
                with patch.object(cnw_runner, "ROOT", root), \
                     patch.object(cnw_runner, "_contract_for", return_value=contract), \
                     patch.object(cnw_runner, "load_state", return_value=state), \
                     patch.object(cnw_runner, "_record_hook", side_effect=lambda _run, _hook, evidence: records.append(evidence)), \
                     patch("subprocess.run", side_effect=(TimeoutError("fixture timeout") if failure_kind == "timeout" else None)) as process:
                    if failure_kind == "nonzero":
                        process.side_effect = None
                        process.return_value = type("Result", (), {"returncode": 7, "stderr": "synthetic failure"})()
                    expected = "ENABLED_BUT_UNAVAILABLE" if failure_kind == "missing" else "CRITICS_INVOCATION_FAILED"
                    with self.assertRaisesRegex(cnw_contract.ContractError, expected):
                        cnw_runner._critics_hook(run, "plot")
                self.assertEqual(len(records), 1)
                self.assertIn(records[0]["status"], {"ENABLED_BUT_UNAVAILABLE", "CRITICS_INVOCATION_FAILED", "FAILED"})
                self.assertEqual(records[0].get("input_sha256"), hashlib.sha256(input_path.read_bytes()).hexdigest())
                if failure_kind == "missing":
                    process.assert_not_called()
                _record_trace(f"critics_failure_{failure_kind}", {"recorded_hook": records[0],
                    "consumer_result": "blocking ContractError; no CNW continuation", "provider_call": "none"})

    def test_plot_and_refine_propagate_enabled_critics_failures(self):
        failure = cnw_contract.ContractError("CRITICS_INVOCATION_FAILED", "synthetic failure")
        contract = {"schema_version": "cnw_work_unit_v2", "integrations": {"critics": "ENABLED"},
            "unit": {"id": "synthetic", "kind": "scene", "language_locale": "en-US",
                "target_visible_chars": 10, "min_visible_chars": 5, "max_visible_chars": 15},
            "story": {"required_beats": []}}
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            run = project / "runs" / "RUN"
            (run / "artifacts/revisions").mkdir(parents=True)
            with patch.object(cnw_runner, "_contract_for", return_value=contract), \
                 patch.object(cnw_runner, "_run_dir_base", return_value=project), \
                 patch.object(cnw_runner, "build_plot_request", return_value={"production_preparation": {}, "messages": []}), \
                 patch.object(cnw_runner, "load_state", return_value={"stages": {"plot": {"artifact": {"path": "artifacts/plot.md"}}}}), \
                 patch.object(cnw_runner, "locked_run"), \
                 patch.object(cnw_runner, "_role_sources", return_value={}), \
                 patch.object(cnw_runner, "_author_messages", return_value=[]), \
                 patch.object(cnw_runner, "_planning_stage", return_value={"stage": "plot"}), \
                 patch.object(cnw_runner, "_critics_hook", side_effect=failure) as hook:
                with self.assertRaisesRegex(cnw_contract.ContractError, "CRITICS_INVOCATION_FAILED"):
                    cnw_runner.execute_plot(run)
                hook.assert_called_once_with(run, "plot")

            with patch.object(cnw_runner, "_contract_for", return_value=contract), \
                 patch.object(cnw_runner, "load_state", return_value={"stages": {
                     "refine": {"pending_findings": None, "refinement_attempt": None},
                     "prose": {}, "completeness_critic": {}}}), \
                 patch.object(cnw_runner, "_read_stage_text", side_effect=lambda _run, _state, stage:
                     '{"candidate_findings": []}' if stage == "completeness_critic" else "synthetic draft"), \
                 patch.object(cnw_runner, "_confirmed_findings", return_value=[]), \
                 patch.object(cnw_runner, "_critics_hook", side_effect=failure) as hook:
                with self.assertRaisesRegex(cnw_contract.ContractError, "CRITICS_INVOCATION_FAILED"):
                    cnw_runner.execute_refine(run)
                hook.assert_called_once_with(run, "prose")

    def test_project_specific_fifth_lens_responsibility_changes_only_its_packet(self):
        sources = {"style_guide": "style", "forbidden_patterns": "lint", "character_bible": "character",
            "voice_samples": "voice", "scene_cards": "cards", "writing_brief": "brief",
            "glossary": "glossary", "timeline": "timeline", "world_bible": "world",
            "project_specific_canon": "project canon"}
        first, second = dict(sources), dict(sources)
        first["fifth_lens_id"] = "reader-promise"
        second["fifth_lens_id"] = "argument-evidence"
        first["fifth_lens_responsibility"] = "Check whether the promised mystery receives an earned clue."
        second["fifth_lens_responsibility"] = "Check whether the argument's central claim is supported."
        first_packets = {lens: cnw_review.build_lens_input(lens, "synthetic draft", first) for lens in cnw_review.LENSES}
        second_packets = {lens: cnw_review.build_lens_input(lens, "synthetic draft", second) for lens in cnw_review.LENSES}
        for lens in cnw_review.LENSES:
            self.assertEqual(first_packets[lens]["input_sha256"] == second_packets[lens]["input_sha256"],
                lens != "story_specific")
        self.assertEqual(first_packets["story_specific"]["sources"]["fifth_lens_id"], "reader-promise")
        self.assertEqual(second_packets["story_specific"]["sources"]["fifth_lens_id"], "argument-evidence")
        self.assertIn(first["fifth_lens_responsibility"], first_packets["story_specific"]["author_lens_definition"])
        self.assertIn(second["fifth_lens_responsibility"], second_packets["story_specific"]["author_lens_definition"])
        first_messages = cnw_review.lens_messages(first_packets["story_specific"])
        second_messages = cnw_review.lens_messages(second_packets["story_specific"])
        first_serialized = json.dumps(first_messages, ensure_ascii=False, sort_keys=True)
        second_serialized = json.dumps(second_messages, ensure_ascii=False, sort_keys=True)
        self.assertNotEqual(first_serialized, second_serialized)
        self.assertIn(first["fifth_lens_responsibility"], first_serialized)
        self.assertNotIn(second["fifth_lens_responsibility"], first_serialized)
        self.assertIn(second["fifth_lens_responsibility"], second_serialized)
        self.assertNotIn(first["fifth_lens_responsibility"], second_serialized)
        _record_trace("fifth_lens_project_policy_isolation", {
            "synthetic_projects": [
                {"project": "FICT_MYSTERY", "packet": first_packets["story_specific"], "messages": first_messages,
                 "messages_sha256": hashlib.sha256(first_serialized.encode("utf-8")).hexdigest()},
                {"project": "FICT_ARGUMENT", "packet": second_packets["story_specific"], "messages": second_messages,
                 "messages_sha256": hashlib.sha256(second_serialized.encode("utf-8")).hexdigest()},
            ], "consumer_result": "actual story_specific messages differ; each carries only its own frozen project duty",
            "provider_call": "none; deterministic packet/message builders"})

    def test_review_source_consumer_rejects_changed_frozen_fifth_lens_duty(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            for relative in ("92_style_engine/style_guide.md", "92_style_engine/forbidden_patterns.md",
                "90_canon/character_bible.md", "92_style_engine/character_voice_samples.md",
                "90_canon/glossary.md", "90_canon/timeline.md", "90_canon/world_bible.md", "90_canon/canon.md"):
                _write(project, relative, "synthetic")
            contract = {"schema_version": "cnw_work_unit_v2", "review": {"fifth_lens": {
                "id": "reader-promise", "responsibility": "Approved synthetic responsibility.",
                "responsibility_sha256": "0" * 64}}}
            with patch.object(cnw_runner, "_read_stage_text", return_value="same-run synthetic stage"):
                with self.assertRaisesRegex(cnw_contract.ContractError, "FIFTH_LENS_CONTRACT_INVALID"):
                    cnw_runner._review_sources(Path(tmp) / "run", {"stages": {}}, contract, project)

    def test_fict_project_id_cannot_enable_live_fixture_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "outside-project"
            contracts = project / "contracts"
            contracts.mkdir(parents=True)
            contract = {"schema_version": "cnw_work_unit_v1", "project_id": "FICT_BAD",
                "source": {"zip_sha256": "a" * 64, "source_manifest_sha256": "b" * 64},
                "unit": {"id": "fixture-scene", "kind": "scene", "planning_mode": "legacy_frozen",
                    "language": "zh-CN", "pov": "Synthetic", "target_visible_chars": 30,
                    "min_visible_chars": 10, "max_visible_chars": 40, "policy_sha256": "c" * 64,
                    "required_beats": [{"beat_id": "B1", "budget_visible_chars": 30}]},
                "story": {"chapter_context": "Fixture", "role_in_story": "Fixture", "reader_reward": "Fixture",
                    "entry_state": "Before", "exit_state": "After", "before_anchor": {"sha256": "d" * 64},
                    "after_anchor": {"sha256": "e" * 64}, "required_beats": [{"beat_id": "B1", "budget_visible_chars": 30}],
                    "characters_in_scene": ["Synthetic"], "character_knowledge_boundary_ref": "fixture",
                    "forbidden_future_revelations": ["No fixture-only bypass"], "voice_sample_refs": ["fixture"]},
                "review": {"workflow_template_git_blob": "fixture", "cnw_reference_manifest_sha256": "f" * 64}}
            contract_path = _write(contracts, "contract.json", json.dumps(contract))
            args = type("Args", (), {"run_id": "FICT-BAD", "work_id": "fixture-scene", "unit": "scene",
                "contract": str(contract_path), "project_root": str(project), "mode": "live", "create_only": True})()
            with patch.object(cnw_runner, "ROOT", root), patch.object(cnw_runner, "cnw_live_call") as provider:
                with self.assertRaisesRegex(cnw_contract.ContractError, "PROJECT_ROOT_OUTSIDE_PRIVATE_WORKSPACE"):
                    cnw_runner.produce(args)
                with cnw_runner._offline_test_fixture_context(), self.assertRaisesRegex(
                        cnw_contract.ContractError, "LIVE_FIXTURE_FORBIDDEN"):
                    cnw_runner.produce(args)
                provider.assert_not_called()
            self.assertFalse((project / "runs/FICT-BAD").exists())
            _record_trace("fict_live_rejection", {"project_id": "FICT_BAD",
                "result": "PROJECT_ROOT_OUTSIDE_PRIVATE_WORKSPACE and LIVE_FIXTURE_FORBIDDEN",
                "provider_dispatch": "not reached", "run_created": False})

    def test_verifier_vote_matrix_uses_confirmed_threshold_and_uncertain_as_refutation(self):
        findings = [{"finding_id": "F1"}, {"finding_id": "F2"}]
        packets = cnw_review.verifier_packets(findings, "Synthetic full draft")
        self.assertEqual(len({item["input_sha256"] for item in packets}), 3)
        for not_refuted, expected in ((0, "REFUTED_OR_UNCERTAIN"), (1, "REFUTED_OR_UNCERTAIN"),
                                      (2, "CONFIRMED"), (3, "CONFIRMED")):
            votes = [{**packet, "votes": [{"finding_id": finding["finding_id"], "verdict":
                "not_refuted" if i < not_refuted else "uncertain"} for finding in findings]} for i, packet in enumerate(packets)]
            self.assertEqual(cnw_review.tally_verifiers(votes)["F1"]["status"], expected)
        bad = [{**packet, "votes": [{"finding_id": "F1", "verdict": "uncertain"}]} for packet in packets]
        bad[0]["votes"].append({"finding_id": "F1", "verdict": "refuted"})
        with self.assertRaisesRegex(ValueError, "duplicate vote"):
            cnw_review.tally_verifiers(bad)
        with self.assertRaisesRegex(cnw_contract.ContractError, "LIVE_VERIFIER_VOTES_INVALID"):
            cnw_runner._single_verifier_vote({"verifier_id": "correctness", "votes": [
                {"finding_id": "F2", "verdict": "not_refuted"}]}, "correctness", "F1")
        with self.assertRaisesRegex(cnw_contract.ContractError, "LIVE_VERIFIER_VOTES_INVALID"):
            cnw_runner._single_verifier_vote({"verifier_id": "correctness", "votes": [
                {"finding_id": "F1", "verdict": "uncertain"},
                {"finding_id": "F2", "verdict": "refuted"}]}, "correctness", "F1")

    def test_runner_consumes_five_isolated_lens_requests_then_three_votes_per_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "project" / "runs" / "RUN"
            (run / "artifacts").mkdir(parents=True)
            prose = "SYNTHETIC FULL DRAFT"
            prose_path = _write(run, "artifacts/prose.md", prose)
            sources = {
                "style_guide": "STYLE_SOURCE", "forbidden_patterns": "LINT_ONLY_CANARY",
                "character_bible": "CHARACTER_SOURCE", "voice_samples": "VOICE_SOURCE",
                "glossary": "GLOSSARY_SOURCE", "timeline": "TIMELINE_SOURCE",
                "world_bible": "WORLD_SOURCE", "scene_cards": "SAME_RUN_CARDS",
                "writing_brief": "SAME_RUN_BRIEF", "project_specific_canon": "PROJECT_CANON",
                "fifth_lens_id": "reader-promise",
                "fifth_lens_responsibility": "Check the project's confirmed reader promise.",
            }
            state = {"max_in_flight": 1, "stages": {
                "prose": {"status": "STAGE_MATERIALIZED", "artifact": {
                    "path": prose_path.relative_to(run).as_posix(),
                    "sha256": hashlib.sha256(prose_path.read_bytes()).hexdigest()}},
                "lint_layer2": _artifact_record(run, "lint2", json.dumps({"findings": []})),
            }}
            responsibility = "Check the project's confirmed reader promise."
            contract = {"schema_version": "cnw_work_unit_v2", "project_id": "FICT_REVIEW",
                        "unit": {"id": "ep01", "kind": "episode"}, "story": {},
                        "review": {"fifth_lens": {"id": "reader-promise", "responsibility": responsibility,
                            "responsibility_sha256": hashlib.sha256(responsibility.encode("utf-8")).hexdigest()}}}
            lens_requests = []
            lens_responses = []
            def lenses(_run, calls):
                lens_requests.extend(calls)
                results = []
                for index, call in enumerate(calls):
                    request = json.loads(call["messages"][1]["content"])
                    finding = []
                    if request["lens_id"] in {"style", "plot"}:
                        finding = [{"finding_id": "RAW", "severity": "minor", "issue": request["lens_id"]}]
                    results.append((json.dumps({"lens_id": call["role_id"], "findings": finding}),
                        {"request_id": f"LENS_{index}", "provider_request_id": f"OFFLINE_LENS_{index}"}))
                lens_responses.extend({"request_id": f"LENS_{index}", "response": json.loads(result[0]),
                    "identity": result[1]} for index, result in enumerate(results))
                return results
            with patch.object(cnw_runner, "load_state", return_value=state), \
                 patch.object(cnw_runner, "_contract_for", return_value=contract), \
                 patch.object(cnw_runner, "_run_dir_base", return_value=run.parents[1]), \
                 patch.object(cnw_runner, "_review_sources", return_value=sources), \
                 patch.object(cnw_runner, "_parallel_provider_calls", side_effect=lenses), \
                 patch.object(cnw_runner, "_persist_stage"):
                result = cnw_runner.execute_five_lenses(run)
            self.assertEqual(result["lenses"], 5)
            self.assertEqual({item["role_id"] for item in lens_requests}, set(cnw_review.LENSES))
            packets = [json.loads(item["messages"][1]["content"]) for item in lens_requests]
            self.assertEqual(len({item["lens_id"] for item in packets}), 5)
            self.assertTrue(all(set(item["sources"]) == set(cnw_review.LENSES[item["lens_id"]]) |
                ({"fifth_lens_id", "fifth_lens_responsibility"} if item["lens_id"] == "story_specific" else set()) for item in packets))
            fifth_packet = next(item for item in packets if item["lens_id"] == "story_specific")
            self.assertEqual(fifth_packet["sources"]["fifth_lens_id"], "reader-promise")
            self.assertEqual(fifth_packet["sources"]["fifth_lens_responsibility"], responsibility)
            self.assertIn(responsibility, fifth_packet["author_lens_definition"])
            self.assertTrue(all("findings" not in item for item in packets))
            index_path = run / "artifacts/multi_lens_review.index.json"
            state["stages"]["multi_lens_review"] = {"status": "STAGE_MATERIALIZED", "artifact": {
                "path": index_path.relative_to(run).as_posix(),
                "sha256": hashlib.sha256(index_path.read_bytes()).hexdigest()}}

            vote_requests = []
            vote_responses = []
            def verifiers(_run, calls):
                vote_requests.extend(calls)
                results = []
                offset = len(vote_requests) - len(calls)
                for index, call in enumerate(calls):
                    request = json.loads(call["messages"][1]["content"])
                    vote = "uncertain" if call["role_id"] == "correctness" else "not_refuted"
                    results.append((json.dumps({"verifier_id": call["role_id"], "votes": [
                        {"finding_id": request["finding_id"], "verdict": vote, "evidence": "Synthetic only"}]}),
                        {"request_id": f"VOTE_{offset + index}", "provider_request_id": f"OFFLINE_VOTE_{offset + index}"}))
                vote_responses.extend({"request_id": f"VOTE_{offset + index}", "response": json.loads(item[0]),
                    "identity": item[1]} for index, item in enumerate(results))
                return results
            with patch.object(cnw_runner, "load_state", return_value=state), \
                 patch.object(cnw_runner, "_contract_for", return_value=contract), \
                 patch.object(cnw_runner, "_run_dir_base", return_value=run.parents[1]), \
                 patch.object(cnw_runner, "_review_sources", return_value=sources), \
                 patch.object(cnw_runner, "_parallel_provider_calls", side_effect=verifiers), \
                 patch.object(cnw_runner, "_persist_stage"):
                result = cnw_runner.execute_three_verifiers(run)
            self.assertEqual(result["findings"], 2)
            self.assertEqual(result["confirmed"], 2)
            self.assertEqual(len(vote_requests), 6)
            by_finding = {}
            for call in vote_requests:
                packet = json.loads(call["messages"][1]["content"])
                by_finding.setdefault(packet["finding_id"], set()).add(call["role_id"])
                self.assertNotIn("other verifier conclusions", call["messages"][1]["content"])
            self.assertTrue(all(ids == set(cnw_review.VERIFIERS) for ids in by_finding.values()))
            _record_trace("review_requests", {"lens_requests": [{"role_id": item["role_id"],
                "messages": item["messages"], "messages_sha256": hashlib.sha256(json.dumps(item["messages"], ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()} for item in lens_requests],
                "lens_responses": lens_responses,
                "vote_requests": [{"role_id": item["role_id"], "messages": item["messages"],
                    "messages_sha256": hashlib.sha256(json.dumps(item["messages"], ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()} for item in vote_requests],
                "vote_responses": vote_responses,
                "consumer_result": result, "provider_requests": "none; injected transport"})

    def test_completeness_candidate_reaches_refine_and_future_lens_feedback_consumer(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            run = project / "runs" / "RUN"
            (run / "artifacts").mkdir(parents=True)
            contract = {"schema_version": "cnw_work_unit_v2", "project_id": "FICT_COMPLETE",
                "integrations": {"nk": "DISABLED", "critics": "DISABLED"},
                "unit": {"id": "ep01", "kind": "scene", "language": "en-US", "language_locale": "en-US",
                    "length_metric": "unicode_visible_code_points", "target_visible_chars": 16,
                "min_visible_chars": 10, "max_visible_chars": 24}, "story": {"required_beats": []},
                "review": {"fifth_lens": {"id": "story_specific",
                    "responsibility": "Check the synthetic project's confirmed reader promise.",
                    "responsibility_sha256": hashlib.sha256(b"Check the synthetic project's confirmed reader promise.").hexdigest()}}}
            _write(run, "artifacts/contract.json", json.dumps(contract))
            source_files = {
                "92_style_engine/style_guide.md": "STYLE", "92_style_engine/forbidden_patterns.md": "LINT",
                "90_canon/character_bible.md": "CHARACTER", "92_style_engine/character_voice_samples.md": "VOICE",
                "90_canon/glossary.md": "GLOSSARY", "90_canon/timeline.md": "TIMELINE",
                "90_canon/world_bible.md": "WORLD", "90_canon/canon.md": "PROJECT_CANON",
            }
            for relative, text in source_files.items():
                _write(project, relative, text)
            initial = {"schema_version": "atom06_test_fixture", "run_id": "RUN", "work_id": "ep01",
                "project_id": "FICT_COMPLETE", "status": "RUNNING", "support_hooks": {},
                "provider_requests": [], "max_in_flight": 1,
                "stages": {stage: {"status": "NOT_RUN", "dependencies": [], "artifact": None}
                           for stage in cnw_runner.CNW_STAGES}}
            cnw_runner.save_state(run, initial)
            cnw_runner._persist_stage(run, "prose", "artifacts/prose.md", "SYNTHETIC UNANSWERED DRAFT")
            cnw_runner._persist_stage(run, "scene_cards", "artifacts/cards.md", "A synthetic unresolved question.")
            cnw_runner._persist_stage(run, "writing_brief", "artifacts/brief.md", "Retain the unresolved question.")
            finding = {"finding_id": "CANON-OMISSION-1", "lens_id": "story_specific",
                "issue": "A confirmed project question is not resolved in the draft.", "evidence": "unresolved question",
                "prompt_update": "On the next review, check whether the confirmed project question receives a concrete response."}
            verify = {"findings": [], "verdicts": {}}
            cnw_runner._persist_stage(run, "adversarial_verify", "artifacts/verify.json", json.dumps(verify))
            completeness_request = []
            def completeness_transport(*args, **kwargs):
                completeness_request.append(kwargs["messages"])
                return json.dumps({"candidate_findings": [finding]}), {
                    "request_id": "OFFLINE_COMPLETENESS", "provider_request_id": "SYNTH_COMPLETENESS"}
            with patch.object(cnw_runner, "cnw_live_call", side_effect=completeness_transport):
                cnw_runner.execute_completeness(run)
            feedback_path = project / "08_review/lens_feedback/story_specific.json"
            self.assertTrue(feedback_path.is_file())
            refine_requests = []
            def refine_transport(*args, **kwargs):
                refine_requests.append(kwargs["messages"])
                request = json.loads(kwargs["messages"][1]["content"])
                self.assertEqual(request["confirmed_findings"]["completeness_candidates"], [finding])
                return "Answer: resolved.", {
                    "request_id": "OFFLINE_REFINE", "provider_request_id": "SYNTH_REFINE"}
            with patch.object(cnw_runner, "cnw_live_call", side_effect=refine_transport):
                cnw_runner.execute_refine(run)
            fresh_state = cnw_runner.load_state(run)
            self.assertEqual(fresh_state["stages"]["refine"]["affected_lenses"], ["story_specific"])
            review_sources = cnw_runner._review_sources(run, fresh_state, contract, project)
            self.assertIn(finding["prompt_update"], review_sources["lens_feedback:story_specific"])
            _record_trace("completeness_refine_feedback", {"candidate": finding,
                "completeness_messages": completeness_request,
                "feedback_file": json.loads(feedback_path.read_text(encoding="utf-8")),
                "refine_messages": refine_requests,
                "refine_messages_sha256": [hashlib.sha256(json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest() for item in refine_requests],
                "next_review_sources": {"story_specific_feedback": review_sources["lens_feedback:story_specific"]},
                "consumer_result": {"affected_lenses": fresh_state["stages"]["refine"]["affected_lenses"],
                    "refine_status": fresh_state["stages"]["refine"]["status"]},
                "re_review": "DEFERRED_TO_ATOM_09"})

    def test_sprint_thresholds_are_read_by_the_active_strategy_consumer(self):
        self.assertEqual(cnw_sprint_live._criteria(), {"size": 5, "min_score": 75,
            "max_p0_findings": 0, "max_p1_findings": 2})

    def test_export_uses_the_frozen_project_locale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "project" / "runs" / "RUN"
            (run / "artifacts").mkdir(parents=True)
            contract = {"schema_version": "cnw_work_unit_v1", "project_id": "FICT_EXPORT",
                "unit": {"id": "ep01", "language": "en-US", "language_locale": "en-US"},
                "source": {}, "story": {}}
            _write(run, "artifacts/contract.json", json.dumps(contract))
            with patch.object(cnw_export, "ROOT", root):
                result = cnw_export.export_reading_package(run, {"run_id": "RUN", "stages": {}},
                    project_root=run.parents[1])
            html = (Path(result["deliverables"]) / "03_前后文连读.html").read_text(encoding="utf-8")
            self.assertIn('<html lang="en-US">', html)


if __name__ == "__main__":
    unittest.main()
