from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from tools import cnw_runner
from tools.cnw_contract import ContractError


ROOT = Path(__file__).resolve().parents[1]


def synthetic_contract():
    return {
        "schema_version": "cnw_work_unit_v1", "project_id": "FICT_CNW_TEST",
        "source": {"zip_sha256": "a" * 64, "source_manifest_sha256": "b" * 64},
        "unit": {"id": "FICT_SCENE_A", "kind": "scene", "planning_mode": "legacy_frozen",
                 "language": "zh-CN", "pov": "Fictional POV", "target_visible_chars": 1800,
                 "min_visible_chars": 1500, "max_visible_chars": 2100, "policy_sha256": "c" * 64},
        "story": {"chapter_context": "Synthetic test context", "role_in_story": "Test only",
                  "reader_reward": "A clear test outcome", "entry_state": "Before fixture event",
                  "exit_state": "After fixture event", "before_anchor": {"scene": "FIXTURE", "source_line": 1, "sha256": "d" * 64},
                  "after_anchor": {"scene": "FIXTURE", "source_line": 2, "sha256": "e" * 64},
                  "required_beats": [{"beat_id": f"B{i}", "goal": f"Synthetic beat {i}", "budget_visible_chars": size}
                                     for i, size in enumerate((300, 500, 600, 400), 1)],
                  "characters_in_scene": ["Fictional POV"], "character_knowledge_boundary_ref": "fixture://knowledge",
                  "forbidden_future_revelations": ["No fixture secret"], "voice_sample_refs": ["fixture://voice"]},
        "review": {"workflow_template_git_blob": "fixture", "require_cnw_11_stages": True,
                   "require_3_verifiers": True, "require_completeness_critic": True,
                   "require_re_review": True, "cnw_reference_manifest_sha256": "f" * 64},
    }


