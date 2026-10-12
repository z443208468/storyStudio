"""Atom-09 offline E2E across two source projects and one original project.

Every stage runs through the production dispatcher, recovery identity checks,
role material readers, review consumers, and export code. Only the transport
boundary returns deterministic simulated content.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools import cnw_export, cnw_recovery, cnw_runner
from tools.cnw_contract import ContractError
from tools.cnw_project import import_source, init_registered_project, standard_operation, write_contract_draft
from tools.project_paths import create_project, setup_data_home


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class ThreeProjectOfflineE2E(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="storystudio-atom09-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data_home = self.root / "isolated-data-home"
        self.user_pointer = self.root / "user-config" / "setup.json"
        setup_data_home(self.data_home, pointer_path=self.user_pointer)
        self.projects: dict[str, dict] = {}
        self.runs: dict[str, dict] = {}
        self.run_context: dict[str, dict] = {}
        self.requests: list[dict] = []
        self.transport_cache: dict[str, tuple[str, dict]] = {}
        self._counter = 0
        self._interrupt_once_for: str | None = None
        self._interrupted: set[str] = set()
        self._recovery_observations: list[dict] = []
        self._guard_lock = threading.Lock()

    def _project(self, project_id: str, title: str, names: tuple[str, str], setting: str) -> Path:
        registered = create_project(project_id=project_id, display_name=title, data_home=self.data_home)
        root = Path(registered["project_root"])
        init_registered_project(root)
        first, second = names
        texts = {
            "94_runtime/current_state.md": f"{first} and {second} are neighbors; their relationship is not familial.",
            "07_draft/manuscript_index.md": "No prior chapter has been accepted.",
            "04_chapter_design/arc_index.md": f"Arc 01 — a small choice in {setting} changes a neighborly relationship.",
            "04_chapter_design/arc_01.md": f"{first} decides whether to ask {second} for help in {setting}.",
            "04_chapter_design/arc_01_episode_details.md": f"Keep the action to one practical choice in {setting} and its immediate consequence.",
            "90_canon/canon.md": f"{first} and {second} are neighbors, not relatives. {setting} is fictional and ordinary.",
            "90_canon/character_bible.md": f"{first} asks direct questions. {second} gives brief, practical answers.",
            "90_canon/world_bible.md": f"A small fictional community gathers around {setting}.",
            "90_canon/timeline.md": "The scene occurs on an ordinary afternoon.",
            "90_canon/glossary.md": f"{setting}: the shared place where the neighbors meet.",
            "92_style_engine/style_guide.md": "Use close third person, concrete action, and distinct dialogue.",
            "92_style_engine/forbidden_patterns.md": "## Layer 1\n\n## Layer 2\n",
            "92_style_engine/character_voice_samples.md": f"## {first}\n'I would rather ask than guess.'\n\n## {second}\n'Try this.'\n",
        }
        for relative, text in texts.items():
            _write(root, relative, text)
        self.projects[project_id] = {"root": root, "names": names, "setting": setting,
                                     "project_instance_id": registered["project_instance_id"]}
        return root

    def _contract(self, root: Path, unit_id: str, intent: str, *, names: tuple[str, str], setting: str,
                  source: dict | None = None, selection: dict | None = None,
                  kind: str = "scene", first_episode: bool | None = None,
                  previous_episode_ref: str | None = None) -> dict:
        first, second = names
        duty = f"For this {setting} project, check whether the practical offer changes the neighbors' trust."
        draft = {
            "schema_version": "cnw_work_unit_draft_v2", "work_intent": intent,
            "unit_id": unit_id, "kind": kind, "language_locale": "en-US", "pov": first,
            "target_visible_chars": 180, "min_visible_chars": 100, "max_visible_chars": 320,
            "chapter_context": f"A practical choice near {setting} lets two neighbors speak plainly.",
            "role_in_story": "Adapt only the selected source moment into one playable scene." if source else
                             f"Continue the original project story in {setting}.",
            "reader_reward": "See a practical offer create a concrete next request.",
            "entry_state": "The issue is unsettled.", "exit_state": "The neighbors choose a next step.",
            "required_beats": [{"beat_id": "B01", "goal": f"{first} asks for help and answers the offer."}],
            "characters_in_scene": [first, second], "character_knowledge_boundary_ref": "90_canon/canon.md",
            "forbidden_future_revelations": ["Do not invent a family relationship or future secret."],
            "voice_sample_refs": [first, second],
            "review": {"fifth_lens": {"id": f"{unit_id.lower()}-reader-promise", "responsibility": duty}},
            "arc_ref": "04_chapter_design/arc_01.md",
            "integrations": {"nk": "DISABLED", "critics": "DISABLED"},
        }
        if source:
            draft.update(source_id=source["source_id"], source_revision_id=source["source_revision_id"],
                         source_manifest_revision_sha256=source["source_manifest_sha256"],
                         source_index_revision_sha256=source["source_index_sha256"])
        if selection:
            draft.update(selection)
        if first_episode is not None:
            draft["first_episode"] = first_episode
        if previous_episode_ref:
            draft["previous_episode_ref"] = previous_episode_ref
        path = root / "contracts" / f"{unit_id}.draft.json"
        path.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
        write_contract_draft(root, path)
        return json.loads((root / "contracts" / f"{unit_id}.json").read_text(encoding="utf-8"))

    def _sections(self, stage: str, first: str, second: str) -> str:
        from tools.cnw_roles import ROLE_REQUIRED_SECTIONS
        role_section = {"scene_cards": "cards", "writing_brief": "brief"}.get(stage, stage)
        blocks = []
        for heading in ROLE_REQUIRED_SECTIONS[role_section]:
            if heading == "## Key Scenes":
                body = f"- S1 {first} asks {second} for a practical repair near the project setting."
            elif heading == "## Required Story Beats":
                body = f"- B01 {first} asks, accepts one practical offer, and chooses a next step."
            elif heading == "## Scene-by-Scene Instructions":
                body = "One scene; 100–320 visible characters; preserve B01 and the project's Canon."
            elif heading == "## Voice References":
                body = f"{first}: ask directly. {second}: answer briefly and practically."
            else:
                body = "Synthetic project-specific constraints; preserve the assigned point of view."
            if stage == "scene_cards" and "B01" not in body:
                body = f"B01 — {first} makes the assigned choice visible.\n{body}"
            blocks.append(f"{heading}\n{body}")
        return "\n\n".join(blocks)

    def _transport(self, run_dir: Path, *, stage: str, role_id: str, messages: list[dict],
                   output_cap: int, extra: dict | None = None):
        state = cnw_runner.load_state(run_dir)
        fingerprint = _sha(json.dumps([str(run_dir.resolve()), stage, role_id, messages, output_cap, extra],
                                      ensure_ascii=False, sort_keys=True).encode("utf-8"))
        cached = self.transport_cache.get(fingerprint)
        if cached:
            cached_content, cached_receipt = cached
            self.assertEqual(cnw_runner._receipt_content(run_dir, cached_receipt), cached_content)
            return cached_content, cached_receipt
        project_root = run_dir.parent.parent
        contract = json.loads((project_root / state["contract_path"]).read_text(encoding="utf-8"))
        context = self.run_context[state["run_id"]]
        first, second = context["names"]
        setting = context["setting"]
        if stage in {"plot", "scene_cards", "writing_brief"}:
            content = self._sections(stage, first, second)
        elif stage == "prose":
            content = (f"{first} found the small problem near {setting}. ‘Could you help me with this?’ "
                       f"{first} asked. {second} offered a practical tool, and they solved it together. "
                       f"Then {first} claimed {second} was a sibling, though Canon says they are neighbors.")
        elif stage == "refine":
            wire = json.dumps(messages, ensure_ascii=False)
            if "OMITTED-READER-PAYOFF" not in wire:
                raise AssertionError("Refine did not consume the Completeness finding")
            content = (f"{first} found the small problem near {setting}. ‘Could you help me with this?’ "
                       f"{first} asked. {second} offered a practical tool. They solved it together, "
                       f"and {first} asked where to return it.")
        elif stage == "multi_lens_review":
            if role_id == "canon":
                claim = f"{first} claimed {second} was a sibling"
                content = json.dumps({"lens_id": role_id, "findings": [{
                    "finding_id": f"{state['run_id']}-CANON-01", "severity": "P1",
                    "issue": "The draft invents a family relationship that conflicts with project Canon.",
                    "evidence": claim, "recommendation": "Remove the invented family relationship."}]})
            else:
                content = json.dumps({"lens_id": role_id, "findings": []})
        elif stage == "adversarial_verify":
            finding_id = extra["finding_id"]
            verdict = "refuted" if role_id == "continuity_plausibility" else "not_refuted"
            content = json.dumps({"verifier_id": role_id, "votes": [{
                "finding_id": finding_id, "verdict": verdict,
                "reason": "Independent synthetic countercheck against the allowed evidence."}]})
        elif stage == "completeness_critic":
            content = json.dumps({"candidate_findings": [{
                "finding_id": "OMITTED-READER-PAYOFF", "lens_id": "story_specific",
                "category": "reader_reward", "issue": "The draft needs an observable next request.",
                "evidence": "The draft has no concrete next request.",
                "recommendation": "Add a small, observable next request.",
                "prompt_update": "Check that the practical offer leads to a concrete next request."}]})
        elif stage == "re_review":
            content = json.dumps({"lens_id": role_id, "findings": []})
        else:
            raise AssertionError(f"unexpected simulated transport call: {stage}/{role_id}")

        with self._guard_lock:
            self._counter += 1
            request_id = f"SIM-{self._counter:05d}-{stage}-{role_id}"
        request_raw = json.dumps({"messages": messages}, ensure_ascii=False, sort_keys=True).encode("utf-8")
        request_path = run_dir / "artifacts/provider" / f"{request_id}.request.json"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_bytes(request_raw)
        raw_raw = json.dumps({"choices": [{"message": {"content": content}}]},
                             ensure_ascii=False, sort_keys=True).encode("utf-8")
        raw_path = request_path.with_suffix(".raw.json")
        raw_path.write_bytes(raw_raw)
        receipt = {"request_id": request_id, "provider_request_id": request_id,
            "request_fingerprint": _sha(json.dumps([stage, role_id, messages], ensure_ascii=False,
                sort_keys=True).encode("utf-8")), "stage": stage, "role_id": role_id,
            "status": "SUCCEEDED", "mode": "MOCK_ONLY", "simulation_status": "SIMULATED",
            "fixture_only": True, "request_path": request_path.relative_to(run_dir).as_posix(),
            "request_sha256": _sha(request_raw),
            "input_sha256": _sha(json.dumps(messages, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")),
            "raw_response_path": raw_path.relative_to(run_dir).as_posix(),
            "raw_response_sha256": _sha(raw_raw), "output_sha256": _sha(content.encode("utf-8"))}
        with cnw_runner.locked_run(run_dir):
            current = cnw_runner.load_state(run_dir)
            current.setdefault("provider_requests", []).append(receipt)
            cnw_runner.save_state(run_dir, current)
        self.transport_cache[fingerprint] = (content, receipt)
        self.requests.append({"project_id": state["project_id"], "run_id": state["run_id"],
            "stage": stage, "role_id": role_id, "request_path": request_path,
            "request_sha256": receipt["request_sha256"], "input_sha256": receipt["input_sha256"],
            "messages": messages})
        if stage == self._interrupt_once_for and stage not in self._interrupted:
            self._interrupted.add(stage)
            raise RuntimeError("SYNTHETIC_ATOM09_INTERRUPTION_AFTER_SIMULATED_RECEIPT")
        return content, receipt

    def _run_chain(self, root: Path, contract: dict, run_id: str, *, interrupt_scene_cards: bool = False) -> dict:
        args = SimpleNamespace(mode="offline", unit=contract["unit"]["kind"], run_id=run_id,
            work_id=contract["unit"]["id"], contract=str(root / "contracts" / f"{contract['unit']['id']}.json"),
            project_root=str(root), create_only=True)
        created = cnw_runner.produce(args)
        run_dir = Path(created["path"])
        start_state = cnw_runner.load_state(run_dir)
        self.assertFalse(start_state["fixture_only"])
        contract_raw = (root / "contracts" / f"{contract['unit']['id']}.json").read_bytes()
        self.assertEqual(start_state["contract_sha256"], _sha(contract_raw))
        self.run_context[run_id] = self.projects[next(key for key, value in self.projects.items()
                                                       if value["root"] == root)]
        self._interrupt_once_for = "scene_cards" if interrupt_scene_cards else None
        stage_rows = []
        with patch.object(cnw_runner, "cnw_live_call", side_effect=self._transport):
            for stage in cnw_runner.CNW_STAGES:
                if interrupt_scene_cards and stage == "scene_cards":
                    plot_record = cnw_runner.load_state(run_dir)["stages"]["plot"]
                    plot_path = run_dir / plot_record["artifact"]["path"]
                    plot_before = _sha(plot_path.read_bytes())
                    reused = cnw_recovery.execute_checked(run_dir, "plot")
                    self.assertEqual(reused["status"], "STAGE_REUSED")
                    with self.assertRaisesRegex(RuntimeError, "SYNTHETIC_ATOM09_INTERRUPTION_AFTER_SIMULATED_RECEIPT"):
                        cnw_recovery.execute_checked(run_dir, stage)
                    failed = cnw_runner.load_state(run_dir)
                    self.assertEqual(failed["stages"][stage]["status"], "EXECUTION_INCOMPLETE")
                    self.assertEqual(_sha(plot_path.read_bytes()), plot_before)
                    recovery = cnw_recovery.plan_recovery(run_dir, root)
                    self.assertEqual(recovery["status"], "RECOVERY_BLOCKED_EXECUTION_HISTORY")
                    self.assertTrue(recovery["state_mutated"] is False)
                    pre_retry_request_count = len([row for row in self.requests
                        if row["run_id"] == run_id and row["stage"] == stage])
                    pre_retry_receipt_count = len(cnw_runner.load_state(run_dir)["provider_requests"])
                    cached_retry = cnw_recovery.execute_checked(run_dir, stage)
                    self.assertEqual(cached_retry["stage"], stage)
                    self.assertEqual(len([row for row in self.requests
                        if row["run_id"] == run_id and row["stage"] == stage]), pre_retry_request_count)
                    resumed = cnw_runner.load_state(run_dir)
                    self.assertEqual(resumed["stages"][stage]["status"], "STAGE_MATERIALIZED")
                    self.assertEqual(len(resumed["provider_requests"]), pre_retry_receipt_count)
                    self.assertEqual(_sha(plot_path.read_bytes()), plot_before)
                    self._recovery_observations.append({"run_id": run_id, "stage": stage,
                        "interruption": "AFTER_SIMULATED_RECEIPT_PERSISTED",
                        "provider_receipt_reused": True,
                        "provider_request_count_before_retry": pre_retry_receipt_count,
                        "provider_request_count_after_retry": len(resumed["provider_requests"]),
                        "predecessor_plot_sha256_preserved": _sha(plot_path.read_bytes())})
                result = cnw_recovery.execute_checked(run_dir, stage)
                current = cnw_runner.load_state(run_dir)
                record = current["stages"][stage]
                artifact = run_dir / record["artifact"]["path"]
                raw = artifact.read_bytes()
                self.assertTrue(raw)
                self.assertEqual(record["artifact"]["sha256"], _sha(raw))
                self.assertEqual(current["run_id"], run_id)
                self.assertEqual(current["contract_sha256"], start_state["contract_sha256"])
                stage_rows.append({"stage": stage, "result": result, "path": record["artifact"]["path"],
                    "sha256": _sha(raw), "execution_identity_sha256": record["execution_identity"]["sha256"],
                    "input_identity": record.get("execution_input_identity", {})})
        state = cnw_runner.load_state(run_dir)
        self.assertEqual(list(state["stages"]), list(cnw_runner.CNW_STAGES))
        self.assertTrue(state["provider_requests"])
        self.assertTrue(all(row.get("mode") == "MOCK_ONLY" and row.get("simulation_status") == "SIMULATED"
                            for row in state["provider_requests"]))
        initial = cnw_runner._read_stage_text(run_dir, state, "prose")
        lens = json.loads(cnw_runner._read_stage_text(run_dir, state, "multi_lens_review"))
        self.assertTrue(lens["findings"])
        verified = json.loads(cnw_runner._read_stage_text(run_dir, state, "adversarial_verify"))
        finding_id = next(row["finding_id"] for row in verified["findings"] if row["lens_id"] == "canon")
        votes = verified["verdicts"][finding_id]["votes"]
        self.assertEqual(sum(value == "not_refuted" for value in votes.values()), 2)
        completeness = json.loads(cnw_runner._read_stage_text(run_dir, state, "completeness_critic"))
        self.assertEqual(completeness["candidate_findings"][0]["finding_id"], "OMITTED-READER-PAYOFF")
        refined = cnw_runner._read_stage_text(run_dir, state, "refine")
        self.assertNotEqual(_sha(initial.encode("utf-8")), _sha(refined.encode("utf-8")))
        self.assertNotIn("was a sibling", refined)
        rereview = json.loads(cnw_runner._read_stage_text(run_dir, state, "re_review"))
        self.assertEqual(rereview["status"], "CLEAN")
        self.assertEqual(rereview["candidate_sha256"], _sha(refined.encode("utf-8")))
        run_requests = [row for row in self.requests if row["run_id"] == run_id]
        from tools.cnw_roles import AUTHOR_ROLE_READS
        expected_reads = {
            "plot": set(AUTHOR_ROLE_READS["plot"]),
            "scene_cards": set(AUTHOR_ROLE_READS["cards"]),
            "writing_brief": set(AUTHOR_ROLE_READS["brief"] + ("90_canon/canon.md",
                "90_canon/timeline.md", "90_canon/world_bible.md", "90_canon/glossary.md")),
            "prose": {"writing_brief", "voice_samples"},
        }
        role_ids = {"plot": "plot_agent", "scene_cards": "scene_card_agent",
                    "writing_brief": "brief_agent", "prose": "prose_agent_1"}
        for stage, role_id in role_ids.items():
            request = next(row for row in run_requests if row["stage"] == stage and row["role_id"] == role_id)
            user_payload = json.loads(request["messages"][1]["content"])
            materials = user_payload.get("materials", user_payload)
            self.assertEqual(set(materials), expected_reads[stage], f"unexpected {stage} role-read set")
        lens_requests = [row for row in run_requests if row["stage"] == "multi_lens_review"]
        self.assertEqual(len(lens_requests), 5)
        self.assertEqual(len({row["role_id"] for row in lens_requests}), 5)
        lens_request_hashes = {row["request_sha256"] for row in lens_requests}
        self.assertEqual(len(lens_request_hashes), 5)
        story_duty = contract["review"]["fifth_lens"]["responsibility"]
        fifth_lens_wire = json.dumps(next(row["messages"] for row in lens_requests
                                          if row["role_id"] == "story_specific"), ensure_ascii=False)
        self.assertIn(story_duty, fifth_lens_wire)
        verifier_requests = [row for row in run_requests if row["stage"] == "adversarial_verify"]
        self.assertEqual(len(verifier_requests), 3)
        self.assertEqual(len({row["role_id"] for row in verifier_requests}), 3)
        rereview_requests = [row for row in run_requests if row["stage"] == "re_review"]
        self.assertTrue(rereview_requests)
        self.assertTrue(all(refined in json.dumps(row["messages"], ensure_ascii=False)
                            for row in rereview_requests))
        self.assertFalse(state.get("support_hooks", {}).get("nk_pov"))
        self.assertFalse(any(row.get("role_id") in {"nk_pov", "critics"}
                             for row in state["provider_requests"]))
        exported = cnw_export.export_reading_package(run_dir, state, project_root=root)
        self.assertEqual(exported["status"], "EXPORT_READY")
        deliverables = Path(exported["deliverables"])
        exports = [{"path": item.relative_to(deliverables).as_posix(), "sha256": _sha(item.read_bytes()),
                    "size": item.stat().st_size} for item in sorted(deliverables.rglob("*")) if item.is_file()]
        self.assertTrue(exports)
        self.runs[run_id] = {"project_id": state["project_id"], "contract_sha256": state["contract_sha256"],
                             "run_dir": str(run_dir)}
        return {"root": root, "run_dir": run_dir, "state": state, "contract": contract,
            "stages": stage_rows, "export": exported, "exports": exports,
            "plot_messages": next(row["messages"] for row in self.requests
                if row["run_id"] == run_id and row["stage"] == "plot"),
            "initial_prose_sha256": _sha(initial.encode("utf-8")), "refined_sha256": _sha(refined.encode("utf-8"))}

    def _source_import(self, root: Path, file_name: str, raw: bytes) -> dict:
        source = self.root / file_name
        source.write_bytes(raw)
        before = _sha(raw)
        imported = import_source(input_file=source, project_root=root)
        self.assertEqual(imported["source_revision_id"], before)
        return imported

    def test_two_source_projects_and_source_free_original_run_real_11_stage_consumers(self):
        # The offline boundary is active for the entire production execution.
        def denied(*args, **kwargs):
            raise RuntimeError("ATOM09_NETWORK_OR_PROCESS_BLOCKED")
        real_popen = subprocess.Popen
        def guarded_popen(args, *pargs, **kwargs):
            command = args[0] if isinstance(args, (tuple, list)) and args else args
            executable = Path(str(command)).name.lower()
            if executable in {"whoami", "whoami.exe", "icacls", "icacls.exe"}:
                return real_popen(args, *pargs, **kwargs)
            raise RuntimeError("ATOM09_NETWORK_OR_PROCESS_BLOCKED")
        with patch.object(socket.socket, "connect", denied), \
             patch.object(socket.socket, "connect_ex", denied), \
             patch.object(socket, "create_connection", denied), \
             patch.object(subprocess, "Popen", guarded_popen), \
             patch.object(os, "system", denied):
            with self.assertRaisesRegex(RuntimeError, "ATOM09_NETWORK_OR_PROCESS_BLOCKED"):
                socket.create_connection(("203.0.113.1", 443), timeout=0.1)
            with self.assertRaisesRegex(RuntimeError, "ATOM09_NETWORK_OR_PROCESS_BLOCKED"):
                subprocess.Popen(["cmd.exe", "/c", "ver"])

            harbor = self._project("TEST_HARBOR", "Synthetic Harbor", ("Mira", "Keeper"), "harbor")
            harbor_a = self._source_import(harbor, "harbor-A.md", b"A_ONLY_CANARY: Mira keeps a private tide chart.\n")
            harbor_b = self._source_import(harbor, "harbor-B.md", (
                b"Before: Mira tests the public door.\n"
                b"Selected: Mira asks the keeper to tighten the loose hinge.\n"
                b"After: The harbor bell rings from the market.\n"))
            harbor_insert = self._contract(harbor, "HARBOR-INSERT", "INSERT_BETWEEN",
                names=("Mira", "Keeper"), setting="harbor", source=harbor_b,
                selection={"before_line": 1, "after_line": 3})
            harbor_adapt = self._contract(harbor, "HARBOR-ADAPT", "ADAPT_SOURCE",
                names=("Mira", "Keeper"), setting="harbor", source=harbor_b,
                selection={"start_line": 2, "end_line": 2})
            frozen_b_manifest = (harbor / harbor_b["source_manifest"]).read_bytes()
            harbor_c = self._source_import(harbor, "harbor-C.md", b"C_ONLY_CANARY: A gull lands on the west rail.\n")
            self.assertEqual((harbor / harbor_b["source_manifest"]).read_bytes(), frozen_b_manifest)
            self.assertEqual(harbor_insert["source"]["manifest_revision_sha256"], harbor_b["source_manifest_sha256"])
            self.assertEqual(harbor_adapt["source"]["source_revision_id"], harbor_b["source_revision_id"])
            insert = self._run_chain(harbor, harbor_insert, "HARBOR-INSERT-RUN", interrupt_scene_cards=True)
            adapt = self._run_chain(harbor, harbor_adapt, "HARBOR-ADAPT-RUN")
            self.assertNotIn("A_ONLY_CANARY", json.dumps(insert["plot_messages"], ensure_ascii=False))
            self.assertNotIn("C_ONLY_CANARY", json.dumps(insert["plot_messages"], ensure_ascii=False))
            self.assertNotIn("A_ONLY_CANARY", json.dumps(adapt["plot_messages"], ensure_ascii=False))
            self.assertNotIn("C_ONLY_CANARY", json.dumps(adapt["plot_messages"], ensure_ascii=False))
            self.assertIn(harbor_b["source_revision_id"], harbor_insert["source"]["source_revision_id"])
            self.assertEqual(harbor_a["source_revision_id"], _sha(b"A_ONLY_CANARY: Mira keeps a private tide chart.\n"))

            orchard = self._project("TEST_ORCHARD", "Synthetic Orchard", ("Lio", "Ona"), "orchard gate")
            orchard_a = self._source_import(orchard, "orchard-A.md", b"A_ONLY_ORCHARD_CANARY: Lio found a red leaf.\n")
            orchard_raw = b'{"chapters":[{"text":"Lio finds an unripe pear."},{"text":"Ona offers a basket by the orchard gate."}]}'
            orchard_b = self._source_import(orchard, "orchard-B.json", orchard_raw)
            orchard_adapt = self._contract(orchard, "ORCHARD-JSON-ADAPT", "ADAPT_SOURCE",
                names=("Lio", "Ona"), setting="orchard gate", source=orchard_b,
                selection={"json_pointer": "/chapters/1/text"})
            orchard_run = self._run_chain(orchard, orchard_adapt, "ORCHARD-JSON-RUN")
            orchard_wire = json.dumps(orchard_run["plot_messages"], ensure_ascii=False)
            self.assertIn("Ona offers a basket by the orchard gate.", orchard_wire)
            self.assertNotIn("A_ONLY_ORCHARD_CANARY", orchard_wire)
            orchard_manifest = json.loads((orchard / orchard_b["source_manifest"]).read_text(encoding="utf-8"))
            orchard_row = next(row for row in orchard_manifest["sources"]
                               if row["source_revision_id"] == orchard_b["source_revision_id"])
            self.assertEqual(_sha((orchard / orchard_row["stored_path"]).read_bytes()), orchard_b["source_revision_id"])
            self.assertEqual(orchard_b["source_revision_id"], orchard_adapt["source"]["source_revision_id"])
            self.assertEqual(orchard_a["source_revision_id"], _sha(b"A_ONLY_ORCHARD_CANARY: Lio found a red leaf.\n"))

            original = self._project("TEST_ORIGINAL", "Synthetic Original", ("Sana", "Keeper"), "coast")
            first_contract = self._contract(original, "ORIGINAL-EP001", "ORIGINAL_EPISODE",
                names=("Sana", "Keeper"), setting="coast", kind="episode", first_episode=True)
            self.assertFalse((original / "_INBOX" / "source_manifest.json").exists())
            ep1 = self._run_chain(original, first_contract, "ORIGINAL-EP001-RUN")
            self.assertEqual(first_contract["source"]["source_origin"], "ORIGINAL_PROJECT")
            self.assertNotIn("source_file", first_contract["story"])
            ep1_state = ep1["state"]
            final_text = cnw_runner._read_stage_text(ep1["run_dir"], ep1_state, "refine")
            episode_path = _write(original, "07_draft/episodes/EP001.md", final_text)
            carry_record = {"status": "SIMULATED_CARRY_FORWARD", "run_id": "ORIGINAL-EP001-RUN",
                "source_stage": "refine", "source_sha256": _sha(episode_path.read_bytes()),
                "promoted": False}
            carry_path = _write(original, "07_draft/episodes/EP001.simulated-carry-forward.json",
                                json.dumps(carry_record, sort_keys=True))
            second_contract = self._contract(original, "ORIGINAL-EP002", "ORIGINAL_EPISODE",
                names=("Sana", "Keeper"), setting="coast", kind="episode", first_episode=False,
                previous_episode_ref="07_draft/episodes/EP001.md")
            self.assertEqual(second_contract["story"]["previous_episode_sha256"], _sha(episode_path.read_bytes()))
            ep2 = self._run_chain(original, second_contract, "ORIGINAL-EP002-RUN")
            ep2_plot = json.dumps(ep2["plot_messages"], ensure_ascii=False)
            self.assertIn(final_text[:80], ep2_plot)
            self.assertEqual(carry_record["status"], json.loads(carry_path.read_text(encoding="utf-8"))["status"])
            self.assertEqual(carry_record["promoted"], json.loads(carry_path.read_text(encoding="utf-8"))["promoted"])
            self.assertEqual(_sha(orchard_raw), orchard_b["source_revision_id"])

            # Identical display run IDs remain isolated by the explicit project roots.
            same_run_dirs = []
            for project_root, selected_contract in ((harbor, harbor_insert), (orchard, orchard_adapt)):
                same_args = SimpleNamespace(mode="offline", unit=selected_contract["unit"]["kind"],
                    run_id="SAME-DISPLAY-RUN", work_id=selected_contract["unit"]["id"],
                    contract=str(project_root / "contracts" / f"{selected_contract['unit']['id']}.json"),
                    project_root=str(project_root), create_only=True)
                same_run_dirs.append(Path(cnw_runner.produce(same_args)["path"]))
            self.assertNotEqual(same_run_dirs[0], same_run_dirs[1])
            same_states = [cnw_runner.load_state(path) for path in same_run_dirs]
            self.assertNotEqual(same_states[0]["source_identity"]["project_instance_id"],
                                same_states[1]["source_identity"]["project_instance_id"])

        projects = [harbor, orchard, original]
        self.assertEqual(len({value["project_instance_id"] for value in self.projects.values()}), 3)
        self.assertEqual(set(self.runs), {"HARBOR-INSERT-RUN", "HARBOR-ADAPT-RUN", "ORCHARD-JSON-RUN",
                                         "ORIGINAL-EP001-RUN", "ORIGINAL-EP002-RUN"})
        evidence = {"schema_version": "atom09_three_project_e2e_v1", "execution": "SIMULATED_OFFLINE_ONLY",
            "data_home": str(self.data_home), "data_home_pointer": str(self.user_pointer),
            "project_roots": [str(path) for path in projects],
            "run_artifacts": [{"project_id": result["state"]["project_id"], "run_id": result["state"]["run_id"],
                "project_instance_id": result["contract"]["project_instance_id"],
                "contract_sha256": result["state"]["contract_sha256"],
                "source_revision_id": result["contract"].get("source", {}).get("source_revision_id"),
                "work_intent": result["contract"]["work_intent"],
                "stages": result["stages"], "export": result["exports"]}
                for result in (insert, adapt, orchard_run, ep1, ep2)],
            "mock_provider_receipts": [{key: value for key, value in request.items()
                if key not in {"messages", "request_path"}} for request in self.requests],
            "recovery_observations": self._recovery_observations,
            "outcomes": {"projects": 3, "runs": 5, "projects_with_distinct_instance_ids": True,
                "all_11_stage_order": [list(cnw_runner.CNW_STAGES)], "provider_call": "none",
                "simulated_receipts": True, "interruption_replayed_without_new_request": True,
                "live_quality": "NOT_VALIDATED"}}
        evidence_path = os.environ.get("ATOM09_E2E_EVIDENCE_OUTPUT")
        if evidence_path:
            destination = Path(evidence_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_workflow03_consumes_real_episode_and_review_without_promoting(self):
        root = self._project("TEST_REVISION", "Synthetic Revision Project", ("Sana", "Keeper"), "coast")
        contract = self._contract(root, "REVISION-EP001", "ORIGINAL_EPISODE",
            names=("Sana", "Keeper"), setting="coast", kind="episode", first_episode=True)
        chain = self._run_chain(root, contract, "REVISION-EP001-RUN")
        final_prose = cnw_runner._read_stage_text(chain["run_dir"], chain["state"], "refine")
        draft_path = _write(root, "07_draft/episodes/EP001.md", final_prose)
        rereview = cnw_runner._read_stage_text(chain["run_dir"], chain["state"], "re_review")
        _write(root, "08_review/cnw_ep001_re_review.json", rereview)
        _write(root, "08_review/beta_feedback.md",
            "# Ordinary beta feedback\nPlease make Sana's next request observable. A reader suggested changing the project's protected premise; that suggestion needs author review.\n")
        canon_path = root / "90_canon/canon.md"
        canon_before = canon_path.read_bytes()
        draft_before = draft_path.read_bytes()
        request_rows = []

        def simulated_maintenance_transport(run, *, stage, role_id, messages, output_cap, **_kwargs):
            self.assertEqual(stage, "project_revision_plan")
            self.assertEqual(role_id, "project_revision_plan")
            payload = json.loads(messages[1]["content"])
            project_sources = payload["project_sources"]
            self.assertIn("08_review/beta_feedback.md", project_sources)
            self.assertIn("08_review/cnw_ep001_re_review.json", project_sources)
            self.assertIn("07_draft/episodes/EP001.md", project_sources)
            self.assertEqual(project_sources["07_draft/episodes/EP001.md"]["sha256"], _sha(draft_before))
            self.assertIn("Please make Sana's next request observable", project_sources["08_review/beta_feedback.md"]["text"])
            self.assertIn("P0 REQUIRES AUTHOR DECISION", messages[0]["content"])
            value = {"documents": {"09_revision/revision_plan.md": (
                    "# Revision Plan\n\n## P0\nREQUIRES AUTHOR DECISION: consider the protected-premise suggestion; do not apply without user approval.\n\n"
                    "## P1\nNone identified from supplied evidence.\n\n"
                    "## P2\nEP001: make Sana's next request observable, based on ordinary beta_feedback.md; keep project Canon unchanged.\n\n"
                    "## P3\nNone identified from supplied evidence.\n")},
                "report_markdown": "# Workflow 03 simulated offline plan\nRead the actual ordinary beta feedback, CNW re-review, draft, and project Canon.",
                "assumptions": [], "unresolved_questions": ["The protected-premise suggestion requires author decision."],
                "next_action": "User reviews the plan; no revision or promotion is authorized."}
            content = json.dumps(value, ensure_ascii=False)
            request_path = run / "artifacts" / "workflow03.request.json"
            raw_path = run / "artifacts" / "workflow03.raw.json"
            request_path.parent.mkdir(parents=True, exist_ok=True)
            request_raw = json.dumps({"messages": messages, "output_cap": output_cap}, ensure_ascii=False,
                                     sort_keys=True).encode("utf-8")
            raw_raw = json.dumps({"choices": [{"message": {"content": content}}]},
                                 ensure_ascii=False, sort_keys=True).encode("utf-8")
            request_path.write_bytes(request_raw)
            raw_path.write_bytes(raw_raw)
            receipt = {"request_id": "SIM-WORKFLOW03-REQUEST", "provider_request_id": "SIM-WORKFLOW03-RECEIPT",
                "status": "SUCCEEDED", "mode": "MOCK_ONLY", "simulation_status": "SIMULATED",
                "request_path": request_path.relative_to(run).as_posix(), "request_sha256": _sha(request_raw),
                "input_sha256": _sha(json.dumps(messages, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")).encode("utf-8")),
                "raw_response_path": raw_path.relative_to(run).as_posix(), "raw_response_sha256": _sha(raw_raw),
                "output_sha256": _sha(content.encode("utf-8"))}
            state = cnw_runner.load_state(run)
            state.setdefault("provider_requests", []).append(receipt)
            cnw_runner.save_state(run, state)
            request_rows.append({"run_dir": str(run), "request_sha256": receipt["request_sha256"],
                "input_sha256": receipt["input_sha256"], "raw_response_sha256": receipt["raw_response_sha256"],
                "output_sha256": receipt["output_sha256"], "mode": receipt["mode"],
                "simulation_status": receipt["simulation_status"],
                "source_sha256": {name: row["sha256"] for name, row in project_sources.items()}})
            return content, receipt

        with patch.object(cnw_runner, "cnw_live_call", side_effect=simulated_maintenance_transport):
            result = standard_operation(root, "revision_plan")
        plan_path = root / "09_revision/revision_plan.md"
        self.assertEqual(result["status"], "STANDARD_OPERATION_RECORDED")
        self.assertFalse(result["revision_approved"])
        self.assertFalse(result["user_creative_accepted"])
        self.assertTrue(plan_path.is_file())
        plan_bytes = plan_path.read_bytes()
        self.assertIn(b"P0", plan_bytes)
        self.assertIn(b"P3", plan_bytes)
        self.assertNotIn(b"\\n", plan_bytes)
        self.assertIn("no revision or promotion", result["next_action"])
        self.assertEqual(draft_path.read_bytes(), draft_before)
        self.assertEqual(canon_path.read_bytes(), canon_before)
        self.assertTrue(request_rows and request_rows[0]["mode"] == "MOCK_ONLY")
        self.assertEqual(request_rows[0]["simulation_status"], "SIMULATED")
        self.assertEqual(_sha(plan_bytes), _sha(plan_path.read_bytes()))
        evidence_path = os.environ.get("ATOM09_WF03_EVIDENCE_OUTPUT")
        if evidence_path:
            evidence = {"schema_version": "atom09_workflow03_offline_evidence_v1",
                "execution": "SIMULATED_OFFLINE_ONLY", "project_id": "TEST_REVISION",
                "run_id": chain["state"]["run_id"], "contract_sha256": chain["state"]["contract_sha256"],
                "request": request_rows[0],
                "revision_plan": {"path": "09_revision/revision_plan.md", "sha256": _sha(plan_bytes),
                    "size": len(plan_bytes)},
                "protected_inputs": {"draft_sha256_before": _sha(draft_before),
                    "draft_sha256_after": _sha(draft_path.read_bytes()), "canon_sha256_before": _sha(canon_before),
                    "canon_sha256_after": _sha(canon_path.read_bytes())},
                "decision_boundary": {"revision_approved": result["revision_approved"],
                    "user_creative_accepted": result["user_creative_accepted"],
                    "provider_call": "SIMULATED_ONLY"}}
            destination = Path(evidence_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
