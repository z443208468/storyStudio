"""Persistent estimate budget guard for the P2 first-scene campaign.

Reserve before a provider request; settle from provider-reported usage afterward.
The ledger is shared across run IDs. Missing usage keeps the full reservation held.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import json
import os
import re
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "production.example.json"
PRICING = ROOT / "config" / "p2_cost_pricing_2026-10-10.json"
LEDGER = ROOT / "runtime" / "private" / "p2-cost-ledger.json"
MICRO = Decimal("0.000001")


@dataclass(frozen=True)
class CostContext:
    """Accounting attribution only; never a Provider or spending grant."""
    project_instance_id: str
    project_id: str
    run_id: str
    stage: str
    binding_sha256: str

    def record(self):
        result = asdict(self)
        for name in ("project_instance_id", "project_id", "run_id", "stage"):
            if not isinstance(result[name], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}", result[name]):
                raise ValueError("COST_CONTEXT_INVALID")
        if not isinstance(self.binding_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.binding_sha256):
            raise ValueError("COST_CONTEXT_INVALID")
        return result


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def money(value: Decimal) -> str:
    return str(value.quantize(MICRO, rounding=ROUND_CEILING))


def campaign_limit(value) -> Decimal | None:
    """JSON null means explicitly unlimited; malformed limits never disable it."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("CAMPAIGN_LIMIT_INVALID")
    try:
        amount = Decimal(str(value))
    except Exception as exc:
        raise ValueError("CAMPAIGN_LIMIT_INVALID") from exc
    if not amount.is_finite() or amount <= 0:
        raise ValueError("CAMPAIGN_LIMIT_INVALID")
    return amount


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
    guard, pricing, _ = _config_snapshot()
    return guard, pricing


def _config_snapshot():
    config_raw, pricing_raw = CONFIG.read_bytes(), PRICING.read_bytes()
    cfg = json.loads(config_raw.decode("utf-8-sig"))
    pricing = json.loads(pricing_raw.decode("utf-8-sig"))
    guard = cfg["cost_guard"]
    campaign_limit(guard["estimated_campaign_limit"])
    if guard.get("currency") != "CNY" or guard.get("persist_across_run_ids") is not True:
        raise ValueError("COST_GUARD_CONFIG_INVALID")
    if pricing.get("requested_model") != cfg["provider"]["model"] or pricing.get("currency") != guard["currency"]:
        raise ValueError("PRICING_CONFIG_MISMATCH")
    guard = dict(guard, model=cfg["provider"]["model"])
    return guard, pricing, {"config_sha256": hashlib.sha256(config_raw).hexdigest(),
                            "pricing_sha256": hashlib.sha256(pricing_raw).hexdigest()}


@contextmanager
def _ledger_lock():
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    if LEDGER.parent.is_symlink() or (LEDGER.exists() and LEDGER.is_symlink()):
        raise ValueError("COST_LEDGER_SYMLINK_REJECTED")
    lock_path = LEDGER.with_suffix(".lock")
    if lock_path.is_symlink():
        raise ValueError("COST_LEDGER_SYMLINK_REJECTED")
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
            yield
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


def read_ledger_snapshot():
    """Read under the writer lock without republishing or creating a ledger."""
    return json.loads(read_ledger_bytes().decode("utf-8"))


def read_ledger_bytes():
    """Retain the exact ledger representation for evidence copies."""
    with _ledger_lock():
        return LEDGER.read_bytes()


def _publish_ledger(tmp, preimage, payload):
    """Retry only the same atomic publish, while the caller retains the lock."""
    for attempt in range(3):
        if tmp.read_bytes() != payload:
            raise ValueError("COST_LEDGER_TEMP_CHANGED")
        current = LEDGER.read_bytes() if LEDGER.exists() else None
        if current != preimage:
            raise ValueError("COST_LEDGER_PREIMAGE_CHANGED")
        try:
            os.replace(tmp, LEDGER)
            return
        except PermissionError as exc:
            if getattr(exc, "winerror", None) not in (5, 32, 33) or attempt == 2:
                raise
            time.sleep(0.05)


@contextmanager
def locked_ledger():
    with _ledger_lock():
        preimage = LEDGER.read_bytes() if LEDGER.exists() else None
        if preimage is not None:
            ledger = json.loads(preimage.decode("utf-8"))
        else:
            guard, pricing = load_config()
            ledger = {
                "schema": 1,
                "campaign_id": guard["scope"],
                "currency": guard["currency"],
                "limit": (str(campaign_limit(guard["estimated_campaign_limit"]))
                          if guard["estimated_campaign_limit"] is not None else None),
                "pricing_snapshot": pricing,
                "created_at": now(),
                "requests": [],
            }
        yield ledger
        tmp = LEDGER.with_name(LEDGER.name + ".tmp-" + uuid.uuid4().hex)
        # Preserve the existing platform newline representation.
        payload = (json.dumps(ledger, ensure_ascii=False, indent=2) + "\n").replace("\n", os.linesep).encode("utf-8")
        tmp.write_bytes(payload)
        _publish_ledger(tmp, preimage, payload)


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


