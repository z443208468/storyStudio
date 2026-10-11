"""Offline path-scope regressions for CritiCS in registered projects."""
from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from tools import critics_bridge, cnw_w10_critics, p2_06_critics_run, p2_cost_guard
from tools.project_paths import create_project, setup_data_home


class CriticsBridgeDataHomeTests(unittest.TestCase):
    def test_registered_project_inputs_and_run_output_are_scoped_to_instance(self):
        with tempfile.TemporaryDirectory(prefix="critics-data-home-") as temp_name:
            temp = Path(temp_name).resolve()
            data_home = temp / "selected-data-home"
            setup_data_home(data_home, pointer_path=temp / "setup.json")
            registration = create_project(project_id="CRITICS-SYNTHETIC", data_home=data_home)
            project = Path(registration["project_root"])
            runs = project / "runs"
            runs.mkdir()
            source = project / "drafts" / "synthetic.md"
            source.parent.mkdir()
            source.write_text("fictional test input", encoding="utf-8")

            self.assertEqual(critics_bridge.project_path(str(source)), source.resolve())

            candidate = runs / "SYNTHETIC-CRITICS"
            self.assertEqual(critics_bridge.project_path(str(candidate), directory=True), candidate)
            self.assertEqual(critics_bridge.create_run_directory(candidate), candidate.resolve())
            self.assertTrue(candidate.is_dir())
            parent_run = runs / "SYNTHETIC-PARENT-RUN"
            parent_run.mkdir()
            evidence_root, critics_run = cnw_w10_critics._critics_run_path(parent_run, "plan-critique")
            self.assertEqual(evidence_root, project)
            self.assertEqual(critics_run, runs / "SYNTHETIC-PARENT-RUN-critics-plan-critique")

            unregistered = temp / "projects" / "unregistered" / "draft.md"
            unregistered.parent.mkdir(parents=True)
            unregistered.write_text("not an application project", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "INPUT_MUST_BE_UNDER_PRIVATE_WORKSPACE_OR_REGISTERED_PROJECT"):
                critics_bridge.project_path(str(unregistered))
            unsafe_run = unregistered.parent / "runs" / "UNREGISTERED"
            with self.assertRaisesRegex(ValueError, "RUN_DIR_MUST_BE_UNDER_REGISTERED_RUNS"):
                critics_bridge.project_path(str(unsafe_run), directory=True)
            with self.assertRaisesRegex(ValueError, "RUNS_ROOT_NOT_REGISTERED"):
                critics_bridge.create_run_directory(unsafe_run)
            self.assertFalse(unsafe_run.exists())

    def test_p2_runner_honors_explicit_registered_run_directory(self):
        with tempfile.TemporaryDirectory(prefix="critics-run-route-") as temp_name:
            temp = Path(temp_name).resolve()
            data_home = temp / "selected-data-home"
            setup_data_home(data_home, pointer_path=temp / "setup.json")
            registration = create_project(project_id="CRITICS-RUN-ROUTE", data_home=data_home)
            project = Path(registration["project_root"])
            (project / "runs").mkdir()
            source = project / "source.md"
            source.write_text("fictional isolated input", encoding="utf-8")
            target = project / "runs" / "SYNTHETIC-CRITICS-RUN"
            ledger = temp / "ledger.json"
            ledger.write_text(json.dumps({"requests": []}), encoding="utf-8")
            observed = {}

            def create_bridge_run(command):
                observed["command"] = command
                parsed_dir = command[command.index("--run-dir") + 1]
                self.assertEqual(Path(parsed_dir), target)
                critics_bridge.create_run_directory(parsed_dir)
                return 0

            with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "synthetic-offline-test-key"}), \
                 patch.object(p2_cost_guard, "LEDGER", ledger), \
                 patch.object(p2_06_critics_run.critics_bridge, "main", side_effect=create_bridge_run):
                result = p2_06_critics_run.main(["--action", "plan-critique", "--input", str(source),
                    "--run-dir", str(target), "--ledger-run-id", "SYNTHETIC-PARENT"])

            self.assertEqual(result, 0)
            self.assertTrue(target.is_dir())
            self.assertTrue((target / "provider-calls.json").is_file())
            self.assertFalse((Path(p2_06_critics_run.ROOT) / "runs" / target.name).exists())


if __name__ == "__main__":
    unittest.main()
