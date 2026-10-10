from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "capture_cnw_reference.py"
SPEC = importlib.util.spec_from_file_location("capture_cnw_reference", SCRIPT)
assert SPEC and SPEC.loader
capture_tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture_tool)


def run_git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


class SourceSnapshotTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, str]:
        (root / ".gitignore").write_text("/runtime/\n", encoding="utf-8")
        source = root / "third_party" / "claude-novel-workflow"
        (source / "docs" / "nested").mkdir(parents=True)
        run_git(root, "init", "-q")
        run_git(source, "init", "-q")
        run_git(source, "config", "user.email", "snapshot-test@example.invalid")
        run_git(source, "config", "user.name", "Snapshot Test")
        for index in range(45):
            target = source / "docs" / "nested" / f"method-{index:02}.md"
            target.write_text(f"Reference method {index}\n", encoding="utf-8")
        run_git(source, "add", "docs")
        run_git(source, "commit", "-q", "-m", "fixture source")
        return source, run_git(source, "rev-parse", "HEAD")

    def test_capture_copies_pinned_bytes_to_ignored_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cnw_snapshot_") as temp:
            root = Path(temp).resolve()
            source, pin = self.make_fixture(root)
            old_pin = capture_tool.PIN
            try:
                capture_tool.PIN = pin
                result = capture_tool.capture(root)
            finally:
                capture_tool.PIN = old_pin
            self.assertEqual(result["status"], "REFERENCE_CAPTURE_VERIFIED")
            self.assertEqual(result["files"], 45)
            original = source / "docs" / "nested" / "method-00.md"
            copied = Path(result["reference_root"]) / "docs" / "nested" / "method-00.md"
            self.assertEqual(copied.read_bytes(), original.read_bytes())
            self.assertIn("runtime", result["manifest"])

    def test_mutated_snapshot_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cnw_collision_") as temp:
            root = Path(temp).resolve()
            _source, pin = self.make_fixture(root)
            old_pin = capture_tool.PIN
            try:
                capture_tool.PIN = pin
                result = capture_tool.capture(root)
                copied = Path(result["reference_root"]) / "docs" / "nested" / "method-00.md"
                copied.write_bytes(copied.read_bytes() + b"tampered")
                with self.assertRaisesRegex(RuntimeError, "EXISTING_REFERENCE_COLLISION"):
                    capture_tool.capture(root)
            finally:
                capture_tool.PIN = old_pin

    def test_nested_symlink_redirect_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cnw_symlink_") as temp:
            root = Path(temp).resolve()
            output = root / "runtime" / "reference" / "snapshot"
            outside = root / "outside"
            (output / "docs").mkdir(parents=True)
            outside.mkdir()
            link = output / "docs" / "nested"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlink unavailable in this environment: {exc}")
            with self.assertRaisesRegex(RuntimeError, "OUTPUT_PATH_REDIRECT"):
                capture_tool.ensure_no_redirect(output, link / "target.md")


if __name__ == "__main__":
    unittest.main()
