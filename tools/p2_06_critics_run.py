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
sys.path.insert(0, str(ROOT / "tools"))
import critics_bridge  # noqa: E402
import p2_cost_guard  # noqa: E402

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
    args = parser.parse_args(argv)

    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY_REQUIRED")
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
    input_path = critics_bridge.project_path(args.input)
    if not input_path.is_file():
        raise SystemExit("INPUT_FILE_NOT_FOUND")
    command = [args.action, "--run-dir", str(run_dir), "--plot" if args.action != "text-refine" else "--excerpt", str(input_path)]
    if args.action == "plan-revise":
        critique_path = critics_bridge.project_path(args.critique)
        if not critique_path.is_file():
            raise SystemExit("CRITIQUE_FILE_NOT_FOUND")
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
        p2_cost_guard.command_reserve(reserve)
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
            p2_cost_guard.command_settle(settle)
            call["response"] = strip_key(payload)
            call["http_status"] = response.status_code
            call["estimated_cost_cny"] = next(
                row.get("estimated_actual_cny", row.get("reserved_cny"))
                for row in p2_cost_guard.read_ledger_snapshot()["requests"]
                if row["request_id"] == request_id
            )
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
                p2_cost_guard.command_settle(settle)
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
    ledger_copy = p2_cost_guard.read_ledger_bytes()
    (run_dir / "p2-cost-ledger.json").write_bytes(ledger_copy)
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
