"""Explicitly offline five-episode sprint fixture; never calls a provider."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

try:
    from .cnw_contract import ContractError, load_contract, validate_episode_budget, validate_scene_budget
except ImportError:
    from cnw_contract import ContractError, load_contract, validate_episode_budget, validate_scene_budget

ROOT = Path(__file__).resolve().parents[1]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_fixture_sprint(project_root: str | Path, sprint_id: str, plan_path: str | Path) -> dict:
    root = Path(project_root).resolve(strict=True)
    private = (ROOT / "workspace").resolve()
    if not root.is_relative_to(private):
        raise ContractError("SPRINT_ROOT_OUTSIDE_PRIVATE_WORKSPACE", str(root))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,63}", sprint_id):
        raise ContractError("SPRINT_ID_INVALID", sprint_id)
    supplied = Path(plan_path).absolute()
    if any(part.is_symlink() for part in (supplied, *supplied.parents) if part.exists()):
        raise ContractError("SPRINT_PLAN_UNSAFE", "plan path contains symlink")
    plan = supplied.resolve(strict=True)
    if not plan.is_relative_to(root) or not plan.is_file():
        raise ContractError("SPRINT_PLAN_OUTSIDE_PROJECT", str(plan))
    try:
        payload = json.loads(plan.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("SPRINT_PLAN_INVALID", str(exc)) from exc
    episodes = payload.get("episodes")
    if not isinstance(episodes, list) or len(episodes) != 5:
        raise ContractError("SPRINT_REQUIRES_FIVE_EPISODES", "fixture plan must contain five episode rows")
    ids: set[str] = set()
    rows = []
    for index, row in enumerate(episodes, 1):
        if not isinstance(row, dict):
            raise ContractError("SPRINT_EPISODE_INVALID", str(index))
        episode_id = row.get("episode_id")
        if not isinstance(episode_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,95}", episode_id) or episode_id in ids:
            raise ContractError("SPRINT_EPISODE_ID_INVALID", str(index))
        ids.add(episode_id)
        contract_path = (root / str(row.get("contract", ""))).resolve(strict=True)
        if not contract_path.is_relative_to(root):
            raise ContractError("SPRINT_CONTRACT_OUTSIDE_PROJECT", episode_id)
        contract = load_contract(contract_path)
        if contract.get("project_id", "").startswith("FICT_") is False:
            raise ContractError("SPRINT_FIXTURE_PROJECT_REQUIRED", episode_id)
        if contract.get("unit", {}).get("kind") == "episode":
            validate_episode_budget(contract["unit"])
        elif contract.get("unit", {}).get("kind") == "scene":
            validate_scene_budget(contract)
        else:
            raise ContractError("SPRINT_UNIT_KIND_INVALID", episode_id)
        if contract.get("unit", {}).get("id") != episode_id:
            raise ContractError("SPRINT_CONTRACT_ID_MISMATCH", episode_id)
        plot_text = row.get("plot_fixture")
        review_status = row.get("review_fixture")
        if not isinstance(plot_text, str) or not plot_text.strip() or review_status not in {"ACCEPTED", "RETURN"}:
            raise ContractError("SPRINT_FIXTURE_STAGE_INVALID", episode_id)
        rows.append({"episode_id": episode_id, "contract": contract_path.relative_to(root).as_posix(),
                     "contract_sha256": digest(contract_path.read_bytes()), "plot": plot_text.strip(),
                     "plot_status": "FIXTURE_READY", "review_status": review_status,
                     "review_notes": row.get("review_notes", ""), "provider_call": "none"})
    out = root / "sprints" / sprint_id
    if out.exists() or out.is_symlink():
        raise ContractError("SPRINT_ID_COLLISION", sprint_id)
    out.mkdir(parents=True)
    (out / "plot.json").write_text(json.dumps({"mode": "TEST_FIXTURE_ONLY", "episodes": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    accepted = [row["episode_id"] for row in rows if row["review_status"] == "ACCEPTED"]
    returned = [row["episode_id"] for row in rows if row["review_status"] == "RETURN"]
    summary = {"mode": "TEST_FIXTURE_ONLY", "sprint_id": sprint_id, "episode_count": len(rows),
               "accepted": accepted, "returned": returned, "provider_call": "none"}
    (out / "batch_review.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    handoff = {"mode": "TEST_FIXTURE_ONLY", "next_sprint_id": sprint_id + "-NEXT",
               "carry_forward": [{"episode_id": row["episode_id"], "status": row["review_status"], "notes": row["review_notes"]} for row in rows if row["review_status"] == "RETURN"],
               "provider_call": "none"}
    (out / "next_sprint_handoff.json").write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "SPRINT_FIXTURE_COMPLETE", "sprint_id": sprint_id, "episode_count": len(rows),
            "output_dir": out.relative_to(root).as_posix(), "mode": "TEST_FIXTURE_ONLY", "provider_call": "none"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--sprint-id", required=True)
    parser.add_argument("--plan", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run_fixture_sprint(args.project_root, args.sprint_id, args.plan), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, ValueError) as exc:
        print(f"CNW_SPRINT_FAILED:{exc}", file=sys.stderr)
        raise SystemExit(2)
