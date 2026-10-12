"""Preflight contracts for CNW scene and episode production.

This module validates frozen, source-bound project contracts. It does not
decide literary quality or infer beat coverage from prose.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


# Atom-06 tested consumer matrix. Lengths are normalized visible Unicode code
# points, not language-specific word counts. Larger work units are rejected
# until their provider-capacity behavior has a separate validated bound.
SUPPORTED_LOCALE_MATRIX = {
    "zh-CN": {"language_name": "简体中文", "length_unit": "unicode_visible_code_points"},
    "en-US": {"language_name": "English (United States)", "length_unit": "unicode_visible_code_points"},
}
VALIDATED_VISIBLE_CHARACTER_CAPACITIES = (4000, 4700)
MAX_VALIDATED_VISIBLE_CHARS_PER_UNIT = max(VALIDATED_VISIBLE_CHARACTER_CAPACITIES)
SUPPORT_INTEGRATION_STATES = {"DISABLED", "ENABLED"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_contract(path: str | Path) -> dict[str, Any]:
    contract_path = Path(path)
    try:
        value = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("CONTRACT_UNREADABLE", str(exc)) from exc
    if not isinstance(value, dict):
        raise ContractError("CONTRACT_INVALID", "contract root must be an object")
    return value


def check_required_fields(contract: dict[str, Any], required: list[str] | None = None) -> None:
    required = required or ["schema_version", "project_id", "source", "unit", "story", "review"]
    missing = [key for key in required if key not in contract or contract[key] in (None, "", [], {})]
    if missing:
        raise ContractError("PREFLIGHT_REQUIRED_FIELD_MISSING", ", ".join(missing))
    unit = contract.get("unit", {})
    for key in ("id", "kind", "language", "pov", "target_visible_chars", "min_visible_chars", "max_visible_chars", "policy_sha256"):
        if key not in unit or unit[key] in (None, "", []):
            code = "PREFLIGHT_TARGET_MISSING" if key == "target_visible_chars" else "PREFLIGHT_REQUIRED_FIELD_MISSING"
            raise ContractError(code, f"unit.{key} is required")
    story = contract.get("story", {})
    intent = contract.get("work_intent") if contract.get("schema_version") == "cnw_work_unit_v2" else None
    story_fields = ["role_in_story", "reader_reward", "entry_state", "exit_state", "required_beats", "characters_in_scene", "character_knowledge_boundary_ref", "forbidden_future_revelations", "voice_sample_refs"]
    if intent == "INSERT_BETWEEN":
        story_fields.extend(("before_anchor", "after_anchor"))
    elif intent == "ORIGINAL_EPISODE":
        story_fields.extend(("first_episode", "arc_ref"))
        if not story.get("first_episode"):
            story_fields.append("previous_episode_ref")
    elif intent == "ADAPT_SOURCE":
        story_fields.append("source_selection")
    elif intent is None:
        story_fields.extend(("before_anchor", "after_anchor"))
    else:
        raise ContractError("WORK_INTENT_UNSUPPORTED", str(intent))
    for key in story_fields:
        if key == "required_beats" and unit.get("planning_mode") == "author_plot":
            continue
        if key not in story or story[key] in (None, "", []):
            raise ContractError("PREFLIGHT_REQUIRED_FIELD_MISSING", f"story.{key} is required")
    for key in ("arc_ref", "previous_episode_ref"):
        if key in story:
            value = story[key]
            if (not isinstance(value, str) or not value.strip() or Path(value).anchor
                    or Path(value).drive or ".." in Path(value).parts or Path(value).suffix.lower() != ".md"):
                raise ContractError("PRODUCTION_CONTEXT_PATH_UNSAFE", f"story.{key} must be a project-relative Markdown path")
    if "first_episode" in story and not isinstance(story["first_episode"], bool):
        raise ContractError("PRODUCTION_CONTEXT_INVALID", "first_episode must be boolean")
    if story.get("first_episode") and story.get("previous_episode_ref"):
        raise ContractError("PRODUCTION_CONTEXT_INVALID", "first_episode conflicts with previous_episode_ref")


def _safe_source_file(source_root: str | Path, relative: str) -> Path:
    root = Path(source_root).resolve(strict=True)
    candidate = root / relative
    if candidate.is_symlink():
        raise ContractError("SOURCE_PATH_UNSAFE", "source file is a symlink")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ContractError("SOURCE_PATH_UNSAFE", "source path escapes source root or is not a file")
    for ancestor in [candidate, *candidate.parents]:
        if ancestor == root.parent:
            break
        if ancestor.is_symlink():
            raise ContractError("SOURCE_PATH_UNSAFE", "source path contains a symlink")
    return resolved


def validate_source_identity(
    contract: dict[str, Any],
    *,
    source_root: str | Path,
    expected_version: str,
    expected_zip_sha256: str,
    expected_manifest_sha256: str,
) -> None:
    source = contract.get("source", {})
    if contract.get("schema_version") == "cnw_work_unit_v2":
        validate_v2_source_identity(contract, source_root=source_root)
        return
    if source.get("identity_type") == "imported_project":
        if source.get("version") != expected_version or source.get("import_id") != expected_zip_sha256:
            raise ContractError("SOURCE_IDENTITY_MISMATCH", "imported source version or import ID differs")
        manifest_path = _safe_source_file(source_root, source.get("manifest_file", ""))
        if _sha256(manifest_path.read_bytes()) != expected_manifest_sha256.lower():
            snapshot = f"_INBOX/revisions/legacy-manifests/{expected_manifest_sha256.lower()}.json"
            try:
                manifest_path = _safe_source_file(source_root, snapshot)
            except (ContractError, OSError) as exc:
                raise ContractError("LEGACY_SOURCE_SNAPSHOT_MISSING", "the v1 contract's exact source-manifest bytes are unavailable") from exc
            if _sha256(manifest_path.read_bytes()) != expected_manifest_sha256.lower():
                raise ContractError("SOURCE_IDENTITY_MISMATCH", "exact imported source-manifest snapshot SHA256 differs")
        source_file = contract.get("story", {}).get("source_file")
        if not source_file:
            raise ContractError("SOURCE_IDENTITY_MISSING", "story.source_file is required")
        path = _safe_source_file(source_root, source_file)
        if _sha256(path.read_bytes()) != source.get("source_file_sha256", "").lower():
            raise ContractError("SOURCE_IDENTITY_MISMATCH", "imported source file SHA256 differs")
        _validate_story_anchors(contract, source_root, path)
        return
    if source.get("identity_type") is not None or "zip_sha256" not in source:
        raise ContractError("SOURCE_TYPE_UNSUPPORTED", str(source.get("identity_type")))
    if source.get("version") != expected_version or source.get("zip_sha256", "").lower() != expected_zip_sha256.lower():
        raise ContractError("SOURCE_IDENTITY_MISMATCH", "source version or release ZIP SHA256 differs")
    if source.get("local_private_source_manifest_sha256", "").lower() != expected_manifest_sha256.lower():
        raise ContractError("SOURCE_IDENTITY_MISMATCH", "private source manifest SHA256 differs")
    manifest_file = source.get("manifest_file")
    if not manifest_file:
        raise ContractError("SOURCE_IDENTITY_MISSING", "source.manifest_file is required")
    manifest_path = _safe_source_file(source_root, manifest_file)
    if _sha256(manifest_path.read_bytes()) != expected_manifest_sha256.lower():
        raise ContractError("SOURCE_IDENTITY_MISMATCH", "actual private source manifest SHA256 differs")
    unit = contract.get("unit", {})
    story = contract.get("story", {})
    source_file = story.get("source_file")
    if not source_file:
        raise ContractError("SOURCE_IDENTITY_MISSING", "story.source_file is required")
    path = _safe_source_file(source_root, source_file)
    data = path.read_bytes()
    if source.get("script_sha256", "").lower() != _sha256(data):
        raise ContractError("SOURCE_IDENTITY_MISMATCH", "script SHA256 differs")
    _validate_story_anchors(contract, source_root, path)
    if unit.get("id") is None:
        raise ContractError("PREFLIGHT_REQUIRED_FIELD_MISSING", "unit.id is required")


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    """Resolve an RFC 6901 pointer without coercion or first-match behavior."""
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ContractError("SOURCE_JSON_POINTER_INVALID", "JSON Pointer must be a non-root absolute pointer")
    current = document
    for encoded in pointer[1:].split("/"):
        if re.search(r"~(?![01])", encoded):
            raise ContractError("SOURCE_JSON_POINTER_INVALID", "invalid JSON Pointer escape")
        part = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if part not in current:
                raise ContractError("SOURCE_JSON_POINTER_MISSING", pointer)
            current = current[part]
        elif isinstance(current, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", part) or int(part) >= len(current):
                raise ContractError("SOURCE_JSON_POINTER_MISSING", pointer)
            current = current[int(part)]
        else:
            raise ContractError("SOURCE_JSON_POINTER_MISSING", pointer)
    return current


def _strict_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("SOURCE_JSON_DUPLICATE_KEY", key)
        result[key] = value
    return result


def validate_v2_source_identity(contract: dict[str, Any], *, source_root: str | Path) -> None:
    source = contract.get("source", {})
    if not isinstance(source, dict) or not isinstance(contract.get("story"), dict):
        raise ContractError("CONTRACT_INVALID", "v2 source and story must be objects")
    intent = contract.get("work_intent")
    origin = source.get("source_origin")
    root = Path(source_root).resolve(strict=True)
    identity_path = _safe_source_file(root, "project_identity.json")
    try:
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("PROJECT_INSTANCE_ID_REQUIRED", "registered project identity is unreadable") from exc
    if not isinstance(identity, dict):
        raise ContractError("PROJECT_INSTANCE_ID_REQUIRED", "registered project identity must be an object")
    instance_id = identity.get("project_instance_id")
    if (instance_id != source.get("project_instance_id") or
            instance_id != contract.get("project_instance_id") or
            identity.get("project_id") != contract.get("project_id")):
        raise ContractError("PROJECT_INSTANCE_IDENTITY_MISMATCH", "contract identity differs from the registered project")
    if "input_pack" in contract:
        try:
            from .cnw_input_pack import validate_input_pack_binding
        except ImportError:
            from cnw_input_pack import validate_input_pack_binding
        validate_input_pack_binding(root, contract["input_pack"], contract=contract)
    story = contract["story"]
    if intent != "ORIGINAL_EPISODE" and ("arc_ref" in story or "arc_sha256" in story):
        arc_ref, arc_sha = story.get("arc_ref"), story.get("arc_sha256")
        if not isinstance(arc_ref, str) or not isinstance(arc_sha, str):
            raise ContractError("PROJECT_CONTEXT_IDENTITY_MISMATCH", "explicit Arc requires its frozen SHA256")
        if _sha256(_safe_source_file(root, arc_ref).read_bytes()) != arc_sha:
            raise ContractError("PROJECT_CONTEXT_IDENTITY_MISMATCH", "selected Arc bytes differ from the work contract")
    if intent == "ORIGINAL_EPISODE":
        story = contract["story"]
        if origin != "ORIGINAL_PROJECT" or any(key in story for key in ("source_file", "before_anchor", "after_anchor")):
            raise ContractError("SOURCE_TYPE_UNSUPPORTED", "original work cannot fabricate source files or anchors")
        if source.get("source_file_sha256") or source.get("source_manifest_sha256"):
            raise ContractError("SOURCE_TYPE_UNSUPPORTED", "original work cannot claim an imported source identity")
        arc_ref, arc_sha = story.get("arc_ref"), story.get("arc_sha256")
        if not isinstance(arc_ref, str) or not isinstance(arc_sha, str):
            raise ContractError("PRE_FLIGHT_MISSING_PROJECT_INPUT", "story.arc_ref and story.arc_sha256 are required")
        arc_path = _safe_source_file(root, arc_ref)
        if _sha256(arc_path.read_bytes()) != arc_sha.lower():
            raise ContractError("PROJECT_CONTEXT_IDENTITY_MISMATCH", "selected Arc bytes differ from the work contract")
        if story.get("first_episode") is True:
            if story.get("previous_episode_ref") or story.get("previous_episode_sha256"):
                raise ContractError("PRODUCTION_CONTEXT_INVALID", "first episode cannot claim a previous episode")
        elif story.get("first_episode") is False:
            previous_ref, previous_sha = story.get("previous_episode_ref"), story.get("previous_episode_sha256")
            if not isinstance(previous_ref, str) or not isinstance(previous_sha, str):
                raise ContractError("PREVIOUS_EPISODE_REFERENCE_REQUIRED", contract.get("unit", {}).get("id", ""))
            previous_path = _safe_source_file(root, previous_ref)
            if _sha256(previous_path.read_bytes()) != previous_sha.lower():
                raise ContractError("PREVIOUS_EPISODE_IDENTITY_MISMATCH", previous_ref)
        else:
            raise ContractError("PRODUCTION_CONTEXT_INVALID", "first_episode must be explicitly true or false")
        return
    if intent not in {"INSERT_BETWEEN", "ADAPT_SOURCE"}:
        raise ContractError("WORK_INTENT_UNSUPPORTED", str(intent))
    if origin != "IMPORTED_PROJECT":
        raise ContractError("SOURCE_TYPE_UNSUPPORTED", str(origin))
    manifest_rel = source.get("manifest_file")
    if not isinstance(manifest_rel, str):
        raise ContractError("SOURCE_IDENTITY_MISSING", "source.manifest_file is required")
    manifest_path = _safe_source_file(root, manifest_rel)
    manifest_raw = manifest_path.read_bytes()
    manifest_sha = _sha256(manifest_raw)
    if manifest_sha != str(source.get("source_manifest_sha256", "")).lower():
        raise ContractError("SOURCE_IDENTITY_MISMATCH", "source manifest revision SHA256 differs")
    try:
        manifest = json.loads(manifest_raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("SOURCE_MANIFEST_INVALID", "source revision is not valid UTF-8 JSON") from exc
    if not isinstance(manifest, dict):
        raise ContractError("SOURCE_MANIFEST_INVALID", "source-manifest root must be an object")
    if manifest.get("schema_version") != "cnw_source_manifest_v2":
        raise ContractError("SOURCE_MANIFEST_INVALID", "v2 contract requires an immutable v2 source manifest")
    if manifest.get("project_id") != contract.get("project_id"):
        raise ContractError("SOURCE_IDENTITY_MISMATCH", "source manifest belongs to a different project")
    if source.get("manifest_revision_sha256") != manifest_sha:
        raise ContractError("SOURCE_IDENTITY_MISMATCH", "manifest revision identity differs")
    index_rel = source.get("source_index_file")
    index_expected = source.get("source_index_sha256")
    if not isinstance(index_rel, str) or not isinstance(index_expected, str):
        raise ContractError("SOURCE_INDEX_REVISION_REQUIRED", "contract must freeze an immutable source-index revision")
    index_path = _safe_source_file(root, index_rel)
    index_raw = index_path.read_bytes()
    if _sha256(index_raw) != index_expected.lower():
        raise ContractError("SOURCE_IDENTITY_MISMATCH", "source-index revision SHA256 differs")
    try:
        source_index = json.loads(index_raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("SOURCE_INDEX_INVALID", "source-index revision is not valid JSON") from exc
    if not isinstance(source_index, dict):
        raise ContractError("SOURCE_INDEX_INVALID", "source-index root must be an object")
    if (source_index.get("schema_version") != "cnw_source_index_v2" or
            source_index.get("project_id") != contract.get("project_id") or
            source_index.get("manifest_revision_sha256") != manifest_sha):
        raise ContractError("SOURCE_IDENTITY_MISMATCH", "source-index does not bind the selected manifest revision")
    manifest_sources = manifest.get("sources")
    index_sources = source_index.get("source_revisions")
    if (not isinstance(manifest_sources, list) or not all(isinstance(entry, dict) for entry in manifest_sources) or
            not isinstance(index_sources, list) or not all(isinstance(entry, dict) for entry in index_sources)):
        raise ContractError("SOURCE_MANIFEST_INVALID", "source manifest and index require object entry lists")
    matches = [item for item in manifest_sources
               if item.get("source_id") == source.get("source_id") and
               item.get("source_revision_id") == source.get("source_revision_id")]
    if len(matches) != 1:
        raise ContractError("SOURCE_SELECTION_INVALID", "source identity is absent or ambiguous in the frozen manifest")
    item = matches[0]
    indexed = [entry for entry in index_sources
               if entry.get("source_id") == source.get("source_id") and
               entry.get("source_revision_id") == source.get("source_revision_id")]
    if len(indexed) != 1 or indexed[0].get("stored_path") != item.get("stored_path"):
        raise ContractError("SOURCE_SELECTION_INVALID", "selected source is absent or ambiguous in the frozen source index")
    source_path = item.get("stored_path")
    if (item.get("sha256") != source.get("source_revision_id") or
            not isinstance(source_path, str) or
            source_path != contract.get("story", {}).get("source_file")):
        raise ContractError("SOURCE_IDENTITY_MISMATCH", "selected source path or byte identity differs")
    raw_path = _safe_source_file(root, source_path)
    raw = raw_path.read_bytes()
    if _sha256(raw) != source.get("source_revision_id"):
        raise ContractError("SOURCE_IDENTITY_MISMATCH", "selected source bytes differ")
    if intent == "INSERT_BETWEEN":
        _validate_story_anchors(contract, root, raw_path)
        before, after = contract["story"]["before_anchor"], contract["story"]["after_anchor"]
        if before.get("source_line_end", before["source_line"]) >= after["source_line"]:
            raise ContractError("SOURCE_ANCHOR_INVALID", "before anchor must precede after anchor")
    else:
        selection = contract["story"].get("source_selection")
        if not isinstance(selection, dict):
            raise ContractError("SOURCE_SELECTION_REQUIRED", "ADAPT_SOURCE needs an explicit source span")
        if selection.get("source_id") != source.get("source_id") or selection.get("source_revision_id") != source.get("source_revision_id"):
            raise ContractError("SOURCE_SELECTION_INVALID", "selection does not bind the selected source revision")
        if item.get("format") == "json":
            try:
                parsed = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_strict_json_object)
            except (UnicodeError, json.JSONDecodeError, ContractError) as exc:
                raise ContractError("SOURCE_JSON_INVALID", "selected JSON source cannot be parsed") from exc
            value = resolve_json_pointer(parsed, selection.get("json_pointer"))
            if value in (None, "", [], {}):
                raise ContractError("SOURCE_SPAN_EMPTY", "JSON Pointer must select a non-empty value")
            selected_bytes = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            expected_format = "json_pointer_canonical_value_sha256"
            canonical_digest = _sha256(selected_bytes)
            wire_excerpt = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
            if (selection.get("canonical_selected_value_sha256") != canonical_digest or
                    selection.get("wire_excerpt_sha256") != _sha256(wire_excerpt)):
                raise ContractError("SOURCE_WIRE_EXCERPT_HASH_MISMATCH",
                                    "canonical selected-value and actual Plot excerpt hashes must be recorded separately")
        elif item.get("format") in {"md", "txt"}:
            start, end = selection.get("start_line"), selection.get("end_line")
            lines = raw.splitlines(keepends=True)
            if (not isinstance(start, int) or isinstance(start, bool) or
                    not isinstance(end, int) or isinstance(end, bool) or
                    start < 1 or end < start or end > len(lines)):
                raise ContractError("SOURCE_SPAN_INVALID", "text source span must be a non-empty valid line range")
            selected_bytes = b"".join(lines[start - 1:end])
            if not selected_bytes.decode("utf-8-sig").strip():
                raise ContractError("SOURCE_SPAN_EMPTY", "text span must contain non-whitespace source text")
            expected_format = "raw_line_span_sha256"
        else:
            raise ContractError("SOURCE_TYPE_UNSUPPORTED", str(item.get("format")))
        if selection.get("hash_semantics") != expected_format or selection.get("selected_sha256") != _sha256(selected_bytes):
            raise ContractError("SOURCE_SPAN_HASH_MISMATCH", "selected source span identity differs")


def _validate_story_anchors(contract: dict[str, Any], source_root: str | Path, path: Path) -> None:
    story = contract.get("story", {})
    data = path.read_bytes()
    for field in ("before_anchor", "after_anchor"):
        anchor = story.get(field, {})
        if not isinstance(anchor, dict):
            raise ContractError("SOURCE_ANCHOR_INVALID", f"{field} must be an object")
        start = anchor.get("source_line")
        end = anchor.get("source_line_end", start)
        expected = anchor.get("sha256", "")
        if (not isinstance(start, int) or isinstance(start, bool) or
                not isinstance(end, int) or isinstance(end, bool) or
                start < 1 or end < start or
                not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected)):
            raise ContractError("SOURCE_ANCHOR_INVALID", f"{field} requires source_line, optional source_line_end and sha256")
        lines = data.splitlines(keepends=True)
        if end > len(lines):
            raise ContractError("SOURCE_ANCHOR_MISMATCH", f"{field} exceeds source line count")
        actual = _sha256(b"".join(lines[start - 1 : end]))
        if actual != expected.lower():
            raise ContractError("SOURCE_ANCHOR_MISMATCH", f"{field} SHA256 differs")


def validate_scene_budget(contract: dict[str, Any]) -> None:
    unit = contract.get("unit", {})
    target, minimum, maximum = (unit.get(k) for k in ("target_visible_chars", "min_visible_chars", "max_visible_chars"))
    if target in (None, 0):
        raise ContractError("PREFLIGHT_TARGET_MISSING", "target_visible_chars must be positive")
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in (target, minimum, maximum)):
        raise ContractError("SCENE_BUDGET_INVALID", "target/min/max must be integers")
    if minimum < 1 or minimum > target or target > maximum:
        raise ContractError("SCENE_BUDGET_INVALID", "require 1 <= min <= target <= max")
    beats = contract.get("story", {}).get("required_beats", [])
    if unit.get("planning_mode") == "author_plot":
        if not isinstance(beats, list):
            raise ContractError("REQUIRED_BEAT_INVALID", "optional assignment requirements must be a list")
        ids = set()
        for beat in beats:
            if (not isinstance(beat, dict) or not isinstance(beat.get("beat_id"), str)
                    or not beat["beat_id"].strip() or beat["beat_id"] in ids
                    or not isinstance(beat.get("goal"), str) or not beat["goal"].strip()):
                raise ContractError("REQUIRED_BEAT_INVALID", "assignment requirements need unique IDs and goals")
            ids.add(beat["beat_id"])
        return
    if not isinstance(beats, list) or not beats:
        raise ContractError("REQUIRED_BEATS_MISSING", "at least one required beat is needed")
    ids: set[str] = set()
    total = 0
    for beat in beats:
        beat_id = beat.get("beat_id") if isinstance(beat, dict) else None
        budget = beat.get("budget_visible_chars") if isinstance(beat, dict) else None
        if not beat_id or beat_id in ids:
            raise ContractError("REQUIRED_BEAT_INVALID", "beat IDs must be present and unique")
        if not isinstance(budget, int) or isinstance(budget, bool) or budget <= 0:
            raise ContractError("SCENE_BUDGET_INVALID", f"beat {beat_id} needs a positive character budget")
        ids.add(beat_id)
        total += budget
    if total != target:
        raise ContractError("SCENE_BUDGET_SUM_MISMATCH", f"beat budgets sum to {total}, target is {target}")


def validate_episode_budget(episode: dict[str, Any]) -> None:
    if episode.get("planning_mode") == "author_plot":
        validate_scene_budget({"unit": episode, "story": {}})
        return
    target = episode.get("chapter_target_visible_chars")
    scenes = episode.get("scenes")
    if not isinstance(target, int) or target <= 0 or not isinstance(scenes, list) or not scenes:
        raise ContractError("EPISODE_BUDGET_INVALID", "positive chapter target and scenes are required")
    ids: set[str] = set()
    total = 0
    for scene in scenes:
        scene_id = scene.get("id")
        budget = scene.get("target_visible_chars")
        if not scene_id or scene_id in ids or not isinstance(budget, int) or budget <= 0:
            raise ContractError("EPISODE_BUDGET_INVALID", "scene IDs must be unique and budgets positive")
        ids.add(scene_id)
        total += budget
    if total != target:
        raise ContractError("EPISODE_BUDGET_SUM_MISMATCH", f"scene budgets sum to {total}, episode target is {target}")


def validate_work_unit(contract: dict[str, Any]) -> None:
    """Validate scope and length without requiring Plot's design in advance."""
    unit = contract["unit"]
    if unit.get("planning_mode") not in (None, "author_plot", "legacy_frozen"):
        raise ContractError("PLANNING_MODE_INVALID", str(unit["planning_mode"]))
    if unit.get("kind") == "scene":
        validate_scene_budget(contract)
    elif unit.get("kind") == "episode":
        validate_episode_budget(unit)
        if unit.get("planning_mode") == "author_plot":
            validate_scene_budget(contract)
    else:
        raise ContractError("WORK_UNIT_KIND_INVALID", str(unit.get("kind")))
    if contract.get("schema_version") == "cnw_work_unit_v2":
        locale = unit.get("language_locale", unit.get("language"))
        if locale not in SUPPORTED_LOCALE_MATRIX:
            raise ContractError("LOCALE_UNSUPPORTED", str(locale))
        if unit.get("language") != locale:
            raise ContractError("LOCALE_CONFIGURATION_MISMATCH", "unit.language and unit.language_locale must identify the same locale")
        if unit.get("length_metric") != SUPPORTED_LOCALE_MATRIX[locale]["length_unit"]:
            raise ContractError("LENGTH_METRIC_UNSUPPORTED", str(unit.get("length_metric")))
        if unit.get("max_visible_chars", MAX_VALIDATED_VISIBLE_CHARS_PER_UNIT + 1) > MAX_VALIDATED_VISIBLE_CHARS_PER_UNIT:
            raise ContractError("UNIT_CAPACITY_UNVALIDATED", f"maximum supported work-unit length is {MAX_VALIDATED_VISIBLE_CHARS_PER_UNIT} visible characters")
        integrations = contract.get("integrations", {"nk": "DISABLED", "critics": "DISABLED"})
        if not isinstance(integrations, dict):
            raise ContractError("SUPPORT_INTEGRATION_CONFIG_INVALID", "integrations must be an object")
        for name in ("nk", "critics"):
            if integrations.get(name, "DISABLED") not in SUPPORT_INTEGRATION_STATES:
                raise ContractError("SUPPORT_INTEGRATION_CONFIG_INVALID", f"integrations.{name} must be DISABLED or ENABLED")


