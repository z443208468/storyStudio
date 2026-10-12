"""Keep the current recovery guide project-neutral and explicit-root only."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ActiveDocumentationScopeTests(unittest.TestCase):
    def test_recovery_examples_require_an_explicit_generic_project_root(self):
        recovery = (ROOT / "docs/CNW_RECOVERY.md").read_text(encoding="utf-8")
        self.assertIn("<ABSOLUTE_PROJECT_ROOT>", recovery)
        self.assertIn("<EXISTING_RUN_ID>", recovery)
        self.assertIn("verify-history", recovery)
        self.assertIn("explicit user Live authorization", recovery)
        for historical_marker in ("workspace/cangqi", "CNW-RESTORE-J19", "J19-20261011"):
            self.assertNotIn(historical_marker, recovery)


if __name__ == "__main__":
    unittest.main()
