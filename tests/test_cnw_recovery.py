"""Controlled offline execution of ordinary stages; no production API calls."""
import copy
from functools import wraps
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools import cnw_runner as r, cnw_roles as roles, cnw_recovery as recovery
from tools.cnw_contract import ContractError


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".cnw-recovery-", dir=r.ROOT / "workspace")
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.run = self.project / "runs/MOCK-RECOVERY"
        self.run.mkdir(parents=True)
        base = json.loads((r.ROOT / "workspace/cangqi/contracts/CQ-J19-INSERT-01.work_unit_contract.json").read_text(encoding="utf-8"))
        base["project_id"] = "FICT_RECOVERY_OFFLINE"
        base["unit"].update(id="ep001", kind="scene", pov="甲", min_visible_chars=30, target_visible_chars=60, max_visible_chars=200)
        base["story"].update(source_file="source.md", first_episode=True, arc_ref="04_chapter_design/arc_01.md",
            before_anchor={"source_line": 1}, after_anchor={"source_line": 2}, characters_in_scene=["甲"],
            required_beats=[{"beat_id": "B01", "budget_visible_chars": 60, "goal": "借伞"}],
            role_in_story="MOCK daily event", reader_reward="MOCK character", entry_state="MOCK entry", exit_state="MOCK exit")
        base["source"] = {"identity_type": "imported_project", "source_root": ".", "manifest_file": "manifest.json"}
        self.contract = base
        documents = {
            "source.md": "甲看见雨。\n乙借出伞。\n", "manifest.json": "{}",
            "contracts/unit.json": json.dumps(base, ensure_ascii=False),
            "runs/MOCK-RECOVERY/artifacts/contract.json": json.dumps(base, ensure_ascii=False),
            "04_chapter_design/arc_01.md": "MOCK fixed arc",
            "04_chapter_design/arc_01_episode_details.md": "MOCK first episode",
            "94_runtime/current_state.md": "MOCK current state",
            "07_draft/manuscript_index.md": "MOCK no previous episode",
            "90_canon/canon.md": "MOCK protected core",
            "90_canon/character_bible.md": "MOCK characters",
            "90_canon/glossary.md": "MOCK glossary",
            "90_canon/timeline.md": "MOCK timeline",
            "90_canon/world_bible.md": "MOCK world",
            "92_style_engine/style_guide.md": "MOCK style",
            "92_style_engine/forbidden_patterns.md": "## Layer 1\n\n## Layer 2\n",
            "92_style_engine/character_voice_samples.md": "## 甲\nMOCK voice\n\n## 乙\nUNUSED voice\n",
        }
        for relative, content in documents.items():
            self.write(relative, content)
        state = {"run_id": self.run.name, "work_id": "ep001", "unit_kind": "scene", "mode": "live",
            "fixture_only": False, "project_id": base["project_id"], "contract_path": "contracts/unit.json",
            "contract_sha256": r.sha((self.project / "contracts/unit.json").read_bytes()),
            "stages": {s: {"status": "NOT_RUN"} for s in r.CNW_STAGES}, "provider_requests": [],
            "support_hooks": {}, "max_in_flight": 1, "status": "RUN_CREATED"}
        state["literary_source_hashes"] = r.literary_source_freeze(base, self.project)
        r.save_state(self.run, state)
        self.sent = []
        self.cache = {}
        self.brief_variant = ""
        self.fail_after_transport = False
        @wraps(r._nk_pov)
        def nk(run, state, contract):
            path = run / "artifacts/support/nk-reflection.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("MOCK reflection", encoding="utf-8")
            fresh = r.load_state(run)
            fresh["support_hooks"]["nk_pov"] = {"status": "MATERIALIZED", "artifact": {"path": str(path.relative_to(run)).replace('\\', '/'), "sha256": r.sha(path.read_bytes())}}
            r.save_state(run, fresh)
            return {"path": "artifacts/support/nk-reflection.md", "mapping": {}}
        self.addCleanup(patch.stopall)
        patch.object(r, "_nk_pov", nk).start()
        patch.object(r, "_critics_hook", return_value={"status": "MOCK_ONLY"}).start()
        patch.object(r, "cnw_live_call", side_effect=self.provider).start()
        patch.object(r.httpx, "post", side_effect=AssertionError("network forbidden")).start()
        patch.object(r, "_p2_guard", side_effect=AssertionError("new reserve forbidden")).start()

    def write(self, relative, content):
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def args(self, **kwargs):
        return SimpleNamespace(run_id=self.run.name, project_root=str(self.project), **kwargs)

    def provider(self, run, *, stage, role_id, messages, output_cap, extra=None):
        key = recovery._digest([stage, role_id, messages, output_cap, extra])
        if key in self.cache:
            content, receipt = self.cache[key]
            r._receipt_content(run, receipt)
            r.reactivate_receipt(run, receipt)
            return content, receipt
        self.sent.append((stage, role_id, copy.deepcopy(messages)))
        if stage in {"plot", "scene_cards", "writing_brief"}:
            role = {"scene_cards": "cards", "writing_brief": "brief"}.get(stage, stage)
            content = "\n".join(heading + "\nB01 MOCK action" for heading in roles.ROLE_REQUIRED_SECTIONS[role])
            if stage == "writing_brief":
                content += "\n## Voice References\n- 甲\n" + self.brief_variant
        elif stage == "prose":
            content = "甲把伞推给乙，自己站回屋檐下。乙拉住伞柄，又往甲那边挪了一步。" * 2
        elif stage == "multi_lens_review":
            content = json.dumps({"lens_id": role_id, "findings": []})
        elif stage == "completeness_critic":
            content = '{"candidate_findings":[]}'
        else:
            raise AssertionError(stage)
        identifier = f"MOCK-{len(self.sent)}"
        request_path = run / f"artifacts/provider/{identifier}.request.json"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(json.dumps({"messages": messages}, ensure_ascii=False), encoding="utf-8")
        raw_path = request_path.with_suffix(".raw.json")
        raw_path.write_text(json.dumps({"choices": [{"message": {"content": content}}]}, ensure_ascii=False), encoding="utf-8")
        receipt = {"status": "SUCCEEDED", "stage": stage, "role_id": role_id,
            "request_id": identifier, "provider_request_id": identifier, "mode": "MOCK_ONLY",
            "request_path": request_path.relative_to(run).as_posix(), "request_sha256": r.sha(request_path.read_bytes()),
            "input_sha256": r.sha(json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()),
            "raw_response_path": raw_path.relative_to(run).as_posix(), "raw_response_sha256": r.sha(raw_path.read_bytes()),
            "output_sha256": r.sha(content.encode())}
        state = r.load_state(run)
        state["provider_requests"].append(receipt)
        r.save_state(run, state)
        self.cache[key] = content, receipt
        if self.fail_after_transport and stage == "scene_cards":
            self.fail_after_transport = False
            raise OSError("MOCK interruption after successful transport")
        return content, receipt

    def execute(self):
        return r.resume_run(self.args())

    def test_resume_real_dispatcher_reuses_and_checks_every_stage(self):
        result = self.execute()
        self.assertEqual(set(result["stages"].values()), {"STAGE_MATERIALIZED"})
        count = len(self.sent)
        self.execute()
        self.assertEqual(len(self.sent), count)
        self.assertIs(r.make_parser().parse_args(["resume", "--run-id", "x"]).func, r.resume_run)
        state = r.load_state(self.run)
        self.assertTrue(all(record.get("execution_identity") for record in state["stages"].values()))

    def test_style_explicit_reopen_preserves_plot_and_identical_downstream(self):
        self.execute()
        before = copy.deepcopy(r.load_state(self.run))
        self.write("92_style_engine/style_guide.md", "MOCK changed style")
        with self.assertRaisesRegex(ContractError, "LITERARY_SOURCE_CHANGED"):
            self.execute()
        result = recovery.refresh_references(self.args(reason="MOCK explicit source correction"))
        self.assertEqual(set(result["reopened"]), {"writing_brief", "multi_lens_review", "re_review"})
        start = len(self.sent)
        self.execute()
        # Brief returns identical bytes: prose, verifiers and completeness reuse.
        self.assertEqual([(s, role) for s, role, _ in self.sent[start:]], [("writing_brief", "brief_agent"), ("multi_lens_review", "style")])
        state = r.load_state(self.run)
        self.assertEqual(state["stages"]["plot"], before["stages"]["plot"])
        recovery.verify_evidence(self.run, state)
        prior = state["stages"]["writing_brief"]["invalidated_attempts"][0]["artifact"]
        self.assertIn("/history/", prior["path"])

    def test_changed_brief_propagates_by_output_content(self):
        self.execute()
        self.write("92_style_engine/style_guide.md", "MOCK changed style")
        self.brief_variant = "Different Brief instruction"
        recovery.refresh_references(self.args(reason="MOCK style change"))
        start = len(self.sent)
        self.execute()
        new = [(s, role) for s, role, _ in self.sent[start:]]
        self.assertIn(("prose", "prose_agent_1"), new)
        self.assertIn(("multi_lens_review", "plot"), new)
        self.assertNotIn(("plot", "plot_agent"), new)
        recovery.verify_evidence(self.run, r.load_state(self.run))

    def test_builder_change_without_prompt_file_change_is_seen(self):
        self.execute()
        original = roles.build_author_role_messages
        def changed(role, contract, materials, *, extra=None):
            messages = original(role, contract, materials, extra=extra)
            if role == "brief":
                messages[0]["content"] += "\nMOCK builder correction"
            return messages
        count = len(self.sent)
        with patch.object(roles, "build_author_role_messages", changed):
            self.execute()
        self.assertEqual(len(self.sent), count + 1)

    def test_raw_or_output_tamper_is_not_repaired_by_new_paid_call(self):
        self.execute()
        for path in (self.run / "artifacts/prose.v0.md", next((self.run / "artifacts/provider").glob("*.raw.json"))):
            saved = path.read_bytes()
            path.write_bytes(b"tampered")
            count = len(self.sent)
            with self.assertRaises(ContractError):
                self.execute()
            self.assertEqual(len(self.sent), count)
            path.write_bytes(saved)

    def test_immutable_source_manifest_contract_rejected(self):
        self.execute()
        for relative in ("source.md", "manifest.json", "contracts/unit.json", "runs/MOCK-RECOVERY/artifacts/contract.json"):
            path = self.project / relative
            saved = path.read_bytes()
            path.write_bytes(saved + b"\nchanged")
            count = len(self.sent)
            with self.assertRaises(ContractError):
                recovery.refresh_references(self.args(reason="MOCK forbidden refreeze"))
            with self.assertRaises(ContractError):
                self.execute()
            self.assertEqual(len(self.sent), count)
            path.write_bytes(saved)

    def test_partial_success_is_replayed_without_resending(self):
        self.fail_after_transport = True
        with self.assertRaisesRegex(OSError, "MOCK interruption"):
            self.execute()
        count = len([row for row in self.sent if row[0] == "scene_cards"])
        self.execute()
        self.assertEqual(len([row for row in self.sent if row[0] == "scene_cards"]), count)
        recovery.verify_evidence(self.run, r.load_state(self.run))

    def test_explicit_invalidation_preserves_versions_and_exact_transport_cache(self):
        self.execute()
        count = len(self.sent)
        r.invalidate_run(self.args(from_stage="writing_brief"))
        self.execute()
        self.assertEqual(len(self.sent), count)
        recovery.verify_evidence(self.run, r.load_state(self.run))
        state = r.load_state(self.run)
        receipt = next(row for row in state["provider_requests"] if row["stage"] == "plot")
        messages = next(row[2] for row in self.sent if row[0] == "plot")
        receipt["request_fingerprint"] = r.sha(json.dumps({"stage": "plot", "role_id": "plot_agent", "messages": messages,
            "output_cap": 4000, "model": r.MODEL, "url": r.API_URL, "extra": None}, ensure_ascii=False, sort_keys=True).encode())
        state["provider_requests"] = [row for row in state["provider_requests"] if row["request_id"] != receipt["request_id"]]
        state.setdefault("provider_attempts", []).append({"prior_receipt": receipt})
        r.save_state(self.run, state)
        content, found = r._cnw_live_call_in_slot(self.run, stage="plot", role_id="plot_agent", messages=messages, output_cap=4000)
        self.assertEqual(found["request_id"], receipt["request_id"])
        self.assertEqual(r._receipt_content(self.run, found), content)
        self.assertIn(found, r.load_state(self.run)["provider_requests"])

    def test_step_cannot_reuse_with_changed_upstream_builder(self):
        self.execute()
        original = roles.build_author_role_messages
        def changed(role, contract, materials, *, extra=None):
            result = original(role, contract, materials, extra=extra)
            if role == "brief":
                result[0]["content"] += "changed"
            return result
        with patch.object(roles, "build_author_role_messages", changed):
            with self.assertRaisesRegex(ContractError, "STAGE_DEPENDENCY_INPUT_CHANGED"):
                r.step(self.args(stage="prose", work_id=None, input=None))

    def test_lens_feedback_reopens_review_only_and_archives_inner_files(self):
        self.execute()
        self.write("08_review/lens_feedback/canon.json", json.dumps([{"run_id": "OTHER-RUN", "instruction": "MOCK check terminology"}]))
        result = recovery.refresh_references(self.args(reason="MOCK review feedback"))
        self.assertEqual(set(result["reopened"]), {"multi_lens_review", "re_review"})
        start = len(self.sent)
        self.execute()
        self.assertEqual([(s, role) for s, role, _ in self.sent[start:]], [("multi_lens_review", "canon")])
        state = r.load_state(self.run)
        archived = state["stages"]["multi_lens_review"]["invalidated_attempts"][0]["artifact_children"]
        self.assertTrue(all("/history/" in row["path"] for row in archived["lenses"].values()))
        recovery.verify_evidence(self.run, state)

    def test_materialized_status_requires_artifact_and_export_code_is_separate(self):
        from tools import cnw_export
        self.execute()
        count = len(self.sent)
        with patch.object(cnw_export, "export_reading_package", return_value={"status": "MOCK renderer"}):
            self.execute()
        self.assertEqual(len(self.sent), count)
        state = r.load_state(self.run)
        state["stages"]["prose"].pop("artifact")
        r.save_state(self.run, state)
        with self.assertRaisesRegex(ContractError, "STAGE_ARTIFACT_MISSING"):
            self.execute()
        self.assertEqual(len(self.sent), count)

    def test_new_plot_saved_with_old_successful_support_is_recoverable(self):
        from tools import cnw_critics_adapter as adapter
        self.execute()
        state = r.load_state(self.run)
        plot = r._read_stage_text(self.run, state, "plot")
        excerpt = "MOCK old native excerpt"
        self.write("runs/MOCK-RECOVERY/artifacts/support/critics-excerpt.md", excerpt)
        for name, source in (("critics_plot", self.run / state["stages"]["plot"]["artifact"]["path"]),
                             ("critics_text", self.run / "artifacts/support/critics-excerpt.md")):
            state["support_hooks"][name] = {"status": "SUCCEEDED", "run_name": name,
                "input_sha256": r.sha(source.read_bytes()), "result": {"MOCK": name}, "evidence_files": []}
        r.save_state(self.run, state)
        def native(run_name, *, action, input_path):
            self.assertEqual(input_path.read_text(encoding="utf-8"), plot if action == "plan-critique" else excerpt)
            return {"result": {"MOCK": run_name}, "evidence_files": []}
        with patch.object(adapter, "read_native_result", side_effect=native):
            recovery.verify_evidence(self.run, state)  # bind legacy input first
            state = r.load_state(self.run)
            recovery.archive_stage(self.run, state, "plot", "MOCK reopen")
            r.save_state(self.run, state)
            r._persist_stage(self.run, "plot", "artifacts/plot.md", "MOCK newly generated Plot, support still pending")
            self.write("runs/MOCK-RECOVERY/artifacts/support/critics-excerpt.md", "MOCK new excerpt")
            recovery.verify_evidence(self.run, r.load_state(self.run))
            # Verification reads the two immutable old inputs, not new outputs.
            state = r.load_state(self.run)
            path = self.run / state["support_hooks"]["critics_plot"]["input_artifact"]["path"]
            path.write_text("tampered snapshot", encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "CRITICS_INPUT_CHANGED"):
                recovery.verify_evidence(self.run, state)


if __name__ == "__main__":
    unittest.main()
