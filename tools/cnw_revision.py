"""Offline length/beat regression gates for a CNW scene revision."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

try:
    from .cnw_contract import ContractError, count_visible_chars, load_contract
    from .cnw_generate import _private_project_root, _project_input, validate_generated_scene
except ImportError:  # direct script execution
    from cnw_contract import ContractError, count_visible_chars, load_contract
    from cnw_generate import _private_project_root, _project_input, validate_generated_scene


def validate_revision(contract: dict, v0: str, v1: str, *, finish_reason: str, v0_beat_evidence: dict[str, str], v1_beat_evidence: dict[str, str], v1_dialogue_evidence: list[str], v1_action_evidence: list[str], start_state_evidence: str, end_state_evidence: str) -> dict:
    before = count_visible_chars(v0)
    after = validate_generated_scene(contract, v1, finish_reason=finish_reason, beat_evidence=v1_beat_evidence, dialogue_evidence=v1_dialogue_evidence, action_evidence=v1_action_evidence, start_state_evidence=start_state_evidence, end_state_evidence=end_state_evidence)
    regression = after["actual_visible_chars"] < contract["unit"]["min_visible_chars"]
    dropped_beats = [beat_id for beat_id, evidence in v0_beat_evidence.items() if evidence and evidence in v0 and not (v1_beat_evidence.get(beat_id) and v1_beat_evidence[beat_id] in v1)]
    if dropped_beats:
        after["failure_codes"].append("REVISION_REGRESSION")
        after["dropped_beat_ids"] = dropped_beats
        regression = True
    if after["actual_visible_chars"] < contract["unit"]["min_visible_chars"]:
        after["failure_codes"].append("REVISION_REGRESSION")
        regression = True
    after["failure_codes"] = list(dict.fromkeys(after["failure_codes"]))
    after["v0_visible_chars"] = before
    after["v1_visible_chars"] = after["actual_visible_chars"]
    after["status"] = "CONTENT_RETURN" if regression or after["failure_codes"] else "CONTENT_VALID"
    # A shorter edit is allowed when it remains in range and preserves required beats.
    return after


def validate_episode_assembly(expected_scene_ids: list[str], scene_results: dict[str, dict]) -> dict:
    missing = [scene_id for scene_id in expected_scene_ids if scene_id not in scene_results or scene_results[scene_id].get("status") != "CONTENT_VALID" or scene_results[scene_id].get("finish_reason") != "stop"]
    return {"status": "CONTENT_VALID" if not missing else "CONTENT_RETURN", "failure_codes": [] if not missing else ["TRUNCATED_OR_UNFINISHED"], "missing_scene_ids": missing}


def plan_persisted_continuation(project_root: str | Path, run_id: str, contract: dict, current_text: str, validation: dict, *, max_attempts: int = 2) -> dict:
    if max_attempts != 2:
        raise ContractError("CONTINUATION_LIMIT_FIXED", "W06 permits at most two attempts")
    root = _private_project_root(project_root)
    if not run_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for ch in run_id) or run_id in {".", ".."}:
        raise ContractError("RUN_ID_INVALID", run_id)
    log = root / "runs" / run_id / "continuation.jsonl"
    if any(part.is_symlink() for part in (log, *log.parents) if part.exists()):
        raise ContractError("CONTINUATION_STATE_UNSAFE", "continuation state contains a symlink")
    log.parent.mkdir(parents=True, exist_ok=True)
    contract_sha = hashlib.sha256(json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    entries = []
    if log.exists():
        try:
            entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError("CONTINUATION_STATE_INVALID", "continuation log is unreadable") from exc
    previous_hash = "0" * 64
    for index, entry in enumerate(entries, 1):
        payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
        digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        if (entry.get("attempt") != index or entry.get("run_id") != run_id or entry.get("contract_sha256") != contract_sha
                or entry.get("previous_sha256") != previous_hash or entry.get("entry_sha256") != digest):
            raise ContractError("CONTINUATION_STATE_INVALID", f"broken chain at attempt {index}")
        previous_hash = digest
    if len(entries) >= max_attempts:
        return {"status": "RETURN_ROOT_CAUSE_REVIEW_REQUIRED", "attempts_used": len(entries), "max_attempts": max_attempts, "provider_call": "none"}
    if validation.get("status") == "CONTENT_VALID":
        return {"status": "CONTINUATION_NOT_REQUIRED", "attempts_used": len(entries), "provider_call": "none"}
    attempt = len(entries) + 1
    payload = {"attempt": attempt, "run_id": run_id, "contract_sha256": contract_sha, "previous_sha256": previous_hash,
               "text_sha256": hashlib.sha256(current_text.encode("utf-8")).hexdigest(),
               "actual_visible_chars": count_visible_chars(current_text),
               "missing_beat_ids": validation.get("missing_beat_ids", []), "failure_codes": validation.get("failure_codes", [])}
    payload["entry_sha256"] = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    with log.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
    if attempt >= max_attempts:
        return {"status": "RETURN_ROOT_CAUSE_REVIEW_REQUIRED", "attempts_used": attempt, "max_attempts": max_attempts, "provider_call": "none"}
    missing = validation.get("missing_beat_ids", [])
    if not missing and "RETURN_UNDERPRODUCED" in validation.get("failure_codes", []):
        missing = [beat["beat_id"] for beat in contract["story"]["required_beats"]]
    result = {"status": "CONTINUE_MISSING_BEATS" if missing else "REVIEW_FAILURE_CODES", "missing_beat_ids": missing,
              "current_visible_chars": count_visible_chars(current_text), "failure_codes": validation.get("failure_codes", []),
              "max_attempts": max_attempts, "provider_call": "not_performed_by_W06_planner"}
    return {**result, "attempts_used": attempt, "state_log": str(log.relative_to(root)), "state_sha256": payload["entry_sha256"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--v0", required=True)
    parser.add_argument("--v1", required=True)
    parser.add_argument("--evidence", help="private JSON evidence map; required to issue PASS/RETURN")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--continuation-run-id", help="persist and enforce the attempt limit under runs/<id>/")
    parser.add_argument("--mode", choices=("offline", "live"), default="offline")
    args = parser.parse_args(argv)
    if args.mode == "live":
        raise ContractError("LIVE_EXECUTOR_NOT_AVAILABLE", "W06 revision validation is offline; live execution remains gated for W10")
    project_root = _private_project_root(args.project_root)
    contract = load_contract(_project_input(project_root, args.contract))
    v0 = _project_input(project_root, args.v0).read_text(encoding="utf-8-sig")
    v1 = _project_input(project_root, args.v1).read_text(encoding="utf-8-sig")
    if not args.evidence:
        raise ContractError("REVISION_EVIDENCE_REQUIRED", "cannot issue revision acceptance from character counts alone")
    evidence = json.loads(_project_input(project_root, args.evidence).read_text(encoding="utf-8"))
    result = validate_revision(contract, v0, v1, finish_reason=evidence["finish_reason"], v0_beat_evidence=evidence["v0_beat_evidence"], v1_beat_evidence=evidence["v1_beat_evidence"], v1_dialogue_evidence=evidence["dialogue_evidence"], v1_action_evidence=evidence["action_evidence"], start_state_evidence=evidence["start_state_evidence"], end_state_evidence=evidence["end_state_evidence"])
    if args.continuation_run_id and result["status"] != "CONTENT_VALID":
        result["continuation"] = plan_persisted_continuation(project_root, args.continuation_run_id, contract, v1, result)
    elif result["status"] != "CONTENT_VALID":
        raise ContractError("CONTINUATION_RUN_ID_REQUIRED", "a failed revision must be recorded in its persistent run state")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "CONTENT_VALID":
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"CNW_REVISION_FAILED:{exc}", file=sys.stderr)
        raise SystemExit(2)
