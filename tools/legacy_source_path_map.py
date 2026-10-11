"""Read-only, explicitly pinned path migration for historical run evidence.

Migration maps live outside Git. A caller must select the destination project,
the original run directory, and the exact map SHA256 before any legacy key is
resolved. Legacy key strings are lookup tokens only and are never opened.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import uuid
from pathlib import Path
from typing import Any

try:
    from .cnw_contract import ContractError
    from .project_paths import resolve_project
except ImportError:  # direct script execution
    from cnw_contract import ContractError
    from project_paths import resolve_project

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "legacy_source_path_map_v1"
EXTERNAL_SCHEMA_VERSION = "legacy_source_path_map_external_v1"
LEGACY_EXTERNAL_ID_NAMESPACE = uuid.UUID("fc242318-55f7-5a78-b39b-c0b8c18be39e")
CATEGORIES = (
    "V5_PROJECT_ORIGINALS",
    "J19_RELEASE_ROOTS",
    "CRITICS_RUNS_AND_NK_EVIDENCE",
    "GLOBAL_LEDGER_AND_DEPENDENCIES",
    "REPOSITORY_PROJECT_AND_WORKSPACE",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _no_reparse(path: Path) -> bool:
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            return True
        except OSError:
            return False
        attributes = getattr(info, "st_file_attributes", 0)
        if stat.S_ISLNK(info.st_mode) or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            return False
    return True


def _safe_project_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\x00" in relative:
        raise ContractError("LEGACY_SOURCE_MAP_INVALID", "mapped path must be a non-empty project-relative path")
    candidate = Path(relative)
    if (candidate.is_absolute() or candidate.drive or "\\" in relative or
            any(part in {"..", ".", ""} for part in relative.split("/"))):
        raise ContractError("LEGACY_SOURCE_MAP_INVALID", f"unsafe mapped path: {relative}")
    current = root
    for part in candidate.parts:
        current = current / part
        if current.exists() and not _no_reparse(current):
            raise ContractError("LEGACY_SOURCE_MAP_PATH_UNSAFE", relative)
    try:
        resolved = current.resolve(strict=True)
    except OSError as exc:
        raise ContractError("LEGACY_SOURCE_SNAPSHOT_MISSING", relative) from exc
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ContractError("LEGACY_SOURCE_MAP_PATH_UNSAFE", relative)
    return resolved


def _safe_relative_token(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ContractError("LEGACY_SOURCE_MAP_INVALID", f"{field} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or path.drive or "\\" in value or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ContractError("LEGACY_SOURCE_MAP_INVALID", f"{field} is not a safe relative path")
    return value


def _required_sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ContractError("LEGACY_SOURCE_MAP_INVALID", f"{field} must be a lowercase SHA256")
    return value


def _read_json_object(path: Path, code: str) -> tuple[dict, bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContractError(code, str(path)) from exc
    if not isinstance(value, dict):
        raise ContractError(code, "JSON root must be an object")
    return value, raw


def legacy_external_project_instance_id(*, project_root: str | Path, project_id: str,
                                        run_id: str, contract_sha256: str,
                                        source_manifest_sha256: str) -> str:
    """Derive an explicitly external identity for a historical project without an identity file."""
    root = Path(project_root).resolve(strict=True)
    canonical_root = str(root).replace("/", "\\").casefold()
    binding = "\0".join((canonical_root, project_id, run_id,
                         contract_sha256.lower(), source_manifest_sha256.lower()))
    return str(uuid.uuid5(LEGACY_EXTERNAL_ID_NAMESPACE, binding))


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def validate_legacy_source_path_map(
    *,
    target_project_root: str | Path,
    legacy_run_dir: str | Path,
    manifest_path: str | Path,
    expected_manifest_sha256: str,
) -> tuple[dict, dict, dict]:
    """Validate map, target registration, and unchanged historical run bytes."""
    requested_root = Path(target_project_root).absolute()
    requested_run = Path(legacy_run_dir).absolute()
    if not _no_reparse(requested_root) or not _no_reparse(requested_run):
        raise ContractError("LEGACY_RUN_PATH_UNSAFE", "project or selected run contains a link/reparse point")
    root = requested_root.resolve(strict=True)
    run_dir = requested_run.resolve(strict=True)
    map_path = Path(manifest_path).absolute()
    if not _SHA256.fullmatch(expected_manifest_sha256 or ""):
        raise ContractError("LEGACY_SOURCE_MAP_SHA_REQUIRED", "explicit map SHA256 is required")
    if not _no_reparse(map_path) or not map_path.is_file():
        raise ContractError("LEGACY_SOURCE_MAP_PATH_UNSAFE", str(map_path))
    if map_path.resolve(strict=True).is_relative_to(ROOT.resolve()):
        raise ContractError("LEGACY_SOURCE_MAP_MUST_BE_EXTERNAL", str(map_path))

    state_path = run_dir / "run_state.json"
    contract_path = run_dir / "artifacts" / "contract.json"
    if not _no_reparse(state_path) or not _no_reparse(contract_path):
        raise ContractError("LEGACY_RUN_PATH_UNSAFE", str(run_dir))
    state, state_raw = _read_json_object(state_path, "LEGACY_RUN_STATE_INVALID")
    contract, contract_raw = _read_json_object(contract_path, "LEGACY_CONTRACT_INVALID")
    map_doc, map_raw = _read_json_object(map_path, "LEGACY_SOURCE_MAP_INVALID")
    if sha256_bytes(map_raw) != expected_manifest_sha256:
        raise ContractError("LEGACY_SOURCE_MAP_SHA_MISMATCH", str(map_path))

    schema_version = map_doc.get("schema_version")
    if schema_version not in {SCHEMA_VERSION, EXTERNAL_SCHEMA_VERSION} or not isinstance(map_doc.get("map_id"), str) or not map_doc["map_id"].strip():
        raise ContractError("LEGACY_SOURCE_MAP_VERSION_UNSUPPORTED", str(map_doc.get("schema_version")))
    target = map_doc.get("target_project")
    source_run = map_doc.get("source_run")
    implementation = map_doc.get("legacy_implementation")
    categories = map_doc.get("categories")
    if not all(isinstance(item, dict) for item in (target, source_run, implementation, categories)):
        raise ContractError("LEGACY_SOURCE_MAP_INVALID", "target, source_run, implementation, and categories are required")

    source_manifest_sha = (contract.get("source", {}).get("source_manifest_sha256") or
                           contract.get("source", {}).get("local_private_source_manifest_sha256"))
    if source_manifest_sha is not None:
        _required_sha(source_manifest_sha, "contract source manifest SHA256")
    if (source_run.get("run_id") != state.get("run_id") or run_dir.name != state.get("run_id") or
            source_run.get("run_state_sha256") != sha256_bytes(state_raw) or
            state.get("contract_sha256") != sha256_bytes(contract_raw) or
            source_run.get("contract_path_in_run") != "artifacts/contract.json" or
            source_run.get("contract_sha256") != sha256_bytes(contract_raw) or
            source_run.get("source_manifest_sha256") != source_manifest_sha):
        raise ContractError("LEGACY_SOURCE_MAP_RUN_IDENTITY_MISMATCH", "source run, contract, or manifest identity differs")

    identity_path = root / "project_identity.json"
    if schema_version == SCHEMA_VERSION:
        if not _no_reparse(identity_path) or not identity_path.is_file():
            raise ContractError("PROJECT_INSTANCE_ID_REQUIRED", "v1 maps require a registered target project")
        registration = resolve_project(root, data_home=root.parent.parent)
        identity, identity_raw = _read_json_object(identity_path, "PROJECT_INSTANCE_ID_REQUIRED")
        if (target.get("project_id") != identity.get("project_id") or
                target.get("project_instance_id") != identity.get("project_instance_id") or
                registration.get("project_id") != identity.get("project_id") or
                registration.get("project_instance_id") != identity.get("project_instance_id") or
                target.get("project_identity_sha256") != sha256_bytes(identity_raw)):
            raise ContractError("PROJECT_INSTANCE_IDENTITY_MISMATCH", "migration map is bound to another target project")
    else:
        if identity_path.exists():
            raise ContractError("LEGACY_EXTERNAL_IDENTITY_CONFLICT", "external legacy mapping cannot override a native identity file")
        recorded_root = target.get("legacy_project_root")
        canonical_target_root = str(root).replace("/", "\\").casefold()
        contract_sha = sha256_bytes(contract_raw)
        project_id = contract.get("project_id")
        binding = target.get("legacy_identity_binding")
        derived_id = legacy_external_project_instance_id(project_root=root,
            project_id=project_id if isinstance(project_id, str) else "",
            run_id=state.get("run_id", ""), contract_sha256=contract_sha,
            source_manifest_sha256=source_manifest_sha or "")
        if (not isinstance(project_id, str) or not project_id.strip() or
                not isinstance(recorded_root, str) or recorded_root.replace("/", "\\").casefold() != canonical_target_root or
                target.get("identity_kind") != "LEGACY_EXTERNAL_V1" or
                target.get("project_id") != project_id or target.get("project_instance_id") != derived_id or
                not isinstance(binding, dict) or binding.get("run_id") != state.get("run_id") or
                binding.get("contract_sha256") != contract_sha or
                binding.get("source_manifest_sha256") != source_manifest_sha or
                binding.get("run_state_sha256") != sha256_bytes(state_raw)):
            raise ContractError("LEGACY_EXTERNAL_IDENTITY_BINDING_MISMATCH", "external identity must bind this root, run, contract, and source manifest")

    source = contract.get("source", {})
    source_sha = (source.get("script_sha256") or source.get("source_file_sha256") or
                  source.get("source_revision_id"))
    if source_sha:
        source_sha = _required_sha(source_sha.lower(), "contract source file SHA256")
        source_key = source_run.get("source_file_legacy_key")
        manifest_key = source_run.get("source_manifest_legacy_key")
        if not isinstance(source_key, str) or not source_key.startswith("source:"):
            raise ContractError("LEGACY_SOURCE_MAP_INVALID", "source_file_legacy_key is required")
        if not isinstance(manifest_key, str) or not manifest_key.startswith("manifest:"):
            raise ContractError("LEGACY_SOURCE_MAP_INVALID", "source_manifest_legacy_key is required")
        manifest_sha = _required_sha(source_manifest_sha or "", "contract source manifest SHA256")
        entries_by_key = {item.get("legacy_key"): item
                          for record in categories.values() if isinstance(record, dict)
                          for item in record.get("entries", []) if isinstance(item, dict)}
        if (source_key not in entries_by_key or entries_by_key[source_key].get("sha256") != source_sha or
                manifest_key not in entries_by_key or entries_by_key[manifest_key].get("sha256") != manifest_sha):
            raise ContractError("LEGACY_SOURCE_MAP_RUN_IDENTITY_MISMATCH", "mapped source or manifest does not match the v1 contract")

    if schema_version == EXTERNAL_SCHEMA_VERSION:
        if (implementation.get("status") != "UNRECORDED" or implementation.get("commit_sha") is not None or
                implementation.get("code_files") != [] or implementation.get("policy_files") != [] or
                not isinstance(implementation.get("reason"), str) or not implementation["reason"].strip()):
            raise ContractError("LEGACY_SOURCE_MAP_INVALID", "external maps must explicitly preserve an unrecorded application build identity")
    else:
        code_files = implementation.get("code_files")
        policy_files = implementation.get("policy_files")
        code_commit = implementation.get("commit_sha")
        if (not isinstance(code_files, list) or not code_files or not isinstance(policy_files, list) or not policy_files or
                not isinstance(code_commit, str) or not re.fullmatch(r"[0-9a-f]{40,64}", code_commit)):
            raise ContractError("LEGACY_SOURCE_MAP_INVALID", "legacy code commit and code/policy identities are required")
        for group, label in ((code_files, "code_files"), (policy_files, "policy_files")):
            for item in group:
                if not isinstance(item, dict):
                    raise ContractError("LEGACY_SOURCE_MAP_INVALID", f"{label} entries must be objects")
                relative = _safe_relative_token(item.get("path"), f"{label}.path")
                expected = _required_sha(item.get("sha256"), f"{label}.sha256")
                try:
                    shown = subprocess.run(["git", "show", f"{code_commit}:{relative}"], cwd=ROOT,
                        capture_output=True, check=False, timeout=20)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    raise ContractError("LEGACY_IMPLEMENTATION_IDENTITY_UNAVAILABLE", relative) from exc
                if shown.returncode != 0 or sha256_bytes(shown.stdout) != expected:
                    raise ContractError("LEGACY_IMPLEMENTATION_IDENTITY_MISMATCH", str(relative))

    if set(categories) != set(CATEGORIES):
        raise ContractError("LEGACY_SOURCE_MAP_CATEGORIES_INCOMPLETE", ", ".join(CATEGORIES))
    all_keys = set()
    for category in CATEGORIES:
        record = categories[category]
        if not isinstance(record, dict) or record.get("status") not in {"MAPPED", "UNAVAILABLE"}:
            raise ContractError("LEGACY_SOURCE_MAP_INVALID", category)
        entries = record.get("entries")
        if not isinstance(entries, list):
            raise ContractError("LEGACY_SOURCE_MAP_INVALID", f"{category}.entries must be a list")
        if record["status"] == "UNAVAILABLE":
            if (entries or not isinstance(record.get("reason"), str) or not record["reason"].strip() or
                    not isinstance(record.get("evidence_ref"), str) or not record["evidence_ref"].strip()):
                raise ContractError("LEGACY_SOURCE_MAP_INVALID", f"{category} unavailable state needs reason, evidence_ref, and no entries")
            continue
        if not entries:
            raise ContractError("LEGACY_SOURCE_MAP_INVALID", f"{category} mapped state needs entries")
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("legacy_key"), str) or not entry["legacy_key"]:
                raise ContractError("LEGACY_SOURCE_MAP_INVALID", f"{category} entry requires an exact legacy_key")
            if not isinstance(entry.get("source_type"), str) or not entry["source_type"]:
                raise ContractError("LEGACY_SOURCE_MAP_INVALID", f"{category} entry requires source_type")
            _safe_relative_token(entry.get("legacy_relative_path"), f"{category}.legacy_relative_path")
            if entry["legacy_key"] in all_keys:
                raise ContractError("LEGACY_SOURCE_MAP_INVALID", "legacy keys must be globally unique across categories")
            all_keys.add(entry["legacy_key"])
            relative = entry.get("target_project_relative_path")
            expected = _required_sha(entry.get("sha256"), f"{category}.sha256")
            destination = _safe_project_file(root, relative)
            raw = destination.read_bytes()
            if (sha256_bytes(raw) != expected or type(entry.get("bytes")) is not int or
                    entry["bytes"] != len(raw)):
                raise ContractError("LEGACY_SOURCE_SNAPSHOT_MISSING", relative)
    identity_raw = identity_path.read_bytes() if schema_version == SCHEMA_VERSION else None
    if (sha256_bytes(state_path.read_bytes()) != sha256_bytes(state_raw) or
            sha256_bytes(contract_path.read_bytes()) != sha256_bytes(contract_raw) or
            (identity_raw is not None and sha256_bytes(identity_path.read_bytes()) != sha256_bytes(identity_raw))):
        raise ContractError("LEGACY_RUN_MUTATED_DURING_READ", str(run_dir))
    if sha256_bytes(map_path.read_bytes()) != sha256_bytes(map_raw):
        raise ContractError("LEGACY_SOURCE_MAP_CHANGED_DURING_READ", str(map_path))
    return map_doc, state, contract


def resolve_legacy_mapped_file(
    *,
    target_project_root: str | Path,
    legacy_run_dir: str | Path,
    manifest_path: str | Path,
    expected_manifest_sha256: str,
    category: str,
    legacy_key: str,
    expected_file_sha256: str,
) -> Path:
    if category not in CATEGORIES:
        raise ContractError("LEGACY_SOURCE_TYPE_UNSUPPORTED", category)
    expected_file_sha256 = _required_sha(expected_file_sha256, "expected_file_sha256")
    map_doc, _state, _contract = validate_legacy_source_path_map(
        target_project_root=target_project_root,
        legacy_run_dir=legacy_run_dir,
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256)
    record = map_doc["categories"][category]
    if record["status"] == "UNAVAILABLE":
        raise ContractError("LEGACY_SOURCE_CATEGORY_UNAVAILABLE", category)
    matches = [entry for entry in record["entries"] if entry.get("legacy_key") == legacy_key]
    if len(matches) != 1:
        raise ContractError("LEGACY_SOURCE_MAP_ENTRY_MISSING", legacy_key)
    entry = matches[0]
    if entry.get("sha256") != expected_file_sha256:
        raise ContractError("SOURCE_IDENTITY_MISMATCH", legacy_key)
    root = Path(target_project_root).resolve(strict=True)
    path = _safe_project_file(root, entry.get("target_project_relative_path"))
    if sha256_bytes(path.read_bytes()) != expected_file_sha256:
        raise ContractError("LEGACY_SOURCE_SNAPSHOT_MISSING", entry.get("target_project_relative_path"))
    return path


def resolve_legacy_key(
    *,
    target_project_root: str | Path,
    legacy_run_dir: str | Path,
    manifest_path: str | Path,
    expected_manifest_sha256: str,
    legacy_key: str,
    expected_file_sha256: str,
) -> Path:
    """Resolve one historical key by exact token across the five disjoint maps."""
    map_doc, _state, _contract = validate_legacy_source_path_map(
        target_project_root=target_project_root,
        legacy_run_dir=legacy_run_dir,
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256)
    categories = [name for name, record in map_doc["categories"].items()
                  if any(item.get("legacy_key") == legacy_key for item in record.get("entries", []))]
    if len(categories) != 1:
        if not categories and any(record.get("status") == "UNAVAILABLE"
                                  for record in map_doc["categories"].values()):
            raise ContractError("LEGACY_SOURCE_CATEGORY_UNAVAILABLE", legacy_key)
        raise ContractError("LEGACY_SOURCE_MAP_ENTRY_MISSING", legacy_key)
    record = map_doc["categories"][categories[0]]
    if record["status"] == "UNAVAILABLE":
        raise ContractError("LEGACY_SOURCE_CATEGORY_UNAVAILABLE", categories[0])
    entry = next(item for item in record["entries"] if item.get("legacy_key") == legacy_key)
    if entry.get("sha256") != _required_sha(expected_file_sha256, "expected_file_sha256"):
        raise ContractError("SOURCE_IDENTITY_MISMATCH", legacy_key)
    path = _safe_project_file(Path(target_project_root).resolve(strict=True), entry.get("target_project_relative_path"))
    if sha256_bytes(path.read_bytes()) != expected_file_sha256:
        raise ContractError("LEGACY_SOURCE_SNAPSHOT_MISSING", entry.get("target_project_relative_path"))
    return path
