"""Pinned authorization identity for the sole P3.1 W10 scene."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

try:
    from .cnw_contract import ContractError
except ImportError:
    from cnw_contract import ContractError

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_REF = "P3.1-W10-CONTRACT-PREFLIGHT-ACCEPT-20261010-CQ-J19-INSERT-01-e5ef4ce8d4468756021b8b7a8e10dd3cff0b9445e25a6a399f3cc683bb0978d0"
CONTRACT_SHA256 = "e5ef4ce8d4468756021b8b7a8e10dd3cff0b9445e25a6a399f3cc683bb0978d0"
SOURCE_SCRIPT_SHA256 = "53c4f9c4f79aed2537928bf5c350d8c253c5783c7cc5d29536c9aa259b689223"
PREFLIGHT_EVIDENCE_SHA256 = "cd0c159bed09a2cbb89cf0ba1f85bbd445d3a283232dc5fe4555242d4276b921"
PREFLIGHT_PATH = ROOT / "workspace/cangqi/08_review/W10_contract_preflight.json"
PER_RUN_PREFLIGHT_SCHEMA = "cnw_w10_per_run_preflight_v1"


def _read_json(path: Path, code: str) -> tuple[dict, bytes]:
    if path.is_symlink() or not path.is_file():
        raise ContractError(code, str(path))
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(code, str(path)) from exc
    if not isinstance(value, dict):
        raise ContractError(code, str(path))
    return value, raw


def _no_reparse(path: Path) -> bool:
    return not any(part.is_symlink() for part in (path, *path.parents) if part.exists())


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify_per_run_preflight_file(
    path: str | Path,
    contract_path: str | Path,
    run_dir: str | Path,
    project_root: str | Path,
) -> tuple[dict, str]:
    """Reject self-asserted per-run verdicts until a trusted attestation exists."""
    evidence = Path(path).absolute()
    if not _no_reparse(evidence) or not evidence.is_file():
        raise ContractError("W10_PER_RUN_PREFLIGHT_PATH_UNSAFE", str(evidence))
    evidence = evidence.resolve(strict=True)
    raw = evidence.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("W10_PREFLIGHT_INVALID", str(evidence)) from exc
    if not isinstance(value, dict) or value.get("schema_version") != PER_RUN_PREFLIGHT_SCHEMA:
        raise ContractError("W10_PREFLIGHT_INVALID", "per-run review schema is invalid")
    if value.get("status") == "ACCEPTED":
        detail = "self-asserted ACCEPTED is unverified; the record must be treated as UNREVIEWED"
    else:
        detail = "per-run review remains UNREVIEWED until a trusted Controller attestation is available"
    raise ContractError("W10_CONTROLLER_ATTESTATION_UNVERIFIED", detail)


def verify_preflight_file(path: str | Path, contract_path: str | Path, *,
                          run_dir: str | Path | None = None,
                          project_root: str | Path | None = None) -> tuple[dict, str]:
    evidence = Path(path).resolve(strict=True)
    raw = evidence.read_bytes()
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("W10_PREFLIGHT_INVALID", "preflight evidence is unreadable") from exc
    if isinstance(document, dict) and document.get("schema_version") == PER_RUN_PREFLIGHT_SCHEMA:
        if run_dir is None or project_root is None:
            raise ContractError("W10_PER_RUN_PREFLIGHT_CONTEXT_REQUIRED", "run and project roots are required")
        return verify_per_run_preflight_file(evidence, contract_path, run_dir, project_root)
    expected_paths = {(ROOT / "workspace").resolve(), (ROOT / "runs").resolve()}
    if not any(evidence.is_relative_to(base) for base in expected_paths):
        raise ContractError("W10_PREFLIGHT_PATH_UNSAFE", "preflight evidence must be private")
    evidence_sha = hashlib.sha256(raw).hexdigest()
    if evidence_sha != PREFLIGHT_EVIDENCE_SHA256:
        raise ContractError("W10_PREFLIGHT_EVIDENCE_MISMATCH", evidence_sha)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("W10_PREFLIGHT_INVALID", "preflight evidence is unreadable") from exc
    contract_file = Path(contract_path).resolve(strict=True)
    contract_sha = hashlib.sha256(contract_file.read_bytes()).hexdigest()
    contract = json.loads(contract_file.read_text(encoding="utf-8"))
    if (value.get("status") != "ACCEPTED" or value.get("scope") != "W10_SINGLE_SCENE"
            or value.get("controller_acceptance_ref") != PREFLIGHT_REF
            or value.get("provider_call_authorized") is not False
            or contract_sha != CONTRACT_SHA256 or value.get("contract_sha256") != contract_sha
            or contract.get("source", {}).get("script_sha256") != SOURCE_SCRIPT_SHA256
            or value.get("source_script_sha256") != SOURCE_SCRIPT_SHA256):
        raise ContractError("W10_PREFLIGHT_BINDING_MISMATCH", "pinned Controller preflight identity does not match")
    return value, evidence_sha


def verify_preflight_object(contract_path: str | Path, value: dict) -> None:
    contract_file = Path(contract_path).resolve(strict=True)
    contract_sha = hashlib.sha256(contract_file.read_bytes()).hexdigest()
    contract = json.loads(contract_file.read_text(encoding="utf-8"))
    if (not isinstance(value, dict) or value.get("status") != "ACCEPTED"
            or value.get("scope") != "W10_SINGLE_SCENE"
            or value.get("controller_acceptance_ref") != PREFLIGHT_REF
            or value.get("provider_call_authorized") is not False
            or contract_sha != CONTRACT_SHA256 or value.get("contract_sha256") != contract_sha
            or contract.get("source", {}).get("script_sha256") != SOURCE_SCRIPT_SHA256
            or value.get("source_script_sha256") != SOURCE_SCRIPT_SHA256):
        raise ContractError("W10_CONTROLLER_PREFLIGHT_REQUIRED", "pinned Controller preflight must bind this exact W10 contract")