class RunnerTests(unittest.TestCase):
    def test_duplicate_local_finding_ids_receive_stable_independent_votes(self):
        run = self.base / "runs/FICT_SCENE_A"
        cnw_runner._persist_stage(run, "prose", "artifacts/prose.md", "MOCK full prose")
        cnw_runner._persist_stage(run, "lint_layer2", "artifacts/lint.json", '{"findings":[]}')
        sources = {key: "MOCK source" for key in ("scene_cards", "writing_brief", "character_bible", "timeline", "glossary")}
        def lenses(run_dir, calls):
            results = []
            for call in calls:
                lens = call["role_id"]
                entries = [{"finding_id": "F1", "issue": "First issue"}, {"finding_id": "F1", "issue": "Second issue"}] if lens == "style" else [{"finding_id": "F1", "issue": "Character issue"}] if lens == "character" else []
                results.append((json.dumps({"lens_id": lens, "findings": entries}),
                    {"request_id": "MOCK-" + lens, "provider_request_id": "MOCK-PROVIDER-" + lens}))
            return results
        with patch.object(cnw_runner, "_review_sources", return_value=sources), \
                patch("tools.cnw_review.build_lens_input", side_effect=lambda lens, draft, src: {"lens_id": lens, "input_sha256": "MOCK-SHA-" + lens}), \
                patch("tools.cnw_review.lens_messages", return_value=[]), \
                patch.object(cnw_runner, "_parallel_provider_calls", side_effect=lenses):
            cnw_runner.execute_five_lenses(run)
            first = json.loads(cnw_runner._read_stage_text(run, cnw_runner.load_state(run), "multi_lens_review"))
            cnw_runner.execute_five_lenses(run)
            repeated = json.loads(cnw_runner._read_stage_text(run, cnw_runner.load_state(run), "multi_lens_review"))
        self.assertEqual(first["findings"], repeated["findings"])
        findings = first["findings"]
        self.assertEqual(len({row["finding_id"] for row in findings}), 3)
        style = [row for row in findings if row["lens_id"] == "style"]
        self.assertEqual([row["lens_finding_id"] for row in style], ["F1", "F1"])
        self.assertEqual([row["lens_finding_index"] for row in style], [1, 2])
        self.assertTrue(all(row["lens_provider_request_id"] == "MOCK-PROVIDER-style" for row in style))
        refuted_id = style[1]["finding_id"]
        sent = []
        def verify(run_dir, calls):
            sent.extend(calls)
            return [(json.dumps({"verifier_id": call["role_id"], "votes": [{"finding_id": call["extra"]["finding_id"],
                     "verdict": "refuted" if call["extra"]["finding_id"] == refuted_id else "not_refuted"}]}),
                     {"request_id": f"MOCK-{call['extra']['finding_id']}-{call['role_id']}",
                      "provider_request_id": f"MOCK-PROVIDER-{call['extra']['finding_id']}-{call['role_id']}"}) for call in calls]
        with patch.object(cnw_runner, "_review_sources", return_value=sources), \
                patch.object(cnw_runner, "_parallel_provider_calls", side_effect=verify):
            cnw_runner.execute_three_verifiers(run)
        report = json.loads(cnw_runner._read_stage_text(run, cnw_runner.load_state(run), "adversarial_verify"))
        self.assertEqual(len(sent), 9)
        self.assertEqual(len(report["verdicts"]), 3)
        for finding in findings:
            fid = finding["finding_id"]
            calls = [call for call in sent if call["extra"]["finding_id"] == fid]
            self.assertEqual({call["role_id"] for call in calls}, set(cnw_runner.VERIFIER_IDS))
            for call in calls:
                packet = json.loads(call["messages"][1]["content"])
                self.assertEqual(packet["claim"], finding)
            self.assertEqual(report["verdicts"][fid]["status"], "REFUTED_OR_UNCERTAIN" if fid == refuted_id else "CONFIRMED")
        surviving = cnw_runner._confirmed_findings(run, cnw_runner.load_state(run))
        self.assertEqual(len(surviving), 2)
        self.assertNotIn(refuted_id, {row["finding_id"] for row in surviving})

    def test_ambiguous_historical_finding_index_is_rejected_before_provider(self):
        run = self.base / "runs/FICT_SCENE_A"
        cnw_runner._persist_stage(run, "prose", "artifacts/prose.md", "MOCK full prose")
        cnw_runner._persist_stage(run, "lint_layer2", "artifacts/lint.json", '{"findings":[]}')
        for ids in (("style-F1", "style-F1"), ("",), (None,)):
            with self.subTest(ids=ids):
                cnw_runner._persist_stage(run, "multi_lens_review", "artifacts/lens-index.json",
                    json.dumps({"findings": [{"finding_id": fid} for fid in ids]}))
                with patch.object(cnw_runner, "_parallel_provider_calls") as calls:
                    with self.assertRaisesRegex(ContractError, "LIVE_FINDING_IDENTITY_INVALID"):
                        cnw_runner.execute_three_verifiers(run)
                    calls.assert_not_called()
        cnw_runner._persist_stage(run, "adversarial_verify", "artifacts/verify.json",
            json.dumps({"findings": [{"finding_id": "style-F1"}, {"finding_id": "style-F1"}],
                        "verdicts": {"style-F1": {"status": "CONFIRMED"}}}))
        with self.assertRaisesRegex(ContractError, "LIVE_FINDING_IDENTITY_INVALID"):
            cnw_runner._confirmed_findings(run, cnw_runner.load_state(run))
        with patch.object(cnw_runner, "cnw_live_call") as calls:
            with self.assertRaisesRegex(ContractError, "LIVE_FINDING_IDENTITY_INVALID"):
                cnw_runner.execute_completeness(run)
            calls.assert_not_called()

    def test_native_critics_result_reaches_refine_and_is_verified_on_reuse(self):
        from tools import cnw_critics_adapter as adapter
        from types import SimpleNamespace
        run = self.base / "runs/FICT_SCENE_A"
        prose = "窗边脚步停了。" * 210
        finding = {"finding_id": "C1", "lens_id": "style", "evidence": "窗边脚步停了。", "issue": "Repetition", "severity": "P2"}
        for stage, value in (("prose", prose), ("writing_brief", "Keep the same scene and Canon."),
                             ("adversarial_verify", json.dumps({"findings": [finding], "verdicts": {"C1": {"status": "CONFIRMED"}}})),
                             ("completeness_critic", '{"candidate_findings":[]}')):
            cnw_runner._persist_stage(run, stage, f"artifacts/{stage}.md", value)
        executable = self.base / "runtime/envs/critics-api/Scripts/python.exe"
        executable.parent.mkdir(parents=True)
        executable.write_text("MOCK executable; never launched", encoding="utf-8")
        native = {"voice": "MOCK voice alternative", "image": "MOCK imagery alternative", "select": "MOCK selected wording"}
        templates = adapter.native_text_templates()
        conversation_template = adapter.native_conversation_template()
        def subprocess_result(command, **kwargs):
            source = Path(command[command.index("--input") + 1])
            self.assertEqual(source.read_text(encoding="utf-8").strip(), finding["evidence"])
            directory = self.base / "runs" / command[command.index("--run-name") + 1]
            directory.mkdir()
            output = directory / "text_refinement.json"
            output.write_text(json.dumps(native), encoding="utf-8")
            build = json.loads(adapter.PATCH_INDEX.read_text(encoding="utf-8"))["runtime_build_id"]
            receipt = {"action": "text-refine", "status": "SUCCEEDED", "model": "deepseek-flash", "base_url": "https://api.deepseek.com/v1",
                       "build": f"runtime/patched/CritiCS/{build}", "input_sha256": cnw_runner.sha(source.read_bytes()).upper(), "output_sha256": cnw_runner.sha(output.read_bytes()).upper()}
            (directory / "run_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
            prompts = {"image": templates["refine_prompt_image"].format(story=source.read_text(encoding="utf-8")),
                       "voice": templates["refine_prompt_voice"].format(story=source.read_text(encoding="utf-8")),
                       "select": templates["choose_critic"].format(Image_refinement=native["image"], Voice_refinement=native["voice"])}
            calls = [{"http_status": 200, "request": {"messages": [{"role": "user", "content": conversation_template.format(history="", input=prompts[key])}]}, "response": {"id": f"MOCK-{key}", "model": "deepseek-flash", "choices": [{"finish_reason": "stop", "message": {"content": native[key]}}]}} for key in ("image", "voice", "select")]
            (directory / "provider-calls.json").write_text(json.dumps(calls), encoding="utf-8")
            return SimpleNamespace(returncode=0)
        def refine_provider(*args, **kwargs):
            request = json.loads(kwargs["messages"][1]["content"])
            self.assertEqual(request["confirmed_findings"]["critics_supplement"]["result"], native)
            self.assertEqual(request["confirmed_findings"]["confirmed"], [finding])
            return prose + "甲" * 100, {"request_id": "MOCK-REFINE"}
        with patch.object(adapter, "ROOT", self.base), patch.object(adapter, "native_text_templates", return_value=templates), patch.object(adapter, "native_conversation_template", return_value=conversation_template), patch("subprocess.run", side_effect=subprocess_result) as process, \
                patch.object(cnw_runner, "cnw_live_call", side_effect=refine_provider):
            with patch.object(adapter, "read_native_result", side_effect=ContractError("CRITICS_NATIVE_DEPENDENCY_MISMATCH", "MOCK validator failure")):
                with self.assertRaisesRegex(ContractError, "CRITICS_NATIVE_DEPENDENCY_MISMATCH"):
                    cnw_runner._critics_hook(run, "prose")
            self.assertEqual(cnw_runner.load_state(run)["support_hooks"]["critics_text"]["status"], "NATIVE_RESULT_PENDING")
            cnw_runner.execute_refine(run)
            supplement = cnw_runner.load_state(run)["support_hooks"]["critics_text"]
            self.assertEqual(supplement["result"], native)
            plan = json.loads((run / "artifacts/revisions/revision-1.plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["supplementary_sources"][0]["result"], native)
            cnw_runner._critics_hook(run, "prose")
            self.assertEqual(process.call_count, 1)
            path = self.base / "runs" / supplement["run_name"] / "text_refinement.json"
            receipt_path = path.parent / "run_receipt.json"
            saved_output, saved_receipt = path.read_bytes(), receipt_path.read_bytes()
            swapped = dict(native, voice=native["image"], image=native["voice"])
            path.write_text(json.dumps(swapped), encoding="utf-8")
            changed_receipt = json.loads(saved_receipt)
            changed_receipt["output_sha256"] = cnw_runner.sha(path.read_bytes()).upper()
            receipt_path.write_text(json.dumps(changed_receipt), encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "CRITICS_RESULT_RESPONSE_MISMATCH"):
                adapter.read_native_result(supplement["run_name"], action="text-refine", input_path=run / "artifacts/support/critics-excerpt.md")
            path.write_bytes(saved_output)
            receipt_path.write_bytes(saved_receipt)
            calls_path = path.parent / "provider-calls.json"
            saved_calls = calls_path.read_bytes()
            calls = json.loads(saved_calls)
            calls[1]["response"]["id"] = calls[0]["response"]["id"]
            calls_path.write_text(json.dumps(calls), encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "CRITICS_PROVIDER_ID_DUPLICATED"):
                adapter.read_native_result(supplement["run_name"], action="text-refine", input_path=run / "artifacts/support/critics-excerpt.md")
            calls_path.write_bytes(saved_calls)
            path.write_text('{}', encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "CRITICS_RECEIPT_HASH_MISMATCH"):
                cnw_runner._critics_hook(run, "prose")
            self.assertEqual(process.call_count, 1)

    def test_critics_excerpt_limits_whole_scene_evidence_to_five_sentences(self):
        run = self.base / "runs/FICT_SCENE_A"
        prose = "甲停步。乙回头！丙抬手？丁放下碗。戊开门。己关窗。庚离开。"
        for stage, value in (("prose", prose),
                             ("adversarial_verify", json.dumps({"findings": [{"finding_id": "S", "evidence": prose}], "verdicts": {"S": {"status": "CONFIRMED"}}})),
                             ("completeness_critic", '{"candidate_findings":[]}')):
            cnw_runner._persist_stage(run, stage, f"artifacts/{stage}.md", value)
        path = cnw_runner._critics_excerpt(run, cnw_runner.load_state(run))
        mapping = json.loads(path.with_suffix(".sources.json").read_text(encoding="utf-8"))
        self.assertEqual(len(mapping["selected_sentences"]), 5)
        self.assertNotIn("己关窗", path.read_text(encoding="utf-8"))
        for row in mapping["selected_sentences"]:
            self.assertEqual(prose[row["start"]:row["end"]], row["text"])

    def test_critics_text_skips_unrelated_or_refuted_findings(self):
        run = self.base / "runs/FICT_SCENE_A"
        for stage, value in (("prose", "Existing prose."),
                             ("adversarial_verify", json.dumps({"findings": [{"finding_id": "R", "evidence": "Existing prose."}], "verdicts": {"R": {"status": "REFUTED"}}})),
                             ("completeness_critic", '{"candidate_findings":[{"evidence":"Absent quote"}]}')):
            cnw_runner._persist_stage(run, stage, f"artifacts/{stage}.md", value)
        with patch("subprocess.run") as process:
            self.assertEqual(cnw_runner._critics_hook(run, "prose")["status"], "NO_RELEVANT_EXCERPT")
            process.assert_not_called()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cnw-runner-")
        self.base = Path(self.temp.name)
        (self.base / "runs").mkdir()
        self.project = self.base
        (self.base / "config").mkdir()
        (self.base / "tools").mkdir()
        (self.base / "config/production.example.json").write_text(json.dumps({"provider": {"max_in_flight": 1}, "cost_guard": {"persist_across_run_ids": True}}), encoding="utf-8")
        (self.base / "tools/p2_cost_guard.py").write_text("# shared cost guard fixture", encoding="utf-8")
        self.contract_dir = self.project / "contracts"
        self.contract_dir.mkdir()
        self.contract = synthetic_contract()
        self.root_patch = patch.object(cnw_runner, "ROOT", self.base)
        self.workflow_patch = patch.object(cnw_runner, "WORKFLOW_PATH", ROOT / "runtime/reference/cnw_97ad71fe5e5e/templates/config/workflow.template.yml")
        self.root_patch.start()
        self.workflow_patch.start()
        self._produce_contract(self.contract, "FICT_SCENE_A", "fixture-a.json")

    def tearDown(self):
        self.workflow_patch.stop()
        self.root_patch.stop()
        self.temp.cleanup()

    def _write_contract(self, value, name):
        path = self.contract_dir / name
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _produce_contract(self, value, run_id, name):
        path = self._write_contract(value, name)
        args = argparse.Namespace(run_id=run_id, work_id=value["unit"]["id"], unit="scene", contract=str(path), project_root=str(self.project), mode="offline")
        with cnw_runner._offline_test_fixture_context():
            return cnw_runner.produce(args)

    def test_fict_prefix_does_not_bypass_live_source_preflight(self):
        path = self._write_contract(self.contract, "create-only.json")
        args = argparse.Namespace(run_id="CREATE-ONLY", work_id=self.contract["unit"]["id"],
            unit="scene", contract=str(path), project_root=str(self.project), mode="live", create_only=True)
        with self.assertRaisesRegex(ContractError, "PROJECT_ROOT_OUTSIDE_PRIVATE_WORKSPACE"):
            cnw_runner.produce(args)
        with cnw_runner._offline_test_fixture_context(), self.assertRaisesRegex(ContractError, "LIVE_FIXTURE_FORBIDDEN"):
            cnw_runner.produce(args)
        self.assertFalse((self.base / "runs/CREATE-ONLY").exists())

    def test_over_limit_prose_recovers_with_same_brief_and_voices_without_splicing(self):
        run = self.base / "runs/FICT_SCENE_A"
        maximum = self.contract["unit"]["max_visible_chars"]
        minimum = self.contract["unit"]["min_visible_chars"]
        messages = [{"role": "system", "content": "Only prose"}, {"role": "user", "content": '{"writing_brief":"brief","voice_samples":"selected"}'}]
        sent = []
        def provider(*args, **kwargs):
            sent.append(kwargs["messages"])
            return ("甲" * (maximum + 1) if len(sent) == 1 else "乙" * minimum), {"request_id": f"MOCK-{len(sent)}"}
        with patch.object(cnw_runner, "_role_sources", return_value={}), patch.object(cnw_runner, "_author_messages", return_value=messages), patch.object(cnw_runner, "cnw_live_call", side_effect=provider):
            result = cnw_runner.execute_prose(run)
        self.assertEqual(result["visible_chars"], minimum)
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[0][1], sent[1][1])
        self.assertIn("actual=2101", sent[1][0]["content"])
        state = cnw_runner.load_state(run)
        self.assertEqual(cnw_runner._read_stage_text(run, state, "prose"), "乙" * minimum)
        self.assertEqual(result["receipts"], ["MOCK-1", "MOCK-2"])

    def test_over_limit_recovery_exhausts_same_three_calls_without_publishing(self):
        run = self.base / "runs/FICT_SCENE_A"
        value = "甲" * (self.contract["unit"]["max_visible_chars"] + 1)
        messages = [{"role": "system", "content": "Only prose"}, {"role": "user", "content": '{"writing_brief":"brief","voice_samples":"selected"}'}]
        with patch.object(cnw_runner, "_role_sources", return_value={}), patch.object(cnw_runner, "_author_messages", return_value=messages), patch.object(cnw_runner, "cnw_live_call", return_value=(value, {"request_id": "MOCK-OVER"})) as provider:
            with self.assertRaisesRegex(ContractError, "RETURN_OVER_LIMIT"):
                cnw_runner.execute_prose(run)
        self.assertEqual(provider.call_count, 3)
        state = cnw_runner.load_state(run)
        self.assertIsNone(state["stages"]["prose"].get("artifact"))
        self.assertFalse((run / "artifacts/candidates/prose").exists())

    def test_completeness_capacity_tracks_actual_review_set_with_fixed_ceiling(self):
        run = self.base / "runs/FICT_SCENE_A"
        cnw_runner._persist_stage(run, "prose", "artifacts/prose.md", "MOCK prose")
        for count, expected in ((0, 2500), (22, 8000), (100, 8000)):
            findings = [{"finding_id": f"F{i}"} for i in range(count)]
            verify = {"findings": findings, "verdicts": {f["finding_id"]: {"status": "CONFIRMED"} for f in findings}}
            cnw_runner._persist_stage(run, "adversarial_verify", "artifacts/verify.json", json.dumps(verify))
            with patch.object(cnw_runner, "_review_sources", return_value={"scene_cards": "cards", "writing_brief": "brief", "project_specific_canon": "canon"}), patch.object(cnw_runner, "cnw_live_call", return_value=('{"candidate_findings":[]}', {"request_id": "MOCK-COMPLETE"})) as provider:
                cnw_runner.execute_completeness(run)
            self.assertEqual(provider.call_args.kwargs["output_cap"], expected)

    def _fixture_first_roles(self, run_id):
        contract = json.loads((self.base / "runs" / run_id / "artifacts/contract.json").read_text(encoding="utf-8"))
        for stage in ("plot", "scene_cards", "writing_brief"):
            result = cnw_runner.step(argparse.Namespace(run_id=run_id, work_id=None, stage=stage, input=None))
            fixture = self.base / "runs" / run_id / "artifacts" / f"{stage}-fixture.json"
            fixture.write_text(json.dumps({"fixture_only": True, "stage": stage, "work_id": contract["unit"]["id"], "target_visible_chars": contract["unit"]["target_visible_chars"], "beat_budgets": [beat["budget_visible_chars"] for beat in contract["story"]["required_beats"]]}, ensure_ascii=False), encoding="utf-8")
            cnw_runner.mark_stage(argparse.Namespace(run_id=run_id, stage=stage, accept_fixture=str(fixture)))
        return cnw_runner.show_run(argparse.Namespace(run_id=run_id))

    def test_author_plot_episode_materializes_generated_structure(self):
        self.contract["unit"].update(kind="episode", planning_mode="author_plot")
        self.contract["story"].pop("required_beats")
        path = self._write_contract(self.contract, "author-episode.json")
        args = argparse.Namespace(run_id="FICT_AUTHOR_EP", work_id=self.contract["unit"]["id"],
                                  unit="episode", contract=str(path), project_root=str(self.project), mode="offline")
        with cnw_runner._offline_test_fixture_context():
            result = cnw_runner.produce(args)
        run_dir = Path(result["path"])
        plot = ("## Identity\nEpisode\n## Role in the Arc\nConsequence\n"
                "## Key Scenes\n1. Encounter\n2. Response\n## Hook\nDecision\n"
                "## Required Story Beats\n- A new event\n- Its consequence\n"
                "## Forbidden Items\nNo secret\n## Connections\nContinue\n## Target Length\n1500\n")
        with patch.object(cnw_runner, "_role_sources", return_value={"arc": "Plan the episode"}), \
                patch.object(cnw_runner, "cnw_live_call", return_value=(plot, {"request_id": "fixture-design", "provider_request_id": "MOCK_ONLY"})):
            cnw_runner._planning_stage(run_dir, "plot", "plot", "artifacts/plot.md", 4000,
                                       role_id="plot_agent")
        meta_ref = cnw_runner.load_state(run_dir)["stages"]["plot"]["meta"]
        meta = json.loads((run_dir / meta_ref["path"]).read_text(encoding="utf-8"))
        self.assertEqual(meta["plot_structure"]["key_scenes"], ["Encounter", "Response"])
        self.assertEqual(meta["plot_structure"]["plot_sha256"], cnw_runner.sha(plot.encode("utf-8")))
        self.assertEqual(meta["beats"], [])
        self.assertNotIn("required_beats", json.loads((run_dir / "artifacts/contract.json").read_text(encoding="utf-8"))["story"])

    def test_different_new_ids_create_independent_contract_bound_runs(self):
        first = cnw_runner.show_run(argparse.Namespace(run_id="FICT_SCENE_A"))
        other = json.loads(json.dumps(self.contract))
        other["unit"]["id"] = "FICT_SCENE_B"
        other["unit"]["target_visible_chars"] = 1800
        other["unit"]["min_visible_chars"] = 1500
        other["unit"]["max_visible_chars"] = 2100
        for beat, amount in zip(other["story"]["required_beats"], (300, 500, 600, 400)):
            beat["budget_visible_chars"] = amount
        created = self._produce_contract(other, "FICT_SCENE_B", "fixture-b.json")
        second = cnw_runner.show_run(argparse.Namespace(run_id="FICT_SCENE_B"))
        self.assertEqual(created["status"], "RUN_CREATED")
        self.assertNotEqual(first["contract_sha256"], second["contract_sha256"])
        self.assertTrue((self.base / "runs/FICT_SCENE_A/artifacts/contract.json").is_file())
        self.assertTrue((self.base / "runs/FICT_SCENE_B/artifacts/contract.json").is_file())
        first = self._fixture_first_roles("FICT_SCENE_A")
        second = self._fixture_first_roles("FICT_SCENE_B")
        for stage in ("plot", "scene_cards", "writing_brief"):
            self.assertEqual(first["stages"][stage], "ACCEPTED")
            self.assertEqual(second["stages"][stage], "ACCEPTED")
        self.assertNotEqual((self.base / "runs/FICT_SCENE_A/artifacts/plot-fixture.json").read_bytes(), (self.base / "runs/FICT_SCENE_B/artifacts/plot-fixture.json").read_bytes())

    def test_new_run_does_not_modify_old_run_state_or_cache(self):
        original_hash = cnw_runner.show_run(argparse.Namespace(run_id="FICT_SCENE_A"))["contract_sha256"]
        old_artifact = self.base / "runs/FICT_SCENE_A/artifacts/contract.json"
        old_state_path = self.base / "runs/FICT_SCENE_A/run_state.json"
        original_artifact_hash = cnw_runner.sha(old_artifact.read_bytes())
        cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="plot", input=None))
        old_state_bytes = old_state_path.read_bytes()
        changed = json.loads(json.dumps(self.contract))
        changed["story"]["reader_reward"] += " Revised contract."
        self._produce_contract(changed, "FICT_SCENE_A-R2", "fixture-a-revised.json")
        old_state = cnw_runner.load_state(self.base / "runs/FICT_SCENE_A")
        self.assertEqual(old_state_path.read_bytes(), old_state_bytes)
        self.assertEqual(old_state["status"], "RUNNING")
        self.assertEqual(old_state["stages"]["plot"]["status"], "READY_FOR_EXECUTION")
        self.assertEqual(old_state["contract_sha256"], original_hash)
        self.assertEqual(cnw_runner.sha(old_artifact.read_bytes()), original_artifact_hash)

    def test_cards_consumes_its_own_run_plot_without_publishing_shared_plot(self):
        (self.base / "06_plot").mkdir()
        (self.base / "90_canon").mkdir()
        public_plot = self.base / "06_plot/ep001_plot.md"
        public_plot.write_text("frozen public plot", encoding="utf-8")
        (self.base / "90_canon/character_bible.md").write_text("fixture character bible", encoding="utf-8")
        first = self.base / "runs/FICT_SCENE_A"
        second_result = self._produce_contract(self.contract, "FICT_SCENE_A2", "fixture-a2.json")
        second = Path(second_result["path"])
        cnw_runner._persist_stage(first, "plot", "artifacts/plot.md", "plot from run one")
        cnw_runner._persist_stage(second, "plot", "artifacts/plot.md", "plot from run two")
        sent = []

        def messages(role, contract, materials, extra=None):
            sent.append(materials["06_plot/<work_id>_plot.md"])
            return [{"role": "user", "content": sent[-1]}]

        cards = ("### Identity\nX\n### Cast\nX\n### Start state\nX\n### End state\nX\n"
                 "### Required beats\nX\n### Forbidden items for this scene\nX\n### Sensory anchor\nX\n"
                 "### Tone / pacing\nX\n### Connection to next scene\nX")
        with patch.object(cnw_runner, "_author_messages", side_effect=messages), \
                patch.object(cnw_runner, "_role_meta", return_value={}), \
                patch.object(cnw_runner, "_validate_role"), \
                patch.object(cnw_runner, "cnw_live_call", return_value=(cards, {"request_id": "MOCK-CARDS", "provider_request_id": "MOCK-PROVIDER-CARDS"})):
            cnw_runner._planning_stage(first, "cards", "scene_cards", "artifacts/scene_cards.md", 4000, role_id="scene_card_agent")
            cnw_runner._planning_stage(second, "cards", "scene_cards", "artifacts/scene_cards.md", 4000, role_id="scene_card_agent")
        self.assertEqual(sent, ["plot from run one", "plot from run two"])
        self.assertEqual(public_plot.read_text(encoding="utf-8"), "frozen public plot")

    def test_stage_persist_interruption_leaves_project_output_and_stage_state_unchanged(self):
        (self.base / "06_plot").mkdir()
        public_plot = self.base / "06_plot/ep001_plot.md"
        public_plot.write_text("frozen public plot", encoding="utf-8")
        run = self.base / "runs/FICT_SCENE_A"
        before = cnw_runner.load_state(run)["stages"]["plot"]
        with patch.object(cnw_runner, "save_state", side_effect=OSError("fixture interruption")):
            with self.assertRaisesRegex(OSError, "fixture interruption"):
                cnw_runner._persist_stage(run, "plot", "artifacts/plot.md", "unregistered candidate")
        after = cnw_runner.load_state(run)["stages"]["plot"]
        self.assertEqual(after, before)
        self.assertEqual(public_plot.read_text(encoding="utf-8"), "frozen public plot")
        candidates = list((run / "artifacts/candidates/plot").glob("*.md"))
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].read_text(encoding="utf-8"), "unregistered candidate")
        self.assertIsNone(cnw_runner.load_state(run)["stages"]["plot"].get("artifact"))

    def test_stage_requests_are_ordered_resumable_and_history_never_claims_live(self):
        with patch.object(cnw_runner, "ROOT", self.base):
            ready = cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="plot", input=None))
            self.assertEqual(ready["status"], "READY_FOR_EXECUTION")
            with self.assertRaisesRegex(ContractError, "EDITORIAL_CANDIDATE_NOT_READY"):
                cnw_runner.review_run(argparse.Namespace(run_id="FICT_SCENE_A"))
            candidate = self.base / "runs/FICT_SCENE_A/artifacts/mock-draft.md"
            candidate.write_text("MOCK_ONLY draft", encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "MOCK_CANDIDATE_CANNOT_REQUEST_EDITORIAL_REVIEW"):
                cnw_runner.register_editorial_candidate(argparse.Namespace(run_id="FICT_SCENE_A", candidate=str(candidate)))
            resumed = cnw_runner.show_run(argparse.Namespace(run_id="FICT_SCENE_A"))
            self.assertEqual(resumed["stages"]["plot"], "READY_FOR_EXECUTION")
            history = cnw_runner.verify_history(argparse.Namespace(run_id="FICT_SCENE_A"))
            self.assertEqual(history["status"], "HISTORICAL_EVIDENCE_FOUND")
            with self.assertRaisesRegex(ContractError, "LIVE_PROVIDER_EVIDENCE_MISSING"):
                cnw_runner.verify_live(argparse.Namespace(run_id="FICT_SCENE_A"))
            state = cnw_runner.load_state(self.base / "runs/FICT_SCENE_A")
            state["provider_requests"] = [{"stage": "lens5", "mode": "MOCK_ONLY", "provider_request_id": "mock-1"}]
            cnw_runner.save_state(self.base / "runs/FICT_SCENE_A", state)
            with self.assertRaisesRegex(ContractError, "MOCK_RECEIPT_CANNOT_PROVE_LIVE"):
                cnw_runner.verify_live(argparse.Namespace(run_id="FICT_SCENE_A"))
            state["stages"]["re_review"]["status"] = "ACCEPTED"
            cnw_runner.save_state(self.base / "runs/FICT_SCENE_A", state)
            with self.assertRaisesRegex(ContractError, "EXTERNAL_REVIEW_EVIDENCE_REQUIRED"):
                cnw_runner.promote_run(argparse.Namespace(run_id="FICT_SCENE_A"))
            with self.assertRaisesRegex(ContractError, "STAGE_DEPENDENCY_NOT_ACCEPTED"):
                cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="cards", input=None))

    def test_scene_cards_change_invalidates_brief_and_downstream(self):
        self._fixture_first_roles("FICT_SCENE_A")
        path = self.base / "runs/FICT_SCENE_A"
        changed = path / "cards-input.json"
        changed.write_text('{"revision":2}', encoding="utf-8")
        cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="scene_cards", input=str(changed)))
        state = cnw_runner.load_state(path)
        self.assertEqual(state["stages"]["scene_cards"]["status"], "READY_FOR_EXECUTION")
        self.assertEqual(state["stages"]["writing_brief"]["status"], "INVALIDATED")

    def test_rereview_stage_persists_affected_lens_set(self):
        path = self.base / "runs/FICT_SCENE_A"
        state = cnw_runner.load_state(path)
        for stage in ("plot", "scene_cards", "writing_brief", "prose", "lint_layer1", "lint_layer2", "multi_lens_review", "adversarial_verify", "completeness_critic", "refine"):
            state["stages"][stage]["status"] = "ACCEPTED"
        cnw_runner.save_state(path, state)
        with self.assertRaisesRegex(ContractError, "REREVIEW_ROLE_SET_REQUIRED"):
            cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="re_review", input=None))
        ready = cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="re_review", input=None, expected_role_ids=["style", "character"]))
        self.assertEqual(ready["status"], "READY_FOR_EXECUTION")
        self.assertEqual(cnw_runner.load_state(path)["stages"]["re_review"]["expected_role_ids"], ["style", "character"])

    def test_prompt_change_invalidates_only_affected_stage_and_preserves_old_artifact(self):
        prompt_root = self.base / "prompts"
        prompt_root.mkdir()
        prompt = prompt_root / "plot.md"
        prompt.write_text("plot prompt v1", encoding="utf-8")
        with patch.object(cnw_runner, "PROMPT_ROOT", prompt_root):
            first = cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="plot", input=None))
            first_path = self.base / "runs/FICT_SCENE_A" / first["artifact"]
            first_hash = cnw_runner.sha(first_path.read_bytes())
            prompt.write_text("plot prompt v2", encoding="utf-8")
            second = cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="plot", input=None))
            second_path = self.base / "runs/FICT_SCENE_A" / second["artifact"]
            self.assertNotEqual(first["fingerprint"], second["fingerprint"])
            self.assertNotEqual(first_path, second_path)
            self.assertTrue(first_path.is_file())
            self.assertEqual(cnw_runner.sha(first_path.read_bytes()), first_hash)
            record = cnw_runner.load_state(self.base / "runs/FICT_SCENE_A")["stages"]["plot"]
            self.assertEqual(len(record["invalidated_attempts"]), 1)
            self.assertEqual(record["status"], "READY_FOR_EXECUTION")
            self.assertEqual(cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="plot", input=None))["status"], "STAGE_REUSED")

    def test_workflow_template_change_invalidates_stage_and_downstream_only(self):
        self._fixture_first_roles("FICT_SCENE_A")
        run_path = self.base / "runs/FICT_SCENE_A"
        state = cnw_runner.load_state(run_path)
        prior_cards_fingerprint = state["stages"]["scene_cards"]["fingerprint"]
        prior_brief_artifact = state["stages"]["writing_brief"]["artifact"]["path"]
        state["workflow_template_sha256"] = "changed-pinned-workflow-hash"
        cnw_runner.save_state(run_path, state)
        result = cnw_runner.step(argparse.Namespace(run_id="FICT_SCENE_A", work_id=None, stage="scene_cards", input=None))
        refreshed = cnw_runner.load_state(run_path)
        self.assertEqual(refreshed["stages"]["plot"]["status"], "ACCEPTED")
        self.assertEqual(refreshed["stages"]["scene_cards"]["status"], "READY_FOR_EXECUTION")
        self.assertNotEqual(refreshed["stages"]["scene_cards"]["fingerprint"], prior_cards_fingerprint)
        self.assertEqual(refreshed["stages"]["writing_brief"]["status"], "INVALIDATED")
        self.assertTrue((run_path / prior_brief_artifact).is_file())
        self.assertEqual(result["status"], "READY_FOR_EXECUTION")

    def test_run_id_collision_and_path_traversal_fail_closed(self):
        with patch.object(cnw_runner, "ROOT", self.base):
            args = argparse.Namespace(run_id="FICT_SCENE_A", work_id=self.contract["unit"]["id"], unit="scene", contract=str(self.contract_dir / "fixture-a.json"), project_root=str(self.project), mode="offline")
            with self.assertRaisesRegex(ContractError, "RUN_ID_COLLISION"):
                with cnw_runner._offline_test_fixture_context():
                    cnw_runner.produce(args)
            with self.assertRaisesRegex(ContractError, "VALID_RUN_ID_REQUIRED"):
                cnw_runner.run_path("../outside")

    def test_live_mode_rejects_unverified_fixture_source_before_any_request(self):
        args = argparse.Namespace(run_id="NO-LIVE-CALL", work_id=self.contract["unit"]["id"], unit="scene", contract=str(self.contract_dir / "fixture-a.json"), project_root=str(self.project), mode="live")
        with patch.object(cnw_runner, "cnw_live_call") as provider:
            with self.assertRaisesRegex(ContractError, "PROJECT_ROOT_OUTSIDE_PRIVATE_WORKSPACE"):
                cnw_runner.produce(args)
            provider.assert_not_called()

    def test_live_candidate_requires_complete_contract_pipeline(self):
        run = self.base / "runs/FICT_SCENE_A"
        state = cnw_runner.load_state(run)
        state["mode"] = "live"
        state["fixture_only"] = False
        state["provider_requests"] = [{"stage": "plot", "mode": "live"}]
        cnw_runner.save_state(run, state)
        with self.assertRaisesRegex(ContractError, "LIVE_PIPELINE_INCOMPLETE"):
            cnw_runner.register_editorial_candidate(argparse.Namespace(run_id="FICT_SCENE_A", candidate="draft.md"))

    def test_raw_provider_payload_must_match_receipt_fields(self):
        raw = self.base / "raw.json"
        content = "raw assistant output"
        receipt = {"request_id": "req-1", "provider_request_id": "provider-1", "model": "deepseek-flash", "finish_reason": "stop", "output_sha256": hashlib.sha256(content.encode()).hexdigest()}
        usage = {"prompt_tokens": 12, "completion_tokens": 8}
        body = {"id": "provider-1", "model": "deepseek-flash", "choices": [{"finish_reason": "stop", "message": {"content": content}}], "usage": usage}
        raw.write_text(json.dumps({"request_id": "req-1", "status": 200, "requested_model": "deepseek-flash", "response": body}), encoding="utf-8")
        cnw_runner._validate_raw_live_response(raw, receipt, usage, 1)
        body["id"] = "other-provider"
        raw.write_text(json.dumps({"request_id": "req-1", "status": 200, "requested_model": "deepseek-flash", "response": body}), encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "LIVE_RAW_RESPONSE_RECEIPT_MISMATCH"):
            cnw_runner._validate_raw_live_response(raw, receipt, usage, 1)

    def test_live_review_coverage_requires_five_lenses_and_three_verifiers(self):
        lenses = [
            {"stage": "multi_lens_review", "lens_id": name}
            for name in ("style", "character", "plot", "canon", "story_specific")
        ]
        verifiers = [
            {"stage": "adversarial_verify", "verifier_id": name, "finding_id": "F1"}
            for name in ("correctness", "character_consistency", "continuity_plausibility")
        ]
        cnw_runner._validate_review_call_coverage(lenses + verifiers, {"F1": set(cnw_runner.VERIFIER_IDS)})
        with self.assertRaisesRegex(ContractError, "LIVE_REVIEW_CALL_SET_INCOMPLETE"):
            cnw_runner._validate_review_call_coverage(lenses[:-1] + verifiers, {"F1": set(cnw_runner.VERIFIER_IDS)})
        duplicate = lenses[:-1] + [{"stage": "multi_lens_review", "lens_id": "canon"}] + verifiers
        with self.assertRaisesRegex(ContractError, "LIVE_REVIEW_CALL_SET_INCOMPLETE"):
            cnw_runner._validate_review_call_coverage(duplicate, {"F1": set(cnw_runner.VERIFIER_IDS)})
        with self.assertRaisesRegex(ContractError, "LIVE_REVIEW_CALL_SET_INCOMPLETE"):
            cnw_runner._validate_review_call_coverage(lenses + verifiers[:-1], {"F1": set(cnw_runner.VERIFIER_IDS)})

    def test_accepted_review_votes_must_match_verified_raw_response_content(self):
        run=self.base/"runs/R1"; artifacts=run/"artifacts"; artifacts.mkdir(parents=True)
        review_rows=[]; provider_rows=[]
        for lens in ("style","character","plot","canon","story_specific"):
            pid=f"L-{lens}"; review_rows.append({"stage":"multi_lens_review","lens_id":lens,"provider_request_id":pid})
            provider_rows.append({"stage":"multi_lens_review","lens_id":lens,"provider_request_id":pid})
        for i,verifier in enumerate(("correctness","character_consistency","continuity_plausibility"),1):
            pid=f"V-{i}"; content=json.dumps({"verifier_id":verifier,"votes":[{"finding_id":"I1","verdict":"not_refuted"}]},sort_keys=True)
            raw={"id":pid,"model":"deepseek-flash","choices":[{"finish_reason":"stop","message":{"content":content}}],"usage":{"prompt_tokens":10,"completion_tokens":10}}
            path=artifacts/f"{pid}.json"; path.write_text(json.dumps(raw),encoding="utf-8")
            review_rows.append({"stage":"adversarial_verify","verifier_id":verifier,"provider_request_id":pid,"finding_id":"I1","response_content":content,"output_sha256":hashlib.sha256(content.encode()).hexdigest()})
            provider_rows.append({"stage":"adversarial_verify","verifier_id":verifier,"provider_request_id":pid,"finding_id":"I1","raw_response_path":path.relative_to(run).as_posix()})
        accepted={"provider_requests":review_rows,"findings":[{"finding_id":"I1"}]}
        cnw_runner.bind_accepted_review_outputs(accepted,provider_rows,run)
        accepted["provider_requests"][-1]["response_content"]="{\"votes\":[]}"
        with self.assertRaisesRegex(ContractError,"ACCEPTED_VERIFIER_OUTPUT_MISMATCH"):
            cnw_runner.bind_accepted_review_outputs(accepted,provider_rows,run)

    def test_same_run_stage_mutations_are_serialized(self):
        path = self.base / "runs/FICT_SCENE_A"
        active = 0
        maximum = 0
        guard = threading.Lock()

        def update():
            nonlocal active, maximum
            with cnw_runner.locked_run(path):
                with guard:
                    active += 1
                    maximum = max(maximum, active)
                time.sleep(0.03)
                with guard:
                    active -= 1

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: update(), range(2)))
        self.assertEqual(maximum, 1)

    def test_project_import_and_publish_mutations_share_one_lock(self):
        from tools import cnw_import_workflow, cnw_revision
        workspace_root = self.base / "workspace"
        root = workspace_root / "shared-project"
        workspace_project = root
        workspace_project.mkdir(parents=True)
        state_path = root / "authority.json"
        state_path.write_text('{"writes":[]}', encoding="utf-8")
        active = maximum = 0
        guard = threading.Lock()

        def mutate(kind):
            nonlocal active, maximum
            with guard:
                active += 1
                maximum = max(maximum, active)
            current = json.loads(state_path.read_text(encoding="utf-8"))
            time.sleep(0.03)
            current["writes"].append(kind)
            state_path.write_text(json.dumps(current), encoding="utf-8")
            with guard:
                active -= 1

        def fake_import(project_root, *, incremental=False):
            self.assertEqual(Path(project_root).resolve(), workspace_project.resolve())
            mutate("source_import")
            return {"status": "FIXTURE_IMPORT"}

        def fake_publish(*args, **kwargs):
            self.assertEqual(Path(args[0]).resolve(), root.resolve())
            mutate("revision_publish")
            return {"status": "FIXTURE_PUBLISH"}

        with patch.object(cnw_import_workflow, "ROOT", self.base), \
                patch.object(cnw_import_workflow, "_run_import", side_effect=fake_import), \
                patch.object(cnw_revision, "_promote_revision_unlocked", side_effect=fake_publish):
            with ThreadPoolExecutor(max_workers=2) as pool:
                imports = pool.submit(cnw_import_workflow.run_import, workspace_project)
                publishes = pool.submit(cnw_revision.promote_revision, root, root / "runs/R1", "candidate.md", {}, {})
                imports.result()
                publishes.result()
        self.assertEqual(maximum, 1)
        self.assertCountEqual(json.loads(state_path.read_text(encoding="utf-8"))["writes"],
                              ["source_import", "revision_publish"])

    def test_incremental_staging_and_publish_share_one_project_lock(self):
        from tools import cnw_project, cnw_revision, project_transactions
        workspace = self.base / "workspace"
        root = workspace / "FICT_INCREMENTAL"
        (root / "_INBOX").mkdir(parents=True)
        (root / "00_meta").mkdir()
        (root / "00_meta/import_state.json").write_text("{}", encoding="utf-8")
        authority = root / "authority.json"
        authority.write_text('{"writes":[]}', encoding="utf-8")
        incoming = self.base / "incremental.md"
        incoming.write_text("Synthetic incremental source", encoding="utf-8")
        active = maximum = 0
        guard = threading.Lock()
        original_lock = project_transactions.project_write_lock

        @contextmanager
        def observed_lock(project_root):
            nonlocal active, maximum
            with original_lock(project_root):
                with guard:
                    active += 1
                    maximum = max(maximum, active)
                try:
                    yield
                finally:
                    with guard:
                        active -= 1

        def fake_import(project_root, *, incremental=False):
            staged = root / "_INBOX/originals"
            self.assertTrue(staged.is_dir())
            self.assertEqual(len(list(staged.iterdir())), 1)
            current = json.loads(authority.read_text(encoding="utf-8"))
            time.sleep(0.03)
            current["writes"].append("incremental_stage_and_import")
            authority.write_text(json.dumps(current), encoding="utf-8")
            return {"status": "FIXTURE_INCREMENTAL"}

        def fake_publish(*args, **kwargs):
            current = json.loads(authority.read_text(encoding="utf-8"))
            time.sleep(0.03)
            current["writes"].append("revision_publish")
            authority.write_text(json.dumps(current), encoding="utf-8")
            return {"status": "FIXTURE_PUBLISH"}

        with patch.object(cnw_project, "ROOT", self.base), \
                patch.object(project_transactions, "project_write_lock", observed_lock), \
                patch("tools.cnw_import_workflow._run_import", side_effect=fake_import), \
                patch.object(cnw_revision, "_promote_revision_unlocked", side_effect=fake_publish):
            with ThreadPoolExecutor(max_workers=2) as pool:
                update = pool.submit(cnw_project.incremental_update, workspace, "FICT_INCREMENTAL", incoming)
                publish = pool.submit(cnw_revision.promote_revision, root, root / "runs/R1", "candidate.md", {}, {})
                self.assertEqual(update.result()["status"], "FIXTURE_INCREMENTAL")
                self.assertEqual(publish.result()["status"], "FIXTURE_PUBLISH")
        self.assertEqual(maximum, 1)
        self.assertCountEqual(json.loads(authority.read_text(encoding="utf-8"))["writes"],
                              ["incremental_stage_and_import", "revision_publish"])

    def test_lens_feedback_publication_serializes_concurrent_feedback_and_publish(self):
        from tools import cnw_revision, project_transactions
        root = self.base / "shared-project"
        root.mkdir()
        authority = root / "authority.json"
        authority.write_text('{"writes":[]}', encoding="utf-8")
        active = maximum = 0
        guard = threading.Lock()
        original_lock = project_transactions.project_write_lock

        @contextmanager
        def observed_lock(project_root):
            nonlocal active, maximum
            with original_lock(project_root):
                with guard:
                    active += 1
                    maximum = max(maximum, active)
                try:
                    yield
                finally:
                    with guard:
                        active -= 1

        def fake_publish(*args, **kwargs):
            current = json.loads(authority.read_text(encoding="utf-8"))
            time.sleep(0.03)
            current["writes"].append("revision_publish")
            authority.write_text(json.dumps(current), encoding="utf-8")
            return {"status": "FIXTURE_PUBLISH"}

        receipt = {"provider_request_id": "MOCK-PROVIDER"}
        feedback = [
            {"lens_id": "style", "prompt_update": "Check sentence rhythm.", "finding_id": "F1"},
            {"lens_id": "style", "prompt_update": "Check repeated imagery.", "finding_id": "F2"},
        ]
        with patch.object(project_transactions, "project_write_lock", observed_lock), \
                patch.object(cnw_revision, "_promote_revision_unlocked", side_effect=fake_publish):
            with ThreadPoolExecutor(max_workers=3) as pool:
                calls = [pool.submit(cnw_runner._publish_lens_feedback, root, root / "runs/R1", [finding], receipt)
                         for finding in feedback]
                publish = pool.submit(cnw_revision.promote_revision, root, root / "runs/R1", "candidate.md", {}, {})
                for call in calls:
                    call.result()
                publish.result()
        self.assertEqual(maximum, 1)
        stored = json.loads((root / "08_review/lens_feedback/style.json").read_text(encoding="utf-8"))
        self.assertEqual({row["instruction"] for row in stored}, {row["prompt_update"] for row in feedback})
        self.assertEqual(json.loads(authority.read_text(encoding="utf-8"))["writes"], ["revision_publish"])
        self.assertEqual(list((root / "08_review/lens_feedback").glob(".style.json.*")), [])

    def test_semantic_import_accepts_registered_datahome_root(self):
        from tools import cnw_import_workflow, cnw_project
        from tools.project_paths import setup_data_home, create_project
        home = self.base / "data-home"
        setup_data_home(home, pointer_path=self.base / "route-pointer.json")
        registered = create_project(project_id="P1", data_home=home)
        root = Path(registered["project_root"])
        with patch.object(cnw_import_workflow, "ROOT", self.base), \
                patch.object(cnw_project, "_registered_project_identity", wraps=cnw_project._registered_project_identity) as identity_reader, \
                patch.object(cnw_import_workflow, "_run_import", return_value={"status": "FIXTURE_IMPORT"}) as importer:
            result = cnw_import_workflow.run_import(root)
        self.assertEqual(result["status"], "FIXTURE_IMPORT")
        identity_reader.assert_called_once_with(root.resolve(strict=True))
        importer.assert_called_once()

    def test_stage_inputs_reject_absolute_escape_and_symlink(self):
        run_dir = self.base / "runs/FICT_SCENE_A"
        outside = self.base / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "STAGE_INPUT_OUTSIDE_RUN"):
            cnw_runner.safe_run_input(outside, run_dir)
        link = run_dir / "artifacts/input-link.md"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable on this host")
        with self.assertRaisesRegex(ContractError, "STAGE_INPUT_UNSAFE"):
            cnw_runner.safe_run_input(link, run_dir)

    def test_stage_aliases_match_pinned_workflow_and_keep_extra_roles_explicit(self):
        workflow = cnw_runner.WORKFLOW_PATH.read_text(encoding="utf-8")
        for source_stage in ("plot", "scene_cards", "writing_brief", "prose", "lint_layer1", "lint_layer2", "multi_lens_review", "adversarial_verify", "completeness_critic", "refine", "re_review"):
            self.assertIn(f"- {source_stage}", workflow)
        for source, target in cnw_runner.STAGE_ALIASES.items():
            self.assertEqual(cnw_runner.normalize_stage(source), target)
        self.assertEqual(cnw_runner.stage_predecessors("writing_brief", "scene"), ("plot", "scene_cards"))

    def test_parallel_transport_keeps_all_receipts_and_shared_budget(self):
        from tools import p2_cost_guard as guard_module
        from unittest.mock import Mock
        run_dir = self.base / "runs/FICT_SCENE_A"
        state = cnw_runner.load_state(run_dir)
        state["max_in_flight"] = 5
        cnw_runner.save_state(run_dir, state)
        config = self.base / "config/production.example.json"
        config.write_text(json.dumps({"provider": {"max_in_flight": 3}}), encoding="utf-8")
        pricing = json.loads((ROOT / "config/p2_cost_pricing_2026-10-10.json").read_text(encoding="utf-8-sig"))
        ledger = self.base / "mock-ledger.json"
        barrier = threading.Barrier(3)
        mutex = threading.Lock()
        active = peak = started = 0
        def post(*args, **kwargs):
            nonlocal active, peak, started
            with mutex:
                active += 1
                peak = max(peak, active)
                started += 1
                ordinal = started
            if ordinal <= 3:
                barrier.wait(timeout=5)
            time.sleep(0.03)
            with mutex:
                active -= 1
            response = Mock(status_code=200)
            response.json.return_value = {"id": kwargs["headers"]["X-Client-Request-Id"] + "-mock-provider", "model": cnw_runner.MODEL,
                "choices": [{"finish_reason": "stop", "message": {"content": "MOCK_ONLY " + kwargs["json"]["messages"][0]["content"]}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10}}
            return response
        calls = [dict(stage="multi_lens_review", role_id=str(i), messages=[{"role": "user", "content": str(i)}], output_cap=100) for i in range(5)]
        with patch.object(guard_module, "CONFIG", config), patch.object(guard_module, "LEDGER", ledger), \
                patch.object(guard_module, "load_config", return_value=({"model": cnw_runner.MODEL, "scope": "MOCK_ONLY", "currency": "CNY", "estimated_campaign_limit": 10}, pricing)), \
                patch.object(cnw_runner.httpx, "post", side_effect=post), \
                patch.dict(cnw_runner.os.environ, {"DEEPSEEK_API_KEY": "MOCK_ONLY_NOT_A_REAL_KEY_12345"}):
            with cnw_runner.locked_run(run_dir, lock_name="execution.lock"):
                results = cnw_runner._parallel_provider_calls(run_dir, calls)
            self.assertEqual(peak, 3)
            self.assertEqual([item[0] for item in results], ["MOCK_ONLY " + str(i) for i in range(5)])
            self.assertEqual(len(cnw_runner.load_state(run_dir)["provider_requests"]), 5)
            entries = json.loads(ledger.read_text(encoding="utf-8"))["requests"]
            self.assertEqual(len(entries), 5)
            self.assertTrue(all(row["status"] == "SETTLED" for row in entries))
            cnw_runner._parallel_provider_calls(run_dir, calls)
            self.assertEqual(started, 5)

    def test_successful_provider_task_is_reused_after_restart_and_hash_checked(self):
        from decimal import Decimal
        from contextlib import nullcontext
        from types import SimpleNamespace
        from unittest.mock import Mock
        run_dir = self.base / "runs/FICT_SCENE_A"
        guard = SimpleNamespace(
            provider_slot=nullcontext,
            command_reserve=lambda args, **kwargs: {"status": "RESERVED"},
            command_settle=lambda args, **kwargs: {"status": "SETTLED", "request_id": args.request_id},
            load_config=lambda: ({}, {}), estimate=lambda *args: Decimal("0.001"))
        body = {"id": "MOCK_PROVIDER_RESPONSE", "model": cnw_runner.MODEL,
                "choices": [{"finish_reason": "stop", "message": {"content": "fixture output"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10}}
        response = Mock(status_code=200)
        response.json.return_value = body
        messages = [{"role": "user", "content": "fixture prompt"}]
        with patch.object(cnw_runner, "_p2_guard", return_value=guard), \
                patch.dict(cnw_runner.os.environ, {"DEEPSEEK_API_KEY": "MOCK_ONLY_NOT_A_REAL_KEY_12345"}), \
                patch.object(cnw_runner.httpx, "post", return_value=response) as post:
            first = cnw_runner.cnw_live_call(run_dir, stage="re_review", role_id="style", messages=messages, output_cap=100)
            again = cnw_runner.cnw_live_call(run_dir, stage="re_review", role_id="style", messages=messages, output_cap=100)
            self.assertEqual(first, again)
            self.assertEqual(post.call_count, 1)
            self.assertEqual(len(cnw_runner.load_state(run_dir)["provider_requests"]), 1)
            (run_dir / first[1]["raw_response_path"]).write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "LIVE_RAW_RESPONSE_HASH_MISMATCH"):
                cnw_runner.cnw_live_call(run_dir, stage="re_review", role_id="style", messages=messages, output_cap=100)
            self.assertEqual(post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
