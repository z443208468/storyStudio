"""Persistent estimate budget guard for the P2 first-scene campaign.

Reserve before a provider request; settle from provider-reported usage afterward.
The ledger is shared across run IDs. Missing usage keeps the full reservation held.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "production.example.json"
PRICING = ROOT / "config" / "p2_cost_pricing_2026-10-10.json"
LEDGER = ROOT / "runtime" / "private" / "p2-cost-ledger.json"
MICRO = Decimal("0.000001")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def money(value: Decimal) -> str:
    return str(value.quantize(MICRO, rounding=ROUND_CEILING))


@contextmanager
def provider_slot():
    """Cross-process admission bound shared by CNW provider requests."""
    limit = json.loads(CONFIG.read_text(encoding="utf-8-sig"))["provider"]["max_in_flight"]
    if type(limit) is not int or not 1 <= limit <= 5:
        raise ValueError("MAX_IN_FLIGHT_POLICY_MISMATCH")
    directory = LEDGER.parent / "provider-slots"
    if directory.is_symlink():
        raise ValueError("PROVIDER_SLOT_PATH_UNSAFE")
    directory.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 210
    acquired = None
    while acquired is None:
        for index in range(limit):
            path = directory / f"slot-{index}.lock"
            if path.is_symlink():
                raise ValueError("PROVIDER_SLOT_PATH_UNSAFE")
            stream = open(path, "a+b")
            # Windows byte-range locks can cover EOF. Initializing a sentinel
            # before locking races with another process already owning byte 0.
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = stream
                break
            except (OSError, BlockingIOError):
                stream.close()
        if acquired is None:
            if time.monotonic() >= deadline:
                raise TimeoutError("PROVIDER_SLOT_TIMEOUT")
            time.sleep(0.05)
    try:
        yield
    finally:
        acquired.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(acquired.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(acquired.fileno(), fcntl.LOCK_UN)
        acquired.close()


def load_config():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    pricing = json.loads(PRICING.read_text(encoding="utf-8-sig"))
    guard = cfg["cost_guard"]
    if guard.get("currency") != "CNY" or guard.get("persist_across_run_ids") is not True:
        raise ValueError("COST_GUARD_CONFIG_INVALID")
    if pricing.get("requested_model") != cfg["provider"]["model"] or pricing.get("currency") != guard["currency"]:
        raise ValueError("PRICING_CONFIG_MISMATCH")
    guard = dict(guard, model=cfg["provider"]["model"])
    return guard, pricing


@contextmanager
def locked_ledger():
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    if LEDGER.parent.is_symlink() or (LEDGER.exists() and LEDGER.is_symlink()):
        raise ValueError("COST_LEDGER_SYMLINK_REJECTED")
    lock_path = LEDGER.with_suffix(".lock")
    stream = open(lock_path, "a+b")
    try:
        deadline = time.monotonic() + 15
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    raise TimeoutError("COST_LEDGER_LOCK_TIMEOUT")
                time.sleep(0.05)
        try:
            if LEDGER.exists():
                ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
            else:
                guard, pricing = load_config()
                ledger = {
                    "schema": 1,
                    "campaign_id": guard["scope"],
                    "currency": guard["currency"],
                    "limit": str(Decimal(str(guard["estimated_campaign_limit"]))),
                    "pricing_snapshot": pricing,
                    "created_at": now(),
                    "requests": [],
                }
            yield ledger
            tmp = LEDGER.with_name(LEDGER.name + ".tmp-" + uuid.uuid4().hex)
            tmp.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(tmp, LEDGER)
        finally:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    finally:
        stream.close()


def estimate(input_tokens: int, output_tokens: int, pricing) -> Decimal:
    usd = (Decimal(input_tokens) * Decimal(str(pricing["input_cache_miss_usd_per_million_peak"]))
           + Decimal(output_tokens) * Decimal(str(pricing["output_usd_per_million_peak"]))) / Decimal(1_000_000)
    return usd * Decimal(str(pricing["usd_to_cny_estimate"]))


def amounts(ledger):
    committed = Decimal("0")
    for request in ledger["requests"]:
        if request["status"] in ("PENDING", "UNKNOWN_NOT_ZERO"):
            committed += Decimal(request["reserved_cny"])
        elif request["status"] in ("SETTLED", "SETTLED_OVER_BUDGET"):
            committed += Decimal(request["estimated_actual_cny"])
    return committed


def command_reserve(args, *, emit=True):
    if args.input_token_cap <= 0 or args.output_token_cap <= 0:
        raise ValueError("TOKEN_CAPS_MUST_BE_POSITIVE")
    with locked_ledger() as ledger:
        if any(row["request_id"] == args.request_id for row in ledger["requests"]):
            raise ValueError("REQUEST_ID_ALREADY_RECORDED")
        guard, pricing = load_config()
        reserve = estimate(args.input_token_cap, args.output_token_cap, pricing)
        committed = amounts(ledger)
        limit = Decimal(ledger["limit"])
        if committed + reserve > limit:
            raise ValueError("CAMPAIGN_ESTIMATE_LIMIT_WOULD_BE_EXCEEDED")
        row = {
            "request_id": args.request_id,
            "run_id": args.run_id,
            "purpose": args.purpose,
            "requested_model": guard["model"],
            "reserved_input_token_cap": args.input_token_cap,
            "reserved_output_token_cap": args.output_token_cap,
            "reserved_cny": money(reserve),
            "status": "PENDING",
            "reserved_at": now(),
        }
        ledger["requests"].append(row)
        result = {"status": "RESERVED", "request_id": args.request_id,
                          "reserved_cny": row["reserved_cny"],
                          "campaign_committed_cny": money(committed + reserve), "limit_cny": ledger["limit"]}
    if emit:
        print(json.dumps(result))
    return result


def command_settle(args, *, emit=True):
    with locked_ledger() as ledger:
        matches = [row for row in ledger["requests"] if row["request_id"] == args.request_id]
        if len(matches) != 1:
            raise ValueError("REQUEST_ID_NOT_FOUND")
        row = matches[0]
        if row["status"] != "PENDING":
            raise ValueError("REQUEST_NOT_PENDING")
        row["provider_request_id"] = args.provider_request_id
        row["returned_model"] = args.returned_model
        row["finish_reason"] = args.finish_reason
        row["settled_at"] = now()
        if args.input_tokens is None or args.output_tokens is None:
            row["status"] = "UNKNOWN_NOT_ZERO"
            row["usage"] = "UNKNOWN_NOT_ZERO"
            charge = Decimal(row["reserved_cny"])
        else:
            if args.input_tokens < 0 or args.output_tokens < 0:
                raise ValueError("USAGE_TOKENS_MUST_BE_NONNEGATIVE")
            _, pricing = load_config()
            charge = estimate(args.input_tokens, args.output_tokens, pricing)
            over_caps = (args.input_tokens > row["reserved_input_token_cap"]
                         or args.output_tokens > row["reserved_output_token_cap"])
            projected_campaign = amounts(ledger) - Decimal(row["reserved_cny"]) + charge
            over_campaign = projected_campaign > Decimal(ledger["limit"])
            over_reservation = charge > Decimal(row["reserved_cny"])
            row["status"] = "SETTLED_OVER_BUDGET" if (over_caps or over_campaign or over_reservation) else "SETTLED"
            row["usage"] = {"input_tokens": args.input_tokens, "output_tokens": args.output_tokens}
            row["estimated_actual_cny"] = money(charge)
            row["budget_exceeded"] = {
                "token_caps": over_caps,
                "reservation": over_reservation,
                "campaign_limit": over_campaign,
            }
        committed = amounts(ledger)
        result = {"status": row["status"], "request_id": args.request_id,
                          "estimated_request_cny": money(charge),
                          "campaign_committed_cny": money(committed), "limit_cny": ledger["limit"]}
    if emit:
        print(json.dumps(result))
    return result


def command_report(_args):
    with locked_ledger() as ledger:
        print(json.dumps({"campaign_id": ledger["campaign_id"], "currency": ledger["currency"],
                          "limit_cny": ledger["limit"], "committed_cny": money(amounts(ledger)),
                          "requests": ledger["requests"]}, ensure_ascii=False, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    reserve = sub.add_parser("reserve")
    reserve.add_argument("--request-id", required=True)
    reserve.add_argument("--run-id", required=True)
    reserve.add_argument("--purpose", required=True)
    reserve.add_argument("--input-token-cap", required=True, type=int)
    reserve.add_argument("--output-token-cap", required=True, type=int)
    reserve.set_defaults(func=command_reserve)
    settle = sub.add_parser("settle")
    settle.add_argument("--request-id", required=True)
    settle.add_argument("--provider-request-id")
    settle.add_argument("--returned-model")
    settle.add_argument("--finish-reason")
    settle.add_argument("--input-tokens", type=int)
    settle.add_argument("--output-tokens", type=int)
    settle.set_defaults(func=command_settle)
    report = sub.add_parser("report")
    report.set_defaults(func=command_report)
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"COST_GUARD_FAILED:{type(exc).__name__}:{exc}", file=sys.stderr)
        raise SystemExit(2)
