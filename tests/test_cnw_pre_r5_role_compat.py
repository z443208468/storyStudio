"""Guard pre-R5 V1 author-role request identity with synthetic inputs."""
import hashlib
import json
import unittest
from unittest.mock import patch

from tools import cnw_roles as roles


def _fixed_author_source(source_path: str) -> tuple[str, str]:
    """Keep this regression fixture independent from local/private reference files."""
    return f"FIXED_AUTHOR_SOURCE:{source_path}\n", f"fixture-blob:{source_path}"


class PreR5RoleCompatibilityTests(unittest.TestCase):
    def test_v1_role_requests_match_pre_r5_baseline(self):
        contract = {
            "schema_version": "cnw_work_unit_v1",
            "project_id": "SYNTHETIC-COMMON",
            "unit": {
                "id": "SYNTHETIC-SCENE-01",
                "kind": "scene",
                "language": "zh-CN",
                "pov": "Mira",
                "target_visible_chars": 300,
                "min_visible_chars": 200,
                "max_visible_chars": 400,
                "required_beats": [],
            },
            "story": {
                "required_beats": [{"beat_id": "B01", "goal": "Mira asks her neighbor for help."}],
                "entry_state": "The hinge is loose.",
                "exit_state": "The neighbors agree on a repair.",
                "characters_in_scene": ["Mira", "Keeper"],
                "before_anchor": "A fictional source anchor.",
                "after_anchor": "A fictional source anchor.",
            },
            "review": {},
        }
        text = {
            "arc": "SYNTHETIC ARC: a small repair changes neighborly trust.",
            "canon": "SYNTHETIC CANON: Mira and Keeper are neighbors.",
            "characters": "SYNTHETIC CHARACTERS: Mira asks direct questions; Keeper is practical.",
            "plot": "SYNTHETIC PLOT: B01 is planned.",
            "cards": "SYNTHETIC CARDS: one scene, one repair.",
            "style": "SYNTHETIC STYLE: concrete action, distinct dialogue.",
            "timeline": "SYNTHETIC TIMELINE: ordinary afternoon.",
            "world": "SYNTHETIC WORLD: a fictional harbor.",
            "glossary": "SYNTHETIC GLOSSARY: harbor door is a public entrance.",
            "brief": "## Voice References\n- Mira\n",
            "voices": "## Mira\nI would rather ask than guess.\n",
        }
        materials = {
            "plot": {
                "04_chapter_design/arc_01.md": text["arc"],
                "90_canon/canon.md": text["canon"],
                "90_canon/character_bible.md": text["characters"],
            },
            "cards": {
                "06_plot/SYNTHETIC-SCENE-01_plot.md": text["plot"],
                "90_canon/character_bible.md": text["characters"],
            },
            "brief": {
                "06_plot/SYNTHETIC-SCENE-01_plot.md": text["plot"],
                "05_scene_cards/SYNTHETIC-SCENE-01_scene_cards.md": text["cards"],
                "90_canon/character_bible.md": text["characters"],
                "92_style_engine/style_guide.md": text["style"],
                "90_canon/canon.md": text["canon"],
                "90_canon/timeline.md": text["timeline"],
                "90_canon/world_bible.md": text["world"],
                "90_canon/glossary.md": text["glossary"],
            },
            "prose": {
                "07_draft/<work_id>_writing_brief.md": text["brief"],
                "92_style_engine/character_voice_samples.md": text["voices"],
            },
        }
        expected = {
            "plot": "e0273b99c9165c20aab4026698513f8c1d6101e9fa7a6b149ed55f53f1a9fda1",
            "cards": "dfe7ef0abc06bebc381b2ff1bf0ffdedf53b129ef95f572c13171780fd0c3ee1",
            "brief": "a14012d5eefbc6b997122585f3aa6f08ad04cdfc22f7b8d34899ca9ef501b60e",
            "prose": "29b4307357f66ffe2be9a800499fd01f95c25ba1f0cc6e8fe85d8dedda81012a",
        }

        with patch.object(roles, "_pinned_upstream", side_effect=_fixed_author_source):
            for role, expected_sha256 in expected.items():
                with self.subTest(role=role):
                    messages = roles.build_author_role_messages(role, contract, materials[role])
                    serialized = json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    self.assertEqual(hashlib.sha256(serialized).hexdigest(), expected_sha256)


if __name__ == "__main__":
    unittest.main()
