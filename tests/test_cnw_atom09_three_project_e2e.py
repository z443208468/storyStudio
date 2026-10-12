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
from tools.cnw_project import (canon_audit, handoff, import_source, init_registered_project,
                              semantic_import, standard_operation, write_contract_draft)
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
        self._interrupt_run_id: str | None = None
        self._interrupted: set[str] = set()
        self._recovery_observations: list[dict] = []
        self._guard_lock = threading.Lock()
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}).start()

        def denied(*args, **kwargs):
            raise RuntimeError("ATOM09_NETWORK_OR_PROCESS_BLOCKED")

        real_popen = subprocess.Popen
        def guarded_popen(args, *pargs, **kwargs):
            command = args[0] if isinstance(args, (tuple, list)) and args else args
            if Path(str(command)).name.lower() in {"whoami", "whoami.exe", "icacls", "icacls.exe"}:
                return real_popen(args, *pargs, **kwargs)
            return denied()

        patch.object(socket.socket, "connect", denied).start()
        patch.object(socket.socket, "connect_ex", denied).start()
        patch.object(socket, "create_connection", denied).start()
        patch.object(subprocess, "Popen", guarded_popen).start()
        patch.object(os, "system", denied).start()

    def _workflow_response(self, run_dir: Path, messages: list[dict], content: str,
                           *, stage: str, role_id: str) -> tuple[str, dict]:
        """Simulate only a model reply; consumers persist their own real results."""
        with self._guard_lock:
            self._counter += 1
            request_id = f"SIM-WORKFLOW-{self._counter:05d}"
        request_raw = json.dumps({"messages": messages}, ensure_ascii=False, sort_keys=True).encode("utf-8")
        response_raw = json.dumps({"choices": [{"message": {"content": content}}]},
                                  ensure_ascii=False, sort_keys=True).encode("utf-8")
        files = {}
        for kind, raw in (("request", request_raw), ("raw", response_raw)):
            relative = f"artifacts/provider/{request_id}.{kind}.json"
            path = run_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            files[kind] = relative
        receipt = {"request_id": request_id, "provider_request_id": request_id,
            "stage": stage, "role_id": role_id, "status": "SUCCEEDED", "mode": "MOCK_ONLY",
            "simulation_status": "SIMULATED", "fixture_only": True,
            "request_path": files["request"], "request_sha256": _sha(request_raw),
            "input_sha256": _sha(json.dumps(messages, ensure_ascii=False, sort_keys=True,
                                              separators=(",", ":")).encode("utf-8")),
            "raw_response_path": files["raw"], "raw_response_sha256": _sha(response_raw),
            "output_sha256": _sha(content.encode("utf-8"))}
        operation_binding = cnw_runner._operation_simulation_request_binding(run_dir,
            stage=stage, role_id=role_id, messages=messages)
        if operation_binding is not None:
            receipt.update(operation_binding)
        with cnw_runner.locked_run(run_dir):
            state = cnw_runner.load_state(run_dir)
            state.setdefault("provider_requests", []).append(receipt)
            cnw_runner.save_state(run_dir, state)
        self.requests.append({"stage": stage, "role_id": role_id, "messages": messages,
            "run_id": state["run_id"], "project_id": state.get("project_id"),
            "receipt": receipt, "request_utf8": request_raw.decode("utf-8"),
            "response_utf8": response_raw.decode("utf-8")})
        return content, receipt

    def _public_evidence(self, name: str, root: Path, outcomes: dict) -> None:
        destination = os.environ.get("ATOM09_PUBLIC_EVIDENCE_OUTPUT")
        if not destination:
            return
        path = Path(destination)
        evidence = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
            "execution": "SIMULATED_OFFLINE_ONLY", "checks": {}}
        files = []
        for file in sorted(root.rglob("*")):
            if file.is_file() and file.suffix in {".md", ".json"}:
                raw = file.read_bytes()
                files.append({"path": file.relative_to(root).as_posix(), "sha256": _sha(raw),
                              "artifact_utf8": raw.decode("utf-8")})
        evidence["checks"][name] = {"project_root": str(root), "outcomes": outcomes,
                                     "actual_files": files}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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

    def _sections(self, stage: str, first: str, second: str, setting: str) -> str:
        from tools.cnw_roles import ROLE_REQUIRED_SECTIONS
        role_section = {"scene_cards": "cards", "writing_brief": "brief"}.get(stage, stage)
        blocks = []
        for heading in ROLE_REQUIRED_SECTIONS[role_section]:
            if heading == "## Key Scenes":
                body = f"- S1 {first} asks {second} for a practical repair near {setting}."
            elif heading == "## Required Story Beats":
                body = f"- B01 {first} asks, accepts one practical offer, and chooses a next step."
            elif heading == "## Scene-by-Scene Instructions":
                body = f"One scene at {setting}; 100–320 visible characters; preserve B01 and the project's Canon."
            elif heading == "## Voice References":
                body = f"- {first}: ask directly.\n- {second}: answer briefly and practically."
            else:
                body = f"Synthetic project-specific constraints at {setting}; preserve the assigned point of view."
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
            payload = json.loads(messages[1]["content"])
            if stage in {"scene_cards", "writing_brief"}:
                self.assertIn(setting, payload["materials"]["06_plot/<work_id>_plot.md"])
            if stage == "writing_brief":
                self.assertIn(setting, payload["materials"]["05_scene_cards/<work_id>_scene_cards.md"])
            content = self._sections(stage, first, second, setting)
            if stage == "plot":
                preparation = payload["support"]["production_preparation"]["documents"]
                selected = preparation.get("selected_source_excerpt")
                if selected:
                    content += "\n\n## Selected source constraint\n" + selected
            else:
                upstream = payload["materials"]["06_plot/<work_id>_plot.md"]
                if "## Selected source constraint\n" in upstream:
                    content += "\n\n## Selected source constraint\n" + upstream.split("## Selected source constraint\n", 1)[1]
        elif stage == "prose":
            payload = json.loads(messages[1]["content"])
            self.assertIn(setting, payload["writing_brief"])
            self.assertIn(first, payload["voice_samples"])
            self.assertIn(second, payload["voice_samples"])
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
        if (stage == self._interrupt_once_for and stage not in self._interrupted
                and self._interrupt_run_id in {None, state["run_id"]}):
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
                    "sha256": _sha(raw), "artifact_utf8": raw.decode("utf-8"),
                    "execution_identity_sha256": record["execution_identity"]["sha256"],
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
                    "size": item.stat().st_size, "artifact_utf8": item.read_bytes().decode("utf-8")}
                   for item in sorted(deliverables.rglob("*")) if item.is_file()]
        self.assertTrue(exports)
        self.runs[run_id] = {"project_id": state["project_id"], "contract_sha256": state["contract_sha256"],
                             "run_dir": str(run_dir)}
        return {"root": root, "run_dir": run_dir, "state": state, "contract": contract,
            "stages": stage_rows, "export": exported, "exports": exports,
            "contract_utf8": (run_dir / "artifacts/contract.json").read_bytes().decode("utf-8"),
            "run_state_utf8": (run_dir / "run_state.json").read_bytes().decode("utf-8"),
            "provider_files": [{"path": relative, "sha256": _sha((run_dir / relative).read_bytes()),
                "artifact_utf8": (run_dir / relative).read_bytes().decode("utf-8")}
                for relative in sorted({receipt[key] for receipt in state["provider_requests"]
                    for key in ("request_path", "raw_response_path")})],
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
            insert_payload = json.loads(insert["plot_messages"][1]["content"])
            insert_sources = insert_payload["support"]["production_preparation"]
            insert_excerpt = json.loads(insert_sources["documents"]["selected_source_excerpt"])
            self.assertEqual(insert_excerpt, {"before_anchor": "Before: Mira tests the public door.\n",
                "after_anchor": "After: The harbor bell rings from the market.\n"})
            self.assertEqual(insert_sources["source_hashes"]["selected_source_excerpt"],
                _sha(insert_sources["documents"]["selected_source_excerpt"].encode("utf-8")))
            adapt_payload = json.loads(adapt["plot_messages"][1]["content"])
            adapt_sources = adapt_payload["support"]["production_preparation"]
            self.assertEqual(adapt_sources["documents"]["selected_source_excerpt"],
                "Selected: Mira asks the keeper to tighten the loose hinge.\n")
            self.assertEqual(adapt_sources["source_hashes"]["selected_source_excerpt"],
                harbor_adapt["story"]["source_selection"]["selected_sha256"])
            brief_request = next(row for row in self.requests if row["run_id"] == "HARBOR-ADAPT-RUN"
                                 and row["stage"] == "writing_brief")
            brief_materials = json.loads(brief_request["messages"][1]["content"])["materials"]
            self.assertIn("Selected: Mira asks the keeper to tighten the loose hinge.",
                          brief_materials["06_plot/<work_id>_plot.md"])
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
                "stages": result["stages"], "export": result["exports"],
                "contract_utf8": result["contract_utf8"], "run_state_utf8": result["run_state_utf8"],
                "provider_files": result["provider_files"]}
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
                "fixture_only": True,
                "request_path": request_path.relative_to(run).as_posix(), "request_sha256": _sha(request_raw),
                "input_sha256": _sha(json.dumps(messages, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")).encode("utf-8")),
                "raw_response_path": raw_path.relative_to(run).as_posix(), "raw_response_sha256": _sha(raw_raw),
                "output_sha256": _sha(content.encode("utf-8"))}
            receipt.update(cnw_runner._operation_simulation_request_binding(run,
                stage=stage, role_id=role_id, messages=messages))
            state = cnw_runner.load_state(run)
            state.setdefault("provider_requests", []).append(receipt)
            cnw_runner.save_state(run, state)
            request_rows.append({"run_dir": str(run), "request_sha256": receipt["request_sha256"],
                "input_sha256": receipt["input_sha256"], "raw_response_sha256": receipt["raw_response_sha256"],
                "output_sha256": receipt["output_sha256"], "mode": receipt["mode"],
                "simulation_status": receipt["simulation_status"],
                "source_sha256": {name: row["sha256"] for name, row in project_sources.items()}})
            return content, receipt

        with cnw_runner._isolated_operation_transport(self.temp, data_home=self.data_home,
                projects=[root], transport=simulated_maintenance_transport):
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
        # The ordinary Workflow03 approved branch is distinct from CNW Refine:
        # user-selected plan items -> real maintenance request -> separate copy.
        original = "07_draft/episodes/EP001.md"
        item = "EP001: make Sana's next request observable, based on ordinary beta_feedback.md; keep project Canon unchanged."
        decision = {"schema_version": "cnw_workflow03_user_approval_v1",
            "author_decision": "APPROVE_SELECTED_ITEMS",
            "project_instance_id": self.projects["TEST_REVISION"]["project_instance_id"],
            "plan_sha256": _sha(plan_bytes), "draft_sha256": {original: _sha(draft_before)},
            "approved_items": [{"chapter": original, "plan_excerpt": item}],
            "protected_sha256": {p.relative_to(root).as_posix(): _sha(p.read_bytes())
                for folder in ("01_theme", "02_logline", "90_canon") for p in (root / folder).rglob("*")
                if p.is_file() and p.suffix.lower() in {".md", ".txt", ".json"}}}
        decision_file = "00_meta/author_decisions/workflow03.json"
        _write(root, decision_file, json.dumps(decision, ensure_ascii=False, sort_keys=True))
        rejects = []
        with patch.object(cnw_runner, "cnw_live_call", side_effect=AssertionError("unapproved revision must not request a model")):
            with self.assertRaises(ContractError) as caught:
                standard_operation(root, "revision_apply", sources=(original,))
            self.assertEqual(caught.exception.code, "REVISION_USER_APPROVAL_REQUIRED")
            rejects.append(caught.exception.code)
            cases = [dict(decision, project_instance_id="different-project"),
                dict(decision, plan_sha256="0" * 64),
                dict(decision, draft_sha256={original: "0" * 64}),
                dict(decision, protected_sha256={}),
                dict(decision, author_decision="NOT_APPROVED"),
                dict(decision, approved_items=[{"chapter": original, "plan_excerpt": "An invented plan item is not approved."}]),
                dict(decision, approved_items=decision["approved_items"] * 2),
                dict(decision, approved_items=[{"chapter": original, "plan_excerpt":
                    "REQUIRES AUTHOR DECISION: consider the protected-premise suggestion; do not apply without user approval."}])]
            for index, invalid in enumerate(cases):
                invalid_file = f"00_meta/author_decisions/invalid-{index}.json"
                _write(root, invalid_file, json.dumps(invalid))
                with self.assertRaises(ContractError) as caught:
                    standard_operation(root, "revision_apply", sources=(original,), revision_approval=invalid_file)
                rejects.append(caught.exception.code)
        approval_sha = _sha((root / decision_file).read_bytes())
        destination = f"09_revision/approved/{approval_sha}/episodes/EP001.md"
        revised = final_prose + "\nSana pointed to the empty crate. 'Can you carry this with me tomorrow?'\n"
        apply_requests = []

        def approved_transport(run, *, stage, role_id, messages, output_cap, **kwargs):
            self.assertEqual(stage, "project_revision_apply")
            payload = json.loads(messages[1]["content"])
            bound = payload["selection"]["revision_approval"]
            self.assertEqual(bound["decision"], decision)
            self.assertEqual(bound["revision_destinations"], {original: destination})
            self.assertEqual(payload["project_sources"][original]["sha256"], _sha(draft_before))
            self.assertEqual(payload["project_sources"]["09_revision/revision_plan.md"]["sha256"], _sha(plan_bytes))
            self.assertEqual(payload["project_sources"][decision_file]["sha256"], approval_sha)
            self.assertIn("ONLY the listed approved", messages[0]["content"])
            self.assertIn("When the user approves specific items", messages[0]["content"])
            value = {"documents": {destination: revised}, "report_markdown": "# Workflow03 revision\nApplied only the approved P2 next-request item; kept the protected-premise P0 unimplemented.",
                "assumptions": [], "unresolved_questions": ["Protected-premise P0 still requires a separate author decision."],
                "next_action": "Author compares the separate revised copy; promotion has not been requested."}
            apply_requests.append(messages)
            return self._workflow_response(run, messages, json.dumps(value, ensure_ascii=False), stage=stage, role_id=role_id)

        # Interrupt an actual filesystem publication, not the execution function.
        replace = Path.replace
        def interrupted_replace(path, target):
            if str(path).endswith(".maintenance-tmp") and Path(target) == root / destination:
                raise OSError("SIMULATED_WORKFLOW03_PUBLICATION_INTERRUPTION")
            return replace(path, target)
        with cnw_runner._isolated_operation_transport(self.temp, data_home=self.data_home,
                projects=[root], transport=approved_transport), patch.object(Path, "replace", interrupted_replace):
            with self.assertRaisesRegex(OSError, "SIMULATED_WORKFLOW03_PUBLICATION_INTERRUPTION"):
                standard_operation(root, "revision_apply", sources=(original,), revision_approval=decision_file)
        self.assertTrue((root / "00_meta/maintenance_pending.json").is_file())
        self.assertFalse((root / destination).exists())
        self.assertEqual(draft_path.read_bytes(), draft_before)
        with cnw_runner._isolated_operation_transport(self.temp, data_home=self.data_home,
                projects=[root], transport=lambda *args, **kwargs: self.fail("completed model receipt must be reused")):
            applied = standard_operation(root, "revision_apply", sources=(original,), revision_approval=decision_file)
            repeat = standard_operation(root, "revision_apply", sources=(original,), revision_approval=decision_file)
        self.assertTrue(applied["recovered"])
        self.assertEqual(repeat["provider_call"], "reused")
        self.assertEqual(len(apply_requests), 1)
        self.assertTrue(applied["revision_approved"])
        self.assertFalse(applied["promoted"])
        self.assertFalse(applied["canon_modified"])
        self.assertFalse(applied["user_creative_accepted"])
        self.assertEqual((root / destination).read_bytes(), revised.encode("utf-8"))
        self.assertEqual(draft_path.read_bytes(), draft_before)
        self.assertEqual(canon_path.read_bytes(), canon_before)
        record = json.loads((root / applied["revision_record"]).read_text(encoding="utf-8"))
        self.assertEqual(record["chapters"][0]["original_sha256"], _sha(draft_before))
        self.assertEqual(record["chapters"][0]["revision_sha256"], _sha(revised.encode("utf-8")))
        self.assertEqual(record["chapters"][0]["approved_items"], [item])
        self.assertIn("Can you carry this", record["chapters"][0]["diff"])
        log = (root / "00_meta/ai_work_log.md").read_text(encoding="utf-8")
        self.assertEqual(log.count("Workflow revision_apply;"), 1)
        self.assertIn(destination, log)
        self._public_evidence("workflow03_user_approved_revision_and_recovery", root,
            {"unapproved": result, "approved": applied, "replay": repeat, "rejected_approvals": rejects,
             "approval_sha256": approval_sha, "record": record,
             "draft_original_sha256": _sha(draft_before), "canon_original_sha256": _sha(canon_before),
             "actual_apply_requests": apply_requests, "model_transport": "MOCK_ONLY / SIMULATED"})
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

    def test_workflow03_rejects_model_write_escalation_and_changed_approval_inputs(self):
        outcomes = []
        for index, fault in enumerate(("write_original", "write_canon", "write_other_copy", "draft", "plan", "protected_json", "approval")):
            with self.subTest(fault=fault):
                root = self._project(f"REVISION-GUARD-{index}", "Synthetic revision guards", ("Mira", "Keeper"), "harbor")
                original = "07_draft/episodes/EP001.md"
                _write(root, original, "Mira asked her neighbor to carry the crate.\n")
                _write(root, "90_canon/locked.json", json.dumps({"locked_fact": "The neighbors are not relatives."}))
                item = "EP001: clarify the next concrete request while preserving the neighborly relationship."
                _write(root, "09_revision/revision_plan.md", "# Revision Plan\n## P2\n" + item + "\n")
                decision_file = "00_meta/author_decisions/revision.json"
                decision = {"schema_version": "cnw_workflow03_user_approval_v1", "author_decision": "APPROVE_SELECTED_ITEMS",
                    "project_instance_id": self.projects[f"REVISION-GUARD-{index}"]["project_instance_id"],
                    "plan_sha256": _sha((root / "09_revision/revision_plan.md").read_bytes()),
                    "draft_sha256": {original: _sha((root / original).read_bytes())},
                    "approved_items": [{"chapter": original, "plan_excerpt": item}],
                    "protected_sha256": {p.relative_to(root).as_posix(): _sha(p.read_bytes())
                        for folder in ("01_theme", "02_logline", "90_canon") for p in (root / folder).rglob("*")
                        if p.is_file() and p.suffix.lower() in {".md", ".txt", ".json"}}}
                _write(root, decision_file, json.dumps(decision, sort_keys=True))
                protected = {name: (root / name).read_bytes() for name in (
                    original, "09_revision/revision_plan.md", "90_canon/canon.md", "90_canon/locked.json", decision_file)}
                changed = {"draft": original, "plan": "09_revision/revision_plan.md",
                    "protected_json": "90_canon/locked.json", "approval": decision_file}.get(fault)
                calls = []
                def malicious_transport(run, *, stage, role_id, messages, output_cap, **kwargs):
                    payload = json.loads(messages[1]["content"])
                    self.assertIn("90_canon/locked.json", payload["project_sources"])
                    destination = payload["selection"]["revision_approval"]["revision_destinations"][original]
                    if fault in {"write_original", "write_canon", "write_other_copy"}:
                        destination = {"write_original": original, "write_canon": "90_canon/canon.md",
                            "write_other_copy": "09_revision/approved/wrong/EP002.md"}[fault]
                    else:
                        (root / changed).write_bytes(protected[changed] + b"\nTOCTOU-CHANGE\n")
                    value = {"documents": {destination: "A changed candidate."}, "report_markdown": "MOCK invalid attempt",
                        "revision_approved": True, "provider_authorized": True, "assumptions": [],
                        "unresolved_questions": [], "next_action": "Attempt automatic promotion."}
                    calls.append(messages)
                    return self._workflow_response(run, messages, json.dumps(value), stage=stage, role_id=role_id)
                with cnw_runner._isolated_operation_transport(self.temp, data_home=self.data_home,
                        projects=[root], transport=malicious_transport):
                    with self.assertRaises(ContractError) as caught:
                        standard_operation(root, "revision_apply", sources=(original,), revision_approval=decision_file)
                expected = "REVISION_APPROVED_DESTINATIONS_REQUIRED" if fault.startswith("write_") else "MAINTENANCE_SOURCE_CHANGED"
                self.assertEqual(caught.exception.code, expected)
                self.assertEqual(len(calls), 1)
                self.assertFalse((root / "00_meta/maintenance_pending.json").exists())
                self.assertFalse((root / "08_review/revision_apply_report.md").exists())
                self.assertFalse(list((root / "09_revision/approved").rglob("*.md")))
                for name, raw in protected.items():
                    if fault not in {"write_original", "write_canon", "write_other_copy"} and name == changed:
                        (root / name).write_bytes(raw)  # restore only deliberately changed fictional input
                    self.assertEqual((root / name).read_bytes(), raw)
                outcomes.append({"fault": fault, "rejection": caught.exception.code, "actual_requests": calls})
                self._public_evidence(f"workflow03_guard_{fault}", root, outcomes[-1])
        # Run the real transport entrance with a present fictional key: author
        # approval alone must not reach the fee guard, slot or network boundary.
        def fee_access_forbidden(*args, **kwargs):
            raise AssertionError("no fee guard access")
        def provider_access_forbidden(*args, **kwargs):
            raise AssertionError("no Provider invocation")
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "SIMULATED_NOT_A_REAL_KEY"}), \
                patch.object(cnw_runner, "_p2_guard", new=fee_access_forbidden), \
                patch.object(cnw_runner, "_cnw_live_call_in_slot", new=provider_access_forbidden):
            with self.assertRaises(ContractError) as caught:
                standard_operation(root, "revision_apply", sources=(original,), revision_approval=decision_file)
        self.assertEqual(caught.exception.code, "LIVE_AUTHORIZATION_REQUIRED")
        self._public_evidence("workflow03_native_live_denied_before_fees", root,
            {"rejection": caught.exception.code, "fee_guard_calls": 0, "provider_calls": 0})

    def test_workflow03_approval_to_request_snapshot_race_is_rejected_without_provider(self):
        for index, selected in enumerate(("07_draft/episodes/EP001.md", "09_revision/revision_plan.md",
                "90_canon/locked.json", "00_meta/author_decisions/revision.json", "project_identity.json")):
            with self.subTest(changed_between_validation_and_snapshot=selected):
                root = self._project(f"REVISION-RACE-{index}", "Synthetic approval race", ("Mira", "Keeper"), "harbor")
                original = "07_draft/episodes/EP001.md"
                item = "EP001: clarify the concrete next request, keeping every Canon fact unchanged."
                _write(root, original, "Mira asked her neighbor to carry a crate tomorrow.\n")
                _write(root, "90_canon/locked.json", '{"relationship":"neighbors"}')
                _write(root, "09_revision/revision_plan.md", "# Revision Plan\n## P2\n" + item + "\n")
                approval_file = "00_meta/author_decisions/revision.json"
                decision = {"schema_version": "cnw_workflow03_user_approval_v1", "author_decision": "APPROVE_SELECTED_ITEMS",
                    "project_instance_id": self.projects[f"REVISION-RACE-{index}"]["project_instance_id"],
                    "plan_sha256": _sha((root / "09_revision/revision_plan.md").read_bytes()),
                    "draft_sha256": {original: _sha((root / original).read_bytes())},
                    "approved_items": [{"chapter": original, "plan_excerpt": item}],
                    "protected_sha256": {p.relative_to(root).as_posix(): _sha(p.read_bytes())
                        for folder in ("01_theme", "02_logline", "90_canon") for p in (root / folder).rglob("*")
                        if p.is_file() and p.suffix.lower() in {".md", ".txt", ".json"}}}
                _write(root, approval_file, json.dumps(decision, sort_keys=True))
                path = root / selected
                before = path.read_bytes()
                read_bytes = Path.read_bytes
                reads = []
                def concurrent_reader(current):
                    if current == path:
                        reads.append(str(current))
                        # The first read validates approval. The second is the
                        # actual request inventory read after that validation.
                        if len(reads) == 2:
                            current.write_bytes(before + b"\nEXTERNAL_EDIT_AFTER_APPROVAL\n")
                    return read_bytes(current)
                with cnw_runner._isolated_operation_transport(self.temp, data_home=self.data_home,
                        projects=[root], transport=lambda *args, **kwargs: self.fail("unapproved snapshot must not reach transport")), \
                        patch.object(Path, "read_bytes", new=concurrent_reader), \
                        patch.object(cnw_runner, "cnw_live_call", side_effect=AssertionError("unapproved snapshot must not reach transport")):
                    with self.assertRaises(ContractError) as caught:
                        standard_operation(root, "revision_apply", sources=(original,), revision_approval=approval_file)
                self.assertEqual(caught.exception.code, "REVISION_APPROVAL_SNAPSHOT_MISMATCH")
                self.assertEqual(len(reads), 2)
                self.assertFalse((root / "94_runtime/maintenance").exists())
                self.assertFalse((root / "09_revision/approved").exists())
                path.write_bytes(before)  # only the deliberate fictional edit
                self._public_evidence(f"workflow03_approval_snapshot_race_{index}", root,
                    {"changed_path": selected, "rejection": caught.exception.code, "provider_calls": 0,
                     "request_snapshot_file_reads": len(reads), "approved_original_sha256": _sha(before)})

    def test_workflow01_then02_retain_originals_and_classify_conflicting_update(self):
        from tools import cnw_import_workflow as workflow
        root = self._project("TEST_IMPORT_CHAIN", "Synthetic Source Updates", ("Mira", "Keeper"), "harbor")
        original = b"Mira owns a brass key. Keeper has a red lamp. They are neighbors.\n"
        first_import = self._source_import(root, "source-v1.md", original)
        manifest = json.loads((root / first_import["source_manifest"]).read_text(encoding="utf-8"))
        old_source = next(row["stored_path"] for row in manifest["sources"]
                          if row["source_revision_id"] == first_import["source_revision_id"])
        observed = []

        def initial_transport(run, *, stage, role_id, messages, **kwargs):
            self.assertEqual(stage, "project_import")
            payload = json.loads(messages[1]["content"])
            self.assertEqual(set(payload["original_sources"]), {old_source})
            self.assertEqual(payload["original_sources"][old_source]["text"], original.decode("utf-8"))
            rows = {name: [{"status": "INFERRED", "text": "A practical choice tests neighborly trust.",
                            "source_refs": [old_source]}] for name in workflow.DOCUMENTS}
            rows["90_canon/canon.md"] = [{"status": "CONFIRMED", "text": "Mira owns a brass key.",
                                           "source_refs": [old_source]}]
            rows["90_canon/character_bible.md"] = [{"status": "CONFIRMED", "text": "Mira and Keeper are neighbors.",
                                                     "source_refs": [old_source]}]
            value = {"documents": rows, "source_notes": {name: "Source bytes or provenance metadata."
                    for name in payload["original_sources"]}, "conflicts": [],
                    "next_action": "Review the source-backed project inputs."}
            observed.append(payload)
            return self._workflow_response(run, messages, json.dumps(value), stage=stage, role_id=role_id)

        with cnw_runner._isolated_operation_transport(self.temp, data_home=self.data_home,
                projects=[root], transport=initial_transport):
            initial_result = semantic_import(root)
        original_canon = (root / "90_canon/canon.md").read_bytes()
        initial_state = json.loads((root / workflow.STATE).read_text(encoding="utf-8"))
        second_import = self._source_import(root, "source-v2.md",
            b"Mira owns a silver key. Keeper now has a blue lamp.\n")
        next_manifest = json.loads((root / second_import["source_manifest"]).read_text(encoding="utf-8"))
        new_source = next(row["stored_path"] for row in next_manifest["sources"]
                          if row["source_revision_id"] == second_import["source_revision_id"])

        def update_transport(run, *, stage, role_id, messages, **kwargs):
            self.assertEqual(stage, "project_update")
            payload = json.loads(messages[1]["content"])
            self.assertEqual(set(payload["original_sources"]), {new_source})
            self.assertIn(new_source, payload["original_sources"])
            self.assertNotIn(old_source, payload["original_sources"])
            self.assertIn("Mira owns a brass key.", payload["existing_documents"]["90_canon/canon.md"])
            value = {"documents": {
                "90_canon/canon.md": [
                    {"status": "CONFIRMED", "text": "Keeper now has a blue lamp.", "source_refs": [new_source]},
                    {"status": "CONFIRMED", "text": "Mira owns a silver key.", "source_refs": [new_source]}],
                "03_project_design/update_observations.md": [
                    {"status": "INFERRED", "text": "The changed lamp may affect a later practical choice.", "source_refs": [new_source]},
                    {"status": "TODO_CONFIRM", "text": "Ask which key description should be authoritative.", "source_refs": [new_source]}]},
                "source_notes": {name: "New source version or provenance metadata."
                                 for name in payload["original_sources"]},
                "conflicts": [{"old_file": "90_canon/canon.md", "old_quote": "Mira owns a brass key.",
                    "new_file": "90_canon/canon.md", "new_entry": 1,
                    "reason": "The new source gives a different key material; retain both for author decision."}],
                "next_action": "Ask the author to resolve the key descriptions."}
            observed.append(payload)
            return self._workflow_response(run, messages, json.dumps(value), stage=stage, role_id=role_id)

        with cnw_runner._isolated_operation_transport(self.temp, data_home=self.data_home,
                projects=[root], transport=update_transport):
            update_result = semantic_import(root, incremental=True)
        current_canon = (root / "90_canon/canon.md").read_bytes()
        self.assertTrue(current_canon.startswith(original_canon))
        self.assertIn(b"Keeper now has a blue lamp.", current_canon)
        self.assertNotIn(b"Mira owns a silver key.", current_canon)
        questions = (root / "90_canon/unresolved_questions.md").read_text(encoding="utf-8")
        self.assertIn("Mira owns a silver key.", questions)
        self.assertIn("TODO_CONFIRM", questions)
        current_state = json.loads((root / workflow.STATE).read_text(encoding="utf-8"))
        for ident, claim in initial_state["claims"].items():
            self.assertEqual(current_state["claims"][ident], claim)
        self.assertEqual((root / old_source).read_bytes(), original)
        self.assertEqual(_sha((root / old_source).read_bytes()), first_import["source_revision_id"])
        self.assertIn("INFERRED", (root / "03_project_design/update_observations.md").read_text(encoding="utf-8"))
        self.assertEqual(len(observed), 2)
        self._public_evidence("workflow01_then02", root, {"initial_result": initial_result,
            "update_result": update_result, "old_source_sha256": _sha(original),
            "old_canon_prefix_retained": True, "retained_claims": list(initial_state["claims"]),
            "conflict_withheld_from_canon": True, "real_provider_calls": 0})

    def test_workflow01_internal_registry_cannot_become_a_confirmed_story_source(self):
        from tools import cnw_import_workflow as workflow
        root = self._project("REGISTRY-GUARD", "Synthetic source authority", ("Mira", "Keeper"), "harbor")
        imported = self._source_import(root, "actual-source.md", b"Mira and Keeper are neighbors.\n")
        canon_before = (root / "90_canon/canon.md").read_bytes()
        sent = []
        def metadata_as_fact_transport(run, *, stage, role_id, messages, **kwargs):
            payload = json.loads(messages[1]["content"])
            sources = payload["original_sources"]
            self.assertTrue(sources)
            self.assertFalse(any(name.startswith("_INBOX/revisions/") for name in sources))
            self.assertFalse(any(name in {"_INBOX/source_manifest.json", "_INBOX/source_index.json"} for name in sources))
            actual = next(iter(sources))
            rows = {name: [{"status": "INFERRED", "text": "A practical neighborly choice.", "source_refs": [actual]}]
                    for name in workflow.DOCUMENTS}
            rows["90_canon/canon.md"] = [{"status": "CONFIRMED", "text": "REGISTRY_ONLY_INVENTED_FACT",
                "source_refs": [imported["source_index"], "author:templates/CLAUDE.md"]}]
            rows["90_canon/character_bible.md"] = [{"status": "CONFIRMED", "text": "Mira and Keeper are neighbors.", "source_refs": [actual]}]
            value = {"source_notes": {name: "Actual supplied original." for name in sources}, "documents": rows,
                "conflicts": [], "next_action": "Review source-backed Canon."}
            sent.append(messages)
            return self._workflow_response(run, messages, json.dumps(value), stage=stage, role_id=role_id)
        registry_before = {p.relative_to(root).as_posix(): p.read_bytes()
                           for p in (root / "_INBOX/revisions").rglob("*") if p.is_file()}
        with cnw_runner._isolated_operation_transport(self.temp, data_home=self.data_home,
                projects=[root], transport=metadata_as_fact_transport):
            with self.assertRaises(ContractError) as caught:
                semantic_import(root)
        self.assertEqual(caught.exception.code, "IMPORT_CONFIRMED_FACT_SOURCE_REQUIRED")
        self.assertEqual((root / "90_canon/canon.md").read_bytes(), canon_before)
        for name, raw in registry_before.items():
            self.assertEqual((root / name).read_bytes(), raw)
        # Retained historical claims tied only to an internal registry are not
        # re-exported as authoritative Canon evidence; old files remain intact.
        fake = {"claims": {"OLD-METADATA": {"status": "CONFIRMED", "document": "90_canon/canon.md",
            "text": "REGISTRY_ONLY_INVENTED_FACT", "sources": {imported["source_index"]: "old-hash"},
            "source_kinds": {imported["source_index"]: "original"}}}}
        self.assertEqual(workflow._confirmed_canon_sources(fake, {"90_canon/canon.md":
            "REGISTRY_ONLY_INVENTED_FACT\n\nClassification: CONFIRMED\nSource: old metadata"}), {})
        alias = "confirmed_canon:90_canon/canon.md:OLD-METADATA"
        fake["claims"]["REPEATED-METADATA"] = {"status": "CONFIRMED", "document": "90_canon/canon.md",
            "text": "A repeated derived metadata fact.", "sources": {alias: _sha(b"REGISTRY_ONLY_INVENTED_FACT")},
            "source_kinds": {alias: "confirmed_canon"}}
        self.assertEqual(workflow._confirmed_canon_sources(fake, {"90_canon/canon.md":
            "REGISTRY_ONLY_INVENTED_FACT\n\nClassification: CONFIRMED\nSource: old metadata\n\n"
            "A repeated derived metadata fact.\n\nClassification: CONFIRMED\nSource: " + alias}), {})
        self._public_evidence("workflow01_registry_authority_rejected", root,
            {"rejection": caught.exception.code, "request": sent[0], "canon_sha256_preserved": _sha(canon_before),
             "registry_sha256_preserved": {name: _sha(raw) for name, raw in registry_before.items()},
             "old_metadata_claim_not_retrusted": True})

    def test_canon_audit_handoff_then_revision_plan_consume_actual_outputs(self):
        from tools import cnw_maintenance as maintenance
        root = self._project("TEST_AUDIT_HANDOFF", "Synthetic Audit Handoff", ("Sana", "Keeper"), "coast")
        contract = self._contract(root, "AUDIT-EP001", "ORIGINAL_EPISODE", names=("Sana", "Keeper"),
                                  setting="coast", kind="episode", first_episode=True)
        chain = self._run_chain(root, contract, "AUDIT-EP001-RUN")
        unapproved_prose = cnw_runner._read_stage_text(chain["run_dir"], chain["state"], "prose")
        draft = _write(root, "07_draft/episodes/ep001.md", unapproved_prose)
        _write(root, "07_draft/manuscript_index.md", "ep001 is an unapproved simulated candidate, not published.")
        canon_before = (root / "90_canon/canon.md").read_bytes()
        requests = []

        def maintenance_transport(run, *, stage, role_id, messages, **kwargs):
            payload = json.loads(messages[1]["content"])
            sources = payload["project_sources"]
            requests.append({"stage": stage, "sources": sources})
            if stage == "project_audit":
                self.assertEqual(sources["07_draft/episodes/ep001.md"]["sha256"], _sha(draft.read_bytes()))
                self.assertIn("was a sibling", sources["07_draft/episodes/ep001.md"]["text"])
                value = {"report_markdown": "# Canon Audit\nHARD CONFLICT: ep001 invents a sibling relationship; Canon says neighbors. Ask the author; do not change Canon.",
                    "action_items": ["Resolve the candidate sibling claim against the source-backed neighbor relationship."]}
            elif stage == "project_handoff":
                audit = root / "08_review/continuity_audit.md"
                self.assertEqual(sources["08_review/continuity_audit.md"]["sha256"], _sha(audit.read_bytes()))
                self.assertIn("HARD CONFLICT", sources["08_review/continuity_audit.md"]["text"])
                value = {"brief_markdown": "\n\n".join("## " + section +
                    "\nThe unapproved ep001 candidate conflicts with Canon; review the actual audit and preserve the neighbor relationship."
                    for section in (*maintenance.HANDOFF_SECTIONS, "Pipeline Context Pack"))}
            elif stage == "project_revision_plan":
                brief = root / "93_exports/handoff_brief.md"
                self.assertEqual(sources["93_exports/handoff_brief.md"]["sha256"], _sha(brief.read_bytes()))
                self.assertIn("unapproved ep001", sources["93_exports/handoff_brief.md"]["text"])
                value = {"documents": {"09_revision/revision_plan.md": "# Revision Plan\n## P0\nNone.\n## P1\nResolve the ep001 relationship conflict using the audit and handoff; keep Canon unchanged.\n## P2\nNone.\n## P3\nNone.\n"},
                    "report_markdown": "# Workflow 03\nConsumed the actual audit, handoff, candidate, and Canon.",
                    "assumptions": [], "unresolved_questions": ["The author has not approved a revision."],
                    "next_action": "Author reviews the plan; no manuscript or Canon change is approved."}
            else:
                raise AssertionError(stage)
            return self._workflow_response(run, messages, json.dumps(value), stage=stage, role_id=role_id)

        with cnw_runner._isolated_operation_transport(self.temp, data_home=self.data_home,
                projects=[root], transport=maintenance_transport):
            audit_result = canon_audit(root)
            handoff_result = handoff(root, pipeline=True)
            plan_result = standard_operation(root, "revision_plan", sources=("93_exports/handoff_brief.md",))
        self.assertEqual((root / "90_canon/canon.md").read_bytes(), canon_before)
        self.assertEqual(draft.read_text(encoding="utf-8"), unapproved_prose)
        self.assertEqual([row["stage"] for row in requests],
                         ["project_audit", "project_handoff", "project_revision_plan"])
        self.assertFalse(plan_result["revision_approved"])
        self.assertTrue((root / "09_revision/revision_plan.md").stat().st_size)
        self._public_evidence("canon_audit_handoff_revision_plan", root, {"audit": audit_result,
            "handoff": handoff_result, "revision_plan": plan_result, "canon_sha256_preserved": _sha(canon_before),
            "draft_sha256_preserved": _sha(draft.read_bytes()), "real_provider_calls": 0})

    def test_five_original_episodes_run_real_sprint_with_resume_batch_gate_arc_and_handoff(self):
        from tools import cnw_sprint_live as sprint
        from tools import cnw_maintenance as maintenance
        root = self._project("TEST_FIVE_ORIGINAL", "Synthetic Five-Episode Sprint", ("Sana", "Keeper"), "coast")
        _write(root, "04_chapter_design/arc_01.md", "# Arc 01\n## Range\nep001 – ep005\n## Purpose\nFive practical requests across a fictional coast.\n")
        _write(root, "00_meta/manuscript_review_rubric.md", "Review concrete choices, neighborly continuity and the next request. Canon conflicts require revision.")
        _write(root, "00_meta/episode_production_manual.md", "Use the fixed eleven CNW stages; candidates require user review before promotion.")
        self._contract(root, "ep001", "ORIGINAL_EPISODE", names=("Sana", "Keeper"),
                       setting="coast pier 1", kind="episode", first_episode=True)
        seed = json.loads((root / "contracts/ep001.draft.json").read_text(encoding="utf-8"))
        episodes = []
        sprint_id = "FIVE-ORIGINAL"
        for index in range(1, 6):
            ident = f"ep{index:03d}"
            draft = dict(seed, unit_id=ident, first_episode=index == 1,
                         chapter_context=f"A distinct practical choice at coast pier {index}.")
            draft_path = _write(root, f"contracts/{ident}.draft.json", json.dumps(draft))
            row = {"episode_id": ident, "contract_draft": draft_path.relative_to(root).as_posix()}
            if index > 1:
                row["previous_episode_id"] = f"ep{index-1:03d}"
            episodes.append(row)
            self.run_context[f"{sprint_id}-ep{index:02d}"] = dict(self.projects["TEST_FIVE_ORIGINAL"],
                                                                  setting=f"coast pier {index}")
        plan_path = _write(root, "sprint_plan.json", json.dumps({"episodes": episodes}))
        canon_before = (root / "90_canon/canon.md").read_bytes()
        response_cache = {}
        gate_case = "pass"

        def transport(run, *, stage, role_id, messages, output_cap, extra=None):
            if stage in cnw_runner.CNW_STAGES:
                if run.name.startswith("SHORT-SPRINT-") and stage == "prose":
                    return self._workflow_response(run, messages, "Short.", stage=stage, role_id=role_id)
                if run.name == f"{sprint_id}-ep05" and stage in {"prose", "multi_lens_review", "completeness_critic"}:
                    if stage == "prose":
                        self.assertIn("coast pier 5", json.loads(messages[1]["content"])["writing_brief"])
                        value = "Sana found the small problem at coast pier 5. She asked Keeper for a practical tool. The two neighbors solved it together, and Sana asked where to return the tool."
                    elif stage == "multi_lens_review":
                        value = json.dumps({"lens_id": role_id, "findings": []})
                    else:
                        value = '{"candidate_findings":[]}'
                    return self._workflow_response(run, messages, value, stage=stage, role_id=role_id)
                return self._transport(run, stage=stage, role_id=role_id, messages=messages,
                                       output_cap=output_cap, extra=extra)
            key = _sha(json.dumps([str(run), stage, role_id, messages, extra, gate_case], sort_keys=True).encode())
            if key in response_cache:
                content, receipt = response_cache[key]
                self.assertEqual(cnw_runner._receipt_content(run, receipt), content)
                return content, receipt
            if role_id == "batch_review":
                payload = json.loads(messages[1]["content"])
                self.assertEqual([row["episode_id"] for row in payload["episodes"]], [row["episode_id"] for row in episodes])
                self.assertEqual(payload["criteria"], {"size": 5, "min_score": 75, "max_p0_findings": 0, "max_p1_findings": 2})
                for row in payload["episodes"]:
                    self.assertEqual(row["sha256"], _sha(row["prose"].encode()))
                first = payload["episodes"][0]
                severity = "P0" if gate_case == "p0" else "P1"
                count = 3 if gate_case == "p1_count" else 1
                value = {"episode_scores": [{"episode_id": row["episode_id"], "score": 74 if gate_case == "score" else 80}
                                            for row in episodes],
                    "lens_scores": [{"lens_id": lens, "score": 80} for lens in cnw_runner.LENS_IDS],
                    "findings": [{"finding_id": f"BATCH-{number}", "severity": severity,
                        "episode_id": "ep001", "evidence": first["prose"][:45],
                        "issue": "Recheck the continuity of a practical request.", "recommendation": "Review the next request."}
                        for number in range(count)], "arc_advance_ready": True,
                    "completeness_notes": "No missing cross-chapter outcome.", "carry_forward": ["Review the practical request."],
                    "project_rubric_status": "revise" if gate_case == "canon" else "pass",
                    "stop_reasons": ["A project Canon conflict requires an author decision."] if gate_case == "canon" else []}
            elif role_id in cnw_runner.VERIFIER_IDS:
                value = {"verifier_id": role_id, "votes": [{"finding_id": extra["finding_id"],
                    "verdict": "refuted" if role_id == "continuity_plausibility" else "not_refuted"}]}
            elif role_id == "batch_completeness":
                value = {"candidate_findings": []}
            elif role_id == "project_arc_review":
                sources = json.loads(messages[1]["content"])["project_sources"]
                candidate_paths = [name for name in sources if "/candidates/ep" in name]
                self.assertEqual(len(candidate_paths), 5)
                for name in candidate_paths:
                    self.assertEqual(sources[name]["sha256"], _sha((root / name).read_bytes()))
                value = {"status": "pass", "review_markdown": "\n\n".join("## " + section +
                    "\nThe five actual candidates keep the protected neighbor relationship and contain distinct practical choices."
                    for section in maintenance.ARC_SECTIONS) + "\nStatus: pass\n"}
            elif role_id == "handoff":
                payload = json.loads(messages[1]["content"])
                self.assertIn("Review the practical request.", payload["batch_review"]["carry_forward"])
                value = "\n\n".join("## " + section + "\nReview the practical request; all drafts are candidates and no next Sprint is started."
                    for section in ("Project pitch", "Creative goal", "Protected core", "Draft state", "Canon warnings",
                                    "Open questions", "Next best action", "File index", "Pipeline-Ready Context Pack"))
            else:
                raise AssertionError(f"unexpected Sprint model call {stage}/{role_id}")
            content = value if isinstance(value, str) else json.dumps(value)
            response_cache[key] = self._workflow_response(run, messages, content, stage=stage, role_id=role_id)
            return response_cache[key]

        self._interrupt_once_for = "scene_cards"
        self._interrupt_run_id = f"{sprint_id}-ep03"
        actual_model_boundary = cnw_runner.cnw_live_call
        def split_transport(run, **kwargs):
            if cnw_runner._operation_owner(run, cnw_runner.load_state(run)) is not None:
                return actual_model_boundary(run, **kwargs)
            return transport(run, **kwargs)
        with cnw_runner._isolated_operation_transport(self.temp, data_home=self.data_home,
                projects=[root], transport=transport), patch.object(cnw_runner, "cnw_live_call", new=split_transport):
            paused = sprint.run_generic_sprint(root, sprint_id, plan_path)
            self.assertEqual(paused["status"], "EXECUTION_INCOMPLETE")
            self.assertEqual(paused["completed_episodes"], 2, paused)
            self.assertFalse((root / "runs" / f"{sprint_id}-ep04").exists())
            earlier = {ident: (root / f"sprints/{sprint_id}/candidates/{ident}.md").read_bytes()
                       for ident in ("ep001", "ep002")}
            prior_requests = {run_id: len(cnw_runner.load_state(root / "runs" / run_id)["provider_requests"])
                              for run_id in (f"{sprint_id}-ep01", f"{sprint_id}-ep02")}
            completed = sprint.run_generic_sprint(root, sprint_id, plan_path)
            self.assertEqual(completed["status"], "PASS")
            self.assertEqual(completed["arc_review"]["status"], "ARC_REVIEW_RECORDED")
            self.assertEqual(completed["provider_call"], "SIMULATED_ONLY")
            self.assertFalse(completed["manuscript_promoted"])
            request_count = len(self.requests)
            repeated = sprint.run_generic_sprint(root, sprint_id, plan_path)
            self.assertTrue(repeated["reused"])
            self.assertEqual(repeated["provider_call"], "none")
            self.assertEqual(len(self.requests), request_count)
            saved_batch = root / f"sprints/{sprint_id}/batch_review.md"
            batch_before = saved_batch.read_bytes()
            saved_batch.write_bytes(batch_before + b"tampered")
            with self.assertRaisesRegex(ContractError, "SPRINT_SNAPSHOT_CHANGED"):
                sprint.run_generic_sprint(root, sprint_id, plan_path)
            self.assertEqual(len(self.requests), request_count)
            saved_batch.write_bytes(batch_before)
            for ident, raw in earlier.items():
                self.assertEqual((root / f"sprints/{sprint_id}/candidates/{ident}.md").read_bytes(), raw)
            for run_id, count in prior_requests.items():
                self.assertEqual(len(cnw_runner.load_state(root / "runs" / run_id)["provider_requests"]), count)

            out = root / "sprints" / sprint_id
            candidates = [json.loads((out / f"candidate_metadata/{row['episode_id']}.json").read_text(encoding="utf-8"))
                          for row in episodes]
            contracts = [(out / f"contracts/{row['episode_id']}.json",
                          json.loads((out / f"contracts/{row['episode_id']}.json").read_text(encoding="utf-8")))
                         for row in episodes]
            for index, (path, contract) in enumerate(contracts, 1):
                self.assertNotIn("source_file", contract["story"])
                run = root / "runs" / f"{sprint_id}-ep{index:02d}"
                state = cnw_runner.load_state(run)
                self.assertEqual(sum(row["status"] == "STAGE_MATERIALIZED" for row in state["stages"].values()), 11)
                self.assertTrue(candidates[index-1]["exports"])
                if index > 1:
                    previous = candidates[index-2]
                    self.assertEqual(contract["story"]["previous_episode_sha256"], previous["sha256"])
                    plot = next(row for row in self.requests if row.get("run_id") == f"{sprint_id}-ep{index:02d}"
                                and row["stage"] == "plot")
                    self.assertIn(previous["prose"], json.dumps(plot["messages"], ensure_ascii=False))
                    lens = next(row for row in self.requests if row.get("run_id") == f"{sprint_id}-ep{index:02d}"
                                and row["stage"] == "multi_lens_review" and row["role_id"] == "story_specific")
                    self.assertIn("concrete next request", json.dumps(lens["messages"], ensure_ascii=False))
                with self.assertRaises(ContractError):
                    cnw_runner.verify_live(SimpleNamespace(run_id=run.name, project_root=str(root)))
            gate_results = {}
            for gate_case in ("score", "p0", "p1_count", "canon"):
                gate_out = root / "sprints" / f"GATE-{gate_case}"
                gate_out.mkdir(parents=True)
                old_handoff = (root / "93_exports/handoff_brief.md").read_bytes()
                cnw_runner.save_state(gate_out, {"run_id": gate_out.name, "mode": "offline", "provider_requests": [],
                    "max_in_flight": 5, "handoff_previous_sha256": _sha(old_handoff)})
                for candidate in candidates:
                    sprint._write_once(gate_out, f"candidates/{candidate['episode_id']}.md", candidate["prose"])
                rejected = sprint._review_candidates(root, gate_out, contracts, sprint._criteria(),
                    sprint._context(root), candidates, publish=False)
                self.assertEqual(rejected["status"], "REVISION_REQUIRED")
                self.assertFalse(rejected["next_sprint_started"])
                gate_results[gate_case] = rejected
            self.run_context["SHORT-SPRINT-ep01"] = dict(self.projects["TEST_FIVE_ORIGINAL"], setting="coast pier 1")
            short = sprint.run_generic_sprint(root, "SHORT-SPRINT", plan_path)
            self.assertEqual(short["status"], "EXECUTION_INCOMPLETE")
            self.assertEqual(short["failed_stage"], "prose")
            self.assertEqual(short["failure_code"], "PROSE_UNDERPRODUCED")
            self.assertFalse((root / "runs/SHORT-SPRINT-ep02").exists())
            gate_results["underproduced_episode_pauses_before_next_run"] = short
            from tools.cnw_arc import arc_context
            with self.assertRaisesRegex(ContractError, "ARC_CANDIDATE_IDENTITY_INVALID"):
                arc_context(root, "04_chapter_design/arc_01.md", candidate_drafts={"ep001": {
                    "path": "90_canon/canon.md", "sha256": _sha(canon_before)}})
            with self.assertRaisesRegex(ContractError, "ARC_CANDIDATE_HASH_MISMATCH"):
                arc_context(root, "04_chapter_design/arc_01.md", candidate_drafts={"ep001": {
                    "path": f"sprints/{sprint_id}/candidates/ep001.md", "sha256": "0" * 64}})
        self.assertEqual((root / "90_canon/canon.md").read_bytes(), canon_before)
        self.assertFalse(any((root / f"07_draft/episodes/{row['episode_id']}.md").exists() for row in episodes))
        self._public_evidence("five_original_sprint", root, {"paused": paused, "completed": completed,
            "negative_batch_gates": gate_results, "canon_sha256_preserved": _sha(canon_before),
            "real_provider_calls": 0, "manuscripts_promoted": False})

    def test_offline_transport_refuses_before_provider_or_ledger_access(self):
        run = self.root / "offline-run"
        run.mkdir()
        cnw_runner.save_state(run, {"run_id": run.name, "mode": "offline", "provider_requests": []})
        _write(run, "artifacts/contract.json", '{"schema_version":"cnw_work_unit_v2"}')
        with patch.object(cnw_runner, "_p2_guard", side_effect=AssertionError("ledger accessed")) as guard:
            with self.assertRaisesRegex(ContractError, "OFFLINE_PROVIDER_FORBIDDEN"):
                cnw_runner.cnw_live_call(run, stage="plot", role_id="plot_agent", messages=[], output_cap=100)
        guard.assert_not_called()


if __name__ == "__main__":
    unittest.main()
