"""Private, source-preserving import tools for new CNW projects.

Raw staging preserves originals and marks unclassified passages TODO_CONFIRM.
The semantic Workflow 01/02 entry points classify directly stated facts,
inferences and open questions through the pinned author method.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from .cnw_contract import ContractError, _safe_source_file, assert_output_within_root, check_required_fields, resolve_json_pointer, validate_scene_budget, validate_source_identity, validate_v2_source_identity, validate_work_unit
except ImportError:  # direct script execution
    from cnw_contract import ContractError, _safe_source_file, assert_output_within_root, check_required_fields, resolve_json_pointer, validate_scene_budget, validate_source_identity, validate_v2_source_identity, validate_work_unit

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,63}\Z")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def project_directory(workspace_root: str | Path, project_id: str) -> Path:
    if not PROJECT_ID.fullmatch(project_id):
        raise ContractError("PROJECT_ID_INVALID", project_id)
    root = Path(workspace_root).resolve()
    private_workspace = (ROOT / "workspace").resolve()
    if not root.is_relative_to(private_workspace):
        raise ContractError("WORKSPACE_ROOT_OUTSIDE_PRIVATE_AREA", str(root))
    destination = (root / project_id).resolve()
    if not destination.is_relative_to(root):
        raise ContractError("PROJECT_PATH_UNSAFE", project_id)
    return destination


def init_project(workspace_root: str | Path, project_id: str) -> dict:
    root = project_directory(workspace_root, project_id)
    new_project = not root.exists()
    try:
        from .project_transactions import project_write_lock
    except ImportError:
        from project_transactions import project_write_lock
    with project_write_lock(root):
        _initialize_project_root(root, project_id, new_project=new_project)
    return {"status": "PROJECT_READY", "project_id": project_id, "project_root": str(root), "provider_call": "none"}


def init_registered_project(project_root: str | Path) -> dict:
    root = Path(project_root).resolve(strict=True)
    identity = _registered_project_identity(root)
    try:
        from .project_transactions import project_write_lock
    except ImportError:
        from project_transactions import project_write_lock
    with project_write_lock(root):
        _initialize_project_root(root, identity["project_id"], new_project=not (root / "CLAUDE.md").exists())
    return {"status": "PROJECT_READY", "project_id": identity["project_id"],
            "project_instance_id": identity["project_instance_id"], "project_root": str(root), "provider_call": "none"}


def _initialize_project_root(root: Path, project_id: str, *, new_project: bool) -> None:
    for folder in ("_INBOX/originals", "00_meta", "01_theme", "02_logline", "03_project_design",
                   "04_chapter_design", "05_scene_cards", "06_plot", "07_draft", "08_review", "09_revision",
                   "90_canon", "91_jet_engine", "92_style_engine", "93_data", "93_exports",
                   "contracts", "runs"):
        directory = root / folder
        if directory.is_symlink():
            raise ContractError("PROJECT_PATH_UNSAFE", f"project folder is a symlink: {folder}")
        directory.mkdir(parents=True, exist_ok=True)
    try:
        from .cnw_roles import REFERENCE_ROOT, _pinned_upstream
    except ImportError:
        from cnw_roles import REFERENCE_ROOT, _pinned_upstream
    _pinned_upstream("templates/CLAUDE.md")
    instructions = (REFERENCE_ROOT / "templates/CLAUDE.md").read_bytes()
    for name in ("CLAUDE.md", "AGENTS.md"):
        target = root / name
        if not target.exists():
            target.write_bytes(instructions)
    if new_project:
        placeholders = {
            "94_runtime/current_state.md": "TODO_CONFIRM: Author must record the current story state; this file contains no story facts.\n",
            "07_draft/manuscript_index.md": "TODO_CONFIRM: Author must list approved manuscript versions; none are registered.\n",
            "04_chapter_design/arc_index.md": "TODO_CONFIRM: Author must define Arc ranges and episode assignments.\n",
            "04_chapter_design/arc_01.md": "TODO_CONFIRM: Author must establish this Arc before writing.\n",
            "04_chapter_design/arc_01_episode_details.md": "TODO_CONFIRM: Author must define episode details for this Arc.\n",
            "90_canon/canon.md": "TODO_CONFIRM: No approved Canon facts have been supplied.\n",
            "90_canon/character_bible.md": "TODO_CONFIRM: No character facts have been supplied.\n",
            "90_canon/world_bible.md": "TODO_CONFIRM: No world facts have been supplied.\n",
            "90_canon/timeline.md": "TODO_CONFIRM: No timeline facts have been supplied.\n",
            "90_canon/glossary.md": "TODO_CONFIRM: No glossary terms have been supplied.\n",
            "92_style_engine/style_guide.md": "TODO_CONFIRM: Author must establish style and tone.\n",
            "92_style_engine/forbidden_patterns.md": "TODO_CONFIRM: Author must define project-specific exclusions.\n",
            "92_style_engine/character_voice_samples.md": "TODO_CONFIRM: No approved voice samples have been supplied.\n",
        }
        for relative, value in placeholders.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with target.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(value)
            except FileExistsError:
                pass


def _json_scalars(value, pointer=""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _json_scalars(child, pointer + "/" + str(key).replace("~", "~0").replace("/", "~1"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _json_scalars(child, pointer + "/" + str(index))
    elif value is not None:
        yield pointer or "/", str(value)


def _reject_duplicate_json_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ContractError("IMPORT_JSON_DUPLICATE_KEY", f"duplicate object key: {key}")
        value[key] = item
    return value


def _write_immutable_snapshot(project_root: Path, category: str, raw: bytes) -> tuple[str, str]:
    digest = sha(raw)
    relative = Path("_INBOX/revisions") / category / f"{digest}.json"
    target = project_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.is_symlink() or target.read_bytes() != raw:
            raise ContractError("SOURCE_REVISION_COLLISION", relative.as_posix())
    else:
        with target.open("xb") as stream:
            stream.write(raw)
            stream.flush()
    return relative.as_posix(), digest


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def import_source(workspace_root: str | Path | None = None, project_id: str | None = None, input_file: str | Path | None = None, *, project_root: str | Path | None = None) -> dict:
    if project_root is not None:
        root = Path(project_root).resolve(strict=True)
    elif workspace_root is not None and project_id is not None:
        root = project_directory(workspace_root, project_id)
        root.mkdir(parents=True, exist_ok=True)
    else:
        raise ContractError("PROJECT_REQUIRED", "supply a registered project_root or legacy workspace_root and project_id")
    try:
        from .project_transactions import project_write_lock
    except ImportError:
        from project_transactions import project_write_lock
    with project_write_lock(root):
        return _import_source_unlocked(workspace_root, project_id, input_file, project_root=project_root)


def _import_source_unlocked(workspace_root: str | Path | None = None, project_id: str | None = None, input_file: str | Path | None = None, *, project_root: str | Path | None = None) -> dict:
    if input_file is None:
        raise ContractError("IMPORT_INPUT_REQUIRED", "select an explicit source file")
    if project_root is not None:
        root = Path(project_root).resolve(strict=True)
        identity = _registered_project_identity(root)
        if project_id is not None and identity.get("project_id") != project_id:
            raise ContractError("PROJECT_IDENTITY_MISMATCH", "display project_id differs from the registered project")
        project_id = identity["project_id"]
        _initialize_project_root(root, project_id, new_project=not (root / "CLAUDE.md").exists())
    else:
        if workspace_root is None or project_id is None:
            raise ContractError("PROJECT_REQUIRED", "supply a registered project_root or legacy workspace_root and project_id")
        root = project_directory(workspace_root, project_id)
    source_path = Path(input_file).resolve(strict=True)
    if not source_path.is_file() or source_path.suffix.lower() not in {".md", ".txt", ".json"}:
        raise ContractError("IMPORT_NEEDS_FORMAT_ADAPTER", "supported source files are UTF-8 .md, .txt, or structured .json")
    raw = source_path.read_bytes()
    digest = sha(raw)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ContractError("IMPORT_ENCODING_INVALID", "source must be UTF-8") from exc
    is_json = source_path.suffix.lower() == ".json"
    if is_json:
        try:
            parsed = json.loads(text, object_pairs_hook=_reject_duplicate_json_keys)
        except json.JSONDecodeError as exc:
            raise ContractError("IMPORT_JSON_INVALID", str(exc)) from exc
        if not isinstance(parsed, (dict, list)):
            raise ContractError("IMPORT_NEEDS_FORMAT_ADAPTER", "JSON root must be an object or array")
    else:
        parsed = None
    if project_root is None:
        init_project(workspace_root, project_id)
    inbox = root / "_INBOX"
    manifest_path = inbox / "source_manifest.json"
    index_path = inbox / "source_index.json"
    canon_path = root / "90_canon" / "canon_candidates.json"
    if inbox.is_symlink() or (inbox / "originals").is_symlink() or (root / "90_canon").is_symlink():
        raise ContractError("SOURCE_PATH_UNSAFE", "source registry and review-state roots must not be symlinks")
    for path in (manifest_path, index_path, canon_path):
        if path.is_symlink():
            raise ContractError("SOURCE_PATH_UNSAFE", f"source registry or derived review state is a symlink: {path.name}")
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    previous_index = json.loads(index_path.read_text(encoding="utf-8")) if previous else None
    previous_canon = json.loads(canon_path.read_text(encoding="utf-8")) if previous else None
    if previous:
        for source in previous["sources"]:
            if source["sha256"] == digest:
                stored = root / source["stored_path"]
                if not stored.is_file() or sha(stored.read_bytes()) != digest:
                    raise ContractError("EXISTING_SOURCE_COLLISION", source["stored_path"])
                return {"status": "SOURCE_ALREADY_IMPORTED", "project_id": project_id,
                        "project_root": str(root), "source_sha256": digest,
                        "provider_call": "none"}
    original_rel = Path("_INBOX/originals") / f"{digest[:16]}_{source_path.name}"
    original = root / original_rel
    if original.is_symlink():
        raise ContractError("SOURCE_PATH_UNSAFE", str(original_rel))
    if original.exists() and sha(original.read_bytes()) != digest:
        raise ContractError("EXISTING_SOURCE_COLLISION", str(original_rel))
    if not original.exists():
        shutil.copyfile(source_path, original)

    locations = []
    candidates = []
    if is_json:
        lines = text.splitlines()
        for pointer, scalar in _json_scalars(parsed):
            # Retain the structured address and exact source text; do not infer
            # whether a scalar is canon, motive, character identity, or fact.
            locations.append({"location": {"json_pointer": pointer}, "text": scalar})
            candidates.append({"candidate_id": f"C{len(candidates)+1:04d}", "claim": scalar, "source": {"file": original_rel.as_posix(), "json_pointer": pointer}, "status": "TODO_CONFIRM"})
    else:
        lines = text.splitlines()
        for number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            locations.append({"location": {"line": number}, "text": line.strip()})
            if line.strip().startswith("#") or len(line.strip()) >= 12:
                candidates.append({"candidate_id": f"C{len(candidates)+1:04d}", "claim": line.strip().lstrip("# "), "source": {"file": original_rel.as_posix(), "line": number}, "status": "TODO_CONFIRM"})
    if not locations:
        raise ContractError("IMPORT_SOURCE_EMPTY", "no source text was indexed")
    manifest = {
        "schema_version": "cnw_source_manifest_v2", "project_id": project_id,
        "import_id": digest,
        "parent_revision_sha256": None,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": [{"source_id": digest[:16], "source_revision_id": digest,
                     "original_path": str(source_path), "stored_path": original_rel.as_posix(),
                     "format": source_path.suffix.lower().lstrip("."), "sha256": digest,
                     "bytes": len(raw), "encoding": "utf-8", "location_count": len(locations)}],
    }
    index = {"schema_version": "cnw_source_index_v1", "project_id": project_id, "source_sha256": digest,
             "source_revisions": [{"source_id": digest[:16], "source_revision_id": digest,
                                   "stored_path": original_rel.as_posix(), "format": source_path.suffix.lower().lstrip(".")}],
             "locations": locations}
    for location in locations:
        location["source_id"] = digest[:16]
        location["source_file"] = original_rel.as_posix()
    if previous:
        previous_bytes = manifest_path.read_bytes()
        # Any extant contract/run may still name either current pointer. Preserve
        # the exact previous revisions before advancing those mutable aliases.
        _write_immutable_snapshot(root, "legacy-manifests", previous_bytes)
        _write_immutable_snapshot(root, "legacy-indexes", index_path.read_bytes())
        if previous.get("schema_version") != "cnw_source_manifest_v2":
            # Preserve every v1 byte identity before advancing the mutable current pointer.
            if canon_path.is_file():
                _write_immutable_snapshot(root, "legacy-state", canon_path.read_bytes())
            prior_sources = []
            for item in previous.get("sources", []):
                prior_sources.append({**item, "source_revision_id": item.get("source_revision_id", item["sha256"])})
            parent_sha = sha(previous_bytes)
        else:
            prior_sources = list(previous.get("sources", []))
            parent_sha = sha(previous_bytes)
        manifest = {**manifest, "import_id": previous.get("import_id", prior_sources[0]["sha256"]),
                    "sources": prior_sources + manifest["sources"],
                    "parent_revision_sha256": parent_sha}
        old_locations = previous_index["locations"]
        if len(previous["sources"]) == 1:
            first = previous["sources"][0]
            old_locations = [{"source_id": first["source_id"],
                              "source_file": first["stored_path"], **item}
                             for item in old_locations]
        old_revisions = previous_index.get("source_revisions") or [
            {"source_id": item["source_id"], "source_revision_id": item.get("source_revision_id", item["sha256"]),
             "stored_path": item["stored_path"], "format": item["format"]}
            for item in prior_sources]
        index = {**previous_index, "source_revisions": old_revisions + index["source_revisions"],
                 "locations": old_locations + locations}
        used_ids = {item["candidate_id"] for item in previous_canon["candidates"]}
        next_id = 1
        for candidate in candidates:
            while f"C{next_id:04d}" in used_ids:
                next_id += 1
            candidate["candidate_id"] = f"C{next_id:04d}"
            used_ids.add(candidate["candidate_id"])
        candidates = previous_canon["candidates"] + candidates
    manifest_raw = _json_bytes(manifest)
    manifest_revision_path, manifest_revision_sha = _write_immutable_snapshot(root, "manifests", manifest_raw)
    index = {**index, "schema_version": "cnw_source_index_v2", "project_id": project_id,
             "manifest_revision_sha256": manifest_revision_sha}
    index_raw = _json_bytes(index)
    index_revision_path, index_revision_sha = _write_immutable_snapshot(root, "indexes", index_raw)
    # These names are compatibility/current-list pointers only. Contracts bind the immutable revisions above.
    manifest_path.write_bytes(manifest_raw)
    index_path.write_bytes(index_raw)
    canon_document = previous_canon or {"schema_version": "cnw_canon_candidates_v1", "project_id": project_id, "policy": "Every entry requires human confirmation; importer makes no Canon inference."}
    canon_document.update(source_manifest_sha256=sha(manifest_path.read_bytes()), candidates=candidates)
    canon_path.write_text(json.dumps(canon_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "SOURCE_IMPORTED_FOR_REVIEW", "project_id": project_id, "project_root": str(root), "source_manifest": manifest_revision_path, "source_index": index_revision_path, "source_manifest_sha256": manifest_revision_sha, "source_index_sha256": index_revision_sha, "source_id": digest[:16], "source_revision_id": digest, "canon_candidates": "90_canon/canon_candidates.json", "source_sha256": digest, "source_locations": len(locations), "canon_candidate_count": len(candidates), "canon_status": "TODO_CONFIRM", "provider_call": "none"}


def build_source_bound_contract(project_root: str | Path, *, unit_id: str, pov: str, language: str, target: int, minimum: int, maximum: int, before_line: int, after_line: int, beat_specs: list[dict] | None = None, entry_state: str, exit_state: str, role_in_story: str, reader_reward: str, characters: list[str] | None = None, kind: str = "scene", planning_mode: str = "author_plot", arc_ref: str | None = None, previous_episode_ref: str | None = None, first_episode: bool | None = None) -> dict:
    root = Path(project_root).resolve()
    manifest_file = _safe_source_file(root, "_INBOX/source_manifest.json")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("schema_version") == "cnw_source_manifest_v2":
        raise ContractError("WORK_INTENT_REQUIRED", "v2 source registries require an explicit source revision and work intent")
    language = _required_text(language, "unit.language")
    index = json.loads(_safe_source_file(root, "_INBOX/source_index.json").read_text(encoding="utf-8"))
    source = manifest["sources"][0]
    raw_path = root / source["stored_path"]
    lines = raw_path.read_bytes().splitlines(keepends=True)
    if min(before_line, after_line) < 1 or max(before_line, after_line) > len(lines) or after_line <= before_line:
        raise ContractError("SOURCE_ANCHOR_INVALID", "line anchors must exist and after_line must follow before_line")
    if kind not in ("scene", "episode") or planning_mode not in ("author_plot", "legacy_frozen"):
        raise ContractError("PLANNING_MODE_INVALID", "expected scene/episode and author_plot/legacy_frozen")
    beats = [{"beat_id": item["beat_id"], "goal": item["goal"], "min_coverage": item.get("min_coverage", "source_supported_action"),
              **({"budget_visible_chars": item["budget_visible_chars"]} if planning_mode == "legacy_frozen" else {})} for item in (beat_specs or [])]
    if planning_mode == "legacy_frozen" and sum(item["budget_visible_chars"] for item in beats) != target:
        raise ContractError("SCENE_BUDGET_SUM_MISMATCH", "explicit beat budgets must sum to target")
    return {
        "schema_version": "cnw_work_unit_v1", "project_id": manifest["project_id"], "status": "PROPOSED_FOR_HUMAN_PREFLIGHT",
        "source": {"identity_type": "imported_project", "version": "IMPORTED-SOURCE-v1", "import_id": manifest["import_id"], "source_file_sha256": source["sha256"], "source_manifest_sha256": sha(manifest_file.read_bytes()), "manifest_file": "_INBOX/source_manifest.json", "source_root": "."},
        "unit": {"id": unit_id, "kind": kind, "planning_mode": planning_mode, "language": language, "pov": pov, "target_visible_chars": target, "min_visible_chars": minimum, "max_visible_chars": maximum, "policy_sha256": sha((ROOT / "config/cnw_production_policy.json").read_bytes())},
        "story": {**({"arc_ref": arc_ref} if arc_ref is not None else {}), **({"previous_episode_ref": previous_episode_ref} if previous_episode_ref is not None else {}), **({"first_episode": first_episode} if first_episode is not None else {}), "source_file": source["stored_path"], "chapter_context": f"Imported source {source['source_id']} with {len(index['locations'])} indexed source locations; confirm all facts before production.", "role_in_story": role_in_story, "reader_reward": reader_reward, "entry_state": entry_state, "exit_state": exit_state, "before_anchor": {"scene": "IMPORTED", "source_line": before_line, "sha256": sha(b"".join(lines[before_line-1:before_line]))}, "after_anchor": {"scene": "IMPORTED", "source_line": after_line, "sha256": sha(b"".join(lines[after_line-1:after_line]))}, "required_beats": beats, "characters_in_scene": characters or [], "character_knowledge_boundary_ref": "90_canon/canon_candidates.json#status=TODO_CONFIRM", "forbidden_future_revelations": ["Do not use unconfirmed Canon candidates or facts outside the approved Writing Brief."], "voice_sample_refs": ["90_canon/canon_candidates.json#voice-sample-review-required"]},
        "review": {"workflow_template_git_blob": "146ea01a484cc0578cf290478b3941599ad7fb15", "require_cnw_11_stages": True, "require_3_verifiers": True, "require_completeness_critic": True, "require_re_review": True, "cnw_reference_manifest_sha256": sha((ROOT / "runtime/reference/cnw_97ad71fe5e5e/CNW_LOCAL_REFERENCE_MANIFEST.json").read_bytes())},
    }


def _required_text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError("PRE_FLIGHT_MISSING_PROJECT_INPUT", field)
    return value.strip()


def _registered_project_identity(root: Path) -> dict:
    if root.parent.name != "projects":
        raise ContractError("PROJECT_INSTANCE_ID_REQUIRED", "project is not a registered DataHome/projects instance")
    try:
        try:
            from .project_paths import resolve_project
        except ImportError:
            from project_paths import resolve_project
        registration = resolve_project(root, data_home=root.parent.parent)
    except Exception as exc:
        raise ContractError("PROJECT_INSTANCE_ID_REQUIRED", "registered project identity or registry could not be verified") from exc
    identity_path = root / "project_identity.json"
    if identity_path.is_symlink() or not identity_path.is_file():
        raise ContractError("PROJECT_INSTANCE_ID_REQUIRED", "register this project before creating a v2 work contract")
    try:
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("PROJECT_INSTANCE_ID_REQUIRED", "registered project identity is unreadable") from exc
    instance_id = identity.get("project_instance_id") if isinstance(identity, dict) else None
    if not isinstance(instance_id, str) or not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", instance_id):
        raise ContractError("PROJECT_INSTANCE_ID_REQUIRED", "registered project identity must contain a canonical instance UUID")
    if registration.get("project_instance_id") != instance_id or registration.get("project_id") != identity.get("project_id"):
        raise ContractError("PROJECT_INSTANCE_ID_REQUIRED", "project identity differs from its registration")
    return identity


def list_source_revisions(project_root: str | Path) -> dict:
    """List verified source identities and immutable registry revisions, without exposing source text."""
    root = Path(project_root).resolve(strict=True)
    identity = _registered_project_identity(root)
    manifest_path = _safe_source_file(root, "_INBOX/source_manifest.json")
    index_path = _safe_source_file(root, "_INBOX/source_index.json")
    try:
        manifest_raw, index_raw = manifest_path.read_bytes(), index_path.read_bytes()
        manifest, source_index = json.loads(manifest_raw), json.loads(index_raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("SOURCE_REGISTRY_INVALID", "current source registry is unreadable") from exc
    manifest_sha, index_sha = sha(manifest_raw), sha(index_raw)
    if (not isinstance(manifest, dict) or not isinstance(source_index, dict) or
            not isinstance(manifest.get("sources"), list) or
            source_index.get("schema_version") != "cnw_source_index_v2" or
            source_index.get("manifest_revision_sha256") != manifest_sha):
        raise ContractError("SOURCE_REGISTRY_INVALID", "source registry revisions are not mutually bound")
    if manifest.get("schema_version") != "cnw_source_manifest_v2":
        raise ContractError("SOURCE_REGISTRY_INVALID", "current source manifest is not v2")
    _source_manifest_revision(root, manifest_sha)
    index_snapshot = _safe_source_file(root, f"_INBOX/revisions/indexes/{index_sha}.json")
    if sha(index_snapshot.read_bytes()) != index_sha:
        raise ContractError("SOURCE_IDENTITY_MISMATCH", "immutable source-index revision SHA256 differs")
    index_rows = source_index.get("source_revisions")
    if not isinstance(index_rows, list) or any(not isinstance(item, dict) for item in index_rows):
        raise ContractError("SOURCE_REGISTRY_INVALID", "source-index revision list is malformed")
    listed = []
    for item in manifest.get("sources", []):
        if not isinstance(item, dict):
            raise ContractError("SOURCE_REGISTRY_INVALID", "source manifest contains a malformed source row")
        source_id, revision_id = item.get("source_id"), item.get("source_revision_id")
        indexed = [row for row in index_rows if row.get("source_id") == source_id and
                   row.get("source_revision_id") == revision_id]
        if len(indexed) != 1 or indexed[0].get("stored_path") != item.get("stored_path"):
            raise ContractError("SOURCE_REGISTRY_INVALID", "manifest source is missing from the bound source index")
        source = _safe_source_file(root, item["stored_path"])
        if sha(source.read_bytes()) != revision_id:
            raise ContractError("SOURCE_IDENTITY_MISMATCH", "stored source bytes differ from the recorded revision")
        listed.append({"source_id": source_id, "source_revision_id": revision_id,
                       "format": item.get("format"), "stored_path": item["stored_path"]})
    return {"status": "SOURCE_REVISIONS_LISTED", "project_id": identity["project_id"],
            "project_instance_id": identity["project_instance_id"],
            "source_manifest_revision_sha256": manifest_sha,
            "source_index_revision_sha256": index_sha, "sources": listed,
            "provider_call": "none"}


def _source_manifest_revision(root: Path, digest: str) -> tuple[dict, str]:
    if not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
        raise ContractError("SOURCE_MANIFEST_REVISION_REQUIRED", "select an exact immutable source-manifest SHA256")
    relative = f"_INBOX/revisions/manifests/{digest}.json"
    try:
        path = _safe_source_file(root, relative)
    except (ContractError, OSError) as exc:
        raise ContractError("LEGACY_SOURCE_SNAPSHOT_MISSING", relative) from exc
    raw = path.read_bytes()
    if sha(raw) != digest:
        raise ContractError("SOURCE_IDENTITY_MISMATCH", "immutable source-manifest revision SHA256 differs")
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("SOURCE_MANIFEST_INVALID", "source-manifest revision is not valid JSON") from exc
    if manifest.get("schema_version") != "cnw_source_manifest_v2":
        raise ContractError("SOURCE_MANIFEST_INVALID", "new contracts require a v2 immutable source-manifest revision")
    return manifest, relative


def build_work_contract_v2(project_root: str | Path, draft: dict, *, registered_identity: dict | None = None) -> dict:
    """Build one explicit intent/source contract; no default source or anchors."""
    if not isinstance(draft, dict):
        raise ContractError("CONTRACT_DRAFT_INVALID", "work-unit draft root must be an object")
    root = Path(project_root).resolve(strict=True)
    identity = registered_identity or _registered_project_identity(root)
    instance_id = identity["project_instance_id"]
    unit_id = draft.get("unit_id")
    if not isinstance(unit_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,95}", unit_id):
        raise ContractError("WORK_UNIT_ID_INVALID", str(unit_id))
    intent = draft.get("work_intent")
    if intent not in {"INSERT_BETWEEN", "ADAPT_SOURCE", "ORIGINAL_EPISODE"}:
        raise ContractError("WORK_INTENT_UNSUPPORTED", str(intent))
    kind = draft.get("kind", "scene")
    if kind not in {"scene", "episode"}:
        raise ContractError("WORK_UNIT_KIND_INVALID", str(kind))
    locale = _required_text(draft.get("language_locale"), "language.locale")
    target, minimum, maximum = (draft.get("target_visible_chars"), draft.get("min_visible_chars"), draft.get("max_visible_chars"))
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in (target, minimum, maximum)) or not (1 <= minimum <= target <= maximum):
        raise ContractError("SCENE_BUDGET_INVALID", "visible-character minimum, target, and maximum must be explicit and ordered")
    root_source: dict
    story_source_fields: dict = {}
    if intent == "ORIGINAL_EPISODE":
        if draft.get("source_id") or draft.get("source_revision_id") or draft.get("source_manifest_revision_sha256"):
            raise ContractError("SOURCE_TYPE_UNSUPPORTED", "original work cannot select or fabricate an imported source")
        if not isinstance(draft.get("first_episode"), bool):
            raise ContractError("PRE_FLIGHT_MISSING_PROJECT_INPUT", "story.first_episode")
        arc_ref = _required_text(draft.get("arc_ref"), "story.arc_ref")
        root_source = {"source_origin": "ORIGINAL_PROJECT", "project_instance_id": instance_id}
        story_source_fields["first_episode"] = draft["first_episode"]
        story_source_fields["arc_ref"] = arc_ref
        if not draft["first_episode"]:
            previous = _required_text(draft.get("previous_episode_ref"), "story.previous_episode_ref")
            path = _safe_source_file(root, previous)
            story_source_fields["previous_episode_ref"] = previous.replace("\\", "/")
            story_source_fields["previous_episode_sha256"] = sha(path.read_bytes())
        arc_path = _safe_source_file(root, arc_ref)
        arc_text = arc_path.read_text(encoding="utf-8-sig").strip()
        if not arc_text or re.search(r"^\s*TODO(?:_CONFIRM)?\s*:", arc_text, re.I | re.M):
            raise ContractError("PRE_FLIGHT_MISSING_PROJECT_INPUT", arc_ref)
        story_source_fields["arc_sha256"] = sha(arc_path.read_bytes())
    else:
        for field in ("source_id", "source_revision_id", "source_manifest_revision_sha256", "source_index_revision_sha256"):
            if not isinstance(draft.get(field), str) or not draft[field]:
                raise ContractError("SOURCE_SELECTION_REQUIRED", f"{field} must be explicitly selected")
        manifest, manifest_rel = _source_manifest_revision(root, draft["source_manifest_revision_sha256"])
        index_rel = f"_INBOX/revisions/indexes/{draft['source_index_revision_sha256']}.json"
        index_path = _safe_source_file(root, index_rel)
        index_raw = index_path.read_bytes()
        if sha(index_raw) != draft["source_index_revision_sha256"]:
            raise ContractError("SOURCE_IDENTITY_MISMATCH", "immutable source-index revision SHA256 differs")
        try:
            source_index = json.loads(index_raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ContractError("SOURCE_INDEX_INVALID", "source-index revision is not valid JSON") from exc
        if source_index.get("schema_version") != "cnw_source_index_v2" or source_index.get("manifest_revision_sha256") != draft["source_manifest_revision_sha256"]:
            raise ContractError("SOURCE_IDENTITY_MISMATCH", "source index does not bind the selected manifest revision")
        matches = [item for item in manifest["sources"] if item.get("source_id") == draft["source_id"] and item.get("source_revision_id") == draft["source_revision_id"]]
        if len(matches) != 1:
            raise ContractError("SOURCE_SELECTION_AMBIGUOUS" if sum(item.get("source_id") == draft["source_id"] for item in manifest["sources"]) > 1 else "SOURCE_SELECTION_INVALID", "select one source ID and source revision present in the exact manifest revision")
        selected = matches[0]
        source_file = _safe_source_file(root, selected["stored_path"])
        if sha(source_file.read_bytes()) != draft["source_revision_id"]:
            raise ContractError("SOURCE_IDENTITY_MISMATCH", "selected source bytes differ from the immutable manifest")
        root_source = {"source_origin": "IMPORTED_PROJECT", "project_instance_id": instance_id,
                       "source_id": draft["source_id"], "source_revision_id": draft["source_revision_id"],
                       "source_file_sha256": draft["source_revision_id"],
                       "manifest_file": manifest_rel,
                       "source_manifest_sha256": draft["source_manifest_revision_sha256"],
                       "manifest_revision_sha256": draft["source_manifest_revision_sha256"],
                       "source_index_file": index_rel,
                       "source_index_sha256": draft["source_index_revision_sha256"]}
        story_source_fields["source_file"] = selected["stored_path"]
        if intent == "INSERT_BETWEEN":
            if selected.get("format") not in {"md", "txt"}:
                raise ContractError("SOURCE_TYPE_UNSUPPORTED", "INSERT_BETWEEN requires an ordered text source")
            before_line, after_line = draft.get("before_line"), draft.get("after_line")
            before_end = draft.get("before_line_end", before_line)
            after_end = draft.get("after_line_end", after_line)
            lines = source_file.read_bytes().splitlines(keepends=True)
            if (any(type(value) is not int for value in (before_line, before_end, after_line, after_end)) or
                    not (1 <= before_line <= before_end < after_line <= after_end <= len(lines))):
                raise ContractError("SOURCE_ANCHOR_INVALID", "both real ordered source line anchors are required")
            story_source_fields["before_anchor"] = {"scene": _required_text(draft.get("before_scene", "SOURCE"), "story.before_anchor.scene"), "source_line": before_line, "source_line_end": before_end, "sha256": sha(b"".join(lines[before_line - 1:before_end]))}
            story_source_fields["after_anchor"] = {"scene": _required_text(draft.get("after_scene", "SOURCE"), "story.after_anchor.scene"), "source_line": after_line, "source_line_end": after_end, "sha256": sha(b"".join(lines[after_line - 1:after_end]))}
        else:
            selection = {"source_id": draft["source_id"], "source_revision_id": draft["source_revision_id"]}
            if selected.get("format") == "json":
                pointer = draft.get("json_pointer")
                try:
                    parsed = json.loads(source_file.read_text(encoding="utf-8-sig"), object_pairs_hook=_reject_duplicate_json_keys)
                except (UnicodeError, json.JSONDecodeError, ContractError) as exc:
                    raise ContractError("SOURCE_JSON_INVALID", "selected JSON source is invalid or has duplicate keys") from exc
                value = resolve_json_pointer(parsed, pointer)
                selected_bytes = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                excerpt = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
                canonical_sha = sha(selected_bytes)
                selection.update(json_pointer=pointer, hash_semantics="json_pointer_canonical_value_sha256",
                                 selected_sha256=canonical_sha,
                                 canonical_selected_value_sha256=canonical_sha,
                                 wire_excerpt_sha256=sha(excerpt.encode("utf-8")))
            elif selected.get("format") in {"md", "txt"}:
                start, end = draft.get("start_line"), draft.get("end_line")
                lines = source_file.read_bytes().splitlines(keepends=True)
                if (not isinstance(start, int) or isinstance(start, bool) or
                        not isinstance(end, int) or isinstance(end, bool) or
                        start < 1 or end < start or end > len(lines)):
                    raise ContractError("SOURCE_SPAN_INVALID", "ADAPT_SOURCE requires a non-empty valid line range")
                selected_bytes = b"".join(lines[start-1:end])
                if not selected_bytes.decode("utf-8-sig").strip():
                    raise ContractError("SOURCE_SPAN_EMPTY", "ADAPT_SOURCE text span must contain non-whitespace source text")
                selection.update(start_line=start, end_line=end, hash_semantics="raw_line_span_sha256", selected_sha256=sha(selected_bytes))
            else:
                raise ContractError("SOURCE_TYPE_UNSUPPORTED", str(selected.get("format")))
            story_source_fields["source_selection"] = selection

    # Source-based work can select an Arc just as original work can. Retain
    # its exact identity instead of discarding it and using a fallback Arc.
    if intent != "ORIGINAL_EPISODE" and "arc_ref" in draft:
        arc_ref = _required_text(draft["arc_ref"], "story.arc_ref")
        try:
            from .cnw_roles import resolve_arc
        except ImportError:
            from cnw_roles import resolve_arc
        arc_path = resolve_arc(root, unit_id, arc_ref)
        story_source_fields.update(arc_ref=arc_ref, arc_sha256=sha(arc_path.read_bytes()))

    beats = draft.get("required_beats", [])
    if not isinstance(beats, list):
        raise ContractError("REQUIRED_BEAT_INVALID", "required_beats must be a list")
    beat_ids = set()
    for beat in beats:
        if (not isinstance(beat, dict) or not isinstance(beat.get("beat_id"), str) or
                not beat["beat_id"].strip() or beat["beat_id"] in beat_ids or
                not isinstance(beat.get("goal"), str) or not beat["goal"].strip()):
            raise ContractError("REQUIRED_BEAT_INVALID", "required beats need unique IDs and non-empty goals")
        beat_ids.add(beat["beat_id"])
    def _text_list(value, field: str) -> list[str]:
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise ContractError("CONTRACT_FIELD_INVALID", f"{field} must be a list of non-empty strings")
        return value
    characters = _text_list(draft.get("characters_in_scene"), "story.characters_in_scene")
    forbidden = _text_list(draft.get("forbidden_future_revelations"), "story.forbidden_future_revelations")
    voice_refs = _text_list(draft.get("voice_sample_refs"), "story.voice_sample_refs")
    integration_draft = draft.get("integrations", {})
    if not isinstance(integration_draft, dict):
        raise ContractError("SUPPORT_INTEGRATION_CONFIG_INVALID", "integrations must be an object")
    integrations = {name: integration_draft.get(name, "DISABLED") for name in ("nk", "critics")}
    review_draft = draft.get("review")
    fifth_lens = review_draft.get("fifth_lens") if isinstance(review_draft, dict) else None
    if (not isinstance(fifth_lens, dict) or not isinstance(fifth_lens.get("id"), str) or
            not fifth_lens["id"].strip() or
            not isinstance(fifth_lens.get("responsibility"), str) or
            not fifth_lens["responsibility"].strip()):
        raise ContractError("PRE_FLIGHT_MISSING_PROJECT_INPUT", "review.fifth_lens.id/responsibility")
    fifth_lens_id = fifth_lens["id"].strip()
    fifth_lens_responsibility = fifth_lens["responsibility"].strip()
    policy_path = ROOT / "config/policies/app_policy.v1.json"
    contract = {
        "schema_version": "cnw_work_unit_v2", "project_id": identity["project_id"],
        "project_instance_id": instance_id, "status": "PROPOSED_FOR_HUMAN_PREFLIGHT", "work_intent": intent,
        "source": root_source,
        "unit": {"id": unit_id, "kind": kind, "planning_mode": "author_plot", "language": locale,
                 "language_locale": locale, "length_metric": "unicode_visible_code_points",
                 "length_semantics": "NFC normalized; Markdown control syntax and whitespace excluded; remaining Unicode code points counted, not word-count units.",
                 "pov": _required_text(draft.get("pov"), "unit.pov"), "target_visible_chars": target,
                 "min_visible_chars": minimum, "max_visible_chars": maximum,
                 "policy_sha256": sha(policy_path.read_bytes())},
        "integrations": integrations,
        "story": {**story_source_fields,
                  "chapter_context": _required_text(draft.get("chapter_context"), "story.chapter_context"),
                  "role_in_story": _required_text(draft.get("role_in_story"), "story.role_in_story"),
                  "reader_reward": _required_text(draft.get("reader_reward"), "story.reader_reward"),
                  "entry_state": _required_text(draft.get("entry_state"), "story.entry_state"),
                  "exit_state": _required_text(draft.get("exit_state"), "story.exit_state"),
                  "required_beats": beats, "characters_in_scene": characters,
                  "character_knowledge_boundary_ref": _required_text(draft.get("character_knowledge_boundary_ref"), "story.character_knowledge_boundary_ref"),
                  "forbidden_future_revelations": forbidden,
                  "voice_sample_refs": voice_refs},
        "review": {"workflow_template_git_blob": "146ea01a484cc0578cf290478b3941599ad7fb15", "require_cnw_11_stages": True,
                   "require_3_verifiers": True, "require_completeness_critic": True, "require_re_review": True,
                   "fifth_lens": {"id": fifth_lens_id, "responsibility": fifth_lens_responsibility,
                                  "responsibility_sha256": sha(fifth_lens_responsibility.encode("utf-8"))},
                   "cnw_reference_manifest_sha256": sha((ROOT / "runtime/reference/cnw_97ad71fe5e5e/CNW_LOCAL_REFERENCE_MANIFEST.json").read_bytes())},
    }
    if kind == "episode":
        scene_targets = draft.get("scene_targets") or [{"id": f"{unit_id}-S01", "target_visible_chars": target}]
        contract["unit"]["chapter_target_visible_chars"] = target
        contract["unit"]["scenes"] = scene_targets
    if "input_pack" in draft:
        # This is an immutable input record, not a role-reading override or
        # an approval receipt. Consumers still use the author reading lists.
        contract["input_pack"] = json.loads(json.dumps(draft["input_pack"]))
    check_required_fields(contract)
    validate_work_unit(contract)
    validate_v2_source_identity(contract, source_root=root)
    return contract


def write_contract_draft(project_root: str | Path, draft_path: str | Path) -> dict:
    root = Path(project_root).resolve(strict=True)
    try:
        from .project_transactions import project_write_lock
    except ImportError:
        from project_transactions import project_write_lock
    with project_write_lock(root):
        return _write_contract_draft_unlocked(root, draft_path)


def _write_contract_draft_unlocked(project_root: str | Path, draft_path: str | Path) -> dict:
    root = Path(project_root).resolve(strict=True)
    registered_identity = None
    if not root.is_relative_to((ROOT / "workspace").resolve()):
        registered_identity = _registered_project_identity(root)
    raw_source = Path(draft_path)
    if raw_source.is_symlink():
        raise ContractError("CONTRACT_PATH_UNSAFE", str(raw_source))
    source = raw_source.resolve(strict=True)
    if not source.is_relative_to(root):
        raise ContractError("CONTRACT_PATH_OUTSIDE_PROJECT", str(source))
    try:
        draft = json.loads(source.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ContractError("CONTRACT_DRAFT_INVALID", str(exc)) from exc
    unit_id = draft["unit_id"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,95}", unit_id) or unit_id in {".", ".."}:
        raise ContractError("WORK_UNIT_ID_INVALID", str(unit_id))
    if draft.get("schema_version") == "cnw_work_unit_draft_v2" or "work_intent" in draft:
        contract = build_work_contract_v2(root, draft, registered_identity=registered_identity)
    else:
        current_manifest = root / "_INBOX/source_manifest.json"
        if current_manifest.is_file():
            try:
                current_schema = json.loads(current_manifest.read_text(encoding="utf-8")).get("schema_version")
            except (OSError, json.JSONDecodeError) as exc:
                raise ContractError("SOURCE_MANIFEST_INVALID", "current source registry is unreadable") from exc
            if current_schema == "cnw_source_manifest_v2":
                raise ContractError("WORK_INTENT_REQUIRED", "new contracts must explicitly select INSERT_BETWEEN, ADAPT_SOURCE, or ORIGINAL_EPISODE")
        contract = build_source_bound_contract(root, unit_id=unit_id, pov=draft["pov"], language=draft.get("language"), target=draft["target_visible_chars"], minimum=draft["min_visible_chars"], maximum=draft["max_visible_chars"], before_line=draft["before_line"], after_line=draft["after_line"], beat_specs=draft.get("required_beats", []), entry_state=draft["entry_state"], exit_state=draft["exit_state"], role_in_story=draft["role_in_story"], reader_reward=draft["reader_reward"], characters=draft.get("characters_in_scene"), kind=draft.get("kind", "scene"), planning_mode=draft.get("planning_mode", "author_plot"), arc_ref=draft.get("arc_ref"), previous_episode_ref=draft.get("previous_episode_ref"), first_episode=draft.get("first_episode"))
    check_required_fields(contract)
    validate_work_unit(contract)
    if contract.get("schema_version") == "cnw_work_unit_v2":
        validate_v2_source_identity(contract, source_root=root)
    else:
        manifest = json.loads((root / "_INBOX/source_manifest.json").read_text(encoding="utf-8"))
        validate_source_identity(contract, source_root=root, expected_version=contract["source"]["version"], expected_zip_sha256=manifest["import_id"], expected_manifest_sha256=contract["source"]["source_manifest_sha256"])
    output = root / "contracts" / f"{contract['unit']['id']}.json"
    if output.exists():
        raise ContractError("CONTRACT_OUTPUT_COLLISION", output.name)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "CONTRACT_DRAFT_READY_FOR_HUMAN_PREFLIGHT", "project_id": contract["project_id"], "contract": str(output), "contract_sha256": sha(output.read_bytes()), "source_manifest_sha256": contract.get("source", {}).get("source_manifest_sha256"), "provider_call": "none"}


def build_contract_preflight(project_root: str | Path, contract_path: str | Path, *, run_id: str) -> dict:
    """Validate one explicit v2 contract and construct its Plot request offline.

    This is a read-only, pre-run identity check. It does not create a run, call
    a provider, or signify literary/Canon approval.
    """
    root = Path(project_root).resolve(strict=True)
    identity = _registered_project_identity(root)
    identity_path = root / "project_identity.json"
    identity_raw = identity_path.read_bytes()
    try:
        if json.loads(identity_raw.decode("utf-8")) != identity:
            raise ContractError("PROJECT_INSTANCE_IDENTITY_CHANGED_DURING_READ", str(root))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("PROJECT_INSTANCE_ID_REQUIRED", "registered project identity is unreadable") from exc
    raw_contract_path = Path(contract_path)
    candidate = raw_contract_path if raw_contract_path.is_absolute() else root / raw_contract_path
    for ancestor in (candidate, *candidate.parents):
        if ancestor.is_symlink():
            raise ContractError("CONTRACT_PATH_UNSAFE", "contract path contains a symlink")
        if ancestor == root:
            break
    selected_contract_path = candidate.resolve(strict=True)
    if not selected_contract_path.is_relative_to(root) or not selected_contract_path.is_file():
        raise ContractError("CONTRACT_PATH_OUTSIDE_PROJECT", str(selected_contract_path))
    if selected_contract_path.suffix.lower() != ".json":
        raise ContractError("CONTRACT_PATH_INVALID", "contract path must name a JSON file")
    run_id = str(run_id)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", run_id) or run_id in {".", ".."}:
        raise ContractError("VALID_RUN_ID_REQUIRED", run_id)
    run_path = root / "runs" / run_id
    if run_path.is_symlink():
        raise ContractError("RUN_PATH_SYMLINK_REJECTED", run_id)
    if run_path.exists():
        raise ContractError("PREFLIGHT_RUN_ID_COLLISION", run_id)

    contract_bytes = selected_contract_path.read_bytes()
    try:
        contract = json.loads(contract_bytes.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("CONTRACT_UNREADABLE", str(exc)) from exc
    if not isinstance(contract, dict) or contract.get("schema_version") != "cnw_work_unit_v2":
        raise ContractError("GENERIC_PREFLIGHT_V2_REQUIRED", "legacy v1 contracts retain their existing compatibility path")
    if (contract.get("project_id") != identity.get("project_id") or
            contract.get("project_instance_id") != identity.get("project_instance_id")):
        raise ContractError("PROJECT_INSTANCE_IDENTITY_MISMATCH", "contract differs from the selected registered project")
    check_required_fields(contract)
    validate_work_unit(contract)
    validate_v2_source_identity(contract, source_root=root)
    app_policy = ROOT / "config/policies/app_policy.v1.json"
    policy_sha256 = sha(app_policy.read_bytes())
    if contract["unit"].get("policy_sha256", "").lower() != policy_sha256:
        raise ContractError("POLICY_IDENTITY_MISMATCH", "contract policy differs from the current generic application policy")

    try:
        from .cnw_runner import build_plot_request
    except ImportError:
        from cnw_runner import build_plot_request
    plot_request = build_plot_request(root, contract)
    if plot_request.get("provider_call") != "none":
        raise ContractError("PREFLIGHT_PROVIDER_DISPATCH_FORBIDDEN", "contract preflight must remain offline")
    preparation = plot_request["production_preparation"]
    intent = contract["work_intent"]
    source = contract.get("source", {})
    story = contract.get("story", {})
    for relative, expected_sha in preparation["source_hashes"].items():
        if relative in {"selected_source_excerpt", "selected_source_identity"}:
            continue
        source_path = root / relative
        resolved_source = source_path.resolve(strict=True)
        if (source_path.is_symlink() or not resolved_source.is_relative_to(root) or
                sha(resolved_source.read_bytes()) != expected_sha):
            raise ContractError("PREFLIGHT_INPUT_CHANGED_DURING_READ", relative)
    if (selected_contract_path.read_bytes() != contract_bytes or
            identity_path.read_bytes() != identity_raw):
        raise ContractError("PREFLIGHT_INPUT_CHANGED_DURING_READ", "contract or project identity changed")
    if sha(app_policy.read_bytes()) != policy_sha256:
        raise ContractError("POLICY_IDENTITY_CHANGED_DURING_READ", str(app_policy))
    if run_path.exists():
        raise ContractError("PREFLIGHT_RUN_ID_COLLISION", run_id)
    if intent == "INSERT_BETWEEN":
        selected_scope = {"before_anchor": story["before_anchor"], "after_anchor": story["after_anchor"]}
        selected_scope_sha256 = sha(json.dumps(selected_scope, ensure_ascii=False, sort_keys=True,
                                              separators=(",", ":")).encode("utf-8"))
    elif intent == "ADAPT_SOURCE":
        selected_scope_sha256 = preparation["source_hashes"]["selected_source_excerpt"]
    else:
        selected_scope = {key: value for key, value in preparation["source_hashes"].items()
                          if key.startswith(("90_canon/", "04_chapter_design/", "92_style_engine/"))}
        selected_scope_sha256 = sha(json.dumps(selected_scope, ensure_ascii=False, sort_keys=True,
                                               separators=(",", ":")).encode("utf-8"))

    identity_sha256 = sha(identity_raw)
    evidence = {
        "schema_version": "cnw_contract_preflight_v1",
        "preflight_version": "cnw_contract_preflight_v1",
        "status": "READY_FOR_LIVE_PRODUCTION",
        "reviewer_identity": "StoryStudio.CNW.OfflineContractPreflight/1",
        "reviewer_type": "DETERMINISTIC_OFFLINE_VALIDATOR",
        "project_instance_id": identity["project_instance_id"],
        "project_id": contract["project_id"],
        "work_id": contract["unit"]["id"],
        "run_id": run_id,
        "run_id_claim": "NOT_RESERVED",
        "contract_sha256": sha(contract_bytes),
        "work_intent": intent,
        "source_identity": source,
        "source_root_identity": {"project_instance_id": identity["project_instance_id"],
                                  "project_identity_sha256": identity_sha256},
        "selected_scope_sha256": selected_scope_sha256,
        "policy_version": {"app_policy_sha256": policy_sha256,
                            "contract_policy_sha256": contract["unit"]["policy_sha256"]},
        "plot_request_sha256": sha(json.dumps(plot_request["messages"], ensure_ascii=False,
                                              sort_keys=True, separators=(",", ":")).encode("utf-8")),
        "production_preparation_hashes": preparation["source_hashes"],
        "provider_call": "none",
        "live_evidence_status": "NOT_RUN",
        "user_creative_acceptance": "PENDING_USER_READING",
    }
    evidence["evidence_digest"] = sha(json.dumps(evidence, ensure_ascii=False, sort_keys=True,
                                                 separators=(",", ":")).encode("utf-8"))
    return evidence


def verify_contract_preflight(project_root: str | Path, contract_path: str | Path, *,
                              run_id: str, evidence: dict) -> dict:
    """Recompute and bind preflight evidence to the current exact inputs."""
    if not isinstance(evidence, dict):
        raise ContractError("PREFLIGHT_EVIDENCE_INVALID", "evidence root must be an object")
    received_digest = evidence.get("evidence_digest")
    unsigned = {key: value for key, value in evidence.items() if key != "evidence_digest"}
    expected_digest = sha(json.dumps(unsigned, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":")).encode("utf-8"))
    if not isinstance(received_digest, str) or received_digest != expected_digest:
        raise ContractError("PREFLIGHT_EVIDENCE_DIGEST_MISMATCH", "evidence digest does not match its fields")
    current = build_contract_preflight(project_root, contract_path, run_id=run_id)
    if evidence != current:
        raise ContractError("PREFLIGHT_EVIDENCE_IDENTITY_MISMATCH", "evidence does not bind the current project, contract, source, run ID, policy and Plot request")
    return {"status": "CONTRACT_PREFLIGHT_EVIDENCE_VERIFIED", "evidence_digest": received_digest,
            "project_instance_id": current["project_instance_id"], "project_id": current["project_id"],
            "work_id": current["work_id"], "run_id": current["run_id"],
            "work_intent": current["work_intent"], "provider_call": "none",
            "live_evidence_status": "NOT_RUN", "user_creative_acceptance": "PENDING_USER_READING"}


SUPPORT_WORKFLOW_SOURCE = {
    "01": "templates/_workflows/01_first_import.md",
    "02": "templates/_workflows/02_incremental_update.md",
    "03": "templates/_workflows/03_revision.md",
    "04": "templates/_workflows/04_canon_audit.md",
    "05": "templates/_workflows/05_handoff.md",
}
REFERENCE_ROOT = ROOT / "runtime/reference/cnw_97ad71fe5e5e"


def _append_log(project_root: Path, message: str) -> None:
    log = project_root / "00_meta" / "ai_work_log.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with log.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(f"- {stamp} {message}\n")


def incremental_update(workspace_root: str | Path, project_id: str, input_file: str | Path) -> dict:
    """Workflow 02: add new material without overwriting prior imports or resolving conflicts."""
    root = project_directory(workspace_root, project_id)
    try:
        from .project_transactions import project_write_lock
    except ImportError:
        from project_transactions import project_write_lock
    with project_write_lock(root):
        return _incremental_update_unlocked(workspace_root, project_id, input_file, root=root)


def _incremental_update_unlocked(workspace_root: str | Path, project_id: str, input_file: str | Path, *, root: Path) -> dict:
    manifest_file = root / "_INBOX/source_manifest.json"
    if (root / "00_meta/import_pending.json").is_file():
        return {**_run_import_unlocked(root, incremental=True), "requested_input_deferred": True,
            "note": "Recovered the pending import first; submit the requested input again after recovery."}
    if not (root / "00_meta/import_state.json").is_file():
        raise ContractError("INCREMENTAL_REQUIRES_INITIAL_IMPORT", "run initial-import first")
    source_path = Path(input_file).resolve(strict=True)
    if source_path.is_relative_to((root / "_INBOX").resolve()):
        assert_output_within_root(root, str(source_path))
    elif all(path.is_file() for path in (manifest_file, root / "_INBOX/source_index.json", root / "90_canon/canon_candidates.json")):
        _import_source_unlocked(workspace_root, project_id, source_path)
    else:
        # Ordinary public _INBOX projects have no legacy staging manifest.
        # Preserve their old material and candidate files; only stage new bytes.
        if not source_path.is_file() or source_path.suffix.lower() not in {".md", ".txt", ".json"}:
            raise ContractError("IMPORT_NEEDS_FORMAT_ADAPTER", str(source_path))
        raw = source_path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ContractError("IMPORT_ENCODING_INVALID", "source must be UTF-8") from exc
        if source_path.suffix.lower() == ".json" and not isinstance(json.loads(text), (dict, list)):
            raise ContractError("IMPORT_NEEDS_FORMAT_ADAPTER", "JSON root must be object or array")
        digest = sha(raw)
        destination = assert_output_within_root(root, f"_INBOX/originals/{digest[:16]}_{source_path.name}")
        if destination.exists() and destination.read_bytes() != raw:
            raise ContractError("EXISTING_SOURCE_COLLISION", destination.name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            destination.write_bytes(raw)
    return _run_import_unlocked(root, incremental=True)


def _run_import_unlocked(project_root: Path, *, incremental: bool) -> dict:
    try:
        from . import cnw_import_workflow
    except ImportError:
        import cnw_import_workflow
    return cnw_import_workflow._run_import(project_root, incremental=incremental)


def semantic_import(project_root: str | Path, *, incremental: bool = False) -> dict:
    try:
        from .cnw_import_workflow import run_import
    except ImportError:
        from cnw_import_workflow import run_import
    return run_import(project_root, incremental=incremental)


def canon_audit(project_root: str | Path, *, scope: str = "full", chapters=(), target: str | None = None) -> dict:
    try:
        from .cnw_maintenance import run_maintenance
    except ImportError:
        from cnw_maintenance import run_maintenance
    return run_maintenance(project_root, "audit", scope=scope, chapters=chapters, target=target)


def handoff(project_root: str | Path, *, pipeline: bool = False) -> dict:
    try:
        from .cnw_maintenance import run_maintenance
    except ImportError:
        from cnw_maintenance import run_maintenance
    return run_maintenance(project_root, "handoff", pipeline=pipeline)


def standard_operation(project_root, operation, *, sources=(), target=None, revision_approval=None):
    try:
        from .cnw_maintenance import run_maintenance
    except ImportError:
        from cnw_maintenance import run_maintenance
    return run_maintenance(project_root, operation, sources=sources, target=target, revision_approval=revision_approval)


def support_workflow_prompt(project_root: str | Path, number: str) -> dict:
    """Emit the pinned author prompt for operator/AI use. No AI result is fabricated."""
    if number not in SUPPORT_WORKFLOW_SOURCE:
        raise ContractError("SUPPORT_WORKFLOW_UNKNOWN", number)
    root = Path(project_root).resolve(strict=True)
    if not root.is_relative_to((ROOT / "workspace").resolve()):
        _registered_project_identity(root)
    source = REFERENCE_ROOT / SUPPORT_WORKFLOW_SOURCE[number]
    if not source.is_file():
        raise ContractError("SUPPORT_WORKFLOW_SOURCE_MISSING", str(source))
    prompt = source.read_text(encoding="utf-8-sig")
    out_dir = root / "93_exports/support_workflows"
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{number}_prompt.md"
    output.write_text(prompt, encoding="utf-8")
    _append_log(root, f"Workflow {number} prompt exported for operator/AI run")
    return {"status": "SUPPORT_WORKFLOW_PROMPT_EXPORTED", "workflow": number, "source": SUPPORT_WORKFLOW_SOURCE[number], "path": output.relative_to(root).as_posix(), "note": "AI 归纳步骤由操作者按原作者提示词运行；本工具不伪造其结果。", "provider_call": "none"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("setup", help="select and persist an explicit private DataHome")
    setup.add_argument("--data-home", required=True)
    setup.add_argument("--pointer-path")
    registered_init = sub.add_parser("registered-init", help="create a registered project instance in an explicitly selected DataHome")
    registered_init.add_argument("--project-id", required=True)
    registered_init.add_argument("--display-name", default="")
    registered_init.add_argument("--data-home", required=True)
    registered_import = sub.add_parser("registered-import", help="create a new registered project and import one explicitly selected source")
    registered_import.add_argument("--project-id", required=True)
    registered_import.add_argument("--display-name", default="")
    registered_import.add_argument("--data-home", required=True)
    registered_import.add_argument("--input", required=True)
    registered_import.add_argument("--format", choices=("md", "txt", "json"))
    source_import = sub.add_parser("source-import", help="import a source revision into an explicitly selected registered project")
    source_import.add_argument("--project-root", required=True)
    source_import.add_argument("--input", required=True)
    source_import.add_argument("--format", choices=("md", "txt", "json"))
    registered_incremental = sub.add_parser("registered-incremental", help="append a source revision and run Workflow 02 in an explicitly selected registered project")
    registered_incremental.add_argument("--project-root", required=True)
    registered_incremental.add_argument("--input", required=True)
    registered_incremental.add_argument("--format", choices=("md", "txt", "json"))
    source_list = sub.add_parser("source-list", help="list verified source IDs and immutable revisions without exposing source text")
    source_list.add_argument("--project-root", required=True)
    init = sub.add_parser("init")
    init.add_argument("--project-id", required=True)
    init.add_argument("--workspace-root", required=True)
    imp = sub.add_parser("import-source")
    imp.add_argument("--project-id", required=True)
    imp.add_argument("--workspace-root", required=True)
    imp.add_argument("--input", required=True)
    imp.add_argument("--format", choices=("md", "txt", "json"))
    initial = sub.add_parser("initial-import", help="Run author Workflow 01 using the shared DeepSeek cost guard")
    initial.add_argument("--project-root", required=True)
    update = sub.add_parser("update-inbox", help="Run author Workflow 02 on only new/changed inbox material")
    update.add_argument("--project-root", required=True)
    draft = sub.add_parser("draft-contract")
    draft.add_argument("--project-root", required=True)
    draft.add_argument("--draft", required=True, help="private JSON with source anchors, overall length and assignment boundaries; Plot designs structure")
    contract_preflight = sub.add_parser("contract-preflight", help="validate one v2 work contract and build its Plot request without writing or calling a provider")
    contract_preflight.add_argument("--project-root", required=True)
    contract_preflight.add_argument("--contract", required=True)
    contract_preflight.add_argument("--run-id", required=True, help="name a future run identity; no directory is created or reserved")
    contract_preflight.add_argument("--evidence-json", help="explicit existing preflight evidence JSON to verify against current inputs")
    incr = sub.add_parser("incremental-update")
    incr.add_argument("--project-id", required=True)
    incr.add_argument("--workspace-root", required=True)
    incr.add_argument("--input", required=True)
    audit = sub.add_parser("canon-audit")
    audit.add_argument("--project-root", required=True)
    audit.add_argument("--scope", choices=("full", "light", "targeted"), default="full")
    audit.add_argument("--chapter", action="append", default=[], help="private 07_draft path for a light audit")
    audit.add_argument("--target", help="subsystem for a targeted audit, e.g. timeline")
    hoff = sub.add_parser("handoff")
    hoff.add_argument("--project-root", required=True)
    hoff.add_argument("--pipeline", action="store_true")
    standard = sub.add_parser("standard-operation")
    standard.add_argument("--project-root", required=True)
    standard.add_argument("--operation", required=True, choices=("decompose", "extract_canon", "jet_diagnostic", "character_os", "revision_plan", "revision_apply"))
    standard.add_argument("--source", action="append", default=[])
    standard.add_argument("--target", help="character, time point or other requested scope; source-derived only")
    standard.add_argument("--revision-approval", help="explicitly selected project-relative author_decisions JSON; not Provider authorization")
    support = sub.add_parser("support-workflow")
    support.add_argument("--project-root", required=True)
    support.add_argument("--number", required=True, choices=tuple(SUPPORT_WORKFLOW_SOURCE))
    args = parser.parse_args(argv)
    if args.command == "setup":
        try:
            from .project_paths import setup_data_home
        except ImportError:
            from project_paths import setup_data_home
        selected = setup_data_home(args.data_home, pointer_path=args.pointer_path)
        result = {"status": "DATA_HOME_READY", "data_home": str(selected), "provider_call": "none"}
    elif args.command == "source-list":
        result = list_source_revisions(args.project_root)
    elif args.command == "registered-init":
        try:
            from .project_paths import create_project
        except ImportError:
            from project_paths import create_project
        project = create_project(project_id=args.project_id, display_name=args.display_name or args.project_id,
                                 data_home=args.data_home)
        result = init_registered_project(project["project_root"])
    elif args.command == "registered-import":
        try:
            from .project_paths import create_project
        except ImportError:
            from project_paths import create_project
        if args.format and Path(args.input).suffix.lower().lstrip(".") != args.format:
            raise ContractError("IMPORT_FORMAT_MISMATCH", args.format)
        project = create_project(project_id=args.project_id, display_name=args.display_name or args.project_id,
                                 data_home=args.data_home)
        init_registered_project(project["project_root"])
        imported = import_source(input_file=args.input, project_root=project["project_root"])
        result = {**project, "status": "SOURCE_IMPORTED", "import": imported, "provider_call": "none"}
    elif args.command == "source-import":
        if args.format and Path(args.input).suffix.lower().lstrip(".") != args.format:
            raise ContractError("IMPORT_FORMAT_MISMATCH", args.format)
        result = import_source(input_file=args.input, project_root=args.project_root)
    elif args.command == "registered-incremental":
        root = Path(args.project_root).resolve(strict=True)
        _registered_project_identity(root)
        if not (root / "00_meta/import_state.json").is_file():
            raise ContractError("INCREMENTAL_REQUIRES_INITIAL_IMPORT", "run Workflow 01 before an incremental source update")
        if args.format and Path(args.input).suffix.lower().lstrip(".") != args.format:
            raise ContractError("IMPORT_FORMAT_MISMATCH", args.format)
        imported = import_source(input_file=args.input, project_root=root)
        result = semantic_import(root, incremental=True)
        result["source_revision_id"] = imported["source_revision_id"]
        result["project_instance_id"] = json.loads((root / "project_identity.json").read_text(encoding="utf-8"))["project_instance_id"]
    elif args.command == "init":
        result = init_project(args.workspace_root, args.project_id)
    elif args.command == "import-source":
        if args.format and Path(args.input).suffix.lower().lstrip(".") != args.format:
            raise ContractError("IMPORT_FORMAT_MISMATCH", args.format)
        result = import_source(args.workspace_root, args.project_id, args.input)
    elif args.command == "incremental-update":
        result = incremental_update(args.workspace_root, args.project_id, args.input)
    elif args.command in ("initial-import", "update-inbox"):
        result = semantic_import(args.project_root, incremental=args.command == "update-inbox")
    elif args.command == "canon-audit":
        result = canon_audit(args.project_root, scope=args.scope, chapters=args.chapter, target=args.target)
    elif args.command == "handoff":
        result = handoff(args.project_root, pipeline=args.pipeline)
    elif args.command == "standard-operation":
        result = standard_operation(args.project_root, args.operation, sources=args.source, target=args.target, revision_approval=args.revision_approval)
    elif args.command == "support-workflow":
        result = support_workflow_prompt(args.project_root, args.number)
    elif args.command == "contract-preflight":
        if args.evidence_json:
            evidence_path = Path(args.evidence_json).resolve(strict=True)
            try:
                evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ContractError("PREFLIGHT_EVIDENCE_INVALID", str(exc)) from exc
            result = verify_contract_preflight(args.project_root, args.contract, run_id=args.run_id, evidence=evidence)
        else:
            result = build_contract_preflight(args.project_root, args.contract, run_id=args.run_id)
    else:
        result = write_contract_draft(args.project_root, args.draft)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"CNW_PROJECT_FAILED:{exc}", file=sys.stderr)
        raise SystemExit(2)
