"""CNW three-layer review: two deterministic lint layers plus a semantic
multi-lens / adversarial / completeness chain.

This module holds the *author-published* review contract (five lenses read the
author's own source files; three adversarial verifiers refute by default;
one completeness critic reads the whole draft plus every prior disposition).

Offline helpers keep the explicit ``MOCK_ONLY`` identity used by the W07
fixtures. The live request builders only build prompts and packets; the runner
performs the cost-guarded provider calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .cnw_lint import lint
except ImportError:
    from cnw_lint import lint

ROOT = Path(__file__).resolve().parents[1]

# --- Author-published Lens contract (THREE_LAYER_REVIEW.md:69-77) ---
LENSES: dict[str, tuple[str, ...]] = {
    "style": ("style_guide", "forbidden_patterns"),
    "character": ("character_bible", "voice_samples"),
    "plot": ("scene_cards", "writing_brief"),
    "canon": ("glossary", "timeline", "world_bible"),
    "story_specific": ("project_specific_canon",),
}
REQUIRED_SOURCES = {name: set(sources) for name, sources in LENSES.items()}

# --- Author-published verifier framings (THREE_LAYER_REVIEW.md:112) ---
VERIFIERS = (
    "correctness",
    "character_consistency",
    "continuity_plausibility",
)

LENS_GOALS = {
    "style": "核验节奏、密度、信息重复与 style_guide / forbidden_patterns 的冲突；只报告可定位的语言问题。",
    "character": "核验人物声音漂移、台词行为越界与称呼错误；只依据 character_bible 与 voice_samples。",
    "plot": "核验 Scene Card 与 Writing Brief 中每个必需节拍、Hook 与连接是否真正落在正文。",
    "canon": "只用 glossary / timeline / world_bible 核验世界事实与术语；不得把推断当事实。",
    "story_specific": "核验项目专属 Canon 中的场景功能、可演性与禁区；不得照抄其他作品的角色设定。",
}
VERIFIER_GOALS = {
    "correctness": "从事实正确性角度尝试反驳该 finding；证据不足时默认反驳。",
    "character_consistency": "从人物一致性与知识边界角度尝试反驳该 finding；证据不足时默认反驳。",
    "continuity_plausibility": "从连续性与情节可信度角度尝试反驳该 finding；证据不足时默认反驳。",
}


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Offline fixtures (MOCK_ONLY; never live evidence)
# --------------------------------------------------------------------------
def dry_run_cost_reservation(tasks: list[dict]) -> dict:
    """Exercise the shared P2 cost guard estimate/ledger boundary without writing reservations."""
    try:
        from . import p2_cost_guard as guard
    except ImportError:
        import p2_cost_guard as guard
    policy, pricing = guard.load_config()
    ledger = json.loads(guard.LEDGER.read_text(encoding="utf-8-sig")) if guard.LEDGER.is_file() else {"requests": [], "limit": policy["estimated_campaign_limit"]}
    committed = guard.amounts(ledger)
    reserved = []
    for task in tasks:
        amount = guard.estimate(task["input_token_cap"], task["output_token_cap"], pricing)
        committed += amount
        if committed > __import__("decimal").Decimal(str(ledger["limit"])):
            raise ValueError("COST_RESERVATION_WOULD_EXCEED_LIMIT")
        reserved.append({"task_key": task["task_key"], "purpose": task["purpose"], "input_token_cap": task["input_token_cap"], "output_token_cap": task["output_token_cap"], "reserved_cny": guard.money(amount), "reservation_status": "DRY_RUN_ONLY"})
    return {"interface": "tools/p2_cost_guard.py:estimate+amounts+campaign_limit", "execution_mode": "MOCK_ONLY", "ledger_written": False, "provider_request_ids": [], "reservations": reserved}


def lens_packet(name: str, draft: str, sources: dict[str, str]) -> dict:
    if name not in LENSES:
        raise ValueError("unknown lens")
    missing = REQUIRED_SOURCES[name] - set(sources)
    if missing:
        raise ValueError(f"LENS_SOURCES_MISSING:{name}:{','.join(sorted(missing))}")
    selected = {key: sources[key] for key in LENSES[name] if key in sources}
    return {"lens_id": name, "draft": draft, "sources": selected, "input_sha256": digest(json.dumps({"lens_id": name, "draft": draft, "sources": selected}, ensure_ascii=False, sort_keys=True)), "execution_mode": "MOCK_ONLY", "provider_request_id": None}


def mock_lens(packet: dict) -> dict:
    name = packet["lens_id"]
    return {"lens_id": name, "input_sha256": packet["input_sha256"], "input_packet": packet, "execution_mode": "MOCK_ONLY", "provider_request_id": None, "findings": [], "simulated_output": {"scope": name, "assessment": "fixture output; no semantic/model judgment performed"}, "simulation": "distinct offline injected transport; no provider call"}


def verifier_packets(findings: list[dict], draft: str, sources: dict[str, str] | None = None) -> list[dict]:
    return [{"verifier_id": v, "challenge_angle": v, "findings": findings, "draft": draft, "sources": sources or {}, "input_sha256": digest(json.dumps({"verifier_id": v, "challenge_angle": v, "findings": findings, "draft": draft, "sources": sources or {}}, ensure_ascii=False, sort_keys=True)), "execution_mode": "MOCK_ONLY", "provider_request_id": None} for v in VERIFIERS]


def tally_verifiers(verdicts: list[dict]) -> dict:
    if len(verdicts) != 3 or len({x.get("verifier_id") for x in verdicts}) != 3:
        raise ValueError("exactly three isolated verifier identities required")
    if {x.get("verifier_id") for x in verdicts} != set(VERIFIERS):
        raise ValueError("unexpected verifier identity")
    if any(x.get("execution_mode") != "MOCK_ONLY" or x.get("provider_request_id") is not None for x in verdicts):
        raise ValueError("offline verifier cannot claim provider identity")
    grouped: dict[str, list[str]] = {}
    per_verifier: dict[str, set] = {}
    for v in verdicts:
        seen = set()
        for item in v.get("votes", []):
            finding_id = item.get("finding_id")
            if finding_id in seen:
                raise ValueError("duplicate vote by verifier for a finding")
            seen.add(finding_id)
            if item.get("verdict") not in {"not_refuted", "refuted", "uncertain"}:
                raise ValueError("invalid verifier verdict")
            grouped.setdefault(finding_id, []).append(item["verdict"])
        per_verifier[v["verifier_id"]] = seen
    if per_verifier and len({tuple(sorted(x)) for x in per_verifier.values()}) != 1:
        raise ValueError("each verifier must vote once on every finding")
    return {k: {"not_refuted": sum(x == "not_refuted" for x in votes), "status": "CONFIRMED" if sum(x == "not_refuted" for x in votes) >= 2 else "REFUTED_OR_UNCERTAIN"} for k, votes in grouped.items()}


def completeness_packet(draft: str, findings: list[dict], rejected: list[dict], sources: dict[str, str] | None = None) -> dict:
    packet = {"draft": draft, "confirmed_findings": findings, "rejected_findings": rejected, "sources": sources or {}, "execution_mode": "MOCK_ONLY", "provider_request_id": None}
    packet["input_sha256"] = digest(json.dumps(packet, ensure_ascii=False, sort_keys=True))
    return packet


def review_offline(draft: str, sources: dict[str, str], verifier_votes: dict[str, list[str]] | None = None, completeness_findings: list[dict] | None = None, cost_reserver=dry_run_cost_reservation) -> dict:
    if not callable(cost_reserver):
        raise ValueError("COST_RESERVATION_INTERFACE_REQUIRED")
    tasks = [{"task_key": f"lens:{name}", "purpose": f"W07 offline {name} lens", "input_token_cap": 12000, "output_token_cap": 2500} for name in LENSES]
    tasks += [{"task_key": f"verifier:{name}", "purpose": f"W07 offline {name}", "input_token_cap": 8000, "output_token_cap": 1200} for name in VERIFIERS]
    tasks += [{"task_key": "completeness", "purpose": "W07 offline completeness", "input_token_cap": 12000, "output_token_cap": 2000}]
    reservation = cost_reserver(tasks)
    if reservation.get("execution_mode") != "MOCK_ONLY" or reservation.get("ledger_written") is not False or reservation.get("provider_request_ids") != [] or len(reservation.get("reservations", [])) != len(tasks):
        raise ValueError("COST_RESERVATION_BOUNDARY_INVALID")
    lenses = [mock_lens(lens_packet(n, draft, sources)) for n in LENSES]
    raw = []
    for layer in ("surface", "structural"):
        raw.extend({**f, "finding_id": f"{layer}-{i+1}", "layer": layer} for i, f in enumerate(lint(draft, layer)["findings"]))
    votes = verifier_votes or {}
    vpack = verifier_packets(raw, draft, sources)
    verdicts = [{**p, "votes": [{"finding_id": f["finding_id"], "verdict": votes.get(p["verifier_id"], [])[i] if i < len(votes.get(p["verifier_id"], [])) else "uncertain"} for i, f in enumerate(raw)]} for p in vpack]
    vote_result = tally_verifiers(verdicts) if raw else {}
    votes_by_id = {}
    for verdict in verdicts:
        for vote in verdict["votes"]:
            votes_by_id.setdefault(vote["finding_id"], []).append(vote["verdict"])
    confirmed = []
    rejected = []
    for finding in raw:
        statuses = votes_by_id.get(finding["finding_id"], [])
        item = {**finding, "verifier_votes": statuses}
        (confirmed if sum(v == "not_refuted" for v in statuses) >= 2 else rejected).append(item)
    complete = completeness_packet(draft, confirmed, rejected, sources)
    complete["candidate_findings"] = completeness_findings or []
    complete["input_sha256"] = digest(json.dumps({k: v for k, v in complete.items() if k != "input_sha256"}, ensure_ascii=False, sort_keys=True))
    all_hashes = [x["input_sha256"] for x in lenses]
    if len(set(all_hashes)) != 5:
        raise AssertionError("lens packets must be distinct")
    return {"execution_mode": "MOCK_ONLY", "provider_request_ids": [], "cost_reservation": reservation, "lenses": lenses, "lint_findings": raw, "verifiers": verdicts, "verifier_summary": vote_result, "completeness": complete, "text_modified": False, "review_status": "OFFLINE_SIMULATION_ONLY"}


# --------------------------------------------------------------------------
# Live request builders (packets only; the runner performs provider calls)
# --------------------------------------------------------------------------
def build_lens_input(lens_id: str, full_draft: str, sources: dict[str, str]) -> dict:
    """Build one Lens packet from the author-defined source list.

    Extra project material may be supplied per lens but never replaces a
    required author source. Each Lens is an isolated context.
    """
    if lens_id not in LENSES:
        raise ValueError("unknown lens")
    missing = REQUIRED_SOURCES[lens_id] - set(sources)
    if missing:
        raise ValueError(f"LENS_SOURCES_MISSING:{lens_id}:{','.join(sorted(missing))}")
    selected = {name: sources[name] for name in LENSES[lens_id]}
    packet = {
        "lens_id": lens_id,
        "draft": full_draft,
        "sources": selected,
        "author_lens_definition": LENS_GOALS[lens_id],
        "execution_mode": "LIVE_REQUEST_READY",
    }
    feedback = sources.get(f"lens_feedback:{lens_id}")
    if feedback:
        packet["additional_review_instructions"] = feedback
    packet["input_sha256"] = digest(json.dumps(packet, ensure_ascii=False, sort_keys=True))
    return packet


def lens_messages(packet: dict) -> list[dict]:
    system = (
        "你是独立的 " + packet["lens_id"] + " Lens。" + packet["author_lens_definition"] +
        " 只使用 sources 中本岗位来源与完整 draft。必须输出 JSON："
        '{"lens_id":"<id>","findings":[{"finding_id":"F1","severity":"major|minor","evidence":"原文短引","issue":"具体问题","recommendation":"可执行修改"}]}。'
        "无问题时 findings 为空。不要读取其他 Lens 的结论，不要泛泛评价。"
        "如有 additional_review_instructions，执行其中本岗位从过去遗漏总结的检查项；仍必须以当前 draft 和 sources 为证据。"
    )
    user = json.dumps({k: v for k, v in packet.items() if k != "input_sha256"}, ensure_ascii=False, sort_keys=True)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_verifier_packet(finding: dict, verifier_id: str, full_draft: str, evidence: Any) -> dict:
    if verifier_id not in VERIFIERS:
        raise ValueError("unknown verifier")
    return {
        "finding_id": finding.get("finding_id"),
        "verifier_id": verifier_id,
        "claim": finding,
        "counter_evidence": evidence,
        "full_draft": full_draft,
        "instruction": "Try to refute the claim. Default to refuted=true under uncertainty.",
        "challenge_angle": VERIFIER_GOALS[verifier_id],
        "execution_mode": "LIVE_REQUEST_READY",
    }


def verifier_messages(packet: dict) -> list[dict]:
    system = (
        "你是反证 verifier：" + packet["verifier_id"] + "。" + packet["challenge_angle"] +
        " 只核验给定 finding 是否被证据支持。输出 JSON："
        '{"verifier_id":"<id>","votes":[{"finding_id":"<id>","verdict":"not_refuted|refuted|uncertain","evidence":"理由"}]}。'
        "不得新增 finding，不得参考其他 verifier 结论。"
    )
    user = json.dumps({k: v for k, v in packet.items() if k != "execution_mode"}, ensure_ascii=False, sort_keys=True)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_completeness_input(full_draft: str, confirmed: list[dict], rejected: list[dict], sources: dict[str, str]) -> dict:
    packet = {
        "draft": full_draft,
        "confirmed_findings": confirmed,
        "rejected_findings": rejected,
        "source_materials": sources,
        "execution_mode": "LIVE_REQUEST_READY",
    }
    packet["input_sha256"] = digest(json.dumps(packet, ensure_ascii=False, sort_keys=True))
    return packet


def completeness_messages(packet: dict) -> list[dict]:
    system = (
        "你是 Completeness Critic，负责找出前面 Lens 设计遗漏的问题类别。"
        "读完整 draft 与已确认/已驳回 findings，输出 JSON："
        '{"inspected_full_text_sha256":"<draft sha256>","candidate_findings":[{"finding_id":"C1","lens_id":"style|character|plot|canon|story_specific","category":"遗漏类别","issue":"缺口","evidence":"正文位置或引文","recommendation":"补入修订队列的动作","prompt_update":"对应 Lens 今后检查这类遗漏的具体指令"}]}。'
        "每个遗漏同时进入本章修订队列并更新对应 Lens 后续提示。prompt_update 只描述可复用的检查类别，不包含本章结论或其他 Lens 的意见。不得直接改写正文。"
    )
    user = json.dumps({k: v for k, v in packet.items() if k != "input_sha256"}, ensure_ascii=False, sort_keys=True)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("draft", type=Path)
    p.add_argument("--sources", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = review_offline(a.draft.read_text(encoding="utf-8-sig"), json.loads(a.sources.read_text(encoding="utf-8-sig")))
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
