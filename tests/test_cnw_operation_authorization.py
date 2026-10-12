"""Bounded Atom-07 operation gates; only the final model boundary is simulated."""
from __future__ import annotations

from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import cnw_import_workflow as imports, cnw_maintenance as maintenance, cnw_runner as runner
from tools.cnw_contract import ContractError
from tools.cnw_project import init_registered_project
from tools.project_paths import PathResolutionError, create_project, setup_data_home


def _write(root, name, raw):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw if isinstance(raw, bytes) else raw.encode("utf-8"))
    return path


class OperationAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.owner = tempfile.TemporaryDirectory(prefix="storystudio-operation-gate-")
        self.addCleanup(self.owner.cleanup)
        self.base = Path(self.owner.name).resolve()
        self.home = self.base / "data-home"
        setup_data_home(self.home, pointer_path=self.base / "user-config/setup.json")
        self.projects = []
        for name in ("HARBOR_OPERATIONS", "ORCHARD_OPERATIONS"):
            registration = create_project(project_id=name, display_name=name, data_home=self.home)
            root = Path(registration["project_root"])
            init_registered_project(root)
            _write(root, "_INBOX/notes.md", "Ada repairs the fictional harbor bell.")
            _write(root, "90_canon/canon.md", "# Canon\nAda is a fictional mechanic.\n")
            self.projects.append(root)
        self.root, self.other = self.projects
        self.calls = []
        self.mutate = None
        self.ledger = _write(self.base, "isolated-ledger.json", '{"records":[]}\n')
        self.ledger_before = self.ledger.read_bytes()
        self.addCleanup(lambda: self.assertEqual(self.ledger_before, self.ledger.read_bytes()))
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {"DEEPSEEK_API_KEY": "TEST_ONLY_UNUSABLE_KEY_1234567890"}).start()
        self.slot = patch.object(runner, "_p2_guard", side_effect=AssertionError("REAL_COST_GUARD_FORBIDDEN")).start()
        self.http = patch.object(runner.httpx, "post", side_effect=AssertionError("REAL_HTTP_FORBIDDEN")).start()
        def denied(*args, **kwargs):
            raise AssertionError("NETWORK_OR_PROVIDER_PROCESS_FORBIDDEN")
        for target, name in ((socket.socket, "connect"), (socket.socket, "connect_ex"),
                             (socket, "create_connection"), (os, "system")):
            patch.object(target, name, denied).start()
        original_popen = subprocess.Popen
        def guarded_popen(args, *pargs, **kwargs):
            command = args[0] if isinstance(args, (tuple, list)) and args else args
            name = Path(str(command)).name.lower()
            if (name in {"whoami", "whoami.exe"} and isinstance(args, (tuple, list))
                    and list(args[1:]) == ["/user", "/fo", "csv", "/nh"]):
                return original_popen(args, *pargs, **kwargs)
            if (name in {"icacls", "icacls.exe"} and isinstance(args, (tuple, list)) and len(args) == 2
                    and Path(args[1]).resolve(strict=True).is_relative_to(self.base)):
                return original_popen(args, *pargs, **kwargs)
            return denied()
        patch.object(subprocess, "Popen", guarded_popen).start()

    def _run(self, kind="imports", root=None, name="operation-run"):
        run = (root or self.root) / "94_runtime" / kind / name
        run.mkdir(parents=True, exist_ok=True)
        runner.save_state(run, {"run_id": name, "schema_version":
            "cnw_import_run_v1" if kind == "imports" else "cnw_maintenance_run_v1",
            "provider_requests": []})
        return run

    def _record(self, run, *, stage, role_id, messages, output_cap, extra=None):
        self.calls.append((run, stage, role_id, messages))
        if stage in {"project_import", "project_update"}:
            payload = json.loads(messages[-1]["content"])
            source = next(iter(payload["original_sources"]))
            content = json.dumps({"documents": {name: [{"status": "CONFIRMED",
                "text": "## Source fact\n" + payload["original_sources"][source]["text"],
                "source_refs": [source]}] for name in imports.DOCUMENTS},
                "conflicts": [], "source_notes": {name: "Fictional source notes"
                    for name in payload["original_sources"]}, "next_action": "Review source-backed candidates."})
        elif stage == "project_handoff":
            content = json.dumps({"brief_markdown": "\n\n".join(
                "## " + name + "\nFictional project; no facts promoted." for name in maintenance.HANDOFF_SECTIONS)})
        else:
            content = json.dumps({"report_markdown": "# Continuity Audit\nNo findings in this fixture.\n", "action_items": []})
        request_id = f"SIM-OP-{len(self.calls)}"
        request = _write(run, f"artifacts/{request_id}.request.json",
                         json.dumps({"messages": messages}, ensure_ascii=False, sort_keys=True))
        raw = _write(run, f"artifacts/{request_id}.raw.json",
                     json.dumps({"choices": [{"message": {"content": content}}]}, ensure_ascii=False))
        receipt = {"request_id": request_id, "provider_request_id": request_id,
            "status": "SUCCEEDED", "mode": "MOCK_ONLY", "simulation_status": "SIMULATED",
            "fixture_only": True, "request_path": request.relative_to(run).as_posix(),
            "request_sha256": runner.sha(request.read_bytes()),
            "raw_response_path": raw.relative_to(run).as_posix(),
            "raw_response_sha256": runner.sha(raw.read_bytes()), "output_sha256": runner.sha(content.encode())}
        receipt.update(runner._operation_simulation_request_binding(run,
            stage=stage, role_id=role_id, messages=messages))
        if self.mutate:
            self.mutate(receipt, run)
        omit = receipt.pop("_omit_registration", False)
        duplicate = receipt.pop("_duplicate_registration", False)
        state = runner.load_state(run)
        if omit is not True:
            state["provider_requests"].append(copy.deepcopy(receipt))
        if duplicate is True:
            state["provider_requests"].append(copy.deepcopy(receipt))
        runner.save_state(run, state)
        return content, receipt

    @contextmanager
    def _session(self, projects=None):
        with runner._isolated_operation_transport(self.owner, data_home=self.home,
                projects=projects or [self.root], transport=self._record):
            yield

    def _call(self, run):
        return runner.cnw_live_call(run, stage="project_audit", role_id="project_audit",
            messages=[{"role": "user", "content": "Audit the fictional bell."}], output_cap=6000)

    def _assert_no_real_transport(self):
        self.slot.assert_not_called()
        self.http.assert_not_called()
        self.assertEqual(self.ledger.read_bytes(), self.ledger_before)

    def test_front_high_low_and_schema_relabel_refuse_before_cost_or_publication(self):
        canon = (self.root / "90_canon/canon.md").read_bytes()
        for action in (lambda: imports.run_import(self.root),
                       lambda: maintenance.run_maintenance(self.root, "audit"),
                       lambda: maintenance.run_maintenance(self.root, "handoff")):
            with self.subTest(action=action), self.assertRaisesRegex(ContractError, "LIVE_AUTHORIZATION_REQUIRED"):
                action()
        for kind in ("imports", "maintenance"):
            run = self._run(kind)
            for schema in ("cnw_import_run_v1", "invented_legacy_state"):
                state = runner.load_state(run)
                state.update(schema_version=schema, mode="live", provider_call_authorized=True)
                runner.save_state(run, state)
                for function in (runner.cnw_live_call, runner._cnw_live_call_in_slot):
                    with self.subTest(kind=kind, schema=schema, function=function.__name__), self.assertRaisesRegex(ContractError, "LIVE_AUTHORIZATION_REQUIRED"):
                        function(run, stage="project_audit", role_id="project_audit", messages=[], output_cap=6000)
            alias = run / ".." / run.name
            for function in (runner.cnw_live_call, runner._cnw_live_call_in_slot):
                with self.subTest(kind=kind, path_alias=True, function=function.__name__), self.assertRaisesRegex(PathResolutionError, "OPERATION_PROJECT_PATH_UNSAFE"):
                    function(alias, stage="project_audit", role_id="project_audit", messages=[], output_cap=6000)
            if os.name == "nt":
                case_alias = run.parent.parent / run.parent.name.upper() / run.name
                for function in (runner.cnw_live_call, runner._cnw_live_call_in_slot):
                    with self.subTest(kind=kind, case_alias=True, function=function.__name__), self.assertRaisesRegex(ContractError, "LIVE_AUTHORIZATION_REQUIRED"):
                        function(case_alias, stage="project_audit", role_id="project_audit", messages=[], output_cap=6000)
        if os.name == "nt":
            # Rename only this owned temporary fixture to exercise physical case.
            # Two hops ensure Windows stores the requested spelling.
            runtime = self.root / "94_runtime"
            temporary = runtime.rename(self.root / "runtime-case-fixture")
            runtime = temporary.rename(self.root / "94_RUNTIME")
            for kind in ("imports", "maintenance"):
                folder = runtime / kind
                temporary = folder.rename(runtime / (kind + "-case-fixture"))
                temporary.rename(runtime / kind.upper())
                physical_alias = self.root / "94_runtime" / kind / "operation-run"
                physical = physical_alias.resolve(strict=True)
                self.assertEqual(physical.parent.name, kind.upper())
                self.assertEqual(physical.parent.parent.name, "94_RUNTIME")
                for function in (runner.cnw_live_call, runner._cnw_live_call_in_slot):
                    with self.subTest(kind=kind, physical_case=True, function=function.__name__), self.assertRaisesRegex(ContractError, "LIVE_AUTHORIZATION_REQUIRED"):
                        function(physical_alias, stage="project_audit", role_id="project_audit", messages=[], output_cap=6000)
        self.assertEqual((self.root / "90_canon/canon.md").read_bytes(), canon)
        self.assertFalse((self.root / imports.PENDING).exists())
        self.assertFalse((self.root / maintenance.PENDING).exists())
        self._assert_no_real_transport()

    def test_actual_import_incremental_and_maintenance_consume_simulated_receipts(self):
        original = (self.root / "_INBOX/notes.md").read_bytes()
        with self._session():
            self.assertEqual(imports.run_import(self.root)["status"], "INITIAL_IMPORT_COMPLETE")
            self.assertIn(original, (self.root / "90_canon/canon.md").read_bytes())
            self.assertEqual(imports.run_import(self.root, incremental=True)["provider_call"], "none")
            _write(self.root, "_INBOX/extra.md", "Ada keeps the original harbor bell.")
            self.assertEqual(imports.run_import(self.root, incremental=True)["status"], "INCREMENTAL_IMPORT_COMPLETE")
            before_audit = (self.root / "90_canon/canon.md").read_bytes()
            self.assertFalse(maintenance.run_maintenance(self.root, "audit")["canon_modified"])
            handoff = maintenance.run_maintenance(self.root, "handoff")
            self.assertTrue((self.root / "93_exports/handoff_brief.md").is_file())
            self.assertEqual((self.root / "90_canon/canon.md").read_bytes(), before_audit)
        self.assertEqual((self.root / "_INBOX/notes.md").read_bytes(), original)
        self.assertEqual([row[1] for row in self.calls],
                         ["project_import", "project_update", "project_audit", "project_handoff"])
        self.assertIsInstance(handoff, dict)
        self._assert_no_real_transport()

    def test_interrupted_import_preserves_receipt_then_requires_session_for_recovery(self):
        original_replace = Path.replace
        def interrupted(path, target):
            if path.name.endswith(".import-tmp"):
                raise OSError("INTERRUPTED_OPERATION_FIXTURE")
            return original_replace(path, target)
        with self._session(), patch.object(Path, "replace", interrupted):
            with self.assertRaisesRegex(OSError, "INTERRUPTED_OPERATION_FIXTURE"):
                imports.run_import(self.root)
        pending = self.root / imports.PENDING
        journal = self.root / json.loads(pending.read_text())["journal"]
        run = journal.parent
        receipt_raw = (run / "run_state.json").read_bytes()
        before = (self.root / "90_canon/canon.md").read_bytes()
        source = self.root / "_INBOX/notes.md"
        source_raw = source.read_bytes()
        with self.assertRaisesRegex(ContractError, "LIVE_AUTHORIZATION_REQUIRED"):
            imports.run_import(self.root)
        self.assertEqual((self.root / "90_canon/canon.md").read_bytes(), before)
        self.assertEqual((run / "run_state.json").read_bytes(), receipt_raw)
        corrupt = runner.load_state(run)
        self._change_extra(corrupt["provider_requests"][0])
        runner.save_state(run, corrupt)
        request = json.loads((run / corrupt["provider_requests"][0]["request_path"]).read_text())
        with self._session():
            with self.assertRaisesRegex(ContractError, "OPERATION_SIMULATION_RECEIPT_BINDING_INVALID"):
                imports.run_import(self.root)
            with self.assertRaisesRegex(ContractError, "OPERATION_SIMULATION_RECEIPT_BINDING_INVALID"):
                imports._reconsume_bookkeeping_response(run, "project_import", request["messages"])
        self.assertEqual((self.root / "90_canon/canon.md").read_bytes(), before)
        (run / "run_state.json").write_bytes(receipt_raw)
        source.write_text("Changed fixture source after interruption.", encoding="utf-8")
        with self._session(), self.assertRaisesRegex(ContractError, "IMPORT_SOURCE_CHANGED"):
            imports.run_import(self.root)
        self.assertEqual((self.root / "90_canon/canon.md").read_bytes(), before)
        self.assertEqual((run / "run_state.json").read_bytes(), receipt_raw)
        source.write_bytes(source_raw)
        with self._session():
            self.assertEqual(imports.run_import(self.root)["status"], "INITIAL_IMPORT_COMPLETE")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual((run / "run_state.json").read_bytes(), receipt_raw)
        self.assertTrue((run / "COMMITTED").is_file())
        self.assertFalse(pending.exists())
        self._assert_no_real_transport()

    def test_maintenance_pending_and_latest_cache_never_publish_without_session(self):
        original_replace = Path.replace
        def interrupted(path, target):
            if path.name.endswith(".maintenance-tmp"):
                raise OSError("INTERRUPTED_MAINTENANCE_FIXTURE")
            return original_replace(path, target)
        with self._session(), patch.object(Path, "replace", interrupted):
            with self.assertRaisesRegex(OSError, "INTERRUPTED_MAINTENANCE_FIXTURE"):
                maintenance.run_maintenance(self.root, "audit")
        pending = self.root / maintenance.PENDING
        pending_raw = pending.read_bytes()
        with self.assertRaisesRegex(ContractError, "LIVE_AUTHORIZATION_REQUIRED"):
            maintenance.run_maintenance(self.root, "audit")
        self.assertEqual(pending.read_bytes(), pending_raw)
        with self._session():
            result = maintenance.run_maintenance(self.root, "audit")
            self.assertTrue(result["recovered"])
            again = maintenance.run_maintenance(self.root, "audit")
            self.assertEqual(again["provider_call"], "reused")
        snapshot = (self.root / "08_review/continuity_audit.md").read_bytes()
        with self.assertRaisesRegex(ContractError, "LIVE_AUTHORIZATION_REQUIRED"):
            maintenance.run_maintenance(self.root, "audit")
        self.assertEqual((self.root / "08_review/continuity_audit.md").read_bytes(), snapshot)
        self.assertEqual(len(self.calls), 1)
        self._assert_no_real_transport()

    def test_strict_markers_bindings_and_unique_record_reject_invalid_model_receipts(self):
        corruptions = {
            "live": lambda row, run: row.update(mode="LIVE"),
            "missing_marker": lambda row, run: row.pop("simulation_status"),
            "numeric_fixture": lambda row, run: row.update(fixture_only=1),
            "foreign_instance": lambda row, run: row.update(project_instance_id="another-instance"),
            "wrong_run": lambda row, run: row.update(run_id="other-run"),
            "wrong_stage": lambda row, run: row.update(stage="project_handoff"),
            "wrong_role": lambda row, run: row.update(role_id="project_handoff"),
            "wrong_request": lambda row, run: row.update(input_sha256="0" * 64),
            "wrong_output": lambda row, run: row.update(output_sha256="0" * 64),
            "wrong_extra": lambda row, run: self._change_extra(row),
            "unregistered": lambda row, run: row.update(_omit_registration=True),
            "duplicate_record": lambda row, run: row.update(_duplicate_registration=True),
        }
        with self._session():
            for name, mutate in corruptions.items():
                self.mutate = mutate
                run = self._run("maintenance", name=name)
                with self.subTest(name=name), self.assertRaises(ContractError):
                    self._call(run)
        self._assert_no_real_transport()

    def _change_extra(self, receipt):
        binding = {key: receipt[key] for key in ("project_instance_id", "project_id", "project_root",
            "run_id", "run_path", "stage", "role_id", "input_sha256", "output_cap", "request_extra")}
        binding["request_extra"] = {"self_reported_grant": True}
        receipt.update(binding)
        receipt["request_fingerprint"] = runner.sha(json.dumps(binding, ensure_ascii=False,
            sort_keys=True, separators=(",", ":")).encode())

    def test_bound_session_cannot_reach_foreign_instance_low_http_or_outlive_its_scope(self):
        run = self._run("maintenance")
        other = self._run("maintenance", root=self.other)
        with self._session():
            self.assertTrue(self._call(run)[0])
            with self.assertRaisesRegex(ContractError, "OPERATION_SIMULATION_SCOPE_MISMATCH"):
                self._call(other)
            with self.assertRaisesRegex(ContractError, "LIVE_AUTHORIZATION_REQUIRED"):
                runner._cnw_live_call_in_slot(run, stage="project_audit", role_id="project_audit", messages=[], output_cap=6000)
            with self.assertRaisesRegex(ContractError, "OPERATION_SIMULATION_NESTED"):
                with self._session():
                    pass
        with self.assertRaisesRegex(ContractError, "LIVE_AUTHORIZATION_REQUIRED"):
            self._call(run)
        with self.assertRaisesRegex(RuntimeError, "FIXTURE_EXCEPTION"):
            with self._session():
                raise RuntimeError("FIXTURE_EXCEPTION")
        self.assertIsNone(runner._OPERATION_SIMULATION.get())
        self.assertIsNone(runner._OPERATION_SIMULATION_REQUEST.get())
        self._assert_no_real_transport()

    def test_fixture_must_own_data_home_and_invalid_registry_never_falls_back(self):
        with tempfile.TemporaryDirectory(prefix="unrelated-operation-fixture-") as elsewhere:
            owner = tempfile.TemporaryDirectory(dir=elsewhere)
            self.addCleanup(owner.cleanup)
            with self.assertRaisesRegex(ContractError, "OPERATION_SIMULATION_FIXTURE_REQUIRED"):
                with runner._isolated_operation_transport(owner, data_home=self.home,
                        projects=[self.root], transport=self._record):
                    pass
        run = self._run("maintenance")
        identity = self.root / "project_identity.json"
        raw = identity.read_bytes()
        identity.write_text('{}', encoding="utf-8")
        try:
            with self.assertRaises(ContractError):
                self._call(run)
            with self.assertRaises(ContractError):
                imports.run_import(self.root)
        finally:
            identity.write_bytes(raw)
        state = runner.load_state(run)
        state["run_id"] = "wrong-directory"
        runner.save_state(run, state)
        # The pre-existing Run reader rejects this mismatch before operation routing.
        with self.assertRaisesRegex(ContractError, "RUN_IDENTITY_MISMATCH"):
            self._call(run)
        self._assert_no_real_transport()

    def test_cached_receipt_mutation_refuses_recovery_and_preserves_outputs(self):
        with self._session():
            maintenance.run_maintenance(self.root, "audit")
        latest = json.loads((self.root / "00_meta/maintenance_audit_state.json").read_text())
        run = (self.root / latest["journal"]).parent
        original = runner.load_state(run)
        before = (self.root / "08_review/continuity_audit.md").read_bytes()
        for kind in ("LIVE", "changed_extra"):
            state = copy.deepcopy(original)
            if kind == "LIVE":
                state["provider_requests"][0]["mode"] = "LIVE"
                expected = "OPERATION_SIMULATION_RECEIPT_INVALID"
            else:
                self._change_extra(state["provider_requests"][0])
                expected = "OPERATION_SIMULATION_RECEIPT_BINDING_INVALID"
            runner.save_state(run, state)
            with self.subTest(kind=kind), self._session(), self.assertRaisesRegex(ContractError, expected):
                maintenance.run_maintenance(self.root, "audit")
            self.assertEqual((self.root / "08_review/continuity_audit.md").read_bytes(), before)
        self.assertEqual(len(self.calls), 1)
        self._assert_no_real_transport()
