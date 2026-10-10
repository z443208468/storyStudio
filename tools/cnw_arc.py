"""Public Arc completion review: select the planned range, never infer from Sprint size."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

try:
    from .cnw_contract import ContractError, assert_output_within_root
except ImportError:
    from cnw_contract import ContractError, assert_output_within_root


def planned_arc_range(root: Path, arc_ref: str) -> dict:
    """Resolve the author's boundary without requiring unwritten chapter drafts."""
    path = assert_output_within_root(root, arc_ref)
    if path.parent != (root / "04_chapter_design").resolve() or not re.fullmatch(r"arc_\d+", path.stem) or not path.is_file():
        raise ContractError("ARC_REFERENCE_INVALID", arc_ref)
    plan = path.read_text(encoding="utf-8-sig")
    section = re.search(r"^##\s+Range\s*$\n(.*?)(?=^##\s|\Z)", plan, re.M | re.S)
    endpoints = re.findall(r"\b(ep|ch)(\d+)\b", section[1] if section else "", re.I)
    if len(endpoints) != 2 or endpoints[0][0].lower() != endpoints[1][0].lower() or len(endpoints[0][1]) != len(endpoints[1][1]) or int(endpoints[0][1]) > int(endpoints[1][1]):
        return {"status": "ARC_RANGE_UNRESOLVED", "arc_ref": arc_ref}
    prefix, start = endpoints[0]
    end = endpoints[1][1]
    ids = [f"{prefix.lower()}{number:0{len(start)}d}" for number in range(int(start), int(end)+1)]
    return {"status": "ARC_RANGE_RESOLVED", "arc_ref": arc_ref, "arc_id": path.stem, "episodes": ids}


def arc_context(root: Path, arc_ref: str, *, last_episode=None, prior_gate="PASS") -> dict:
    if prior_gate != "PASS":
        return {"status": "ARC_REVIEW_BLOCKED_BY_PRIOR_GATE", "prior_gate": prior_gate}
    context = planned_arc_range(root, arc_ref)
    if context["status"] != "ARC_RANGE_RESOLVED":
        return context
    ids = context["episodes"]
    path = assert_output_within_root(root, arc_ref)
    if last_episode is not None and last_episode not in ids:
        raise ContractError("ARC_EPISODE_OUTSIDE_RANGE", last_episode)
    if last_episode is not None and last_episode != ids[-1]:
        return {"status": "ARC_NOT_AT_END", "arc_ref": arc_ref, "last_episode": last_episode, "planned_end": ids[-1]}
    paths, missing = [], []
    for episode in ids:
        choices = [f"07_draft/episodes/{episode}.md", f"07_draft/{episode}.md"]
        actual = [name for name in choices if assert_output_within_root(root, name).is_file()]
        if len(actual) > 1:
            raise ContractError("ARC_EPISODE_AMBIGUOUS", episode)
        if not actual:
            missing.append(episode)
        else:
            paths.extend(actual)
    if missing:
        return {"status": "ARC_DRAFTS_INCOMPLETE", "arc_ref": arc_ref, "missing_episodes": missing}
    details = path.with_name(path.stem + "_episode_details.md")
    if not details.is_file():
        return {"status": "ARC_DETAILS_MISSING", "arc_ref": arc_ref}
    return {"status": "ARC_READY_FOR_REVIEW", "arc_ref": arc_ref, "arc_id": path.stem,
        "details": details.relative_to(root).as_posix(), "episodes": ids, "draft_paths": paths}


def review_arc(project_root, arc_ref, *, last_episode=None, prior_gate="PASS", handoff=True):
    try:
        from .cnw_maintenance import run_maintenance
    except ImportError:
        from cnw_maintenance import run_maintenance
    root = Path(project_root).resolve(strict=True)
    context = arc_context(root, arc_ref, last_episode=last_episode, prior_gate=prior_gate)
    if context["status"] != "ARC_READY_FOR_REVIEW":
        return {**context, "provider_call": "none", "next_arc_started": False}
    result = run_maintenance(root, "arc_review", target=arc_ref)
    if handoff:
        result["handoff"] = run_maintenance(root, "handoff", pipeline=True)
    return {**result, "next_arc_started": False, "user_creative_accepted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--arc-ref", required=True)
    parser.add_argument("--last-episode")
    parser.add_argument("--prior-gate", default="PASS", choices=("PASS", "REVISION_REQUIRED", "REWRITE_REQUIRED"))
    args = parser.parse_args()
    print(json.dumps(review_arc(args.project_root, args.arc_ref, last_episode=args.last_episode, prior_gate=args.prior_gate), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
