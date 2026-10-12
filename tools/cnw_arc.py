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


def arc_context(root: Path, arc_ref: str, *, last_episode=None, prior_gate="PASS", candidate_drafts=None) -> dict:
    if prior_gate != "PASS":
        return {"status": "ARC_REVIEW_BLOCKED_BY_PRIOR_GATE", "prior_gate": prior_gate}
    context = planned_arc_range(root, arc_ref)
    if context["status"] != "ARC_RANGE_RESOLVED":
        return context
    ids = context["episodes"]
    candidates = candidate_drafts or {}
    if not isinstance(candidates, dict) or set(candidates) - set(ids):
        raise ContractError("ARC_CANDIDATE_IDENTITY_INVALID", "candidate episodes must belong to the selected Arc")
    path = assert_output_within_root(root, arc_ref)
    if last_episode is not None and last_episode not in ids:
        raise ContractError("ARC_EPISODE_OUTSIDE_RANGE", last_episode)
    if last_episode is not None and last_episode != ids[-1]:
        return {"status": "ARC_NOT_AT_END", "arc_ref": arc_ref, "last_episode": last_episode, "planned_end": ids[-1]}
    paths, missing = [], []
    for episode in ids:
        if episode in candidates:
            row = candidates[episode]
            if not isinstance(row, dict) or not isinstance(row.get("path"), str) or not isinstance(row.get("sha256"), str):
                raise ContractError("ARC_CANDIDATE_IDENTITY_INVALID", episode)
            candidate = assert_output_within_root(root, row["path"])
            parts = candidate.relative_to(root).parts
            if (len(parts) != 4 or parts[0] != "sprints" or parts[2] != "candidates"
                    or parts[3] != f"{episode}.md"):
                raise ContractError("ARC_CANDIDATE_IDENTITY_INVALID", "select a named Sprint manuscript candidate")
            import hashlib
            if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest() != row["sha256"]:
                raise ContractError("ARC_CANDIDATE_HASH_MISMATCH", episode)
            paths.append(candidate.relative_to(root).as_posix())
            continue
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


def review_arc(project_root, arc_ref, *, last_episode=None, prior_gate="PASS", handoff=True, candidate_drafts=None):
    try:
        from .cnw_maintenance import run_maintenance
    except ImportError:
        from cnw_maintenance import run_maintenance
    root = Path(project_root).resolve(strict=True)
    context = arc_context(root, arc_ref, last_episode=last_episode, prior_gate=prior_gate,
                          candidate_drafts=candidate_drafts)
    if context["status"] != "ARC_READY_FOR_REVIEW":
        return {**context, "provider_call": "none", "next_arc_started": False}
    result = run_maintenance(root, "arc_review", target=arc_ref, candidate_drafts=candidate_drafts)
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
