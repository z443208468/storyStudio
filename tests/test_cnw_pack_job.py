"""Package entry owns real CNW scheduling; only final model replies are injected."""
from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import subprocess
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import test_cnw_pack_app as pack_fixtures
from tests import test_cnw_atom09_three_project_e2e as model_fixtures
from tests.test_cnw_input_pack import encoded, sha
from tools import cnw_pack_app as app, cnw_runner as runner
from tools.cnw_contract import count_visible_chars


class PackageJobTests(unittest.TestCase):
    def setUp(self):
        self.pack_fixture = pack_fixtures.PackApplicationTests()
        self.pack_fixture.setUp()
        self.addCleanup(self.pack_fixture.tearDown)
        self.f = self.pack_fixture.fixture
        self.pack_fixture.set_bounds(4700)
        for label in "ABC":
            self.f.files[f"scenes/{label}/project_seed/92_style_engine/forbidden_patterns.md"] = (
                f"## Layer 1\n| Rule | Pattern | Cap |\n|---|---|---|\n| SURFACE-{label} | `SURFACE_{label}` | 0 |\n"
                f"## Layer 2\n| Rule | Pattern | Cap |\n|---|---|---|\n| STRUCTURAL-{label} | `STRUCTURAL_{label}` | 0 |\n").encode()
        self.f.write_pack()
        self.model = model_fixtures.ThreeProjectOfflineE2E()
        self.model._guard_lock = threading.Lock()
        self.model._counter = 0
        self.model.requests = []
        self.cache = {}
        self.interrupted = False
        self.fail_once = False
        self.created_job = None
        self.evidence = []
        self.extra_refine = False
        self.always_fail_review = False

    def _fit(self, passage, target=3100, prefix=""):
        text = prefix + (passage + "\n") * (target // max(1, count_visible_chars(passage)) + 2)
        end, visible = 0, 0
        for end, char in enumerate(text, 1):
            visible += count_visible_chars(char)
            if visible == target:
                break
        value = text[:end].strip()
        self.assertEqual(count_visible_chars(value), target)
        return value

    def _response(self, run, stage, role, messages, extra):
        state = runner.load_state(run)
        contract = json.loads((run / "artifacts/contract.json").read_text(encoding="utf-8"))
        label = contract["unit"]["id"].rsplit("-", 1)[1]
        wire = json.dumps(messages, ensure_ascii=False)
        for other in "ABC":
            if other != label:
                self.assertNotIn(f"CONFIRMED-CANON-{other}", wire)
                self.assertNotIn(f"ENTRY-{other}", wire)
        if stage in {"plot", "scene_cards", "writing_brief"}:
            if stage == "plot":
                self.assertIn(f"ENTRY-{label}", wire)
                self.assertIn(f"REWARD-{label}", wire)
                self.assertIn(f"SELECTED-ARC-{label}", wire)
                self.assertIn("Preserve even unmapped requirements.", wire)
                self.assertIn("SOURCE-", wire)
            if stage in {"scene_cards", "writing_brief"}:
                self.assertIn(f"fictional courtyard {label}", wire)
            return self.model._sections(stage, "Mira", "Mira", f"fictional courtyard {label}").replace(
                "100–320 visible characters", "2200–4700 visible characters; target 3100")
        if stage == "prose":
            payload = json.loads(messages[1]["content"])
            self.assertEqual(set(payload), {"writing_brief", "voice_samples"})
            self.assertIn(f"fictional courtyard {label}", payload["writing_brief"])
            self.assertNotIn("PRIVATE-SECRET", wire)
            self.assertNotIn("SURFACE_", wire)
            self.assertNotIn("STRUCTURAL_", wire)
            # B has different project rules and therefore no hits on A's markers.
            token = "A" if label == "B" else label
            return self._fit(f"Mira checked the courtyard {label}. She accepted the tool and claimed a sibling.",
                             prefix=f"SURFACE_{token} STRUCTURAL_{token}.\n")
        if stage == "multi_lens_review":
            if role == "story_specific":
                self.assertIn(f"Check local promise {label} and its exact boundary.", wire)
            findings = [{"finding_id": f"FABRICATED-KINSHIP-{label}", "severity": "P1", "issue": "Invented sibling contradicts Canon.",
                         "evidence": "claimed a sibling", "recommendation": "Remove the invented relationship."}] if role == "canon" else []
            return json.dumps({"lens_id": role, "findings": findings})
        if stage == "adversarial_verify":
            return json.dumps({"verifier_id": role, "votes": [{"finding_id": extra["finding_id"],
                "verdict": "refuted" if role == "continuity_plausibility" else "not_refuted", "reason": "Independent simulated countercheck."}]})
        if stage == "completeness_critic":
            return json.dumps({"candidate_findings": [{"finding_id": f"OMITTED-NEXT-REQUEST-{label}", "lens_id": "story_specific",
                "category": "reader_reward", "issue": "No observable next request.", "evidence": "The draft stops at the tool.",
                "recommendation": "Add a concrete return request.", "prompt_update": "Check the concrete next request."}]})
        if stage == "refine":
            if runner.load_state(run)["stages"]["refine"].get("pending_findings"):
                self.assertIn("R1-canon-1" if not self.always_fail_review else "canon-1", wire)
            else:
                self.assertIn(f"OMITTED-NEXT-REQUEST-{label}", wire)
            self.assertIn("canon-1", wire)
            version = extra["revision_number"]
            return self._fit(f"Mira checked the courtyard {label} at repair step {version}. She accepted the tool, tightened the hinge, and asked where to return it.")
        if stage == "re_review":
            if extra and extra.get("task_kind") == "verifier":
                return json.dumps({"verifier_id": role, "votes": [{"finding_id": extra["finding_id"],
                    "verdict": "refuted" if role == "continuity_plausibility" else "not_refuted", "reason": "Independent new-draft countercheck."}]})
            self.assertIn("asked where to return it", wire)
            payload = json.loads(messages[1]["content"])
            self.assertNotIn("claimed a sibling", payload["draft"])
            revision = state["stages"]["refine"].get("revision_number", 1)
            findings = [{"severity": "P1", "issue": "Repair response needs a clearer observation.", "evidence": "tightened the hinge",
                         "recommendation": "Make the visible result explicit."}] if role == "canon" and (self.always_fail_review or self.extra_refine and revision == 1) else []
            return json.dumps({"lens_id": role, "findings": findings})
        raise AssertionError(f"unexpected model stage {stage}/{role}")

    def transport(self, run, *, stage, role_id, messages, output_cap, extra=None):
        # Explicit fixture ownership is checked in every worker thread; no
        # thread-local context or production/trust switch supplies permission.
        self.assertTrue(self.f.temp._finalizer.alive)
        self.assertTrue(run.resolve().is_relative_to(self.f.home.resolve()))
        state = runner.load_state(run)
        self.assertFalse(state["fixture_only"])
        self.assertEqual(state["mode"], "offline")
        key = sha(encoded([str(run.resolve()), stage, role_id, messages, output_cap, extra]))
        if key in self.cache:
            content, receipt = self.cache[key]
            self.assertEqual(runner._receipt_content(run, receipt), content)
            return content, receipt
        content = self._response(run, stage, role_id, messages, extra)
        result = self.model._workflow_response(run, messages, content, stage=stage, role_id=role_id)
        self.cache[key] = result
        if self.fail_once and stage == "scene_cards" and not self.interrupted:
            self.interrupted = True
            raise RuntimeError("SIMULATED_PACKAGE_INTERRUPTION_AFTER_RECEIPT")
        return result

    @contextlib.contextmanager
    def disconnected(self):
        def denied(*args, **kwargs):
            raise AssertionError("real network/request forbidden")
        real_popen = subprocess.Popen
        def local_process(command, *args, **kwargs):
            if not isinstance(command, (list, tuple)) or not command:
                raise AssertionError("shell/network subprocess forbidden")
            executable = Path(str(command[0])).name.lower()
            if executable in {"whoami", "whoami.exe", "icacls", "icacls.exe"}:
                return real_popen(command, *args, **kwargs)
            # Only pinned object reads used by real readers; never fetch/clone.
            if executable in {"git", "git.exe"} and any(x in command for x in ("show", "cat-file", "rev-parse")):
                if any(x in command for x in ("fetch", "clone", "push", "pull")):
                    raise AssertionError("Git network forbidden")
                return real_popen(command, *args, **kwargs)
            raise AssertionError("network/subprocess startup forbidden")
        with patch.dict(os.environ, {k: v for k, v in os.environ.items() if k not in {"DEEPSEEK_API_KEY", "OPENAI_API_KEY"}}, clear=True), \
             patch.object(socket.socket, "connect", new=denied), \
             patch.object(socket.socket, "connect_ex", new=denied), \
             patch.object(subprocess, "Popen", new=local_process), \
             patch.object(os, "system", new=denied), \
             patch("socket.create_connection", side_effect=AssertionError("network forbidden")), \
             patch("urllib.request.urlopen", side_effect=AssertionError("HTTP forbidden")), \
             patch.object(runner, "_p2_guard", side_effect=AssertionError("slot/fees forbidden")), \
             patch.object(runner, "_cnw_live_call_in_slot", new=denied):
            yield

    def entry(self, *, job=None, transport=True):
        args = ["--data-home", str(self.f.home), "--offline", "--execute-job"]
        args += ["--job", job] if job else ["--input", str(self.f.pack), "--source-repository", str(self.f.repo)]
        stdout = io.StringIO()
        boundary = patch.object(runner, "cnw_live_call", side_effect=self.transport) if transport else contextlib.nullcontext()
        with self.disconnected(), boundary, contextlib.redirect_stdout(stdout):
            code = app.main(args)
        result = json.loads(stdout.getvalue())
        self.created_job = result["job_record"]
        return code, result

    def test_formal_package_entry_automatically_executes_three_chains_export_and_resume(self):
        source_before = (self.f.repo / "source.md").read_bytes()
        pack_before = self.f.pack.read_bytes()
        pointer_before = (self.f.base / "pointer.json").read_bytes()
        self.fail_once = True
        code, interrupted = self.entry()
        self.assertEqual(code, 2)
        self.assertEqual(interrupted["status"], "JOB_EXECUTION_INCOMPLETE")
        row = interrupted["tasks"][0]
        run = Path(row["run_preparation"]["run_path"])
        plot = runner.load_state(run)["stages"]["plot"]["artifact"]
        plot_before = (run / plot["path"]).read_bytes()
        receipts_before = runner.load_state(run)["provider_requests"]
        self.assertEqual(len(receipts_before), 2)
        code, finished = self.entry(job=self.created_job)
        self.assertEqual(code, 0, [(r.get("execution", {}).get("interruptions"), r["status"]) for r in finished["tasks"]])
        self.assertEqual(finished["status"], "MOCK_STORIES_EXPORTED")
        self.assertEqual((run / plot["path"]).read_bytes(), plot_before)
        self.assertEqual(len({r["project_instance_id"] for r in finished["tasks"]}), 3)
        for label, task in zip("ABC", finished["tasks"]):
            root = Path(task["project_root"])
            run = root / "runs" / task["planned_run_id"]
            state = runner.load_state(run)
            self.assertEqual(list(task["execution"]["stages"]), list(runner.CNW_STAGES))
            self.assertEqual(len(state["provider_requests"]), 16 if label == "B" else 22)
            self.assertEqual(len([r for r in state["provider_requests"] if r["stage"] == "scene_cards"]), 1)
            for stage in runner.CNW_STAGES:
                material = state["stages"][stage]
                self.assertEqual(material["status"], "STAGE_MATERIALIZED")
                self.assertEqual(sha((run / material["artifact"]["path"]).read_bytes()), material["artifact"]["sha256"])
                self.assertTrue((run / material["artifact"]["path"]).stat().st_size)
            prose = runner._read_stage_text(run, state, "prose")
            refined = runner._read_stage_text(run, state, "refine")
            self.assertEqual(count_visible_chars(prose), 3100)
            self.assertEqual(count_visible_chars(refined), 3100)
            self.assertNotEqual(sha(prose.encode()), sha(refined.encode()))
            for layer in ("lint_layer1", "lint_layer2"):
                lint = json.loads(runner._read_stage_text(run, state, layer))
                self.assertEqual(lint["source_sha256"], sha(prose.encode()))
                self.assertFalse(lint["text_modified"])
                self.assertEqual(lint["executable_rule_count"], 1)
                self.assertEqual(bool(lint["findings"]), label != "B")
            votes = json.loads(runner._read_stage_text(run, state, "adversarial_verify"))
            self.assertIn("canon-1", json.dumps(votes))
            self.assertEqual(len(votes["findings"]), 1 if label == "B" else 2)
            for item in votes["verdicts"].values():
                self.assertEqual(item["status"], "CONFIRMED")
                self.assertEqual(len(item["votes"]), 3)
                self.assertEqual(list(item["votes"].values()).count("not_refuted"), 2)
            rereview = json.loads(runner._read_stage_text(run, state, "re_review"))
            self.assertEqual(rereview["candidate_sha256"], sha(refined.encode()))
            self.assertEqual(rereview["status"], "CLEAN")
            export = task["execution"]["export"]
            target = Path(export["result"]["deliverables"])
            self.assertEqual((target / "02_修订稿.txt").read_text(encoding="utf-8"), refined)
            manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["execution_mode"], "MOCK_ONLY")
            self.assertEqual(manifest["simulation_status"], "SIMULATED")
            self.assertEqual(manifest["live_validation_status"], "NOT_LIVE_VALIDATED")
            self.assertFalse(manifest["user_creative_accepted"])
            self.assertIn("MOCK_ONLY / SIMULATED", (target / "03_前后文连读.html").read_text(encoding="utf-8"))
            self.evidence.append({"task": task, "run_state": state,
                                  "artifacts": {s: runner._read_stage_text(run, state, s) for s in runner.CNW_STAGES},
                                  "export_files": {p.relative_to(root).as_posix(): {"sha256": sha(p.read_bytes()), "raw_utf8": p.read_bytes().decode("utf-8")}
                                                   for p in target.iterdir() if p.is_file()}})
        hashes = {p: sha(p.read_bytes()) for t in finished["tasks"] for p in (Path(t["project_root"]) / "runs").rglob("*") if p.is_file() and not p.name.endswith(".lock")}
        requests = len(self.model.requests)
        code, again = self.entry(job=self.created_job)
        self.assertEqual(code, 0, again)
        self.assertEqual(len(self.model.requests), requests)
        for path, digest in hashes.items():
            self.assertEqual(sha(path.read_bytes()), digest)
        self.assertEqual(self.f.pack.read_bytes(), pack_before)
        self.assertEqual((self.f.repo / "source.md").read_bytes(), source_before)
        self.assertEqual((self.f.base / "pointer.json").read_bytes(), pointer_before)
        destination = os.environ.get("ATOM09_PACK_JOB_EVIDENCE_OUTPUT")
        if destination:
            Path(destination).write_bytes(encoded({"execution": "SIMULATED_OFFLINE_PACKAGE_JOB", "interrupted": interrupted,
                "finished": finished, "tasks": self.evidence, "model_requests": self.model.requests,
                "existing_run_bytes_unchanged_on_repeat": True, "network_and_fees": "NOT_RUN"}))

    def test_real_job_without_harness_refuses_before_slot_fee_http(self):
        code, report = self.entry(transport=False)
        self.assertEqual(code, 2)
        self.assertEqual(report["blocking_code"], "OFFLINE_PROVIDER_FORBIDDEN")
        self.assertEqual(report["status"], "JOB_EXECUTION_INCOMPLETE")
        self.assertFalse(self.model.requests)
        for task in report["tasks"]:
            root = Path(task["project_root"])
            state = runner.load_state(root / "runs" / task["planned_run_id"])
            self.assertFalse(state["provider_requests"])
            self.assertFalse((root / "deliverables").exists())

    def test_all_capacity_pending_tasks_do_not_claim_execution_or_story_export(self):
        for label in "ABC":
            name = f"scenes/{label}/work_order.draft.json"
            order = json.loads(self.f.files[name]); order["max_visible_chars"] = 4701
            self.f.files[name] = encoded(order)
            name = f"scenes/{label}/project_seed/config/project.yml"
            self.f.files[name] = self.f.files[name].replace(b": 4700\n", b": 4701\n")
        self.f.write_pack()
        code, report = self.entry()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "INPUTS_PREPARED_WITH_CAPACITY_PENDING")
        self.assertEqual(report["simulation_status"], "NOT_EXECUTED")
        self.assertFalse(self.model.requests)
        for task in report["tasks"]:
            self.assertEqual(task["status"], "CAPACITY_PENDING")
            self.assertFalse(any((Path(task["project_root"]) / "runs").iterdir()))
            self.assertFalse((Path(task["project_root"]) / "deliverables").exists())

    def test_changed_job_contract_and_export_are_rejected_and_old_bytes_retained(self):
        code, report = self.entry()
        self.assertEqual(code, 0, [(r.get("execution", {}).get("interruptions"), r["status"]) for r in report["tasks"]])
        task = report["tasks"][0]
        output = Path(task["execution"]["export"]["result"]["deliverables"]) / "02_修订稿.txt"
        output.write_text("Externally changed fixture candidate: preserve it.", encoding="utf-8")
        requests = len(self.model.requests)
        code, changed = self.entry(job=self.created_job)
        self.assertEqual(code, 2)
        self.assertEqual(changed["blocking_code"], "INPUT_PACK_EXPORT_CHANGED")
        self.assertEqual(output.read_text(encoding="utf-8"), "Externally changed fixture candidate: preserve it.")
        self.assertEqual(len(self.model.requests), requests)
        contract = Path(task["contract"])
        before = contract.read_bytes()
        contract.write_bytes(before + b"\n")
        with self.assertRaisesRegex(app.ContractError, "INPUT_PACK_JOB_BINDINGS_CHANGED"):
            self.entry(job=self.created_job)
        self.assertEqual(contract.read_bytes(), before + b"\n")

    def single_task(self):
        for label in "BC":
            self.f.files.pop(f"scenes/{label}/work_order.draft.json")
        self.f.files["workpack_index.json"] = encoded({"schema": "cnw_workpack_index_v1", "workpacks": [{"root": "scenes/A/project_seed"}]})
        self.f.write_pack()

    def test_export_file_interruption_and_completed_export_before_job_save_resume(self):
        self.single_task()
        actual_rename = Path.rename
        tripped = False
        def interrupted_file(path, target):
            nonlocal tripped
            if Path(target).name == "02_修订稿.txt" and ".export-" in str(target) and not tripped:
                tripped = True
                raise OSError("SIMULATED_EXPORT_FILE_WRITE_INTERRUPTION")
            return actual_rename(path, target)
        with patch.object(Path, "rename", new=interrupted_file):
            code, failed = self.entry()
        self.assertEqual(code, 2)
        self.assertTrue(tripped)
        task = failed["tasks"][0]
        root = Path(task["project_root"])
        partial = next(p for p in (root / "deliverables" / task["project_instance_id"]).glob("*.export-*") if (p / ".story-studio-export.json").is_file())
        self.assertTrue(partial.is_dir())
        existing = {p.name: sha(p.read_bytes()) for p in partial.iterdir() if p.is_file()}
        requests = len(self.model.requests)
        code, finished = self.entry(job=self.created_job)
        self.assertEqual(code, 0, finished.get("blocking_code"))
        self.assertEqual(len(self.model.requests), requests)
        final = Path(finished["tasks"][0]["execution"]["export"]["result"]["deliverables"])
        for name, digest in existing.items():
            self.assertEqual(sha((final / name).read_bytes()), digest)

        # A fresh job's process dies after the genuine exporter returns and
        # before job CAS records that export. The transaction itself persists.
        class SimulatedPowerLoss(BaseException):
            pass
        actual_save = app._save_job_progress
        def interrupted_save(path, previous, report):
            if any(r.get("execution", {}).get("export") for r in report["tasks"]):
                raise SimulatedPowerLoss("SIMULATED_EXPORT_TO_JOB_CAS_POWER_LOSS")
            return actual_save(path, previous, report)
        with patch.object(app, "_save_job_progress", new=interrupted_save), self.assertRaises(SimulatedPowerLoss):
            self.entry()
        candidates = [p for p in (self.f.home / "shared/input_pack_jobs").glob("*/result.json") if str(p.resolve()) != str(Path(self.created_job).resolve())]
        self.assertEqual(len(candidates), 1)
        record = candidates[0]
        persisted = json.loads(record.read_text(encoding="utf-8"))
        self.assertNotIn("export", persisted["tasks"][0]["execution"])
        owned = persisted["tasks"][0]
        destination = Path(owned["project_root"]) / "deliverables" / owned["project_instance_id"] / owned["planned_run_id"]
        before = {p.name: sha(p.read_bytes()) for p in destination.iterdir()}
        requests = len(self.model.requests)
        code, recovered = self.entry(job=str(record))
        self.assertEqual(code, 0, recovered.get("blocking_code"))
        self.assertEqual(len(self.model.requests), requests)
        self.assertEqual({p.name: sha(p.read_bytes()) for p in destination.iterdir()}, before)

    def test_additional_refine_job_and_export_follow_final_run_and_exhaustion_pauses(self):
        self.single_task()
        self.extra_refine = True
        code, report = self.entry()
        self.assertEqual(code, 0, [r.get("execution", {}).get("interruptions") for r in report["tasks"]])
        task = report["tasks"][0]
        run = Path(task["run_preparation"]["run_path"])
        state = runner.load_state(run)
        self.assertEqual(state["stages"]["refine"]["revision_number"], 2)
        self.assertEqual(task["execution"]["stages"]["refine"]["artifact"], state["stages"]["refine"]["artifact"])
        self.assertEqual(task["execution"]["stages"]["refine"]["execution_identity"], state["stages"]["refine"]["execution_identity"])
        first_receipt = next(r for r in state["provider_requests"] if r["stage"] == "refine")
        first_version = run / "artifacts/candidates/refine" / (first_receipt["output_sha256"] + ".md")
        self.assertTrue(first_version.is_file())
        revised = runner._read_stage_text(run, state, "refine")
        self.assertNotEqual(sha(revised.encode()), first_receipt["output_sha256"])
        self.assertEqual((run / "artifacts/revisions/revision-2.base.md").read_text(encoding="utf-8"), first_version.read_text(encoding="utf-8"))
        review = json.loads(runner._read_stage_text(run, state, "re_review"))
        self.assertEqual(review["candidate_sha256"], sha(revised.encode()))
        target = Path(task["execution"]["export"]["result"]["deliverables"])
        self.assertEqual((target / "02_修订稿.txt").read_text(encoding="utf-8"), revised)
        self.always_fail_review = True
        code, paused = self.entry()
        self.assertEqual(code, 2)
        self.assertEqual(paused["status"], "JOB_AWAITING_AUTHOR")
        self.assertEqual(paused["blocking_code"], "REREVIEW_REQUIRES_REVISION")
        self.assertNotIn("export", paused["tasks"][0]["execution"])
        pending_run = Path(paused["tasks"][0]["run_preparation"]["run_path"])
        old = {p.relative_to(pending_run).as_posix(): sha(p.read_bytes()) for p in pending_run.rglob("*") if p.is_file() and not p.name.endswith(".lock")}
        requests = len(self.model.requests)
        code, again = self.entry(job=self.created_job)
        self.assertEqual(code, 2)
        self.assertEqual(again["status"], "JOB_AWAITING_AUTHOR")
        self.assertEqual(len(self.model.requests), requests)
        self.assertEqual({p.relative_to(pending_run).as_posix(): sha(p.read_bytes()) for p in pending_run.rglob("*") if p.is_file() and not p.name.endswith(".lock")}, old)
        self.assertFalse((pending_run.parent.parent / "deliverables").exists())
