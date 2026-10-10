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
    for key in ("role_in_story", "reader_reward", "entry_state", "exit_state", "before_anchor", "after_anchor", "required_beats", "characters_in_scene", "character_knowledge_boundary_ref", "forbidden_future_revelations", "voice_sample_refs"):
        if key not in story or story[key] in (None, "", []):
            raise ContractError("PREFLIGHT_REQUIRED_FIELD_MISSING", f"story.{key} is required")


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
    if source.get("identity_type") == "imported_project":
        if source.get("version") != expected_version or source.get("import_id") != expected_zip_sha256:
            raise ContractError("SOURCE_IDENTITY_MISMATCH", "imported source version or import ID differs")
        manifest_path = _safe_source_file(source_root, source.get("manifest_file", ""))
        if _sha256(manifest_path.read_bytes()) != expected_manifest_sha256.lower():
            raise ContractError("SOURCE_IDENTITY_MISMATCH", "actual imported source manifest SHA256 differs")
        source_file = contract.get("story", {}).get("source_file")
        if not source_file:
            raise ContractError("SOURCE_IDENTITY_MISSING", "story.source_file is required")
        path = _safe_source_file(source_root, source_file)
        if _sha256(path.read_bytes()) != source.get("source_file_sha256", "").lower():
            raise ContractError("SOURCE_IDENTITY_MISMATCH", "imported source file SHA256 differs")
        _validate_story_anchors(contract, source_root, path)
        return
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


def _validate_story_anchors(contract: dict[str, Any], source_root: str | Path, path: Path) -> None:
    story = contract.get("story", {})
    data = path.read_bytes()
    for field in ("before_anchor", "after_anchor"):
        anchor = story.get(field, {})
        start = anchor.get("source_line")
        end = anchor.get("source_line_end", start)
        expected = anchor.get("sha256", "").lower()
        if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start or not expected:
            raise ContractError("SOURCE_ANCHOR_INVALID", f"{field} requires source_line, optional source_line_end and sha256")
        lines = data.splitlines(keepends=True)
        if end > len(lines):
            raise ContractError("SOURCE_ANCHOR_MISMATCH", f"{field} exceeds source line count")
        actual = _sha256(b"".join(lines[start - 1 : end]))
        if actual != expected:
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


_MARKDOWN_CONTROL = re.compile(r"```|`|^\s{0,3}#{1,6}\s+|^\s*>\s?|^\s*[-*+]\s+|^\s*\d+[.)]\s+|(?<!\\)(?:\*\*|__|~~|\*|_)", re.MULTILINE)


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
