"""Content-addressed, read-only policy and identity snapshot resolver.

This module is an Atom-02 shadow facility. Legacy production consumers keep
reading their existing files until their later migration atoms are accepted.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

try:
    from .cnw_contract import MAX_VALIDATED_VISIBLE_CHARS_PER_UNIT, SUPPORTED_LOCALE_MATRIX, VALIDATED_VISIBLE_CHARACTER_CAPACITIES
except ImportError:
    from cnw_contract import MAX_VALIDATED_VISIBLE_CHARS_PER_UNIT, SUPPORTED_LOCALE_MATRIX, VALIDATED_VISIBLE_CHARACTER_CAPACITIES

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = ROOT / "config" / "policy_snapshots"
INDEX_NAME = "index.v1.json"
INDEX_SCHEMA = "storystudio_policy_snapshot_index_v1"
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
PROJECT_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
POLICY_KIND_ALIASES = {
    "legacy_production_config": "legacy_combined_production_config",
    "project_policy_template": "project_policy",
}

METHOD_STAGES = (
    "plot", "scene_cards", "writing_brief", "prose", "lint_layer1",
    "lint_layer2", "multi_lens_review", "adversarial_verify",
    "completeness_critic", "refine", "re_review",
)
METHOD_LENSES = ("style", "character", "plot", "canon", "story_specific")
METHOD_VERIFIERS = {"verifier_count": 3, "refute_default": True, "threshold": 2}
METHOD_SPRINT = {"size": 5, "min_score": 75, "max_p0_findings": 0, "max_p1_findings": 2}
WORK_CONTRACT_REQUIREMENTS = {
    "required_scene_fields": ["source", "unit", "story", "review"],
    "required_story_fields": [
        "role_in_story", "reader_reward", "entry_state", "exit_state", "before_anchor",
        "after_anchor", "required_beats", "characters_in_scene",
        "character_knowledge_boundary_ref", "forbidden_future_revelations", "voice_sample_refs",
    ],
    "require_exact_beat_budget_sum": True,
}
CNW_METHOD_REFERENCE = {
    "repository": "MintoTsukino/claude-novel-workflow",
    "commit": "97ad71fe5e5e76a82275c6c63d4add06fb60ab6e",
    "workflow_template_blob": "146ea01a484cc0578cf290478b3941599ad7fb15",
    "local_reference_manifest_sha256": "E9B989C52C66AB9BE8C73F09E84BC5BD7D2ECC92F9F1CBFC61BA300DC6CD3983",
}
PROJECT_REQUIRED_FIELDS = (
    "project_id", "language.locale", "language.length_unit", "language.length_semantics", "writing.target_length",
    "writing.minimum_length", "writing.maximum_length", "arc", "canon",
    "characters", "world", "voice", "forbidden_phrases", "review.fifth_lens.id",
    "review.fifth_lens.responsibility", "sources",
)
_FORBIDDEN_PROJECT_OVERRIDES = {
    "method", "workflow", "stages", "lenses", "verifiers", "verifier_count",
    "refute_default", "threshold", "sprint", "method_reference", "per_unit_stages", "lens_ids",
}
_PROJECT_KEYS = {
    "schema_version", "project_id", "display_name", "language", "writing", "arc", "canon",
    "characters", "world", "voice", "forbidden_phrases", "review", "sources", "integrations", "execution",
}


def _contains_forbidden_override(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(_FORBIDDEN_PROJECT_OVERRIDES.intersection(value)) or any(_contains_forbidden_override(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_override(child) for child in value)
    return False


class PolicySnapshotError(ValueError):
    def __init__(self, code: str, message: str, *, sha256: str | None = None):
        self.code = code
        self.sha256 = sha256
        super().__init__(f"{code}: {message}")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _policy_kind(document: dict[str, Any]) -> str:
    schema = document.get("schema_version")
    if schema == "storystudio_app_policy_v1":
        return "app_policy"
    if schema == "storystudio_provider_policy_v1":
        return "provider_policy"
    if schema == "storystudio_project_policy_v1":
        return "project_policy"
    if schema == "cnw_production_policy_v1":
        return "legacy_project_policy"
    if document.get("plan_version") == "P2" and isinstance(document.get("provider"), dict):
        return "legacy_combined_production_config"
    raise PolicySnapshotError("POLICY_SCHEMA_UNSUPPORTED", "unknown policy schema")


def _get_path(value: dict[str, Any], dotted_path: str) -> Any:
    current: Any = value
    for part in dotted_path.split("."):
        current = current.get(part) if isinstance(current, dict) else None
    return current


def project_preflight_missing(policy: dict[str, Any]) -> list[str]:
    """List real project inputs still needed before a writing run can start."""
    missing = []
    for field in PROJECT_REQUIRED_FIELDS:
        value = _get_path(policy, field)
        if value is None or value == "":
            missing.append(field)
    writing = policy.get("writing") if isinstance(policy.get("writing"), dict) else {}
    for field in ("target_length", "minimum_length", "maximum_length"):
        if type(writing.get(field)) is not int or writing[field] <= 0:
            dotted = f"writing.{field}"
            if dotted not in missing:
                missing.append(dotted)
    locale = _get_path(policy, "language.locale")
    if locale not in SUPPORTED_LOCALE_MATRIX:
        missing.append("language.locale_supported")
    elif _get_path(policy, "language.length_unit") != SUPPORTED_LOCALE_MATRIX[locale]["length_unit"]:
        missing.append("language.length_unit_supported")
    maximum = writing.get("maximum_length")
    if type(maximum) is int and maximum > MAX_VALIDATED_VISIBLE_CHARS_PER_UNIT:
        missing.append("writing.maximum_length_supported")
    if all(type(writing.get(key)) is int for key in ("minimum_length", "target_length", "maximum_length")):
        if not writing["minimum_length"] <= writing["target_length"] <= writing["maximum_length"]:
            missing.append("writing.length_range_consistency")
    for field in ("arc", "canon", "world", "voice"):
        value = policy.get(field)
        if not isinstance(value, dict) or value.get("status") not in {"APPROVED", "CONFIRMED"} or not value.get("reference"):
            missing.append(f"{field}.approved_reference")
    if not isinstance(policy.get("characters"), list):
        missing.append("characters.explicit_list")
    if not isinstance(policy.get("forbidden_phrases"), list):
        missing.append("forbidden_phrases.explicit_list")
    if not isinstance(policy.get("sources"), list):
        missing.append("sources.explicit_registry")
    lens = _get_path(policy, "review.fifth_lens")
    if not isinstance(lens, dict) or not lens.get("id") or not lens.get("responsibility"):
        missing.append("review.fifth_lens.actual_duties")
    return sorted(set(missing))


def validate_policy_document(document: Any, *, expected_kind: str | None = None) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise PolicySnapshotError("POLICY_DOCUMENT_INVALID", "policy root must be a JSON object")
    kind = _policy_kind(document)
    if expected_kind and kind != expected_kind:
        raise PolicySnapshotError("POLICY_KIND_MISMATCH", f"expected {expected_kind}; received {kind}")
    if kind in {"legacy_project_policy", "legacy_combined_production_config"}:
        return {"kind": kind, "compatibility": "LEGACY_READ_ONLY", "missing_project_inputs": []}
    if kind == "app_policy":
        method = document.get("method")
        expected = {
            "per_unit_stages": list(METHOD_STAGES),
            "lens_ids": list(METHOD_LENSES),
            "adversarial": METHOD_VERIFIERS,
            "sprint": METHOD_SPRINT,
        }
        if method != expected:
            raise PolicySnapshotError("METHOD_CONTRACT_MISMATCH", "app policy weakens or changes the pinned CNW author method")
        if document.get("work_contract_requirements") != WORK_CONTRACT_REQUIREMENTS:
            raise PolicySnapshotError("METHOD_CONTRACT_MISMATCH", "app policy weakens or changes the pinned work-contract structure")
        if document.get("method_reference") != CNW_METHOD_REFERENCE:
            raise PolicySnapshotError("METHOD_REFERENCE_MISMATCH", "app policy does not identify the pinned CNW source and captured reference")
        defaults = document.get("installation_defaults", {})
        if (defaults.get("live_authorization") is not False or
                defaults.get("project_required_for_writes") is not True or
                defaults.get("provider_override_requires_registered_adapter") is not True or
                defaults.get("unconfigured_project_fields_are_errors") is not True):
            raise PolicySnapshotError("LIVE_DEFAULT_MUST_BE_CLOSED", "new installation must require an explicit project, adapter, and authorization")
        compatibility = document.get("execution_compatibility", {})
        if (compatibility.get("tested_locales") != sorted(SUPPORTED_LOCALE_MATRIX) or
                type(compatibility.get("maximum_validated_visible_characters_per_unit")) is not int or
                compatibility.get("maximum_validated_visible_characters_per_unit") not in VALIDATED_VISIBLE_CHARACTER_CAPACITIES):
            raise PolicySnapshotError("EXECUTION_COMPATIBILITY_UNVERIFIED", "locale/capacity claims must match the Atom-06 tested matrix")
        safety = document.get("safety", {})
        if (safety.get("max_in_flight") != 5 or safety.get("missing_usage") != "UNKNOWN_NOT_ZERO" or
                safety.get("reservation_before_send") is not True or safety.get("settlement_after_response") is not True or
                safety.get("campaign_limit_inheritance") is not False or
                safety.get("allow_output_without_frozen_work_contract") is not False or
                safety.get("method_fields_project_override_allowed") is not False or
                safety.get("method_fields_provider_override_allowed") is not False):
            raise PolicySnapshotError("APP_SAFETY_POLICY_INVALID", "app safety defaults do not match the protected execution contract")
        paths = document.get("path_policy", {})
        if (paths.get("data_home_must_be_explicit_or_user_selected") is not True or
                paths.get("project_identity_is_instance_scoped") is not True or
                paths.get("project_writes_require_registered_project") is not True):
            raise PolicySnapshotError("APP_PATH_POLICY_INVALID", "project writes must require an explicitly registered project")
        return {"kind": kind, "compatibility": "SHADOW_V1", "missing_project_inputs": []}
    if kind == "provider_policy":
        adapter = document.get("adapter_id")
        if adapter != "deepseek_flash":
            raise PolicySnapshotError("PROVIDER_ADAPTER_UNSUPPORTED", "only the implemented deepseek_flash adapter is supported")
        if (document.get("model") != "deepseek-flash" or
                document.get("base_url") != "https://api.deepseek.com/v1" or
                document.get("key_environment_variable") != "DEEPSEEK_API_KEY"):
            raise PolicySnapshotError("PROVIDER_POLICY_INVALID", "DeepSeek Flash model, endpoint, and key environment name must match the implemented adapter")
        request = document.get("request_policy")
        if (not isinstance(request, dict) or type(request.get("max_in_flight")) is not int or
                not 1 <= request["max_in_flight"] <= 5 or request.get("sdk_max_retries") != 0 or
                request.get("network_extra_attempts") != 2 or request.get("format_repair_extra_attempts") != 1 or
                request.get("thinking") != "disabled" or request.get("read_timeout_seconds") != 180 or
                request.get("output_tokens") != "derive_from_provider_capability_and_work_unit_requirements"):
            raise PolicySnapshotError("PROVIDER_POLICY_INVALID", "provider concurrency and retry settings do not match the implemented adapter")
        pricing = document.get("pricing")
        if (not isinstance(pricing, dict) or pricing.get("currency") != "CNY" or
                pricing.get("price_source") != "official_current_pricing_at_execution" or
                pricing.get("missing_usage") != "UNKNOWN_NOT_ZERO"):
            raise PolicySnapshotError("PROVIDER_POLICY_INVALID", "provider pricing and missing-usage rules do not match the accounting contract")
        accounting = document.get("accounting")
        if (not isinstance(accounting, dict) or accounting.get("reserve_before_send") is not True or
                accounting.get("settle_after_response") is not True or
                accounting.get("persist_across_run_ids") is not True or
                accounting.get("auto_top_up") is not False or
                accounting.get("new_project_inherits_historical_campaign_limit") is not False):
            raise PolicySnapshotError("PROVIDER_POLICY_INVALID", "provider accounting must preserve reserve/send/settle and prevent historical cap inheritance")
        if ("method" in document or "workflow" in document or "project_id" in document or
                _contains_forbidden_override(document)):
            raise PolicySnapshotError("PROVIDER_POLICY_SCOPE_INVALID", "provider policy cannot own method or project settings")
        if document.get("supported_project_override_ids") != ["deepseek_flash"]:
            raise PolicySnapshotError("PROVIDER_ADAPTER_UNSUPPORTED", "provider override registry must list only the implemented adapter")
        return {"kind": kind, "compatibility": "SHADOW_V1", "missing_project_inputs": []}
    if kind == "project_policy":
        if _contains_forbidden_override(document):
            raise PolicySnapshotError("PROJECT_METHOD_OVERRIDE_FORBIDDEN", "project policy cannot override the pinned author method")
        if document.get("schema_version") != "storystudio_project_policy_v1":
            raise PolicySnapshotError("POLICY_SCHEMA_UNSUPPORTED", "unsupported project policy version")
        if set(document) - _PROJECT_KEYS:
            raise PolicySnapshotError("PROJECT_POLICY_FIELD_UNSUPPORTED", "project policy contains fields outside the versioned schema")
        project_id = document.get("project_id")
        if project_id is not None and (not isinstance(project_id, str) or not PROJECT_ID_RE.fullmatch(project_id)):
            raise PolicySnapshotError("PROJECT_POLICY_INVALID", "project_id must be a short safe display label")
        override = _get_path(document, "execution.provider_override")
        if override not in (None, "deepseek_flash"):
            raise PolicySnapshotError("PROVIDER_ADAPTER_UNSUPPORTED", "project override is not an implemented adapter")
        live = _get_path(document, "execution.live_authorization")
        if type(live) is not bool:
            raise PolicySnapshotError("PROJECT_POLICY_INVALID", "live_authorization must be explicit true or false")
        if live:
            execution = document.get("execution", {})
            if not execution.get("authorization_ref"):
                raise PolicySnapshotError("PROJECT_LIVE_AUTHORIZATION_INCOMPLETE", "live use needs an explicit authorization reference")
            mode = execution.get("campaign_limit_mode")
            cap = execution.get("campaign_limit_cny")
            if mode == "bounded":
                if isinstance(cap, bool) or not isinstance(cap, (int, float)) or cap <= 0:
                    raise PolicySnapshotError("PROJECT_LIVE_AUTHORIZATION_INCOMPLETE", "bounded live use needs its own positive campaign cap")
            elif mode == "unlimited_explicit":
                if cap is not None:
                    raise PolicySnapshotError("PROJECT_LIVE_AUTHORIZATION_INCOMPLETE", "explicit unlimited mode must not also set a numeric cap")
            else:
                raise PolicySnapshotError("PROJECT_LIVE_AUTHORIZATION_INCOMPLETE", "live use needs an explicit bounded or unlimited budget decision")
        return {"kind": kind, "compatibility": "SHADOW_V1", "missing_project_inputs": project_preflight_missing(document)}
    raise PolicySnapshotError("POLICY_SCHEMA_UNSUPPORTED", "unknown policy schema")


class SnapshotStore:
    """Append-only SHA-256 byte store. Resolution never repairs or writes files."""

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root)
        self.objects = self.root / "objects" / "sha256"
        self.index_path = self.root / INDEX_NAME

    def _read_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"schema_version": INDEX_SCHEMA, "entries": []}
        try:
            value = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PolicySnapshotError("SNAPSHOT_INDEX_INVALID", "snapshot index is unreadable") from exc
        if not isinstance(value, dict) or value.get("schema_version") != INDEX_SCHEMA or not isinstance(value.get("entries"), list):
            raise PolicySnapshotError("SNAPSHOT_INDEX_INVALID", "snapshot index schema is invalid")
        return value

    @contextmanager
    def _index_lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        lock = self.root / ".index.lock"
        try:
            with lock.open("x", encoding="ascii") as stream:
                stream.write(f"pid={os.getpid()}\n")
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as exc:
            raise PolicySnapshotError("SNAPSHOT_INDEX_BUSY", "snapshot index is locked; recover stale locks explicitly") from exc
        try:
            yield
        finally:
            try:
                lock.unlink()
            except FileNotFoundError:
                pass

    def put_bytes(self, raw: bytes, *, kind: str, source_ref: str, expected_sha256: str | None = None) -> str:
        digest = sha256_bytes(raw)
        if expected_sha256 is not None and digest != expected_sha256.lower():
            raise PolicySnapshotError("SNAPSHOT_SOURCE_HASH_MISMATCH", "source bytes do not match the declared identity", sha256=expected_sha256)
        if not kind or not source_ref or ".." in Path(source_ref).parts:
            raise PolicySnapshotError("SNAPSHOT_METADATA_INVALID", "kind and a non-traversing source reference are required", sha256=digest)
        self.objects.mkdir(parents=True, exist_ok=True)
        object_path = self.objects / f"{digest}.blob"
        try:
            with object_path.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            if sha256_bytes(object_path.read_bytes()) != digest:
                raise PolicySnapshotError("SNAPSHOT_OBJECT_CORRUPT", "existing content-addressed object failed verification", sha256=digest)
        with self._index_lock():
            index = self._read_index()
            entries = index["entries"]
            matches = [item for item in entries if item.get("sha256") == digest]
            if matches:
                if len(matches) != 1:
                    raise PolicySnapshotError("SNAPSHOT_INDEX_INVALID", "duplicate SHA entries are not allowed", sha256=digest)
                entry = matches[0]
                if entry.get("availability") not in {"AVAILABLE", "LEGACY_SNAPSHOT_MISSING"}:
                    raise PolicySnapshotError("SNAPSHOT_INDEX_INVALID", "unknown availability value", sha256=digest)
                entry["availability"] = "AVAILABLE"
                entry.pop("reason_code", None)
                entry.pop("reason", None)
                entry["kinds"] = sorted(set(entry.get("kinds", [])) | {kind})
                entry["source_refs"] = sorted(set(entry.get("source_refs", [])) | {source_ref})
            else:
                entries.append({"sha256": digest, "availability": "AVAILABLE", "kinds": [kind], "source_refs": [source_ref]})
            entries.sort(key=lambda item: item["sha256"])
            self._write_index(index)
        return digest

    def mark_legacy_missing(self, digest: str, *, kind: str, source_ref: str, reason: str) -> None:
        if not SHA256_RE.fullmatch(digest.lower()):
            raise PolicySnapshotError("SNAPSHOT_SHA_INVALID", "expected a lowercase SHA-256 identity", sha256=digest)
        digest = digest.lower()
        with self._index_lock():
            index = self._read_index()
            entries = index["entries"]
            matches = [item for item in entries if item.get("sha256") == digest]
            if matches:
                if matches[0].get("availability") == "AVAILABLE":
                    return
                entry = matches[0]
                entry["kinds"] = sorted(set(entry.get("kinds", [])) | {kind})
                entry["source_refs"] = sorted(set(entry.get("source_refs", [])) | {source_ref})
            else:
                entry = {"sha256": digest, "availability": "LEGACY_SNAPSHOT_MISSING", "kinds": [kind], "source_refs": [source_ref], "reason_code": "LEGACY_MIGRATION_REQUIRED", "reason": reason}
                entries.append(entry)
            entries.sort(key=lambda item: item["sha256"])
            self._write_index(index)

    def _write_index(self, index: dict[str, Any]) -> None:
        raw = (json.dumps(index, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        fd, name = tempfile.mkstemp(prefix=".index-", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.index_path)
        finally:
            try:
                os.unlink(name)
            except FileNotFoundError:
                pass

    def resolve_snapshot_by_sha(self, digest: str, *, expected_kind: str | None = None) -> dict[str, Any]:
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise PolicySnapshotError("SNAPSHOT_SHA_INVALID", "expected a lowercase SHA-256 identity", sha256=str(digest))
        index = self._read_index()
        matches = [item for item in index["entries"] if item.get("sha256") == digest]
        if len(matches) != 1:
            raise PolicySnapshotError("SNAPSHOT_NOT_FOUND", "no unique registered snapshot has this SHA-256", sha256=digest)
        entry = matches[0]
        if expected_kind and expected_kind not in entry.get("kinds", []):
            raise PolicySnapshotError("SNAPSHOT_KIND_MISMATCH", f"snapshot is not registered as {expected_kind}", sha256=digest)
        if entry.get("availability") == "LEGACY_SNAPSHOT_MISSING":
            raise PolicySnapshotError("LEGACY_MIGRATION_REQUIRED", entry.get("reason", "historical bytes are unavailable"), sha256=digest)
        object_path = self.objects / f"{digest}.blob"
        try:
            raw = object_path.read_bytes()
        except OSError as exc:
            raise PolicySnapshotError("SNAPSHOT_OBJECT_MISSING", "registered snapshot object cannot be read", sha256=digest) from exc
        if sha256_bytes(raw) != digest:
            raise PolicySnapshotError("SNAPSHOT_HASH_MISMATCH", "content-addressed snapshot failed SHA-256 verification", sha256=digest)
        return {"sha256": digest, "kinds": entry.get("kinds", []), "source_refs": entry.get("source_refs", []), "bytes": raw}

    def resolve_policy_by_sha(self, digest: str, *, expected_kind: str | None = None) -> dict[str, Any]:
        resolved = self.resolve_snapshot_by_sha(digest, expected_kind=expected_kind)
        try:
            document = json.loads(resolved["bytes"].decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PolicySnapshotError("POLICY_DOCUMENT_INVALID", "snapshot is not valid UTF-8 JSON", sha256=digest) from exc
        classified_kind = _policy_kind(document) if isinstance(document, dict) else None
        normalized_expected = POLICY_KIND_ALIASES.get(expected_kind, expected_kind)
        validation = validate_policy_document(document, expected_kind=normalized_expected or classified_kind)
        return {**resolved, "document": document, "validation": validation}


def resolve_policy_by_sha(digest: str, *, store: str | os.PathLike[str] = DEFAULT_STORE, expected_kind: str | None = None) -> dict[str, Any]:
    """Resolve and verify one policy by immutable content SHA; this never writes."""
    return SnapshotStore(store).resolve_policy_by_sha(digest, expected_kind=expected_kind)


def resolve_contract_app_policy(contract: dict[str, Any], *, store: str | os.PathLike[str] = DEFAULT_STORE) -> dict[str, Any]:
    """Read the registered policy bound by a contract, never the current pointer."""
    if contract.get("schema_version") != "cnw_work_unit_v2":
        raise PolicySnapshotError("POLICY_CONTRACT_VERSION_UNSUPPORTED", "this resolver requires a V2 work contract")
    unit = contract.get("unit", {})
    digest = unit.get("policy_sha256")
    if not isinstance(digest, str):
        raise PolicySnapshotError("POLICY_IDENTITY_MISSING", "contract must bind an immutable application policy")
    resolved = resolve_policy_by_sha(digest.lower(), store=store, expected_kind="app_policy")
    maximum = unit.get("max_visible_chars")
    capacity = resolved["document"]["execution_compatibility"]["maximum_validated_visible_characters_per_unit"]
    if type(maximum) is not int or maximum < 1:
        raise PolicySnapshotError("SCENE_BUDGET_INVALID", "contract must have an explicit positive maximum")
    if maximum > capacity:
        raise PolicySnapshotError("UNIT_CAPACITY_UNVALIDATED", f"bound policy supports at most {capacity} visible characters", sha256=resolved["sha256"])
    return resolved


def compose_policy_bundle(
    app_policy_sha256: str,
    provider_policy_sha256: str,
    project_policy_sha256: str,
    *,
    store: str | os.PathLike[str] = DEFAULT_STORE,
) -> dict[str, Any]:
    resolver = SnapshotStore(store)
    app = resolver.resolve_policy_by_sha(app_policy_sha256, expected_kind="app_policy")
    provider = resolver.resolve_policy_by_sha(provider_policy_sha256, expected_kind="provider_policy")
    project = resolver.resolve_policy_by_sha(project_policy_sha256, expected_kind="project_policy")
    selected_adapter = _get_path(project["document"], "execution.provider_override") or provider["document"]["adapter_id"]
    if selected_adapter != provider["document"]["adapter_id"]:
        raise PolicySnapshotError("PROVIDER_ADAPTER_UNSUPPORTED", "selected project adapter has no matching implemented provider policy")
    missing = project["validation"]["missing_project_inputs"]
    return {
        "status": "PRE_FLIGHT_MISSING_PROJECT_INPUT" if missing else "POLICY_BUNDLE_READY",
        "app_policy_sha256": app_policy_sha256,
        "provider_policy_sha256": provider_policy_sha256,
        "project_policy_sha256": project_policy_sha256,
        "project_id": project["document"].get("project_id"),
        "provider_adapter_id": selected_adapter,
        "live_authorization": project["document"]["execution"]["live_authorization"],
        "execution_compatibility": "NOT_VALIDATED_BY_ATOM_02",
        "missing_project_inputs": missing,
    }