_MARKDOWN_CONTROL = re.compile(r"```|`|^\s{0,3}#{1,6}\s+|^\s*>\s?|^\s*[-*+]\s+|^\s*\d+[.)]\s+|(?<!\\)(?:\*\*|__|~~|\*|_)", re.MULTILINE)


def validate_work_unit_policy(contract: dict[str, Any]) -> dict | None:
    """Validate a V2 unit against its own registered immutable app policy.

    Current installation changes must not reinterpret a historical contract.
    V1 retains its separately pinned policy and recovery behavior.
    """
    if contract.get("schema_version") != "cnw_work_unit_v2":
        return None
    try:
        try:
            from .policy_snapshots import resolve_contract_app_policy, PolicySnapshotError
        except ImportError:
            from policy_snapshots import resolve_contract_app_policy, PolicySnapshotError
        return resolve_contract_app_policy(contract)
    except PolicySnapshotError as exc:
        raise ContractError(exc.code, str(exc)) from exc


def visible_char_metrics(text: str) -> dict[str, int | str]:
    normalized = unicodedata.normalize("NFC", text)
    with_link_labels = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", normalized)
    plain = _MARKDOWN_CONTROL.sub("", with_link_labels)
    visible = [ch for ch in plain if not ch.isspace()]
    return {
        "algorithm": "NFC; remove fenced/inline code and Markdown heading, quote, list markers; exclude whitespace; count remaining Unicode code points.",
        "visible_chars": len(visible),
        "han_chars": sum("CJK UNIFIED IDEOGRAPH" in unicodedata.name(ch, "") for ch in visible),
        "punctuation_chars": sum(unicodedata.category(ch).startswith("P") for ch in visible),
        "dialogue_paragraphs": sum(line.lstrip().startswith(("**", "「", "『")) for line in normalized.splitlines() if line.strip()),
        "action_narration_paragraphs": sum(bool(line.strip()) and not line.lstrip().startswith(("**", "「", "『", "#", "- ", ">")) for line in normalized.splitlines()),
    }


