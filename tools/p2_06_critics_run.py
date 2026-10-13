"""Run one native CritiCS method in a private P2-06 run with per-call cost capture."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid

import httpx

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
try:
    from . import critics_bridge, p2_cost_guard, cost_guard
except ImportError:  # direct script execution
    sys.path.insert(0, str(ROOT / "tools"))
    import critics_bridge
    import p2_cost_guard
    import cost_guard

MODEL = "deepseek-flash"
HOST = "api.deepseek.com"
CAP_INPUT = 12000
CAP_OUTPUT = 2048


def strip_key(value):
    if isinstance(value, dict):
        return {k: strip_key(v) for k, v in value.items() if k not in {"reasoning_content", "api_key", "authorization"}}
    if isinstance(value, list):
        return [strip_key(v) for v in value]
    return value


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", required=True, choices=("plan-critique", "plan-revise", "text-refine"))
    parser.add_argument("--input", required=True, help="Plot or key excerpt under the selected private project")
    parser.add_argument("--critique", help="CritiCS feedback JSON for plan-revise")
    run_group = parser.add_mutually_exclusive_group(required=True)
    run_group.add_argument("--run-name", help="Legacy run name under the repository runs directory")
    run_group.add_argument("--run-dir", help="Explicit direct child of a registered private runs directory")
    parser.add_argument("--ledger-run-id", help="Optional parent production run ID for shared campaign settlement")
    parser.add_argument("--parent-run-dir", help="Registered CNW parent Run whose project owns cost attribution")
    parser.add_argument("--parent-stage", help="CNW support hook stage used in the shared cost context")
    args = parser.parse_args(argv)

    if args.action == "plan-revise" and not args.critique:
        raise SystemExit("CRITIQUE_REQUIRED_FOR_PLAN_REVISE")
    if args.run_name:
        run_name = Path(args.run_name).name
        if run_name != args.run_name or run_name in {"", ".", ".."}:
            raise SystemExit("RUN_NAME_INVALID")
        run_dir = ROOT / "runs" / run_name
    else:
        supplied_run_dir = critics_bridge.project_path(args.run_dir, directory=True)
        run_name = supplied_run_dir.name
        run_dir = supplied_run_dir
    account = None
    parent_run_dir = None
    if args.parent_run_dir:
        parent_run_dir = critics_bridge.project_path(args.parent_run_dir, directory=True)
        project = critics_bridge._registered_project_for_path(parent_run_dir)
        child_project = critics_bridge._registered_project_for_path(run_dir)
        if (not project or child_project != project or run_dir.parent != parent_run_dir.parent
                or parent_run_dir.name != args.ledger_run_id
                or args.parent_stage != ("critics_text" if args.action == "text-refine" else "critics_plot")):
            raise SystemExit("CRITICS_PARENT_RUN_BINDING_INVALID")
        try:
            from .cnw_runner import _require_generic_provider_authorization
        except ImportError:
            from cnw_runner import _require_generic_provider_authorization
        _require_generic_provider_authorization(parent_run_dir, stage=args.parent_stage)
        account = cost_guard.for_run(parent_run_dir, stage=args.parent_stage, model=MODEL)
        if not isinstance(account, cost_guard.RunAccount):
            raise SystemExit("CRITICS_COST_CONTEXT_NOT_REGISTERED")
    elif args.parent_stage:
        raise SystemExit("CRITICS_PARENT_RUN_BINDING_INVALID")
    elif critics_bridge._registered_project_for_path(run_dir):
        raise SystemExit("CRITICS_PARENT_RUN_BINDING_REQUIRED")
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY_REQUIRED")
    return _execute_native(args, run_dir, account=account, parent_run_dir=parent_run_dir)


def _execute_native(args, run_dir: Path, *, account=None, parent_run_dir: Path | None = None) -> int:
    """Execute an admitted native action through the shared accounting boundary.

    The CLI performs production admission before calling this component. Offline
    component tests inject only native transport, using a synthetic shared ledger.
    """
    run_name = run_dir.name
    owner = critics_bridge._registered_project_for_path(run_dir)
    if owner and (not isinstance(account, cost_guard.RunAccount) or parent_run_dir is None
                  or parent_run_dir.parent.parent != owner or parent_run_dir.parent != run_dir.parent
                  or account.run != parent_run_dir or args.ledger_run_id != parent_run_dir.name
                  or account.context.run_id != parent_run_dir.name
                  or account.context.stage != args.parent_stage):
        raise SystemExit("CRITICS_PARENT_RUN_BINDING_INVALID")
    guard = account or p2_cost_guard
    input_path = critics_bridge.project_path(args.input)
    if not input_path.is_file():
        raise SystemExit("INPUT_FILE_NOT_FOUND")
    if account and (parent_run_dir is None or not input_path.is_relative_to(parent_run_dir)
                    or critics_bridge._registered_project_for_path(input_path) != parent_run_dir.parent.parent):
        raise SystemExit("CRITICS_INPUT_PARENT_RUN_MISMATCH")
    command = [args.action, "--run-dir", str(run_dir), "--plot" if args.action != "text-refine" else "--excerpt", str(input_path)]
    if args.action == "plan-revise":
        critique_path = critics_bridge.project_path(args.critique)
        if not critique_path.is_file():
            raise SystemExit("CRITIQUE_FILE_NOT_FOUND")
        if account and critics_bridge._registered_project_for_path(critique_path) != parent_run_dir.parent.parent:
            raise SystemExit("CRITICS_CRITIQUE_PROJECT_MISMATCH")
        command.extend(["--critique", str(critique_path)])

    calls = []
    original_send = httpx.Client.send

    def capture_send(client, request, *send_args, **send_kwargs):
        if request.url.host != HOST or request.url.path != "/v1/chat/completions" or request.method != "POST":
            return original_send(client, request, *send_args, **send_kwargs)

        request_id = f"p206-{args.action}-{uuid.uuid4().hex}"
        raw_bytes = request.read()
        try:
            body = json.loads(raw_bytes.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError("CRITICS_PROVIDER_REQUEST_NOT_JSON") from exc
        if body.get("model") != MODEL:
            raise RuntimeError("CRITICS_PROVIDER_MODEL_MISMATCH")
        if body.get("max_tokens") is None or int(body["max_tokens"]) > CAP_OUTPUT:
            body["max_tokens"] = CAP_OUTPUT

        reserve = argparse.Namespace(
            request_id=request_id,
            run_id=args.ledger_run_id or run_name,
            purpose=f"P2-06 native CritiCS {args.action} provider call",
            input_token_cap=CAP_INPUT,
            output_token_cap=CAP_OUTPUT,
        )
        headers = {k: v for k, v in request.headers.items() if k.lower() != "content-length"}
        outbound = httpx.Request(
            request.method,
            request.url,
            headers=headers,
            content=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            extensions=request.extensions,
        )
        call = {"local_request_id": request_id, "request": strip_key(body), "max_output_tokens_enforced": CAP_OUTPUT}
        try:
            with guard.provider_slot():
                if account:
                    reservation = account.command_reserve(reserve, emit=False)
                else:
                    reservation = p2_cost_guard.command_reserve(reserve, emit=False)
                if reservation.get("status") != "RESERVED":
                    raise RuntimeError("CRITICS_COST_RESERVATION_FAILED")
                response = original_send(client, outbound, *send_args, **send_kwargs)
                response.read()
                try:
                    payload = response.json()
                except Exception:
                    payload = {"non_json_response": True}
                choices = payload.get("choices") or []
                choice = choices[0] if choices else {}
                usage = payload.get("usage") or {}
                provider_id = payload.get("id")
                returned_model = payload.get("model")
                finish_reason = choice.get("finish_reason")
                input_tokens = usage.get("prompt_tokens")
                output_tokens = usage.get("completion_tokens")
                settle = argparse.Namespace(
                    request_id=request_id,
                    provider_request_id=provider_id,
                    returned_model=returned_model,
                    finish_reason=finish_reason,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                settlement = account.command_settle(settle, emit=False) if account else p2_cost_guard.command_settle(settle, emit=False)
                call["ledger_settlement"] = settlement
                call["cost_context"] = account.context.record() if account else None
                call["response"] = strip_key(payload)
                call["http_status"] = response.status_code
                call["estimated_cost_cny"] = settlement.get("estimated_request_cny")
                calls.append(call)
                response.extensions.update(request.extensions)
                return response
        except Exception as exc:
            settle = argparse.Namespace(
                request_id=request_id,
                provider_request_id=None,
                returned_model=None,
                finish_reason=None,
                input_tokens=None,
                output_tokens=None,
            )
            try:
                if account:
                    settlement = account.command_settle(settle, emit=False)
                else:
                    settlement = p2_cost_guard.command_settle(settle, emit=False)
                call["ledger_settlement"] = settlement
                call["cost_context"] = account.context.record() if account else None
            except Exception:
                pass
            call["transport_error_type"] = type(exc).__name__
            calls.append(call)
            raise

    httpx.Client.send = capture_send
    failure = None
    try:
        result = critics_bridge.main(command)
    except BaseException as exc:
        result = 1
        failure = type(exc).__name__
    finally:
        httpx.Client.send = original_send

    if not run_dir.is_dir():
        raise RuntimeError("CRITICS_RUN_DIRECTORY_MISSING")
    (run_dir / "provider-calls.json").write_text(json.dumps(calls, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if account:
        context = account.context.record()
        rows = [row for row in p2_cost_guard.read_ledger_snapshot()["requests"]
                if row.get("cost_context") == context]
        (run_dir / "p2-cost-ledger.json").write_text(json.dumps({
            "schema": "cnw_critics_scoped_cost_evidence_v1", "cost_context": context,
            "requests": rows}, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    else:
        ledger_copy = p2_cost_guard.read_ledger_bytes()
        (run_dir / "p2-cost-ledger.json").write_bytes(ledger_copy)
    if account:
        receipt_path = run_dir / "run_receipt.json"
        if receipt_path.is_file():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["cost_binding"] = {"project_id": account.context.project_id,
                "project_instance_id": account.context.project_instance_id,
                "parent_run_id": account.context.run_id, "parent_run_path": str(parent_run_dir),
                "stage": args.parent_stage, "cost_context": account.context.record()}
            receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    if failure:
        (run_dir / "runner-error.json").write_text(json.dumps({"status": "FAILED_OR_UNKNOWN", "error_type": failure}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "SUCCEEDED" if result == 0 and failure is None else "FAILED_OR_UNKNOWN",
        "action": args.action,
        "run_dir": str(run_dir),
        "provider_call_count": len(calls),
        "provider_request_ids": [c.get("response", {}).get("id") for c in calls],
        "error_type": failure,
    }, ensure_ascii=False))
    return 0 if result == 0 and failure is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"P2_06_CRITICS_RUN_FAILED:{type(exc).__name__}:{exc}", file=sys.stderr)
        raise SystemExit(2)
