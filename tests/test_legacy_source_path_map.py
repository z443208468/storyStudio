"""Read-only legacy path migration checks using synthetic temporary projects."""
from __future__ import annotations

import hashlib
import base64
import json
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from tools.cnw_contract import ContractError
from tools import cnw_runner, cnw_w10_policy
from tools.cnw_runner import validate_literary_source_freeze
from tools.legacy_source_path_map import (CATEGORIES, EXTERNAL_SCHEMA_VERSION,
    legacy_external_project_instance_id, resolve_legacy_key,
    resolve_legacy_mapped_file, validate_legacy_source_path_map)
from tools.project_paths import create_project, setup_data_home


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_sha(value) -> str:
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8"))


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

    def test_original_run_state_snapshot_allows_only_stable_identity_after_run_advances(self):
        snapshot = self.temp / "external-original-run-state.json"
        original = self.state_path.read_bytes()
        snapshot.write_bytes(original)
        current = json.loads(original.decode("utf-8"))
        current["stages"]["plot"]["status"] = "EXECUTION_INCOMPLETE"
        current["execution_failures"] = [{"stage": "plot", "code": "SYNTHETIC_FAILURE"}]
        advanced = json.dumps(current, sort_keys=True).encode("utf-8")
        self.state_path.write_bytes(advanced)

        with self.assertRaisesRegex(ContractError, "LEGACY_SOURCE_MAP_RUN_IDENTITY_MISMATCH"):
            validate_legacy_source_path_map(target_project_root=self.project, legacy_run_dir=self.run,
                manifest_path=self.map_path, expected_manifest_sha256=self.map_sha)

        before_current = self.state_path.read_bytes()
        validate_legacy_source_path_map(target_project_root=self.project, legacy_run_dir=self.run,
            manifest_path=self.map_path, expected_manifest_sha256=self.map_sha,
            original_run_state_path=snapshot)
        self.assertEqual(self.state_path.read_bytes(), before_current)
        self.assertEqual(snapshot.read_bytes(), original)

        altered_snapshot = json.loads(original.decode("utf-8"))
        altered_snapshot["unrelated_synthetic_field"] = "tampered"
        snapshot.write_text(json.dumps(altered_snapshot, sort_keys=True), encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "LEGACY_SOURCE_MAP_RUN_IDENTITY_MISMATCH"):
            validate_legacy_source_path_map(target_project_root=self.project, legacy_run_dir=self.run,
                manifest_path=self.map_path, expected_manifest_sha256=self.map_sha,
                original_run_state_path=snapshot)

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

    def test_legacy_recovery_plan_rejects_run_state_changed_during_source_validation(self):
        args = SimpleNamespace(project_root=str(self.project), run_id="SYNTHETIC-LEGACY",
            legacy_source_map=str(self.map_path), legacy_source_map_sha256=self.map_sha)
        original_validate = cnw_runner.validate_literary_source_freeze

        def mutate_after_validation(*call_args, **call_kwargs):
            result = original_validate(*call_args, **call_kwargs)
            self.state_path.write_bytes(self.state_path.read_bytes() + b"\n")
            return result

        with patch.object(cnw_runner, "validate_literary_source_freeze", side_effect=mutate_after_validation):
            with self.assertRaisesRegex(ContractError, "LEGACY_RUN_MUTATED_DURING_READ"):
                cnw_runner.legacy_recovery_plan(args)

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

    def test_external_legacy_identity_map_supports_v1_without_creating_identity_or_resume(self):
        external_root = self.temp / "legacy-v5-project"
        shutil.copytree(self.project, external_root)
        (external_root / "project_identity.json").unlink()
        external_run = external_root / "runs" / "SYNTHETIC-LEGACY"
        external_state = external_run / "run_state.json"
        external_contract = external_run / "artifacts/contract.json"
        state_raw = external_state.read_bytes()
        contract_raw = external_contract.read_bytes()
        contract = json.loads(contract_raw)
        manifest_sha = contract["source"]["source_manifest_sha256"]
        project_id = contract["project_id"]
        instance_id = legacy_external_project_instance_id(project_root=external_root,
            project_id=project_id)
        self.assertEqual(instance_id, legacy_external_project_instance_id(
            project_root=external_root, project_id=project_id))
        self.assertNotEqual(instance_id, legacy_external_project_instance_id(
            project_root=external_root, project_id=project_id + "-different-instance"))
        categories = {}
        for category in CATEGORIES:
            categories[category] = {"status": "UNAVAILABLE",
                "reason": "synthetic legacy fixture does not contain this external dependency",
                "evidence_ref": f"fixture:unavailable:{category}", "entries": []}
        categories["V5_PROJECT_ORIGINALS"] = {"status": "MAPPED", "entries": [
            {"legacy_key": "source:workspace/legacy/source.txt", "source_type": "IMPORTED_PROJECT",
             "legacy_relative_path": "workspace/legacy/source.txt",
             "target_project_relative_path": "_INBOX/legacy-snapshots/source.txt",
             "sha256": sha(self.source_bytes), "bytes": len(self.source_bytes)},
            {"legacy_key": "manifest:workspace/legacy/source_manifest.json", "source_type": "SOURCE_MANIFEST",
             "legacy_relative_path": "workspace/legacy/source_manifest.json",
             "target_project_relative_path": "_INBOX/legacy-snapshots/manifest.json",
             "sha256": sha(self.manifest_bytes), "bytes": len(self.manifest_bytes)},
        ]}
        map_doc = {"schema_version": EXTERNAL_SCHEMA_VERSION, "map_id": "synthetic-external-map",
            "target_project": {"identity_kind": "LEGACY_EXTERNAL_V1",
                "legacy_project_root": str(external_root.resolve()), "project_id": project_id,
                "project_instance_id": instance_id,
                "legacy_identity_binding": {"run_id": "SYNTHETIC-LEGACY",
                    "contract_sha256": sha(contract_raw), "source_manifest_sha256": manifest_sha,
                    "run_state_sha256": sha(state_raw)}},
            "source_run": {"run_id": "SYNTHETIC-LEGACY", "run_state_sha256": sha(state_raw),
                "contract_path_in_run": "artifacts/contract.json", "contract_sha256": sha(contract_raw),
                "source_manifest_sha256": manifest_sha,
                "source_file_legacy_key": "source:workspace/legacy/source.txt",
                "source_manifest_legacy_key": "manifest:workspace/legacy/source_manifest.json"},
            "legacy_implementation": {"status": "UNRECORDED", "commit_sha": None,
                "code_files": [], "policy_files": [],
                "reason": "synthetic historical run did not record a StoryStudio application commit"},
            "categories": categories}
        map_path = self.temp / "external-legacy-map.json"
        map_path.write_text(json.dumps(map_doc, sort_keys=True), encoding="utf-8")
        map_sha = sha(map_path.read_bytes())
        args = SimpleNamespace(project_root=str(external_root), run_id="SYNTHETIC-LEGACY",
            legacy_source_map=str(map_path), legacy_source_map_sha256=map_sha)
        before = {"state": external_state.read_bytes(), "contract": external_contract.read_bytes(),
            "project_contract": (external_root / "contracts/SYNTHETIC-UNIT.json").read_bytes()}
        result = cnw_runner.legacy_recovery_plan(args)
        self.assertEqual(result["status"], "V5_RECOVERY_REVIEW_REQUIRED")
        self.assertEqual(result["project_instance_id"], instance_id)
        self.assertEqual(result["project_identity_kind"], "LEGACY_EXTERNAL_MAPPED")
        self.assertEqual(result["legacy_implementation_identity"], "UNRECORDED")
        self.assertEqual(result["resume_eligibility"], "NOT_ESTABLISHED")
        self.assertEqual(result["provider_call"], "none")
        self.assertFalse((external_root / "project_identity.json").exists())
        self.assertEqual(before["state"], external_state.read_bytes())
        self.assertEqual(before["contract"], external_contract.read_bytes())
        self.assertEqual(before["project_contract"], (external_root / "contracts/SYNTHETIC-UNIT.json").read_bytes())

        original_state_path = self.temp / "external-original-state-snapshot.json"
        original_state_path.write_bytes(state_raw)
        controller_evidence = self.temp / "synthetic-controller-review.json"
        controller_ref = "SYNTHETIC-W10-PREFLIGHT-ACCEPT-01"
        run_contract = json.loads(contract_raw)
        workflow_sha = json.loads(state_raw)["workflow_template_sha256"]
        reviewer_identity = "synthetic-independent-read-only-controller"
        target = map_doc["target_project"]
        selected_identity = {key: run_contract["story"].get(key)
            for key in ("before_anchor", "after_anchor")}
        bindings = {"project_id": project_id, "run_id": "SYNTHETIC-LEGACY",
            "work_id": "SYNTHETIC-UNIT", "contract_sha256": sha(contract_raw),
            "source_file_sha256": run_contract["source"]["source_file_sha256"],
            "source_manifest_sha256": manifest_sha,
            "policy_sha256": run_contract["unit"]["policy_sha256"],
            "workflow_template_sha256": workflow_sha,
            "identity_kind": "LEGACY_EXTERNAL_V1", "project_instance_id": instance_id,
            "work_intent": "LEGACY_V1_INSERT_BETWEEN",
            "source_id": run_contract["source"]["import_id"],
            "source_revision_id": run_contract["source"]["source_revision_id"],
            "source_manifest_revision_sha256": manifest_sha,
            "source_root_identity": canonical_sha({"legacy_identity_map_sha256": map_sha,
                "legacy_project_root": target.get("legacy_project_root"),
                "project_id": project_id, "project_instance_id": instance_id}),
            "selected_span_or_anchor_sha": canonical_sha(selected_identity),
            "reviewer_identity": reviewer_identity,
            "controller_acceptance_ref": controller_ref, "provider_call_authorized": False,
            "legacy_identity_map_sha256": map_sha,
            "original_run_state_sha256": sha(state_raw)}
        evidence_digest = canonical_sha(bindings)
        controller_doc = {"schema_version": "cnw_w10_controller_verdict_v1", "status": "ACCEPTED",
            "scope": "W10_SINGLE_SCENE", "controller_acceptance_ref": controller_ref,
            "provider_call_authorized": False, "identity_kind": "LEGACY_EXTERNAL_V1",
            "project_instance_id": instance_id, "project_id": project_id,
            "run_id": "SYNTHETIC-LEGACY", "work_id": "SYNTHETIC-UNIT",
            "contract_sha256": sha(contract_raw),
            "source_file_sha256": run_contract["source"]["source_file_sha256"],
            "source_manifest_sha256": manifest_sha,
            "policy_sha256": run_contract["unit"]["policy_sha256"],
            "workflow_template_sha256": workflow_sha,
            "legacy_identity_map_sha256": map_sha,
            "original_run_state_sha256": sha(state_raw)}
        controller_doc.update({**bindings, "evidence_digest": evidence_digest})
        controller_evidence.write_text(json.dumps(controller_doc, sort_keys=True), encoding="utf-8")
        preflight = {
            "schema_version": cnw_w10_policy.PER_RUN_PREFLIGHT_SCHEMA,
            "status": "ACCEPTED", "scope": "W10_SINGLE_SCENE",
            "controller_acceptance_ref": controller_ref,
            "controller_evidence_path": str(controller_evidence),
            "controller_evidence_sha256": sha(controller_evidence.read_bytes()),
            "provider_call_authorized": False,
            "identity_kind": "LEGACY_EXTERNAL_V1", "project_instance_id": instance_id,
            "project_id": project_id, "run_id": "SYNTHETIC-LEGACY", "work_id": "SYNTHETIC-UNIT",
            "contract_sha256": sha(contract_raw),
            "source_file_sha256": run_contract["source"]["source_file_sha256"],
            "source_manifest_sha256": manifest_sha,
            "policy_sha256": run_contract["unit"]["policy_sha256"],
            "workflow_template_sha256": workflow_sha,
            "legacy_identity_map_path": str(map_path), "legacy_identity_map_sha256": map_sha,
            "original_run_state_path": str(original_state_path),
            "original_run_state_sha256": sha(state_raw),
        }
        preflight.update({**bindings, "evidence_digest": evidence_digest})
        preflight_path = self.temp / "synthetic-w10-preflight.json"
        preflight_path.write_text(json.dumps(preflight, sort_keys=True), encoding="utf-8")
        for asserted_status in ("ACCEPTED", "UNREVIEWED"):
            preflight["status"] = asserted_status
            preflight_path.write_text(json.dumps(preflight, sort_keys=True), encoding="utf-8")
            offline, _preflight_sha = cnw_w10_policy.validate_per_run_bindings(
                preflight_path, external_contract, external_run, external_root)
            self.assertEqual(offline["status"], "OFFLINE_BINDINGS_VALIDATED")
            self.assertEqual(offline["bindings"]["identity_kind"], "LEGACY_EXTERNAL_V1")
            with self.assertRaisesRegex(ContractError, "W10_ATTESTATION_PENDING"):
                cnw_w10_policy.verify_preflight_file(
                    preflight_path, external_contract, run_dir=external_run, project_root=external_root)

        # Status labels and old self-asserted controller fields do not change the
        # deterministic identity result or create production trust.
        forged = json.loads(preflight_path.read_text(encoding="utf-8"))
        forged["status"] = "ACCEPTED"
        forged["controller_acceptance_ref"] = "FORGED-ACCEPT"
        forged["reviewer_identity"] = "self-claimed-reviewer"
        preflight_path.write_text(json.dumps(forged, sort_keys=True), encoding="utf-8")
        report, _ = cnw_w10_policy.validate_per_run_bindings(
            preflight_path, external_contract, external_run, external_root)
        self.assertEqual(report["status"], "OFFLINE_BINDINGS_VALIDATED")
        with self.assertRaisesRegex(ContractError, "W10_ATTESTATION_PENDING"):
            cnw_w10_policy.verify_preflight_file(
                preflight_path, external_contract, run_dir=external_run, project_root=external_root)

        # A deterministic fake verifier exercises the signed binding protocol
        # only in this synthetic test. Production loads trust from deployment.
        stage_payload = {"purpose": "W10_PER_RUN_PREFLIGHT", "decision": "ACCEPT",
            "bindings": report["bindings"], "identity_sha256": report["identity_sha256"],
            "provider_call_authorized": False}
        attestation_path = self.temp / "synthetic-signed-controller.json"
        attestation_path.write_text(json.dumps({
            "schema_version": "cnw_signed_controller_attestation_v1",
            "payload": stage_payload, "signer_id": "TEST_ONLY_MOCK_SIGNER",
            "signature_base64": base64.b64encode(b"MOCK_ONLY").decode("ascii")},
            sort_keys=True), encoding="utf-8")
        forged["controller_attestation_path"] = str(attestation_path)
        forged["controller_attestation_sha256"] = sha(attestation_path.read_bytes())
        preflight_path.write_text(json.dumps(forged, sort_keys=True), encoding="utf-8")
        class TestOnlyVerifier:
            def verify(self, signer_id, message, signature):
                return (signer_id == "TEST_ONLY_MOCK_SIGNER" and signature == b"MOCK_ONLY"
                    and json.loads(message.decode("utf-8")) == stage_payload)
        accepted, _ = cnw_w10_policy.verify_per_run_preflight_file(
            preflight_path, external_contract, external_run, external_root,
            verifier=TestOnlyVerifier())
        self.assertEqual(accepted["status"], "ATTESTED")
        self.assertIs(accepted["provider_call_authorized"], False)
        forged["controller_attestation_path"] = str(attestation_path)
        forged["controller_attestation_sha256"] = sha(attestation_path.read_bytes())

        # The identity proof rejects a changed Run, contract, source map, policy,
        # workflow, and mapped project identity independently of any verdict.
        for key, bad_value in (("project_id", "OTHER-PROJECT"), ("run_id", "OTHER-RUN"),
                               ("work_id", "OTHER-WORK"), ("contract_sha256", "0" * 64),
                               ("source_file_sha256", "5" * 64),
                               ("source_manifest_sha256", "1" * 64),
                               ("source_id", "OTHER-SOURCE"),
                               ("source_revision_id", "6" * 64),
                               ("source_manifest_revision_sha256", "7" * 64),
                               ("source_root_identity", "8" * 64),
                               ("selected_span_or_anchor_sha", "9" * 64),
                               ("policy_sha256", "2" * 64),
                               ("workflow_template_sha256", "3" * 64),
                               ("legacy_identity_map_sha256", "4" * 64),
                               ("original_run_state_sha256", "a" * 64),
                               ("project_instance_id", "OTHER-INSTANCE")):
            altered = dict(forged)
            altered[key] = bad_value
            preflight_path.write_text(json.dumps(altered, sort_keys=True), encoding="utf-8")
            with self.subTest(binding=key), self.assertRaises(ContractError):
                cnw_w10_policy.validate_per_run_bindings(
                    preflight_path, external_contract, external_run, external_root)
        preflight_path.write_text(json.dumps(forged, sort_keys=True), encoding="utf-8")
        external_state.write_bytes(state_raw)

        other_root = self.temp / "same-files-different-legacy-root"
        shutil.copytree(external_root, other_root)
        with self.assertRaisesRegex(ContractError, "LEGACY_EXTERNAL_IDENTITY_BINDING_MISMATCH"):
            validate_legacy_source_path_map(target_project_root=other_root,
                legacy_run_dir=other_root / "runs/SYNTHETIC-LEGACY", manifest_path=map_path,
                expected_manifest_sha256=map_sha)


if __name__ == "__main__":
    unittest.main()
