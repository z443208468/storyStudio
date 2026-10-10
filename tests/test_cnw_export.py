import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import cnw_export
from tools.cnw_contract import ContractError


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "runs/TEST"
        (self.run / "artifacts").mkdir(parents=True)
        source = self.root / "original.md"
        source.write_bytes(b"Before <anchor>\r\nFollowing choice\n")
        lines = source.read_bytes().splitlines(keepends=True)
        self.contract = {"project_id": "FICT_EXPORT", "unit": {"id": "TEST"},
                         "source": {"identity_type": "imported_project", "source_root": "."},
                         "story": {"source_file": source.name, "before_anchor": {
                             "scene": "A", "source_line": 1, "sha256": hashlib.sha256(lines[0]).hexdigest()},
                             "after_anchor": {"scene": "A", "source_line": 2, "sha256": hashlib.sha256(lines[1]).hexdigest()}}}
        (self.run / "artifacts/contract.json").write_text(json.dumps(self.contract), encoding="utf-8")
        (self.run / "artifacts/prose.md").write_text("Actual insert", encoding="utf-8")
        self.state = {"run_id": "TEST", "stages": {"prose": {"artifact": {"path": "artifacts/prose.md"}}}}

    def test_reading_package_contains_verified_real_anchors_in_order(self):
        with patch.object(cnw_export, "ROOT", self.root):
            result = cnw_export.export_reading_package(self.run, self.state, project_root=self.root)
        files = Path(result["deliverables"])
        reading = (files / "03_前后文连读.md").read_text(encoding="utf-8")
        self.assertLess(reading.index("Before <anchor>"), reading.index("Actual insert"))
        self.assertLess(reading.index("Actual insert"), reading.index("Following choice"))
        html = (files / "03_前后文连读.html").read_text(encoding="utf-8")
        self.assertIn("Before &lt;anchor&gt;", html)
        self.assertIn("Following choice", html)
        self.assertIn("show-run -ProjectRoot <project>", (files / "05_复用操作说明.md").read_text(encoding="utf-8"))
        self.assertEqual(result["provider_call"], "none")
        self.assertEqual(result["candidate_status"], "UNREVIEWED_CANDIDATE")
        self.assertIn("UNREVIEWED_CANDIDATE", (files / "00_运行状态.md").read_text(encoding="utf-8"))
        self.assertIn("UNREVIEWED_CANDIDATE", html)

    def test_changed_anchor_refuses_instead_of_exporting_different_context(self):
        (self.root / "original.md").write_text("Changed\nFollowing choice\n", encoding="utf-8")
        with patch.object(cnw_export, "ROOT", self.root), self.assertRaisesRegex(ContractError, "SOURCE_ANCHOR_MISMATCH"):
            cnw_export.export_reading_package(self.run, self.state, project_root=self.root)


if __name__ == "__main__":
    unittest.main()
