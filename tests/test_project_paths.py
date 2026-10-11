"""Offline tests for explicit generic-app DataHome/project identity routing."""
from __future__ import annotations

import os
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.project_paths import (
    APP_ROOT,
    PathResolutionError,
    create_project,
    resolve_data_home,
    resolve_project,
    setup_data_home,
    setup_pointer_path,
)


class GenericProjectPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="storystudio-generic-paths-"))
        self.data_home = self.temp / "private-data"
        self.pointer = self.temp / "user-config" / "StoryStudio" / "setup.json"

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def _grant_everyone_full_control(self, path: Path):
        icacls = shutil.which("icacls.exe") or shutil.which("icacls")
        if not icacls:
            self.skipTest("icacls is unavailable")
        result = subprocess.run(
            [icacls, str(path), "/grant", "*S-1-1-0:(OI)(CI)F"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            self.skipTest(f"cannot construct the broad-ACL fixture: {result.stderr or result.stdout}")

    def test_missing_or_corrupt_setup_pointer_fails_closed(self):
        with self.assertRaises(PathResolutionError) as missing:
            resolve_data_home(pointer_path=self.pointer)
        self.assertEqual(missing.exception.code, "DATA_HOME_REQUIRED")

        self.pointer.parent.mkdir(parents=True)
        self.pointer.write_text("not-json", encoding="utf-8")
        with self.assertRaises(PathResolutionError) as corrupt:
            resolve_data_home(pointer_path=self.pointer)
        self.assertEqual(corrupt.exception.code, "SETUP_POINTER_INVALID")

    def test_existing_shared_data_home_is_rejected_without_changing_permissions(self):
        shared = self.temp / "inherited-shared-folder"
        shared.mkdir()
        with self.assertRaises(PathResolutionError) as unsafe:
            setup_data_home(shared, pointer_path=self.pointer)
        self.assertIn(unsafe.exception.code, {"DATA_HOME_ACL_NOT_INDEPENDENT", "DATA_HOME_ACL_TOO_BROAD"})
        self.assertFalse(self.pointer.exists())

    def test_project_commands_require_explicit_registered_project(self):
        with self.assertRaises(PathResolutionError) as missing:
            resolve_project(None, data_home=self.data_home)
        self.assertEqual(missing.exception.code, "PROJECT_REQUIRED")

    def test_setup_pointer_resolves_same_root_in_a_fresh_process(self):
        env = os.environ.copy()
        env.pop("STORYSTUDIO_DATA_HOME", None)
        if os.name == "nt":
            env["LOCALAPPDATA"] = str(self.temp / "user-config")
        else:
            env["XDG_CONFIG_HOME"] = str(self.temp / "user-config")
        selected = setup_data_home(self.data_home, env=env)
        self.assertEqual(setup_pointer_path(env), self.temp / "user-config" / "StoryStudio" / "setup.json")
        code = "from tools.project_paths import resolve_data_home; print(resolve_data_home())"
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=APP_ROOT, env=env,
            check=True, capture_output=True, text=True,
        )
        self.assertEqual(Path(result.stdout.strip()), selected)

    def test_two_projects_with_same_display_id_get_distinct_instances(self):
        setup_data_home(self.data_home, pointer_path=self.pointer)
        first = create_project(project_id="NOVEL", display_name="First", pointer_path=self.pointer)
        second = create_project(project_id="NOVEL", display_name="Second", pointer_path=self.pointer)
        self.assertNotEqual(first["project_instance_id"], second["project_instance_id"])
        self.assertNotEqual(first["project_root"], second["project_root"])
        self.assertEqual(resolve_project(first["project_root"], pointer_path=self.pointer)["project_instance_id"], first["project_instance_id"])
        self.assertEqual(resolve_project(second["project_root"], pointer_path=self.pointer)["project_instance_id"], second["project_instance_id"])

    def test_copied_identity_cannot_open_as_a_second_active_instance(self):
        setup_data_home(self.data_home, pointer_path=self.pointer)
        original = create_project(project_id="SAMPLE", pointer_path=self.pointer)
        projects_root = self.data_home / "projects"
        copied_root = projects_root / "copied-instance"
        copied_root.mkdir()
        identity = Path(original["project_root"]) / "project_identity.json"
        shutil.copyfile(identity, copied_root / "project_identity.json")
        with self.assertRaises(PathResolutionError) as collision:
            resolve_project(copied_root, pointer_path=self.pointer)
        self.assertEqual(collision.exception.code, "PROJECT_INSTANCE_COLLISION")

    def test_malformed_identity_cannot_escape_registry_directory(self):
        setup_data_home(self.data_home, pointer_path=self.pointer)
        original = create_project(project_id="BAD-ID", pointer_path=self.pointer)
        identity_path = Path(original["project_root"]) / "project_identity.json"
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        identity["project_instance_id"] = "..\\outside"
        identity_path.write_text(json.dumps(identity), encoding="utf-8")
        with self.assertRaises(PathResolutionError) as invalid:
            resolve_project(original["project_root"], pointer_path=self.pointer)
        self.assertEqual(invalid.exception.code, "PROJECT_IDENTITY_INVALID")

    def test_data_home_inside_repository_is_rejected(self):
        with self.assertRaises(PathResolutionError) as unsafe:
            setup_data_home(APP_ROOT / "tests" / "fixture-data", pointer_path=self.pointer)
        self.assertEqual(unsafe.exception.code, "DATA_HOME_INSIDE_APP_ROOT")
        self.assertFalse((APP_ROOT / "tests" / "fixture-data").exists())

    def test_stale_registration_lock_fails_closed_and_is_preserved(self):
        setup_data_home(self.data_home, pointer_path=self.pointer)
        lock = self.data_home / "shared" / "project_instances" / ".registration.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text("interrupted owner\n", encoding="ascii")
        with self.assertRaises(PathResolutionError) as busy:
            create_project(project_id="LOCKED", pointer_path=self.pointer)
        self.assertEqual(busy.exception.code, "PROJECT_REGISTRY_BUSY")
        self.assertEqual(lock.read_text(encoding="ascii"), "interrupted owner\n")

    def test_symbolic_link_data_home_is_rejected_when_supported(self):
        target = self.temp / "real-data"
        target.mkdir()
        link = self.temp / "linked-data"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlinks are unavailable on this host: {exc}")
        with self.assertRaises(PathResolutionError) as unsafe:
            resolve_data_home(explicit=link)
        self.assertEqual(unsafe.exception.code, "DATA_HOME_REPARSE_POINT")

    @unittest.skipUnless(os.name == "nt", "Windows junction behavior")
    def test_windows_junction_data_home_is_rejected_when_supported(self):
        target = self.temp / "junction-target"
        junction = self.temp / "junction-data"
        target.mkdir()
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            self.skipTest(f"junction creation unavailable: {result.stderr or result.stdout}")
        try:
            with self.assertRaises(PathResolutionError) as unsafe:
                resolve_data_home(explicit=junction)
            self.assertEqual(unsafe.exception.code, "DATA_HOME_REPARSE_POINT")
        finally:
            if junction.exists():
                os.rmdir(junction)

    @unittest.skipUnless(os.name == "nt", "Windows ACL behavior")
    def test_broad_projects_child_acl_is_rejected_before_project_files_are_created(self):
        setup_data_home(self.data_home, pointer_path=self.pointer)
        projects = self.data_home / "projects"
        projects.mkdir()
        self._grant_everyone_full_control(projects)
        with self.assertRaises(PathResolutionError) as unsafe:
            create_project(project_id="WIDE-PROJECTS", pointer_path=self.pointer)
        self.assertEqual(unsafe.exception.code, "DATA_HOME_ACL_TOO_BROAD")
        self.assertEqual(list(projects.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "Windows ACL behavior")
    def test_broad_registry_child_acl_is_rejected_before_project_files_are_created(self):
        setup_data_home(self.data_home, pointer_path=self.pointer)
        shared = self.data_home / "shared"
        shared.mkdir()
        registry = shared / "project_instances"
        registry.mkdir()
        self._grant_everyone_full_control(registry)
        with self.assertRaises(PathResolutionError) as unsafe:
            create_project(project_id="WIDE-REGISTRY", pointer_path=self.pointer)
        self.assertEqual(unsafe.exception.code, "DATA_HOME_ACL_TOO_BROAD")
        projects = self.data_home / "projects"
        self.assertTrue(projects.is_dir())
        self.assertEqual(list(projects.iterdir()), [])
        self.assertEqual(list(registry.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "Windows ACL behavior")
    def test_broad_existing_project_acl_is_rejected_during_resolution(self):
        setup_data_home(self.data_home, pointer_path=self.pointer)
        project = create_project(project_id="WIDE-ROOT", pointer_path=self.pointer)
        project_root = Path(project["project_root"])
        self._grant_everyone_full_control(project_root)
        with self.assertRaises(PathResolutionError) as unsafe:
            resolve_project(project_root, pointer_path=self.pointer)
        self.assertEqual(unsafe.exception.code, "DATA_HOME_ACL_TOO_BROAD")

    def test_project_root_from_another_volume_is_rejected_when_available(self):
        setup_data_home(self.data_home, pointer_path=self.pointer)
        project = create_project(project_id="VOLUME", pointer_path=self.pointer)
        other_volume = None
        if os.name == "nt":
            current_drive = Path(self.data_home.anchor).drive.casefold()
            for drive in ("C:\\", "D:\\", "E:\\"):
                if Path(drive).exists() and drive.casefold() != current_drive:
                    other_volume = Path(drive) / "temp" / f"ss-cross-volume-{self.temp.name}"
                    break
        if other_volume is None:
            self.skipTest("no second mounted volume is available")
        try:
            other_volume.mkdir(parents=True, exist_ok=True)
            copied = other_volume / "project-copy"
            copied.mkdir()
            shutil.copyfile(Path(project["project_root"]) / "project_identity.json", copied / "project_identity.json")
            with self.assertRaises(PathResolutionError) as unsafe:
                resolve_project(copied, pointer_path=self.pointer)
            self.assertEqual(unsafe.exception.code, "PROJECT_PATH_OUTSIDE_DATA_HOME")
        finally:
            shutil.rmtree(other_volume, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
