"""Single-attempt DeepSeek transport with per-call budget and raw receipts.

No orchestration or automatic retries occur here. Callers must freeze the stage
input first and persist the returned receipt before advancing the run.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import httpx
import io
import json
import os
from pathlib import Path
import re
import uuid
from decimal import Decimal, InvalidOperation

try:
    from . import p2_cost_guard
    from .cnw_contract import ContractError
except ImportError:
    import p2_cost_guard
    from cnw_contract import ContractError

ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-flash"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sanitize_provider_payload(value):
    if isinstance(value, dict):
        return {key: sanitize_provider_payload(child) for key, child in value.items()
                if key not in {"reasoning_content", "api_key", "authorization"}}
    if isinstance(value, list):
        return [sanitize_provider_payload(child) for child in value]
    return value


def safe_run(run_dir: str | Path) -> Path:
    supplied = Path(run_dir).absolute()
    if any(part.is_symlink() for part in (supplied, *supplied.parents) if part.exists()):
        raise ContractError("LIVE_RUN_PATH_UNSAFE", "run path contains symlink")
    run = supplied.resolve(strict=True)
    private_runs = (ROOT / "runs").resolve()
    workspace = (ROOT / "workspace").resolve()
    allowed = run.is_relative_to(private_runs) or (
        run.parent.name == "runs" and run.parent.parent.is_relative_to(workspace))
    if not allowed and run.parent.name == "runs":
        # Generic registered projects live at DataHome/projects/<instance>/runs/<run>.
        # Resolve that exact instance against its parent DataHome registry; never
        # admit an arbitrary sibling path merely because it is outside workspace.
        project_root = run.parent.parent
        data_home = project_root.parent.parent
        try:
            try:
                from .project_paths import resolve_project
            except ImportError:
                from project_paths import resolve_project
            registration = resolve_project(project_root, data_home=data_home)
            allowed = registration.get("project_root") == str(project_root.resolve(strict=True))
        except Exception:
            allowed = False
    if not allowed or not run.is_dir():
        raise ContractError("LIVE_RUN_PATH_UNSAFE", "live artifacts must be under runs/")
    return run


def verify_run_preflight(run: Path, state: dict | None = None, *, preflight_path: str | Path | None = None) -> dict:
    """Validate legacy J19 authorization or an explicit project-bound preflight."""
    if state is None:
        try:
            state = json.loads((run / "run_state.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ContractError("LIVE_RUN_STATE_INVALID", run.name) from exc
    authorization = state.get("w10_contract_preflight", {})
    try:
        from .cnw_w10_policy import CONTRACT_SHA256, PREFLIGHT_EVIDENCE_SHA256, PREFLIGHT_REF, SOURCE_SCRIPT_SHA256
    except ImportError:
        from cnw_w10_policy import CONTRACT_SHA256, PREFLIGHT_EVIDENCE_SHA256, PREFLIGHT_REF, SOURCE_SCRIPT_SHA256
    legacy_authorized = (
        state.get("run_id") == run.name and state.get("mode") == "live"
        and state.get("fixture_only") is False
        and authorization.get("status") == "ACCEPTED"
        and authorization.get("scope") == "W10_SINGLE_SCENE"
        and authorization.get("contract_sha256") == CONTRACT_SHA256
        and state.get("contract_sha256") == CONTRACT_SHA256
        and authorization.get("source_script_sha256") == SOURCE_SCRIPT_SHA256
        and authorization.get("evidence_sha256") == PREFLIGHT_EVIDENCE_SHA256
        and authorization.get("controller_acceptance_ref") == PREFLIGHT_REF
        and authorization.get("provider_call_authorized") is True)
    if legacy_authorized:
        return state
    preflight_path = preflight_path or os.environ.get("STORYSTUDIO_W10_PREFLIGHT_PATH")
    if preflight_path:
        try:
            from .cnw_w10_policy import verify_preflight_file
        except ImportError:
            from cnw_w10_policy import verify_preflight_file
        contract_path = run / "artifacts/contract.json"
        project_root = run.parent.parent
        preflight, _evidence_sha = verify_preflight_file(
            preflight_path, contract_path, run_dir=run, project_root=project_root)
        if (state.get("run_id") != run.name or state.get("mode") != "live"
                or state.get("fixture_only") is not False
                or preflight.get("provider_call_authorized") is not False):
            raise ContractError("LIVE_STAGE_NOT_AUTHORIZED_OR_READY", "per-run review is not a production grant")
        raise ContractError("LIVE_AUTHORIZATION_REQUIRED", "independent review was verified; separate real user Live and fee grants are still required")
    raise ContractError("LIVE_STAGE_NOT_AUTHORIZED_OR_READY", "W10 run preflight")


def _load_live_state(run: Path, stage: str) -> dict:
    state = verify_run_preflight(run)
    stage_state = state.get("stages", {}).get(stage, {})
    if stage_state.get("status") != "READY_FOR_EXECUTION":
        raise ContractError("LIVE_STAGE_NOT_AUTHORIZED_OR_READY", stage)
    return state


def _reserve(request_id: str, run_id: str, stage: str, input_cap: int, output_cap: int) -> dict:
    args = argparse.Namespace(request_id=request_id, run_id=run_id,
                              purpose=f"P3 W10 CNW stage {stage}",
                              input_token_cap=input_cap, output_token_cap=output_cap)
    capture = io.StringIO()
    with redirect_stdout(capture):
        p2_cost_guard.command_reserve(args)
    result = json.loads(capture.getvalue())
    if result.get("status") != "RESERVED":
        raise ContractError("LIVE_COST_RESERVATION_FAILED", stage)
    return result


def _settle(request_id: str, payload: dict | None) -> dict:
    choices = (payload or {}).get("choices") or []
    usage = (payload or {}).get("usage") or {}
    choice = choices[0] if choices and isinstance(choices[0], dict) else {}
    args = argparse.Namespace(request_id=request_id,
        provider_request_id=(payload or {}).get("id"), returned_model=(payload or {}).get("model"),
        finish_reason=choice.get("finish_reason"), input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"))
    capture = io.StringIO()
    with redirect_stdout(capture):
        p2_cost_guard.command_settle(args)
    result = json.loads(capture.getvalue())
    if result.get("status") not in {"SETTLED", "UNKNOWN_NOT_ZERO", "SETTLED_OVER_BUDGET"}:
        raise ContractError("LIVE_COST_SETTLEMENT_FAILED", request_id)
    return result


def _record_failed_attempt(run: Path, attempt: dict) -> None:
    try:
        from .cnw_runner import locked_run, load_state, save_state
    except ImportError:
        from cnw_runner import locked_run, load_state, save_state
    with locked_run(run):
        state = load_state(run)
        _load_live_state(run, attempt["stage"])
        state.setdefault("provider_attempts", []).append(attempt)
        state["updated_at"] = utc_now()
        save_state(run, state)


def complete(run_dir: str | Path, *, stage: str, messages: list[dict], input_sha256: str,
             input_token_cap: int, output_token_cap: int, role_id: str | None = None,
             transport=None) -> tuple[str, dict]:
    """Make exactly one live request; transport injection exists only for tests."""
    run = safe_run(run_dir)
    state_path = run / "run_state.json"
    if state_path.is_symlink() or not state_path.is_file():
        raise ContractError("LIVE_RUN_STATE_MISSING", run.name)
    if stage == "pov":
        raise ContractError("NK_ADAPTER_REQUIRED", "POV must execute through the pinned local NK service")
    if stage not in {"plot", "cards", "brief", "draft", "lens5", "verifier3", "completeness", "refine", "re-review"}:
        raise ContractError("LIVE_STAGE_INVALID", stage)
    role_field = "lens_id" if stage in {"lens5", "re-review"} else "verifier_id" if stage == "verifier3" else None
    if role_field and (not role_id or not re.fullmatch(r"[a-z0-9_]{2,32}", role_id)):
        raise ContractError("LIVE_ROLE_ID_REQUIRED", stage)
    canonical_input = json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") if isinstance(messages, list) else b""
    if (not re.fullmatch(r"[0-9a-f]{64}", input_sha256)
            or sha(canonical_input) != input_sha256
            or not isinstance(messages, list) or not messages
            or not isinstance(input_token_cap, int) or input_token_cap <= 0
            or not isinstance(output_token_cap, int) or output_token_cap <= 0):
        raise ContractError("LIVE_REQUEST_INVALID", stage)
    state = _load_live_state(run, stage)
    failed_attempts = [row for row in state.get("provider_attempts", [])
                       if row.get("stage") == stage and row.get("status") != "INVALIDATED_AFTER_INPUT_CHANGE"]
    if failed_attempts:
        raise ContractError("LIVE_STAGE_RETRY_REQUIRES_CONTROLLER_REVIEW", stage)
    active_receipts = [row for row in state.get("provider_requests", [])
                       if row.get("stage") == stage and row.get("stage_fingerprint") == state["stages"][stage].get("fingerprint")
                       and (row.get("lens_id") or row.get("verifier_id")) == role_id]
    if active_receipts:
        raise ContractError("LIVE_STAGE_ALREADY_HAS_PROVIDER_RESPONSE", stage)
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key or len(key.strip()) < 20:
        raise ContractError("DEEPSEEK_API_KEY_REQUIRED", stage)
    request_id = f"p3-{run.name}-{stage}-{uuid.uuid4().hex}"
    reservation = _reserve(request_id, run.name, stage, input_token_cap, output_token_cap)
    body = {"model": MODEL, "messages": messages, "max_tokens": output_token_cap,
            "stream": False, "thinking": {"type": "disabled"}}
    safe_request = {**body, "request_id": request_id, "input_sha256": input_sha256,
                    "stage": stage, "role_id": role_id, "created_at": utc_now()}
    evidence = run / "artifacts" / "live" / request_id
    evidence.mkdir(parents=True, exist_ok=False)
    request_bytes = (json.dumps(safe_request, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    (evidence / "request.json").write_bytes(request_bytes)
    raw_path = evidence / "response.json"
    response_payload = None
    status_code = None
    try:
        if transport is None:
            response = httpx.post(API_URL, headers={"Authorization": f"Bearer {key}",
                "Content-Type": "application/json", "X-Client-Request-Id": request_id},
                json=body, timeout=httpx.Timeout(180.0, connect=20.0), follow_redirects=False)
        else:
            response = transport(API_URL, body, request_id, key)
        status_code = int(response.status_code)
        try:
            response_payload = response.json()
        except (ValueError, json.JSONDecodeError):
            response_payload = None
        raw_bytes = ((json.dumps(sanitize_provider_payload(response_payload), ensure_ascii=False,
                                separators=(",", ":")) + "\n").encode("utf-8")
                     if response_payload is not None else response.content)
        raw_path.write_bytes(raw_bytes)
    except Exception as exc:
        raw_path.write_text(json.dumps({"transport_error_type": type(exc).__name__,
            "request_id": request_id}, indent=2) + "\n", encoding="utf-8")
        settlement = _settle(request_id, None)
        _record_failed_attempt(run, {"stage": stage, "request_id": request_id,
            "status": "OUTCOME_UNKNOWN", "input_sha256": input_sha256,
            "raw_response_path": raw_path.relative_to(run).as_posix(),
            "raw_response_sha256": sha(raw_path.read_bytes()), "ledger_settlement": settlement,
            "transport_error_type": type(exc).__name__, "created_at": utc_now()})
        raise ContractError("LIVE_PROVIDER_OUTCOME_UNKNOWN", f"{stage}: {type(exc).__name__}; reservation={settlement.get('status')}") from exc
    usage = response_payload.get("usage") if isinstance(response_payload, dict) else None
    provider_id = response_payload.get("id") if isinstance(response_payload, dict) else None
    returned_model = response_payload.get("model") if isinstance(response_payload, dict) else None
    choices = response_payload.get("choices") if isinstance(response_payload, dict) else None
    choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    finish = choice.get("finish_reason")
    settlement = _settle(request_id, response_payload)
    if settlement.get("status") == "SETTLED_OVER_BUDGET":
        _record_failed_attempt(run, {"stage": stage, "request_id": request_id,
            "provider_request_id": provider_id, "status": "SETTLED_OVER_BUDGET",
            "input_sha256": input_sha256,
            "raw_response_path": raw_path.relative_to(run).as_posix(),
            "raw_response_sha256": sha(raw_path.read_bytes()), "ledger_settlement": settlement,
            "created_at": utc_now()})
        raise ContractError("LIVE_PROVIDER_BUDGET_EXCEEDED", f"{stage}: actual usage exceeded its reservation or campaign caps")
    if status_code != 200 or not isinstance(response_payload, dict):
        _record_failed_attempt(run, {"stage": stage, "request_id": request_id,
            "provider_request_id": provider_id, "status": "PROVIDER_REJECTED",
            "http_status": status_code, "input_sha256": input_sha256,
            "raw_response_path": raw_path.relative_to(run).as_posix(),
            "raw_response_sha256": sha(raw_path.read_bytes()), "ledger_settlement": settlement,
            "created_at": utc_now()})
        raise ContractError("LIVE_PROVIDER_RESPONSE_INVALID", f"{stage}: HTTP {status_code}; settled={settlement.get('status')}")
    content = choice.get("message", {}).get("content") if isinstance(choice.get("message"), dict) else None
    if (returned_model != MODEL or not isinstance(provider_id, str) or not provider_id
            or finish != "stop" or not isinstance(content, str) or not content.strip()
            or not isinstance(usage, dict)
            or not all(isinstance(usage.get(k), int) and usage[k] > 0 for k in ("prompt_tokens", "completion_tokens"))):
        _record_failed_attempt(run, {"stage": stage, "request_id": request_id,
            "provider_request_id": provider_id, "status": "INVALID_PROVIDER_RESPONSE",
            "http_status": status_code, "input_sha256": input_sha256,
            "raw_response_path": raw_path.relative_to(run).as_posix(),
            "raw_response_sha256": sha(raw_path.read_bytes()), "ledger_settlement": settlement,
            "created_at": utc_now()})
        raise ContractError("LIVE_PROVIDER_RESPONSE_INVALID", f"{stage}: model, finish, content or usage invalid")
    _, pricing = p2_cost_guard.load_config()
    from decimal import Decimal, ROUND_CEILING
    actual_cost = p2_cost_guard.estimate(usage["prompt_tokens"], usage["completion_tokens"], pricing)
    simulated = transport is not None
    receipt = {"stage": stage, "request_id": request_id, "provider_request_id": provider_id,
        "model": returned_model, "status": "SUCCEEDED", "http_status": status_code,
        "finish_reason": finish, "usage": {"prompt_tokens": usage["prompt_tokens"], "completion_tokens": usage["completion_tokens"]},
        "input_sha256": input_sha256, "output_sha256": sha(content.encode("utf-8")),
        "stage_fingerprint": state["stages"][stage].get("fingerprint"),
        "raw_response_path": raw_path.relative_to(run).as_posix(), "raw_response_sha256": sha(raw_path.read_bytes()),
        "cost_cny": float(actual_cost.quantize(Decimal("0.000001"), rounding=ROUND_CEILING)),
        "ledger_settlement": settlement, "mode": "MOCK_ONLY" if simulated else "LIVE",
        "fixture_only": simulated}
    if role_field:
        receipt[role_field] = role_id
    receipt_path = evidence / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        from .cnw_runner import locked_run, load_state, save_state
    except ImportError:
        from cnw_runner import locked_run, load_state, save_state
    with locked_run(run):
        state = load_state(run)
        _load_live_state(run, stage)
        if any(row.get("request_id") == request_id or row.get("provider_request_id") == provider_id
               for row in state.get("provider_requests", [])):
            raise ContractError("LIVE_PROVIDER_REQUEST_ID_DUPLICATE", provider_id)
        state.setdefault("provider_requests", []).append(receipt)
        state["updated_at"] = utc_now()
        save_state(run, state)
    return content, receipt


def accept_validated_stage(run_dir: str | Path, *, stage: str, content: str,
                           validation: dict, role_id: str | None = None) -> dict:
    """Persist one validated output and close its stage only when call coverage is complete."""
    run = safe_run(run_dir)
    if not isinstance(validation, dict) or validation.get("status") not in {
        "CONTENT_VALID", "ROLE_OUTPUT_VALID", "LINT_CLEAN", "REVIEW_COMPLETED"
    }:
        raise ContractError("LIVE_STAGE_VALIDATION_REQUIRED", stage)
    if not isinstance(content, str) or not content.strip():
        raise ContractError("LIVE_STAGE_OUTPUT_EMPTY", stage)
    role_field = "lens_id" if stage in {"lens5", "re-review"} else "verifier_id" if stage == "verifier3" else None
    if role_field and not role_id:
        raise ContractError("LIVE_ROLE_ID_REQUIRED", stage)
    if role_field is None and role_id is not None:
        raise ContractError("LIVE_ROLE_ID_UNEXPECTED", stage)
    try:
        from .cnw_runner import locked_run, load_state, save_state, stage_predecessors
    except ImportError:
        from cnw_runner import locked_run, load_state, save_state, stage_predecessors
    with locked_run(run):
        state = load_state(run)
        _load_live_state(run, stage)
        stage_record = state.get("stages", {}).get(stage, {})
        if stage_record.get("status") != "READY_FOR_EXECUTION":
            raise ContractError("LIVE_STAGE_NOT_READY", stage)
        if any(state["stages"][dependency]["status"] != "ACCEPTED"
               for dependency in stage_predecessors(stage, state["unit_kind"])):
            raise ContractError("STAGE_DEPENDENCY_NOT_ACCEPTED", stage)
        matching = [row for row in state.get("provider_requests", []) if row.get("stage") == stage]
        if stage not in {"lint1", "lint2"} and any(
                row.get("mode") != "LIVE" or row.get("fixture_only") is not False for row in matching):
            raise ContractError("LIVE_MOCK_PROVIDER_ACCEPTANCE_FORBIDDEN", stage)
        content_sha = sha(content.encode("utf-8"))
        local_stage = stage in {"lint1", "lint2"}
        if local_stage:
            if matching:
                raise ContractError("LIVE_LOCAL_STAGE_HAS_PROVIDER_CALL", stage)
            if validation.get("status") not in {"LINT_CLEAN", "LINT_COMPLETE"}:
                raise ContractError("LIVE_STAGE_VALIDATION_REQUIRED", stage)
            rel = f"artifacts/stages/{stage}.json"
        elif stage in {"lens5", "verifier3", "re-review"}:
            matching_role = [row for row in matching if row.get(role_field) == role_id]
            if not matching_role:
                raise ContractError("LIVE_STAGE_PROVIDER_RECEIPT_REQUIRED", f"{stage}:{role_id}")
            if len(matching_role) != 1 or matching_role[0].get("output_sha256") != content_sha:
                raise ContractError("LIVE_STAGE_OUTPUT_RECEIPT_MISMATCH", f"{stage}:{role_id}")
            rel = f"artifacts/stages/{stage}-{role_id}.json"
        else:
            if len(matching) != 1:
                raise ContractError("LIVE_STAGE_PROVIDER_RECEIPT_REQUIRED", stage)
            if matching[0].get("output_sha256") != content_sha:
                raise ContractError("LIVE_STAGE_OUTPUT_RECEIPT_MISMATCH", stage)
            rel = f"artifacts/stages/{stage}.json"
        target = run / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            raise ContractError("LIVE_STAGE_ARTIFACT_COLLISION", rel)
        artifact = {"schema_version": "cnw_live_stage_artifact_v1", "run_id": run.name,
            "stage": stage, "role_id": role_id, "content": content, "validation": validation,
            "provider_request_ids": [row["provider_request_id"] for row in matching]}
        raw = (json.dumps(artifact, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        target.write_bytes(raw)
        stage_record.setdefault("role_artifacts", {})[role_id or "default"] = {
            "path": rel, "sha256": sha(raw), "validation": validation}
        expected = {
            "lens5": {"style", "character", "plot", "canon", "story_specific"},
            "verifier3": {"verifier_1", "verifier_2", "verifier_3"},
            "re-review": set(stage_record.get("expected_role_ids", [])),
        }.get(stage)
        completed = set(stage_record["role_artifacts"])
        if expected is None:
            stage_record["status"] = "ACCEPTED"
            stage_record["artifact"] = {"path": rel, "sha256": sha(raw)}
        elif expected and expected.issubset(completed):
            stage_record["status"] = "ACCEPTED"
            aggregate = {"schema_version": "cnw_live_stage_set_v1", "stage": stage,
                "role_artifacts": stage_record["role_artifacts"], "expected_role_ids": sorted(expected)}
            aggregate_path = run / f"artifacts/stages/{stage}-index.json"
            aggregate_raw = (json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            aggregate_path.write_bytes(aggregate_raw)
            stage_record["artifact"] = {"path": aggregate_path.relative_to(run).as_posix(),
                                        "sha256": sha(aggregate_raw)}
        state["stages"][stage] = stage_record
        state["updated_at"] = utc_now()
        save_state(run, state)
    return {"status": stage_record["status"], "stage": stage, "artifact": stage_record.get("artifact"),
                "role_artifacts": len(stage_record["role_artifacts"])}


def record_nk_pov_receipt(run_dir: str | Path, receipt: dict) -> dict:
    """Bind a separately captured local-NK call to this W10 run and shared ledger."""
    run = safe_run(run_dir)
    required = {"stage", "request_id", "provider_request_id", "model", "status", "http_status",
                "finish_reason", "usage", "input_sha256", "output_sha256", "raw_response_path",
                "input_payload_path", "raw_response_sha256", "cost_cny", "ledger_settlement", "mode", "fixture_only"}
    if not isinstance(receipt, dict) or not required.issubset(receipt) or receipt.get("stage") != "pov":
        raise ContractError("NK_PROVIDER_RECEIPT_INVALID", "required live POV receipt fields are missing")
    if receipt.get("mode") != "LIVE" or receipt.get("fixture_only") is not False:
        raise ContractError("NK_PROVIDER_RECEIPT_INVALID", "fixture/mock POV cannot prove W10")
    rel = Path(str(receipt.get("raw_response_path", "")))
    if rel.is_absolute() or ".." in rel.parts or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("raw_response_sha256", "")).lower()):
        raise ContractError("NK_RAW_RESPONSE_PATH_UNSAFE", str(receipt.get("raw_response_path")))
    raw = run / rel
    if (any(part.is_symlink() for part in (raw, *raw.parents) if part.exists())
            or not raw.resolve(strict=True).is_relative_to(run)
            or not raw.is_file()
            or sha(raw.read_bytes()) != str(receipt["raw_response_sha256"]).lower()):
        raise ContractError("NK_RAW_RESPONSE_HASH_MISMATCH", receipt["request_id"])
    input_rel = Path(str(receipt.get("input_payload_path", "")))
    if input_rel.is_absolute() or ".." in input_rel.parts:
        raise ContractError("NK_INPUT_PATH_UNSAFE", str(receipt.get("input_payload_path")))
    input_path = run / input_rel
    input_sha = str(receipt.get("input_sha256", "")).lower()
    if (any(part.is_symlink() for part in (input_path, *input_path.parents) if part.exists())
            or not input_path.resolve(strict=True).is_relative_to(run)
            or not input_path.is_file() or not re.fullmatch(r"[0-9a-f]{64}", input_sha)
            or sha(input_path.read_bytes()) != input_sha):
        raise ContractError("NK_INPUT_HASH_MISMATCH", receipt["request_id"])
    try:
        from .cnw_runner import locked_run, load_state, save_state, _validate_raw_live_response
    except ImportError:
        from cnw_runner import locked_run, load_state, save_state, _validate_raw_live_response
    with locked_run(run):
        state = load_state(run)
        _load_live_state(run, "pov")
        usage = receipt.get("usage")
        if (not isinstance(usage, dict)
                or not all(isinstance(usage.get(key), int) and not isinstance(usage.get(key), bool) and usage[key] > 0
                           for key in ("prompt_tokens", "completion_tokens"))
                or not isinstance(receipt.get("request_id"), str) or not receipt["request_id"]
                or not isinstance(receipt.get("provider_request_id"), str) or not receipt["provider_request_id"]
                or receipt.get("model") != MODEL or receipt.get("http_status") != 200
                or receipt.get("finish_reason") != "stop"
                or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("output_sha256", "")).lower())):
            raise ContractError("NK_PROVIDER_RECEIPT_INVALID", "identity, status, usage or hashes are invalid")
        _validate_raw_live_response(raw, receipt, usage, 1)
        ledger_path = p2_cost_guard.LEDGER
        if ledger_path.is_symlink() or not ledger_path.is_file():
            raise ContractError("LIVE_COST_LEDGER_MISSING", str(ledger_path))
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        rows = [row for row in ledger.get("requests", []) if row.get("request_id") == receipt["request_id"]]
        if len(rows) != 1:
            raise ContractError("LIVE_COST_LEDGER_ROW_MISSING", receipt["request_id"])
        row = rows[0]
        expected_usage = {"input_tokens": receipt["usage"]["prompt_tokens"],
                          "output_tokens": receipt["usage"]["completion_tokens"]}
        try:
            settled_cost = Decimal(str(row.get("estimated_actual_cny")))
            receipt_cost = Decimal(str(receipt.get("cost_cny")))
        except (InvalidOperation, ValueError):
            raise ContractError("LIVE_COST_SETTLEMENT_MISMATCH", receipt["request_id"])
        if (not settled_cost.is_finite() or not receipt_cost.is_finite() or receipt_cost < 0
                or row.get("status") != "SETTLED" or row.get("provider_request_id") != receipt["provider_request_id"]
                or row.get("usage") != expected_usage or row.get("finish_reason") != "stop"
                or row.get("returned_model") != MODEL
                or settled_cost != receipt_cost):
            raise ContractError("LIVE_COST_SETTLEMENT_MISMATCH", receipt["request_id"])
        if any(item.get("request_id") == receipt["request_id"]
               or item.get("provider_request_id") == receipt["provider_request_id"]
               for item in state.get("provider_requests", [])):
            raise ContractError("LIVE_PROVIDER_REQUEST_ID_DUPLICATE", receipt["provider_request_id"])
        state.setdefault("provider_requests", []).append(receipt)
        state["updated_at"] = utc_now()
        save_state(run, state)
    return {"status": "NK_LIVE_RECEIPT_BOUND", "request_id": receipt["request_id"],
            "provider_request_id": receipt["provider_request_id"]}
