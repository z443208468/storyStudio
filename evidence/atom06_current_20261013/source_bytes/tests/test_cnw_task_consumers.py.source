"""Frozen package requirements through real CNW consumers; mock transport only."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import socket
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_cnw_input_pack as fixtures
from tests import test_cnw_atom09_three_project_e2e as responses
from tools import cnw_recovery, cnw_review, cnw_runner, cnw_task_requirements as task
from tools.cnw_contract import ContractError
from tools.cnw_project import write_contract_draft
from tools.cnw_roles import AUTHOR_ROLE_READS, AUTHOR_TEMPLATE_READS, read_production_preparation


class TaskConsumerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.InputPackTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        order = json.loads(self.fixture.files["scenes/A/work_order.draft.json"])
        order.update(scope_of_new_plot="LOCAL-OFFER-ONLY", allowed_local_change="A reversible promise.",
            creative_freedom="Choose how to offer help.", standalone_trial=True,
            knowledge_snapshot={"Mira": {"known": ["PUBLIC-MESSAGE"], "private": ["PRIVATE-KNOWLEDGE-CANARY"],
                                         "unknown": ["HIDDEN-OUTCOME"]}},
            gameplay_snapshot={"scope": "same-task", "valid_at": "BEFORE-MEETING",
                               "grain": 0, "can_attack": False, "not_canonical_history": True})
        self.fixture.files["scenes/A/work_order.draft.json"] = fixtures.encoded(order)
        packet = {"standalone_trial": True, "new_plot_pre_designed": False,
            "available_time": "BEFORE-MEETING", "current_location": "courtyard", "pov": "Mira",
            "cast": ["Mira"], "creative_freedom": "Select a practical gesture.",
            "allowed_local_change": "A reversible promise.", "next_fixed_event": "FIXED-MEETING",
            "role_states": {"Mira": {"focus": True, "narrator_access": "Visible actions only.",
                "private_facts": ["PRIVATE-STATE-CANARY"], "unknown": ["HIDDEN-OUTCOME"]}},
            "reader_knowledge": ["PUBLIC-MESSAGE"], "forbidden_future": ["HIDDEN-OUTCOME"]}
        prefix = "scenes/A/project_seed/"
        self.fixture.files[prefix + "scene_packet.json"] = fixtures.encoded(packet)
        self.fixture.files[prefix + "93_data/gameplay_snapshot.json"] = fixtures.encoded(order["gameplay_snapshot"])
        self.fixture.files[prefix + "93_data/temporal_envelope.json"] = fixtures.encoded({
            "time": None, "basis": "INFERRED", "status": "TODO_CONFIRM", "scope": "LOCAL_ONLY"})
        self.fixture.files[prefix + "90_canon/canon.md"] += b"CANON-SECRET-CANARY\n"
        self.fixture.files[prefix + "92_style_engine/forbidden_patterns.md"] = b'# Forbidden\n- "BANNED-PHRASE-CANARY"\n'
        self.fixture.write_pack()
        self.root = self.fixture.project("TASK-CONSUMERS")
        self.prepared = self.fixture.prepare(self.root)
        result = write_contract_draft(self.root, self.prepared["draft"])
        self.contract_path = Path(result["contract"])
        self.contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        self.context_name, self.context = task.read_bound_task_context(self.root, self.contract)
        self.model = responses.ThreeProjectOfflineE2E()
        self.model._guard_lock = threading.Lock()
        self.model._counter = 0
        self.model.requests = []
        self.calls = []

    def new_run(self, name):
        return Path(cnw_runner.produce(SimpleNamespace(mode="offline", unit="scene", run_id=name,
            work_id="TRIAL-A", contract=str(self.contract_path), project_root=str(self.root), create_only=True))["path"])

    def transport(self, run, *, stage, role_id, messages, output_cap, extra=None):
        payload = json.loads(messages[1]["content"])
        self.calls.append({"run_id": run.name, "stage": stage, "role_id": role_id, "messages": messages})
        if stage in {"plot", "scene_cards", "writing_brief"}:
            if stage == "plot":
                preparation = payload["support"]["production_preparation"]
                context = json.loads(preparation["documents"][self.context_name])
                self.assertEqual(context, self.context)
                self.assertEqual(preparation["source_hashes"][self.context_name], fixtures.sha(task.encode(context)))
                state = context["data"]["gameplay_snapshot"]
                current_time = context["data"]["scene_packet"].get("available_time")
                order_state = context["data"]["work_order"]["gameplay_snapshot"]
                if state.get("valid_at") != current_time and order_state.get("valid_at") == current_time:
                    state = order_state  # Mock model consumes the explicit task time, not JSON order.
                constraint = (f"TASK-REQUIREMENT grain={state['grain']}; can_attack={state['can_attack']}; "
                    f"valid_at={state.get('valid_at')}; scope={context['data']['work_order']['scope_of_new_plot']}; focus=Mira; "
                    "reader knows PUBLIC-MESSAGE only; fixed next event FIXED-MEETING; "
                    "time is TODO_CONFIRM, not an established fact; choose a reversible practical gesture.")
            else:
                upstream = payload["materials"]["06_plot/<work_id>_plot.md"]
                constraint = upstream.split("## Scoped task directions\n", 1)[1].strip()
                if stage == "writing_brief":
                    self.assertIn(constraint, payload["materials"]["05_scene_cards/<work_id>_scene_cards.md"])
            content = self.model._sections(stage, "Mira", "Mira", "courtyard")
            content = content.replace("- Mira: ask directly.\n- Mira: answer briefly and practically.", "- Mira: concise current speech.")
            content += "\n\n## Scoped task directions\n" + constraint
        elif stage == "prose":
            self.assertEqual(set(payload), {"writing_brief", "voice_samples"})
            self.assertIn("grain=0; can_attack=False", payload["writing_brief"])
            content = "Mira gave a public, reversible promise in the courtyard before the meeting. WRONG-ACTION"
        elif stage == "multi_lens_review":
            findings = []
            if role_id == "story_specific":
                view = json.loads(payload["sources"]["task_constraints"])
                self.assertIs(view["data"]["gameplay_snapshot"]["can_attack"], False)
                findings = [{"finding_id": "GAMEPLAY", "severity": "minor", "evidence": "WRONG-ACTION",
                    "issue": "This task forbids an attack.", "recommendation": "Restore the reversible local gesture."}]
            content = json.dumps({"lens_id": role_id, "findings": findings})
        elif stage == "adversarial_verify":
            view = json.loads(payload["counter_evidence"]["task_constraints"])
            self.assertEqual(view["lens_id"], "story_specific")
            self.assertIs(view["data"]["gameplay_snapshot"]["can_attack"], False)
            content = json.dumps({"verifier_id": role_id, "votes": [{"finding_id": payload["finding_id"],
                "verdict": "uncertain" if role_id == "continuity_plausibility" else "not_refuted",
                "evidence": "SIMULATED independent task-evidence check."}]})
        elif stage == "completeness_critic":
            context = json.loads(payload["source_materials"]["task_requirements"])
            self.assertEqual(context["data"]["scene_packet"]["next_fixed_event"], "FIXED-MEETING")
            content = json.dumps({"candidate_findings": [{"finding_id": "MISSED-FIXED-EVENT", "lens_id": "plot",
                "severity": "minor", "evidence": "WRONG-ACTION", "issue": "Missing the transition to the fixed meeting.",
                "recommendation": "End at FIXED-MEETING without changing the local scope.",
                "prompt_update": "Check the next fixed event and local scope in task constraints."}]})
        elif stage == "refine":
            self.assertIn("MISSED-FIXED-EVENT", messages[1]["content"])
            content = "Mira gave a public, reversible promise and returned to FIXED-MEETING, keeping the next choice open."
        elif stage == "re_review":
            self.assertIn("FIXED-MEETING", payload["draft"])
            self.assertNotIn("WRONG-ACTION", payload["draft"])
            self.assertIn("task_constraints", payload["sources"])
            content = json.dumps({"lens_id": role_id, "findings": []})
        else:
            raise AssertionError(stage)
        return self.model._workflow_response(run, messages, content, stage=stage, role_id=role_id)

    def record(self, name, run):
        destination = os.environ.get("ATOM06_TASK_EVIDENCE_OUTPUT")
        if not destination:
            return
        path = Path(destination)
        report = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"execution": "MOCK_ONLY / SIMULATED", "cases": {}}
        state = cnw_runner.load_state(run)
        artifacts = []
        for stage, record in state["stages"].items():
            if record.get("artifact"):
                raw = (run / record["artifact"]["path"]).read_bytes()
                artifacts.append({"stage": stage, "path": record["artifact"]["path"], "sha256": fixtures.sha(raw),
                                  "utf8": raw.decode("utf-8"), "execution_identity": record.get("execution_identity")})
        report["cases"][name] = {"contract": self.contract, "context": self.context, "calls": self.calls,
                                "artifacts": artifacts, "receipts": state["provider_requests"]}
        path.write_bytes(fixtures.encoded(report))

    def test_actual_requirements_reach_each_consumer_and_new_text_rereview(self):
        run = self.new_run("TASK-CONSUMERS-RUN")
        protected = {str(path.relative_to(self.root)): path.read_bytes() for path in
                     (self.root / "90_canon").glob("*.md")}
        with patch.object(cnw_runner, "cnw_live_call", side_effect=self.transport), \
             patch.object(socket, "create_connection", side_effect=AssertionError("Network forbidden")):
            for stage in cnw_runner.CNW_STAGES:
                cnw_recovery.execute_checked(run, stage)
                state = cnw_runner.load_state(run)
                artifact = state["stages"][stage]["artifact"]
                self.assertEqual(fixtures.sha((run / artifact["path"]).read_bytes()), artifact["sha256"])
            count = len(self.calls)
            self.assertEqual(cnw_recovery.execute_checked(run, "plot")["status"], "STAGE_REUSED")
            self.assertEqual(len(self.calls), count)
        state = cnw_runner.load_state(run)
        for row in self.calls:
            payload = json.loads(row["messages"][1]["content"])
            wire = json.dumps(row["messages"])
            if row["stage"] in {"prose", "refine"}:
                for forbidden in ("PRIVATE-KNOWLEDGE-CANARY", "PRIVATE-STATE-CANARY", "CANON-SECRET-CANARY",
                                  "BANNED-PHRASE-CANARY", "cnw_task_requirements_v1"):
                    self.assertNotIn(forbidden, wire)
            if row["stage"] in {"plot", "scene_cards", "writing_brief"}:
                role = {"scene_cards": "cards", "writing_brief": "brief"}.get(row["stage"], row["stage"])
                self.assertEqual(set(payload["materials"]), set(AUTHOR_ROLE_READS[role] + AUTHOR_TEMPLATE_READS.get(role, ())))
                self.assertNotIn("KNOWN-B", wire)
            if row["stage"] == "multi_lens_review":
                if row["role_id"] == "style":
                    self.assertNotIn("task_constraints", payload["sources"])
                else:
                    view = json.loads(payload["sources"]["task_constraints"])
                    self.assertEqual(view["context_source"]["sha256"], fixtures.sha(task.encode(self.context)))
                    self.assertEqual(view["lens_id"], row["role_id"])
                    self.assertTrue(view["provenance"])
                    self.assertNotIn("findings", view)
                    if row["role_id"] in {"plot", "canon"}:
                        self.assertNotIn("PRIVATE-STATE-CANARY", json.dumps(view))
        votes = json.loads(cnw_runner._read_stage_text(run, state, "adversarial_verify"))
        self.assertEqual(votes["verdicts"]["story_specific-1"]["status"], "CONFIRMED")
        self.assertEqual(len([row for row in self.calls if row["stage"] == "adversarial_verify"]), 3)
        review = json.loads(cnw_runner._read_stage_text(run, state, "re_review"))
        self.assertEqual(set(review["affected_lenses"]), {"plot", "story_specific"})
        revised = cnw_runner._read_stage_text(run, state, "refine")
        self.assertEqual(review["candidate_sha256"], fixtures.sha(revised.encode()))
        self.assertIn("WRONG-ACTION", cnw_runner._read_stage_text(run, state, "prose"))
        for name, raw in protected.items():
            self.assertEqual((self.root / name).read_bytes(), raw)
        self.assertTrue(all(row["mode"] == "MOCK_ONLY" and row["simulation_status"] == "SIMULATED" for row in state["provider_requests"]))
        cnw_recovery.verify_evidence(run, state)
        self.record("actual_requirement_consumers", run)

    def test_rehashed_forged_projection_cannot_replace_frozen_originals(self):
        index_path = self.root / self.contract["input_pack"]["index_file"]
        index_raw = index_path.read_bytes()
        context_path = self.root / self.context_name
        context_raw = context_path.read_bytes()
        for change in ("type", "locator", "instance", "recipe"):
            context = copy.deepcopy(self.context)
            if change == "type": context["data"]["gameplay_snapshot"]["can_attack"] = 0
            elif change == "locator": context["provenance"][0]["source_pointer"] = "/invented"
            elif change == "instance": context["project_instance_id"] = "forged"
            else: context["recipe_version"] = "self_accepted_future"
            raw = task.encode(context)
            context_path.write_bytes(raw)
            index = json.loads(index_raw)
            index["files"][self.context_name] = fixtures.sha(raw)
            index["task_context"]["sha256"] = fixtures.sha(raw)
            index_path.write_bytes(fixtures.encoded(index))
            contract = copy.deepcopy(self.contract)
            contract["input_pack"]["index_sha256"] = fixtures.sha(index_path.read_bytes())
            with self.subTest(change=change), self.assertRaises(ContractError):
                read_production_preparation(self.root, contract)
        context_path.write_bytes(context_raw)
        index_path.write_bytes(index_raw)
        other = self.fixture.project("OTHER-INSTANCE")
        self.fixture.prepare(other, "B")
        with self.assertRaises(ContractError):
            task.read_bound_task_context(other, self.contract)

    def test_changed_valid_task_values_change_actual_plot_cards_and_brief_messages(self):
        runs = []
        for version in ("ORIGINAL", "CHANGED"):
            if version == "CHANGED":
                name = "scenes/A/work_order.draft.json"
                order = json.loads(self.fixture.files[name])
                order["gameplay_snapshot"].update(grain=7, can_attack=True)
                order["scope_of_new_plot"] = "ALTERNATE-LOCAL-CHOICE"
                self.fixture.files[name] = fixtures.encoded(order)
                self.fixture.files["scenes/A/project_seed/93_data/gameplay_snapshot.json"] = fixtures.encoded(order["gameplay_snapshot"])
                self.fixture.write_pack()
                self.root = self.fixture.project("TASK-VARIANT")
                self.prepared = self.fixture.prepare(self.root)
                self.contract_path = Path(write_contract_draft(self.root, self.prepared["draft"])["contract"])
                self.contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
                self.context_name, self.context = task.read_bound_task_context(self.root, self.contract)
            run = self.new_run("TASK-VALUES-" + version)
            with patch.object(cnw_runner, "cnw_live_call", side_effect=self.transport):
                for stage in ("plot", "scene_cards", "writing_brief"):
                    cnw_recovery.execute_checked(run, stage)
            runs.append(run)
            self.record("task_values_" + version.lower(), run)
        for stage in ("plot", "scene_cards", "writing_brief"):
            first, second = [next(row for row in self.calls if row["stage"] == stage and row["run_id"] == run.name) for run in runs]
            self.assertNotEqual(first["messages"], second["messages"])
            self.assertIn("LOCAL-OFFER-ONLY", first["messages"][1]["content"])
            self.assertIn("ALTERNATE-LOCAL-CHOICE", second["messages"][1]["content"])
            self.assertIn("grain=7; can_attack=True", second["messages"][1]["content"] if stage != "plot" else
                          cnw_runner._read_stage_text(runs[1], cnw_runner.load_state(runs[1]), "plot"))

    def test_interrupted_cards_resume_keeps_receipt_and_reuses_matching_plot(self):
        run = self.new_run("TASK-INTERRUPTION")
        saved = None
        def interrupted(*args, **kwargs):
            nonlocal saved
            if kwargs["stage"] != "scene_cards":
                return self.transport(*args, **kwargs)
            if saved is not None:
                return saved
            saved = self.transport(*args, **kwargs)
            raise RuntimeError("SIMULATED_AFTER_CARDS_RECEIPT")
        with patch.object(cnw_runner, "cnw_live_call", side_effect=interrupted):
            cnw_recovery.execute_checked(run, "plot")
            before = cnw_runner.load_state(run)
            plot_raw = (run / before["stages"]["plot"]["artifact"]["path"]).read_bytes()
            with self.assertRaisesRegex(RuntimeError, "SIMULATED_AFTER_CARDS_RECEIPT"):
                cnw_recovery.execute_checked(run, "scene_cards")
            failed = cnw_runner.load_state(run)
            receipt_count = len(failed["provider_requests"])
            self.assertTrue(failed["stages"]["scene_cards"]["execution_failures"])
            self.assertEqual(cnw_recovery.execute_checked(run, "plot")["status"], "STAGE_REUSED")
            cnw_recovery.execute_checked(run, "scene_cards")
        state = cnw_runner.load_state(run)
        self.assertEqual(len(state["provider_requests"]), receipt_count)
        self.assertEqual((run / state["stages"]["plot"]["artifact"]["path"]).read_bytes(), plot_raw)
        self.assertTrue(state["stages"]["scene_cards"]["execution_failures"])
        self.assertEqual(cnw_runner._receipt_content(run, saved[1]), saved[0])
        self.record("interrupted_cards_resume", run)

    def test_normalized_draft_cannot_change_boolean_to_numeric_zero(self):
        path = Path(self.prepared["draft"])
        value = json.loads(path.read_text(encoding="utf-8"))
        value["new_plot_pre_designed"] = 0
        path.write_bytes(fixtures.encoded(value))
        with self.assertRaisesRegex(ContractError, "INPUT_PACK_REQUIREMENT_MISMATCH"):
            write_contract_draft(self.root, path)

    def test_rereview_finding_gets_original_sources_scoped_task_and_three_votes(self):
        run = self.new_run("TASK-REREVIEW-FINDING")
        def dispatch(run, *, stage, role_id, messages, output_cap, extra=None):
            if stage != "re_review":
                return self.transport(run, stage=stage, role_id=role_id, messages=messages, output_cap=output_cap, extra=extra)
            payload = json.loads(messages[1]["content"])
            self.calls.append({"run_id": run.name, "stage": stage, "role_id": role_id, "messages": messages})
            if extra["task_kind"] == "lens":
                findings = [] if role_id != "story_specific" else [{"finding_id": "REVISED-CHECK", "severity": "minor",
                    "evidence": "FIXED-MEETING", "issue": "Check the revised transition against task and original sources.",
                    "recommendation": "Verify the current version only."}]
                content = json.dumps({"lens_id": role_id, "findings": findings})
            else:
                self.assertIn("FIXED-MEETING", payload["full_draft"])
                self.assertNotIn("WRONG-ACTION", payload["full_draft"])
                evidence = payload["counter_evidence"]
                for name in ("style_guide", "forbidden_patterns", "voice_samples", "world_bible", "project_specific_canon"):
                    self.assertIn(name, evidence)
                self.assertNotIn("task_requirements", evidence)
                self.assertFalse(any(name.startswith("task_constraints:") for name in evidence))
                self.assertEqual(json.loads(evidence["task_constraints"])["lens_id"], "story_specific")
                content = json.dumps({"verifier_id": role_id, "votes": [{"finding_id": payload["finding_id"],
                    "verdict": "not_refuted" if role_id == "correctness" else "refuted",
                    "evidence": "SIMULATED: original sources and revised task transition refute this claim."}]})
            return self.model._workflow_response(run, messages, content, stage=stage, role_id=role_id)
        with patch.object(cnw_runner, "cnw_live_call", side_effect=dispatch):
            for stage in cnw_runner.CNW_STAGES:
                cnw_recovery.execute_checked(run, stage)
        state = cnw_runner.load_state(run)
        report = json.loads(cnw_runner._read_stage_text(run, state, "re_review"))
        self.assertEqual(report["status"], "CLEAN")
        disposition = report["dispositions"][0]
        self.assertFalse(disposition["confirmed"])
        self.assertEqual(len(disposition["votes"]), 3)
        self.assertEqual({row["verifier_id"] for row in disposition["votes"]}, set(cnw_runner.VERIFIER_IDS))
        self.record("rereview_finding_three_votes", run)

    def test_first_verifier_preserves_finding_lens_sources(self):
        sources = {name: name for names in cnw_review.LENSES.values() for name in names}
        sources.update(task.review_task_sources(self.root, self.contract))
        for lens in cnw_review.LENSES:
            evidence = cnw_review.verifier_sources({"lens_id": lens}, sources)
            self.assertTrue(set(cnw_review.LENSES[lens]) <= set(evidence))
            self.assertNotIn("task_requirements", evidence)
            if lens == "style":
                self.assertNotIn("task_constraints", evidence)
            else:
                self.assertEqual(json.loads(evidence["task_constraints"])["lens_id"], lens)

    def test_actual_private_job_retains_duplicate_conflict_and_original_archive(self):
        from tools.cnw_pack_app import import_package
        for label in ("A", "B", "C"):
            name = f"scenes/{label}/project_seed/00_meta/OUTPUT_REQUIREMENTS.md"
            self.fixture.files[name] = b'| Lens | Inputs | Duty |\n|---|---|---|\n| Story-specific Lens | Canon | Check the local scope. |\n'
        name = "scenes/A/project_seed/93_data/gameplay_snapshot.json"
        value = json.loads(self.fixture.files[name]); value["can_attack"] = True
        self.fixture.files[name] = fixtures.encoded(value)
        self.fixture.write_pack()
        package_before = self.fixture.pack.read_bytes()
        report = import_package(self.fixture.pack, data_home=self.fixture.home, local_source=self.fixture.repo, offline=True)
        self.assertEqual(report["status"], "IMPORT_INCOMPLETE")
        self.assertEqual(report["blocking_code"], "TASK_REQUIREMENTS_DUPLICATE_CONFLICT")
        private = json.loads(Path(report["job_record"]).read_text(encoding="utf-8"))
        locations = private["input_conflict"]["conflicts"][0]["sources"]
        root = Path(private["tasks"][-1]["project_root"])
        for location in locations:
            self.assertEqual(fixtures.sha((root / location["file"]).read_bytes()), location["sha256"])
        self.assertEqual(Path(report["job_record"]).with_name("input.zip").read_bytes(), package_before)
        self.assertEqual(self.fixture.pack.read_bytes(), package_before)
        self.assertFalse((root / "contracts/TRIAL-A.json").exists())
        self.assertFalse((root / "runs").exists())

    def test_actual_import_keeps_distinct_valid_at_snapshots_and_real_consumers(self):
        order_name = "scenes/A/work_order.draft.json"
        order = json.loads(self.fixture.files[order_name])
        order["gameplay_snapshot"].update(scope="same-task", valid_at="BEFORE-MEETING", grain=2)
        self.fixture.files[order_name] = fixtures.encoded(order)
        game_name = "scenes/A/project_seed/93_data/gameplay_snapshot.json"
        game = {**order["gameplay_snapshot"], "valid_at": "AFTER-MEETING", "grain": 1}
        self.fixture.files[game_name] = fixtures.encoded(game)
        self.fixture.write_pack()
        self.root = self.fixture.project("TASK-DIFFERENT-TIMES")
        self.prepared = self.fixture.prepare(self.root)
        self.contract_path = Path(write_contract_draft(self.root, self.prepared["draft"])["contract"])
        self.contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        self.context_name, self.context = task.read_bound_task_context(self.root, self.contract)
        run = self.new_run("TASK-DIFFERENT-TIMES-RUN")
        with patch.object(cnw_runner, "cnw_live_call", side_effect=self.transport):
            for stage in ("plot", "scene_cards", "writing_brief"):
                cnw_recovery.execute_checked(run, stage)
        self.assertEqual(self.context["data"]["work_order"]["gameplay_snapshot"]["valid_at"], "BEFORE-MEETING")
        self.assertEqual(self.context["data"]["gameplay_snapshot"]["valid_at"], "AFTER-MEETING")
        packet = json.loads(next(row for row in self.calls if row["stage"] == "plot")["messages"][1]["content"])
        actual = json.loads(packet["support"]["production_preparation"]["documents"][self.context_name])
        self.assertEqual(actual["data"]["work_order"]["gameplay_snapshot"]["grain"], 2)
        self.assertEqual(actual["data"]["gameplay_snapshot"]["grain"], 1)
        for stage in ("plot", "scene_cards", "writing_brief"):
            output = cnw_runner._read_stage_text(run, cnw_runner.load_state(run), stage)
            self.assertIn("grain=2; can_attack=False; valid_at=BEFORE-MEETING", output)
        self.record("valid_at_distinct_times", run)

    def test_old_binding_without_recipe_keeps_its_preparation_and_review_semantics(self):
        index_path = self.root / self.contract["input_pack"]["index_file"]
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index.pop("task_context")
        index["files"].pop(self.context_name)
        index_path.write_bytes(fixtures.encoded(index))
        contract = copy.deepcopy(self.contract)
        contract["input_pack"]["index_sha256"] = fixtures.sha(index_path.read_bytes())
        preparation = read_production_preparation(self.root, contract)
        self.assertNotIn(self.context_name, preparation["documents"])
        self.assertEqual(task.review_task_sources(self.root, contract), {})
        sources = {name: name + "-historical" for names in cnw_review.LENSES.values() for name in names}
        evidence = cnw_review.verifier_sources({"lens_id": "character"}, sources)
        self.assertEqual(set(evidence), {"scene_cards", "writing_brief", "character_bible", "timeline", "glossary"})
        self.assertEqual(cnw_review.verifier_sources({}, sources, rereview=True), sources)
        for lens in cnw_review.LENSES:
            self.assertEqual(set(cnw_review.build_lens_input(lens, "draft", sources)["sources"]), set(cnw_review.LENSES[lens]))


if __name__ == "__main__":
    unittest.main()
