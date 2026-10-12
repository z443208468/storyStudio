"""Package jobs prepare real offline Runs; no author stage or Provider executes."""
import copy
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from tests import test_cnw_pack_app as pack_fixtures
from tests.test_cnw_input_pack import encoded, sha
from tools import cnw_pack_app as app, cnw_runner
from tools.cnw_contract import ContractError


class PackageRunPreparationTests(unittest.TestCase):
    def setUp(self):
        self.helper = pack_fixtures.PackApplicationTests()
        self.helper.setUp()
        self.addCleanup(self.helper.tearDown)
        self.fixture = self.helper.fixture

    def imported(self):
        return app.import_package(self.fixture.pack, data_home=self.fixture.home,
                                  local_source=self.fixture.repo, offline=True)

    def prepare(self, report):
        with patch.object(cnw_runner, "cnw_live_call", side_effect=AssertionError("No Provider")):
            return app.prepare_package_runs(report["job_record"], data_home=self.fixture.home)

    def assert_prepared(self, report):
        self.assertEqual(report["status"], "RUNS_PREPARED_PENDING_AUTHORIZATION")
        self.assertEqual(len(report["tasks"]), 3)
        for task in report["tasks"]:
            preparation = task["run_preparation"]
            self.assertIs(preparation["provider_call_authorized"], False)
            self.assertEqual(preparation["controller_attestation_status"], "ATTESTATION_PENDING")
            self.assertEqual(preparation["live_authorization_status"], "NOT_AUTHORIZED")
            run = Path(preparation["run_path"])
            state = cnw_runner.load_state(run)
            self.assertEqual(state["run_id"], task["planned_run_id"])
            self.assertEqual(state["contract_sha256"], task["contract_sha256"])
            self.assertEqual(state["mode"], "offline")
            self.assertEqual(state["provider_requests"], [])
            self.assertEqual(state["next_stage"], "plot")
            self.assertFalse((run / "artifacts/plot.json").exists())
            raw = Path(preparation["record"]).read_bytes()
            self.assertEqual(sha(raw), preparation["record_sha256"])
            bindings = json.loads(raw)
            self.assertEqual(bindings["bindings"]["project_instance_id"], task["project_instance_id"])

    def test_actual_powershell_entry_then_repeat_preserves_runs_and_bindings(self):
        result = self.helper.invoke("-SourceRepository", str(self.fixture.repo), "-Offline", "-PrepareRuns")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        prepared = json.loads(result.stdout)
        self.assert_prepared(prepared)
        preserved = {str(path): path.read_bytes() for task in prepared["tasks"]
                     for path in Path(task["run_preparation"]["run_path"]).rglob("*") if path.is_file()}
        preserved.update({task["run_preparation"]["record"]: Path(task["run_preparation"]["record"]).read_bytes()
                          for task in prepared["tasks"]})
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        result = subprocess.run([self.helper.powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-File",
            str(pack_fixtures.ROOT / "tools/studio.ps1"), "project-pack", "-JobFile", prepared["job_record"],
            "-DataHome", str(self.fixture.home), "-Offline"], cwd=pack_fixtures.ROOT, env=env,
            capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        repeated = json.loads(result.stdout)
        self.assert_prepared(repeated)
        self.assertEqual(prepared["tasks"], repeated["tasks"])
        for name, raw in preserved.items():
            self.assertEqual(Path(name).read_bytes(), raw)
        history = Path(prepared["job_record"]).parent / "history"
        self.assertTrue(any(history.iterdir()))
        target = os.environ.get("ATOM07_EVIDENCE_OUTPUT")
        if target:
            Path(target).with_suffix(".jobs.json").write_bytes(encoded({"execution": "FICTIONAL_OFFLINE_NO_PROVIDER",
                "first": prepared, "repeated": repeated, "run_bytes_preserved": True}))

    def test_interruption_after_real_run_creation_rechecks_without_recreation(self):
        imported = self.imported()
        actual = cnw_runner.produce
        runs = []
        def interrupted(args):
            result = actual(args)
            runs.append(Path(result["path"]))
            raise OSError("SIMULATED_INTERRUPTION_AFTER_RUN_CREATE")
        with patch.object(cnw_runner, "produce", side_effect=interrupted), self.assertRaises(OSError):
            self.prepare(imported)
        preserved = {str(p): p.read_bytes() for p in runs[0].rglob("*") if p.is_file()}
        with patch.object(cnw_runner, "produce", wraps=actual) as create:
            final = self.prepare(imported)
        self.assertEqual(create.call_count, 2)
        self.assert_prepared(final)
        for name, raw in preserved.items():
            self.assertEqual(Path(name).read_bytes(), raw)

    def test_capacity_pending_stays_pending_and_creates_no_runs(self):
        self.helper.set_bounds(4701)
        imported = self.imported()
        with patch.object(cnw_runner, "produce", side_effect=AssertionError("No capacity validated")):
            result = self.prepare(imported)
        self.assertEqual(result["status"], "INPUTS_PREPARED_WITH_CAPACITY_PENDING")
        for task in result["tasks"]:
            self.assertEqual(task["status"], "CAPACITY_PENDING")
            self.assertFalse(any((Path(task["project_root"]) / "runs").iterdir()))

    def test_job_cross_task_contract_archive_and_legacy_origin_changes_reject(self):
        imported = self.imported()
        record = Path(imported["job_record"])
        original = record.read_bytes()
        for field, value in (("project_root", imported["tasks"][1]["project_root"]),
                ("project_instance_id", imported["tasks"][1]["project_instance_id"]),
                ("contract_sha256", "0" * 64), ("planned_run_id", "OTHER-RUN"),
                ("requested_max_visible_chars", 0)):
            altered = copy.deepcopy(imported); altered["tasks"][0][field] = value
            record.write_bytes(encoded(altered))
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, "JOB_BINDINGS_CHANGED"):
                self.prepare(altered)
            self.assertEqual(record.read_bytes(), encoded(altered))
        record.write_bytes(original)
        archive = record.parent / "input.zip"
        archive_raw = archive.read_bytes(); archive.write_bytes(archive_raw + b"tampered")
        with self.assertRaisesRegex(ContractError, "JOB_BINDINGS_CHANGED"):
            self.prepare(imported)
        archive.write_bytes(archive_raw)
        # A missing original record is not retrospectively invented.
        origin = record.parent / "origin.json"
        origin.rename(record.parent / "origin.saved.json")
        with self.assertRaisesRegex(ContractError, "JOB_ORIGIN_UNAVAILABLE"):
            self.prepare(imported)
        self.assertEqual(record.read_bytes(), original)
        for task in imported["tasks"]:
            self.assertFalse(any((Path(task["project_root"]) / "runs").iterdir()))

    def test_repeated_job_detects_tampered_existing_run_without_overwriting_it(self):
        report = self.prepare(self.imported())
        state_path = Path(report["tasks"][0]["run_preparation"]["run_path"]) / "run_state.json"
        state = json.loads(state_path.read_bytes()); state["run_id"] = "FOREIGN-RUN"
        modified = encoded(state); state_path.write_bytes(modified)
        job_raw = Path(report["job_record"]).read_bytes()
        with patch.object(cnw_runner, "produce", side_effect=AssertionError("Existing Run must not be replaced")), self.assertRaises(ContractError):
            self.prepare(report)
        self.assertEqual(state_path.read_bytes(), modified)
        self.assertEqual(Path(report["job_record"]).read_bytes(), job_raw)


if __name__ == "__main__":
    unittest.main()
