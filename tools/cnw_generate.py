"""Build and validate Brief-sized CNW prose requests without hiding short drafts."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
import hashlib
from decimal import Decimal, InvalidOperation

try:
    from .cnw_contract import ContractError, assert_output_within_root, count_visible_chars, load_contract, validate_scene_budget
except ImportError:  # direct script execution
    from cnw_contract import ContractError, assert_output_within_root, count_visible_chars, load_contract, validate_scene_budget


ROOT = Path(__file__).resolve().parents[1]


def load_capacity_reference(run_directory: str | Path, ledger_path: str | Path | None = None) -> dict:
    supplied_run = Path(run_directory).absolute()
    if any(part.is_symlink() for part in (supplied_run, *supplied_run.parents) if part.exists()):
        raise ContractError("CAPACITY_REFERENCE_INVALID", "capacity run path contains a symlink")
    run = supplied_run.resolve(strict=True)
    historical_runs = (ROOT / "runs").resolve()
    if not run.is_relative_to(historical_runs) or not run.is_dir():
        raise ContractError("CAPACITY_REFERENCE_INVALID", "capacity run must be an existing private historical run")
    receipt_path, raw_path = run / "run_receipt.json", run / "provider-call.json"
    if any(path.is_symlink() or not path.is_file() for path in (receipt_path, raw_path)):
        raise ContractError("CAPACITY_REFERENCE_INVALID", "historical receipt and provider response are required")
    ledger_file = Path(ledger_path) if ledger_path else ROOT / "runtime/private/p2-cost-ledger.json"
    if ledger_file.is_symlink() or not ledger_file.is_file():
        raise ContractError("CAPACITY_REFERENCE_INVALID", "shared settled cost ledger is required")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        ledger = json.loads(ledger_file.read_text(encoding="utf-8"))
        response = raw["response"]
        choice = response["choices"][0]
        content = choice["message"]["content"]
        usage = response["usage"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, IndexError) as exc:
        raise ContractError("CAPACITY_REFERENCE_INVALID", "historical evidence is incomplete") from exc
    rows = [row for row in ledger.get("requests", []) if row.get("request_id") == receipt.get("request_id")]
    if len(rows) != 1:
        raise ContractError("CAPACITY_REFERENCE_INVALID", "exactly one settled ledger row is required")
    row = rows[0]
    if (receipt.get("status") != "SUCCEEDED" or raw.get("run_id") != run.name
            or raw.get("request_id") != receipt.get("request_id")
            or response.get("id") != receipt.get("provider_request_id")
            or response.get("model") != receipt.get("model")
            or choice.get("finish_reason") != receipt.get("finish_reason")
            or response.get("model") != "deepseek-flash" or choice.get("finish_reason") != "stop"
            or len(content) != receipt.get("scene_chars")
            or usage.get("completion_tokens") != receipt.get("output_tokens")
            or usage.get("prompt_tokens") != receipt.get("input_tokens")
            or row.get("status") != "SETTLED"
            or row.get("provider_request_id") != receipt.get("provider_request_id")
            or row.get("returned_model") != receipt.get("model")
            or row.get("finish_reason") != receipt.get("finish_reason")
            or row.get("usage") != {"input_tokens": receipt.get("input_tokens"), "output_tokens": receipt.get("output_tokens")}):
        raise ContractError("CAPACITY_REFERENCE_INVALID", "receipt, provider response and settled ledger disagree")
    return {"receipt": receipt, "raw_response_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(), "provider_response": response, "ledger_row": row}


def capacity_ratio(reference: dict) -> float:
    receipt = reference.get("receipt", {})
    response = reference.get("provider_response", {})
    ledger = reference.get("ledger_row", {})
    if (receipt.get("status") != "SUCCEEDED" or not receipt.get("request_id")
            or not receipt.get("provider_request_id") or receipt.get("model") != "deepseek-flash"
            or receipt.get("finish_reason") != "stop"):
        raise ContractError("CAPACITY_REFERENCE_INVALID", "expected a completed DeepSeek Flash receipt")
    chars, tokens = receipt.get("scene_chars"), receipt.get("output_tokens")
    if not isinstance(chars, int) or not isinstance(tokens, int) or chars <= 0 or tokens <= 0:
        raise ContractError("CAPACITY_REFERENCE_INVALID", "scene_chars and output_tokens must be positive integers")
    try:
        choice = response["choices"][0]
        content = choice["message"]["content"]
        usage = response["usage"]
    except (KeyError, TypeError, IndexError) as exc:
        raise ContractError("CAPACITY_REFERENCE_INVALID", "verified raw provider response is required") from exc
    if (not reference.get("raw_response_sha256") or len(content) != chars
            or response.get("id") != receipt.get("provider_request_id")
            or response.get("model") != receipt.get("model")
            or choice.get("finish_reason") != receipt.get("finish_reason")
            or usage.get("completion_tokens") != tokens
            or ledger.get("status") != "SETTLED"
            or ledger.get("request_id") != receipt.get("request_id")
            or ledger.get("provider_request_id") != receipt.get("provider_request_id")
            or ledger.get("returned_model") != receipt.get("model")
            or ledger.get("finish_reason") != receipt.get("finish_reason")
            or ledger.get("usage") != {"input_tokens": receipt.get("input_tokens"), "output_tokens": tokens}):
        raise ContractError("CAPACITY_REFERENCE_INVALID", "raw response and ledger do not support receipt metrics")
    return chars / tokens


def _canonical_sha256(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_accepted_prose_inputs(contract: dict, brief: str, voice_samples: str, context: dict) -> None:
    brief_sha = hashlib.sha256(brief.encode("utf-8")).hexdigest()
    voice_sha = hashlib.sha256(voice_samples.encode("utf-8")).hexdigest()
    refs = contract.get("story", {}).get("voice_sample_refs", [])
    ref = context.get("voice_sample_reference", "")
    if (not context.get("run_id") or context.get("contract_approval_status") != "ACCEPTED"
            or context.get("contract_sha256") != _canonical_sha256(contract)
            or not re.fullmatch(r"[0-9a-f]{64}", str(context.get("contract_approval_evidence_sha256", "")))
            or context.get("brief_stage_status") != "ACCEPTED"
            or context.get("brief_fixture_only") is not False
            or context.get("brief_sha256") != brief_sha
            or context.get("voice_sample_sha256") != voice_sha
            or ref not in refs or f"SHA256={voice_sha}" not in ref):
        raise ContractError("PROSE_INPUTS_NOT_ACCEPTED", "contract, Brief, and cited voice sample must be frozen and hash-bound")


def _tokens_for_chars(characters: int, chars_per_token: float, headroom: float) -> int:
    if not math.isfinite(chars_per_token) or chars_per_token <= 0 or not 1 <= headroom <= 2:
        raise ContractError("CAPACITY_REFERENCE_INVALID", "invalid capacity ratio or headroom")
    return math.ceil(characters / chars_per_token * headroom)


def plan_output_segments(contract: dict, capacity_receipt: dict, *, provider_output_cap: int, budget_output_cap: int, headroom: float = 1.15) -> dict:
    validate_scene_budget(contract)
    if not isinstance(provider_output_cap, int) or not isinstance(budget_output_cap, int) or min(provider_output_cap, budget_output_cap) <= 0:
        raise ContractError("OUTPUT_CAP_INVALID", "provider and budget caps must be positive")
    ratio = capacity_ratio(capacity_receipt)
    usable_cap = min(provider_output_cap, budget_output_cap)
    target = contract["unit"]["target_visible_chars"]
    target_tokens = _tokens_for_chars(target, ratio, headroom)
    beats = contract["story"]["required_beats"]
    if target_tokens <= usable_cap:
        segments = [{"segment_id": "SCENE", "beat_ids": [beat["beat_id"] for beat in beats], "target_visible_chars": target, "output_token_cap": target_tokens, "requires_previous_context": False}]
    else:
        segments = []
        current = []
        current_chars = 0
        current_tokens = 0
        for beat in beats:
            beat_tokens = _tokens_for_chars(beat["budget_visible_chars"], ratio, headroom)
            if beat_tokens > usable_cap:
                raise ContractError("SCENE_SEGMENT_EXCEEDS_TOKEN_CAP", beat["beat_id"])
            if current and current_tokens + beat_tokens > usable_cap:
                segments.append({"segment_id": f"SEG{len(segments) + 1:02d}", "beat_ids": current, "target_visible_chars": current_chars, "output_token_cap": current_tokens, "requires_previous_context": bool(segments)})
                current, current_chars, current_tokens = [], 0, 0
            current.append(beat["beat_id"])
            current_chars += beat["budget_visible_chars"]
            current_tokens += beat_tokens
        if current:
            segments.append({"segment_id": f"SEG{len(segments) + 1:02d}", "beat_ids": current, "target_visible_chars": current_chars, "output_token_cap": current_tokens, "requires_previous_context": bool(segments)})
    return {"observed_chars_per_output_token": ratio, "capacity_receipt_id": capacity_receipt["receipt"]["request_id"], "capacity_raw_response_sha256": capacity_receipt["raw_response_sha256"], "headroom": headroom, "target_output_tokens": target_tokens, "usable_output_token_cap": usable_cap, "segmented": len(segments) > 1, "segments": segments}


def build_prose_request(contract: dict, brief: str, voice_samples: str, capacity_receipt: dict, *, accepted_context: dict, provider_output_cap: int, budget_output_cap: int) -> dict:
    validate_scene_budget(contract)
    if not brief.strip() or not voice_samples.strip():
        raise ContractError("PROSE_INPUT_MISSING", "accepted Brief and voice samples are required")
    validate_accepted_prose_inputs(contract, brief, voice_samples, accepted_context)
    for beat in contract["story"]["required_beats"]:
        if beat["beat_id"] not in brief:
            raise ContractError("BRIEF_BEAT_ID_MISSING", beat["beat_id"])
    plan = plan_output_segments(contract, capacity_receipt, provider_output_cap=provider_output_cap, budget_output_cap=budget_output_cap)
    unit = contract["unit"]
    system = (
        f"Write a complete, fully dramatized Chinese interactive-fiction scene in {unit['pov']}'s limited POV. "
        "Follow the supplied Writing Brief and participating-character voice samples. Write actions, responses, dialogue, pauses, and transitions as scene prose; do not return an outline, beat list, synopsis, or a two-sentence summary. "
        f"The scene target is {unit['target_visible_chars']} visible characters; acceptable range {unit['min_visible_chars']}–{unit['max_visible_chars']}. Cover every required beat in the Brief. "
        "Do not impose an additional 500–700-character limit. Output only the scene prose."
    )
    return {
        "schema_version": "cnw_prose_request_v1",
        "inputs": {"brief": brief, "voice_samples": voice_samples, "brief_sha256": accepted_context["brief_sha256"], "voice_sample_sha256": accepted_context["voice_sample_sha256"], "run_id": accepted_context["run_id"]},
        "execution_contract": {"target_visible_chars": unit["target_visible_chars"], "min_visible_chars": unit["min_visible_chars"], "max_visible_chars": unit["max_visible_chars"], "required_beats": contract["story"]["required_beats"]},
        "system": system,
        "segments": plan["segments"],
        "capacity_plan": plan,
        "provider_call": "not_performed_by_W06_offline_builder",
    }


def build_segment_request(base_request: dict, segment_id: str, completed_segments: list[dict]) -> dict:
    segments = base_request["segments"]
    position = next((index for index, item in enumerate(segments) if item["segment_id"] == segment_id), None)
    if position is None:
        raise ContractError("SEGMENT_ID_UNKNOWN", segment_id)
    if len(completed_segments) != position:
        raise ContractError("SEGMENT_SEQUENCE_INVALID", "all earlier segments must be complete before this request")
    for expected, completed in zip(segments[:position], completed_segments):
        if completed.get("segment_id") != expected["segment_id"] or completed.get("finish_reason") != "stop" or not completed.get("text", "").strip():
            raise ContractError("SEGMENT_SEQUENCE_INVALID", "prior segments must be present, ordered, nonempty and complete")
    item = segments[position]
    continuity = completed_segments[-1]["text"][-1200:] if completed_segments else ""
    return {"segment": item, "system": base_request["system"], "prior_context": continuity, "brief": base_request["inputs"]["brief"], "voice_samples": base_request["inputs"]["voice_samples"], "output_token_cap": item["output_token_cap"], "instruction": "Write only this segment's assigned beats. Continue directly from prior_context when present; do not repeat its ending. Preserve POV, voice, and state continuity."}


def assemble_segment_outputs(contract: dict, base_request: dict, outputs: list[dict], *, cost_ledger_path: str | Path | None = None, beat_evidence: dict[str, str], dialogue_evidence: list[str], action_evidence: list[str], start_state_evidence: str, end_state_evidence: str) -> dict:
    try:
        from . import p2_cost_guard
    except ImportError:
        import p2_cost_guard
    expected = base_request["segments"]
    if len(outputs) != len(expected) or any(output.get("segment_id") != segment["segment_id"] for output, segment in zip(outputs, expected)):
        raise ContractError("SEGMENT_SEQUENCE_INVALID", "all planned segments must be supplied in order")
    if any(output.get("finish_reason") != "stop" or not output.get("text", "").strip() for output in outputs):
        raise ContractError("SEGMENT_INCOMPLETE", "each segment must be nonempty and completed")
    request_ids, provider_ids = set(), set()
    ledger_path = Path(cost_ledger_path) if cost_ledger_path else p2_cost_guard.LEDGER
    if ledger_path.is_symlink() or not ledger_path.is_file():
        raise ContractError("SEGMENT_COST_LEDGER_MISSING", str(ledger_path))
    try:
        ledger_bytes = ledger_path.read_bytes() if cost_ledger_path else p2_cost_guard.read_ledger_bytes()
        cost_ledger = json.loads(ledger_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("SEGMENT_COST_LEDGER_INVALID", str(exc)) from exc
    private_runtime = (ROOT / "runtime/private").resolve()
    if not ledger_path.resolve().is_relative_to(private_runtime):
        raise ContractError("SEGMENT_COST_LEDGER_UNSAFE", "cost ledger must come from private runtime accounting")
    rows = cost_ledger.get("requests", [])
    for output in outputs:
        required = ("request_id", "provider_request_id", "model", "status", "usage", "cost_cny", "raw_response_sha256", "output_sha256", "ledger_settlement")
        if not all(output.get(key) is not None for key in required):
            raise ContractError("SEGMENT_COST_EVIDENCE_MISSING", output["segment_id"])
        if (not isinstance(output["request_id"], str) or not output["request_id"]
                or not isinstance(output["provider_request_id"], str) or not output["provider_request_id"] or output["model"] != "deepseek-flash"
                or output["status"] != "SUCCEEDED" or output["finish_reason"] != "stop"):
            raise ContractError("SEGMENT_RECEIPT_INVALID", output["segment_id"])
        if output["request_id"] in request_ids or output["provider_request_id"] in provider_ids:
            raise ContractError("SEGMENT_RECEIPT_DUPLICATE", output["segment_id"])
        request_ids.add(output["request_id"])
        provider_ids.add(output["provider_request_id"])
        usage = output["usage"]
        if not isinstance(usage, dict) or not all(isinstance(usage.get(key), int) and usage[key] > 0 for key in ("prompt_tokens", "completion_tokens")):
            raise ContractError("SEGMENT_RECEIPT_INVALID", output["segment_id"])
        if (not isinstance(output["text"], str) or not re.fullmatch(r"[0-9a-fA-F]{64}", str(output["raw_response_sha256"]))
                or hashlib.sha256(output["text"].encode("utf-8")).hexdigest() != output["output_sha256"]):
            raise ContractError("SEGMENT_RECEIPT_HASH_INVALID", output["segment_id"])
        settlement = output["ledger_settlement"]
        matches = [row for row in rows if row.get("request_id") == output["request_id"]]
        try:
            billed = Decimal(str(matches[0].get("estimated_actual_cny"))) if len(matches) == 1 else Decimal("NaN")
            reported = Decimal(str(output["cost_cny"]))
        except (InvalidOperation, ValueError):
            raise ContractError("SEGMENT_COST_SETTLEMENT_MISMATCH", output["segment_id"])
        if not isinstance(settlement, dict) or not billed.is_finite() or not reported.is_finite() or reported < 0:
            raise ContractError("SEGMENT_COST_SETTLEMENT_MISMATCH", output["segment_id"])
        if (len(matches) != 1 or matches[0].get("status") != "SETTLED"
                or matches[0].get("provider_request_id") != output["provider_request_id"]
                or matches[0].get("returned_model") != output["model"]
                or matches[0].get("finish_reason") != output["finish_reason"]
                or matches[0].get("usage") != {"input_tokens": usage["prompt_tokens"], "output_tokens": usage["completion_tokens"]}
                or settlement.get("status") != "SETTLED" or settlement.get("request_id") != output["request_id"]
                or billed != reported):
            raise ContractError("SEGMENT_COST_SETTLEMENT_MISMATCH", output["segment_id"])
    prose = "\n".join(output["text"].strip() for output in outputs)
    validation = validate_generated_scene(contract, prose, finish_reason="stop", beat_evidence=beat_evidence, dialogue_evidence=dialogue_evidence, action_evidence=action_evidence, start_state_evidence=start_state_evidence, end_state_evidence=end_state_evidence)
    return {"status": "DRAFT_CONTENT_AND_COST_VALIDATED" if validation["status"] == "CONTENT_VALID" else "DRAFT_RETURN", "scope": "content_and_settlement_reconciled; raw_provider_authentication_requires_runner_verify_live", "prose": prose, "segment_order": [output["segment_id"] for output in outputs], "segment_response_ids": [output["provider_request_id"] for output in outputs], "settled_cost_cny": str(sum((Decimal(str(output["cost_cny"])) for output in outputs), Decimal("0"))), "cost_ledger_sha256": hashlib.sha256(ledger_bytes).hexdigest(), "validation": validation}


def _project_root(value: str | Path) -> Path:
    candidate = Path(value).absolute()
    if any(part.is_symlink() for part in (candidate, *candidate.parents) if part.exists()):
        raise ContractError("PROJECT_PATH_UNSAFE", "project root contains a symlink")
    root = candidate.resolve(strict=True)
    workspace = (ROOT / "workspace").resolve()
    if root.is_relative_to(workspace) and root.is_dir():
        return root
    try:
        try:
            from .project_paths import resolve_project
        except ImportError:
            from project_paths import resolve_project
        registration = resolve_project(root, data_home=root.parent.parent)
    except Exception as exc:
        raise ContractError("PROJECT_ROOT_NOT_REGISTERED", str(root)) from exc
    identity_path = root / "project_identity.json"
    if (not identity_path.is_file() or identity_path.is_symlink() or
            registration.get("project_id") is None or not root.is_dir()):
        raise ContractError("PROJECT_ROOT_NOT_REGISTERED", str(root))
    return root


def _private_project_root(value: str | Path) -> Path:
    """Preserve the private-workspace-only boundary for legacy revision tools."""
    root = _project_root(value)
    workspace = (ROOT / "workspace").resolve()
    if not root.is_relative_to(workspace):
        raise ContractError("PROJECT_ROOT_OUTSIDE_PRIVATE_WORKSPACE", str(root))
    return root


def _project_input(root: Path, value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    if any(part.is_symlink() for part in (candidate, *candidate.parents) if part.exists()):
        raise ContractError("PROJECT_INPUT_PATH_UNSAFE", str(value))
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ContractError("PROJECT_INPUT_OUTSIDE_PRIVATE_PROJECT", str(value))
    return resolved


def validate_generated_scene(contract: dict, prose: str, *, finish_reason: str, beat_evidence: dict[str, str], dialogue_evidence: list[str], action_evidence: list[str], start_state_evidence: str, end_state_evidence: str) -> dict:
    failures = []
    visible = count_visible_chars(prose)
    unit = contract["unit"]
    if visible < unit["min_visible_chars"]:
        failures.append("RETURN_UNDERPRODUCED")
    if visible > unit["max_visible_chars"]:
        failures.append("RETURN_OVER_LIMIT")
    missing_beats = [beat["beat_id"] for beat in contract["story"]["required_beats"] if not beat_evidence.get(beat["beat_id"]) or beat_evidence[beat["beat_id"]] not in prose]
    if missing_beats:
        failures.append("RETURN_MISSING_BEAT")
    # Contracts may list exact source-backed revelations the current POV cannot
    # know yet. Treat them as deterministic hard blockers, not prompt advice.
    forbidden_revelations = contract.get("story", {}).get("forbidden_future_revelations", [])
    leaked_revelations = [item for item in forbidden_revelations
                          if isinstance(item, str) and item.strip()
                          and not item.lstrip().lower().startswith(("do not ", "不得", "禁止"))
                          and item in prose]
    if leaked_revelations:
        failures.append("RETURN_KNOWLEDGE_BOUNDARY")
    if not any(span and span in prose for span in dialogue_evidence):
        failures.append("RETURN_MISSING_DIALOGUE")
    if not any(span and span in prose for span in action_evidence):
        failures.append("RETURN_MISSING_ACTION")
    if not start_state_evidence or start_state_evidence not in prose:
        failures.append("RETURN_START_STATE_UNPROVEN")
    if not end_state_evidence or end_state_evidence not in prose:
        failures.append("RETURN_END_STATE_UNPROVEN")
    if finish_reason != "stop":
        failures.append("TRUNCATED_OR_UNFINISHED")
    return {"status": "CONTENT_VALID" if not failures else "CONTENT_RETURN", "failure_codes": failures,
            "missing_beat_ids": missing_beats, "leaked_revelations": leaked_revelations,
            "actual_visible_chars": visible, "finish_reason": finish_reason,
            "validation_scope": "CONTENT_ONLY_NO_COST_OR_PROVIDER_AUTHENTICATION"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--voice-samples", required=True)
    parser.add_argument("--capacity-run", required=True, help="historical private run directory containing provider-call.json and run_receipt.json")
    parser.add_argument("--provider-output-cap", type=int, default=2048)
    parser.add_argument("--budget-output-cap", type=int, required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True, help="private output path, relative to project root under runs/")
    parser.add_argument("--mode", choices=("offline", "live"), default="offline")
    args = parser.parse_args(argv)
    if args.mode == "live":
        raise ContractError("LIVE_EXECUTOR_NOT_AVAILABLE", "W06 constructs and validates requests offline; live execution remains gated for W10")
    project_root = _project_root(args.project_root)
    run_id = args.run_id
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,95}", run_id) or run_id in {".", ".."}:
        raise ContractError("RUN_ID_INVALID", run_id)
    run_root = project_root / "runs" / run_id
    try:
        run_root = run_root.resolve(strict=True)
    except OSError as exc:
        raise ContractError("RUN_STATE_MISSING_OR_UNSAFE", run_id) from exc
    if not run_root.is_relative_to(project_root) or any(part.is_symlink() for part in (project_root / "runs" / run_id, project_root / "runs")):
        raise ContractError("RUN_STATE_MISSING_OR_UNSAFE", run_id)
    state_path = run_root / "run_state.json"
    if state_path.is_symlink() or not state_path.is_file():
        raise ContractError("RUN_STATE_MISSING_OR_UNSAFE", run_id)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        contract_path = run_root / "artifacts/contract.json"
        if contract_path.is_symlink() or not contract_path.is_file():
            raise ContractError("PROSE_INPUTS_NOT_ACCEPTED", "contract artifact missing or unsafe")
        contract_bytes = contract_path.read_bytes()
        contract = json.loads(contract_bytes)
        brief_record = state["stages"]["brief"]
        brief_relative = brief_record["artifact"]["path"]
        brief_path = (run_root / brief_relative).resolve(strict=True)
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ContractError("PROSE_INPUTS_NOT_ACCEPTED", "run must contain frozen contract and accepted Brief artifacts") from exc
    if not brief_path.is_relative_to(run_root):
        raise ContractError("PROSE_INPUTS_NOT_ACCEPTED", "Brief artifact escapes run directory")
    if contract.get("schema_version") == "cnw_work_unit_v2":
        try:
            from .cnw_contract import validate_v2_source_identity
            from .cnw_runner import validate_literary_source_freeze
        except ImportError:
            from cnw_contract import validate_v2_source_identity
            from cnw_runner import validate_literary_source_freeze
        validate_v2_source_identity(contract, source_root=project_root)
        validate_literary_source_freeze(state, project_root)
    if (state.get("run_id") != run_id or state.get("fixture_only") is True
            or state.get("contract_sha256") != hashlib.sha256(contract_bytes).hexdigest()
            or state.get("contract_approval", {}).get("status") != "ACCEPTED"
            or not state.get("contract_approval", {}).get("evidence_sha256")
            or brief_record.get("status") != "ACCEPTED" or brief_record.get("fixture_only") is not False
            or brief_record.get("artifact", {}).get("sha256") != hashlib.sha256(brief_path.read_bytes()).hexdigest()
            or not brief_path.is_relative_to(run_root)):
        raise ContractError("PROSE_INPUTS_NOT_ACCEPTED", "run state, contract approval, or Brief artifact identity is invalid")
    approval = state["contract_approval"]
    approval_path = _project_input(project_root, approval.get("evidence_path", ""))
    approval_bytes = approval_path.read_bytes()
    if hashlib.sha256(approval_bytes).hexdigest() != approval["evidence_sha256"]:
        raise ContractError("PROSE_INPUTS_NOT_ACCEPTED", "contract approval evidence hash mismatch")
    try:
        approval_record = json.loads(approval_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("PROSE_INPUTS_NOT_ACCEPTED", "contract approval evidence is invalid") from exc
    if (approval_record.get("status") != "ACCEPTED"
            or approval_record.get("contract_sha256") != state["contract_sha256"]
            or not approval_record.get("reviewer_id")):
        raise ContractError("PROSE_INPUTS_NOT_ACCEPTED", "contract approval evidence does not bind this frozen contract")
    brief = brief_path.read_text(encoding="utf-8-sig")
    voice_path = _project_input(project_root, args.voice_samples)
    capacity_reference = load_capacity_reference(args.capacity_run)
    voice_samples = voice_path.read_text(encoding="utf-8-sig")
    voice_hash = hashlib.sha256(voice_path.read_bytes()).hexdigest()
    voice_reference = next((ref for ref in contract.get("story", {}).get("voice_sample_refs", []) if f"SHA256={voice_hash}" in ref), "")
    context = {"run_id": run_id, "contract_sha256": _canonical_sha256(contract), "contract_approval_status": "ACCEPTED",
               "contract_approval_evidence_sha256": state["contract_approval"]["evidence_sha256"], "brief_stage_status": "ACCEPTED",
               "brief_fixture_only": False, "brief_sha256": hashlib.sha256(brief.encode("utf-8")).hexdigest(),
               "voice_sample_sha256": voice_hash, "voice_sample_reference": voice_reference}
    result = build_prose_request(contract, brief, voice_samples, capacity_reference, accepted_context=context, provider_output_cap=args.provider_output_cap, budget_output_cap=args.budget_output_cap)
    relative = Path(args.output)
    if relative.is_absolute() or not relative.parts or relative.parts[0].lower() != "runs":
        raise ContractError("OUTPUT_PATH_UNSAFE", "request artifact must be written under runs/")
    destination = assert_output_within_root(project_root, str(relative))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "REQUEST_BUILT_OFFLINE", "output": str(destination), "target_visible_chars": result["execution_contract"]["target_visible_chars"], "segmented": result["capacity_plan"]["segmented"], "provider_call": result["provider_call"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"CNW_GENERATE_FAILED:{exc}", file=sys.stderr)
        raise SystemExit(2)
