"""Read-only legacy path migration checks using synthetic temporary projects."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from tools.cnw_contract import ContractError
from tools import cnw_runner
from tools.cnw_runner import validate_literary_source_freeze
from tools.legacy_source_path_map import CATEGORIES, resolve_legacy_key, resolve_legacy_mapped_file, validate_legacy_source_path_map
from tools.project_paths import create_project, setup_data_home


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def changed_plot_builder(run_dir):
    return {"provider_call": "none", "fixture": "changed-builder"}


class LegacySourcePathMapTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="storystudio-legacy-map-")).resolve()
        self.data_home = self.temp / "data-home"
        setup_data_home(self.data_home, pointer_path=self.temp / "user-config" / "setup.json")
        registered = create_project(project_id="MAPTEST", display_name="Synthetic map test", data_home=self.data_home)
        self.project = Path(registered["project_root"])
        self.map_path = self.temp / "external-map.json"
        self.run = self.project / "runs" / "SYNTHETIC-LEGACY"
        (self.run / "artifacts").mkdir(parents=True)
        (self.project / "contracts").mkdir()
        (self.project / "_INBOX" / "legacy-snapshots").mkdir(parents=True)
        self.source_bytes = b"First fictional line.\nMiddle fictional line.\nLast fictional line.\n"
        self.manifest_bytes = b'{"schema_version":"synthetic_source_manifest_v1"}\n'
        (self.project / "_INBOX/legacy-snapshots/source.txt").write_bytes(self.source_bytes)
        (self.project / "_INBOX/legacy-snapshots/manifest.json").write_bytes(self.manifest_bytes)
        self.contract = {
            "schema_version": "cnw_work_unit_v1", "project_id": "MAPTEST",
            "unit": {"id": "SYNTHETIC-UNIT", "kind": "scene",
                     "policy_sha256": sha((Path(__file__).resolve().parents[1] / "config/cnw_production_policy.json").read_bytes())},
            "source": {"identity_type": "imported_project", "version": "SYNTHETIC-v1",
                       "import_id": "fixture-import-id", "source_file_sha256": sha(self.source_bytes),
                       "source_manifest_sha256": sha(self.manifest_bytes), "manifest_file": "_INBOX/source_manifest.json",
                       "source_revision_id": sha(self.source_bytes)},
            "story": {"source_file": "_INBOX/originals/source.txt",
                      "before_anchor": {"source_line": 1, "sha256": sha(b"First fictional line.\n")},
                      "after_anchor": {"source_line": 3, "sha256": sha(b"Last fictional line.\n")}},
        }
        contract_raw = json.dumps(self.contract, sort_keys=True).encode("utf-8")
        self.contract_path = self.project / "contracts/SYNTHETIC-UNIT.json"
        self.contract_path.write_bytes(contract_raw)
        run_contract = self.run / "artifacts/contract.json"
        run_contract.write_bytes(contract_raw)
        state = {"schema_version": "cnw_run_state_v1", "run_id": "SYNTHETIC-LEGACY",
                 "contract_path": "contracts/SYNTHETIC-UNIT.json", "contract_sha256": sha(contract_raw),
                 "workflow_template_sha256": sha(cnw_runner.WORKFLOW_PATH.read_bytes()),
                 "stages": {stage: {"status": "NOT_RUN"} for stage in cnw_runner.CNW_STAGES},
                 "literary_source_hashes": {
                     "source:workspace/legacy/source.txt": sha(self.source_bytes),
                     "manifest:workspace/legacy/source_manifest.json": sha(self.manifest_bytes),
                     "source:anchor_excerpt": sha(b"1: First fictional line.\n2: Middle fictional line.\n3: Last fictional line.")}}
        self.state_path = self.run / "run_state.json"
        self.state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
        self.state = state
        for relative, content in {
            "04_chapter_design/arc_01.md": "Fictional arc for preflight.\n",
            "90_canon/canon.md": "Fictional canon A.\n",
            "90_canon/character_bible.md": "Mira is fictional.\n",
            "94_runtime/current_state.md": "Fictional state.\n",
            "07_draft/manuscript_index.md": "Fictional manuscript index.\n",
            "04_chapter_design/arc_01_episode_details.md": "Fictional episode details.\n",
            "92_style_engine/character_voice_samples.md": "## Mira\nFictional sample.\n",
        }.items():
            target = self.project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        self._write_map()

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def _write_map(self, *, critics_unavailable=False):
        identity_raw = (self.project / "project_identity.json").read_bytes()
        categories = {}
        for category in CATEGORIES:
            if category == "CRITICS_RUNS_AND_NK_EVIDENCE" and critics_unavailable:
                categories[category] = {"status": "UNAVAILABLE", "reason": "synthetic fixture has no native evidence",
                                        "evidence_ref": "fixture:synthetic-no-native-evidence", "entries": []}
                continue
            categories[category] = {"status": "MAPPED", "entries": []}
        entries = [
            ("V5_PROJECT_ORIGINALS", "source:workspace/legacy/source.txt", "source.txt", self.source_bytes),
            ("V5_PROJECT_ORIGINALS", "manifest:workspace/legacy/source_manifest.json", "manifest.json", self.manifest_bytes),
        ]
        for index, category in enumerate(CATEGORIES[1:], start=1):
            if categories[category]["status"] == "UNAVAILABLE":
                continue
            relative = f"category-{index}.bin"
            raw = f"synthetic category {category}".encode()
            target = self.project / "_INBOX/legacy-snapshots" / relative
            target.write_bytes(raw)
            entries.append((category, f"{category}:synthetic-key", relative, raw))
        for category, key, relative, raw in entries:
            destination = "_INBOX/legacy-snapshots/" + relative
            categories[category]["entries"].append({"legacy_key": key, "source_type": "IMPORTED_PROJECT",
                "legacy_relative_path": relative, "target_project_relative_path": destination,
                "sha256": sha(raw), "bytes": len(raw)})
        repo = Path(__file__).resolve().parents[1]
        legacy_commit = "a00eb1a625f32dc7f0c527b286cbcef31543b794"
        def git_sha(path):
            raw = subprocess.run(["git", "show", f"{legacy_commit}:{path}"], cwd=repo,
                                 capture_output=True, check=True, timeout=20).stdout
            return sha(raw)
        implementation = {"commit_sha": legacy_commit,
            "code_files": [{"path": "tools/cnw_runner.py", "sha256": git_sha("tools/cnw_runner.py")}],
            "policy_files": [{"path": "config/cnw_production_policy.json", "sha256": git_sha("config/cnw_production_policy.json")}]}
        doc = {"schema_version": "legacy_source_path_map_v1", "map_id": "synthetic-map-id",
            "target_project": {"project_id": "MAPTEST", "project_instance_id": json.loads(identity_raw)["project_instance_id"],
                               "project_identity_sha256": sha(identity_raw)},
            "source_run": {"run_id": "SYNTHETIC-LEGACY", "run_state_sha256": sha(self.state_path.read_bytes()),
                "contract_path_in_run": "artifacts/contract.json", "contract_sha256": self.state["contract_sha256"],
                "source_manifest_sha256": sha(self.manifest_bytes),
                "source_file_legacy_key": "source:workspace/legacy/source.txt",
                "source_manifest_legacy_key": "manifest:workspace/legacy/source_manifest.json"},
            "legacy_implementation": implementation, "categories": categories}
        self.map_path.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")
        self.map_sha = sha(self.map_path.read_bytes())

    def test_exact_map_and_run_bindings_resolve_source_and_validate_old_freeze_read_only(self):
        before_state = self.state_path.read_bytes()
        before_contract = (self.run / "artifacts/contract.json").read_bytes()
        before_map = self.map_path.read_bytes()
        resolved = resolve_legacy_key(target_project_root=self.project, legacy_run_dir=self.run,
            manifest_path=self.map_path, expected_manifest_sha256=self.map_sha,
            legacy_key="source:workspace/legacy/source.txt", expected_file_sha256=sha(self.source_bytes))
        self.assertEqual(resolved.read_bytes(), self.source_bytes)
        validate_legacy_source_path_map(target_project_root=self.project, legacy_run_dir=self.run,
            manifest_path=self.map_path, expected_manifest_sha256=self.map_sha)
        validate_literary_source_freeze(self.state, self.project, legacy_run_dir=self.run,
            legacy_map_path=self.map_path, legacy_map_sha256=self.map_sha)
        result = cnw_runner.legacy_source_preflight(SimpleNamespace(
            project_root=str(self.project), run_id="SYNTHETIC-LEGACY",
            legacy_source_map=str(self.map_path), legacy_source_map_sha256=self.map_sha))
        self.assertEqual(result["status"], "V5_RESUME_PREFLIGHT_ELIGIBLE_WITHOUT_NETWORK")
        self.assertEqual(result["provider_call"], "none")
        plot_identity = result["prospective_plot_identity"]
        self.assertEqual(plot_identity["stage"], "plot")
        self.assertEqual(plot_identity["contract_sha256"], self.state["contract_sha256"])
        for key in ("input_sha256", "input_hashes", "message_sha256", "builder_sha256",
                    "workflow_sha256", "model", "api_url", "transport_sha256", "sha256"):
            self.assertTrue(plot_identity[key], key)
        # The selected migration API keeps the exact historical freeze keys.
        self.assertEqual(self.state_path.read_bytes(), before_state)
        self.assertEqual((self.run / "artifacts/contract.json").read_bytes(), before_contract)
        self.assertEqual(self.map_path.read_bytes(), before_map)

    def test_prospective_plot_identity_tracks_bound_input_and_builder_without_mutating_run(self):
        args = SimpleNamespace(project_root=str(self.project), run_id="SYNTHETIC-LEGACY",
            legacy_source_map=str(self.map_path), legacy_source_map_sha256=self.map_sha)
        first = cnw_runner.legacy_source_preflight(args)["prospective_plot_identity"]
        canon = self.project / "90_canon/canon.md"
        canon.write_text("Fictional canon B, changed bound Plot input.\n", encoding="utf-8")
        second = cnw_runner.legacy_source_preflight(args)["prospective_plot_identity"]
        self.assertNotEqual(first["input_sha256"], second["input_sha256"])
        with patch.object(cnw_runner, "execute_plot", changed_plot_builder):
            third = cnw_runner.legacy_source_preflight(args)["prospective_plot_identity"]
        self.assertNotEqual(second["builder_sha256"], third["builder_sha256"])
        self.assertEqual(self.state_path.read_bytes(), json.dumps(self.state, sort_keys=True).encode("utf-8"))

    def test_preflight_rejects_not_run_stage_with_execution_failure_evidence(self):
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        state["stages"]["plot"]["execution_failures"] = [{"status": "FAILED", "fixture": True}]
        self.state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
        self.state = state
        self._write_map()
        args = SimpleNamespace(project_root=str(self.project), run_id="SYNTHETIC-LEGACY",
            legacy_source_map=str(self.map_path), legacy_source_map_sha256=self.map_sha)
        with self.assertRaisesRegex(ContractError, "LEGACY_STAGE_IDENTITY_REVIEW_REQUIRED"):
            cnw_runner.legacy_source_preflight(args)

    def test_legacy_recovery_plan_preserves_incomplete_history_and_never_claims_eligibility(self):
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        state["status"] = "EXECUTION_INCOMPLETE"
        state["next_stage"] = "plot"
        state["stages"]["plot"].update(status="EXECUTION_INCOMPLETE",
            execution_failures=[{"error_type": "SyntheticTransportError", "error_code": "UNKNOWN_NOT_ZERO"}])
        state["provider_requests"] = [{"request_id": "SYNTHETIC-RECEIPT",
            "stage": "plot", "status": "UNKNOWN_NOT_ZERO", "cost_cny": None}]
        self.state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
        self.state = state
        self._write_map()
        args = SimpleNamespace(project_root=str(self.project), run_id="SYNTHETIC-LEGACY",
            legacy_source_map=str(self.map_path), legacy_source_map_sha256=self.map_sha)
        before_state = self.state_path.read_bytes()
        before_contract = (self.run / "artifacts/contract.json").read_bytes()
        before_project_contract = self.contract_path.read_bytes()
        result = cnw_runner.legacy_recovery_plan(args)
        self.assertEqual(result["status"], "V5_RECOVERY_REVIEW_REQUIRED")
        self.assertEqual(result["next_stage_candidate"], "plot")
        self.assertEqual(result["next_stage_identity_assessment"], "COMPUTED_OFFLINE")
        self.assertEqual(result["prospective_next_stage_identity"]["stage"], "plot")
        self.assertEqual(result["stage_history"][0]["stage"], "plot")
        self.assertEqual(result["stage_history"][0]["execution_failure_count"], 1)
        self.assertEqual(result["provider_receipt_history"]["counts_by_status"], {"UNKNOWN_NOT_ZERO": 1})
        self.assertEqual(result["provider_receipt_history"]["validation"], "PRESERVED_UNVERIFIED")
        self.assertEqual(result["cost_ledger"], "NOT_READ_RECONCILIATION_REQUIRED")
        self.assertEqual(result["resume_eligibility"], "NOT_ESTABLISHED")
        self.assertFalse(result["resume_executed"])
        self.assertEqual(result["provider_call"], "none")
        self.assertTrue(result["run_state_unchanged"])
        self.assertEqual(result["run_state_sha256_before"], result["run_state_sha256_after"])
        self.assertEqual(self.state_path.read_bytes(), before_state)
        self.assertEqual((self.run / "artifacts/contract.json").read_bytes(), before_contract)
        self.assertEqual(self.contract_path.read_bytes(), before_project_contract)
        with self.assertRaisesRegex(ContractError, "LEGACY_STAGE_IDENTITY_REVIEW_REQUIRED"):
            cnw_runner.legacy_source_preflight(args)

    def test_map_sha_path_traversal_and_missing_key_fail_closed(self):
        with self.assertRaisesRegex(ContractError, "LEGACY_SOURCE_MAP_SHA_MISMATCH"):
            validate_legacy_source_path_map(target_project_root=self.project, legacy_run_dir=self.run,
                manifest_path=self.map_path, expected_manifest_sha256="0" * 64)
        with self.assertRaisesRegex(ContractError, "LEGACY_SOURCE_MAP_ENTRY_MISSING"):
            resolve_legacy_key(target_project_root=self.project, legacy_run_dir=self.run,
                manifest_path=self.map_path, expected_manifest_sha256=self.map_sha,
                legacy_key="source:C:/untrusted/file.txt", expected_file_sha256=sha(self.source_bytes))
        doc = json.loads(self.map_path.read_text(encoding="utf-8"))
        doc["categories"]["V5_PROJECT_ORIGINALS"]["entries"][0]["target_project_relative_path"] = "../escape.txt"
        self.map_path.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")
        self.map_sha = sha(self.map_path.read_bytes())
        with self.assertRaisesRegex(ContractError, "LEGACY_SOURCE_MAP_INVALID"):
            validate_legacy_source_path_map(target_project_root=self.project, legacy_run_dir=self.run,
                manifest_path=self.map_path, expected_manifest_sha256=self.map_sha)

    def test_fixed_release_fallback_is_removed(self):
        legacy_release_contract = {"source": {"identity_type": None, "zip_sha256": "f" * 64}}
        with self.assertRaisesRegex(ContractError, "LEGACY_MIGRATION_REQUIRED"):
            cnw_runner._source_root(legacy_release_contract, self.project)

    def test_unavailable_category_is_explicit_and_cannot_be_resolved(self):
        self._write_map(critics_unavailable=True)
        doc, _, _ = validate_legacy_source_path_map(target_project_root=self.project, legacy_run_dir=self.run,
            manifest_path=self.map_path, expected_manifest_sha256=self.map_sha)
        self.assertEqual(doc["categories"]["CRITICS_RUNS_AND_NK_EVIDENCE"]["status"], "UNAVAILABLE")
        self.assertEqual(doc["categories"]["CRITICS_RUNS_AND_NK_EVIDENCE"]["entries"], [])
        with self.assertRaisesRegex(ContractError, "LEGACY_SOURCE_CATEGORY_UNAVAILABLE"):
            resolve_legacy_mapped_file(target_project_root=self.project, legacy_run_dir=self.run,
                manifest_path=self.map_path, expected_manifest_sha256=self.map_sha,
                category="CRITICS_RUNS_AND_NK_EVIDENCE", legacy_key="critics:unavailable",
                expected_file_sha256="f" * 64)


if __name__ == "__main__":
    unittest.main()
