"""Real package CLI plus pinned-source acquisition and DataHome boundaries."""
from __future__ import annotations

import copy
import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import socketserver
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import test_cnw_input_pack as fixtures
from tests.test_cnw_input_pack import encoded, sha
from tools import cnw_pack_app as app
from tools.cnw_contract import ContractError
from tools.cnw_runner import build_plot_request


ROOT = Path(__file__).resolve().parents[1]


class PackApplicationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.InputPackTests()
        self.fixture.setUp()
        for label in ("A", "B", "C"):
            self.fixture.files[f"scenes/{label}/project_seed/00_meta/OUTPUT_REQUIREMENTS.md"] = (
                "# Output responsibilities\n| Role | Sources | Duty |\n|---|---|---|\n"
                f"| Story-specific Lens | Canon + prose | Check local promise {label} and its exact boundary. |\n").encode()
        self.fixture.write_pack()
        self.powershell = shutil.which("pwsh") or shutil.which("powershell")

    def tearDown(self):
        self.fixture.tearDown()

    def invoke(self, *extra):
        if not self.powershell:
            self.fail("PowerShell is required for this Windows application entry check")
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        for key in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "STORYSTUDIO_W10_PREFLIGHT_PATH"):
            env.pop(key, None)
        return subprocess.run([self.powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-File",
                               str(ROOT / "tools/studio.ps1"), "project-pack", "-InputFile", str(self.fixture.pack),
                               "-DataHome", str(self.fixture.home), *extra],
                              env=env, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120)

    def test_powershell_package_entry_creates_all_isolated_tasks(self):
        original_repo = {p.relative_to(self.fixture.repo).as_posix(): sha(p.read_bytes()) for p in self.fixture.repo.rglob("*") if p.is_file()}
        pointer_before = (self.fixture.base / "pointer.json").read_bytes()
        first = self.invoke("-SourceRepository", str(self.fixture.repo), "-Offline")
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        result = json.loads(first.stdout)
        self.assertEqual(result["status"], "CONTRACTS_READY_FOR_PREFLIGHT")
        self.assertEqual(len(result["tasks"]), 3)
        self.assertEqual(len({t["project_instance_id"] for t in result["tasks"]}), 3)
        for label, task in zip(("A", "B", "C"), result["tasks"]):
            self.assertEqual(task["status"], "CONTRACT_READY_FOR_PREFLIGHT")
            self.assertEqual(task["preflight"]["status"], "OFFLINE_BINDINGS_VALIDATED")
            self.assertFalse(task["preflight"]["provider_call_authorized"])
            root = Path(task["project_root"])
            contract = json.loads(Path(task["contract"]).read_text(encoding="utf-8"))
            self.assertEqual(contract["review"]["fifth_lens"]["responsibility"], f"Check local promise {label} and its exact boundary.")
            derivation = task["fifth_lens_derivation"]
            self.assertEqual(derivation["locator"], {"line": 4})
            self.assertEqual(derivation["source_sha256"], sha((root / "00_meta/OUTPUT_REQUIREMENTS.md").read_bytes()))
            draft = json.loads(Path(task["draft"]).read_text(encoding="utf-8"))
            self.assertEqual(draft["custom_future_requirement"]["exact_number"], ord(label)-ord("A")+1)
            request = build_plot_request(root, contract)
            self.assertIn(f"SELECTED-ARC-{label}", json.dumps(request["messages"]))
            manifest = json.loads((root / contract["source"]["manifest_file"]).read_text(encoding="utf-8"))
            source = next(s for s in manifest["sources"] if s["source_id"] == contract["source"]["source_id"])
            # Windows TEMP may be an 8.3 spelling (ADMINI~1); registration
            # records the canonical long DataHome path.
            self.assertTrue(Path(source["original_path"]).is_relative_to(self.fixture.home.resolve()))
        before = {p.relative_to(self.fixture.home).as_posix(): sha(p.read_bytes()) for p in self.fixture.home.rglob("*") if p.is_file()}
        second = self.invoke("-SourceRepository", str(self.fixture.repo), "-Offline")
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        repeated = json.loads(second.stdout)
        self.assertFalse({t["project_instance_id"] for t in result["tasks"]} & {t["project_instance_id"] for t in repeated["tasks"]})
        for name, digest in before.items():
            self.assertEqual(sha((self.fixture.home / name).read_bytes()), digest)
        self.assertEqual(pointer_before, (self.fixture.base / "pointer.json").read_bytes())
        self.assertEqual(original_repo, {p.relative_to(self.fixture.repo).as_posix(): sha(p.read_bytes()) for p in self.fixture.repo.rglob("*") if p.is_file()})
        target = os.environ.get("ATOM04_PACK_APP_EVIDENCE_OUTPUT")
        if target:
            Path(target).write_bytes(encoded({"execution": "FICTIONAL_OFFLINE_NO_PROVIDER", "first": result, "repeat": repeated,
                                             "source_repo_unchanged": True, "global_pointer_unchanged": True}))

    def test_execute_job_requires_explicit_model_mode_not_source_offline_switch(self):
        result = self.invoke("-SourceRepository", str(self.fixture.repo), "-Offline", "-ExecuteJob")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PROJECT_PACK_EXECUTE_JOB_REQUIRES_MODE_OFFLINE_OR_LIVE", result.stderr + result.stdout)
        self.assertFalse((self.fixture.home / "projects").exists())

    def test_live_model_intent_is_not_downgraded_to_offline_or_sent(self):
        result = self.invoke("-SourceRepository", str(self.fixture.repo), "-Offline", "-Mode", "live", "-ExecuteJob")
        self.assertNotEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "JOB_EXECUTION_INCOMPLETE")
        self.assertEqual(report["requested_execution_mode"], "live")
        self.assertTrue(report["job_record"].endswith("result.json"))
        self.assertEqual(report["blocking_code"], "LIVE_AUTHORIZATION_REQUIRED")
        self.assertEqual(report["provider_request_count"], 0)
        self.assertEqual(report["fee_reservation_count"], 0)
        self.assertEqual(report["provider_call"], "none")
        self.assertTrue(Path(report["attempt_record"]).is_file())
        self.assertNotEqual(report["attempt_record"], report["job_record"])

    def set_bounds(self, maximum):
        for label in ("A", "B", "C"):
            name = f"scenes/{label}/work_order.draft.json"
            value = json.loads(self.fixture.files[name]); value.update(target_visible_chars=3100, min_visible_chars=2200, max_visible_chars=maximum)
            self.fixture.files[name] = encoded(value)
            name = f"scenes/{label}/project_seed/config/project.yml"
            self.fixture.files[name] = self.fixture.files[name].replace(b": 90\n", b": 3100\n").replace(b": 60\n", b": 2200\n").replace(b": 120\n", f": {maximum}\n".encode())
        self.fixture.write_pack()

    def test_powershell_4700_creates_bounded_contracts_without_creating_runs(self):
        self.set_bounds(4700)
        result = self.invoke("-SourceRepository", str(self.fixture.repo), "-Offline")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "CONTRACTS_READY_FOR_PREFLIGHT")
        for task in report["tasks"]:
            self.assertEqual(task["status"], "CONTRACT_READY_FOR_PREFLIGHT")
            contract = json.loads(Path(task["contract"]).read_text(encoding="utf-8"))
            self.assertEqual(tuple(contract["unit"][k] for k in ("min_visible_chars", "target_visible_chars", "max_visible_chars")), (2200, 3100, 4700))
            self.assertFalse(task["preflight"]["provider_call_authorized"])
            self.assertFalse(any((Path(task["project_root"]) / "runs").iterdir()))
        self.assertEqual(report["provider_call"], "none")
        self.assertEqual(report["production_status"], "NOT_AUTHORIZED")

    def test_powershell_unvalidated_capacity_is_preserved_without_creating_runs(self):
        self.set_bounds(4701)
        result = self.invoke("-SourceRepository", str(self.fixture.repo), "-Offline")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "INPUTS_PREPARED_WITH_CAPACITY_PENDING")
        for task in report["tasks"]:
            self.assertEqual(task["status"], "CAPACITY_PENDING")
            self.assertEqual(task["blocking_code"], "UNIT_CAPACITY_UNVALIDATED")
            self.assertEqual(json.loads(Path(task["draft"]).read_text(encoding="utf-8"))["max_visible_chars"], 4701)
            self.assertFalse(any((Path(task["project_root"]) / "runs").iterdir()))
        self.assertEqual(report["provider_call"], "none")
        self.assertEqual(report["production_status"], "NOT_AUTHORIZED")

    def test_missing_offline_objects_wrong_blob_and_occupied_home_fail_before_registration(self):
        pack = app.read_input_pack(self.fixture.pack)
        home = self.fixture.home
        with patch.object(app, "_git", side_effect=AssertionError("Network/git acquisition forbidden in Offline")):
            with self.assertRaisesRegex(ContractError, "SOURCE_OBJECT_MISSING_OFFLINE"):
                app.import_package(self.fixture.pack, data_home=home, offline=True)
        self.assertFalse((home / "projects").exists())
        files = copy.deepcopy(self.fixture.files)
        order = json.loads(files["scenes/A/work_order.draft.json"]); order["original_authority"]["blob_sha1"] = "0"*40
        files["scenes/A/work_order.draft.json"] = encoded(order)
        self.fixture.write_pack(files)
        with self.assertRaisesRegex(ContractError, "PINNED_SOURCE_BLOB_MISMATCH"):
            app.import_package(self.fixture.pack, data_home=home, local_source=self.fixture.repo, offline=True)
        self.assertFalse((home / "projects").exists())
        occupied = self.fixture.base / "other-application"
        occupied.mkdir(); (occupied / "unrelated.txt").write_bytes(b"Preserve unrelated contents.")
        # Use normal permission preparation solely on this fictional directory.
        from tools.project_paths import _windows_private_acl
        if os.name == "nt": _windows_private_acl(occupied, create=True)
        else: occupied.chmod(0o700)
        self.fixture.write_pack()
        with self.assertRaisesRegex(ContractError, "DATA_HOME_OCCUPIED"):
            app.import_package(self.fixture.pack, data_home=occupied, local_source=self.fixture.repo, offline=True)
        self.assertEqual(list(occupied.iterdir()), [occupied / "unrelated.txt"])
        self.assertEqual((occupied / "unrelated.txt").read_bytes(), b"Preserve unrelated contents.")

    def test_cached_source_transfer_is_pinned_and_offline_reuses_without_transport(self):
        home = app._home(self.fixture.home)
        order = json.loads(self.fixture.files["scenes/A/work_order.draft.json"])
        authority = order["original_authority"]
        git_calls = []
        actual_git = app._git
        def local_transfer(args, *, cwd):
            git_calls.append(list(args))
            if args[0] == "fetch":
                # Only the network transfer is replaced; native Git still
                # persists the exact fictional objects and the app verifies them.
                self.assertEqual(args[-2], "https://github.com/synthetic/source.git")
                source = self.fixture.repo.resolve(strict=True)
                destination = Path(cwd).resolve(strict=True)
                hooks = self.fixture.base.resolve(strict=True) / "transfer-empty-hooks"
                hooks.mkdir(exist_ok=True)
                command = [shutil.which("git"), "-c", "protocol.allow=never", "-c", "protocol.file.allow=always",
                           "-c", "core.hooksPath=" + str(hooks), "-c", "submodule.recurse=false",
                           "-c", "fetch.recurseSubmodules=false", "-C", str(destination), "fetch",
                           "--no-tags", "--depth=1", "--no-write-fetch-head", "--no-recurse-submodules",
                           str(source), args[-1]]
                system_keys = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP",
                               "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"}
                env = {k: v for k, v in os.environ.items() if k.upper() in system_keys}
                env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                           GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
                # Optional external verification guard. No production code
                # imports it or obtains Provider permission from this scope.
                guard = sys.modules.get("sitecustomize")
                permit = getattr(guard, "fixture_git_transfer", None)
                scope = (permit(self.fixture.temp, source, destination, args[-1], command, env)
                         if permit else contextlib.nullcontext())
                with scope:
                    return subprocess.run(command, env=env, capture_output=True, timeout=60)
            return actual_git(args, cwd=cwd)
        with patch.object(app, "_git", side_effect=local_transfer):
            cached = app.source_repository(home, authority, local=None, offline=False)
        self.assertEqual(sum(args[0] == "fetch" for args in git_calls), 1)
        with patch.object(app, "_git", side_effect=AssertionError("Offline must never acquire objects")):
            self.assertEqual(app.source_repository(home, authority, local=None, offline=True), cached)
        marker = cached.parent / "source_cache_identity.json"
        marker.write_bytes(encoded({"schema_version": "cnw_input_source_cache_v1", "url": "https://github.com/wrong/source.git", "commit": authority["commit"]}))
        with self.assertRaisesRegex(ContractError, "INPUT_SOURCE_CACHE_IDENTITY_MISMATCH"):
            app.source_repository(home, authority, local=None, offline=True)
        self.assertTrue(cached.exists())

    def test_partial_clone_reads_cannot_lazy_fetch_and_tree_is_not_a_commit(self):
        from tools import cnw_input_pack as adapter
        order = json.loads(self.fixture.files["scenes/A/work_order.draft.json"])
        original_run = subprocess.run
        calls = []
        def guarded(command, **options):
            calls.append(command)
            self.assertIn("protocol.allow=never", command)
            self.assertEqual(options["env"]["GIT_NO_LAZY_FETCH"], "1")
            return original_run(command, **options)
        with patch.object(adapter.subprocess, "run", side_effect=guarded):
            adapter._source_bytes(self.fixture.repo, order["original_authority"])
        self.assertTrue(calls)
        wrong = dict(order["original_authority"])
        wrong["commit"] = subprocess.check_output(["git", "-C", str(self.fixture.repo), "rev-parse", "HEAD^{tree}"]).decode().strip()
        with self.assertRaisesRegex(ContractError, "INPUT_PACK_AUTHORITY_INVALID"):
            adapter._source_bytes(self.fixture.repo, wrong)

    def test_lens_duties_are_derived_from_explicit_sources_and_ambiguity_rejects(self):
        pack = app.read_input_pack(self.fixture.pack)
        lens = app.derive_fifth_lens(pack, "scenes/A")
        self.assertEqual(lens["derivation"]["locator"], {"line": 4})
        pack["files"]["scenes/A/project_seed/00_meta/OUTPUT_REQUIREMENTS.md"] += b"| Story-specific Lens | Canon | conflicting duty |\n"
        with self.assertRaisesRegex(ContractError, "MISSING_OR_AMBIGUOUS"):
            app.derive_fifth_lens(pack, "scenes/A")
        for name, duty in (("config/project_policy.v1.json", "Approved duty A"), ("config/policies/project_policy.v1.json", "Approved duty B")):
            pack["files"]["scenes/A/project_seed/"+name] = encoded({"schema_version": "storystudio_project_policy_v1", "review": {"fifth_lens": {"id": "custom", "responsibility": duty}}})
        with self.assertRaisesRegex(ContractError, "DUTIES_CONFLICT"):
            app.derive_fifth_lens(pack, "scenes/A")

    def test_task_count_comes_from_the_index_and_interruption_keeps_registered_progress(self):
        files = copy.deepcopy(self.fixture.files)
        for label in ("B", "C"):
            files.pop(f"scenes/{label}/work_order.draft.json")
        files["workpack_index.json"] = encoded({"schema": "cnw_workpack_index_v1", "workpacks": [{"root": "scenes/A/project_seed"}]})
        self.fixture.write_pack(files)
        single = app.import_package(self.fixture.pack, data_home=self.fixture.home, local_source=self.fixture.repo, offline=True)
        self.assertEqual(len(single["tasks"]), 1)
        preserved = {p.relative_to(self.fixture.home).as_posix(): sha(p.read_bytes()) for p in self.fixture.home.rglob("*") if p.is_file()}
        actual_open = Path.open
        def interrupted_write(path, *args, **kwargs):
            mode = args[0] if args else kwargs.get("mode", "r")
            if mode == "xb" and "input_packs" in path.parts and path.name == "work_order.draft.json":
                raise OSError("SIMULATED_DISK_WRITE_FAILURE")
            return actual_open(path, *args, **kwargs)
        with patch.object(Path, "open", interrupted_write):
            failed = app.import_package(self.fixture.pack, data_home=self.fixture.home, local_source=self.fixture.repo, offline=True)
        self.assertEqual(failed["status"], "IMPORT_INCOMPLETE")
        self.assertEqual(failed["error_type"], "OSError")
        self.assertTrue(Path(failed["tasks"][0]["project_root"]).is_dir())
        self.assertTrue(Path(failed["job_record"]).is_file())
        for name, digest in preserved.items():
            self.assertEqual(sha((self.fixture.home / name).read_bytes()), digest)

    def test_partial_clone_missing_blob_cannot_contact_network_in_offline_mode(self):
        contacts = []
        class Trap(socketserver.BaseRequestHandler):
            def handle(self):
                contacts.append(True)
                self.request.sendall(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
        server = socketserver.TCPServer(("127.0.0.1", 0), Trap)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        order = json.loads(self.fixture.files["scenes/A/work_order.draft.json"])
        repo = self.fixture.repo
        for key, value in (("core.repositoryformatversion", "1"), ("extensions.partialClone", "origin"),
                           ("remote.origin.promisor", "true"), ("remote.origin.url", f"http://127.0.0.1:{server.server_address[1]}/source.git")):
            subprocess.run(["git", "-C", str(repo), "config", "--local", key, value], check=True, capture_output=True)
        blob = self.fixture.blob
        object_path = repo / ".git/objects" / blob[:2] / blob[2:]
        saved = self.fixture.base / "held-source-blob"
        object_path.rename(saved)
        try:
            with self.assertRaisesRegex(ContractError, "SOURCE_OBJECT_MISSING_OFFLINE"):
                app.source_repository(self.fixture.home, order["original_authority"], local=repo, offline=True)
            self.assertEqual(contacts, [])
        finally:
            saved.rename(object_path)
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_failed_fetch_is_retained_and_incomplete_cache_is_refused(self):
        home = app._home(self.fixture.home)
        authority = json.loads(self.fixture.files["scenes/A/work_order.draft.json"])["original_authority"]
        actual = app._git
        def failed_transfer(args, *, cwd):
            return subprocess.CompletedProcess(args, 1, b"", b"SIMULATED SOURCE FETCH FAILURE") if args[0] == "fetch" else actual(args, cwd=cwd)
        with patch.object(app, "_git", side_effect=failed_transfer):
            with self.assertRaisesRegex(ContractError, "INPUT_SOURCE_FETCH_FAILED"):
                app.source_repository(home, authority, local=None, offline=False)
        caches = list((home / "tool_cache/input_sources").iterdir())
        self.assertEqual(len(caches), 1)
        attempts = list((caches[0] / "fetch_attempts").glob("*.json"))
        self.assertEqual(json.loads(attempts[0].read_text(encoding="utf-8"))["status"], "FETCH_FAILED")
        head = caches[0] / "objects.git/HEAD"
        backup = self.fixture.base / "held-cache-head"
        head.rename(backup)
        try:
            with patch.object(app, "_git", side_effect=AssertionError("corrupt cache must not fetch")):
                with self.assertRaisesRegex(ContractError, "INPUT_SOURCE_CACHE_INCOMPLETE"):
                    app.source_repository(home, authority, local=None, offline=False)
        finally:
            backup.rename(head)


if __name__ == "__main__":
    unittest.main()
