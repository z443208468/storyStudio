"""Build and validate Brief-sized CNW prose requests without hiding short drafts."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
import hashlib

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


def build_prose_request(contract: dict, brief: str, voice_samples: str, capacity_receipt: dict, *, provider_output_cap: int, budget_output_cap: int) -> dict:
    validate_scene_budget(contract)
    if not brief.strip() or not voice_samples.strip():
        raise ContractError("PROSE_INPUT_MISSING", "accepted Brief and voice samples are required")
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
        "inputs": {"brief": brief, "voice_samples": voice_samples},
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


def assemble_segment_outputs(contract: dict, base_request: dict, outputs: list[dict], *, beat_evidence: dict[str, str], dialogue_evidence: list[str], action_evidence: list[str], start_state_evidence: str, end_state_evidence: str) -> dict:
    expected = base_request["segments"]
    if len(outputs) != len(expected) or any(output.get("segment_id") != segment["segment_id"] for output, segment in zip(outputs, expected)):
        raise ContractError("SEGMENT_SEQUENCE_INVALID", "all planned segments must be supplied in order")
    if any(output.get("finish_reason") != "stop" or not output.get("text", "").strip() for output in outputs):
        raise ContractError("SEGMENT_INCOMPLETE", "each segment must be nonempty and completed")
    prose = "\n".join(output["text"].strip() for output in outputs)
    validation = validate_generated_scene(contract, prose, finish_reason="stop", beat_evidence=beat_evidence, dialogue_evidence=dialogue_evidence, action_evidence=action_evidence, start_state_evidence=start_state_evidence, end_state_evidence=end_state_evidence)
    return {"status": validation["status"], "prose": prose, "segment_order": [output["segment_id"] for output in outputs], "segment_response_ids": [output.get("provider_request_id") for output in outputs], "validation": validation}


def _private_project_root(value: str | Path) -> Path:
    candidate = Path(value).absolute()
    if any(part.is_symlink() for part in (candidate, *candidate.parents) if part.exists()):
        raise ContractError("PROJECT_PATH_UNSAFE", "project root contains a symlink")
    root = candidate.resolve(strict=True)
    workspace = (ROOT / "workspace").resolve(strict=True)
    if not root.is_relative_to(workspace) or not root.is_dir():
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
    return {"status": "PASS" if not failures else "RETURN", "failure_codes": failures, "missing_beat_ids": missing_beats, "actual_visible_chars": visible, "finish_reason": finish_reason}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--brief", required=True)
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
    project_root = _private_project_root(args.project_root)
    contract_path = _project_input(project_root, args.contract)
    brief_path = _project_input(project_root, args.brief)
    voice_path = _project_input(project_root, args.voice_samples)
    capacity_reference = load_capacity_reference(args.capacity_run)
    contract = load_contract(contract_path)
    result = build_prose_request(contract, brief_path.read_text(encoding="utf-8-sig"), voice_path.read_text(encoding="utf-8-sig"), capacity_reference, provider_output_cap=args.provider_output_cap, budget_output_cap=args.budget_output_cap)
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
