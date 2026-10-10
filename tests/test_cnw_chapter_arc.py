"""Finite Chapter/Arc offline evidence. Ordinary executors run; APIs are mocked."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_cnw_recovery as recovery_fixture, test_cnw_maintenance as maintenance_fixture
from tools import cnw_runner as r, cnw_roles as roles, cnw_arc as arc, cnw_maintenance as maintenance
from tools.cnw_contract import ContractError


def mock_receipt(run, request, content, identifier):
    path = run / f"artifacts/{identifier}.request.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps({"messages": request["messages"]}, ensure_ascii=False).encode())
    raw = path.with_suffix(".raw.json")
    raw.write_bytes(json.dumps({"choices": [{"message": {"content": content}}]}, ensure_ascii=False).encode())
    row = {"request_id": identifier, "provider_request_id": identifier, "status": "SUCCEEDED", "mode": "MOCK_ONLY",
        "stage": request["stage"], "role_id": request["role_id"],
        "request_path": path.relative_to(run).as_posix(), "request_sha256": r.sha(path.read_bytes()),
        "input_sha256": r.sha(json.dumps(request["messages"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()),
        "raw_response_path": raw.relative_to(run).as_posix(), "raw_response_sha256": r.sha(raw.read_bytes()),
        "output_sha256": r.sha(content.encode())}
    state = r.load_state(run)
    state["provider_requests"].append(row)
    r.save_state(run, state)
    return content, row


class ChapterTests(unittest.TestCase):
    def test_ordinary_two_scene_chapter_continuation_refine_and_review(self):
        case = recovery_fixture.RecoveryTests("test_resume_real_dispatcher_reuses_and_checks_every_stage")
        case.setUp()
        self.addCleanup(case.doCleanups)
        contract = case.contract
        contract["unit"].update(kind="episode", planning_mode="author_plot", min_visible_chars=1500, target_visible_chars=1800, max_visible_chars=4000)
        contract["story"]["required_beats"] = []
        for name in ("contracts/unit.json", "runs/MOCK-RECOVERY/artifacts/contract.json"):
            case.write(name, json.dumps(contract, ensure_ascii=False))
        state = r.load_state(case.run)
        state.update(unit_kind="episode", contract_sha256=r.sha((case.project / "contracts/unit.json").read_bytes()), literary_source_hashes=r.literary_source_freeze(contract, case.project))
        r.save_state(case.run, state)
        plot = "\n".join(h + "\nMOCK chapter" for h in roles.ROLE_REQUIRED_SECTIONS["plot"])
        plot = plot.replace("## Key Scenes\nMOCK chapter", "## Key Scenes\n- S1 借伞\n- S2 归灯")
        plot = plot.replace("## Required Story Beats\nMOCK chapter", "## Required Story Beats\n- B01 借出伞\n- B02 送回灯")
        cards = "\n".join("## Scene S" + str(i) + "\n" + "\n".join(h + "\n- B0" + str(i) + " MOCK action" for h in roles.ROLE_REQUIRED_SECTIONS["cards"]) for i in (1, 2))
        brief = "\n".join(h + "\nMOCK chapter" for h in roles.ROLE_REQUIRED_SECTIONS["brief"])
        brief = brief.replace("## Scene-by-Scene Instructions\nMOCK chapter", "## Scene-by-Scene Instructions\nS1 借伞 → S2 归灯，保留顺序与两场动作。")
        brief = brief.replace("## Voice References\nMOCK chapter", "## Voice References\n- 甲")
        first = "甲把伞推给乙，自己站回屋檐下。" * 50
        second = "乙在灯边停住，递回干布，又把灯移到甲的脚边。" * 50
        prose = first + "\n\n" + second
        requests, cache = [], {}
        refine_count = 0
        def provider(run, **request):
            nonlocal refine_count
            key = json.dumps(request, ensure_ascii=False, sort_keys=True)
            if key in cache:
                content, receipt = cache[key]
                r._receipt_content(run, receipt)
                r.reactivate_receipt(run, receipt)
                return content, receipt
            requests.append(request)
            stage, role = request["stage"], request["role_id"]
            if stage in {"plot", "scene_cards", "writing_brief"}:
                content = {"plot": plot, "scene_cards": cards, "writing_brief": brief}[stage]
            elif stage == "prose":
                content = first if role == "prose_agent_1" else second
            elif stage == "multi_lens_review":
                content = json.dumps({"lens_id": role, "findings": [{"finding_id": "I1", "severity": "P2", "issue": "MOCK rhythm", "evidence": "甲把伞推给乙", "recommendation": "Adjust rhythm"}] if role == "style" else []})
            elif stage == "adversarial_verify":
                packet = json.loads(request["messages"][1]["content"])
                content = json.dumps({"verifier_id": role, "votes": [{"finding_id": packet["finding_id"], "verdict": "not_refuted"}]})
            elif stage == "completeness_critic":
                content = '{"candidate_findings":[]}'
            elif stage == "refine":
                refine_count += 1
                content = "甲先把伞推给乙。乙归灯。" if refine_count == 1 else prose.replace("甲把伞", "甲先把伞")
            elif stage == "re_review":
                content = json.dumps({"lens_id": role, "findings": []})
            else:
                raise AssertionError(stage)
            cache[key] = mock_receipt(run, request, content, "CHAPTER-MOCK-" + str(len(requests)))
            return cache[key]
        with patch.object(r, "cnw_live_call", side_effect=provider):
            case.execute()
            count = len(requests)
            case.execute()
            self.assertEqual(len(requests), count)
        cards_input = json.loads(next(x for x in requests if x["stage"] == "scene_cards")["messages"][1]["content"])
        self.assertEqual(cards_input["materials"]["06_plot/<work_id>_plot.md"].strip(), plot.strip())
        brief_input = json.loads(next(x for x in requests if x["stage"] == "writing_brief")["messages"][1]["content"])
        self.assertEqual(brief_input["materials"]["05_scene_cards/<work_id>_scene_cards.md"].strip(), cards.strip())
        prose_input = json.loads(next(x for x in requests if x["role_id"] == "prose_agent_1")["messages"][1]["content"])
        self.assertEqual(set(prose_input), {"writing_brief", "voice_samples"})
        self.assertNotIn("UNUSED", prose_input["voice_samples"])
        continuation = next(x for x in requests if x["role_id"] == "prose_agent_2")
        self.assertIn("同一章", continuation["messages"][0]["content"])
        self.assertIn("各场顺序", continuation["messages"][0]["content"])
        refinements = [x for x in requests if x["stage"] == "refine"]
        self.assertEqual(len(refinements), 2)
        self.assertTrue(all(x["output_cap"] > 4096 and "整章" in x["messages"][0]["content"] for x in refinements))
        restoration = json.loads(refinements[1]["messages"][1]["content"])
        self.assertEqual(restoration["brief_constraints"].strip(), brief.strip())
        self.assertEqual(restoration["revision_base"].strip(), prose.strip())
        final = r._read_stage_text(case.run, r.load_state(case.run), "refine")
        self.assertIn("伞", final)
        self.assertIn("灯", final)
        self.assertEqual([x["role_id"] for x in requests if x["stage"] == "re_review"], ["style"])


class ArcTests(unittest.TestCase):
    def setUp(self):
        self.case = maintenance_fixture.MaintenanceTests("test_full_audit_real_materials_method_and_canon_protection")
        # Fixture setup is reused; its outer workflow is never mocked here.
        self.case.setUp()
        self.addCleanup(self.case.tearDown)
        self.root = self.case.root
        self.requests = []
        self.status = "pass"
        for name, text in {"04_chapter_design/arc_01.md": "# Arc 01\n## Range\nep01 – ep02\n## Purpose\nMOCK character change\n",
            "04_chapter_design/arc_01_episode_details.md": "ep01: borrow bell. ep02: return bell.",
            "00_meta/manuscript_review_rubric.md": "MOCK project rubric"}.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode())

    def provider(self, run, **request):
        self.requests.append(request)
        if request["stage"] == "project_arc_review":
            value = {"status": self.status, "review_markdown": "\n".join("## " + h + "\nMOCK review" for h in maintenance.ARC_SECTIONS) + "\nStatus: " + self.status}
        else:
            value = {"brief_markdown": "\n".join("## " + h + "\nMOCK Arc handoff" for h in (*maintenance.HANDOFF_SECTIONS, "Pipeline Context Pack"))}
        return mock_receipt(run, request, json.dumps(value), "ARC-MOCK-" + str(len(self.requests)))

    def test_arc_end_uses_all_drafts_and_handoff_preserves_originals(self):
        canon = (self.root / "90_canon/canon.md").read_bytes()
        old = (self.root / "93_exports/handoff_brief.md").read_bytes()
        with patch.object(r, "cnw_live_call", side_effect=self.provider):
            result = arc.review_arc(self.root, "04_chapter_design/arc_01.md", last_episode="ep02")
        self.assertEqual(result["arc_status"], "pass")
        payload = json.loads(self.requests[0]["messages"][1]["content"])
        self.assertIn("07_draft/episodes/ep01.md", payload["project_sources"])
        self.assertIn("07_draft/episodes/ep02.md", payload["project_sources"])
        self.assertIn("04_chapter_design/arc_01_episode_details.md", payload["project_sources"])
        self.assertIn("部単位チェック", self.requests[0]["messages"][0]["content"])
        self.assertEqual((self.root / "90_canon/canon.md").read_bytes(), canon)
        self.assertEqual((self.root / result["handoff"]["archive"]).read_bytes(), old)
        with patch.object(r, "cnw_live_call", side_effect=AssertionError("no duplicate Arc call")):
            repeated = arc.review_arc(self.root, "04_chapter_design/arc_01.md", last_episode="ep02")
        self.assertEqual(repeated["provider_call"], "reused")
        self.assertEqual(repeated["handoff"]["provider_call"], "reused")

    def test_mid_arc_missing_drafts_and_prior_gate_do_not_call_model(self):
        with patch.object(r, "cnw_live_call", side_effect=AssertionError("no calls for inapplicable Arc")):
            self.assertEqual(arc.review_arc(self.root, "04_chapter_design/arc_01.md", last_episode="ep01")["status"], "ARC_NOT_AT_END")
            self.assertEqual(arc.review_arc(self.root, "04_chapter_design/arc_01.md", prior_gate="REVISION_REQUIRED")["status"], "ARC_REVIEW_BLOCKED_BY_PRIOR_GATE")
            (self.root / "07_draft/episodes/ep01.md").unlink()
            self.assertEqual(arc.review_arc(self.root, "04_chapter_design/arc_01.md", last_episode="ep02")["status"], "ARC_DRAFTS_INCOMPLETE")

    def test_arc_revise_does_not_start_next_arc(self):
        self.status = "revise"
        with patch.object(r, "cnw_live_call", side_effect=self.provider):
            result = arc.review_arc(self.root, "04_chapter_design/arc_01.md", handoff=False)
        self.assertEqual(result["arc_status"], "revise")
        self.assertFalse(result["next_arc_started"])
        self.assertFalse(result["user_creative_accepted"])


if __name__ == "__main__":
    unittest.main()
