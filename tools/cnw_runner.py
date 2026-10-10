"""Persistent dispatcher for CNW production runs.

The stage sequence is the author's published per-chapter workflow
(``templates/config/workflow.template.yml``): plot -> scene_cards ->
writing_brief -> prose -> lint_layer1 -> lint_layer2 -> multi_lens_review ->
adversarial_verify -> completeness_critic -> refine -> re_review.

NK perspective is a support hook consumed while the writing brief is frozen;
CritiCS is a support hook attached to plot/text. Neither replaces an author
stage. ``promote`` / ``export`` / ``resume`` / ``sprint`` are post actions.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import uuid
from decimal import Decimal, InvalidOperation, ROUND_CEILING

import httpx

try:
    from .cnw_contract import ContractError, assert_output_within_root, check_required_fields, load_contract, validate_episode_budget, validate_scene_budget, validate_source_identity, validate_work_unit
except ImportError:  # direct script execution from PowerShell
    from cnw_contract import ContractError, assert_output_within_root, check_required_fields, load_contract, validate_episode_budget, validate_scene_budget, validate_source_identity, validate_work_unit

ROOT = Path(__file__).resolve().parents[1]

# CNW author `templates/config/workflow.template.yml` — 11 published stages.
CNW_STAGES = (
    "plot", "scene_cards", "writing_brief", "prose",
    "lint_layer1", "lint_layer2", "multi_lens_review",
    "adversarial_verify", "completeness_critic", "refine", "re_review",
)
STAGES = CNW_STAGES  # compatibility for callers iterating STAGES

# Non-CNW hooks and post actions, never counted as an author stage.
SUPPORT_HOOKS = ("nk_pov", "critics_plot", "critics_text")
POST_ACTIONS = ("promote", "export", "resume", "sprint")

LEGACY_ALIASES = {
    "cards": "scene_cards", "brief": "writing_brief", "draft": "prose",
    "lint1": "lint_layer1", "lint2": "lint_layer2",
    "lens5": "multi_lens_review", "verifier3": "adversarial_verify",
    "completeness": "completeness_critic", "re-review": "re_review",
}
STAGE_ALIASES = LEGACY_ALIASES  # historical name used by tooling/tests
STAGE_PROMPTS = {"plot": "plot.md", "scene_cards": "scene_cards.md", "writing_brief": "brief.md", "prose": "prose.md"}
PROVIDER_STAGES = {"plot", "scene_cards", "writing_brief", "prose", "multi_lens_review", "adversarial_verify", "completeness_critic", "refine", "re_review"}
LOCAL_STAGES = {"lint_layer1", "lint_layer2"}

WORKFLOW_PATH = ROOT / "runtime/reference/cnw_97ad71fe5e5e/templates/config/workflow.template.yml"
PROMPT_ROOT = ROOT / "prompts/cnw"
LENS_IDS = ("style", "character", "plot", "canon", "story_specific")
VERIFIER_IDS = ("correctness", "character_consistency", "continuity_plausibility")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-flash"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def safe_run_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", value) or value in {".", ".."}:
        raise ContractError("VALID_RUN_ID_REQUIRED", value)
    return value


def normalize_stage(value: str) -> str:
    if value in CNW_STAGES:
        return value
    if value in LEGACY_ALIASES:
        return LEGACY_ALIASES[value]
    raise ContractError("UNKNOWN_STAGE", value)


def stage_predecessors(stage: str, unit_kind: str | None = None) -> tuple[str, ...]:
    """Author stage order; content dependencies are recorded separately.

    Scene/Episode does not change the author's 11-stage order.
    """
    stage = normalize_stage(stage)
    return tuple(CNW_STAGES[:CNW_STAGES.index(stage)])


def run_path(run_id: str, runs_root: Path | None = None) -> Path:
    run_id = safe_run_id(run_id)
    base_candidate = (runs_root or ROOT / "runs").absolute()
    cursor = base_candidate
    while cursor != cursor.parent:
        if cursor.is_symlink():
            raise ContractError("RUN_ROOT_SYMLINK_REJECTED", str(cursor))
        cursor = cursor.parent
    base = base_candidate.resolve()
    target = base / run_id
    if target.is_symlink():
        raise ContractError("RUN_PATH_SYMLINK_REJECTED", run_id)
    resolved = target.resolve()
    if not resolved.is_relative_to(base):
        raise ContractError("RUN_PATH_UNSAFE", run_id)
    for parent in (target, *target.parents):
        if parent == base.parent:
            break
        if parent.is_symlink():
            raise ContractError("RUN_PATH_SYMLINK_REJECTED", str(parent))
    return target


def runs_root_for(args) -> Path:
    project_root = getattr(args, "project_root", None)
    return (Path(project_root).resolve() if project_root else ROOT) / "runs"


def safe_run_input(path: str | Path, run_directory: Path) -> Path:
    base = run_directory.resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (run_directory / candidate).absolute()
    cursor = candidate
    while cursor != cursor.parent:
        if cursor.is_symlink():
            raise ContractError("STAGE_INPUT_UNSAFE", "input path contains a symlink")
        cursor = cursor.parent
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(base) or not resolved.is_file():
        raise ContractError("STAGE_INPUT_OUTSIDE_RUN", str(candidate))
    return resolved


def load_state(path: Path) -> dict:
    state_path = path / "run_state.json"
    if not state_path.is_file() or state_path.is_symlink():
        raise ContractError("RUN_STATE_MISSING_OR_UNSAFE", str(state_path))
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("RUN_STATE_INVALID", str(exc)) from exc
    if state.get("run_id") != path.name:
        raise ContractError("RUN_IDENTITY_MISMATCH", path.name)
    # Compatibility read layer for pre-P3.1 run states: old aliases map to author
    # stages; the historical `pov` stage migrates into support_hooks['nk_pov'].
    stages = state.get("stages")
    if isinstance(stages, dict):
        migrated = dict(stages)  # keep the original records readable
        legacy_pov = stages.get("pov")
        for key, value in stages.items():
            if key in LEGACY_ALIASES:
                migrated.setdefault(LEGACY_ALIASES[key], value)
        for stage in CNW_STAGES:
            migrated.setdefault(stage, {"status": "NOT_RUN", "dependencies": [], "artifact": None})
        state["stages"] = migrated
        if legacy_pov is not None:
            state.setdefault("support_hooks", {}).setdefault("nk_pov", legacy_pov)
        state.setdefault("state_migrations", []).append("P3.1-stage-aliases")
    state.setdefault("support_hooks", {})
    if state.get("schema_version") == "cnw_run_state_v1" and "provider_config_sha256" not in state:
        production_config = ROOT / "config/production.example.json"
        cost_guard_runner = ROOT / "tools/p2_cost_guard.py"
        state["provider_config_sha256"] = sha(production_config.read_bytes())
        state["cost_guard_runner_sha256"] = sha(cost_guard_runner.read_bytes())
        state.setdefault("state_migrations", []).append("W05-provider-cost-policy-hashes")
    return state


def save_state(path: Path, state: dict) -> None:
    state_path = path / "run_state.json"
    if state_path.is_symlink():
        raise ContractError("RUN_STATE_SYMLINK_REJECTED", str(state_path))
    temp = state_path.with_name(f"run_state.json.tmp-{uuid.uuid4().hex}")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, state_path)


_HELD_LOCKS = threading.local()


def _held_paths() -> set:
    held = getattr(_HELD_LOCKS, "paths", None)
    if held is None:
        held = set()
        _HELD_LOCKS.paths = held
    return held


@contextmanager
def locked_run(path: Path, *, lock_name: str = "run.lock"):
    key = str((Path(path) / lock_name).resolve())
    held = _held_paths()
    if key in held:
        # Reentrant within the same process/thread: an enclosing stage already
        # owns the run lock, so downstream helpers may mutate state directly.
        yield
        return
    lock_path = path / lock_name
    if lock_path.is_symlink():
        raise ContractError("RUN_LOCK_SYMLINK_REJECTED", str(lock_path))
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
                    raise ContractError("RUN_LOCK_TIMEOUT", path.name)
                time.sleep(0.05)
        held.add(key)
        try:
            yield
        finally:
            held.discard(key)
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    finally:
        stream.close()


# --------------------------------------------------------------------------
# Literary source freeze
# --------------------------------------------------------------------------
def _source_root(contract: dict, project_root: Path) -> Path:
    source = contract["source"]
    if source.get("identity_type") == "imported_project":
        return (project_root / source.get("source_root", ".")).resolve(strict=True)
    return ROOT / "inputs/private/release" / source["zip_sha256"].lower() / "Cangqi_Jun_Release_2_3"


def literary_source_freeze(contract: dict, project_root: Path) -> dict[str, str]:
    paths = {
        "90_canon/canon.md": project_root / "90_canon/canon.md",
        "90_canon/character_bible.md": project_root / "90_canon/character_bible.md",
        "90_canon/glossary.md": project_root / "90_canon/glossary.md",
        "90_canon/timeline.md": project_root / "90_canon/timeline.md",
        "90_canon/world_bible.md": project_root / "90_canon/world_bible.md",
        "92_style_engine/style_guide.md": project_root / "92_style_engine/style_guide.md",
        "92_style_engine/forbidden_patterns.md": project_root / "92_style_engine/forbidden_patterns.md",
        "92_style_engine/character_voice_samples.md": project_root / "92_style_engine/character_voice_samples.md",
    }
    try:
        from .cnw_roles import read_production_preparation
    except ImportError:
        from cnw_roles import read_production_preparation
    preparation = read_production_preparation(project_root, contract)
    paths.update({name: project_root / name for name in preparation["source_hashes"]})
    arc_index = project_root / "04_chapter_design/arc_index.md"
    if arc_index.is_file():
        paths["04_chapter_design/arc_index.md"] = arc_index
    source_root = _source_root(contract, project_root)
    script = (source_root / contract["story"]["source_file"]).resolve(strict=True)
    manifest = (source_root / contract["source"]["manifest_file"]).resolve(strict=True)
    result = {f"project:{name}": sha(path.read_bytes()) for name, path in paths.items() if path.is_file()}
    result["preparation:identity"] = sha(json.dumps({"files": preparation["source_hashes"],
        "arc_index": sha(arc_index.read_bytes()) if arc_index.is_file() else None}, sort_keys=True).encode("utf-8"))
    result[f"source:{script.relative_to(ROOT).as_posix()}"] = sha(script.read_bytes())
    result[f"manifest:{manifest.relative_to(ROOT).as_posix()}"] = sha(manifest.read_bytes())
    lines = script.read_text(encoding="utf-8-sig").splitlines()
    start = int(contract["story"]["before_anchor"].get("source_line_end", contract["story"]["before_anchor"]["source_line"]))
    end = int(contract["story"]["after_anchor"].get("source_line_end", contract["story"]["after_anchor"]["source_line"]))
    anchor_text = "\n".join(f"{number}: {lines[number - 1]}" for number in range(start, end + 1))
    result["source:anchor_excerpt"] = sha(anchor_text.encode("utf-8"))
    return result


def validate_literary_source_freeze(state: dict, project_root: Path) -> str:
    expected = state.get("literary_source_hashes")
    if not isinstance(expected, dict) or not expected:
        raise ContractError("LITERARY_SOURCE_FREEZE_MISSING", state.get("run_id", "unknown"))
    actual = {}
    contract = load_contract(project_root / state["contract_path"])
    for key, digest in expected.items():
        if key == "preparation:identity":
            try:
                from .cnw_roles import read_production_preparation
            except ImportError:
                from cnw_roles import read_production_preparation
            preparation = read_production_preparation(project_root, contract)
            arc_index = project_root / "04_chapter_design/arc_index.md"
            actual[key] = sha(json.dumps({"files": preparation["source_hashes"],
                "arc_index": sha(arc_index.read_bytes()) if arc_index.is_file() else None}, sort_keys=True).encode("utf-8"))
            continue
        if key.startswith("project:"):
            path = project_root / key.removeprefix("project:")
        elif key.startswith(("source:", "manifest:")) and key.rsplit(":", 1)[-1] != "anchor_excerpt":
            path = ROOT / key.split(":", 1)[1]
        elif key == "source:anchor_excerpt":
            continue
        else:
            raise ContractError("LITERARY_SOURCE_FREEZE_INVALID", key)
        if path.is_symlink() or not path.is_file():
            raise ContractError("LITERARY_SOURCE_CHANGED", key)
        actual[key] = sha(path.read_bytes())
    contract_path = project_root / state["contract_path"]
    contract = load_contract(contract_path)
    source_script = next((ROOT / key.split(":", 1)[1] for key in expected if key.startswith("source:") and not key.endswith("anchor_excerpt")), None)
    if source_script is None:
        raise ContractError("LITERARY_SOURCE_FREEZE_INVALID", "source script path missing")
    lines = source_script.read_text(encoding="utf-8-sig").splitlines()
    start = int(contract["story"]["before_anchor"].get("source_line_end", contract["story"]["before_anchor"]["source_line"]))
    end = int(contract["story"]["after_anchor"].get("source_line_end", contract["story"]["after_anchor"]["source_line"]))
    actual["source:anchor_excerpt"] = sha("\n".join(f"{number}: {lines[number - 1]}" for number in range(start, end + 1)).encode("utf-8"))
    if actual != expected:
        changed = sorted(key for key in expected if actual.get(key) != expected[key])
        raise ContractError("LITERARY_SOURCE_CHANGED", ", ".join(changed))
    return sha(json.dumps(expected, sort_keys=True).encode("utf-8"))


def stage_prompt_hash(stage: str) -> str | None:
    filename = STAGE_PROMPTS.get(stage)
    if not filename:
        return None
    prompt = PROMPT_ROOT / filename
    if prompt.is_symlink() or not prompt.is_file():
        raise ContractError("STAGE_PROMPT_MISSING_OR_UNSAFE", str(prompt))
    return sha(prompt.read_bytes())


# --------------------------------------------------------------------------
# Live transport (single attempt; reserve -> send -> settle)
# --------------------------------------------------------------------------
def _p2_guard():
    try:
        from . import p2_cost_guard
    except ImportError:
        import p2_cost_guard
    return p2_cost_guard


def _estimate_input_tokens(messages: list[dict]) -> int:
    raw = json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    # Conservative upper bound: one token per UTF-8 char is never below the
    # provider count for mixed CJK/ASCII JSON at this scale.
    return max(256, len(raw.decode("utf-8")) + 256)


def _sanitize(value):
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items() if k not in {"reasoning_content", "api_key", "authorization"}}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


def cnw_live_call(run_dir: Path, *, stage: str, role_id: str | None, messages: list[dict], output_cap: int, extra: dict | None = None) -> tuple[str, dict]:
    with _p2_guard().provider_slot():
        return _cnw_live_call_in_slot(run_dir, stage=stage, role_id=role_id, messages=messages, output_cap=output_cap, extra=extra)


def cached_receipts(state: dict) -> list[dict]:
    return state.get("provider_requests", []) + [attempt["prior_receipt"]
        for attempt in state.get("provider_attempts", []) if attempt.get("prior_receipt")]


def reactivate_receipt(run_dir: Path, receipt: dict) -> None:
    with locked_run(run_dir):
        state = load_state(run_dir)
        if not any(row.get("request_id") == receipt["request_id"] for row in state.get("provider_requests", [])):
            state.setdefault("provider_requests", []).append(receipt)
            save_state(run_dir, state)


def _cnw_live_call_in_slot(run_dir: Path, *, stage: str, role_id: str | None, messages: list[dict], output_cap: int, extra: dict | None = None) -> tuple[str, dict]:
    if stage not in PROVIDER_STAGES | {"project_import", "project_update", "project_audit", "project_handoff", "sprint_review", "sprint_handoff"}:
        raise ContractError("LIVE_STAGE_INVALID", stage)
    fingerprint = sha(json.dumps({"stage": stage, "role_id": role_id, "messages": messages,
        "output_cap": output_cap, "model": MODEL, "url": API_URL, "extra": extra}, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    for previous in cached_receipts(load_state(run_dir)):
        if previous.get("request_fingerprint") == fingerprint and previous.get("status") == "SUCCEEDED":
            content = _receipt_content(run_dir, previous)
            reactivate_receipt(run_dir, previous)
            return content, previous
    guard = _p2_guard()
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key or len(key.strip()) < 20:
        raise ContractError("DEEPSEEK_API_KEY_REQUIRED", stage)
    input_cap = _estimate_input_tokens(messages)
    request_id = f"cnw-{run_dir.name}-{stage}-{uuid.uuid4().hex}"
    reserved = guard.command_reserve(argparse.Namespace(request_id=request_id, run_id=run_dir.name,
            purpose=f"P3.1 CNW {stage}/{role_id or 'single'}", input_token_cap=input_cap, output_token_cap=output_cap), emit=False)
    if reserved.get("status") != "RESERVED":
        raise ContractError("LIVE_COST_RESERVATION_FAILED", stage)
    provider_dir = run_dir / "artifacts" / "provider"
    provider_dir.mkdir(parents=True, exist_ok=True)
    raw_path = provider_dir / f"{request_id}.json"
    body = {"model": MODEL, "messages": messages, "max_tokens": output_cap, "stream": False, "thinking": {"type": "disabled"}}
    request_path = provider_dir / f"{request_id}.request.json"
    # Preserve the exact API body for source-to-request review. Headers and keys
    # are excluded; project text remains in the private, ignored run directory.
    request_path.write_text(json.dumps(body, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    payload = None
    status_code = None
    try:
        response = httpx.post(API_URL, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-Client-Request-Id": request_id},
            json=body, timeout=httpx.Timeout(180.0, connect=20.0), follow_redirects=False)
        status_code = int(response.status_code)
        try:
            payload = response.json()
        except Exception:
            payload = None
        raw_bytes = (json.dumps({"request_id": request_id, "status": status_code, "requested_model": MODEL, "response": _sanitize(payload)}, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8") if payload is not None else response.content
        raw_path.write_bytes(raw_bytes)
    except Exception as exc:  # transport failure: keep the reservation held
        raw_path.write_text(json.dumps({"request_id": request_id, "transport_error_type": type(exc).__name__}, indent=2) + "\n", encoding="utf-8")
        guard.command_settle(argparse.Namespace(request_id=request_id, provider_request_id=None, returned_model=None, finish_reason=None, input_tokens=None, output_tokens=None), emit=False)
        raise ContractError("LIVE_PROVIDER_OUTCOME_UNKNOWN", f"{stage}: {type(exc).__name__}") from exc
    settlement = guard.command_settle(argparse.Namespace(request_id=request_id, provider_request_id=(payload or {}).get("id"),
            returned_model=(payload or {}).get("model"), finish_reason=((payload or {}).get("choices") or [{}])[0].get("finish_reason"),
            input_tokens=((payload or {}).get("usage") or {}).get("prompt_tokens"), output_tokens=((payload or {}).get("usage") or {}).get("completion_tokens")), emit=False)
    if settlement.get("status") == "SETTLED_OVER_BUDGET":
        raise ContractError("LIVE_PROVIDER_BUDGET_EXCEEDED", stage)
    if status_code != 200 or not isinstance(payload, dict):
        raise ContractError("LIVE_PROVIDER_RESPONSE_INVALID", f"{stage}: HTTP {status_code}")
    choice = (payload.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content")
    usage = payload.get("usage") or {}
    if (payload.get("model") != MODEL or choice.get("finish_reason") != "stop" or not isinstance(content, str) or not content.strip()
            or not all(isinstance(usage.get(k), int) and usage[k] > 0 for k in ("prompt_tokens", "completion_tokens"))):
        raise ContractError("LIVE_PROVIDER_RESPONSE_INVALID", f"{stage}: model/finish/content/usage invalid")
    _, pricing = guard.load_config()
    cost = guard.estimate(usage["prompt_tokens"], usage["completion_tokens"], pricing)
    receipt = {
        "stage": stage, "role_id": role_id, "request_id": request_id,
        "request_fingerprint": fingerprint,
        "provider_request_id": payload.get("id"), "model": payload.get("model"), "status": "SUCCEEDED",
        "http_status": status_code, "finish_reason": choice.get("finish_reason"),
        "usage": {"prompt_tokens": usage["prompt_tokens"], "completion_tokens": usage["completion_tokens"]},
        "input_sha256": sha(json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")),
        "request_path": request_path.relative_to(run_dir).as_posix(), "request_sha256": sha(request_path.read_bytes()),
        "output_sha256": sha(content.encode("utf-8")),
        "raw_response_path": raw_path.relative_to(run_dir).as_posix(), "raw_response_sha256": sha(raw_path.read_bytes()),
        "cost_cny": float(cost.quantize(Decimal("0.000001"), rounding=ROUND_CEILING)),
        "ledger_settlement": settlement, "mode": "LIVE", "fixture_only": False,
    }
    if extra:
        receipt.update(extra)
    with locked_run(run_dir):
        current = load_state(run_dir)
        if any(row.get("request_id") == request_id or row.get("provider_request_id") == receipt["provider_request_id"] for row in current.get("provider_requests", [])):
            raise ContractError("LIVE_PROVIDER_REQUEST_ID_DUPLICATE", receipt["provider_request_id"])
        current.setdefault("provider_requests", []).append(receipt)
        current["updated_at"] = now()
        save_state(run_dir, current)
    return content, receipt


def _receipt_content(run_dir: Path, receipt: dict) -> str:
    """Read a successful response only when both stored hashes still match."""
    path = assert_output_within_root(run_dir, receipt["raw_response_path"])
    if sha(path.read_bytes()) != receipt["raw_response_sha256"]:
        raise ContractError("LIVE_RAW_RESPONSE_HASH_MISMATCH", receipt["request_id"])
    if receipt.get("request_path"):
        request_path = assert_output_within_root(run_dir, receipt["request_path"])
        if sha(request_path.read_bytes()) != receipt.get("request_sha256"):
            raise ContractError("LIVE_REQUEST_HASH_MISMATCH", receipt["request_id"])
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if receipt.get("request_format") == "native_nk_payload":
            input_hash = sha(json.dumps(request, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        else:
            input_hash = sha(json.dumps(request["messages"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        if input_hash != receipt["input_sha256"]:
            raise ContractError("LIVE_REQUEST_IDENTITY_MISMATCH", receipt["request_id"])
    raw = json.loads(path.read_text(encoding="utf-8"))
    body = raw.get("response", raw)
    content = body["choices"][0]["message"]["content"]
    if not isinstance(content, str) or sha(content.encode("utf-8")) != receipt["output_sha256"]:
        raise ContractError("LIVE_RESPONSE_CONTENT_CHANGED", receipt["request_id"])
    return content


def _validate_raw_live_response(raw_path: Path, receipt: dict, usage: dict, index: int) -> None:
    try:
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        body = payload.get("response", payload) if isinstance(payload, dict) else None
        choices = body.get("choices") if isinstance(body, dict) else None
        raw_usage = body.get("usage") if isinstance(body, dict) else None
        if not choices or not isinstance(choices[0], dict) or not isinstance(raw_usage, dict):
            raise ValueError("missing response fields")
        outer_status = payload.get("status") if isinstance(payload, dict) else None
        outer_model = payload.get("requested_model") if isinstance(payload, dict) else None
        if outer_status is not None and outer_status != 200:
            raise ValueError("HTTP status mismatch")
        if outer_model is not None and outer_model != receipt["model"]:
            raise ValueError("requested model mismatch")
        if (body.get("id") != receipt["provider_request_id"] or body.get("model") != receipt["model"]
                or choices[0].get("finish_reason") != receipt["finish_reason"]
                or raw_usage.get("prompt_tokens") != usage["prompt_tokens"]
                or raw_usage.get("completion_tokens") != usage["completion_tokens"]):
            raise ValueError("raw response fields disagree with receipt")
        message = choices[0].get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or sha(content.encode("utf-8")) != str(receipt.get("output_sha256", "")).lower():
            raise ValueError("raw output content hash disagrees with receipt")
        if payload.get("request_id") is not None and payload["request_id"] != receipt["request_id"]:
            raise ValueError("request id mismatch")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError, IndexError, AttributeError) as exc:
        raise ContractError("LIVE_RAW_RESPONSE_RECEIPT_MISMATCH", f"request {index}: {exc}") from exc


def _validate_review_call_coverage(receipts: list[dict], findings_by_id: dict[str, set] | None = None) -> None:
    lenses = [row for row in receipts if row.get("stage") == "multi_lens_review"]
    if len(lenses) != 5 or {row.get("lens_id") for row in lenses} != set(LENS_IDS):
        raise ContractError("LIVE_REVIEW_CALL_SET_INCOMPLETE", f"multi_lens_review: expected {sorted(LENS_IDS)}, got {[r.get('lens_id') for r in lenses]}")
    verifiers = [row for row in receipts if row.get("stage") == "adversarial_verify"]
    if findings_by_id:
        for finding_id, expected in findings_by_id.items():
            selected = {row.get("verifier_id") for row in verifiers if row.get("finding_id") == finding_id}
            if selected != set(expected):
                raise ContractError("LIVE_REVIEW_CALL_SET_INCOMPLETE", f"adversarial_verify {finding_id}: expected {sorted(expected)}, got {sorted(selected)}")
    else:
        if verifiers:
            raise ContractError("LIVE_REVIEW_CALL_SET_INCOMPLETE", "adversarial_verify receipts without findings")


def bind_accepted_review_outputs(accepted_review: dict, provider_receipts: list[dict], run_root: Path) -> None:
    review_rows = accepted_review.get("provider_requests", [])
    lenses = [row for row in review_rows if row.get("stage") == "multi_lens_review"]
    if len(lenses) != 5 or {row.get("lens_id") for row in lenses} != set(LENS_IDS):
        raise ContractError("ACCEPTED_REVIEW_CALL_SET_INVALID", "five lenses required")
    findings = accepted_review.get("findings", [])
    verifier_rows = [row for row in review_rows if row.get("stage") == "adversarial_verify"]
    for finding in findings:
        selected = [row for row in verifier_rows if row.get("finding_id") == finding.get("finding_id")]
        if {row.get("verifier_id") for row in selected} != set(VERIFIER_IDS):
            raise ContractError("ACCEPTED_REVIEW_CALL_SET_INVALID", "three verifiers per finding required")
    actual = {(row.get("stage"), row.get("lens_id"), row.get("verifier_id"), row.get("provider_request_id")) for row in provider_receipts}
    expected = {(row.get("stage"), row.get("lens_id"), row.get("verifier_id"), row.get("provider_request_id")) for row in review_rows}
    if not expected.issubset(actual):
        raise ContractError("ACCEPTED_REVIEW_PROVIDER_RECEIPTS_UNBOUND", "review requests must belong to this verified run")
    receipt_by_id = {row.get("provider_request_id"): row for row in provider_receipts}
    for review_receipt in verifier_rows:
        receipt = receipt_by_id[review_receipt["provider_request_id"]]
        raw_path = assert_output_within_root(run_root, receipt["raw_response_path"])
        try:
            raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
            body = raw_payload.get("response", raw_payload)
            content = body["choices"][0]["message"]["content"]
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, IndexError) as exc:
            raise ContractError("ACCEPTED_VERIFIER_RAW_OUTPUT_INVALID", review_receipt.get("verifier_id", "unknown")) from exc
        if review_receipt.get("response_content") != content or review_receipt.get("output_sha256") != sha(content.encode("utf-8")):
            raise ContractError("ACCEPTED_VERIFIER_OUTPUT_MISMATCH", review_receipt.get("verifier_id", "unknown"))


# --------------------------------------------------------------------------
# Run creation
# --------------------------------------------------------------------------
def produce(args) -> dict:
    run_id = safe_run_id(args.run_id)
    unit_id = args.work_id or ""
    project_root = Path(args.project_root).resolve() if args.project_root else ROOT
    contract_file = Path(args.contract)
    if not contract_file.is_absolute():
        project_relative = project_root / contract_file
        contract_file = project_relative if project_relative.is_file() else ROOT / contract_file
    contract_candidate = contract_file.absolute()
    for ancestor in (contract_candidate, *contract_candidate.parents):
        if ancestor.is_symlink():
            raise ContractError("CONTRACT_PATH_UNSAFE", "contract path contains a symlink")
    contract_file = contract_file.resolve(strict=True)
    if not contract_file.is_relative_to(project_root):
        raise ContractError("CONTRACT_PATH_OUTSIDE_PROJECT", str(contract_file))
    contract = load_contract(contract_file)
    check_required_fields(contract)
    is_fixture = str(contract.get("project_id", "")).startswith("FICT_")
    private_workspace = (ROOT / "workspace").resolve()
    if not project_root.is_relative_to(private_workspace) and not is_fixture:
        raise ContractError("PROJECT_ROOT_OUTSIDE_PRIVATE_WORKSPACE", str(project_root))
    source = contract.get("source", {})
    if source.get("identity_type") == "imported_project":
        source_root = (project_root / source.get("source_root", ".")).resolve()
        if not source_root.is_relative_to(project_root):
            raise ContractError("SOURCE_PATH_UNSAFE", "import source root escapes the private project")
        validate_source_identity(contract, source_root=source_root, expected_version=source["version"], expected_zip_sha256=source["import_id"], expected_manifest_sha256=source["source_manifest_sha256"])
    elif not is_fixture:
        release_root = ROOT / "inputs/private/release" / source["zip_sha256"].lower() / "Cangqi_Jun_Release_2_3"
        validate_source_identity(contract, source_root=release_root, expected_version=source["version"], expected_zip_sha256=source["zip_sha256"], expected_manifest_sha256=source["local_private_source_manifest_sha256"])
    source_freeze = literary_source_freeze(contract, project_root) if not is_fixture else {}
    kind = args.unit or contract["unit"].get("kind")
    if kind != contract["unit"].get("kind"):
        raise ContractError("UNIT_KIND_MISMATCH", f"requested {kind}; contract has {contract['unit'].get('kind')}")
    if not unit_id:
        unit_id = str(contract["unit"].get("id", ""))
    if unit_id != contract["unit"].get("id"):
        raise ContractError("WORK_ID_MISMATCH", unit_id)
    validate_work_unit(contract)
    production_config = ROOT / "config/production.example.json"
    cost_guard_runner = ROOT / "tools/p2_cost_guard.py"
    provider_settings = json.loads(production_config.read_text(encoding="utf-8-sig"))
    max_in_flight = provider_settings.get("provider", {}).get("max_in_flight")
    if type(max_in_flight) is not int or not 1 <= max_in_flight <= 5:
        raise ContractError("MAX_IN_FLIGHT_POLICY_MISMATCH", "max_in_flight must be an integer from 1 to 5")
    if provider_settings.get("cost_guard", {}).get("persist_across_run_ids") is not True:
        raise ContractError("COST_GUARD_POLICY_MISMATCH", "persistent campaign accounting is required")
    path = run_path(run_id, project_root / "runs")
    try:
        path.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ContractError("RUN_ID_COLLISION", run_id) from exc
    try:
        (path / "artifacts").mkdir()
        contract_copy = path / "artifacts" / "contract.json"
        contract_bytes = contract_file.read_bytes()
        contract_copy.write_bytes(contract_bytes)
        stages = {stage: {"status": "NOT_RUN", "dependencies": list(stage_predecessors(stage)), "artifact": None} for stage in CNW_STAGES}
        state = {
            "schema_version": "cnw_run_state_v1", "run_id": run_id, "work_id": unit_id,
            "unit_kind": kind, "project_id": contract["project_id"],
            "contract_path": str(contract_file.relative_to(project_root)).replace("\\", "/"),
            "contract_sha256": sha(contract_bytes), "source_identity": contract["source"], "fixture_only": is_fixture,
            "created_at": now(), "updated_at": now(), "status": "RUN_CREATED", "mode": args.mode,
            "workflow_template_sha256": sha(WORKFLOW_PATH.read_bytes()),
            "cnw_method_source": {"commit": "97ad71fe5e5e76a82275c6c63d4add06fb60ab6e", "workflow_blob": "146ea01a484cc0578cf290478b3941599ad7fb15"},
            "cnw_stages": list(CNW_STAGES), "support_hooks": {}, "next_stage": CNW_STAGES[0],
            "provider_requests": [], "stages": stages, "max_in_flight": max_in_flight,
            "literary_source_hashes": source_freeze,
            "provider_config_sha256": sha(production_config.read_bytes()),
            "cost_guard_runner_sha256": sha(cost_guard_runner.read_bytes()),
        }
        save_state(path, state)
        for previous_path in (project_root / "runs").iterdir():
            if previous_path == path or previous_path.is_symlink() or not previous_path.is_dir():
                continue
            previous_state_path = previous_path / "run_state.json"
            if not previous_state_path.is_file() or previous_state_path.is_symlink():
                continue
            try:
                previous = json.loads(previous_state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if previous.get("work_id") == unit_id and previous.get("contract_sha256") != state["contract_sha256"]:
                previous["status"] = "INVALIDATED"
                previous["updated_at"] = now()
                for record in previous.get("stages", {}).values():
                    if record.get("status") in {"ACCEPTED", "READY_FOR_EXECUTION"}:
                        record["status"] = "INVALIDATED"
                save_state(previous_path, previous)
    except Exception:
        shutil.rmtree(path, ignore_errors=True)
        raise
    if args.mode == "live" and not getattr(args, "create_only", False):
        if not os.environ.get("DEEPSEEK_API_KEY"):
            raise ContractError("DEEPSEEK_API_KEY_REQUIRED", "live production requires the provider key")
        run_remaining_stages(path)
        state = load_state(path)
    return {"status": "LIVE_RUN_READY" if args.mode == "live" else "RUN_CREATED", "run_id": run_id, "work_id": unit_id, "contract_sha256": state["contract_sha256"], "path": str(path), "next_stage": state.get("next_stage", CNW_STAGES[0]), "provider_call": "performed" if args.mode == "live" else "none"}


def run_remaining_stages(run_dir: Path) -> None:
    for stage in CNW_STAGES:
        execute_cnw_stage(run_dir, stage)


# --------------------------------------------------------------------------
# Stage step (offline request packet, or live execution)
# --------------------------------------------------------------------------
def step(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    with locked_run(path, lock_name="execution.lock"):
        return _step_locked(args, path)


_MATERIALIZED = {"ACCEPTED", "STAGE_MATERIALIZED"}


def _step_locked(args, path: Path) -> dict:
    stage = normalize_stage(args.stage)
    state = load_state(path)
    if args.work_id and args.work_id != state["work_id"]:
        raise ContractError("WORK_ID_MISMATCH", args.work_id)
    if state.get("mode") == "live" and not state.get("fixture_only"):
        # Live step, produce and resume share the actual-consumption identity.
        # The packet-only fingerprint below remains the offline fixture path.
        if getattr(args, "input", None):
            raise ContractError("LIVE_STAGE_INPUT_NOT_SUPPORTED", "edit the designated project source and explicitly reopen references")
        expected = getattr(args, "expected_role_ids", None)
        if stage == "re_review" and expected is not None:
            if not expected or len(expected) != len(set(expected)) or set(expected) - set(LENS_IDS):
                raise ContractError("REREVIEW_ROLE_SET_REQUIRED", str(expected))
            state["stages"][stage]["expected_role_ids"] = expected
            save_state(path, state)
        return {"run_id": args.run_id, **execute_cnw_stage(path, stage)}
    else:
        source_hash = None
    expected_role_ids = None
    if stage == "re_review":
        expected_role_ids = getattr(args, "expected_role_ids", None)
        allowed_lenses = set(LENS_IDS)
        if (not isinstance(expected_role_ids, list) or not expected_role_ids
                or len(expected_role_ids) != len(set(expected_role_ids))
                or set(expected_role_ids) - allowed_lenses):
            raise ContractError("REREVIEW_ROLE_SET_REQUIRED", "supply the unique affected Lens IDs from the revision diff")
    requested_input = safe_run_input(args.input, path) if args.input else None
    for dependency in stage_predecessors(stage, state["unit_kind"]):
        if state["stages"][dependency]["status"] not in _MATERIALIZED:
            raise ContractError("STAGE_DEPENDENCY_NOT_ACCEPTED", dependency)
    input_hashes = {"contract": state["contract_sha256"]}
    for dependency in stage_predecessors(stage, state["unit_kind"]):
        record = state["stages"][dependency]
        if record.get("artifact"):
            input_hashes[dependency] = record["artifact"]["sha256"]
    if expected_role_ids is not None:
        input_hashes["expected_role_ids"] = sha(json.dumps(expected_role_ids, sort_keys=True).encode("utf-8"))
    if requested_input:
        input_hashes["provided_input"] = sha(requested_input.read_bytes())
    if source_hash:
        input_hashes["literary_source_freeze"] = source_hash
    existing = state["stages"][stage]
    prompt_hash = stage_prompt_hash(stage)
    fingerprint = sha(json.dumps({"stage": stage, "contract": state["contract_sha256"], "dependencies": input_hashes, "prompt_sha256": prompt_hash, "workflow_template_sha256": state["workflow_template_sha256"], "provider_config_sha256": state["provider_config_sha256"], "cost_guard_runner_sha256": state["cost_guard_runner_sha256"]}, sort_keys=True).encode())
    if existing.get("fingerprint") == fingerprint and existing["status"] in _MATERIALIZED | {"READY_FOR_EXECUTION"}:
        return {"status": "STAGE_REUSED", "run_id": args.run_id, "stage": stage, "fingerprint": fingerprint, "provider_call": "none"}
    if existing["status"] not in ("NOT_RUN", "INVALIDATED"):
        start = CNW_STAGES.index(stage)
        invalidated_stages = set(CNW_STAGES[start:])
        for downstream in CNW_STAGES[start:]:
            record = state["stages"][downstream]
            if record["status"] not in {"NOT_RUN", "INVALIDATED"}:
                record.setdefault("invalidated_attempts", []).append({key: value for key, value in record.items() if key != "invalidated_attempts"})
                record["status"] = "INVALIDATED"
                record.pop("fingerprint", None)
        retained_receipts = []
        for receipt in state.get("provider_requests", []):
            if receipt.get("stage") in invalidated_stages:
                state.setdefault("provider_attempts", []).append({"stage": receipt.get("stage"), "status": "INVALIDATED_AFTER_INPUT_CHANGE", "prior_receipt": receipt, "invalidated_at": now()})
            else:
                retained_receipts.append(receipt)
        state["provider_requests"] = retained_receipts
    if state.get("mode") == "live" and not state.get("fixture_only"):
        state["stages"][stage]["fingerprint"] = fingerprint
        state["stages"][stage]["input_hashes"] = input_hashes
        if expected_role_ids is not None:
            state["stages"][stage]["expected_role_ids"] = expected_role_ids
        state["updated_at"] = now()
        save_state(path, state)
        execute_cnw_stage(path, stage)
        fresh = load_state(path)
        return {"status": "STAGE_MATERIALIZED", "run_id": fresh["run_id"], "stage": stage, "fingerprint": fingerprint, "provider_call": "performed"}
    artifact_rel = f"artifacts/{stage}.{fingerprint[:12]}.json"
    artifact_path = assert_output_within_root(path, artifact_rel)
    artifact = {"schema_version": "cnw_stage_request_v1", "run_id": args.run_id, "work_id": state["work_id"], "stage": stage, "contract_sha256": state["contract_sha256"], "prompt_sha256": prompt_hash, "input_hashes": input_hashes, "fingerprint": fingerprint, "status": "READY_FOR_EXECUTION", "provider_call": "not_performed_by_W05_runner"}
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    attempts = existing.get("invalidated_attempts", [])
    state["stages"][stage] = {"status": "READY_FOR_EXECUTION", "fingerprint": fingerprint, "prompt_sha256": prompt_hash, "input_hashes": input_hashes, "artifact": {"path": artifact_rel, "sha256": sha(artifact_path.read_bytes())}, "updated_at": now(), "invalidated_attempts": attempts}
    if expected_role_ids is not None:
        state["stages"][stage]["expected_role_ids"] = expected_role_ids
    state["status"] = "RUNNING"
    state["updated_at"] = now()
    save_state(path, state)
    return {"status": "READY_FOR_EXECUTION", "run_id": args.run_id, "stage": stage, "artifact": artifact_rel, "fingerprint": fingerprint, "provider_call": "none"}


def mark_stage(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    with locked_run(path, lock_name="execution.lock"), locked_run(path):
        return _mark_stage_locked(args, path)


def _mark_stage_locked(args, path: Path) -> dict:
    state = load_state(path)
    stage = normalize_stage(args.stage)
    record = state["stages"][stage]
    if record["status"] != "READY_FOR_EXECUTION":
        raise ContractError("STAGE_NOT_READY", stage)
    if args.accept_fixture is None:
        raise ContractError("STAGE_EXECUTOR_NOT_IMPLEMENTED", "offline requests; no provider or fixture execution is implicit")
    fixture = safe_run_input(args.accept_fixture, path)
    record["status"] = "ACCEPTED"
    record["fixture_only"] = True
    record["request_artifact"] = record.get("artifact")
    record["artifact"] = {"path": fixture.relative_to(path).as_posix(), "sha256": sha(fixture.read_bytes())}
    state["updated_at"] = now()
    state["status"] = "RUNNING"
    save_state(path, state)
    return {"status": "FIXTURE_STAGE_ACCEPTED", "run_id": args.run_id, "stage": stage, "provider_call": "none"}


# --------------------------------------------------------------------------
# Live stage execution
# --------------------------------------------------------------------------
def _run_dir_base(run_dir: Path) -> Path:
    return run_dir.parent.parent


def _contract_for(run_dir: Path) -> dict:
    return load_contract(run_dir / "artifacts/contract.json")


def _write_project_output(project_root: Path, relative: str, content: str) -> Path:
    target = (project_root / relative).resolve()
    if not target.is_relative_to(project_root.resolve()):
        raise ContractError("PROJECT_OUTPUT_OUTSIDE_PROJECT", relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")
    return target


def _persist_stage(run_dir: Path, stage: str, relative: str, text: str, *, receipt_ids: list[str] | None = None, validation: dict | None = None, role_id: str | None = None, extra: dict | None = None) -> dict:
    target = assert_output_within_root(run_dir, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text if isinstance(text, str) else json.dumps(text, ensure_ascii=False, indent=2), encoding="utf-8")
    with locked_run(run_dir):
        state = load_state(run_dir)
        record = state["stages"][stage]
        record["status"] = "STAGE_MATERIALIZED"
        record["artifact"] = {"path": relative, "sha256": sha(target.read_bytes())}
        record["role_ids"] = ([role_id] if role_id else record.get("role_ids", []))
        if receipt_ids:
            record.setdefault("provider_request_ids", []).extend(receipt_ids)
        if validation is not None:
            record["validation"] = validation
        if extra:
            record.update(extra)
        state["next_stage"] = _next_stage(state)
        state["updated_at"] = now()
        state["status"] = "RUNNING"
        save_state(run_dir, state)
    return {"path": relative, "sha256": sha(target.read_bytes())}


def _next_stage(state: dict) -> str | None:
    return next((stage for stage in CNW_STAGES if state["stages"][stage]["status"] not in _MATERIALIZED), None)


def _read_stage_text(run_dir: Path, state: dict, stage: str) -> str:
    record = state["stages"][stage]
    path = assert_output_within_root(run_dir, record["artifact"]["path"])
    if sha(path.read_bytes()) != record["artifact"]["sha256"]:
        raise ContractError("STAGE_ARTIFACT_HASH_MISMATCH", stage)
    return path.read_text(encoding="utf-8-sig")


def _project_relative(run_dir: Path, contract: dict, name: str) -> str:
    work_id = contract["unit"]["id"]
    return name.replace("<work_id>", work_id)


def _role_sources(role: str, run_dir: Path, state: dict, contract: dict, project_root: Path) -> dict[str, str]:
    """Author reading list for a live role, resolved to actual file text."""
    try:
        from .cnw_roles import read_actual_texts
    except ImportError:
        from cnw_roles import read_actual_texts
    return read_actual_texts(project_root, role, contract["unit"]["id"], arc_ref=contract["story"].get("arc_ref"))


def _author_messages(role: str, contract: dict, materials: dict[str, str], extra: dict | None = None) -> list[dict]:
    try:
        from .cnw_roles import build_author_role_messages
    except ImportError:
        from cnw_roles import build_author_role_messages
    return build_author_role_messages(role, contract, materials, extra=extra)


def _validate_role(role: str, contract: dict, content: str, meta: dict) -> None:
    try:
        from .cnw_roles import validate_role_output
    except ImportError:
        from cnw_roles import validate_role_output
    validate_role_output(role, contract, content, meta)


def _role_meta(role: str, contract: dict) -> dict:
    try:
        from .cnw_roles import role_metadata
    except ImportError:
        from cnw_roles import role_metadata
    return role_metadata(role, contract)


def execute_cnw_stage(run_dir: Path, stage: str) -> dict:
    with locked_run(run_dir, lock_name="execution.lock"):
        return _execute_cnw_stage_locked(run_dir, stage)


def _execute_cnw_stage_locked(run_dir: Path, stage: str) -> dict:
    stage = normalize_stage(stage)
    state = load_state(run_dir)
    if state.get("mode") == "live" and not state.get("fixture_only"):
        try:
            from .cnw_recovery import execute_checked
        except ImportError:
            from cnw_recovery import execute_checked
        return execute_checked(run_dir, stage)
    return _dispatch_cnw_stage(run_dir, stage)


def _dispatch_cnw_stage(run_dir: Path, stage: str) -> dict:
    if stage == "plot":
        return execute_plot(run_dir)
    if stage == "scene_cards":
        return execute_scene_cards(run_dir)
    if stage == "writing_brief":
        return execute_writing_brief(run_dir)
    if stage == "prose":
        return execute_prose(run_dir)
    if stage in LOCAL_STAGES:
        return execute_lint(run_dir, stage)
    if stage == "multi_lens_review":
        return execute_five_lenses(run_dir)
    if stage == "adversarial_verify":
        return execute_three_verifiers(run_dir)
    if stage == "completeness_critic":
        return execute_completeness(run_dir)
    if stage == "refine":
        return execute_refine(run_dir)
    if stage == "re_review":
        return execute_re_review(run_dir)
    raise ContractError("UNKNOWN_STAGE", stage)


def _planning_stage(run_dir: Path, role: str, stage: str, output_name: str, output_cap: int, *, extra=None, project_dir: str | None, role_id: str) -> dict:
    state = load_state(run_dir)
    contract = _contract_for(run_dir)
    project_root = _run_dir_base(run_dir)
    materials = _role_sources(role, run_dir, state, contract, project_root)
    messages = _author_messages(role, contract, materials, extra)
    meta = _role_meta(role, contract)
    content, receipt = cnw_live_call(run_dir, stage=stage, role_id=role_id, messages=messages, output_cap=output_cap)
    _validate_role(role, contract, content, meta)
    if role == "plot" and contract["unit"].get("planning_mode") == "author_plot":
        try:
            from .cnw_roles import plot_structure
        except ImportError:
            from cnw_roles import plot_structure
        meta["plot_structure"] = plot_structure(content, contract)
    if project_dir:
        _write_project_output(project_root, project_dir.replace("<work_id>", contract["unit"]["id"]), content)
    _persist_stage(run_dir, stage, output_name, content, receipt_ids=[receipt["request_id"]], role_id=role_id)
    meta_rel = f"artifacts/{stage}.meta.json"
    meta_path = run_dir / meta_rel
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with locked_run(run_dir):
        s = load_state(run_dir)
        s["stages"][stage]["meta"] = {"path": meta_rel, "sha256": sha(meta_path.read_bytes())}
        save_state(run_dir, s)
    return {"stage": stage, "receipt": receipt["request_id"], "provider_request_id": receipt["provider_request_id"]}


def execute_plot(run_dir: Path) -> dict:
    try:
        from .cnw_roles import read_production_preparation
    except ImportError:
        from cnw_roles import read_production_preparation
    contract = _contract_for(run_dir)
    preparation = read_production_preparation(_run_dir_base(run_dir), contract)
    if contract["unit"]["kind"] == "scene":
        source = _source_root(contract, _run_dir_base(run_dir)) / contract["story"]["source_file"]
        lines = source.read_text(encoding="utf-8-sig").splitlines()
        anchor = contract["story"]["before_anchor"]
        preparation["preceding_source_text"] = "\n".join(lines[anchor["source_line"]-1:anchor.get("source_line_end", anchor["source_line"])])
    context_path = run_dir / "artifacts/production_preparation.json"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text(json.dumps(preparation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with locked_run(run_dir):
        current = load_state(run_dir)
        current["production_preparation"] = {"path": "artifacts/production_preparation.json", "sha256": sha(context_path.read_bytes())}
        save_state(run_dir, current)
    result = _planning_stage(run_dir, "plot", "plot", "artifacts/plot.md", 4000,
                            extra={"production_preparation": preparation}, project_dir="06_plot/<work_id>_plot.md", role_id="plot_agent")
    _critics_hook(run_dir, "plot")  # user-authorized supplement, not a CNW completion gate
    return result


def execute_scene_cards(run_dir: Path) -> dict:
    return _planning_stage(run_dir, "cards", "scene_cards", "artifacts/scene_cards.md", 4000, project_dir="05_scene_cards/<work_id>_scene_cards.md", role_id="scene_card_agent")


def _nk_pov(run_dir: Path, state: dict, contract: dict) -> dict:
    """Run the pinned local NK service for the accepted Scene Cards before the Brief."""
    try:
        from .cnw_nk_adapter import build_nk_payload, map_reflection_to_brief
    except ImportError:
        from cnw_nk_adapter import build_nk_payload, map_reflection_to_brief
    project_root = _run_dir_base(run_dir)
    cards_text = _read_stage_text(run_dir, state, "scene_cards")
    payload = build_nk_payload(contract, cards_text, _role_meta("cards", contract))
    existing = state.get("support_hooks", {}).get("nk_pov", {})
    receipt = next((item for item in state.get("provider_requests", [])
                    if item.get("request_id") == existing.get("request_id")
                    and item.get("role_id") == "nk_pov" and item.get("status") == "SUCCEEDED"), None)
    payload_hash = sha(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    if existing.get("status") == "MATERIALIZED" and receipt and receipt.get("input_sha256") == payload_hash:
        artifact = existing["artifact"]
        reflection = assert_output_within_root(run_dir, artifact["path"])
        if sha(reflection.read_bytes()) != artifact["sha256"]:
            raise ContractError("NK_REFLECTION_HASH_MISMATCH", receipt["request_id"])
        _receipt_content(run_dir, receipt)
        return {"path": artifact["path"], "mapping": existing["mapping"], "provider_call": "reused"}
    nk_result = _invoke_nk_service(run_dir, payload)
    reflection_response = nk_result["response"]
    receipt = nk_result["receipt"]
    mapped, mapping = map_reflection_to_brief("", reflection_response, {
        "status": "LIVE_ACCEPTED", "request_id": receipt["request_id"], "provider_request_id": receipt["provider_request_id"],
        "model": receipt["model"], "finish_reason": receipt["finish_reason"], "usage": receipt["usage"],
        "http_status": receipt["http_status"], "validated_response_sha256": sha(json.dumps(reflection_response, ensure_ascii=False, sort_keys=True).encode("utf-8")),
        "raw_response_sha256": receipt["raw_response_sha256"]})
    path = run_dir / "artifacts/support/nk-reflection.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(mapped, encoding="utf-8")
    with locked_run(run_dir):
        s = load_state(run_dir)
        s.setdefault("support_hooks", {})["nk_pov"] = {"status": "MATERIALIZED", "artifact": {"path": "artifacts/support/nk-reflection.md", "sha256": sha(path.read_bytes())}, "request_id": receipt["request_id"], "provider_request_id": receipt["provider_request_id"], "mapping": mapping}
        provider = s.get("provider_requests", [])
        if not any(row.get("request_id") == receipt["request_id"] for row in provider):
            provider.append(receipt)
        s["provider_requests"] = provider
        save_state(run_dir, s)
    return {"path": "artifacts/support/nk-reflection.md", "mapping": mapping}


def _invoke_nk_service(run_dir: Path, payload: dict) -> dict:
    import socket
    import shutil
    import subprocess
    index = json.loads((ROOT / "patches/nk/PATCH_INDEX.json").read_text(encoding="utf-8"))
    build = ROOT / "runtime/patched/NK" / index["runtime_build_id"]
    if not (build / "node_modules").is_dir():
        raise ContractError("NK_BUILD_MISSING", str(build))
    node = shutil.which("node")
    next_cli = build / "node_modules/next/dist/bin/next"
    if not node or not next_cli.is_file():
        raise ContractError("NK_LAUNCHER_MISSING", str(build))
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise ContractError("DEEPSEEK_API_KEY_REQUIRED", "nk")
    guard = _p2_guard()
    request_id = f"nk-{run_dir.name}-{uuid.uuid4().hex}"
    reservation = guard.command_reserve(argparse.Namespace(request_id=request_id, run_id=run_dir.name,
        purpose="P3.1 NK generate-perspective", input_token_cap=10000, output_token_cap=1024), emit=False)
    if reservation.get("status") != "RESERVED":
        raise ContractError("NK_COST_RESERVATION_FAILED", request_id)
    capture = run_dir / f"nk-provider-{request_id}.jsonl"
    env = dict(os.environ)
    env["DEEPSEEK_API_KEY"] = key
    env["STORYSTUDIO_NK_LIVE_CAPTURE"] = str(capture).replace("\\", "/")
    env["STORYSTUDIO_NK_LIVE_REQUEST_ID"] = request_id
    env["NODE_OPTIONS"] = f"--require={(ROOT / 'tools/nk-live-fetch.cjs').as_posix()}"
    # A fixed port can reach a previous run's server and capture under its ID.
    # Launch Next directly so the PID we terminate is the actual server.
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    command = [node, str(next_cli), "start", "--hostname", "127.0.0.1", "--port", str(port)]
    manifest = {"request_id": request_id, "port": port, "command": command,
                "runtime_build_id": index["runtime_build_id"], "status": "STARTING"}
    service_path = run_dir / f"nk-service-{request_id}.json"
    request_path = run_dir / "artifacts/provider" / f"{request_id}.request.json"
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    server = None
    failure = None
    try:
        server = subprocess.Popen(command, cwd=str(build), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
        manifest["pid"] = server.pid
        service_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        ready = False
        for _ in range(120):
            if server.poll() is not None:
                raise ContractError("NK_SERVER_EXITED", request_id)
            try:
                httpx.get(f"http://127.0.0.1:{port}/", timeout=1.0)
                if server.poll() is not None:
                    raise ContractError("NK_SERVER_EXITED", request_id)
                ready = True
                break
            except ContractError:
                raise
            except Exception:
                time.sleep(0.5)
        if not ready:
            raise ContractError("NK_SERVER_NOT_READY", str(port))
        response = httpx.post(f"http://127.0.0.1:{port}/api/generate-perspective", json=payload, timeout=180.0)
        http_status = int(response.status_code)
        body = response.json()
    except Exception as exc:
        failure = exc
    finally:
        if server is not None:
            try:
                if server.poll() is None:
                    server.terminate()
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)
        manifest["status"] = "STOPPED" if server is None or server.poll() is not None else "STOP_FAILED"
        service_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    record = None
    if capture.is_file():
        try:
            records = [json.loads(line) for line in capture.read_text(encoding="utf-8").splitlines() if line.strip()]
            if len(records) == 1 and records[0].get("request_id") == request_id:
                record = records[0]
        except (ValueError, TypeError):
            pass
    if record is None:
        guard.command_settle(argparse.Namespace(request_id=request_id, provider_request_id=None,
            returned_model=None, finish_reason=None, input_tokens=None, output_tokens=None), emit=False)
        if failure is not None:
            raise failure
        raise ContractError("NK_PROVIDER_CAPTURE_MISSING_OR_INVALID", request_id)
    provider_response = record.get("response", {})
    usage = provider_response.get("usage", {})
    settlement = guard.command_settle(argparse.Namespace(request_id=request_id,
        provider_request_id=provider_response.get("id"), returned_model=provider_response.get("model"),
        finish_reason=((provider_response.get("choices") or [{}])[0]).get("finish_reason"),
        input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens")), emit=False)
    if settlement.get("status") != "SETTLED":
        raise ContractError("NK_COST_SETTLEMENT_FAILED", request_id)
    if failure is not None:
        raise failure
    if http_status != 200 or not isinstance(body.get("perspectives"), list) or len(body["perspectives"]) != 1 or not body["perspectives"][0].get("reflection"):
        raise ContractError("NK_RESULT_INVALID", request_id)
    raw_path = run_dir / "artifacts/provider" / f"{request_id}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps({"request_id": request_id, "status": http_status, "requested_model": MODEL, "response": _sanitize(provider_response)}, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    _, pricing = guard.load_config()
    cost = guard.estimate(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), pricing)
    nk_content = (((provider_response.get("choices") or [{}])[0].get("message")) or {}).get("content") or ""
    receipt = {"stage": "support_hook", "role_id": "nk_pov", "request_id": request_id, "provider_request_id": provider_response.get("id"),
        "model": provider_response.get("model"), "status": "SUCCEEDED", "http_status": http_status,
        "finish_reason": ((provider_response.get("choices") or [{}])[0]).get("finish_reason"),
        "usage": {"prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens")},
        "input_sha256": sha(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")),
        "request_path": request_path.relative_to(run_dir).as_posix(), "request_sha256": sha(request_path.read_bytes()),
        "request_format": "native_nk_payload",
        "output_sha256": sha(nk_content.encode("utf-8")),
        "raw_response_path": raw_path.relative_to(run_dir).as_posix(), "raw_response_sha256": sha(raw_path.read_bytes()),
        "cost_cny": float(cost.quantize(Decimal("0.000001"), rounding=ROUND_CEILING)),
        "ledger_settlement": settlement,
        "mode": "LIVE", "fixture_only": False}
    return {"response": body, "receipt": receipt}


def execute_writing_brief(run_dir: Path) -> dict:
    state = load_state(run_dir)
    contract = _contract_for(run_dir)
    nk = _nk_pov(run_dir, state, contract)
    state = load_state(run_dir)
    project_root = _run_dir_base(run_dir)
    materials = _role_sources("brief", run_dir, state, contract, project_root)
    extra = {"nk_perspective_reflection_support_only": (run_dir / nk["path"]).read_text(encoding="utf-8")}
    messages = _author_messages("brief", contract, materials, extra)
    content, receipt = cnw_live_call(run_dir, stage="writing_brief", role_id="brief_agent", messages=messages, output_cap=4000)
    meta = _role_meta("brief", contract)
    _validate_role("brief", contract, content, meta)
    _write_project_output(project_root, f"07_draft/{contract['unit']['id']}_writing_brief.md", content)
    _persist_stage(run_dir, "writing_brief", "artifacts/writing_brief.md", content, receipt_ids=[receipt["request_id"]], role_id="brief_agent")
    return {"stage": "writing_brief", "nk_request": nk["mapping"].get("provider_request_id"), "receipt": receipt["request_id"]}


def execute_prose(run_dir: Path) -> dict:
    state = load_state(run_dir)
    contract = _contract_for(run_dir)
    project_root = _run_dir_base(run_dir)
    materials = _role_sources("prose", run_dir, state, contract, project_root)
    base_messages = _author_messages("prose", contract, materials)
    output_cap = max(4096, math.ceil(contract["unit"]["max_visible_chars"] * 1.2) + 512)
    try:
        from .cnw_contract import validate_output_length, count_visible_chars
    except ImportError:
        from cnw_contract import validate_output_length, count_visible_chars

    def strip_envelope(text: str) -> str:
        if text.lstrip().startswith("{"):
            try:
                parsed = json.loads(text)
                return parsed.get("prose", text)
            except json.JSONDecodeError:
                return text
        return text

    parts: list[str] = []
    receipt_ids: list[str] = []
    validation = None
    # At most an initial write plus two bounded continuation attempts.
    for attempt in range(3):
        if attempt == 0:
            messages = base_messages
        else:
            already = "\n".join(parts)
            remaining = contract["unit"]["min_visible_chars"] - count_visible_chars(already)
            messages = [
                {"role": "system", "content": (
                    "你是在续写同一场中文正文。只输出接续上一段末尾的新内容，不得重复、不得概述前文、不得使用标题或说明。"
                    "继续把 Writing Brief 中尚未落位的必需动作、回应、对白与停顿实际写成戏，直到整场完整且达到合同可见字数。"
                )},
                {"role": "user", "content": json.dumps({
                    "brief": base_messages[1]["content"],
                    "already_written_tail": already[-1500:],
                    "still_needed_visible_chars": max(remaining, 0),
                    "instruction": "只续写，不重复。",
                }, ensure_ascii=False, sort_keys=True)},
            ]
        content, receipt = cnw_live_call(run_dir, stage="prose", role_id=f"prose_agent_{attempt + 1}", messages=messages, output_cap=output_cap)
        receipt_ids.append(receipt["request_id"])
        parts.append(strip_envelope(content).strip())
        merged = "\n\n".join(part for part in parts if part)
        if count_visible_chars(merged) >= contract["unit"]["min_visible_chars"]:
            validation = validate_output_length(contract, merged)
            parts = [merged]
            break
    content = "\n\n".join(part for part in parts if part)
    if validation is None:
        try:
            validation = validate_output_length(contract, content)
        except ContractError as exc:
            raise ContractError("PROSE_UNDERPRODUCED", f"{exc}; actual={count_visible_chars(content)}") from exc
    _persist_stage(run_dir, "prose", "artifacts/prose.v0.md", content, receipt_ids=receipt_ids, role_id="prose_agent", validation={"actual_visible_chars": count_visible_chars(content)})
    return {"stage": "prose", "receipts": receipt_ids, "visible_chars": count_visible_chars(content)}


def execute_lint(run_dir: Path, stage: str) -> dict:
    state = load_state(run_dir)
    text = _read_stage_text(run_dir, state, "prose")
    try:
        from .cnw_lint import lint
    except ImportError:
        from cnw_lint import lint
    layer = "surface" if stage == "lint_layer1" else "structural"
    report = lint(text, layer, _run_dir_base(run_dir) / "92_style_engine/forbidden_patterns.md")
    report["stage"] = stage
    report["role"] = "local_deterministic_runner"
    rel = f"artifacts/{stage}.json"
    _persist_stage(run_dir, stage, rel, json.dumps(report, ensure_ascii=False, indent=2), validation={"status": report["status"], "source_sha256": report["source_sha256"], "findings": len(report["findings"]), "executable_rule_count": report["executable_rule_count"]})
    return {"stage": stage, "findings": len(report["findings"]), "provider_call": "none"}


def _review_sources(run_dir: Path, state: dict, contract: dict, project_root: Path) -> dict[str, str]:
    sources = {
        "style_guide": (project_root / "92_style_engine/style_guide.md").read_text(encoding="utf-8-sig"),
        "forbidden_patterns": (project_root / "92_style_engine/forbidden_patterns.md").read_text(encoding="utf-8-sig"),
        "character_bible": (project_root / "90_canon/character_bible.md").read_text(encoding="utf-8-sig"),
        "voice_samples": (project_root / "92_style_engine/character_voice_samples.md").read_text(encoding="utf-8-sig"),
        "glossary": (project_root / "90_canon/glossary.md").read_text(encoding="utf-8-sig"),
        "timeline": (project_root / "90_canon/timeline.md").read_text(encoding="utf-8-sig"),
        "world_bible": (project_root / "90_canon/world_bible.md").read_text(encoding="utf-8-sig"),
        "scene_cards": _read_stage_text(run_dir, state, "scene_cards"),
        "writing_brief": _read_stage_text(run_dir, state, "writing_brief"),
        "project_specific_canon": (project_root / "90_canon/canon.md").read_text(encoding="utf-8-sig"),
    }
    for lens_id in LENS_IDS:
        feedback = project_root / "08_review/lens_feedback" / f"{lens_id}.json"
        if feedback.is_file():
            updates = json.loads(feedback.read_text(encoding="utf-8"))
            sources[f"lens_feedback:{lens_id}"] = "\n".join(item["instruction"] for item in updates)
    return sources


def _parse_json_content(content: str, label: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text).strip()
    parsed = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # The model may wrap the required JSON object in a short explanation;
        # extract the outermost {...} span before failing.
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                parsed = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                parsed = None
    if not isinstance(parsed, dict):
        raise ContractError("LIVE_REVIEW_OUTPUT_NOT_JSON", label)
    return parsed


def _parallel_provider_calls(run_dir: Path, calls: list[dict]) -> list[tuple[str, dict]]:
    """Independent prompts fan out; the coordinator combines ordered results."""
    limit = load_state(run_dir).get("max_in_flight", 1)
    if type(limit) is not int or not 1 <= limit <= 5:
        raise ContractError("MAX_IN_FLIGHT_POLICY_MISMATCH", str(limit))
    if not calls:
        return []
    with ThreadPoolExecutor(max_workers=min(limit, len(calls))) as pool:
        futures = [pool.submit(cnw_live_call, run_dir, **call) for call in calls]
        try:
            return [future.result() for future in futures]
        except BaseException:
            for future in futures:
                future.cancel()
            # Context exit waits for requests already sent to settle and retain
            # their receipts. Retrying reuses those exact successful responses.
            raise


def execute_five_lenses(run_dir: Path) -> dict:
    state = load_state(run_dir)
    contract = _contract_for(run_dir)
    project_root = _run_dir_base(run_dir)
    draft = _read_stage_text(run_dir, state, "prose")
    sources = _review_sources(run_dir, state, contract, project_root)
    try:
        from .cnw_review import build_lens_input, lens_messages
    except ImportError:
        from cnw_review import build_lens_input, lens_messages
    artifacts = {}
    receipt_ids = []
    all_findings = []
    packets = {lens_id: build_lens_input(lens_id, draft, sources) for lens_id in LENS_IDS}
    results = _parallel_provider_calls(run_dir, [dict(stage="multi_lens_review", role_id=lens_id,
        messages=lens_messages(packets[lens_id]), output_cap=2500, extra={"lens_id": lens_id}) for lens_id in LENS_IDS])
    for lens_id, (content, receipt) in zip(LENS_IDS, results):
        packet = packets[lens_id]
        parsed = _parse_json_content(content, f"multi_lens_review:{lens_id}")
        if parsed.get("lens_id") != lens_id or not isinstance(parsed.get("findings"), list):
            raise ContractError("LIVE_LENS_OUTPUT_INVALID", lens_id)
        rel = f"artifacts/review/lens-{lens_id}.json"
        target = run_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"lens_id": lens_id, "input_sha256": packet["input_sha256"], "provider_request_id": receipt["provider_request_id"], "findings": parsed["findings"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        artifacts[lens_id] = {"path": rel, "sha256": sha(target.read_bytes())}
        receipt_ids.append(receipt["request_id"])
        for finding in parsed["findings"]:
            local_id = str(finding.get("finding_id", ""))
            all_findings.append({**finding, "lens_id": lens_id, "lens_finding_id": local_id, "finding_id": f"{lens_id}-{local_id}"})
    index_path = run_dir / "artifacts/multi_lens_review.index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps({"stage": "multi_lens_review", "lenses": artifacts, "findings": all_findings}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _persist_stage(run_dir, "multi_lens_review", "artifacts/multi_lens_review.index.json", index_path.read_text(encoding="utf-8"), receipt_ids=receipt_ids, role_id=None)
    return {"stage": "multi_lens_review", "lenses": len(artifacts), "findings": len(all_findings)}


def execute_three_verifiers(run_dir: Path) -> dict:
    state = load_state(run_dir)
    contract = _contract_for(run_dir)
    project_root = _run_dir_base(run_dir)
    draft = _read_stage_text(run_dir, state, "prose")
    lint2 = json.loads(_read_stage_text(run_dir, state, "lint_layer2"))
    lens_index = json.loads(_read_stage_text(run_dir, state, "multi_lens_review"))
    findings = list(lens_index.get("findings", []))
    for index, candidate in enumerate(lint2.get("findings", []), 1):
        findings.append({"finding_id": f"L2-{index}", "lens_id": "lint_layer2", "severity": "minor", "evidence": candidate.get("matched_text", ""), "issue": candidate.get("rule_id", ""), "recommendation": "人工复核该本地候选", "candidate_only": True})
    if not findings:
        report = {"stage": "adversarial_verify", "status": "NO_FINDINGS_TO_VERIFY", "receipts": [], "verdicts": {}}
        _persist_stage(run_dir, "adversarial_verify", "artifacts/adversarial_verify.json", json.dumps(report, ensure_ascii=False, indent=2))
        return {"stage": "adversarial_verify", "status": "NO_FINDINGS_TO_VERIFY", "provider_call": "none"}
    try:
        from .cnw_review import build_verifier_packet, verifier_messages
    except ImportError:
        from cnw_review import build_verifier_packet, verifier_messages
    sources = _review_sources(run_dir, state, contract, project_root)
    verdicts = {}
    receipt_ids = []
    rows = []
    for finding in findings:
        finding_id = finding.get("finding_id")
        if not finding_id:
            continue
        evidence = {name: sources[name] for name in ("scene_cards", "writing_brief", "character_bible", "timeline", "glossary")}
        votes = {}
        results = _parallel_provider_calls(run_dir, [dict(stage="adversarial_verify", role_id=verifier_id,
            messages=verifier_messages(build_verifier_packet(finding, verifier_id, draft, evidence)), output_cap=1200,
            extra={"finding_id": finding_id, "verifier_id": verifier_id}) for verifier_id in VERIFIER_IDS])
        for verifier_id, (content, receipt) in zip(VERIFIER_IDS, results):
            parsed = _parse_json_content(content, f"adversarial_verify:{finding_id}:{verifier_id}")
            if parsed.get("verifier_id") != verifier_id or not isinstance(parsed.get("votes"), list):
                raise ContractError("LIVE_VERIFIER_OUTPUT_INVALID", verifier_id)
            vote = next((row for row in parsed["votes"] if row.get("finding_id") == finding_id), None)
            if not vote or vote.get("verdict") not in {"not_refuted", "refuted", "uncertain"}:
                raise ContractError("LIVE_VERIFIER_VOTES_INVALID", f"{finding_id}:{verifier_id}")
            votes[verifier_id] = vote["verdict"]
            receipt_ids.append(receipt["request_id"])
            rows.append({"finding_id": finding_id, "verifier_id": verifier_id, "verdict": vote["verdict"], "provider_request_id": receipt["provider_request_id"], "request_id": receipt["request_id"]})
        verdicts[finding_id] = {"votes": votes, "status": "CONFIRMED" if sum(v == "not_refuted" for v in votes.values()) >= 2 else "REFUTED_OR_UNCERTAIN"}
    report = {"stage": "adversarial_verify", "status": "VERIFIED", "findings": findings, "verdicts": verdicts, "receipts": rows}
    _persist_stage(run_dir, "adversarial_verify", "artifacts/adversarial_verify.json", json.dumps(report, ensure_ascii=False, indent=2), receipt_ids=receipt_ids)
    return {"stage": "adversarial_verify", "findings": len(verdicts), "confirmed": sum(1 for v in verdicts.values() if v["status"] == "CONFIRMED")}


def execute_completeness(run_dir: Path) -> dict:
    state = load_state(run_dir)
    contract = _contract_for(run_dir)
    project_root = _run_dir_base(run_dir)
    draft = _read_stage_text(run_dir, state, "prose")
    verify = json.loads(_read_stage_text(run_dir, state, "adversarial_verify"))
    confirmed = [f for f in verify.get("findings", []) if verify.get("verdicts", {}).get(f.get("finding_id"), {}).get("status") == "CONFIRMED"]
    rejected = [f for f in verify.get("findings", []) if verify.get("verdicts", {}).get(f.get("finding_id"), {}).get("status") != "CONFIRMED"]
    sources = _review_sources(run_dir, state, contract, project_root)
    try:
        from .cnw_review import build_completeness_input, completeness_messages
    except ImportError:
        from cnw_review import build_completeness_input, completeness_messages
    packet = build_completeness_input(draft, confirmed, rejected, {"scene_cards": sources["scene_cards"], "writing_brief": sources["writing_brief"], "project_specific_canon": sources["project_specific_canon"]})
    content, receipt = cnw_live_call(run_dir, stage="completeness_critic", role_id="completeness", messages=completeness_messages(packet), output_cap=2500)
    parsed = _parse_json_content(content, "completeness_critic")
    if not isinstance(parsed.get("candidate_findings"), list):
        raise ContractError("LIVE_COMPLETENESS_OUTPUT_INVALID", "candidate_findings required")
    for finding in parsed["candidate_findings"]:
        if (not isinstance(finding, dict) or finding.get("lens_id") not in LENS_IDS
                or not isinstance(finding.get("prompt_update"), str) or not finding["prompt_update"].strip()):
            raise ContractError("LIVE_COMPLETENESS_OUTPUT_INVALID", "each omission needs a relevant lens and reusable prompt_update")
    feedback_dir = project_root / "08_review/lens_feedback"
    for finding in parsed["candidate_findings"]:
        feedback_dir.mkdir(parents=True, exist_ok=True)
        path = feedback_dir / f"{finding['lens_id']}.json"
        updates = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        instruction = finding["prompt_update"].strip()
        if not any(item["instruction"] == instruction for item in updates):
            updates.append({"instruction": instruction, "category": finding.get("category"),
                            "run_id": run_dir.name, "finding_id": finding.get("finding_id"),
                            "provider_request_id": receipt["provider_request_id"]})
            path.write_text(json.dumps(updates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    parsed["stage"] = "completeness_critic"
    parsed["confirmed_findings"] = [f.get("finding_id") for f in confirmed]
    parsed["rejected_findings"] = [f.get("finding_id") for f in rejected]
    _persist_stage(run_dir, "completeness_critic", "artifacts/completeness_critic.json", json.dumps(parsed, ensure_ascii=False, indent=2), receipt_ids=[receipt["request_id"]], role_id="completeness")
    return {"stage": "completeness_critic", "candidates": len(parsed["candidate_findings"])}


def _confirmed_findings(run_dir: Path, state: dict) -> list[dict]:
    verify = json.loads(_read_stage_text(run_dir, state, "adversarial_verify"))
    findings = verify.get("findings", [])
    verdicts = verify.get("verdicts", {})
    return [f for f in findings if verdicts.get(f.get("finding_id"), {}).get("status") == "CONFIRMED"]


def execute_refine(run_dir: Path) -> dict:
    state = load_state(run_dir)
    contract = _contract_for(run_dir)
    project_root = _run_dir_base(run_dir)
    previous_revision = state["stages"]["refine"]
    pending = previous_revision.get("pending_findings")
    v0 = _read_stage_text(run_dir, state, "refine" if pending else "prose")
    occupied = [int(match.group(1)) for path in (run_dir / "artifacts").glob("prose.v*.md")
                if (match := re.fullmatch(r"prose\.v(\d+)\.md", path.name))]
    occupied += [int(match.group(1)) for path in (run_dir / "artifacts/revisions").glob("revision-*.plan.json")
                 if (match := re.fullmatch(r"revision-(\d+)\.plan\.json", path.name))]
    revision_number = max(occupied, default=0) + 1
    completeness = json.loads(_read_stage_text(run_dir, state, "completeness_critic"))
    confirmed = pending if pending else _confirmed_findings(run_dir, state)
    candidates = [] if pending else list(completeness.get("candidate_findings", []))
    supplement = None
    if not pending:
        supplement = _critics_hook(run_dir, "prose")  # support hook, never an additional CNW stage
    if not confirmed and not candidates:
        plan = {"schema": 1, "status": "NO_CHANGE", "self_acceptance": False, "issues": []}
        _write_project_output(project_root, f"09_revision/{contract['unit']['id']}_revision_plan.json", json.dumps(plan, ensure_ascii=False, indent=2))
        _persist_stage(run_dir, "refine", f"artifacts/prose.v{revision_number}.md", v0,
            validation={"status": "NO_CHANGE", "v0_sha256": sha(v0.encode("utf-8"))},
            extra={"revision_number": revision_number, "affected_lenses": [], "pending_findings": [], "revision_base": None})
        return {"stage": "refine", "status": "NO_CHANGE"}
    feedback = {"confirmed": confirmed, "completeness_candidates": candidates}
    if supplement and supplement.get("status") == "SUCCEEDED":
        feedback["critics_supplement"] = supplement
    brief = _read_stage_text(run_dir, state, "writing_brief")
    input_identity = sha(json.dumps({"draft": v0, "feedback": feedback, "brief": brief, "contract": contract}, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    attempt = previous_revision.get("refinement_attempt")
    if attempt and attempt.get("input_identity") == input_identity:
        revision_number = attempt["revision_number"]
    else:
        with locked_run(run_dir):
            current = load_state(run_dir)
            current["stages"]["refine"]["refinement_attempt"] = {"input_identity": input_identity, "revision_number": revision_number}
            save_state(run_dir, current)
    affected = sorted({f.get("lens_id", f.get("owner")) for f in confirmed + candidates} & set(LENS_IDS))
    if any(f.get("lens_id", f.get("owner")) not in LENS_IDS for f in confirmed + candidates):
        affected = list(LENS_IDS)  # unknown historical provenance requires conservative coverage
    plan = {"schema": 2, "status": "READY_FOR_REFINE", "self_acceptance": False,
            "revision_number": revision_number, "draft_sha256": sha(v0.encode("utf-8")),
            "affected_lenses": affected, "issues": confirmed + candidates,
            "supplementary_sources": [supplement] if supplement else [],
            "supplement_policy": "CritiCS suggestions are unaccepted alternatives; use only to address listed CNW findings within Brief constraints. Reject new Canon, additional scenes and route changes."}
    plan_path = run_dir / f"artifacts/revisions/revision-{revision_number}.plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    system = (
        "你是 CNW Refine Agent。根据已确认 finding 与 Completeness 候选，修订整场中文正文，保留有效戏剧内容与所有必需节拍，"
        "不得删除必需动作、不得引入新 Canon、不得越过读者知识边界。只输出修订后的完整正文 Markdown，不要解释、不要评价、不要输出 JSON。"
        "CritiCS 补充结果只是尚未采纳的候选表达，不是 CNW 审稿结论；只可用于解决已列出的 finding。"
        "拒用其中增加场景、新秘密、路线变化或违背 Brief 的建议；不得把补充建议自动当成新事实。"
    )
    user = json.dumps({"v0": v0, "confirmed_findings": feedback, "brief_constraints": brief}, ensure_ascii=False, sort_keys=True)
    try:
        from .cnw_contract import count_visible_chars, validate_output_length
    except ImportError:
        from cnw_contract import count_visible_chars, validate_output_length
    base_messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    receipt_ids: list[str] = []
    content = ""
    for attempt in range(3):
        if attempt == 0:
            messages = base_messages
        else:
            messages = [
                {"role": "system", "content": (
                    "上一次修订删得过短。请在保留已采纳修改的前提下，把整场正文补回完整篇幅：恢复被删掉的必需动作、回应、对白与结尾，"
                    "不得新增 Canon、不得越过知识边界、不得使用标题或说明。只输出补全后的完整正文 Markdown。"
                )},
                {"role": "user", "content": json.dumps({"under_length_draft": content, "target_visible_chars": contract["unit"]["target_visible_chars"], "min_visible_chars": contract["unit"]["min_visible_chars"], "confirmed_findings": feedback}, ensure_ascii=False, sort_keys=True)},
            ]
        content, receipt = cnw_live_call(run_dir, stage="refine", role_id="refine", messages=messages, output_cap=4096, extra={"revision_number": revision_number})
        receipt_ids.append(receipt["request_id"])
        if count_visible_chars(content) >= contract["unit"]["min_visible_chars"]:
            break
    if count_visible_chars(content) < contract["unit"]["min_visible_chars"]:
        raise ContractError("REVISION_REGRESSION", f"v1 underproduced after bounded restoration: {count_visible_chars(content)}")
    validate_output_length(contract, content)
    diff = {"v0_sha256": sha(v0.encode("utf-8")), "v1_sha256": sha(content.encode("utf-8")), "v0_visible_chars": count_visible_chars(v0), "v1_visible_chars": count_visible_chars(content)}
    base_path = run_dir / f"artifacts/revisions/revision-{revision_number}.base.md"
    base_path.write_text(v0, encoding="utf-8")
    _persist_stage(run_dir, "refine", f"artifacts/prose.v{revision_number}.md", content, receipt_ids=receipt_ids, role_id="refine", validation=diff,
                   extra={"revision_number": revision_number, "affected_lenses": affected, "pending_findings": [], "refinement_attempt": None,
                          "revision_base": {"path": base_path.relative_to(run_dir).as_posix(), "sha256": sha(base_path.read_bytes())}})
    _write_project_output(project_root, f"09_revision/{run_dir.name}/{contract['unit']['id']}_v{revision_number}.md", content)
    return {"stage": "refine", "receipts": receipt_ids, "changed": diff["v0_sha256"] != diff["v1_sha256"], **diff}


def execute_re_review(run_dir: Path, *, remaining_passes: int = 3) -> dict:
    state = load_state(run_dir)
    if state["stages"]["refine"].get("pending_findings"):
        execute_refine(run_dir)
        state = load_state(run_dir)
    contract = _contract_for(run_dir)
    project_root = _run_dir_base(run_dir)
    v0 = _read_stage_text(run_dir, state, "prose")
    v1 = _read_stage_text(run_dir, state, "refine")
    revision = state["stages"]["refine"]
    revision_number = revision.get("revision_number", 1)
    if revision.get("revision_base"):
        base = revision["revision_base"]
        base_path = assert_output_within_root(run_dir, base["path"])
        if sha(base_path.read_bytes()) != base["sha256"]:
            raise ContractError("REVISION_BASE_CHANGED", base["path"])
        v0 = base_path.read_text(encoding="utf-8")
    if sha(v0.encode("utf-8")) == sha(v1.encode("utf-8")) and revision.get("validation", {}).get("status") == "NO_CHANGE":
        report = {"stage": "re_review", "status": "NO_CHANGED_TEXT", "receipts": [], "candidate_sha256": sha(v1.encode("utf-8"))}
        _persist_stage(run_dir, "re_review", "artifacts/re_review.json", json.dumps(report, ensure_ascii=False, indent=2))
        return {"stage": "re_review", "status": "NO_CHANGED_TEXT"}
    expected = state["stages"]["re_review"].get("expected_role_ids")
    affected = list(expected) if isinstance(expected, list) and expected else revision.get("affected_lenses", list(LENS_IDS))
    if len(set(affected)) != len(affected) or set(affected) - set(LENS_IDS):
        raise ContractError("LIVE_REREVIEW_CALL_SET_INVALID", str(affected))
    sources = _review_sources(run_dir, state, contract, project_root)
    try:
        from .cnw_review import build_lens_input, lens_messages, build_verifier_packet, verifier_messages
    except ImportError:
        from cnw_review import build_lens_input, lens_messages, build_verifier_packet, verifier_messages
    import difflib
    changed_hunks = "".join(difflib.unified_diff(v0.splitlines(keepends=True), v1.splitlines(keepends=True), fromfile="before", tofile="after", n=3))
    results = {}
    receipt_ids = []
    findings = []
    candidate_sha = sha(v1.encode("utf-8"))
    calls = []
    for lens_id in affected:
        packet = build_lens_input(lens_id, v1, sources)
        packet["changed_context"] = {"v0_sha256": sha(v0.encode("utf-8")), "v1_sha256": candidate_sha,
                                     "diff": changed_hunks, "instruction": "Review changed passages and their consequences in the full draft; do not reopen unchanged unrelated passages."}
        calls.append(dict(stage="re_review", role_id=lens_id, messages=lens_messages(packet), output_cap=2500,
                          extra={"lens_id": lens_id, "task_kind": "lens", "revision_number": revision_number, "candidate_sha256": candidate_sha}))
    for lens_id, (content, receipt) in zip(affected, _parallel_provider_calls(run_dir, calls)):
        parsed = _parse_json_content(content, f"re_review:{lens_id}")
        if parsed.get("lens_id") != lens_id or not isinstance(parsed.get("findings"), list):
            raise ContractError("LIVE_LENS_OUTPUT_INVALID", f"re_review:{lens_id}")
        results[lens_id] = {"findings": parsed.get("findings", []), "provider_request_id": receipt["provider_request_id"]}
        receipt_ids.append(receipt["request_id"])
        for index, finding in enumerate(parsed["findings"], 1):
            findings.append({**finding, "lens_id": lens_id, "finding_id": f"R{revision_number}-{lens_id}-{index}"})
    confirmed, dispositions = [], []
    for finding in findings:
        votes = []
        calls = [dict(stage="re_review", role_id=verifier_id,
            messages=verifier_messages(build_verifier_packet(finding, verifier_id, v1, sources)), output_cap=1200,
            extra={"task_kind": "verifier", "verifier_id": verifier_id, "finding_id": finding["finding_id"], "revision_number": revision_number, "candidate_sha256": candidate_sha}) for verifier_id in VERIFIER_IDS]
        for verifier_id, (content, receipt) in zip(VERIFIER_IDS, _parallel_provider_calls(run_dir, calls)):
            parsed = _parse_json_content(content, "re_review:verify")
            rows = parsed.get("votes", [])
            if (parsed.get("verifier_id") != verifier_id or len(rows) != 1
                    or rows[0].get("finding_id") != finding["finding_id"] or rows[0].get("verdict") not in {"not_refuted", "refuted", "uncertain"}):
                raise ContractError("LIVE_VERIFIER_VOTES_INVALID", finding["finding_id"])
            votes.append({**rows[0], "verifier_id": verifier_id, "request_id": receipt["request_id"], "provider_request_id": receipt["provider_request_id"]})
            receipt_ids.append(receipt["request_id"])
        survives = sum(vote["verdict"] == "not_refuted" for vote in votes) >= 2
        dispositions.append({"finding": finding, "votes": votes, "confirmed": survives})
        if survives:
            confirmed.append(finding)
    report = {"stage": "re_review", "status": "REVISION_REQUIRED" if confirmed else "CLEAN", "affected_lenses": affected, "lenses": results,
              "revision_number": revision_number, "candidate_sha256": candidate_sha, "dispositions": dispositions, "confirmed_findings": confirmed}
    archive = run_dir / f"artifacts/revisions/review-{revision_number}.json"
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if confirmed:
        with locked_run(run_dir):
            current = load_state(run_dir)
            current["stages"]["refine"]["pending_findings"] = confirmed
            current["stages"]["re_review"].update(status="REVISION_REQUIRED", artifact={"path": archive.relative_to(run_dir).as_posix(), "sha256": sha(archive.read_bytes())})
            current["status"] = "REVISION_REQUIRED"
            current["next_stage"] = "re_review"
            save_state(run_dir, current)
        if remaining_passes <= 1:
            raise ContractError("REREVIEW_REQUIRES_REVISION", "confirmed findings preserved for the next revision; no final acceptance")
        execute_refine(run_dir)
        return execute_re_review(run_dir, remaining_passes=remaining_passes - 1)
    _persist_stage(run_dir, "re_review", "artifacts/re_review.json", json.dumps(report, ensure_ascii=False, indent=2), receipt_ids=receipt_ids)
    return {"stage": "re_review", "lenses": len(results), "status": "CLEAN", "revision_number": revision_number}


def _critics_excerpt(run_dir: Path, state: dict) -> Path | None:
    """Select a short, source-referenced excerpt for CritiCS text-refine."""
    prose = _read_stage_text(run_dir, state, "prose")
    ranges = []
    findings = _confirmed_findings(run_dir, state)
    findings += json.loads(_read_stage_text(run_dir, state, "completeness_critic")).get("candidate_findings", [])
    for finding in findings:
        evidence = finding.get("evidence", "")
        if isinstance(evidence, str) and evidence.strip() and evidence in prose:
            start = prose.index(evidence)
            ranges.append((start, start + len(evidence)))
    selected = []
    total = 0
    for match in re.finditer(r'[^。！？.!?\n]+(?:[。！？.!?]+[”’"\']*|\n|$)', prose):
        if not any(match.start() < end and match.end() > start for start, end in ranges):
            continue
        # Complete source sentences only; bound unusually long unpunctuated input.
        if total + len(match[0]) > 1200:
            continue
        selected.append({"start": match.start(), "end": match.end(), "text": match[0]})
        total += len(match[0])
        if len(selected) == 5:
            break
    if not selected:
        return None
    excerpt = "\n".join(item["text"] for item in selected)
    target = run_dir / "artifacts/support/critics-excerpt.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(excerpt.rstrip() + "\n", encoding="utf-8")
    target.with_suffix(".sources.json").write_text(json.dumps({"prose_sha256": sha(prose.encode("utf-8")),
        "offset_unit": "decoded Unicode character index", "selected_sentences": selected,
        "excerpt_sha256": sha(target.read_bytes())}, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _critics_hook(run_dir: Path, stage: str) -> dict:
    """Attach the existing cost-guarded CritiCS bridge as a support hook."""
    import subprocess
    try:
        from .cnw_critics_adapter import read_native_result
    except ImportError:
        from cnw_critics_adapter import read_native_result
    action = "plan-critique" if stage == "plot" else "text-refine"
    hook_name = "critics_plot" if action == "plan-critique" else "critics_text"
    python = ROOT / "runtime/envs/critics-api/Scripts/python.exe"
    state = load_state(run_dir)
    previous = state.get("support_hooks", {}).get(hook_name, {})
    if previous.get("status") == "SUCCEEDED" and not previous.get("input_artifact"):
        try:
            from .cnw_recovery import support_input_snapshot
        except ImportError:
            from cnw_recovery import support_input_snapshot
        support_input_snapshot(run_dir, state, hook_name, previous)
    if stage == "plot":
        input_path = assert_output_within_root(run_dir, state["stages"]["plot"]["artifact"]["path"])
    else:
        # CritiCS text-refine only reviews the source-referenced key excerpt, not the whole scene.
        input_path = _critics_excerpt(run_dir, state)
        if input_path is None:
            evidence = {"status": "NO_RELEVANT_EXCERPT"}
            _record_hook(run_dir, hook_name, evidence)
            return evidence
    input_sha = sha(input_path.read_bytes())
    input_snapshot = run_dir / f"artifacts/support/critics-input-{input_sha}.md"
    input_snapshot.parent.mkdir(parents=True, exist_ok=True)
    if input_snapshot.exists() and sha(input_snapshot.read_bytes()) != input_sha:
        raise ContractError("CRITICS_INPUT_CHANGED", hook_name)
    input_snapshot.write_bytes(input_path.read_bytes())
    input_path = input_snapshot
    input_artifact = {"path": input_snapshot.relative_to(run_dir).as_posix(), "sha256": input_sha}
    if previous.get("status") == "SUCCEEDED" and previous.get("input_sha256") == input_sha:
        evidence = read_native_result(previous["run_name"], action=action, input_path=input_path)
        if previous.get("evidence_files") and previous["evidence_files"] != evidence["evidence_files"]:
            raise ContractError("CRITICS_EVIDENCE_CHANGED", previous["run_name"])
        evidence["input_artifact"] = input_artifact
        _record_hook(run_dir, hook_name, evidence)
        return evidence
    if not python.is_file():
        evidence = {"status": "CRITICS_ENV_MISSING"}
        _record_hook(run_dir, hook_name, evidence)
        return evidence
    run_name = f"{run_dir.name}-critics-{action}-{uuid.uuid4().hex[:8]}"
    command = [str(python), str(ROOT / "tools/p2_06_critics_run.py"), "--action", action, "--input", str(input_path), "--run-name", run_name, "--ledger-run-id", run_dir.name]
    try:
        completed = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    except Exception as exc:
        evidence = {"status": "CRITICS_INVOCATION_FAILED", "error": type(exc).__name__, "run_name": run_name}
        _record_hook(run_dir, hook_name, evidence)
        return evidence
    evidence = {"status": "SUCCEEDED" if completed.returncode == 0 else "FAILED", "action": action, "run_name": run_name, "returncode": completed.returncode, "input_sha256": input_sha}
    if completed.returncode != 0:
        evidence["stderr_tail"] = (completed.stderr or "")[-300:]
    else:
        evidence = read_native_result(run_name, action=action, input_path=input_path)
    evidence["input_artifact"] = input_artifact
    _record_hook(run_dir, hook_name, evidence)
    return evidence


def _record_hook(run_dir: Path, hook: str, evidence: dict) -> None:
    with locked_run(run_dir):
        state = load_state(run_dir)
        previous = state.get("support_hooks", {}).get(hook)
        if previous and previous != evidence:
            state.setdefault("support_hook_attempts", []).append({"hook": hook, "evidence": previous, "superseded_at": now()})
        state.setdefault("support_hooks", {})[hook] = evidence
        save_state(run_dir, state)


# --------------------------------------------------------------------------
# Views / verification
# --------------------------------------------------------------------------
def show_run(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    state = load_state(path)
    return {"status": state["status"], "run_id": state["run_id"], "work_id": state["work_id"], "contract_sha256": state["contract_sha256"], "stages": {key: value["status"] for key, value in state["stages"].items()}, "support_hooks": {k: v.get("status", v) if isinstance(v, dict) else v for k, v in state.get("support_hooks", {}).items()}, "provider_requests": len(state["provider_requests"])}


def resume_run(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    state = load_state(path)
    if state.get("mode") != "live" or state.get("fixture_only"):
        return {**show_run(args), "resume_execution": "OFFLINE_FIXTURE_REQUIRES_EXPLICIT_STEP", "provider_call": "none"}
    with locked_run(path, lock_name="execution.lock"):
        run_remaining_stages(path)
    return {**show_run(args), "resume_execution": "EXECUTED_WITH_IDENTITY_VALIDATION"}


def review_run(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    state = load_state(path)
    candidate = state.get("editorial_candidate")
    if not candidate:
        raise ContractError("EDITORIAL_CANDIDATE_NOT_READY", "stage request artifacts are not a prose candidate")
    target = assert_output_within_root(path, candidate.get("path", ""))
    if not target.is_file() or sha(target.read_bytes()) != candidate.get("sha256"):
        raise ContractError("EDITORIAL_CANDIDATE_HASH_MISMATCH", args.run_id)
    return {"status": "READY_FOR_EDITORIAL_REVIEW", "run_id": args.run_id, "candidate": candidate, "review_evidence": "external_controller_or_author_required", "self_acceptance": False, "promote_allowed": False}


def register_editorial_candidate(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    with locked_run(path, lock_name="execution.lock"), locked_run(path):
        state = load_state(path)
        if state.get("fixture_only") or state.get("mode") != "live":
            raise ContractError("MOCK_CANDIDATE_CANNOT_REQUEST_EDITORIAL_REVIEW", args.run_id)
        verify_live(args)
        target = safe_run_input(args.candidate, path)
        candidate = {"path": target.relative_to(path).as_posix(), "sha256": sha(target.read_bytes()), "status": "READY_FOR_EDITORIAL_REVIEW", "provider_evidence": "validated"}
        state["editorial_candidate"] = candidate
        state["status"] = "READY_FOR_EDITORIAL_REVIEW"
        state["updated_at"] = now()
        save_state(path, state)
        return {"status": "READY_FOR_EDITORIAL_REVIEW", "run_id": args.run_id, "candidate": candidate, "self_acceptance": False}


def invalidate_run(args) -> dict:
    """Reopen a stage and its downstream consumers without destroying prior receipts/artifacts."""
    path = run_path(args.run_id, runs_root_for(args))
    with locked_run(path, lock_name="execution.lock"), locked_run(path):
        state = load_state(path)
        start = CNW_STAGES.index(normalize_stage(args.from_stage))
        reopened = CNW_STAGES[start:]
        try:
            from .cnw_recovery import archive_stage, verify_evidence
        except ImportError:
            from cnw_recovery import archive_stage, verify_evidence
        verify_evidence(path, state)
        for stage in reopened:
            record = state["stages"][stage]
            if record.get("status") != "NOT_RUN" or record.get("artifact"):
                archive_stage(path, state, stage, "EXPLICIT_STAGE_REOPEN")
        state["next_stage"] = next((stage for stage in CNW_STAGES if state["stages"][stage]["status"] not in _MATERIALIZED), None)
        state["updated_at"] = now()
        save_state(path, state)
    return {"status": "STAGES_REOPENED", "run_id": args.run_id, "from_stage": normalize_stage(args.from_stage), "reopened": list(reopened), "provider_call": "none"}


def promote_run(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    state = load_state(path)
    if state["stages"].get("re_review", {}).get("status") not in _MATERIALIZED:
        raise ContractError("PROMOTION_GATE_NOT_ACCEPTED", "re_review")
    candidate_arg = getattr(args, "candidate", None)
    evidence_arg = getattr(args, "review_evidence", None)
    if not candidate_arg or not evidence_arg:
        raise ContractError("EXTERNAL_REVIEW_EVIDENCE_REQUIRED", "supply --candidate and --review-evidence under this run")
    if state.get("mode") != "live" or state.get("fixture_only"):
        raise ContractError("MOCK_CANDIDATE_CANNOT_PROMOTE", args.run_id)
    verify_live(args)
    candidate_value = Path(candidate_arg)
    evidence_value = Path(evidence_arg)
    candidate = safe_run_input(candidate_value if candidate_value.is_absolute() else path / candidate_value, path)
    evidence_path = safe_run_input(evidence_value if evidence_value.is_absolute() else path / evidence_value, path)
    project_root = Path(getattr(args, "project_root", None) or ROOT).resolve(strict=True)
    contract_path = (project_root / state["contract_path"]).resolve(strict=True)
    if not contract_path.is_relative_to(project_root) or contract_path.is_symlink():
        raise ContractError("CONTRACT_PATH_UNSAFE", state["contract_path"])
    contract = load_contract(contract_path)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    accepted_review = evidence.get("accepted_review")
    if not isinstance(accepted_review, dict):
        raise ContractError("ACCEPTED_REVIEW_EVIDENCE_REQUIRED", "promotion record must include the reviewed provider receipts")
    bind_accepted_review_outputs(accepted_review, state["provider_requests"], path)
    try:
        from .cnw_revision import promote_revision
    except ImportError:
        from cnw_revision import promote_revision
    result = promote_revision(project_root, path, candidate, contract, evidence)
    with locked_run(path):
        state = load_state(path)
        state["editorial_review"] = {**evidence, "evidence_sha256": sha(evidence_path.read_bytes()), "candidate_path": candidate.relative_to(path).as_posix()}
        state["stages"]["refine"]["promoted"] = True
        state["updated_at"] = now()
        state["status"] = "PROMOTED"
        save_state(path, state)
    return {**result, "run_id": args.run_id, "self_acceptance": False}


def export_run(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    state = load_state(path)
    try:
        from .cnw_export import export_reading_package
    except ImportError:
        from cnw_export import export_reading_package
    return export_reading_package(path, state, project_root=Path(getattr(args, "project_root", None) or ROOT))


def sprint_run(args) -> dict:
    try:
        from .cnw_sprint import run_fixture_sprint
    except ImportError:
        from cnw_sprint import run_fixture_sprint
    plan = getattr(args, "sprint_plan", None)
    if not plan:
        raise ContractError("SPRINT_QUEUE_REQUIRED", "supply --sprint-plan with five episode contracts")
    if getattr(args, "mode", "fixture") == "live":
        try:
            from .cnw_sprint_live import run_live_sprint
        except ImportError:
            from cnw_sprint_live import run_live_sprint
        return run_live_sprint(Path(getattr(args, "project_root", None) or ROOT), args.run_id, Path(plan))
    return run_fixture_sprint(Path(getattr(args, "project_root", None) or ROOT), args.run_id, Path(plan))


def verify_history(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    state = load_state(path)
    for record in state["stages"].values():
        artifacts = [record.get("artifact"), record.get("request_artifact"), *[attempt.get("artifact") for attempt in record.get("invalidated_attempts", [])], *[attempt.get("request_artifact") for attempt in record.get("invalidated_attempts", [])]]
        for artifact in artifacts:
            if not artifact:
                continue
            target = assert_output_within_root(path, artifact["path"])
            if not target.is_file() or sha(target.read_bytes()) != artifact["sha256"]:
                raise ContractError("RUN_ARTIFACT_HASH_MISMATCH", artifact["path"])
    return {"status": "HISTORICAL_EVIDENCE_FOUND", "run_id": args.run_id, "provider_call": "none", "provider_requests": len(state["provider_requests"])}


def verify_live(args) -> dict:
    run_root = run_path(args.run_id, runs_root_for(args))
    state = load_state(run_root)
    if not state["provider_requests"]:
        raise ContractError("LIVE_PROVIDER_EVIDENCE_MISSING", args.run_id)
    if any(receipt.get("mode") == "MOCK_ONLY" or receipt.get("fixture_only") is True for receipt in state["provider_requests"]):
        raise ContractError("MOCK_RECEIPT_CANNOT_PROVE_LIVE", args.run_id)
    for stage in CNW_STAGES:
        record = state["stages"].get(stage, {})
        if record.get("status") not in _MATERIALIZED:
            raise ContractError("LIVE_PIPELINE_INCOMPLETE", f"{stage}: {record.get('status')}")
        if stage in LOCAL_STAGES:
            if any(receipt.get("stage") == stage for receipt in state["provider_requests"]):
                raise ContractError("LIVE_LOCAL_STAGE_HAS_PROVIDER_CALL", stage)
            continue
        matching = [receipt for receipt in state["provider_requests"] if receipt.get("stage") == stage]
        if stage == "multi_lens_review":
            continue
        if stage == "adversarial_verify":
            continue
        if not matching and stage == "refine" and record.get("validation", {}).get("status") == "NO_CHANGE":
            if _read_stage_text(run_root, state, "prose") != _read_stage_text(run_root, state, "refine"):
                raise ContractError("LIVE_NO_CHANGE_MISMATCH", stage)
            continue
        if not matching and stage == "re_review":
            report = json.loads(_read_stage_text(run_root, state, "re_review"))
            if report.get("status") == "NO_CHANGED_TEXT" and state["stages"]["refine"].get("validation", {}).get("status") == "NO_CHANGE":
                continue
        if not matching:
            raise ContractError("LIVE_PIPELINE_INCOMPLETE", f"{stage}: provider receipt missing")
    project_root = _run_dir_base(run_root)
    validate_literary_source_freeze(state, project_root)
    # Five isolated Lens receipts. The role identity may be recorded as the
    # canonical `lens_id` field or the transport's `role_id`.
    lens_rows = [row for row in state["provider_requests"] if row.get("stage") == "multi_lens_review"]
    lens_identities = [row.get("lens_id") or row.get("role_id") for row in lens_rows]
    if len(lens_rows) != 5 or set(lens_identities) != set(LENS_IDS):
        raise ContractError("LIVE_REVIEW_CALL_SET_INCOMPLETE", f"lens ids {lens_identities}")
    # Actual findings from the materialized lens index + structural lint candidates.
    lens_index = json.loads(_read_stage_text(run_root, state, "multi_lens_review"))
    findings = lens_index.get("findings", [])
    lint2 = json.loads(_read_stage_text(run_root, state, "lint_layer2"))
    has_candidates = bool(findings) or bool(lint2.get("findings"))
    verifier_rows = [row for row in state["provider_requests"] if row.get("stage") == "adversarial_verify"]
    verify_artifact = json.loads(_read_stage_text(run_root, state, "adversarial_verify"))
    if not has_candidates:
        if verify_artifact.get("status") != "NO_FINDINGS_TO_VERIFY" or verifier_rows:
            raise ContractError("LIVE_REVIEW_CALL_SET_INCOMPLETE", "no findings must produce NO_FINDINGS_TO_VERIFY and no verifier receipts")
    else:
        finding_ids = {row.get("finding_id") for row in findings}
        for finding_id in finding_ids:
            names = {row.get("verifier_id") or row.get("role_id") for row in verifier_rows if row.get("finding_id") == finding_id}
            if names != set(VERIFIER_IDS):
                raise ContractError("LIVE_REVIEW_CALL_SET_INCOMPLETE", f"adversarial_verify {finding_id}: {sorted(str(n) for n in names)}")
    # Completeness receives the whole draft plus dispositions.
    completeness = json.loads(_read_stage_text(run_root, state, "completeness_critic"))
    if "candidate_findings" not in completeness:
        raise ContractError("LIVE_COMPLETENESS_OUTPUT_INVALID", "candidate_findings required")
    # Re-review receipts are distinct lens ids from the current revised draft.
    rereview_report = json.loads(_read_stage_text(run_root, state, "re_review"))
    final_sha = sha(_read_stage_text(run_root, state, "refine").encode("utf-8"))
    if rereview_report.get("candidate_sha256") != final_sha or rereview_report.get("status") not in {"CLEAN", "NO_CHANGED_TEXT"}:
        raise ContractError("LIVE_REREVIEW_NOT_CLEAN", "current candidate requires a clean, hash-bound re-review")
    if rereview_report.get("status") == "CLEAN":
        round_number = rereview_report.get("revision_number")
        round_rows = [row for row in state["provider_requests"] if row.get("stage") == "re_review" and row.get("revision_number") == round_number and row.get("candidate_sha256") == final_sha]
        rereview_ids = [row.get("lens_id") for row in round_rows if row.get("task_kind") == "lens"]
        if len(set(rereview_ids)) != len(rereview_ids) or set(rereview_ids) != set(rereview_report.get("affected_lenses", [])) or not rereview_ids:
            raise ContractError("LIVE_REREVIEW_CALL_SET_INVALID", str(rereview_ids))
        actual_findings = {}
        for row in round_rows:
            if row.get("task_kind") != "lens":
                continue
            lens_id = row["lens_id"]
            parsed = _parse_json_content(_receipt_content(run_root, row), "re_review:raw-lens")
            reported = rereview_report.get("lenses", {}).get(lens_id, {})
            if (parsed.get("lens_id") != lens_id or not isinstance(parsed.get("findings"), list)
                    or reported.get("findings") != parsed["findings"] or reported.get("provider_request_id") != row["provider_request_id"]):
                raise ContractError("LIVE_REREVIEW_OUTPUT_UNBOUND", lens_id)
            for number, finding in enumerate(parsed["findings"], 1):
                fid = f"R{round_number}-{lens_id}-{number}"
                actual_findings[fid] = {**finding, "lens_id": lens_id, "finding_id": fid}
        dispositions = rereview_report.get("dispositions", [])
        disposition_ids = [item.get("finding", {}).get("finding_id") for item in dispositions]
        if set(disposition_ids) != set(actual_findings) or len(disposition_ids) != len(actual_findings):
            raise ContractError("LIVE_REREVIEW_OUTPUT_UNBOUND", "finding dispositions differ from original Lens output")
        for disposition in rereview_report.get("dispositions", []):
            finding_id = disposition["finding"]["finding_id"]
            if disposition["finding"] != actual_findings[finding_id]:
                raise ContractError("LIVE_REREVIEW_OUTPUT_UNBOUND", finding_id)
            votes = disposition.get("votes", [])
            tasks = [row for row in round_rows if row.get("task_kind") == "verifier" and row.get("finding_id") == finding_id]
            if len(tasks) != 3 or {row.get("verifier_id") for row in tasks} != set(VERIFIER_IDS) or len(votes) != 3:
                raise ContractError("LIVE_REREVIEW_CALL_SET_INVALID", finding_id)
            if {v.get("provider_request_id") for v in votes} != {row["provider_request_id"] for row in tasks}:
                raise ContractError("LIVE_REREVIEW_CALL_SET_INVALID", finding_id)
            for task in tasks:
                raw_vote = _parse_json_content(_receipt_content(run_root, task), "re_review:raw-verifier")
                rows = raw_vote.get("votes", [])
                reported = next(v for v in votes if v["provider_request_id"] == task["provider_request_id"])
                if (raw_vote.get("verifier_id") != task["verifier_id"] or len(rows) != 1
                        or rows[0].get("finding_id") != finding_id or rows[0].get("verdict") != reported.get("verdict")
                        or reported.get("verifier_id") != task["verifier_id"]):
                    raise ContractError("LIVE_REREVIEW_OUTPUT_UNBOUND", finding_id)
            if sum(v.get("verdict") == "not_refuted" for v in votes) >= 2:
                raise ContractError("LIVE_REREVIEW_NOT_CLEAN", finding_id)
    # Each provider receipt is authenticated against its raw response and ledger.
    required = {"stage", "request_id", "provider_request_id", "model", "status", "http_status", "finish_reason", "usage", "input_sha256", "output_sha256", "raw_response_path", "raw_response_sha256", "cost_cny", "ledger_settlement"}
    ledger_path = ROOT / "runtime/private/p2-cost-ledger.json"
    if ledger_path.is_symlink() or not ledger_path.is_file():
        raise ContractError("LIVE_COST_LEDGER_MISSING", str(ledger_path))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    seen_provider_ids = set()
    seen_request_ids = set()
    for index, receipt in enumerate(state["provider_requests"], 1):
        if receipt.get("mode") == "MOCK_ONLY" or receipt.get("fixture_only") is True:
            raise ContractError("MOCK_RECEIPT_CANNOT_PROVE_LIVE", f"request {index}")
        missing = sorted(required - set(receipt))
        if missing:
            raise ContractError("LIVE_RECEIPT_INCOMPLETE", f"request {index} missing {', '.join(missing)}")
        if not all(isinstance(receipt.get(key), str) and receipt[key].strip() for key in ("stage", "request_id", "provider_request_id")):
            raise ContractError("LIVE_RECEIPT_IDENTITY_INVALID", f"request {index}")
        if receipt["provider_request_id"] in seen_provider_ids or receipt["request_id"] in seen_request_ids:
            raise ContractError("LIVE_PROVIDER_REQUEST_ID_DUPLICATE", receipt["provider_request_id"])
        seen_provider_ids.add(receipt["provider_request_id"])
        seen_request_ids.add(receipt["request_id"])
        if receipt["status"] != "SUCCEEDED" or receipt["http_status"] != 200 or receipt["model"] != MODEL or receipt["finish_reason"] != "stop":
            raise ContractError("LIVE_RECEIPT_STATUS_INVALID", f"request {index}")
        usage = receipt["usage"]
        if not isinstance(usage, dict) or not all(isinstance(usage.get(key), int) and usage[key] > 0 for key in ("prompt_tokens", "completion_tokens")):
            raise ContractError("LIVE_USAGE_MISSING", f"request {index}")
        if not all(re.fullmatch(r"[0-9a-fA-F]{64}", str(receipt[key])) for key in ("input_sha256", "output_sha256", "raw_response_sha256")):
            raise ContractError("LIVE_RECEIPT_HASH_INVALID", f"request {index}")
        raw_response = assert_output_within_root(run_root, receipt["raw_response_path"])
        if not raw_response.is_file() or sha(raw_response.read_bytes()) != receipt["raw_response_sha256"].lower():
            raise ContractError("LIVE_RAW_RESPONSE_HASH_MISMATCH", f"request {index}")
        _validate_raw_live_response(raw_response, receipt, usage, index)
        if not isinstance(receipt["cost_cny"], (int, float)) or isinstance(receipt["cost_cny"], bool) or not math.isfinite(receipt["cost_cny"]) or receipt["cost_cny"] < 0:
            raise ContractError("LIVE_COST_MISSING", f"request {index}")
        settlement = receipt["ledger_settlement"]
        if not isinstance(settlement, dict) or settlement.get("status") != "SETTLED" or settlement.get("request_id") != receipt["request_id"]:
            raise ContractError("LIVE_COST_NOT_SETTLED", f"request {index}")
        rows = [row for row in ledger.get("requests", []) if row.get("request_id") == receipt["request_id"]]
        if len(rows) != 1:
            raise ContractError("LIVE_COST_LEDGER_ROW_MISSING", receipt["request_id"])
        row = rows[0]
        usage_matches = row.get("usage") == {"input_tokens": usage["prompt_tokens"], "output_tokens": usage["completion_tokens"]}
        try:
            settled_cost = Decimal(str(row.get("estimated_actual_cny")))
            receipt_cost = Decimal(str(receipt["cost_cny"])).quantize(Decimal("0.000001"), rounding=ROUND_CEILING)
        except (InvalidOperation, ValueError):
            raise ContractError("LIVE_COST_MISSING", f"request {index}")
        if row.get("status") != "SETTLED" or row.get("provider_request_id") != receipt["provider_request_id"] or row.get("finish_reason") != "stop" or not usage_matches or settled_cost != receipt_cost:
            raise ContractError("LIVE_COST_SETTLEMENT_MISMATCH", f"request {index}")
    return {"status": "LIVE_EVIDENCE_VALIDATED", "run_id": args.run_id, "provider_requests": len(state["provider_requests"]), "all_receipts_settled": True}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("produce")
    create.add_argument("--unit", choices=("scene", "episode"))
    create.add_argument("--contract", required=True)
    create.add_argument("--work-id")
    create.add_argument("--run-id", required=True)
    create.add_argument("--mode", choices=("offline", "live"), required=True)
    create.add_argument("--project-root")
    create.add_argument("--create-only", action="store_true", help="create the live run state without executing stages")
    create.set_defaults(func=produce)
    run = sub.add_parser("step")
    run.add_argument("--run-id", required=True)
    run.add_argument("--work-id")
    run.add_argument("--stage", required=True)
    run.add_argument("--input")
    run.add_argument("--project-root")
    run.add_argument("--expected-role-ids", nargs="+")
    run.set_defaults(func=step)
    candidate = sub.add_parser("register-candidate")
    candidate.add_argument("--run-id", required=True)
    candidate.add_argument("--candidate", required=True)
    candidate.add_argument("--project-root")
    candidate.set_defaults(func=register_editorial_candidate)
    record = sub.add_parser("record-fixture")
    record.add_argument("--run-id", required=True)
    record.add_argument("--stage", required=True)
    record.add_argument("--accept-fixture", required=True)
    record.add_argument("--project-root")
    record.set_defaults(func=mark_stage)
    reopen = sub.add_parser("invalidate")
    reopen.add_argument("--run-id", required=True)
    reopen.add_argument("--from-stage", required=True)
    reopen.add_argument("--project-root")
    reopen.set_defaults(func=invalidate_run)
    references = sub.add_parser("refresh-references")
    references.add_argument("--run-id", required=True)
    references.add_argument("--project-root")
    references.add_argument("--reason", required=True)
    try:
        from .cnw_recovery import refresh_references
    except ImportError:
        from cnw_recovery import refresh_references
    references.set_defaults(func=refresh_references)
    for command, func in (("show-run", show_run), ("resume", resume_run), ("verify-history", verify_history), ("verify-live", verify_live)):
        item = sub.add_parser(command)
        item.add_argument("--run-id", required=True)
        item.add_argument("--project-root")
        item.set_defaults(func=func)
    for command, func in (("review", review_run), ("promote", promote_run), ("export", export_run), ("sprint", sprint_run)):
        item = sub.add_parser(command)
        item.add_argument("--run-id", required=True)
        item.add_argument("--project-root")
        if command == "promote":
            item.add_argument("--candidate")
            item.add_argument("--review-evidence")
        if command == "sprint":
            item.add_argument("--sprint-plan")
            item.add_argument("--mode", choices=("fixture", "live"), default="fixture")
        item.set_defaults(func=func)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    result = args.func(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, ValueError) as exc:
        print(f"CNW_RUNNER_FAILED:{exc}", file=sys.stderr)
        raise SystemExit(2)
