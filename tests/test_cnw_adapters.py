import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.cnw_contract import ContractError, load_contract, check_required_fields, validate_work_unit
from tools.cnw_critics_adapter import build_plan_critique_command, verify_plan_receipt, read_native_result, native_templates, native_conversation_template, native_prompt_dependencies_match
from tools.cnw_nk_adapter import build_nk_payload, map_reflection_to_brief
from tools import cnw_roles as roles
from tools.cnw_roles import build_prose_input_view, build_role_packet, role_receipt, validate_role_output, verify_stage_chain, resolve_arc, read_production_preparation, role_metadata, plot_structure
from synthetic_cnw_fixtures import write_imported_v1_project


ROOT = Path(__file__).resolve().parents[1]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class AdapterTests(unittest.TestCase):
    def setUp(self):
        workspace = ROOT / "workspace"
        workspace.mkdir(exist_ok=True)
        (ROOT / "runs").mkdir(exist_ok=True)  # owned fixture parent, also in a clean clone
        self.temp = tempfile.TemporaryDirectory(prefix=".cnw-adapter-fixtures-", dir=workspace)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo_root = ROOT
        self.project = self.base
        self.contract_path, self.contract = write_imported_v1_project(self.project)
        manifest_raw = roles.REFERENCE_MANIFEST.read_bytes()
        self.contract["review"]["cnw_reference_manifest_sha256"] = sha(manifest_raw)
        policy_raw = (self.repo_root / "config/cnw_production_policy.json").read_bytes()
        self.contract["unit"]["policy_sha256"] = sha(policy_raw)
        self.contract_path.write_text(json.dumps(self.contract, ensure_ascii=False), encoding="utf-8")
        for relative, content in (("90_canon/canon.md", "Synthetic confirmed Canon."),
                                  ("06_plot/source_anchors.md", "Synthetic before and after anchors.")):
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_native_empty_conversation_framing_preserves_exact_dependencies(self):
        expected = ["MOCK imagery input", "MOCK voice input", "MOCK selected prior outputs"]
        template = native_conversation_template()
        wrapped = [template.format(history="", input=value) for value in expected]
        self.assertTrue(native_prompt_dependencies_match(expected, expected))
        self.assertTrue(native_prompt_dependencies_match(wrapped, expected))
        self.assertFalse(native_prompt_dependencies_match([wrapped[0], expected[1], wrapped[2]], expected))
        self.assertFalse(native_prompt_dependencies_match([value + " altered" for value in wrapped], expected))
        self.assertFalse(native_prompt_dependencies_match([template.format(history="MOCK old conversation", input=value) for value in expected], expected))

    def test_native_plan_revise_binds_original_plot_and_critique_request(self):
        with tempfile.TemporaryDirectory(prefix=".native-proposal-", dir=ROOT / "runs") as temp:
            run = Path(temp)
            source = run / "original.md"
            source.write_text("MOCK original scene", encoding="utf-8")
            critique_path = run / "critique.json"
            critique = {"inspector": "MOCK tighten the same scene"}
            critique_path.write_text(json.dumps(critique), encoding="utf-8")
            output = run / "modified_plot.md"
            output.write_text("MOCK native proposed scene", encoding="utf-8")
            build = json.loads((ROOT / "patches/critics/PATCH_INDEX.json").read_text(encoding="utf-8"))["runtime_build_id"]
            receipt = {"action": "plan-revise", "status": "SUCCEEDED", "model": "deepseek-flash", "base_url": "https://api.deepseek.com/v1",
                       "build": f"runtime/patched/CritiCS/{build}", "input_sha256": sha(source.read_bytes()).upper(), "output_sha256": sha(output.read_bytes()).upper()}
            (run / "run_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
            template = native_templates("storyline_template.py", {"applyQA"})["applyQA"]
            call = {"http_status": 200, "request": {"messages": [{"role": "user", "content": template.format(final_critic=critique, storyline=source.read_text(encoding="utf-8"))}]},
                    "response": {"id": "MOCK-PROPOSAL", "model": "deepseek-flash", "choices": [{"finish_reason": "stop", "message": {"content": output.read_text(encoding="utf-8")}}]}}
            calls = run / "provider-calls.json"
            calls.write_text(json.dumps([call]), encoding="utf-8")
            result = read_native_result(run.name, action="plan-revise", input_path=source, critique_path=critique_path)
            self.assertEqual(result["result"], "MOCK native proposed scene")
            call["request"]["messages"][0]["content"] = "Unrelated proposal request"
            calls.write_text(json.dumps([call]), encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "CRITICS_NATIVE_DEPENDENCY_MISMATCH"):
                read_native_result(run.name, action="plan-revise", input_path=source, critique_path=critique_path)

    def test_author_plot_design_needs_no_prefilled_beats_or_scenes(self):
        contract = load_contract(self.contract_path)
        contract["unit"].update(planning_mode="author_plot", kind="episode")
        contract["story"].pop("required_beats")
        check_required_fields(contract)
        validate_work_unit(contract)
        plot = ("## Identity\nep001\n## Role in the Arc\nDevelop conflict\n"
                "## Key Scenes\n1. An encounter\n2. A consequence\n"
                "## Hook\nA choice\n## Required Story Beats\n- Act\n- Respond\n"
                "## Forbidden Items\nNo disclosure\n## Connections\nContinue\n## Target Length\n1500\n")
        meta = role_metadata("plot", contract)
        self.assertEqual(meta["beats"], [])
        validate_role_output("plot", contract, plot, meta)
        self.assertEqual(plot_structure(plot, contract)["key_scenes"], ["An encounter", "A consequence"])
        cards = "## Scene 1\n### Required Beats\n1. New actual event\n### End state\n- Not an event\n## Scene 2\n### Required beats\n- Actual consequence\n"
        events = build_nk_payload(contract, cards)["eventSequence"]
        self.assertEqual([row["description"] for row in events], ["New actual event", "Actual consequence"])
        with self.assertRaisesRegex(ContractError, "NK_EVENT_SEQUENCE_MISSING"):
            build_nk_payload(contract, "## Scene 1\nNo events")
        contract["unit"]["kind"] = "scene"
        # List count alone cannot establish narrative scope against the source.
        validate_role_output("plot", contract, plot, meta)
        contract["story"]["required_beats"] = [{"beat_id": "B01", "goal": "Required outcome"}]
        validate_work_unit(contract)
        contract["story"]["required_beats"].append({"beat_id": "B01", "goal": "Duplicate"})
        with self.assertRaisesRegex(ContractError, "REQUIRED_BEAT_INVALID"):
            validate_work_unit(contract)

    def test_production_preparation_resolves_episode_arc_and_reads_previous_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            contents = {
                "04_chapter_design/arc_index.md": "| Arc | Title | Episodes | Purpose |\n|---|---|---|---|\n| 01 | First | 1-5 | Start |\n| 02 | Second | 6-10 | Develop |\n",
                "04_chapter_design/arc_01.md": "First Arc",
                "04_chapter_design/arc_02.md": "Second Arc",
                "04_chapter_design/arc_02_episode_details.md": "Episode seven purpose",
                "94_runtime/current_state.md": "Next: ep007",
                "07_draft/manuscript_index.md": "ep006 drafted",
                "07_draft/episodes/ep006.md": "Previous chapter text",
                "92_style_engine/character_voice_samples.md": "Voice samples",
                "90_canon/character_bible.md": "Character facts",
            }
            for relative, text in contents.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            self.assertEqual(resolve_arc(root, "ep007").name, "arc_02.md")
            self.assertEqual(resolve_arc(root, "custom-scene", "04_chapter_design/arc_01.md").name, "arc_01.md")
            context = read_production_preparation(root, {"unit": {"id": "ep007", "kind": "episode"}, "story": {}})
            self.assertEqual(context["documents"]["07_draft/episodes/ep006.md"], "Previous chapter text")
            self.assertNotIn("04_chapter_design/arc_01.md", context["documents"])
            self.assertEqual(len(context["source_hashes"]), 7)
            with self.assertRaisesRegex(ContractError, "ARC_INDEX_INVALID"):
                resolve_arc(root, "ep020")
            (root / "07_draft/episodes/ep006.md").unlink()
            with self.assertRaisesRegex(ContractError, "PRODUCTION_CONTEXT_MISSING"):
                read_production_preparation(root, {"unit": {"id": "ep007", "kind": "episode"}, "story": {}})

    def test_live_role_packet_requires_live_mode_and_frozen_contract(self):
        packet = build_role_packet("plot", self.contract_path, {
            "canon_scope": self.project / "90_canon/canon.md",
            "source_anchors": self.project / "06_plot/source_anchors.md",
        }, mode="live")
        self.assertEqual(packet["execution_mode"], "LIVE_REQUEST_READY")
        self.assertEqual(packet["contract_sha256"], sha(self.contract_path.read_bytes()))
        with self.assertRaisesRegex(ContractError, "ROLE_MODE_INVALID"):
            build_role_packet("plot", self.contract_path, {
                "canon_scope": self.project / "90_canon/canon.md",
                "source_anchors": self.project / "06_plot/source_anchors.md",
            }, mode="pretend-live")

    def test_nk_receives_ordered_events_and_reflection_enters_brief(self):
        contract = load_contract(self.contract_path)
        cards = (
            "# Scene Cards — SYNTHETIC-INSERT-01\n\n## Scene 1\n\n### Required beats\n"
            "- 甲 asks clearly\n- 乙 answers\n- 丙 observes\n- 丁 chooses a next step\n"
        )
        payload = build_nk_payload(contract, cards)
        self.assertEqual(len(payload["eventSequence"]), 4)
        self.assertIn("甲 asks clearly", payload["eventSequence"][0]["description"])
        self.assertEqual(len(payload["perspectives"]), 1)
        task = payload["perspectives"][0]
        self.assertEqual(task["narrator"], "甲")
        self.assertEqual(len(task["characterSnapshots"]), 4)
        self.assertTrue(task["eventObjective"])
        result, mapping = map_reflection_to_brief("# Brief", {"perspectives": [{"reflection": "我只能写亲眼所见。"}]}, {"status": "FIXTURE_ONLY"})
        self.assertIn("我只能写亲眼所见。", result)
        self.assertIn(mapping["response_sha256"], result)
        with self.assertRaisesRegex(ContractError, "NK_RESPONSE_INVALID"):
            map_reflection_to_brief("# Brief", {"perspectives": []}, {"status": "FIXTURE_ONLY"})
        with self.assertRaisesRegex(ContractError, "NK_PROVIDER_RECEIPT_REQUIRED"):
            map_reflection_to_brief("# Brief", {"perspectives": [{"reflection": "结果"}]}, {})
        response = {"perspectives": [{"reflection": "经核对的反思。"}]}
        response_hash = sha(json.dumps(response, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        live_receipt = {
            "status": "LIVE_ACCEPTED", "request_id": "local-id", "provider_request_id": "provider-id",
            "model": "deepseek-flash", "finish_reason": "stop", "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "http_status": 200, "validated_response_sha256": response_hash, "raw_response_sha256": "raw-hash",
        }
        self.assertEqual(map_reflection_to_brief("# Brief", response, live_receipt)[1]["source_status"], "LIVE_ACCEPTED")
        live_receipt["validated_response_sha256"] = "wrong"
        with self.assertRaisesRegex(ContractError, "NK_PROVIDER_RESPONSE_HASH_MISMATCH"):
            map_reflection_to_brief("# Brief", response, live_receipt)

    def test_prose_packet_is_limited_to_brief_and_voice_samples(self):
        contract = load_contract(self.contract_path)
        workdir = self.project / "role-packet"
        workdir.mkdir(parents=True, exist_ok=True)
        try:
            paths = {}
            for name, content in (("plot", "PLOT"), ("cards", "CARDS"), ("brief", "BRIEF"), ("canon", "CANON"), ("anchors", "ANCHORS"), ("style", "STYLE"), ("voices", "VOICES"), ("nk", "NK REFLECTION")):
                path = workdir / f"{name}.md"
                path.write_text(content, encoding="utf-8")
                paths[name] = path
            voices = "\n\n".join(f"### {name}\nSample voice" for name in contract["story"]["characters_in_scene"])
            voices += "\n\n### Unrelated character\nPrivate unrelated sample"
            brief = "# Brief\n## Voice References\n" + "\n".join(
                f"- {name} — see voice sample" for name in contract["story"]["characters_in_scene"])
            view = build_prose_input_view(contract, brief, voices)
            self.assertEqual(set(view["inputs"]), {"brief", "voice_samples"})
            self.assertNotIn("contract", view)
            self.assertEqual(view["execution_contract"]["target_visible_chars"], 1500)
            self.assertNotIn("character_knowledge_boundary_ref", json.dumps(view, ensure_ascii=False))
            self.assertNotIn("Private unrelated sample", view["inputs"]["voice_samples"])
            with self.assertRaisesRegex(ContractError, "ROLE_INPUT_SCOPE_VIOLATION"):
                build_role_packet("plot", self.contract_path, {"canon_scope": paths["canon"], "source_anchors": paths["anchors"], "future_route": paths["canon"]})
        finally:
            for path in workdir.glob("*"):
                path.unlink()
            workdir.rmdir()

    def test_prose_cannot_unlock_with_fixture_or_unaccepted_stage(self):
        receipts = [{"role": role, "work_id": "W", "status": "CONTROLLER_ACCEPTED", "contract_sha256": "hash", "provider_request_ids": [f"fixture-id-{role}"], "controller_accept_ref": "TEST_ONLY"} for role in ("plot", "cards", "brief")]
        with self.assertRaisesRegex(ContractError, "CNW_FIXTURE_CANNOT_UNLOCK_PROSE"):
            verify_stage_chain(receipts)
        with self.assertRaisesRegex(ContractError, "ROLE_ACCEPTANCE_EVIDENCE_MISSING"):
            role_receipt("plot", {"work_id": "W"}, "plot", status="CONTROLLER_ACCEPTED")

    def test_plot_card_brief_cannot_drop_beat_ids_or_budget(self):
        contract = load_contract(self.contract_path)
        with self.assertRaisesRegex(ContractError, "ROLE_UNKNOWN"):
            validate_role_output("typo", contract, "nonempty output")
        valid = "\n".join([
            "## Quick Header", "## Active Canon", "## Scene-by-Scene Instructions", "## Voice References",
            "## Hard Constraints", "## Style Targets", "## What NOT to include in the prose", "NK Perspective Reflection",
            "CNW_CONTRACT target_visible_chars=1500 min_visible_chars=1200 max_visible_chars=1800",
            *[f"CNW_BEAT {beat['beat_id']} budget_visible_chars={beat['budget_visible_chars']}" for beat in contract["story"]["required_beats"]],
        ])
        validate_role_output("brief", contract, valid)
        with self.assertRaisesRegex(ContractError, "ROLE_TEMPLATE_SECTION_MISSING"):
            validate_role_output("brief", contract, valid.replace("## Active Canon", "## Missing"))
        with self.assertRaisesRegex(ContractError, "ROLE_BEAT_ID_DROPPED"):
            validate_role_output("brief", contract, valid.replace("B02", "MISSING"))
        with self.assertRaisesRegex(ContractError, "ROLE_BEAT_BUDGET_MISMATCH"):
            validate_role_output("brief", contract, valid.replace("CNW_BEAT B02 budget_visible_chars=750", "CNW_BEAT B02 budget_visible_chars=751"))

    def test_role_prompt_sources_match_captured_cnw_manifest_blobs(self):
        manifest = json.loads((ROOT / "runtime/reference/cnw_97ad71fe5e5e/CNW_LOCAL_REFERENCE_MANIFEST.json").read_text(encoding="utf-8"))
        upstream = {item["source_path"]: item["upstream_git_blob"] for item in manifest["references"]}
        prompt_sources = {
            "plot.md": ["templates/06_plot/plot.template.md"],
            "scene_cards.md": ["templates/05_scene_cards/scene_cards.template.md"],
            "brief.md": ["templates/07_draft/writing_brief.template.md"],
            "prose.md": ["templates/config/ai_roles.template.yml", "templates/07_draft/writing_brief.template.md"],
        }
        for prompt_name, source_paths in prompt_sources.items():
            prompt = (ROOT / "prompts/cnw" / prompt_name).read_text(encoding="utf-8")
            actual_blobs = set(re.findall(r"^\s*(?:upstream_blob|blob): ([0-9a-f]+)$", prompt, re.MULTILINE))
            self.assertEqual(actual_blobs, {upstream[source_path] for source_path in source_paths}, prompt_name)

    def test_critics_hook_routes_through_existing_cost_guarded_runner(self):
        plot_input = self.project / "plot.md"
        plot_input.write_text("Synthetic plot input.", encoding="utf-8")
        command = build_plan_critique_command("python.exe", str(plot_input), "synthetic-plot-critique")
        self.assertEqual(Path(command[1]), ROOT / "tools/p2_06_critics_run.py")
        self.assertIn("--action", command)
        self.assertIn("plan-critique", command)
        self.assertIn("--run-name", command)
        self.assertNotIn("critics_bridge.py", command[1])

    def test_critics_receipt_binds_source_output_and_pinned_build(self):
        source = self.base / "synthetic-plot.md"
        source.write_text("Synthetic plot input.", encoding="utf-8")
        build_id = json.loads((ROOT / "patches/critics/PATCH_INDEX.json").read_text(encoding="utf-8"))["runtime_build_id"]
        run = self.base / "runs/.synthetic-critics-receipt"
        run.mkdir(parents=True, exist_ok=False)
        output = run / "critique.json"
        try:
            output.write_text('{"fixture":true}\n', encoding="utf-8")
            receipt = {
                "action": "plan-critique", "status": "SUCCEEDED", "model": "deepseek-flash",
                "base_url": "https://api.deepseek.com/v1", "build": f"runtime/patched/CritiCS/{build_id}",
                "input_sha256": sha(source.read_bytes()).upper(), "output_sha256": sha(output.read_bytes()).upper(),
            }
            verified = verify_plan_receipt(receipt, action="plan-critique", input_path=source, output_path=output)
            self.assertEqual(verified["status"], "FOUND_AND_HASH_VERIFIED")
            receipt["build"] = "unpatched"
            with self.assertRaisesRegex(ContractError, "CRITICS_RECEIPT_METHOD_MISMATCH"):
                verify_plan_receipt(receipt, action="plan-critique", input_path=source, output_path=output)
        finally:
            output.unlink(missing_ok=True)
            run.rmdir()


if __name__ == "__main__":
    unittest.main()
