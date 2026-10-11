"""Early CNW end-to-end gate: real stage consumers, isolated MOCK_ONLY transport."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from tools import cnw_runner as runner, cnw_recovery, cnw_export, cnw_lint
from tools.cnw_contract import ContractError
from tools.cnw_project import import_source, init_registered_project, write_contract_draft
from tools.cnw_roles import build_author_role_messages
from tools.project_paths import create_project, setup_data_home


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write(project: Path, relative: str, text: str) -> Path:
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class EarlyCNWE2EGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="storystudio-early-cnw-e2e-")
        self.addCleanup(self.temp.cleanup)
        self.temp_root = Path(self.temp.name)
        self.data_home = self.temp_root / "ExplicitTestDataHome"
        setup_data_home(self.data_home, pointer_path=self.temp_root / "test-user-config" / "setup.json")
        registered = create_project(project_id="TIDELINE", display_name="Synthetic Harbor Project",
                                    data_home=self.data_home)
        self.project = Path(registered["project_root"])
        init_registered_project(self.project)
        self._prepare_project_inputs()
        self.source_a_path = self.temp_root / "source-A.md"
        self.source_a_path.write_text("A_ONLY_SECRET_CANARY: Mira inherited the harbor.\n", encoding="utf-8")
        self.source_b_path = self.temp_root / "source-B.md"
        self.source_b_path.write_text("Mira asks the keeper to help with a loose hinge.\n", encoding="utf-8")
        self.source_a = import_source(input_file=self.source_a_path, project_root=self.project)
        self.source_b = import_source(input_file=self.source_b_path, project_root=self.project)
        self.contract = self._make_adapt_contract()
        self.run_id = "EARLY-E2E-ADAPT"

    def _prepare_project_inputs(self):
        files = {
            "94_runtime/current_state.md": "Mira and the keeper are neighbors; their relationship is not familial.",
            "07_draft/manuscript_index.md": "No prior story chapter has been accepted.",
            "04_chapter_design/arc_index.md": "Arc 01 — a neighborly repair and a small change in trust.",
            "04_chapter_design/arc_01.md": "Mira chooses whether to ask her neighbor for help with the harbor door.",
            "04_chapter_design/arc_01_episode_details.md": "Keep the action to one hinge repair and its immediate social consequence.",
            "90_canon/canon.md": "Mira and the keeper are neighbors. They are not related. The harbor door has a loose hinge.",
            "90_canon/character_bible.md": "Mira asks direct questions. The keeper answers briefly and offers practical help.",
            "90_canon/world_bible.md": "A small fictional harbor has a public door with a loose hinge.",
            "90_canon/timeline.md": "The scene occurs on an ordinary afternoon.",
            "90_canon/glossary.md": "Harbor door: the public entrance beside the workshop.",
            "92_style_engine/style_guide.md": "Use close third person, concrete action, and distinct dialogue.",
            "92_style_engine/forbidden_patterns.md": "## Layer 1\n\n## Layer 2\n",
            "92_style_engine/character_voice_samples.md": "## Mira\n'I would rather ask than guess.'\n\n## Keeper\n'Try this screwdriver.'\n",
        }
        for relative, text in files.items():
            _write(self.project, relative, text)

    def _make_adapt_contract(self):
        duty = "Check whether this project makes a practical offer feel emotionally earned."
        draft = {
            "schema_version": "cnw_work_unit_draft_v2",
            "work_intent": "ADAPT_SOURCE",
            "unit_id": "ADAPT-HINGE-01",
            "kind": "scene",
            "language_locale": "en-US",
            "pov": "Mira",
            "target_visible_chars": 150,
            "min_visible_chars": 100,
            "max_visible_chars": 250,
            "chapter_context": "A small repair gives two neighbors a reason to speak plainly.",
            "role_in_story": "Adapt only the selected source moment into one playable scene.",
            "reader_reward": "See a practical offer change the distance between neighbors.",
            "entry_state": "The hinge is loose and Mira has not asked for help.",
            "exit_state": "The hinge works and Mira has made a specific next request.",
            "required_beats": [{"beat_id": "B01", "goal": "Mira asks for help and responds to the offer."}],
            "characters_in_scene": ["Mira", "Keeper"],
            "character_knowledge_boundary_ref": "90_canon/canon.md",
            "forbidden_future_revelations": ["Do not invent a family relationship or future secret."],
            "voice_sample_refs": ["Mira", "Keeper"],
            "review": {"fifth_lens": {"id": "harbor-reader-promise", "responsibility": duty}},
            "source_id": self.source_b["source_id"],
            "source_revision_id": self.source_b["source_revision_id"],
            "source_manifest_revision_sha256": self.source_b["source_manifest_sha256"],
            "source_index_revision_sha256": self.source_b["source_index_sha256"],
            "start_line": 1,
            "end_line": 1,
            "arc_ref": "04_chapter_design/arc_01.md",
            "integrations": {"nk": "DISABLED", "critics": "DISABLED"},
        }
        draft_path = self.project / "contracts/ADAPT-HINGE-01.draft.json"
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
        write_contract_draft(self.project, draft_path)
        return json.loads((self.project / "contracts/ADAPT-HINGE-01.json").read_text(encoding="utf-8"))

    def _outputs(self):
        from tools.cnw_roles import ROLE_REQUIRED_SECTIONS
        plot = []
        for heading in ROLE_REQUIRED_SECTIONS["plot"]:
            body = ("- S1 Mira asks for a screwdriver and steadies the public door."
                    if heading == "## Key Scenes" else
                    "- B01 Mira asks for help, accepts a practical offer, and chooses a next step."
                    if heading == "## Required Story Beats" else "Synthetic Plot context.")
            plot.append(f"{heading}\n{body}")
        cards = []
        for heading in ROLE_REQUIRED_SECTIONS["cards"]:
            cards.append(f"{heading}\nB01 Mira asks; the keeper responds with a screwdriver.")
        brief = []
        for heading in ROLE_REQUIRED_SECTIONS["brief"]:
            body = ("One scene; 100–250 visible characters; preserve B01."
                    if heading == "## Scene-by-Scene Instructions" else
                    "Mira: direct question. Keeper: brief practical offer."
                    if heading == "## Voice References" else "Synthetic project constraints.")
            brief.append(f"{heading}\n{body}")
        prose = ("Mira found the hinge loose again. ‘Could you help me with this?’ she asked. "
                 "The keeper offered a screwdriver, and they steadied the door together. "
                 "Someone told Mira the keeper was her brother, though the project Canon says they are neighbors.")
        revised = ("Mira tested the loose hinge. ‘Could you help me with this?’ she asked. "
                   "The keeper offered a screwdriver. She steadied the door while he tightened one screw. "
                   "When it swung freely, Mira thanked him and asked where to return the tool.")
        return {"plot": "\n\n".join(plot), "scene_cards": "\n\n".join(cards),
                "writing_brief": "\n\n".join(brief), "prose": prose, "refine": revised}

    def _simulated_transport(self, outputs, requests, *, fail_once=None):
        guard = threading.Lock()
        counter = 0
        failures = set()
        def transport(run_dir, *, stage, role_id, messages, output_cap, extra=None):
            nonlocal counter
            with guard:
                if fail_once == stage and stage not in failures:
                    failures.add(stage)
                    raise RuntimeError("SYNTHETIC_TRANSPORT_INTERRUPTION")
                counter += 1
                request_id = f"MOCK-{counter:04d}-{stage}-{role_id}"
            request_payload = {"messages": messages}
            request_raw = json.dumps(request_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            request_path = run_dir / "artifacts/provider" / f"{request_id}.request.json"
            request_path.parent.mkdir(parents=True, exist_ok=True)
            request_path.write_bytes(request_raw)
            content = self._response(stage, role_id, extra, outputs, messages)
            raw_raw = json.dumps({"choices": [{"message": {"content": content}}]},
                                 ensure_ascii=False, sort_keys=True).encode("utf-8")
            raw_path = request_path.with_suffix(".raw.json")
            raw_path.write_bytes(raw_raw)
            receipt = {"request_id": request_id, "provider_request_id": request_id,
                "request_fingerprint": sha(json.dumps([stage, role_id, messages], ensure_ascii=False,
                    sort_keys=True).encode("utf-8")), "stage": stage, "role_id": role_id,
                "status": "SUCCEEDED", "mode": "MOCK_ONLY", "simulation_status": "SIMULATED",
                "fixture_only": True, "request_path": request_path.relative_to(run_dir).as_posix(),
                "request_sha256": sha(request_raw),
                "input_sha256": sha(json.dumps(messages, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")).encode("utf-8")),
                "raw_response_path": raw_path.relative_to(run_dir).as_posix(),
                "raw_response_sha256": sha(raw_raw), "output_sha256": sha(content.encode("utf-8"))}
            with runner.locked_run(run_dir):
                state = runner.load_state(run_dir)
                state.setdefault("provider_requests", []).append(receipt)
                runner.save_state(run_dir, state)
            request_info = {"stage": stage, "role_id": role_id,
                "request_id": request_id, "input_sha256": receipt["input_sha256"],
                "request_sha256": receipt["request_sha256"], "mode": receipt["mode"],
                "messages": messages}
            if stage in {"plot", "scene_cards", "writing_brief", "prose"}:
                try:
                    user_payload = json.loads(messages[1]["content"])
                    request_info["material_keys"] = sorted(user_payload.get("materials", user_payload).keys())
                except (IndexError, TypeError, json.JSONDecodeError):
                    request_info["material_keys"] = []
            requests.append(request_info)
            return content, receipt
        return transport

    def _response(self, stage, role_id, extra, outputs, messages):
        if stage == "refine":
            wire = json.dumps(messages, ensure_ascii=False)
            if "OMITTED-READER-PAYOFF" not in wire or "canon-1" not in wire:
                raise AssertionError("Refine did not consume Completeness and confirmed 2/3 feedback")
            return outputs["refine"]
        if stage in outputs:
            return outputs[stage]
        if stage == "multi_lens_review":
            if role_id == "canon":
                return json.dumps({"lens_id": role_id, "findings": [{
                    "finding_id": "FALSE-CANON-01", "severity": "P1",
                    "issue": "The draft invents a family relationship contradicted by project Canon.",
                    "evidence": "the keeper was her brother", "recommendation": "Remove the invented relation."}]})
            return json.dumps({"lens_id": role_id, "findings": []})
        if stage == "adversarial_verify":
            finding_id = extra["finding_id"]
            verdict = "refuted" if role_id == "continuity_plausibility" else "not_refuted"
            return json.dumps({"verifier_id": role_id,
                               "votes": [{"finding_id": finding_id, "verdict": verdict,
                                          "reason": "SYNTHETIC independent countercheck."}]})
        if stage == "completeness_critic":
            return json.dumps({"candidate_findings": [{
                "finding_id": "OMITTED-READER-PAYOFF", "lens_id": "story_specific",
                "category": "reader_reward", "issue": "The next request should earn a concrete response.",
                "evidence": "The initial draft ends without a follow-up choice.",
                "recommendation": "Add a small, observable next request.",
                "prompt_update": "Check that a practical offer leads to a concrete next request."}]})
        if stage == "re_review":
            self.rereview_messages.append((role_id, json.dumps(messages, ensure_ascii=False)))
            return json.dumps({"lens_id": role_id, "findings": []})
        raise AssertionError(f"unexpected simulated model stage: {stage}/{role_id}")

    def test_early_cnw_e2e_gate_real_11_stage_chain_recovery_review_and_export(self):
        outputs = self._outputs()
        requests = []
        self.rereview_messages = []
        args = type("OfflineRunArgs", (), {"mode": "offline", "unit": "scene",
            "run_id": self.run_id, "work_id": self.contract["unit"]["id"],
            "contract": str(self.project / "contracts/ADAPT-HINGE-01.json"),
            "project_root": str(self.project), "create_only": True})()
        created = runner.produce(args)
        run_dir = Path(created["path"])
        state_before = runner.load_state(run_dir)
        self.assertFalse(state_before["fixture_only"])
        self.assertEqual(self.contract["work_intent"], "ADAPT_SOURCE")
        self.assertNotIn("before_anchor", self.contract["story"])
        self.assertNotIn("after_anchor", self.contract["story"])
        provider = self._simulated_transport(outputs, requests, fail_once="scene_cards")
        stage_log = []

        with patch.object(runner, "cnw_live_call", side_effect=provider):
            for stage in runner.CNW_STAGES:
                if stage == "scene_cards":
                    plot_state = runner.load_state(run_dir)
                    plot_record = plot_state["stages"]["plot"]
                    plot_file = run_dir / plot_record["artifact"]["path"]
                    plot_hash = sha(plot_file.read_bytes())
                    repeated = cnw_recovery.execute_checked(run_dir, "plot")
                    self.assertEqual(repeated["status"], "STAGE_REUSED")
                    self.assertEqual(sha(plot_file.read_bytes()), plot_hash)
                    with self.assertRaisesRegex(RuntimeError, "SYNTHETIC_TRANSPORT_INTERRUPTION"):
                        cnw_recovery.execute_checked(run_dir, stage)
                    interrupted = runner.load_state(run_dir)
                    self.assertEqual(interrupted["stages"][stage]["status"], "EXECUTION_INCOMPLETE")
                    self.assertEqual(sha(plot_file.read_bytes()), plot_hash)
                    recovery_plan = cnw_recovery.plan_recovery(run_dir, self.project)
                    self.assertEqual(recovery_plan["status"], "RECOVERY_BLOCKED_EXECUTION_HISTORY")
                    self.assertEqual(recovery_plan["next_stage_candidate"], "scene_cards")
                    self.assertFalse(recovery_plan["resume_executed"])
                    self.assertFalse(recovery_plan["state_mutated"])
                result = cnw_recovery.execute_checked(run_dir, stage)
                state = runner.load_state(run_dir)
                record = state["stages"][stage]
                artifact = run_dir / record["artifact"]["path"]
                artifact_sha = sha(artifact.read_bytes())
                self.assertTrue(artifact.read_bytes())
                self.assertEqual(record["artifact"]["sha256"], artifact_sha)
                self.assertIn(record["status"], runner._MATERIALIZED)
                self.assertEqual(state["run_id"], self.run_id)
                self.assertEqual(state["contract_sha256"], state_before["contract_sha256"])
                self.assertEqual(state["project_id"], self.contract["project_id"])
                stage_log.append({"stage": stage, "result": result, "artifact_path": record["artifact"]["path"],
                    "artifact_sha256": artifact_sha, "execution_identity_sha256": record["execution_identity"]["sha256"],
                    "execution_input_sha256": record.get("execution_input_identity", {}).get("input_sha256"),
                    "execution_input_hashes": record.get("execution_input_identity", {}).get("input_hashes", {}),
                    "provider_request_ids": list(record.get("provider_request_ids", []))})

        state = runner.load_state(run_dir)
        self.assertEqual(list(state["stages"]), list(runner.CNW_STAGES))
        self.assertEqual([item["stage"] for item in stage_log], list(runner.CNW_STAGES))
        self.assertEqual(state["stages"]["scene_cards"]["execution_failures"][0]["error_type"], "RuntimeError")
        self.assertFalse(state.get("support_hooks", {}).get("nk_pov"))
        self.assertFalse(any(row.get("role_id") == "nk_pov" for row in state["provider_requests"]))
        plot_receipt = next(row for row in state["provider_requests"] if row["stage"] == "plot")
        plot_wire = json.loads((run_dir / plot_receipt["request_path"]).read_text(encoding="utf-8"))
        plot_messages = json.dumps(plot_wire["messages"], ensure_ascii=False)
        plot_payload = json.loads(plot_wire["messages"][1]["content"])
        preparation = plot_payload["support"]["production_preparation"]
        self.assertIn("Mira asks the keeper to help with a loose hinge.",
                      preparation["documents"]["selected_source_excerpt"])
        self.assertEqual(preparation["source_hashes"]["selected_source_excerpt"], self.source_b["source_revision_id"])
        self.assertNotIn("A_ONLY_SECRET_CANARY", plot_messages)
        self.assertNotIn("before_anchor", plot_payload["assignment"]["story"])
        self.assertNotIn("after_anchor", plot_payload["assignment"]["story"])
        self.assertEqual(self.source_b["source_revision_id"], self.contract["source"]["source_revision_id"])
        self.assertEqual(self.contract["project_instance_id"], self.contract["source"]["project_instance_id"])
        self.assertEqual(len(state["provider_requests"]), len(requests))
        self.assertTrue(all(row.get("mode") == "MOCK_ONLY" and row.get("simulation_status") == "SIMULATED"
                            for row in state["provider_requests"]))
        for row in stage_log:
            stage_record = state["stages"][row["stage"]]
            identity = stage_record.get("execution_input_identity")
            self.assertIsInstance(identity, dict)
            self.assertEqual(len(identity.get("input_sha256", "")), 64)
            self.assertIsInstance(identity.get("input_hashes"), dict)
        from tools.cnw_roles import AUTHOR_ROLE_READS
        expected_reads = {
            "plot": set(AUTHOR_ROLE_READS["plot"]),
            "scene_cards": set(AUTHOR_ROLE_READS["cards"]),
            "writing_brief": set(AUTHOR_ROLE_READS["brief"] + ("90_canon/canon.md",
                                  "90_canon/timeline.md", "90_canon/world_bible.md",
                                  "90_canon/glossary.md")),
            "prose": {"writing_brief", "voice_samples"},
        }
        expected_roles = {"plot": "plot_agent", "scene_cards": "scene_card_agent",
                          "writing_brief": "brief_agent", "prose": "prose_agent_1"}
        for stage, role_id in expected_roles.items():
            matches = [item for item in requests if item["stage"] == stage and item["role_id"] == role_id]
            self.assertTrue(matches, f"missing request {stage}/{role_id}; actual={[(r['stage'], r['role_id']) for r in requests]}")
            request = matches[0]
            self.assertEqual(set(request["material_keys"]), expected_reads[stage])
        self.assertNotIn("nk_payload", state["stages"]["writing_brief"]["execution_input_identity"]["input_hashes"])
        from tools import cnw_nk_adapter
        brief_identity_sha = cnw_recovery.stage_identity(run_dir, "writing_brief")["sha256"]
        with patch.object(cnw_nk_adapter, "build_nk_payload", side_effect=AssertionError("disabled NK builder must not run")):
            self.assertEqual(cnw_recovery.stage_identity(run_dir, "writing_brief")["sha256"], brief_identity_sha)
        with self.assertRaisesRegex(ContractError, "MOCK_RECEIPT_CANNOT_PROVE_LIVE"):
            runner.verify_live(args)

        initial_prose = runner._read_stage_text(run_dir, state, "prose")
        lens_index = json.loads(runner._read_stage_text(run_dir, state, "multi_lens_review"))
        self.assertTrue(any(row["lens_id"] == "canon" for row in lens_index["findings"]))
        verify = json.loads(runner._read_stage_text(run_dir, state, "adversarial_verify"))
        canon_id = next(row["finding_id"] for row in verify["findings"] if row["lens_id"] == "canon")
        self.assertEqual(verify["verdicts"][canon_id]["status"], "CONFIRMED")
        self.assertEqual(sum(v == "not_refuted" for v in verify["verdicts"][canon_id]["votes"].values()), 2)
        completeness = json.loads(runner._read_stage_text(run_dir, state, "completeness_critic"))
        self.assertEqual(completeness["candidate_findings"][0]["finding_id"], "OMITTED-READER-PAYOFF")
        refined = runner._read_stage_text(run_dir, state, "refine")
        self.assertNotEqual(sha(initial_prose.encode("utf-8")), sha(refined.encode("utf-8")))
        self.assertNotIn("her brother", refined)
        self.assertTrue(self.rereview_messages)
        self.assertTrue(all("return the tool" in wire for _, wire in self.rereview_messages))
        rereview = json.loads(runner._read_stage_text(run_dir, state, "re_review"))
        self.assertEqual(rereview["status"], "CLEAN")
        self.assertEqual(rereview["candidate_sha256"], sha(refined.encode("utf-8")))
        canon_before_export = (self.project / "90_canon/canon.md").read_bytes()
        result = cnw_export.export_reading_package(run_dir, state, project_root=self.project)
        self.assertEqual(result["status"], "EXPORT_READY")
        reading = Path(result["deliverables"]) / "03_前后文连读.md"
        self.assertTrue(reading.is_file() and reading.stat().st_size > 0)
        self.assertEqual((self.project / "90_canon/canon.md").read_bytes(), canon_before_export)

        # The negative matrix uses the production role builder, lint parser and
        # verifier validators; it does not replace any stage executor.
        prose_materials = {"07_draft/<work_id>_writing_brief.md": "## Voice References\n- Mira\n",
                           "92_style_engine/character_voice_samples.md": "## Mira\nI ask first.\n",
                           "cross_project_secret": "CROSS_PROJECT_CANARY"}
        messages = build_author_role_messages("prose", self.contract, prose_materials)
        self.assertNotIn("CROSS_PROJECT_CANARY", json.dumps(messages, ensure_ascii=False))
        self.assertEqual(set(json.loads(messages[1]["content"])), {"writing_brief", "voice_samples"})
        forbidden = self.temp_root / "forbidden-rules.md"
        forbidden.write_text("## Layer 1\n| Rule | Pattern | Cap |\n|---|---|---:|\n| BANNED | `BANNED_WORD` | 0 |\n## Layer 2\n", encoding="utf-8")
        lint_result = cnw_lint.lint("A BANNED_WORD slips in.", "surface", forbidden)
        self.assertEqual(lint_result["findings"][0]["rule_id"], "BANNED")
        self.assertFalse(lint_result["text_modified"])
        with self.assertRaisesRegex(ContractError, "LIVE_FINDING_IDENTITY_INVALID"):
            runner._validate_finding_identities([{"finding_id": "DUP"}, {"finding_id": "DUP"}])
        with self.assertRaisesRegex(ContractError, "LIVE_VERIFIER_VOTES_INVALID"):
            runner._single_verifier_vote({"verifier_id": "correctness", "votes": [
                {"finding_id": "OTHER", "verdict": "not_refuted"}]}, "correctness", "EXPECTED")

        evidence = {
            "schema_version": "early_cnw_e2e_gate_evidence_v1",
            "execution": "SYNTHETIC_OFFLINE_ONLY",
            "run_identity": {"run_id": self.run_id, "project_id": self.contract["project_id"],
                "project_instance_id": self.contract["project_instance_id"],
                "contract_sha256": state["contract_sha256"], "work_intent": self.contract["work_intent"],
                "source_id": self.contract["source"]["source_id"],
                "source_revision_id": self.contract["source"]["source_revision_id"],
                "source_manifest_revision_sha256": self.contract["source"]["manifest_revision_sha256"],
                "selected_excerpt_sha256": self.contract["story"]["source_selection"]["selected_sha256"],
                "unselected_source_sha256": self.source_a["source_revision_id"]},
            "stages": stage_log,
            "stage_artifacts": [{"stage": row["stage"], "artifact_path": row["artifact_path"],
                "sha256": row["artifact_sha256"],
                "content": (run_dir / state["stages"][row["stage"]]["artifact"]["path"])
                    .read_text(encoding="utf-8-sig")}
                for row in stage_log],
            "transport_receipts": [{key: row.get(key) for key in
                ("stage", "role_id", "request_id", "input_sha256", "request_sha256",
                 "raw_response_sha256", "output_sha256", "mode", "simulation_status")}
                for row in state["provider_requests"]],
            "role_request_summaries": requests,
            "recovery": {"interrupted_stage": "scene_cards", "status": recovery_plan["status"],
                "next_stage_candidate": recovery_plan["next_stage_candidate"],
                "old_plot_artifact_preserved": True, "matching_plot_not_rerun": True,
                "execution_failure_history_preserved": True},
            "review": {"initial_lens_finding_count": len(lens_index["findings"]),
                "independent_verifier_votes": verify["verdicts"][canon_id]["votes"],
                "threshold_2_of_3": verify["verdicts"][canon_id]["status"],
                "completeness_candidate": completeness["candidate_findings"][0]["finding_id"],
                "refined_sha256": sha(refined.encode("utf-8")),
                "rereview_candidate_sha256": rereview["candidate_sha256"],
                "rereview_status": rereview["status"],
                "rereview_request_count": len(self.rereview_messages)},
            "negative_guards": {"cross_project_prose_data": "EXCLUDED_FROM_PROSE_REQUEST",
                "forbidden_word": lint_result["findings"][0]["rule_id"],
                "false_canon": "CONFIRMED_THEN_REMOVED; CANON_UNCHANGED",
                "duplicate_finding": "LIVE_FINDING_IDENTITY_INVALID",
                "mismatched_verifier_ticket": "LIVE_VERIFIER_VOTES_INVALID",
                "enabled_nk_unavailable": "ENABLED_BUT_UNAVAILABLE",
                "mock_live_acceptance": "MOCK_RECEIPT_CANNOT_PROVE_LIVE"},
            "export": {"status": result["status"], "files": [
                {"path": path.relative_to(Path(result["deliverables"])).as_posix(),
                 "sha256": sha(path.read_bytes()), "size": path.stat().st_size,
                 "content": path.read_text(encoding="utf-8-sig")}
                for path in sorted(Path(result["deliverables"]).iterdir()) if path.is_file()]},
            "canon_before_sha256": sha(canon_before_export),
            "canon_after_sha256": sha((self.project / "90_canon/canon.md").read_bytes()),
        }
        evidence_output = os.environ.get("EARLY_CNW_E2E_EVIDENCE_OUTPUT")
        if evidence_output:
            destination = Path(evidence_output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_enabled_nk_unavailable_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-nk-unavailable-") as temp:
            contract = {"schema_version": "cnw_work_unit_v2",
                        "integrations": {"nk": "ENABLED", "critics": "DISABLED"}}
            env = dict(os.environ)
            env.pop("DEEPSEEK_API_KEY", None)
            with patch.object(runner, "ROOT", Path(temp)), patch.dict(os.environ, env, clear=True):
                with self.assertRaisesRegex(ContractError, "ENABLED_BUT_UNAVAILABLE"):
                    runner._assert_support_components_available(contract)


if __name__ == "__main__":
    unittest.main()
