import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from tools.cnw_contract import ContractError, load_contract
from tools.cnw_critics_adapter import build_plan_critique_command, verify_plan_receipt
from tools.cnw_nk_adapter import build_nk_payload, map_reflection_to_brief
from tools.cnw_roles import build_prose_input_view, build_role_packet, role_receipt, validate_role_output, verify_stage_chain


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "workspace/cangqi/contracts/CQ-J19-INSERT-01.work_unit_contract.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class AdapterTests(unittest.TestCase):
    def test_nk_receives_ordered_events_and_reflection_enters_brief(self):
        contract = load_contract(CONTRACT_PATH)
        payload = build_nk_payload(contract)
        self.assertEqual([event["label"] for event in payload["eventSequence"]], ["B01", "B02", "B03", "B04"])
        self.assertEqual(len(payload["perspectives"]), 1)
        task = payload["perspectives"][0]
        self.assertEqual(task["narrator"], "君天离")
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
        contract = load_contract(CONTRACT_PATH)
        workdir = ROOT / "workspace/cangqi/.w04-test-packet"
        workdir.mkdir(parents=True, exist_ok=True)
        try:
            paths = {}
            for name, content in (("plot", "PLOT"), ("cards", "CARDS"), ("brief", "BRIEF"), ("canon", "CANON"), ("anchors", "ANCHORS"), ("style", "STYLE"), ("voices", "VOICES"), ("nk", "NK REFLECTION")):
                path = workdir / f"{name}.md"
                path.write_text(content, encoding="utf-8")
                paths[name] = path
            view = build_prose_input_view(contract, "BRIEF", "VOICES")
            self.assertEqual(set(view["inputs"]), {"brief", "voice_samples"})
            self.assertNotIn("contract", view)
            self.assertEqual(view["execution_contract"]["target_visible_chars"], 1500)
            self.assertNotIn("character_knowledge_boundary_ref", json.dumps(view, ensure_ascii=False))
            with self.assertRaisesRegex(ContractError, "ROLE_INPUT_SCOPE_VIOLATION"):
                build_role_packet("plot", CONTRACT_PATH, {"canon_scope": paths["canon"], "source_anchors": paths["anchors"], "future_route": paths["canon"]})
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
        contract = load_contract(CONTRACT_PATH)
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
            validate_role_output("brief", contract, valid.replace("B03", "MISSING"))
        with self.assertRaisesRegex(ContractError, "ROLE_BEAT_BUDGET_MISMATCH"):
            validate_role_output("brief", contract, valid.replace("CNW_BEAT B03 budget_visible_chars=500", "CNW_BEAT B03 budget_visible_chars=501"))

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
        command = build_plan_critique_command(
            "python.exe",
            "workspace/cangqi/06_plot/ep001_plot.v1.md",
            "w04-fixture-plot-critique",
        )
        self.assertEqual(Path(command[1]), ROOT / "tools/p2_06_critics_run.py")
        self.assertIn("--action", command)
        self.assertIn("plan-critique", command)
        self.assertIn("--run-name", command)
        self.assertNotIn("critics_bridge.py", command[1])

    def test_critics_receipt_binds_source_output_and_pinned_build(self):
        source = ROOT / "workspace/cangqi/06_plot/ep001_plot.v1.md"
        build_id = json.loads((ROOT / "patches/critics/PATCH_INDEX.json").read_text(encoding="utf-8"))["runtime_build_id"]
        run = ROOT / "runs/.w04-test-critics-receipt"
        run.mkdir(exist_ok=False)
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
