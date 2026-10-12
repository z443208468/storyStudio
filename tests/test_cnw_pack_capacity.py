"""4700 work-unit capacity and immutable older policy identity (offline only)."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_cnw_input_pack as fixtures
from tests import test_policy_snapshots as policy_fixtures
from tests import test_cnw_atom09_three_project_e2e as transport_fixtures
from tools import cnw_export, cnw_recovery, cnw_runner
from tools.cnw_contract import ContractError, count_visible_chars, validate_output_length, validate_work_unit_policy
from tools.cnw_project import build_contract_preflight, write_contract_draft
from tools.policy_snapshots import (DEFAULT_STORE, PolicySnapshotError, SnapshotStore,
                                   resolve_contract_app_policy, validate_policy_document)


class CapacityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="storystudio-capacity-policy-")
        self.addCleanup(self.temp.cleanup)
        self.store = SnapshotStore(Path(self.temp.name) / "snapshots")

    def put_policy(self, capacity, *, kind="app_policy"):
        document = policy_fixtures.app_policy()
        document["execution_compatibility"]["maximum_validated_visible_characters_per_unit"] = capacity
        raw = policy_fixtures.raw_json(document)
        digest = self.store.put_bytes(raw, kind=kind, source_ref=f"fictional/capacity-{capacity}.json")
        return digest, raw

    def test_only_the_two_explicit_capacity_versions_are_accepted(self):
        for capacity in (4000, 4700):
            digest, raw = self.put_policy(capacity)
            self.assertEqual(self.store.resolve_policy_by_sha(digest, expected_kind="app_policy")["bytes"], raw)
        for capacity in (3999, 4500, 4701, True, "4700"):
            with self.subTest(capacity=capacity):
                value = policy_fixtures.app_policy()
                value["execution_compatibility"]["maximum_validated_visible_characters_per_unit"] = capacity
                with self.assertRaisesRegex(PolicySnapshotError, "EXECUTION_COMPATIBILITY_UNVERIFIED"):
                    validate_policy_document(value, expected_kind="app_policy")

    def test_old_policy_keeps_4000_bound_and_new_policy_keeps_4700_bound(self):
        old, old_raw = self.put_policy(4000)
        new, new_raw = self.put_policy(4700)
        contract = {"schema_version": "cnw_work_unit_v2", "unit": {"policy_sha256": old, "max_visible_chars": 4000}}
        self.assertEqual(resolve_contract_app_policy(contract, store=self.store.root)["bytes"], old_raw)
        contract["unit"]["max_visible_chars"] = 4700
        with self.assertRaisesRegex(PolicySnapshotError, "UNIT_CAPACITY_UNVALIDATED"):
            resolve_contract_app_policy(contract, store=self.store.root)
        contract["unit"]["policy_sha256"] = new
        self.assertEqual(resolve_contract_app_policy(contract, store=self.store.root)["bytes"], new_raw)
        self.assertEqual((self.store.objects / f"{old}.blob").read_bytes(), old_raw)
        contract["unit"]["max_visible_chars"] = 4701
        with self.assertRaisesRegex(PolicySnapshotError, "UNIT_CAPACITY_UNVALIDATED"):
            resolve_contract_app_policy(contract, store=self.store.root)

    def test_unregistered_wrong_kind_missing_and_changed_objects_reject(self):
        contract = {"schema_version": "cnw_work_unit_v2", "unit": {"policy_sha256": "0" * 64, "max_visible_chars": 2200}}
        with self.assertRaisesRegex(PolicySnapshotError, "SNAPSHOT_NOT_FOUND"):
            resolve_contract_app_policy(contract, store=self.store.root)
        wrong, _ = self.put_policy(4700, kind="tool")
        contract["unit"]["policy_sha256"] = wrong
        with self.assertRaisesRegex(PolicySnapshotError, "SNAPSHOT_KIND_MISMATCH"):
            resolve_contract_app_policy(contract, store=self.store.root)
        valid, raw = self.put_policy(4000)
        contract["unit"]["policy_sha256"] = valid
        object_file = self.store.objects / f"{valid}.blob"
        held = object_file.with_suffix(".held")
        object_file.rename(held)
        with self.assertRaisesRegex(PolicySnapshotError, "SNAPSHOT_OBJECT_MISSING"):
            resolve_contract_app_policy(contract, store=self.store.root)
        held.rename(object_file)
        object_file.write_bytes(raw + b" ")
        with self.assertRaisesRegex(PolicySnapshotError, "SNAPSHOT_HASH_MISMATCH"):
            resolve_contract_app_policy(contract, store=self.store.root)

    def test_method_and_safety_changes_do_not_gain_capacity_acceptance(self):
        for field in ("method", "safety"):
            value = policy_fixtures.app_policy()
            value["execution_compatibility"]["maximum_validated_visible_characters_per_unit"] = 4700
            if field == "method":
                value["method"]["per_unit_stages"].remove("adversarial_verify")
            else:
                value["safety"]["reservation_before_send"] = False
            digest = self.store.put_bytes(policy_fixtures.raw_json(value), kind="app_policy", source_ref=f"fictional/wrong-{field}.json")
            contract = {"schema_version": "cnw_work_unit_v2", "unit": {"policy_sha256": digest, "max_visible_chars": 4700}}
            with self.subTest(field=field), self.assertRaises(PolicySnapshotError):
                resolve_contract_app_policy(contract, store=self.store.root)

    def test_visible_count_boundaries_preserve_target_and_normalization(self):
        contract = {"unit": {"min_visible_chars": 2200, "target_visible_chars": 3100, "max_visible_chars": 4700}}
        for count, code in ((2199, "RETURN_UNDERPRODUCED"), (2200, None), (4700, None), (4701, "RETURN_OVER_LIMIT")):
            text = "# " + "甲" * count + "\n\t "
            with self.subTest(count=count):
                self.assertEqual(count_visible_chars(text), count)
                if code:
                    with self.assertRaisesRegex(ContractError, code):
                        validate_output_length(contract, text)
                else:
                    self.assertEqual(validate_output_length(contract, text)["visible_chars"], count)
        self.assertEqual(contract["unit"]["target_visible_chars"], 3100)
        self.assertEqual(count_visible_chars("**e\u0301** \n"), 1)


class CapacityContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.InputPackTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def create_run(self, root, contract_path, *, run_id="CAPACITY-RUN"):
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        created = cnw_runner.produce(SimpleNamespace(mode="offline", unit="scene", run_id=run_id,
            work_id=contract["unit"]["id"], contract=str(contract_path), project_root=str(root), create_only=True))
        return Path(created["path"])

    def test_real_contract_preflight_and_run_keep_all_2200_3100_4700_bounds(self):
        for label in ("A", "B", "C"):
            name = f"scenes/{label}/work_order.draft.json"
            value = json.loads(self.fixture.files[name])
            value.update(min_visible_chars=2200, target_visible_chars=3100, max_visible_chars=4700)
            self.fixture.files[name] = fixtures.encoded(value)
            name = f"scenes/{label}/project_seed/config/project.yml"
            self.fixture.files[name] = self.fixture.files[name].replace(b": 60\n", b": 2200\n").replace(b": 90\n", b": 3100\n").replace(b": 120\n", b": 4700\n")
        self.fixture.write_pack()
        root = self.fixture.project("CAPACITY")
        prepared = self.fixture.prepare(root)
        result = write_contract_draft(root, prepared["draft"])
        contract_path = Path(result["contract"])
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        self.assertEqual(tuple(contract["unit"][key] for key in ("min_visible_chars", "target_visible_chars", "max_visible_chars")), (2200, 3100, 4700))
        policy = validate_work_unit_policy(contract)
        self.assertEqual(policy["document"]["execution_compatibility"]["maximum_validated_visible_characters_per_unit"], 4700)
        preflight = build_contract_preflight(root, contract_path, run_id="CAPACITY-RUN")
        self.assertEqual(preflight["policy_version"]["contract_policy_sha256"], policy["sha256"])
        run = self.create_run(root, contract_path)
        self.assertFalse(cnw_runner.load_state(run)["provider_requests"])
        self.assertEqual(json.loads((run / "artifacts/contract.json").read_text(encoding="utf-8")), contract)

    def test_old_4000_contract_run_and_preflight_use_original_registered_policy(self):
        root = self.fixture.project("OLD-CAPACITY")
        prepared = self.fixture.prepare(root)
        result = write_contract_draft(root, prepared["draft"])
        contract_path = Path(result["contract"])
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        store = SnapshotStore(DEFAULT_STORE)
        historical = []
        for entry in store._read_index()["entries"]:
            if entry["availability"] == "AVAILABLE" and "app_policy" in entry["kinds"]:
                raw = store.resolve_snapshot_by_sha(entry["sha256"], expected_kind="app_policy")["bytes"]
                document = json.loads(raw.decode("utf-8-sig"))
                if document.get("execution_compatibility", {}).get("maximum_validated_visible_characters_per_unit") == 4000:
                    historical.append(store.resolve_policy_by_sha(entry["sha256"], expected_kind="app_policy"))
        self.assertTrue(historical)
        old = historical[0]
        # This newly created fictional contract represents an older legal
        # binding; no real history or existing fixture run is rewritten.
        contract["unit"]["policy_sha256"] = old["sha256"]
        contract_path.write_bytes(fixtures.encoded(contract))
        before_contract = contract_path.read_bytes()
        preflight = build_contract_preflight(root, contract_path, run_id="OLD-CAPACITY-RUN")
        self.assertEqual(preflight["policy_version"]["app_policy_sha256"], old["sha256"])
        run = self.create_run(root, contract_path, run_id="OLD-CAPACITY-RUN")
        before = {path.relative_to(root).as_posix(): fixtures.sha(path.read_bytes()) for path in root.rglob("*") if path.is_file()}
        plan = cnw_recovery.plan_recovery(run, root)
        self.assertEqual(plan["status"], "RECOVERY_PLAN_READY")
        self.assertFalse(plan["state_mutated"])
        self.assertEqual(contract_path.read_bytes(), before_contract)
        for name, digest in before.items():
            self.assertEqual(fixtures.sha((root / name).read_bytes()), digest)
        self.assertEqual(store.resolve_policy_by_sha(old["sha256"])["bytes"], old["bytes"])
        changed = copy.deepcopy(contract)
        changed["unit"].update(min_visible_chars=2200, target_visible_chars=3100, max_visible_chars=4700)
        with self.assertRaisesRegex(ContractError, "UNIT_CAPACITY_UNVALIDATED"):
            validate_work_unit_policy(changed)


class CapacityProseTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.InputPackTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        for label in ("A", "B", "C"):
            name = f"scenes/{label}/work_order.draft.json"
            value = json.loads(self.fixture.files[name])
            value.update(min_visible_chars=2200, target_visible_chars=3100, max_visible_chars=4700)
            self.fixture.files[name] = fixtures.encoded(value)
            name = f"scenes/{label}/project_seed/config/project.yml"
            self.fixture.files[name] = self.fixture.files[name].replace(b": 60\n", b": 2200\n").replace(b": 90\n", b": 3100\n").replace(b": 120\n", b": 4700\n")
        self.fixture.write_pack()
        self.root = self.fixture.project("CAPACITY-STAGES")
        prepared = self.fixture.prepare(self.root)
        result = write_contract_draft(self.root, prepared["draft"])
        self.contract_path = Path(result["contract"])
        self.contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        self.model = transport_fixtures.ThreeProjectOfflineE2E()
        # Reuse only its explicit simulated transport receipt writer. No
        # stages, role readers, persistence or validation functions are replaced.
        self.model._guard_lock = threading.Lock()
        self.model._counter = 0
        self.model.requests = []
        self.calls = []

    def new_run(self, run_id):
        return Path(cnw_runner.produce(SimpleNamespace(mode="offline", unit="scene", run_id=run_id,
            work_id="TRIAL-A", contract=str(self.contract_path), project_root=str(self.root), create_only=True))["path"])

    def transport(self, prose_responses):
        replies = iter(prose_responses)
        def dispatch(run, *, stage, role_id, messages, output_cap, extra=None):
            self.calls.append({"run_id": run.name, "stage": stage, "role_id": role_id,
                               "messages": messages, "output_cap": output_cap})
            if stage == "prose":
                content = next(replies)
            else:
                content = self.model._sections(stage, "Mira", "Mira", "a fictional courtyard")
                content = content.replace("100–320 visible characters", "2200–4700 visible characters; target 3100")
                content = content.replace("- Mira: ask directly.\n- Mira: answer briefly and practically.", "- Mira: concise speech.")
            return self.model._workflow_response(run, messages, content, stage=stage, role_id=role_id)
        return dispatch

    def run_prefix(self, run):
        for stage in ("plot", "scene_cards", "writing_brief"):
            cnw_recovery.execute_checked(run, stage)
            state = cnw_runner.load_state(run)
            record = state["stages"][stage]
            path = run / record["artifact"]["path"]
            self.assertEqual(record["status"], "STAGE_MATERIALIZED")
            self.assertEqual(fixtures.sha(path.read_bytes()), record["artifact"]["sha256"])

    def record(self, name, run, outcome):
        destination = os.environ.get("ATOM06_CAPACITY_EVIDENCE_OUTPUT")
        if not destination:
            return
        path = Path(destination)
        document = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
            "execution": "MOCK_ONLY_SIMULATED_OFFLINE", "cases": {}}
        state = cnw_runner.load_state(run)
        artifacts = []
        for artifact in sorted((run / "artifacts").rglob("*")):
            if artifact.is_file():
                raw = artifact.read_bytes()
                artifacts.append({"path": artifact.relative_to(run).as_posix(), "sha256": fixtures.sha(raw),
                                  "artifact_utf8": raw.decode("utf-8")})
        document["cases"][name] = {"outcome": outcome, "contract": self.contract, "state": state,
            "actual_calls": [call for call in self.calls if call["run_id"] == run.name], "actual_artifacts": artifacts}
        path.write_bytes(fixtures.encoded(document))

    def test_underproduced_then_continued_same_brief_to_minimum(self):
        run = self.new_run("CAPACITY-CONTINUE")
        with patch.object(cnw_runner, "cnw_live_call", side_effect=self.transport(["A" * 1000, "B" * 1200])), \
             patch("socket.create_connection", side_effect=AssertionError("Network forbidden")):
            self.run_prefix(run)
            cnw_recovery.execute_checked(run, "prose")
        state = cnw_runner.load_state(run)
        output = cnw_runner._read_stage_text(run, state, "prose")
        self.assertEqual(count_visible_chars(output), 2200)
        calls = [row for row in self.calls if row["stage"] == "prose"]
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(row["output_cap"] == 6152 for row in calls))
        self.assertEqual(set(json.loads(calls[0]["messages"][1]["content"])), {"writing_brief", "voice_samples"})
        continued = json.loads(calls[1]["messages"][1]["content"])
        self.assertEqual(continued["already_written_tail"], "A" * 1000)
        self.assertEqual(continued["still_needed_visible_chars"], 1200)
        self.assertEqual(continued["brief"], calls[0]["messages"][1]["content"])
        self.assertTrue(all(row["mode"] == "MOCK_ONLY" and row["fixture_only"] for row in state["provider_requests"]))
        self.record("underproduction_continued", run, {"visible_chars": 2200, "output_cap": 6152})

    def test_exact_4700_materializes_complete_tail(self):
        run = self.new_run("CAPACITY-EXACT")
        expected = "L" * 4694 + "ENDING"
        with patch.object(cnw_runner, "cnw_live_call", side_effect=self.transport([expected])):
            self.run_prefix(run)
            cnw_recovery.execute_checked(run, "prose")
        state = cnw_runner.load_state(run)
        self.assertEqual(cnw_runner._read_stage_text(run, state, "prose"), expected)
        self.assertEqual(state["stages"]["prose"]["validation"]["actual_visible_chars"], 4700)
        self.record("exact_4700", run, {"visible_chars": 4700, "tail_preserved": True})

    def test_over_limit_rewrites_complete_prose_without_splicing_old_attempt(self):
        run = self.new_run("CAPACITY-REWRITE")
        with patch.object(cnw_runner, "cnw_live_call", side_effect=self.transport(["A" * 4701, "B" * 3100])):
            self.run_prefix(run)
            cnw_recovery.execute_checked(run, "prose")
        state = cnw_runner.load_state(run)
        self.assertEqual(cnw_runner._read_stage_text(run, state, "prose"), "B" * 3100)
        calls = [row for row in self.calls if row["stage"] == "prose"]
        self.assertEqual(len(calls), 2)
        self.assertIn("Rewrite the complete prose", calls[1]["messages"][0]["content"])
        self.assertEqual(calls[1]["messages"][1]["content"], calls[0]["messages"][1]["content"])
        old = next(row for row in state["provider_requests"] if row["stage"] == "prose")
        self.assertEqual(cnw_runner._receipt_content(run, old), "A" * 4701)
        self.record("over_limit_rewrite", run, {"visible_chars": 3100, "old_raw_retained": True})

    def test_exhausted_under_and_over_length_fail_without_materializing_prose(self):
        for label, responses, error in (("UNDER", ["U" * 600] * 3, "PROSE_UNDERPRODUCED"),
                                         ("OVER", ["O" * 4701] * 3, "RETURN_OVER_LIMIT")):
            with self.subTest(label=label):
                run = self.new_run("CAPACITY-FAIL-" + label)
                with patch.object(cnw_runner, "cnw_live_call", side_effect=self.transport(responses)):
                    self.run_prefix(run)
                    plot_before = cnw_runner._read_stage_text(run, cnw_runner.load_state(run), "plot")
                    with self.assertRaisesRegex(ContractError, error):
                        cnw_recovery.execute_checked(run, "prose")
                state = cnw_runner.load_state(run)
                self.assertEqual(state["stages"]["prose"]["status"], "EXECUTION_INCOMPLETE")
                self.assertFalse((run / "artifacts/prose.v0.md").exists())
                self.assertEqual(cnw_runner._read_stage_text(run, state, "plot"), plot_before)
                self.assertEqual(len([row for row in self.calls if row["run_id"] == run.name and row["stage"] == "prose"]), 3)
                self.assertTrue(state["stages"]["prose"]["execution_failures"])
                self.record("exhausted_" + label.lower(), run, {"error": error, "prose_materialized": False})


    def test_transport_truncation_rejects_even_when_length_reaches_minimum(self):
        run = self.new_run("CAPACITY-TRUNCATION")
        with patch.object(cnw_runner, "cnw_live_call", side_effect=self.transport([])):
            self.run_prefix(run)
        mock_ledger = []
        def reserve(args, **kwargs):
            mock_ledger.append({"operation": "reserve", "execution": "MOCK_ONLY", **vars(args)})
            return {"status": "RESERVED", "execution": "MOCK_ONLY"}
        def settle(args, **kwargs):
            mock_ledger.append({"operation": "settle", "execution": "MOCK_ONLY", **vars(args)})
            return {"status": "SETTLED", "execution": "MOCK_ONLY"}
        guard = SimpleNamespace(command_reserve=reserve, command_settle=settle)
        payload = {"id": "SIMULATED-TRUNCATED", "model": cnw_runner.MODEL,
            "choices": [{"finish_reason": "length", "message": {"content": "T" * 2200}}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 6152}}
        response = SimpleNamespace(status_code=200, json=lambda: payload)
        # A direct consumer test of the real transport parser. Its accounting
        # substitute is a local, explicitly MOCK_ONLY list, not a real reserve.
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "SIMULATED-NONLIVE-TEST-KEY"}), \
             patch.object(cnw_runner, "_p2_guard", return_value=guard), \
             patch.object(cnw_runner.httpx, "post", return_value=response) as post, \
             patch.object(cnw_runner, "cnw_live_call", side_effect=cnw_runner._cnw_live_call_in_slot):
            with self.assertRaisesRegex(ContractError, "LIVE_PROVIDER_RESPONSE_INVALID"):
                cnw_recovery.execute_checked(run, "prose")
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs["json"]["max_tokens"], 6152)
        self.assertEqual([row["operation"] for row in mock_ledger], ["reserve", "settle"])
        self.assertEqual(mock_ledger[1]["finish_reason"], "length")
        state = cnw_runner.load_state(run)
        self.assertEqual(state["stages"]["prose"]["status"], "EXECUTION_INCOMPLETE")
        self.assertFalse(any(row["stage"] == "prose" for row in state["provider_requests"]))
        self.assertFalse((run / "artifacts/prose.v0.md").exists())
        raws = [path for path in (run / "artifacts/provider").glob("cnw-*.json") if not path.name.endswith(".request.json")]
        self.assertEqual(len(raws), 1)
        self.assertEqual(json.loads(raws[0].read_text(encoding="utf-8"))["response"], payload)
        self.record("truncated_response", run, {"error": "LIVE_PROVIDER_RESPONSE_INVALID", "mock_accounting": mock_ledger})

    def long_review_transport(self, refine_responses):
        base = self.transport(["L" * 4690 + "WRONG-TAIL"])
        revised = iter(refine_responses)
        def dispatch(run, *, stage, role_id, messages, output_cap, extra=None):
            if stage in {"plot", "scene_cards", "writing_brief", "prose"}:
                return base(run, stage=stage, role_id=role_id, messages=messages, output_cap=output_cap, extra=extra)
            self.calls.append({"run_id": run.name, "stage": stage, "role_id": role_id,
                               "messages": messages, "output_cap": output_cap})
            packet = json.loads(messages[1]["content"])
            if stage == "multi_lens_review":
                findings = [] if role_id != "plot" else [{"finding_id": "TAIL-ISSUE", "severity": "minor",
                    "evidence": "WRONG-TAIL", "issue": "The final response does not close the local action.",
                    "recommendation": "Restore the agreed final response without changing Canon."}]
                content = json.dumps({"lens_id": role_id, "findings": findings})
            elif stage == "adversarial_verify":
                content = json.dumps({"verifier_id": role_id, "votes": [{"finding_id": packet["finding_id"],
                    "verdict": "refuted" if role_id == "continuity_plausibility" else "not_refuted",
                    "evidence": "A simulated independent check of the full tail."}]})
            elif stage == "completeness_critic":
                content = json.dumps({"candidate_findings": [{"finding_id": "OMITTED-CLOSE", "lens_id": "plot",
                    "severity": "minor", "evidence": "WRONG-TAIL", "issue": "The closing response is omitted.",
                    "recommendation": "Keep the final response complete.", "prompt_update": "Check the closing response at the end of the full draft."}]})
            elif stage == "refine":
                content = next(revised)
            elif stage == "re_review":
                content = json.dumps({"lens_id": packet["lens_id"], "findings": []})
            else:
                raise AssertionError("Unexpected model stage: " + stage)
            return self.model._workflow_response(run, messages, content, stage=stage, role_id=role_id)
        return dispatch

    def run_through_completeness(self, run):
        for stage in cnw_runner.CNW_STAGES[:9]:
            cnw_recovery.execute_checked(run, stage)

    def test_long_review_revision_rereview_and_export_keep_full_current_tail(self):
        run = self.new_run("CAPACITY-REVIEW-TAIL")
        expected = "R" * 4694 + "ENDING"
        with patch.object(cnw_runner, "cnw_live_call", side_effect=self.long_review_transport(["S" * 1000, expected])):
            self.run_through_completeness(run)
            state = cnw_runner.load_state(run)
            original = cnw_runner._read_stage_text(run, state, "prose")
            cnw_recovery.execute_checked(run, "refine")
            cnw_recovery.execute_checked(run, "re_review")
        state = cnw_runner.load_state(run)
        self.assertEqual(cnw_runner._read_stage_text(run, state, "prose"), original)
        self.assertEqual(cnw_runner._read_stage_text(run, state, "refine"), expected)
        review_calls = [row for row in self.calls if row["stage"] == "multi_lens_review"]
        self.assertEqual(len(review_calls), 5)
        for row in review_calls:
            self.assertEqual(json.loads(row["messages"][1]["content"])["draft"], original)
            self.assertIn("WRONG-TAIL", original[4000:])
        verifier_calls = [row for row in self.calls if row["stage"] == "adversarial_verify"]
        self.assertEqual(len(verifier_calls), 3)
        self.assertEqual({row["role_id"] for row in verifier_calls}, set(cnw_runner.VERIFIER_IDS))
        for row in verifier_calls:
            self.assertEqual(json.loads(row["messages"][1]["content"])["full_draft"], original)
        verified = json.loads(cnw_runner._read_stage_text(run, state, "adversarial_verify"))
        self.assertEqual(verified["verdicts"]["plot-1"]["status"], "CONFIRMED")
        complete = next(row for row in self.calls if row["stage"] == "completeness_critic")
        self.assertEqual(json.loads(complete["messages"][1]["content"])["draft"], original)
        refine_calls = [row for row in self.calls if row["stage"] == "refine"]
        self.assertEqual(len(refine_calls), 2)
        self.assertTrue(all(row["output_cap"] == 6152 for row in refine_calls))
        self.assertIn("OMITTED-CLOSE", refine_calls[0]["messages"][1]["content"])
        self.assertIn("WRONG-TAIL", refine_calls[1]["messages"][1]["content"])
        rereview_calls = [row for row in self.calls if row["stage"] == "re_review"]
        self.assertTrue(rereview_calls)
        for row in rereview_calls:
            self.assertEqual(json.loads(row["messages"][1]["content"])["draft"], expected)
        rereview = json.loads(cnw_runner._read_stage_text(run, state, "re_review"))
        self.assertEqual(rereview["candidate_sha256"], fixtures.sha(expected.encode()))
        exported = cnw_export.export_reading_package(run, state, project_root=self.root)
        exports = Path(exported["deliverables"])
        for name in ("02_修订稿.md", "02_修订稿.txt"):
            self.assertEqual((exports / name).read_bytes(), expected.encode())
        self.assertIn(expected, (exports / "03_前后文连读.html").read_text(encoding="utf-8"))
        reading = (exports / "03_前后文连读.md").read_text(encoding="utf-8")
        self.assertIn("SOURCE-1 final.", reading)
        self.assertIn("SOURCE-2 final.", reading)
        self.assertIn(expected, reading)
        self.assertFalse(exported["user_creative_accepted"])
        self.assertTrue(all(row["mode"] == "MOCK_ONLY" for row in state["provider_requests"]))
        self.record("long_tail_review_revision_export", run, {"initial_visible_chars": 4700,
            "revised_visible_chars": 4700, "full_current_rereview": True, "export": exported})

    def test_refine_over_limit_and_exhausted_under_length_preserve_v0(self):
        for label, replies, error in (("OVER", ["O" * 4701], "RETURN_OVER_LIMIT"),
                                       ("UNDER", ["U" * 1000] * 3, "REVISION_REGRESSION")):
            with self.subTest(label=label):
                run = self.new_run("CAPACITY-REFINE-" + label)
                with patch.object(cnw_runner, "cnw_live_call", side_effect=self.long_review_transport(replies)):
                    self.run_through_completeness(run)
                    original = cnw_runner._read_stage_text(run, cnw_runner.load_state(run), "prose")
                    with self.assertRaisesRegex(ContractError, error):
                        cnw_recovery.execute_checked(run, "refine")
                state = cnw_runner.load_state(run)
                self.assertEqual(cnw_runner._read_stage_text(run, state, "prose"), original)
                self.assertEqual(state["stages"]["refine"]["status"], "EXECUTION_INCOMPLETE")
                self.assertFalse((run / "artifacts/prose.v1.md").exists())
                self.record("refine_failure_" + label.lower(), run, {"error": error, "v0_preserved": True})


if __name__ == "__main__":
    unittest.main()
