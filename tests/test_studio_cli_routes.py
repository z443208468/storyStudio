"""Offline checks for the Atom-04 PowerShell route surface."""
from __future__ import annotations

import re
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import cnw_project, cnw_maintenance, cnw_sprint, cnw_sprint_live, studio_health
from tools.project_paths import create_project, setup_data_home

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "tools" / "studio.ps1"
COMMANDS_DOC = ROOT / "docs" / "CLI_COMMANDS.md"


class StudioCliRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = STUDIO.read_text(encoding="utf-8")
        cls.docs = COMMANDS_DOC.read_text(encoding="utf-8")
        cls.powershell = shutil.which("pwsh.exe") or shutil.which("pwsh") or shutil.which("powershell.exe") or shutil.which("powershell")

    def _invoke(self, command: str, *arguments: str):
        return subprocess.run(
            [self.powershell, "-NoProfile", "-File", str(STUDIO), command, *arguments],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        )

    def test_public_commands_match_registry(self):
        match = re.search(r"\[ValidateSet\((.*?)\)\]\s*\[string\]\$Command", self.script, re.S)
        self.assertIsNotNone(match)
        public = set(re.findall(r"'([^']+)'", match.group(1)))
        rows = [line for line in self.docs.splitlines() if line.startswith("| ") and "| COMMAND |" not in line]
        registered = {line.split("|")[1].strip() for line in rows}
        self.assertEqual(public, registered)

    def test_supported_routes_point_to_tracked_implementations(self):
        for line in self.docs.splitlines():
            if not line.startswith("| ") or "| COMMAND |" in line:
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) < 6 or cells[4] != "SUPPORTED" or cells[2] != "YES":
                continue
            for path in re.findall(r"`(tools/[^:` ]+)(?::[^`]*)?`", cells[1]):
                result = subprocess.run(
                    ["git", "ls-files", "--error-unmatch", path], cwd=ROOT,
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, f"untracked supported implementation: {path}")

    def test_doctor_app_only_needs_no_project(self):
        if not self.powershell:
            self.skipTest("PowerShell is unavailable")
        result = self._invoke("doctor", "-AppOnly")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = __import__("json").loads(result.stdout)
        self.assertIn(payload["status"], {"ENGINE_READY", "ENGINE_INCOMPLETE"})
        self.assertEqual(payload["project"], "NOT_SELECTED")
        self.assertEqual(payload["provider_call"], "none")
        self.assertEqual(payload["generic_live_production"], "NOT_RUN")
        self.assertNotEqual(payload["author_reference"], "PINNED_REFERENCE_AVAILABLE")
        self.assertIn(payload["author_reference"], {
            "PINNED_REFERENCE_VERIFIED", "PIN_MISMATCH", "RUNTIME_MISSING", "UNVERIFIED",
        })

    def test_health_checks_reject_reference_and_build_identity_mismatch(self):
        with tempfile.TemporaryDirectory(prefix="studio-health-") as temporary:
            root = Path(temporary)
            reference_root = root / "runtime/reference/cnw_97ad71fe5e5e"
            rows = []
            for source_path, blob in studio_health.REFERENCE_BLOBS.items():
                relative = f"runtime/reference/cnw_97ad71fe5e5e/{source_path}"
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                content = f"fixture:{source_path}\n".encode()
                target.write_bytes(content)
                rows.append({"source_path": source_path, "local_reference": relative,
                             "upstream_git_blob": blob, "bytes": len(content),
                             "sha256": hashlib.sha256(content).hexdigest()})
            reference_root.mkdir(parents=True, exist_ok=True)
            manifest_path = reference_root / "CNW_LOCAL_REFERENCE_MANIFEST.json"
            manifest = {"project": "MintoTsukino/claude-novel-workflow",
                        "upstream_commit": studio_health.REFERENCE_COMMIT,
                        "file_count": len(rows), "references": rows}
            manifest_path.write_text(__import__("json").dumps(manifest), encoding="utf-8")
            self.assertEqual(studio_health.verify_author_reference(root), "PINNED_REFERENCE_VERIFIED")
            manifest["upstream_commit"] = "wrong-pin"
            manifest_path.write_text(__import__("json").dumps(manifest), encoding="utf-8")
            self.assertEqual(studio_health.verify_author_reference(root), "PIN_MISMATCH")

            patch_bytes, lock_bytes = b"synthetic patch\n", b"synthetic lock\n"
            (root / "patches/critics").mkdir(parents=True)
            (root / "patches/critics/patch.diff").write_bytes(patch_bytes)
            (root / "requirements").mkdir()
            (root / "requirements/critics.lock").write_bytes(lock_bytes)
            patch_hash, lock_hash = hashlib.sha256(patch_bytes).hexdigest(), hashlib.sha256(lock_bytes).hexdigest()
            build_id = f"p2-02-12345678-{patch_hash[:12]}-{lock_hash[:12]}"
            build = root / "runtime/patched/CritiCS" / build_id
            (build / "critics/plan").mkdir(parents=True)
            (build / "critics/text").mkdir(parents=True)
            (build / "critics/plan/plan.py").write_text("# fixture\n", encoding="utf-8")
            (build / "critics/text/text.py").write_text("# fixture\n", encoding="utf-8")
            index_path = root / "patches/critics/PATCH_INDEX.json"
            index = {"source_commit": "1234567890abcdef", "ordered_patch_files": ["patches/critics/patch.diff"],
                     "patch_sha256": [patch_hash], "dependency_lock": "requirements/critics.lock",
                     "dependency_lock_sha256": lock_hash, "runtime_build_id": build_id,
                     "runtime_path": f"runtime/patched/CritiCS/{build_id}"}
            index_path.write_text(__import__("json").dumps(index), encoding="utf-8")
            self.assertEqual(studio_health.verify_optional_build(root, "critics"), "AVAILABLE_PINNED")
            index["runtime_build_id"] = "unrelated-build"
            index_path.write_text(__import__("json").dumps(index), encoding="utf-8")
            self.assertEqual(studio_health.verify_optional_build(root, "critics"), "IDENTITY_MISMATCH")

    def test_live_sprint_accepts_registered_root_before_plan_validation(self):
        with tempfile.TemporaryDirectory(prefix="studio-live-sprint-root-") as temporary:
            base = Path(temporary)
            data_home = base / "data-home"
            pointer = base / "config" / "StoryStudio" / "setup.json"
            setup_data_home(data_home, pointer_path=pointer)
            project = create_project(project_id="SPRINT_FIXTURE", pointer_path=pointer)
            project_root = Path(project["project_root"])
            plan = project_root / "sprint-plan.json"
            plan.write_text("{}", encoding="utf-8")
            with self.assertRaises(cnw_project.ContractError) as caught:
                cnw_sprint_live.run_live_sprint(project_root, "fixture-sprint", plan)
            self.assertEqual(str(caught.exception).split(":", 1)[0], "SPRINT_REQUIRES_FIVE_EPISODES")

    def test_project_routes_fail_closed_before_dispatch(self):
        guarded = re.search(r"\$ProjectCommands\s*=\s*@\((.*?)\)", self.script, re.S)
        self.assertIsNotNone(guarded)
        commands = re.findall(r"'([^']+)'", guarded.group(1))
        self.assertGreaterEqual(len(commands), 20)
        self.assertIn("if ($Command -in $ProjectCommands", self.script)
        for command in commands:
            self.assertIn(f"| {command} |", self.docs)
        if not self.powershell:
            self.skipTest("PowerShell is unavailable")
        result = self._invoke("show-run", "-RunId", "offline-fixture")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PROJECT_REQUIRED", (result.stderr or "") + (result.stdout or ""))

    def test_legacy_scene_requires_and_reads_explicit_project(self):
        if not self.powershell:
            self.skipTest("PowerShell is unavailable")
        with tempfile.TemporaryDirectory(prefix="studio-legacy-scene-") as temporary:
            project = Path(temporary)
            plot = project / "06_plot" / "FIC-01_plot.v1.md"
            plot.parent.mkdir()
            plot.write_text("Synthetic checkpoint only.\n", encoding="utf-8")
            result = self._invoke("legacy-scene", "-ProjectRoot", str(project),
                                  "-Stage", "plot", "-WorkId", "FIC-01")
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            payload = __import__("json").loads(result.stdout)
            self.assertEqual(payload["status"], "LEGACY_CHECKPOINT_ONLY")
            self.assertEqual(payload["work_id"], "FIC-01")
            self.assertEqual(payload["sha256"], __import__("hashlib").sha256(plot.read_bytes()).hexdigest().upper())

    def test_project_import_and_source_list_use_temp_data_home(self):
        if not self.powershell:
            self.skipTest("PowerShell is unavailable")
        with tempfile.TemporaryDirectory(prefix="studio-project-import-") as temporary:
            base = Path(temporary)
            data_home = base / "data-home"
            pointer = base / "config" / "StoryStudio" / "setup.json"
            setup = self._invoke("setup", "-DataHome", str(data_home), "-DataHomePointer", str(pointer))
            self.assertEqual(setup.returncode, 0, setup.stderr or setup.stdout)
            self.assertTrue(pointer.is_file())
            source = base / "fiction.md"
            source.write_text("Fictional fixture source.\n", encoding="utf-8")
            imported = self._invoke("project-import", "-ProjectId", "FICT_IMPORT",
                                    "-DataHome", str(data_home), "-InputFile", str(source), "-Format", "md")
            self.assertEqual(imported.returncode, 0, imported.stderr or imported.stdout)
            project = __import__("json").loads(imported.stdout)
            project_root = project["project_root"]
            source_id = project["import"]["source_id"]
            self.assertTrue(Path(project_root).resolve(strict=True).is_relative_to(
                data_home.resolve(strict=True) / "projects"))
            listed = self._invoke("source-list", "-ProjectRoot", project_root)
            self.assertEqual(listed.returncode, 0, listed.stderr or listed.stdout)
            registry = __import__("json").loads(listed.stdout)
            self.assertEqual(registry["sources"][0]["source_id"], source_id)
            self.assertEqual(registry["provider_call"], "none")

    def test_active_facade_has_no_fixed_project_or_historical_live_receipt_shortcut(self):
        self.assertNotIn("$SourceRoot", self.script)
        self.assertNotRegex(self.script, r"workspace[\\/]cangqi")
        self.assertNotIn("P2_ACCEPTANCE_LOG.md", self.script)
        self.assertNotIn("LIVE_ACCEPTANCE_EVIDENCE_MISSING", self.script)

    def test_source_list_reports_only_verified_ids_and_registry_revisions(self):
        with tempfile.TemporaryDirectory(prefix="studio-source-list-") as temporary:
            root = Path(temporary)
            source_path = root / "_INBOX" / "originals" / "fiction.md"
            source_path.parent.mkdir(parents=True)
            raw_source = b"Fictional source fixture.\n"
            source_path.write_bytes(raw_source)
            revision = cnw_project.sha(raw_source)
            source_id = revision[:16]
            manifest = {
                "schema_version": "cnw_source_manifest_v2", "project_id": "FIXTURE",
                "sources": [{"source_id": source_id, "source_revision_id": revision,
                              "stored_path": "_INBOX/originals/fiction.md", "format": "md"}],
            }
            manifest_raw = cnw_project._json_bytes(manifest)
            manifest_sha = cnw_project.sha(manifest_raw)
            index = {
                "schema_version": "cnw_source_index_v2", "project_id": "FIXTURE",
                "manifest_revision_sha256": manifest_sha,
                "source_revisions": [{"source_id": source_id, "source_revision_id": revision,
                                      "stored_path": "_INBOX/originals/fiction.md", "format": "md"}],
            }
            index_raw = cnw_project._json_bytes(index)
            inbox = root / "_INBOX"
            (inbox / "source_manifest.json").write_bytes(manifest_raw)
            (inbox / "source_index.json").write_bytes(index_raw)
            manifest_snapshot = inbox / "revisions" / "manifests" / f"{manifest_sha}.json"
            index_snapshot = inbox / "revisions" / "indexes" / f"{cnw_project.sha(index_raw)}.json"
            manifest_snapshot.parent.mkdir(parents=True)
            index_snapshot.parent.mkdir(parents=True)
            manifest_snapshot.write_bytes(manifest_raw)
            index_snapshot.write_bytes(index_raw)
            identity = {"project_id": "FIXTURE", "project_instance_id": "00000000-0000-0000-0000-000000000001"}
            with patch.object(cnw_project, "_registered_project_identity", return_value=identity):
                result = cnw_project.list_source_revisions(root)
            self.assertEqual(result["source_manifest_revision_sha256"], manifest_sha)
            self.assertEqual(result["sources"], [{"source_id": source_id, "source_revision_id": revision,
                                                   "format": "md", "stored_path": "_INBOX/originals/fiction.md"}])
            self.assertNotIn("Fictional source fixture", str(result))

    def test_maintenance_and_fixture_sprint_accept_only_resolved_generic_identity(self):
        identity = {"project_id": "FIXTURE", "project_instance_id": "00000000-0000-0000-0000-000000000001"}
        with tempfile.TemporaryDirectory(prefix="studio-registered-route-") as temporary:
            root = Path(temporary)
            with patch.object(cnw_project, "_registered_project_identity", return_value=identity) as resolve_identity:
                with self.assertRaisesRegex(cnw_project.ContractError, "MAINTENANCE_OPERATION_INVALID"):
                    cnw_maintenance.run_maintenance(root, "not-a-route")
                resolved_root = root.resolve(strict=True)
                resolve_identity.assert_called_once_with(resolved_root)
                resolve_identity.reset_mock()
                with self.assertRaisesRegex(cnw_project.ContractError, "SPRINT_ID_INVALID"):
                    cnw_sprint.run_fixture_sprint(root, "", root / "missing-plan.json")
                resolve_identity.assert_called_once_with(resolved_root)


if __name__ == "__main__":
    unittest.main()
