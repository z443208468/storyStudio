"""Pure task projection; actual role integration is checked separately."""
import copy
import unittest
from unittest.mock import patch

from tools.cnw_contract import ContractError
from tools import cnw_task_requirements as task


class TaskDerivationTests(unittest.TestCase):
    def setUp(self):
        self.identity = {"project_id": "TRIAL-ONE", "project_instance_id": "b8e7cffe-982a-4bf0-b82e-95d7776cbfd9"}
        self.order = {"project_id": "INPUT-ONE", "unit_id": "SCENE-ONE", "pov": "Mira",
            "new_plot_pre_designed": False, "focus_characters": ["Mira"],
            "scope_of_new_plot": "One local choice.", "fact_provenance": "INFERRED remains inferred.",
            "knowledge_snapshot": {"Mira": {"private": ["PRIVATE-KNOWLEDGE-CANARY"], "unknown": ["UNDECIDED"]}},
            "custom_future_requirement": {"zero": 0, "flag": False, "unknown": None},
            "input_preflight_v5": {"status": "ACCEPTED"}, "integrations": {"nk": "ENABLED"},
            "original_authority": {"before_scene": "OLD-COPY"}}
        self.packet = {"pov": "Mira", "standalone_trial": True, "new_plot_pre_designed": False,
            "creative_freedom": "Decide the visible response.", "allowed_local_change": "A short offer.",
            "original_before": "Do not treat this stale copy as authoritative.",
            "role_states": {"Mira": {"where_now": "courtyard", "current_voice_phase": "brief",
                "must_not_force": ["A confession"], "narrator_access": "Visible behavior only.", "private_facts": ["PRIVATE-STATE-CANARY"]}},
            "reader_knowledge": ["Only the public offer."], "next_fixed_event": "Return to the planned meeting."}
        self.temporal = {"time": None, "space": "courtyard", "unresolved": ["Timing remains open."],
                         "status": "TODO_CONFIRM", "basis": "INFERRED"}
        self.game = {"grain": 0, "can_attack": False, "not_canonical_history": True}

    def sources(self):
        return {key: (f"_INBOX/input_packs/{'a' * 64}/scenes/ONE/{key}.json", task.encode(value))
                for key, value in (("work_order", self.order), ("scene_packet", self.packet),
                                   ("temporal_envelope", self.temporal), ("gameplay_snapshot", self.game))}

    def derive(self, sources=None):
        return task.derive_task_context(sources=sources or self.sources(), identity=self.identity,
                                       scene_root="scenes/ONE", pack_sha256="a" * 64)

    def validate(self, value, sources=None):
        task.validate_derivation(value, sources=sources or self.sources(), identity=self.identity,
                                 scene_root="scenes/ONE", pack_sha256="a" * 64)

    def test_preserves_false_zero_null_and_source_locators_without_file_reads(self):
        with patch("builtins.open", side_effect=AssertionError("Pure recipe must not open files")):
            value = self.derive()
            self.validate(value)
        extension = value["data"]["work_order"]["custom_future_requirement"]
        self.assertIs(extension["flag"], False)
        self.assertIs(type(extension["zero"]), int)
        self.assertIsNone(extension["unknown"])
        self.assertNotIn("input_preflight_v5", value["data"]["work_order"])
        self.assertNotIn("integrations", value["data"]["work_order"])
        self.assertNotIn("original_before", value["data"]["scene_packet"])
        self.assertEqual(value["opaque_work_order_fields"], ["custom_future_requirement"])
        self.assertEqual(value["opaque_semantic_status"], "UNPROVEN_EXTENSION")
        record = next(row for row in value["provenance"] if row["source_pointer"] == "/role_states")
        self.assertEqual(record["source_sha256"], task.sha(self.sources()["scene_packet"][1]))
        self.assertNotIn("CONFIRMED", value["authority"])

    def test_changed_values_types_locators_and_instance_reject(self):
        original = self.derive()
        for change in ("type", "value", "locator", "instance"):
            value = copy.deepcopy(original)
            if change == "type": value["data"]["work_order"]["custom_future_requirement"]["flag"] = 0
            if change == "value": value["data"]["gameplay_snapshot"]["grain"] = 1
            if change == "locator": value["provenance"][0]["source_pointer"] = "/unrelated"
            if change == "instance": value["project_instance_id"] = "0" * 32
            with self.subTest(change=change), self.assertRaisesRegex(ContractError, "TASK_REQUIREMENTS_DERIVATION_MISMATCH"):
                self.validate(value)

    def test_unknown_recipe_and_changed_frozen_source_reject(self):
        value = self.derive()
        changed = copy.deepcopy(value)
        changed["recipe_version"] = "self_accepted_future_recipe"
        with self.assertRaisesRegex(ContractError, "TASK_REQUIREMENTS_RECIPE_UNSUPPORTED"):
            self.validate(changed)
        self.game["grain"] = 2
        with self.assertRaisesRegex(ContractError, "TASK_REQUIREMENTS_DERIVATION_MISMATCH"):
            self.validate(value)

    def test_discrete_conflict_rejects_but_free_text_and_unknown_do_not(self):
        self.order["creative_freedom"] = "Use a concrete act of help."
        self.derive()  # Different free wording does not prove incompatibility.
        self.order["new_plot_pre_designed"] = None
        value = self.derive()
        self.assertIsNone(value["data"]["work_order"]["new_plot_pre_designed"])
        self.order["new_plot_pre_designed"] = True
        with self.assertRaisesRegex(ContractError, "TASK_REQUIREMENTS_DISCRETE_CONFLICT"):
            self.derive()

    def test_lens_views_keep_their_own_task_duties_and_types(self):
        value = self.derive()
        character = task.lens_task_view(value, "character")
        self.assertIn("must_not_force", character["data"]["scene_packet"]["role_states"]["Mira"])
        self.assertNotIn("gameplay_snapshot", character["data"])
        plot = task.lens_task_view(value, "plot")
        self.assertIn("scope_of_new_plot", plot["data"]["work_order"])
        self.assertNotIn("role_states", plot["data"]["scene_packet"])
        canon = task.lens_task_view(value, "canon")
        self.assertEqual(canon["data"]["temporal_envelope"]["status"], "TODO_CONFIRM")
        self.assertNotIn("gameplay_snapshot", canon["data"])
        specific = task.lens_task_view(value, "story_specific")
        self.assertIs(specific["data"]["gameplay_snapshot"]["can_attack"], False)
        self.assertEqual(specific["data"]["gameplay_snapshot"]["grain"], 0)
        self.assertIsNone(task.lens_task_view(value, "style"))

    def test_duplicate_gameplay_discrete_values_keep_two_original_locations(self):
        self.order["gameplay_snapshot"] = {"grain": 0, "can_attack": False, "unknown": None}
        self.derive()
        for key, value in (("grain", 1), ("can_attack", 0)):
            original = self.game[key]
            self.game[key] = value
            sources = self.sources()
            with self.subTest(key=key), self.assertRaises(task.TaskRequirementConflict) as caught:
                self.derive(sources)
            report = caught.exception.task_conflict
            locations = report["conflicts"][0]["sources"]
            self.assertEqual([item["sha256"] for item in locations],
                             [task.sha(sources[name][1]) for name in ("work_order", "gameplay_snapshot")])
            self.assertEqual(locations[0]["pointer"], "/gameplay_snapshot/" + key)
            self.assertEqual(locations[1]["pointer"], "/" + key)
            self.game[key] = original
        self.game.update(extra_current_state="Additional fields are valid.", unknown=0)
        self.order["gameplay_snapshot"]["comment"] = "A different phrasing."
        self.game["comment"] = "Keep local gameplay state."
        self.derive()  # null and missing never replace either retained source.
        self.order["gameplay_snapshot"].update(time_scope="past", grain=2)
        self.game["time_scope"] = "current"
        self.derive()  # Separate explicit temporal scopes are not contradictions.

    def test_real_valid_at_format_preserves_distinct_times_and_rejects_same_time_conflict(self):
        self.order["gameplay_snapshot"] = {"scope": "same-task", "valid_at": "BEFORE", "grain": 2, "can_attack": False}
        self.game = {"scope": "same-task", "valid_at": "AFTER", "grain": 1, "can_attack": True}
        value = self.derive()
        self.assertEqual(value["data"]["work_order"]["gameplay_snapshot"]["grain"], 2)
        self.assertEqual(value["data"]["gameplay_snapshot"]["grain"], 1)
        self.assertEqual(value["data"]["gameplay_snapshot"]["valid_at"], "AFTER")
        self.game["valid_at"] = "BEFORE"
        for key in ("grain", "can_attack"):
            self.game.update(grain=2, can_attack=False)
            self.game[key] = 1 if key == "grain" else True
            sources = self.sources()
            with self.subTest(key=key), self.assertRaises(task.TaskRequirementConflict) as caught:
                self.derive(sources)
            locations = caught.exception.task_conflict["conflicts"][0]["sources"]
            self.assertEqual(locations[0]["sha256"], task.sha(sources["work_order"][1]))
            self.assertEqual(locations[1]["sha256"], task.sha(sources["gameplay_snapshot"][1]))
        self.game.update(grain=1, can_attack=True)
        self.game["valid_at"] = None
        value = self.derive()
        self.assertIsNone(value["data"]["gameplay_snapshot"]["valid_at"])
        self.game.pop("valid_at")
        value = self.derive()
        self.assertNotIn("valid_at", value["data"]["gameplay_snapshot"])


if __name__ == "__main__":
    unittest.main()