def command_reserve(args, *, emit=True, context: CostContext | None = None, expected_model=None,
                    authorization_check=None):
    binding = context.record() if isinstance(context, CostContext) else None
    if context is not None and binding is None:
        raise ValueError("COST_CONTEXT_INVALID")
    if binding is not None and args.run_id != binding["run_id"]:
        raise ValueError("COST_CONTEXT_RUN_MISMATCH")
    if args.input_token_cap <= 0 or args.output_token_cap <= 0:
        raise ValueError("TOKEN_CAPS_MUST_BE_POSITIVE")
    with locked_ledger() as ledger:
        if any(row["request_id"] == args.request_id for row in ledger["requests"]):
            raise ValueError("REQUEST_ID_ALREADY_RECORDED")
        if binding is None:
            guard, pricing = load_config()
            snapshot = None
        else:
            guard, pricing, snapshot = _config_snapshot()
        if expected_model is not None and guard["model"] != expected_model:
            raise ValueError("COST_PROVIDER_MODEL_MISMATCH")
        reserve = estimate(args.input_token_cap, args.output_token_cap, pricing)
        committed = amounts(ledger)
        limit = campaign_limit(ledger["limit"])
        if limit is not None and committed + reserve > limit:
            raise ValueError("CAMPAIGN_ESTIMATE_LIMIT_WOULD_BE_EXCEEDED")
        live_grant = (authorization_check(ledger=ledger, args=args, reserve=reserve, cost_snapshot=snapshot)
                      if authorization_check is not None else None)
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
        if binding is not None:
            row["cost_context"] = binding
            row["cost_policy_snapshot"] = snapshot
            row["cost_pricing_snapshot"] = pricing
        if live_grant is not None:
            row["live_authorization"] = live_grant
        ledger["requests"].append(row)
        result = {"status": "RESERVED", "request_id": args.request_id,
                          "reserved_cny": row["reserved_cny"],
                          "campaign_committed_cny": money(committed + reserve), "limit_cny": ledger["limit"]}
        if binding is not None:
            result["cost_context"] = binding
    if emit:
        print(json.dumps(result))
    return result


def command_settle(args, *, emit=True, context: CostContext | None = None):
    binding = context.record() if isinstance(context, CostContext) else None
    if context is not None and binding is None:
        raise ValueError("COST_CONTEXT_INVALID")
    with locked_ledger() as ledger:
        matches = [row for row in ledger["requests"] if row["request_id"] == args.request_id]
        if len(matches) != 1:
            raise ValueError("REQUEST_ID_NOT_FOUND")
        row = matches[0]
        if row.get("cost_context") != binding:
            raise ValueError("COST_CONTEXT_SETTLEMENT_MISMATCH")
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
            if binding is None:
                _, pricing = load_config()
            else:
                pricing = row["cost_pricing_snapshot"]
            charge = estimate(args.input_tokens, args.output_tokens, pricing)
            over_caps = (args.input_tokens > row["reserved_input_token_cap"]
                         or args.output_tokens > row["reserved_output_token_cap"])
            projected_campaign = amounts(ledger) - Decimal(row["reserved_cny"]) + charge
            limit = campaign_limit(ledger["limit"])
            over_campaign = limit is not None and projected_campaign > limit
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
        if binding is not None:
            result["cost_context"] = binding
    if emit:
        print(json.dumps(result))
    return result


def command_report(_args):
    with locked_ledger() as ledger:
        print(json.dumps({"campaign_id": ledger["campaign_id"], "currency": ledger["currency"],
                          "limit_cny": ledger["limit"], "committed_cny": money(amounts(ledger)),
                          "requests": ledger["requests"]}, ensure_ascii=False, indent=2))


def command_set_limit(args, *, emit=True):
    """Change campaign admission policy while preserving every historical charge."""
    if not isinstance(args.reason, str) or not args.reason.strip():
        raise ValueError("CAMPAIGN_LIMIT_CHANGE_REASON_REQUIRED")
    limit = None if args.unlimited else campaign_limit(args.limit_cny)
    if not args.unlimited and limit is None:
        raise ValueError("CAMPAIGN_LIMIT_INVALID")
    value = str(limit) if limit is not None else None
    with locked_ledger() as ledger:
        old = ledger["limit"]
        if old != value:
            ledger.setdefault("limit_changes", []).append({"at": now(), "old_limit_cny": old,
                "new_limit_cny": value, "reason": args.reason.strip()})
            ledger["limit"] = value
        result = {"status": "CAMPAIGN_LIMIT_UPDATED", "old_limit_cny": old,
                  "limit_cny": value, "campaign_committed_cny": money(amounts(ledger)),
                  "requests_preserved": len(ledger["requests"])}
    if emit:
        print(json.dumps(result, ensure_ascii=False))
    return result


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
    change = sub.add_parser("set-limit")
    option = change.add_mutually_exclusive_group(required=True)
    option.add_argument("--unlimited", action="store_true")
    option.add_argument("--limit-cny")
    change.add_argument("--reason", required=True)
    change.set_defaults(func=command_set_limit)
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"COST_GUARD_FAILED:{type(exc).__name__}:{exc}", file=sys.stderr)
        raise SystemExit(2)