def count_visible_chars(text: str) -> int:
    return int(visible_char_metrics(text)["visible_chars"])


def validate_output_length(contract: dict[str, Any], text: str) -> dict[str, Any]:
    metrics = visible_char_metrics(text)
    unit = contract.get("unit", {})
    minimum = unit.get("min_visible_chars")
    maximum = unit.get("max_visible_chars")
    if not isinstance(minimum, int) or not isinstance(maximum, int):
        raise ContractError("PREFLIGHT_TARGET_MISSING", "min/max visible character range is required")
    actual = int(metrics["visible_chars"])
    if actual < minimum:
        raise ContractError("RETURN_UNDERPRODUCED", f"{actual} visible characters is below minimum {minimum}")
    if actual > maximum:
        raise ContractError("RETURN_OVER_LIMIT", f"{actual} visible characters exceeds maximum {maximum}")
    return metrics


def check_required_beats(contract: dict[str, Any], evidence: dict[str, str]) -> None:
    missing = [b["beat_id"] for b in contract.get("story", {}).get("required_beats", []) if not evidence.get(b["beat_id"], "").strip()]
    if missing:
        raise ContractError("RETURN_MISSING_BEAT", ", ".join(missing))


def assert_output_within_root(root: str | Path, relative: str) -> Path:
    base = Path(root).resolve()
    candidate = base / relative
    if candidate.is_symlink():
        raise ContractError("OUTPUT_PATH_UNSAFE", "output target is a symlink")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(base):
        raise ContractError("OUTPUT_PATH_UNSAFE", "output path escapes root")
    cursor = candidate
    while cursor != base and cursor != cursor.parent:
        if cursor.is_symlink():
            raise ContractError("OUTPUT_PATH_UNSAFE", "output path contains a symlink")
        cursor = cursor.parent
    return candidate
