"""Run one real W10 CritiCS action and bind its receipt to the production run."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
try:
    from .cnw_contract import ContractError
    from .cnw_live_provider import safe_run, verify_run_preflight
    from .cnw_runner import (_contract_for, _support_integration_mode,
        locked_run, load_state, save_state, now)
    from . import p2_cost_guard
except ImportError:
    from cnw_contract import ContractError
    from cnw_live_provider import safe_run, verify_run_preflight
    from cnw_runner import (_contract_for, _support_integration_mode,
        locked_run, load_state, save_state, now)
    import p2_cost_guard
ROOT = Path(__file__).resolve().parents[1]

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _evidence_path(path: Path, project_root: Path) -> str:
    resolved = path.resolve(strict=True)
    for base in (project_root.resolve(strict=True), ROOT.resolve(strict=True)):
        try:
            return resolved.relative_to(base).as_posix()
        except ValueError:
            continue
    raise ContractError("W10_CRITICS_EVIDENCE_PATH_OUTSIDE_SCOPE", str(resolved))


def _critics_run_path(run: Path, action: str) -> tuple[Path, Path]:
    try:
        from .critics_bridge import _registered_project_for_path
    except ImportError:
        from critics_bridge import _registered_project_for_path
    project = _registered_project_for_path(run)
    evidence_root = project or ROOT
    runs_root = project / "runs" if project else ROOT / "runs"
    critic_run_id = f"{run.name}-critics-{action}"
    return evidence_root, runs_root / critic_run_id


def run_action(run_dir: str | Path, action: str, *, preflight_path: str | Path | None = None) -> dict:
    run = safe_run(run_dir)
    if action not in {"plan-critique", "text-refine"}:
        raise ContractError("W10_CRITICS_ACTION_INVALID", action)
    state = load_state(run)
    contract = _contract_for(run)
    project_root, critic_dir = _critics_run_path(run, action)
    if _support_integration_mode(contract, "critics") == "DISABLED":
        return {"status": "DISABLED", "action": action, "provider_call_count": 0,
                "provider_call": "none"}
    verify_run_preflight(run, state, preflight_path=preflight_path)
    stage = "plot" if action == "plan-critique" else "draft"
    record = state.get("stages", {}).get(stage, {})
    if record.get("status") != "ACCEPTED" or not record.get("role_output_path"):
        raise ContractError("W10_CRITICS_STAGE_NOT_ACCEPTED", stage)
    input_path = (run / record["role_output_path"]).resolve(strict=True)
    input_sha = sha(input_path.read_bytes())
    if any(row.get("action") == action for row in state.get("critics_evidence", [])):
        raise ContractError("W10_CRITICS_ACTION_ALREADY_RECORDED", action)
    critic_run_id = critic_dir.name
    if critic_dir.exists() or critic_dir.is_symlink():
        raise ContractError("W10_CRITICS_RUN_COLLISION", critic_run_id)
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise ContractError("DEEPSEEK_API_KEY_REQUIRED", action)
    command = [sys.executable, str(ROOT / "tools/p2_06_critics_run.py"), "--action", action,
               "--input", str(input_path), "--run-dir", str(critic_dir), "--ledger-run-id", run.name]
    completed = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise ContractError("W10_CRITICS_ACTION_FAILED", f"{action}; exit={completed.returncode}")
    results = [line for line in completed.stdout.splitlines() if line.strip().startswith("{")]
    if not results:
        raise ContractError("W10_CRITICS_RESULT_MISSING", action)
    result = json.loads(results[-1])
    critic_root = critic_dir
    receipt_path = critic_root / "run_receipt.json"
    calls_path = critic_root / "provider-calls.json"
    output_path = Path(result.get("output", "")).resolve(strict=True)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    calls = json.loads(calls_path.read_text(encoding="utf-8"))
    if (receipt.get("action") != action or receipt.get("status") != "SUCCEEDED"
            or receipt.get("model") != "deepseek-flash" or receipt.get("input_sha256") != input_sha
            or receipt.get("output_sha256") != sha(output_path.read_bytes()) or not calls):
        raise ContractError("W10_CRITICS_RECEIPT_INVALID", action)
    request_ids = [call.get("local_request_id") for call in calls]
    provider_ids = [call.get("response", {}).get("id") for call in calls]
    if (any(not isinstance(value, str) or not value for value in request_ids + provider_ids)
            or len(set(request_ids)) != len(request_ids) or len(set(provider_ids)) != len(provider_ids)):
        raise ContractError("W10_CRITICS_PROVIDER_IDS_INVALID", action)
    ledger = json.loads(p2_cost_guard.LEDGER.read_text(encoding="utf-8"))
    rows = [row for row in ledger.get("requests", []) if row.get("request_id") in request_ids]
    if len(rows) != len(request_ids) or any(row.get("run_id") != run.name or row.get("status") != "SETTLED" for row in rows):
        raise ContractError("W10_CRITICS_COST_SETTLEMENT_INVALID", action)
    rows_by_id = {row["request_id"]: row for row in rows}
    for call in calls:
        response = call.get("response", {})
        usage = response.get("usage", {})
        row = rows_by_id.get(call.get("local_request_id"), {})
        if (row.get("provider_request_id") != response.get("id")
                or row.get("returned_model") != response.get("model")
                or row.get("finish_reason") != (response.get("choices") or [{}])[0].get("finish_reason")
                or row.get("usage") != {"input_tokens": usage.get("prompt_tokens"),
                                         "output_tokens": usage.get("completion_tokens")}):
            raise ContractError("W10_CRITICS_USAGE_LEDGER_MISMATCH", action)
        try:
            estimated = Decimal(str(row.get("estimated_actual_cny", "NaN")))
            reported_cost = Decimal(str(call.get("estimated_cost_cny", "NaN")))
        except InvalidOperation as exc:
            raise ContractError("W10_CRITICS_COST_LEDGER_MISMATCH", action) from exc
        if not estimated.is_finite() or not reported_cost.is_finite() or estimated != reported_cost:
            raise ContractError("W10_CRITICS_COST_LEDGER_MISMATCH", action)
    evidence = {"action": action, "path_root": "project_root",
        "run_dir": _evidence_path(critic_root, project_root),
        "receipt_path": _evidence_path(receipt_path, project_root),
        "receipt_sha256": sha(receipt_path.read_bytes()), "calls_path": _evidence_path(calls_path, project_root),
        "calls_sha256": sha(calls_path.read_bytes()), "input_path": _evidence_path(input_path, project_root),
        "input_sha256": input_sha, "output_path": _evidence_path(output_path, project_root),
        "output_sha256": sha(output_path.read_bytes()), "request_ids": request_ids,
        "provider_request_ids": provider_ids, "status": "SUCCEEDED"}
    with locked_run(run):
        current = load_state(run)
        if current.get("stages", {}).get(stage, {}).get("role_output_sha256") != input_sha:
            raise ContractError("W10_CRITICS_INPUT_CHANGED", action)
        current.setdefault("critics_evidence", []).append(evidence)
        current["updated_at"] = now()
        save_state(run, current)
    return {"status": "W10_CRITICS_BOUND", "action": action, "provider_call_count": len(calls),
            "provider_request_ids": provider_ids, "input_sha256": input_sha,
            "output_sha256": evidence["output_sha256"]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--action", required=True, choices=("plan-critique", "text-refine"))
    parser.add_argument("--preflight")
    args = parser.parse_args()
    print(json.dumps(run_action(args.run_dir, args.action, preflight_path=args.preflight),
        ensure_ascii=False, indent=2))
if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"W10_CRITICS_FAILED:{exc}", file=sys.stderr)
        raise SystemExit(2)
