"""CNW role packets, provenance receipts, and offline structural gates."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from .cnw_contract import ContractError, check_required_fields, load_contract, validate_episode_budget, validate_output_length, validate_scene_budget, validate_source_identity
except ImportError:  # direct script execution
    from cnw_contract import ContractError, check_required_fields, load_contract, validate_episode_budget, validate_output_length, validate_scene_budget, validate_source_identity

ROOT = Path(__file__).resolve().parents[1]
PROMPT_DIR = ROOT / "prompts" / "cnw"
ROLE_FILES = {"plot": "plot.md", "cards": "scene_cards.md", "brief": "brief.md", "prose": "prose.md"}
UPSTREAM_METHOD = {"plot": "plot", "cards": "scene_cards", "brief": "writing_brief", "prose": "ai_roles"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _read_project_file(path: str | Path) -> tuple[Path, str]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    resolved = candidate.resolve(strict=True)
    allowed = ((ROOT / "workspace" / "cangqi").resolve(), (ROOT / "runs").resolve())
    if not any(resolved.is_relative_to(root) for root in allowed) or not resolved.is_file():
        raise ContractError("ROLE_INPUT_PATH_UNSAFE", "role input must be a private project or run file")
    return resolved, resolved.read_text(encoding="utf-8-sig")


def _hash_inputs(inputs: dict[str, str | Path]) -> dict[str, str]:
    result = {}
    for name, value in sorted(inputs.items()):
        path, _ = _read_project_file(value)
        result[name] = sha256_file(path)
    return result


def build_prose_input_view(contract: dict[str, Any], brief: str, voice_samples: str) -> dict[str, Any]:
    """Return only the brief, relevant voices, and minimum execution bounds."""
    unit = contract["unit"]
    return {
        "execution_contract": {
            "unit_id": unit["id"],
            "language": unit["language"],
            "pov": unit["pov"],
            "target_visible_chars": unit["target_visible_chars"],
            "min_visible_chars": unit["min_visible_chars"],
            "max_visible_chars": unit["max_visible_chars"],
            "required_beat_ids": [beat["beat_id"] for beat in contract["story"].get("required_beats", [])],
        },
        "inputs": {"brief": brief, "voice_samples": voice_samples},
    }


def build_role_packet(role: str, contract_path: str | Path, inputs: dict[str, str | Path], *, accepted_receipts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if role not in ROLE_FILES:
        raise ContractError("ROLE_UNKNOWN", role)
    contract_file, _ = _read_project_file(contract_path)
    contract_path = contract_file
    contract = load_contract(contract_path)
    check_required_fields(contract)
    source = contract["source"]
    release_root = ROOT / "inputs" / "private" / "release" / source["zip_sha256"].lower() / "Cangqi_Jun_Release_2_3"
    validate_source_identity(
        contract,
        source_root=release_root,
        expected_version=source["version"],
        expected_zip_sha256=source["zip_sha256"],
        expected_manifest_sha256=source["local_private_source_manifest_sha256"],
    )
    policy_path = ROOT / "config" / "cnw_production_policy.json"
    if contract["unit"].get("policy_sha256", "").lower() != sha256_file(policy_path):
        raise ContractError("PRODUCTION_POLICY_IDENTITY_MISMATCH", "policy SHA256 differs from the frozen contract")
    cnw_manifest = ROOT / "runtime" / "reference" / "cnw_97ad71fe5e5e" / "CNW_LOCAL_REFERENCE_MANIFEST.json"
    expected_cnw_manifest = contract.get("review", {}).get("cnw_reference_manifest_sha256", "").lower()
    if not cnw_manifest.is_file() or sha256_file(cnw_manifest) != expected_cnw_manifest:
        raise ContractError("CNW_REFERENCE_IDENTITY_MISMATCH", "captured CNW reference manifest differs")
    if contract["unit"]["kind"] == "scene":
        validate_scene_budget(contract)
    elif contract["unit"]["kind"] == "episode":
        validate_episode_budget(contract["unit"])
    else:
        raise ContractError("WORK_UNIT_KIND_INVALID", str(contract["unit"].get("kind")))
    allowed_inputs = {
        "plot": ("canon_scope", "source_anchors"),
        "cards": ("plot", "canon_scope"),
        "brief": ("plot", "cards", "canon_scope", "style_guide", "voice_samples", "nk_reflection"),
        "prose": ("brief", "voice_samples"),
    }[role]
    expected = allowed_inputs
    missing = [name for name in expected if name not in inputs]
    if missing:
        raise ContractError("ROLE_DEPENDENCY_MISSING", ", ".join(missing))
    extra = set(inputs) - set(allowed_inputs)
    if extra:
        raise ContractError("ROLE_INPUT_SCOPE_VIOLATION", f"{role} may not receive {sorted(extra)}")
    if role == "prose" and "voice_samples" not in inputs:
        raise ContractError("ROLE_DEPENDENCY_MISSING", "voice_samples")
    required_receipts = {"plot": (), "cards": ("plot",), "brief": ("plot", "cards"), "prose": ("plot", "cards", "brief")}[role]
    if required_receipts:
        receipts = accepted_receipts or []
        verify_stage_chain(receipts, required_receipts)
        contract_digest = sha256_file(contract_path)
        for prior_role in required_receipts:
            match = next(receipt for receipt in receipts if receipt.get("role") == prior_role)
            if match.get("contract_sha256") != contract_digest:
                raise ContractError("CNW_STAGE_CONTRACT_MISMATCH", prior_role)
            input_name = {"plot": "plot", "cards": "cards", "brief": "brief"}[prior_role]
            if input_name in inputs:
                input_path, _ = _read_project_file(inputs[input_name])
                if match.get("output_sha256") != sha256_file(input_path):
                    raise ContractError("CNW_DEPENDENCY_OUTPUT_MISMATCH", prior_role)
    prompt_path = PROMPT_DIR / ROLE_FILES[role]
    prompt = prompt_path.read_text(encoding="utf-8")
    hashes = _hash_inputs(inputs)
    packet = {
        "role": role,
        "work_id": contract["unit"]["id"],
        "contract_sha256": sha256_file(contract_path),
        "upstream_method": UPSTREAM_METHOD[role],
        "prompt_sha256": sha256_file(prompt_path),
        "input_hashes": hashes,
        "target_visible_chars": contract["unit"].get("target_visible_chars"),
        "required_beat_ids": [b["beat_id"] for b in contract["story"].get("required_beats", [])],
        "prompt": prompt,
        "inputs": {name: _read_project_file(path)[1] for name, path in inputs.items()},
    }
    if role == "prose":
        packet.update(build_prose_input_view(contract, packet["inputs"]["brief"], packet["inputs"]["voice_samples"]))
    else:
        packet["contract"] = contract
    return packet


def validate_role_output(role: str, contract: dict[str, Any], output: str) -> None:
    if not output.strip() or output.lstrip().startswith("RETURN:"):
        raise ContractError("ROLE_OUTPUT_INVALID", "empty output or role returned a failure")
    beat_ids = [beat["beat_id"] for beat in contract["story"].get("required_beats", [])]
    if role in ("plot", "cards", "brief"):
        required_sections = {
            "plot": ("## Identity", "## Role in the Arc", "## Key Scenes", "## Hook", "## Required Story Beats", "## Forbidden Items", "## Connections", "## Target Length", "Reader Reward"),
            "cards": ("### Identity", "### Cast", "### Start state", "### End state", "Character Wants", "### Required beats", "### Forbidden items for this scene", "### Sensory anchor", "### Tone / pacing", "### Connection to next scene"),
            "brief": ("## Quick Header", "## Active Canon", "## Scene-by-Scene Instructions", "## Voice References", "## Hard Constraints", "## Style Targets", "## What NOT to include in the prose", "NK Perspective Reflection"),
        }[role]
        missing_sections = [section for section in required_sections if section.casefold() not in output.casefold()]
        if missing_sections:
            raise ContractError("ROLE_TEMPLATE_SECTION_MISSING", ", ".join(missing_sections))
        missing = [beat_id for beat_id in beat_ids if beat_id not in output]
        if missing:
            raise ContractError("ROLE_BEAT_ID_DROPPED", ", ".join(missing))
        unit = contract["unit"]
        marker = re.search(r"^CNW_CONTRACT target_visible_chars=(\d+) min_visible_chars=(\d+) max_visible_chars=(\d+)$", output, re.MULTILINE)
        expected = (unit["target_visible_chars"], unit["min_visible_chars"], unit["max_visible_chars"])
        if not marker:
            raise ContractError("ROLE_CONTRACT_MANIFEST_MISSING", "required CNW_CONTRACT marker not found")
        actual = tuple(int(value) for value in marker.groups())
        if actual != expected:
            raise ContractError("ROLE_CONTRACT_LENGTH_MISMATCH", f"expected {expected}, got {actual}")
        beat_markers = re.findall(r"^CNW_BEAT ([A-Za-z0-9_.-]+) budget_visible_chars=(\d+)$", output, re.MULTILINE)
        expected_beats = {beat["beat_id"]: beat["budget_visible_chars"] for beat in contract["story"].get("required_beats", [])}
        actual_beats = {beat_id: int(budget) for beat_id, budget in beat_markers}
        if actual_beats != expected_beats or len(beat_markers) != len(expected_beats):
            raise ContractError("ROLE_BEAT_BUDGET_MISMATCH", f"expected {expected_beats}, got {actual_beats}")
    if role == "prose":
        validate_output_length(contract, output)


def role_receipt(role: str, packet: dict[str, Any], output: str, *, status: str, provider_request_ids: list[str] | None = None, controller_accept_ref: str | None = None) -> dict[str, Any]:
    if status not in {"FIXTURE_ONLY", "PROVIDER_RESULT_PENDING_REVIEW", "CONTROLLER_ACCEPTED"}:
        raise ContractError("ROLE_RECEIPT_STATUS_INVALID", status)
    if status == "CONTROLLER_ACCEPTED" and (not provider_request_ids or not controller_accept_ref):
        raise ContractError("ROLE_ACCEPTANCE_EVIDENCE_MISSING", "a real provider request and Controller acceptance reference are required")
    return {
        "role": role,
        "work_id": packet["work_id"],
        "status": status,
        "contract_sha256": packet["contract_sha256"],
        "prompt_sha256": packet["prompt_sha256"],
        "input_hashes": packet["input_hashes"],
        "output_sha256": sha256_bytes(output.encode("utf-8")),
        "provider_request_ids": provider_request_ids or [],
        "controller_accept_ref": controller_accept_ref,
    }


def verify_stage_chain(receipts: list[dict[str, Any]], required_roles: tuple[str, ...] = ("plot", "cards", "brief")) -> None:
    roles = tuple(receipt.get("role") for receipt in receipts)
    if roles != required_roles:
        raise ContractError("CNW_STAGE_CHAIN_INCOMPLETE", f"expected {required_roles}, got {roles}")
    work_ids = {receipt.get("work_id") for receipt in receipts}
    if len(work_ids) != 1:
        raise ContractError("CNW_STAGE_WORK_ID_MISMATCH", "role receipts have different work IDs")
    if any(receipt.get("status") != "CONTROLLER_ACCEPTED" for receipt in receipts):
        # Offline fixtures can test the chain, but may never unlock Prose.
        raise ContractError("CNW_FIXTURE_CANNOT_UNLOCK_PROSE", "only explicitly reviewed provider results can unlock Prose")
    contract_hashes = {receipt.get("contract_sha256") for receipt in receipts}
    if len(contract_hashes) != 1 or None in contract_hashes:
        raise ContractError("CNW_STAGE_CONTRACT_MISMATCH", "role receipts do not share one frozen contract")
    if any(not receipt.get("provider_request_ids") or not receipt.get("controller_accept_ref") for receipt in receipts):
        raise ContractError("CNW_ACCEPTANCE_EVIDENCE_MISSING", "each planning role needs a real request and Controller acceptance")
    if any(str(request_id).lower().startswith(("fixture", "test", "mock")) for receipt in receipts for request_id in receipt.get("provider_request_ids", [])):
        raise ContractError("CNW_FIXTURE_CANNOT_UNLOCK_PROSE", "fixture request IDs cannot satisfy a production stage gate")
