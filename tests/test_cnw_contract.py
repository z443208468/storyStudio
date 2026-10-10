import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.cnw_contract import (
    ContractError,
    check_required_beats,
    count_visible_chars,
    validate_episode_budget,
    validate_output_length,
    validate_scene_budget,
    visible_char_metrics,
    validate_source_identity,
)


def scene_contract():
    return {
        "unit": {"target_visible_chars": 1000, "min_visible_chars": 700, "max_visible_chars": 1400},
        "story": {"required_beats": [
            {"beat_id": "B01", "budget_visible_chars": 300},
            {"beat_id": "B02", "budget_visible_chars": 400},
            {"beat_id": "B03", "budget_visible_chars": 300},
        ]},
    }


class ContractTests(unittest.TestCase):
    def test_scene_budget_requires_positive_target_and_exact_beat_sum(self):
        contract = scene_contract()
        validate_scene_budget(contract)
        for target in (None, 0):
            bad = scene_contract()
            bad["unit"]["target_visible_chars"] = target
            with self.assertRaisesRegex(ContractError, "PREFLIGHT_TARGET_MISSING"):
                validate_scene_budget(bad)
        bad = scene_contract()
        del bad["unit"]["target_visible_chars"]
        with self.assertRaisesRegex(ContractError, "PREFLIGHT_TARGET_MISSING"):
            validate_scene_budget(bad)
        contract["story"]["required_beats"][0]["budget_visible_chars"] = 299
        with self.assertRaisesRegex(ContractError, "SCENE_BUDGET_SUM_MISMATCH"):
            validate_scene_budget(contract)


    def test_episode_scene_budgets_sum_to_chapter_target(self):
        episode = {"chapter_target_visible_chars": 3200, "scenes": [
            {"id": "S1", "target_visible_chars": 900},
            {"id": "S2", "target_visible_chars": 1100},
            {"id": "S3", "target_visible_chars": 1200},
        ]}
        validate_episode_budget(episode)
        episode["scenes"][1]["target_visible_chars"] = 999
        with self.assertRaisesRegex(ContractError, "EPISODE_BUDGET_SUM_MISMATCH"):
            validate_episode_budget(episode)


    def test_visible_chars_are_nfc_and_distinct_from_file_bytes(self):
        text = "# 标题\n\n**天离：** 茶\u0301。\n动作。"
        metrics = visible_char_metrics(text)
        self.assertEqual(metrics["visible_chars"], count_visible_chars(text))
        self.assertLess(metrics["visible_chars"], len(text.encode("utf-8")))
        self.assertEqual(metrics["dialogue_paragraphs"], 1)
        self.assertGreaterEqual(metrics["han_chars"], 5)
        self.assertEqual(count_visible_chars("[可见文字](https://example.invalid)"), 4)
        self.assertEqual(count_visible_chars("`可见文字`"), 4)


    def test_required_beats_need_external_evidence_for_each_beat(self):
        with self.assertRaisesRegex(ContractError, "RETURN_MISSING_BEAT"):
            check_required_beats(scene_contract(), {"B01": "行1-3", "B03": "行7"})
        check_required_beats(scene_contract(), {"B01": "行1-3", "B02": "行4-6", "B03": "行7"})

    def test_short_output_is_rejected_even_when_transport_would_succeed(self):
        contract = scene_contract()
        contract["unit"].update(target_visible_chars=1000, min_visible_chars=700, max_visible_chars=1400)
        contract["story"]["required_beats"] = [
            {"beat_id": "B01", "budget_visible_chars": 350},
            {"beat_id": "B02", "budget_visible_chars": 350},
            {"beat_id": "B03", "budget_visible_chars": 300},
        ]
        with self.assertRaisesRegex(ContractError, "RETURN_UNDERPRODUCED"):
            validate_output_length(contract, "短稿。" * 30)
        self.assertGreaterEqual(validate_output_length(contract, "正文。" * 400)["visible_chars"], 700)

    def test_source_identity_binds_manifest_script_and_anchors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = "before\ninsert\nafter\n".encode()
            manifest = b"{\"release\":\"test\"}\n"
            (root / "script.md").write_bytes(script)
            (root / "source_manifest.json").write_bytes(manifest)
            digest = lambda data: hashlib.sha256(data).hexdigest()
            contract = {
                "source": {
                    "version": "v1",
                    "zip_sha256": "zip",
                    "local_private_source_manifest_sha256": digest(manifest),
                    "manifest_file": "source_manifest.json",
                    "script_sha256": digest(script),
                },
                "unit": {"id": "S1"},
                "story": {
                    "source_file": "script.md",
                    "before_anchor": {"source_line": 1, "sha256": digest(b"before\n")},
                    "after_anchor": {"source_line": 3, "sha256": digest(b"after\n")},
                },
            }
            validate_source_identity(
                contract,
                source_root=root,
                expected_version="v1",
                expected_zip_sha256="zip",
                expected_manifest_sha256=digest(manifest),
            )
            (root / "source_manifest.json").write_bytes(b"changed")
            with self.assertRaisesRegex(ContractError, "actual private source manifest"):
                validate_source_identity(
                    contract,
                    source_root=root,
                    expected_version="v1",
                    expected_zip_sha256="zip",
                    expected_manifest_sha256=digest(manifest),
                )


if __name__ == "__main__":
  unittest.main()
