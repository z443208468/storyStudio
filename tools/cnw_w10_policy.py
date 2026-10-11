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
    """Verify a project-bound W10 review without replacing the frozen J19 pin."""
    evidence = Path(path).absolute()
    contract_file = Path(contract_path).absolute()
    run = Path(run_dir).resolve(strict=True)
    project = Path(project_root).resolve(strict=True)
    if not _no_reparse(evidence) or not evidence.is_file():
        raise ContractError("W10_PER_RUN_PREFLIGHT_PATH_UNSAFE", str(evidence))
    evidence = evidence.resolve(strict=True)
    if not (evidence.is_relative_to(project) or not evidence.is_relative_to(ROOT.resolve())):
        raise ContractError("W10_PER_RUN_PREFLIGHT_PATH_UNSAFE", "evidence must be in the selected project or external private storage")
    state_path = run / "run_state.json"
    run_contract_path = run / "artifacts" / "contract.json"
    if (not _no_reparse(state_path) or not _no_reparse(contract_file)
            or not _no_reparse(run_contract_path)):
        raise ContractError("W10_PER_RUN_PREFLIGHT_PATH_UNSAFE", str(run))
    state, state_raw = _read_json(state_path, "LIVE_RUN_STATE_INVALID")
    contract, contract_raw = _read_json(contract_file, "LIVE_CONTRACT_INVALID")
    _run_contract, run_contract_raw = _read_json(run_contract_path, "LIVE_CONTRACT_INVALID")
    if contract_raw != run_contract_raw:
        raise ContractError("W10_PER_RUN_PREFLIGHT_BINDING_MISMATCH", "project and Run contract snapshots differ")
    value, evidence_raw = _read_json(evidence, "W10_PREFLIGHT_INVALID")
    if evidence_raw != evidence.read_bytes():
        raise ContractError("W10_PREFLIGHT_CHANGED_DURING_READ", str(evidence))

    contract_sha = hashlib.sha256(contract_raw).hexdigest()
    source = contract.get("source", {})
    unit = contract.get("unit", {})
    try:
        from .cnw_runner import WORKFLOW_PATH
    except ImportError:
        from cnw_runner import WORKFLOW_PATH
    policy_path = ROOT / "config/cnw_production_policy.json"
    if (policy_path.is_symlink() or not policy_path.is_file()
            or WORKFLOW_PATH.is_symlink() or not WORKFLOW_PATH.is_file()):
        raise ContractError("W10_POLICY_OR_WORKFLOW_UNAVAILABLE", "production policy or pinned workflow is unavailable")
    policy_raw = policy_path.read_bytes()
    workflow_raw = WORKFLOW_PATH.read_bytes()
    actual_policy_sha = hashlib.sha256(policy_raw).hexdigest()
    actual_workflow_sha = hashlib.sha256(workflow_raw).hexdigest()
    source_sha = (source.get("script_sha256") or source.get("source_file_sha256") or
                  source.get("source_revision_id") or source.get("import_id"))
    manifest_sha = (source.get("source_manifest_sha256") or
                    source.get("local_private_source_manifest_sha256"))
    workflow_sha = state.get("workflow_template_sha256")
    if unit.get("policy_sha256") != actual_policy_sha:
        raise ContractError("PRODUCTION_POLICY_IDENTITY_MISMATCH", "contract policy SHA differs from the installed policy")
    if workflow_sha != actual_workflow_sha:
        raise ContractError("CNW_METHOD_IDENTITY_MISMATCH", "Run workflow SHA differs from the pinned workflow")
    expected_identity = {
        "project_id": contract.get("project_id"),
        "run_id": state.get("run_id"),
        "work_id": unit.get("id"),
        "contract_sha256": contract_sha,
        "source_file_sha256": source_sha,
        "source_manifest_sha256": manifest_sha,
        "policy_sha256": unit.get("policy_sha256"),
        "workflow_template_sha256": workflow_sha,
    }
    recorded_identity = {key: value.get(key) for key in expected_identity}
    if (run.name != state.get("run_id") or project != run.parent.parent.resolve(strict=True)
            or state.get("project_id") not in {None, expected_identity["project_id"]}
            or state.get("contract_sha256") != contract_sha
            or any(expected is None or recorded_identity[key] != expected
                   for key, expected in expected_identity.items())):
        raise ContractError("W10_PER_RUN_PREFLIGHT_BINDING_MISMATCH", "project, run, contract, source, policy, or workflow differs")
    if (value.get("schema_version") != PER_RUN_PREFLIGHT_SCHEMA
            or value.get("status") != "ACCEPTED"
            or value.get("scope") != "W10_SINGLE_SCENE"
            or not isinstance(value.get("controller_acceptance_ref"), str)
            or not value["controller_acceptance_ref"].strip()
            or type(value.get("provider_call_authorized")) is not bool):
        raise ContractError("W10_PER_RUN_PREFLIGHT_REVIEW_INVALID", "accepted per-run review evidence is required")

    bound_files: list[tuple[Path, bytes]] = []

    def external_bound_file(path_key: str, sha_key: str, error_code: str) -> tuple[Path, bytes]:
        supplied = value.get(path_key)
        expected_sha = value.get(sha_key)
        if (not isinstance(supplied, str) or not supplied or not Path(supplied).is_absolute()
                or not isinstance(expected_sha, str)):
            raise ContractError(error_code, "path and SHA256 are required")
        bound = Path(supplied).absolute()
        if not _no_reparse(bound) or not bound.is_file():
            raise ContractError(error_code, str(bound))
        bound = bound.resolve(strict=True)
        raw = bound.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha.lower():
            raise ContractError(error_code, "SHA256 mismatch")
        bound_files.append((bound, raw))
        return bound, raw

    controller_evidence, controller_raw = external_bound_file(
        "controller_evidence_path", "controller_evidence_sha256", "W10_CONTROLLER_EVIDENCE_INVALID")
    if not (controller_evidence.is_relative_to(project) or not controller_evidence.is_relative_to(ROOT.resolve())):
        raise ContractError("W10_CONTROLLER_EVIDENCE_INVALID", "controller evidence must be in project or external private storage")
    controller_doc, _ = _read_json(controller_evidence, "W10_CONTROLLER_EVIDENCE_INVALID")
    if (controller_doc.get("schema_version") != "cnw_w10_controller_verdict_v1"
            or controller_doc.get("status") != "ACCEPTED"
            or controller_doc.get("scope") != "W10_SINGLE_SCENE"
            or controller_doc.get("controller_acceptance_ref") != value["controller_acceptance_ref"]
            or value.get("provider_call_authorized") is not False
            or controller_doc.get("provider_call_authorized") is not False):
        raise ContractError("W10_CONTROLLER_EVIDENCE_INVALID", "bound Controller verdict does not match the preflight")

    identity_path = project / "project_identity.json"
    identity_raw = None
    legacy_map_doc = None
    legacy_map_sha = None
    if identity_path.is_file():
        identity, identity_raw = _read_json(identity_path, "PROJECT_IDENTITY_INVALID")
        identity_sha = hashlib.sha256(identity_raw).hexdigest()
        if (value.get("identity_kind") != "NATIVE"
                or value.get("project_instance_id") != identity.get("project_instance_id")
                or value.get("project_identity_sha256") != identity_sha
                or identity.get("project_id") != expected_identity["project_id"]):
            raise ContractError("W10_PER_RUN_PREFLIGHT_IDENTITY_MISMATCH", "native project identity differs")
    else:
        map_path, _map_raw = external_bound_file(
            "legacy_identity_map_path", "legacy_identity_map_sha256", "W10_LEGACY_IDENTITY_MAP_INVALID")
        original_state_path, original_state_raw = external_bound_file(
            "original_run_state_path", "original_run_state_sha256", "W10_ORIGINAL_RUN_STATE_INVALID")
        if value.get("identity_kind") != "LEGACY_EXTERNAL_V1":
            raise ContractError("W10_PER_RUN_PREFLIGHT_IDENTITY_MISMATCH", "a missing native identity requires an external legacy map")
        try:
            from .legacy_source_path_map import validate_legacy_source_path_map
        except ImportError:
            from legacy_source_path_map import validate_legacy_source_path_map
        map_doc, _current_state, mapped_contract = validate_legacy_source_path_map(
            target_project_root=project, legacy_run_dir=run, manifest_path=map_path,
            expected_manifest_sha256=value["legacy_identity_map_sha256"],
            original_run_state_path=original_state_path)
        legacy_map_doc = map_doc
        legacy_map_sha = value["legacy_identity_map_sha256"].lower()
        target = map_doc.get("target_project", {})
        source_run = map_doc.get("source_run", {})
        if (target.get("project_id") != expected_identity["project_id"]
                or target.get("project_instance_id") != value.get("project_instance_id")
                or source_run.get("run_state_sha256") != hashlib.sha256(original_state_raw).hexdigest()
                or (mapped_contract.get("source", {}).get("source_manifest_sha256") or
                    mapped_contract.get("source", {}).get("local_private_source_manifest_sha256")) != manifest_sha):
            raise ContractError("W10_PER_RUN_PREFLIGHT_IDENTITY_MISMATCH", "legacy map does not bind the approved run and source")

    story = contract.get("story", {})
    work_intent = contract.get("work_intent")
    if not isinstance(work_intent, str) or not work_intent:
        work_intent = ("LEGACY_V1_INSERT_BETWEEN" if
            isinstance(story.get("before_anchor"), dict) and isinstance(story.get("after_anchor"), dict)
            else "LEGACY_V1")
    source_id = source.get("source_id") or source.get("import_id")
    source_revision_id = (source.get("source_revision_id") or source.get("source_file_sha256")
                          or source.get("script_sha256"))
    source_manifest_revision_sha = (source.get("source_manifest_revision_sha256") or manifest_sha)
    selection = story.get("source_selection")
    if work_intent == "ADAPT_SOURCE" and isinstance(selection, dict):
        selected_identity = selection
    elif work_intent in {"INSERT_BETWEEN", "LEGACY_V1_INSERT_BETWEEN"}:
        selected_identity = {key: story.get(key) for key in ("before_anchor", "after_anchor")}
    elif work_intent == "ORIGINAL_EPISODE":
        selected_identity = {key: story.get(key) for key in
            ("arc_ref", "canon_ref", "previous_episode_identity", "chapter_context") if key in story}
    else:
        selected_identity = None
    selected_span_or_anchor_sha = _canonical_sha256(selected_identity) if selected_identity else None
    if identity_raw is not None:
        source_root_identity = hashlib.sha256(identity_raw).hexdigest()
    else:
        target = legacy_map_doc.get("target_project", {}) if legacy_map_doc else {}
        source_root_identity = _canonical_sha256({"legacy_identity_map_sha256": legacy_map_sha,
            "legacy_project_root": target.get("legacy_project_root"),
            "project_id": target.get("project_id"),
            "project_instance_id": target.get("project_instance_id")})
    controller_bindings = {**expected_identity, "identity_kind": value.get("identity_kind"),
        "project_instance_id": value.get("project_instance_id"),
        "work_intent": work_intent,
        "source_id": source_id,
        "source_revision_id": source_revision_id,
        "source_manifest_revision_sha256": source_manifest_revision_sha,
        "source_root_identity": source_root_identity,
        "selected_span_or_anchor_sha": selected_span_or_anchor_sha,
        "reviewer_identity": value.get("reviewer_identity"),
        "controller_acceptance_ref": value.get("controller_acceptance_ref"),
        "provider_call_authorized": False}
    if value.get("identity_kind") == "LEGACY_EXTERNAL_V1":
        controller_bindings.update({"legacy_identity_map_sha256": value.get("legacy_identity_map_sha256"),
            "original_run_state_sha256": value.get("original_run_state_sha256")})
    if any(value.get(key) != expected for key, expected in controller_bindings.items()):
        raise ContractError("W10_PER_RUN_PREFLIGHT_BINDING_MISMATCH", "preflight does not bind the complete project/source review identity")
    if any(controller_doc.get(key) != expected for key, expected in controller_bindings.items()):
        raise ContractError("W10_CONTROLLER_EVIDENCE_INVALID", "Controller verdict is not bound to this project/Run identity")
    if (not isinstance(value.get("reviewer_identity"), str) or not value["reviewer_identity"].strip()
            or controller_doc.get("reviewer_identity") != value["reviewer_identity"]):
        raise ContractError("W10_CONTROLLER_EVIDENCE_INVALID", "independent reviewer identity is required")
    evidence_digest = _canonical_sha256(controller_bindings)
    if (value.get("evidence_digest") != evidence_digest
            or controller_doc.get("evidence_digest") != evidence_digest):
        raise ContractError("W10_CONTROLLER_EVIDENCE_INVALID", "review evidence digest differs from the bound identity")

    if (state_path.read_bytes() != state_raw or contract_file.read_bytes() != contract_raw
            or run_contract_path.read_bytes() != run_contract_raw
            or evidence.read_bytes() != evidence_raw or controller_evidence.read_bytes() != controller_raw
            or policy_path.read_bytes() != policy_raw or WORKFLOW_PATH.read_bytes() != workflow_raw
            or (identity_raw is not None and identity_path.read_bytes() != identity_raw)
            or any(bound.read_bytes() != raw for bound, raw in bound_files)):
        raise ContractError("W10_PER_RUN_PREFLIGHT_CHANGED_DURING_READ", run.name)
    return value, hashlib.sha256(evidence_raw).hexdigest()


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
