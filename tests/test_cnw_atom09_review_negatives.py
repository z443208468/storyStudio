"""Actual CNW consumers for empty reviews, verifier gates and a bad revision."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_cnw_atom09_three_project_e2e as fixtures
from tools import cnw_recovery, cnw_runner
from tools.cnw_contract import ContractError


class ReviewConsumerNegatives(unittest.TestCase):
    def setUp(self):
        self.harness = fixtures.ThreeProjectOfflineE2E()
        self.harness.setUp()
        self.addCleanup(self.harness.doCleanups)
        self.h = self.harness
        self.project = self.h._project("TEST_REVIEW_NEGATIVES", "Synthetic Review Boundaries",
                                      ("Sana", "Keeper"), "coast")

    def _run(self, run_id, root=None):
        root = root or self.project
        contract = self.h._contract(root, run_id, "ORIGINAL_EPISODE", names=("Sana", "Keeper"),
            setting="coast", kind="episode", first_episode=True)
        self.h.run_context[run_id] = next(value for value in self.h.projects.values() if value["root"] == root)
        args = SimpleNamespace(mode="offline", run_id=run_id, work_id=run_id, unit="episode",
            project_root=str(root), contract=str(root / f"contracts/{run_id}.json"), create_only=True)
        return root / "runs" / cnw_runner.produce(args)["run_id"]

    def _response(self, run, messages, content, stage, role_id):
        return self.h._workflow_response(run, messages, content, stage=stage, role_id=role_id)

    def test_no_findings_create_no_verifier_refine_or_rereview_requests(self):
        run = self._run("NO-FINDINGS")
        clean = ("Sana found a small problem near the coast. She asked Keeper for a practical tool. "
                 "The two neighbors solved the problem together, and Sana asked where to return it.")

        def transport(run, *, stage, role_id, messages, output_cap, extra=None):
            if stage == "multi_lens_review":
                content = json.dumps({"lens_id": role_id, "findings": []})
            elif stage == "completeness_critic":
                content = '{"candidate_findings":[]}'
            elif stage == "prose":
                content = clean
            elif stage in {"adversarial_verify", "refine", "re_review"}:
                raise AssertionError("An empty review must not fabricate a model task")
            else:
                return self.h._transport(run, stage=stage, role_id=role_id, messages=messages,
                                         output_cap=output_cap, extra=extra)
            return self._response(run, messages, content, stage, role_id)

        with patch.object(cnw_runner, "cnw_live_call", side_effect=transport):
            for stage in cnw_runner.CNW_STAGES:
                cnw_recovery.execute_checked(run, stage)
        state = cnw_runner.load_state(run)
        self.assertEqual(cnw_runner._read_stage_text(run, state, "refine"), clean)
        review = json.loads(cnw_runner._read_stage_text(run, state, "re_review"))
        self.assertEqual(review["status"], "NO_CHANGED_TEXT")
        self.assertFalse(any(row["stage"] in {"adversarial_verify", "refine", "re_review"}
                             for row in state["provider_requests"]))
        self.assertEqual(sum(row["stage"] == "multi_lens_review" for row in state["provider_requests"]), 5)
        self.h._public_evidence("zero_finding_chain", self.project, {"run_id": run.name,
            "verifier_model_calls": 0, "refine_model_calls": 0, "rereview_model_calls": 0,
            "prose_preserved": True, "real_provider_calls": 0})

    def test_two_projects_actual_lint_stages_apply_their_own_rules_without_editing(self):
        other = self.h._project("TEST_LINT_OTHER", "Synthetic Different Lint Rules", ("Sana", "Keeper"), "coast")
        observations = []
        for root, cap in ((self.project, 0), (other, 10)):
            rules = ("## Layer 1\n| Rule | Pattern | Cap | Notes |\n|---|---|---|---|\n"
                     f"| Selected name | `Sana` | {cap} | Candidate only |\n"
                     "## Layer 2\n| Rule | Pattern | Cap | Notes |\n|---|---|---|---|\n"
                     f"| Relationship claim | `sibling` | {cap} | Candidate only |\n")
            fixtures._write(root, "92_style_engine/forbidden_patterns.md", rules)
            run = self._run(f"LINT-CAP-{cap}", root)
            with patch.object(cnw_runner, "cnw_live_call", side_effect=self.h._transport):
                for stage in cnw_runner.CNW_STAGES[:4]:
                    cnw_recovery.execute_checked(run, stage)
                state = cnw_runner.load_state(run)
                prose = cnw_runner._read_stage_text(run, state, "prose")
                prose_path = run / state["stages"]["prose"]["artifact"]["path"]
                before = prose_path.read_bytes()
                for stage in ("lint_layer1", "lint_layer2"):
                    cnw_recovery.execute_checked(run, stage)
            state = cnw_runner.load_state(run)
            self.assertEqual(prose_path.read_bytes(), before)
            reports = {stage: json.loads(cnw_runner._read_stage_text(run, state, stage))
                       for stage in ("lint_layer1", "lint_layer2")}
            for report in reports.values():
                self.assertFalse(report["text_modified"])
                self.assertEqual(report["rules_sha256"], fixtures._sha((root / "92_style_engine/forbidden_patterns.md").read_bytes()))
                self.assertEqual(bool(report["findings"]), cap == 0)
            observations.append({"cap": cap, "prose_sha256": fixtures._sha(before), "reports": reports})
            self.h._public_evidence(f"lint_project_cap_{cap}", root, observations[-1])
        self.assertEqual(observations[0]["prose_sha256"], observations[1]["prose_sha256"])
        self.assertNotEqual(observations[0]["reports"]["lint_layer1"]["rules_sha256"],
                            observations[1]["reports"]["lint_layer1"]["rules_sha256"])

    def test_actual_verifier_consumer_enforces_threshold_and_rejects_bad_tickets(self):
        outcomes = {}
        for count in range(4):
            run = self._run(f"VOTE-{count}")

            def transport(run, *, stage, role_id, messages, output_cap, extra=None):
                if stage != "adversarial_verify":
                    return self.h._transport(run, stage=stage, role_id=role_id, messages=messages,
                                             output_cap=output_cap, extra=extra)
                index = cnw_runner.VERIFIER_IDS.index(role_id)
                verdict = "not_refuted" if index < count else "uncertain"
                value = {"verifier_id": role_id, "votes": [{"finding_id": extra["finding_id"], "verdict": verdict}]}
                return self._response(run, messages, json.dumps(value), stage, role_id)

            with patch.object(cnw_runner, "cnw_live_call", side_effect=transport):
                for stage in cnw_runner.CNW_STAGES[:8]:
                    cnw_recovery.execute_checked(run, stage)
            state = cnw_runner.load_state(run)
            report = json.loads(cnw_runner._read_stage_text(run, state, "adversarial_verify"))
            verdict = next(iter(report["verdicts"].values()))
            self.assertEqual(verdict["status"], "CONFIRMED" if count >= 2 else "REFUTED_OR_UNCERTAIN")
            self.assertEqual(len([row for row in state["provider_requests"] if row["stage"] == "adversarial_verify"]), 3)
            outcomes[str(count)] = verdict
        for fault in ("duplicate", "missing", "wrong-finding"):
            run = self._run("BAD-" + fault.upper())

            def bad_transport(run, *, stage, role_id, messages, output_cap, extra=None):
                if stage != "adversarial_verify":
                    return self.h._transport(run, stage=stage, role_id=role_id, messages=messages,
                                             output_cap=output_cap, extra=extra)
                vote = {"finding_id": "WRONG" if fault == "wrong-finding" else extra["finding_id"],
                        "verdict": "not_refuted"}
                value = {"verifier_id": role_id, "votes": [] if fault == "missing" else
                         [vote, vote] if fault == "duplicate" else [vote]}
                return self._response(run, messages, json.dumps(value), stage, role_id)

            with patch.object(cnw_runner, "cnw_live_call", side_effect=bad_transport):
                for stage in cnw_runner.CNW_STAGES[:7]:
                    cnw_recovery.execute_checked(run, stage)
                with self.assertRaisesRegex(ContractError, "LIVE_VERIFIER_VOTES_INVALID"):
                    cnw_recovery.execute_checked(run, "adversarial_verify")
            self.assertEqual(cnw_runner.load_state(run)["stages"]["adversarial_verify"]["status"], "EXECUTION_INCOMPLETE")
            outcomes[fault] = "REJECTED"
        self.h._public_evidence("actual_verifier_matrix", self.project, {"outcomes": outcomes, "real_provider_calls": 0})

    def test_rereview_detects_a_new_violation_in_actual_refined_text(self):
        canon = self.project / "90_canon/canon.md"
        canon.write_text(canon.read_text(encoding="utf-8") + "\nKeeper's lamp must remain in place.\n", encoding="utf-8")
        canon_before = canon.read_bytes()
        run = self._run("NEW-REVISION-DEFECT")
        bad_revision = ("Sana found the small problem near the coast. She asked Keeper for a practical tool. "
                        "The neighbors solved it together, and she asked where to return it. "
                        "Then Sana removed Keeper's lamp.")
        observed_candidates = []

        def transport(run, *, stage, role_id, messages, output_cap, extra=None):
            if stage == "refine":
                return self._response(run, messages, bad_revision, stage, role_id)
            if stage == "re_review":
                self.assertIn(bad_revision, json.dumps(messages, ensure_ascii=False))
                observed_candidates.append(extra["candidate_sha256"])
                if role_id in cnw_runner.VERIFIER_IDS:
                    value = {"verifier_id": role_id, "votes": [{"finding_id": extra["finding_id"], "verdict": "not_refuted"}]}
                else:
                    value = {"lens_id": role_id, "findings": [{"severity": "P1", "issue": "The revision newly moves the protected lamp.",
                        "evidence": "Sana removed Keeper's lamp.", "recommendation": "Keep the lamp in place."}]
                        if role_id == "canon" else []}
                return self._response(run, messages, json.dumps(value), stage, role_id)
            return self.h._transport(run, stage=stage, role_id=role_id, messages=messages,
                                     output_cap=output_cap, extra=extra)

        with patch.object(cnw_runner, "cnw_live_call", side_effect=transport):
            for stage in cnw_runner.CNW_STAGES[:-1]:
                cnw_recovery.execute_checked(run, stage)
            initial_state = cnw_runner.load_state(run)
            initial_prose = cnw_runner._read_stage_text(run, initial_state, "prose")
            with self.assertRaisesRegex(ContractError, "REREVIEW_REQUIRES_REVISION"):
                cnw_recovery.execute_checked(run, "re_review")
        state = cnw_runner.load_state(run)
        self.assertEqual(state["status"], "REVISION_REQUIRED")
        self.assertEqual(canon.read_bytes(), canon_before)
        self.assertEqual(cnw_runner._read_stage_text(run, state, "prose"), initial_prose)
        self.assertTrue(observed_candidates)
        self.assertTrue(all(digest == fixtures._sha(bad_revision.encode()) for digest in observed_candidates))
        self.assertEqual(len(list((run / "artifacts/revisions").glob("review-*.json"))), 3)
        self.h._public_evidence("new_revision_violation", self.project, {"run_id": run.name,
            "status": state["status"], "new_candidate_sha256": fixtures._sha(bad_revision.encode()),
            "fresh_review_requests": len(observed_candidates), "canon_and_initial_prose_preserved": True,
            "real_provider_calls": 0})
