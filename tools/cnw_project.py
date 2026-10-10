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
    from .cnw_contract import ContractError, check_required_fields, validate_scene_budget, validate_source_identity, validate_work_unit
except ImportError:  # direct script execution
    from cnw_contract import ContractError, check_required_fields, validate_scene_budget, validate_source_identity, validate_work_unit

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
    for folder in ("_INBOX/originals", "00_meta", "01_theme", "02_logline", "03_project_design",
                   "04_chapter_design", "05_scene_cards", "06_plot", "07_draft", "08_review", "09_revision",
                   "90_canon", "91_jet_engine", "92_style_engine", "93_data", "93_exports",
                   "contracts", "runs"):
        (root / folder).mkdir(parents=True, exist_ok=True)
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
    return {"status": "PROJECT_READY", "project_id": project_id, "project_root": str(root), "provider_call": "none"}


def _json_scalars(value, pointer=""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _json_scalars(child, pointer + "/" + str(key).replace("~", "~0").replace("/", "~1"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _json_scalars(child, pointer + "/" + str(index))
    elif value is not None:
        yield pointer or "/", str(value)


def import_source(workspace_root: str | Path, project_id: str, input_file: str | Path) -> dict:
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
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ContractError("IMPORT_JSON_INVALID", str(exc)) from exc
        if not isinstance(parsed, (dict, list)):
            raise ContractError("IMPORT_NEEDS_FORMAT_ADAPTER", "JSON root must be an object or array")
    else:
        parsed = None
    init_project(workspace_root, project_id)
    inbox = root / "_INBOX"
    manifest_path = inbox / "source_manifest.json"
    index_path = inbox / "source_index.json"
    canon_path = root / "90_canon" / "canon_candidates.json"
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
        "schema_version": "cnw_source_manifest_v1", "project_id": project_id,
        "import_id": digest, "imported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_count": 1,
        "sources": [{"source_id": digest[:16], "original_path": str(source_path), "stored_path": original_rel.as_posix(), "format": source_path.suffix.lower().lstrip("."), "sha256": digest, "bytes": len(raw), "encoding": "utf-8", "location_count": len(locations)}],
    }
    index = {"schema_version": "cnw_source_index_v1", "project_id": project_id, "source_sha256": digest, "locations": locations}
    for location in locations:
        location["source_id"] = digest[:16]
        location["source_file"] = original_rel.as_posix()
    if previous:
        # Keep the first-import identity and every previous source revision.
        # Changed files append a new revision; prior conclusions stay intact.
        manifest = {**previous, "sources": previous["sources"] + manifest["sources"],
                    "updated_at": manifest["imported_at"]}
        manifest["source_count"] = len(manifest["sources"])
        old_locations = previous_index["locations"]
        if len(previous["sources"]) == 1:
            first = previous["sources"][0]
            old_locations = [{"source_id": first["source_id"],
                              "source_file": first["stored_path"], **item}
                             for item in old_locations]
        index = {**previous_index, "locations": old_locations + locations}
        used_ids = {item["candidate_id"] for item in previous_canon["candidates"]}
        next_id = 1
        for candidate in candidates:
            while f"C{next_id:04d}" in used_ids:
                next_id += 1
            candidate["candidate_id"] = f"C{next_id:04d}"
            used_ids.add(candidate["candidate_id"])
        candidates = previous_canon["candidates"] + candidates
    (inbox / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (inbox / "source_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    canon_document = previous_canon or {"schema_version": "cnw_canon_candidates_v1", "project_id": project_id, "policy": "Every entry requires human confirmation; importer makes no Canon inference."}
    canon_document.update(source_manifest_sha256=sha(manifest_path.read_bytes()), candidates=candidates)
    canon_path.write_text(json.dumps(canon_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "SOURCE_IMPORTED_FOR_REVIEW", "project_id": project_id, "project_root": str(root), "source_manifest": "_INBOX/source_manifest.json", "source_index": "_INBOX/source_index.json", "canon_candidates": "90_canon/canon_candidates.json", "source_sha256": digest, "source_locations": len(locations), "canon_candidate_count": len(candidates), "canon_status": "TODO_CONFIRM", "provider_call": "none"}


def build_source_bound_contract(project_root: str | Path, *, unit_id: str, pov: str, target: int, minimum: int, maximum: int, before_line: int, after_line: int, beat_specs: list[dict] | None = None, entry_state: str, exit_state: str, role_in_story: str, reader_reward: str, characters: list[str] | None = None, kind: str = "scene", planning_mode: str = "author_plot", arc_ref: str | None = None, previous_episode_ref: str | None = None, first_episode: bool | None = None) -> dict:
    root = Path(project_root).resolve()
    manifest_file = root / "_INBOX/source_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    index = json.loads((root / "_INBOX/source_index.json").read_text(encoding="utf-8"))
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
        "unit": {"id": unit_id, "kind": kind, "planning_mode": planning_mode, "language": "zh-CN", "pov": pov, "target_visible_chars": target, "min_visible_chars": minimum, "max_visible_chars": maximum, "policy_sha256": sha((ROOT / "config/cnw_production_policy.json").read_bytes())},
        "story": {**({"arc_ref": arc_ref} if arc_ref is not None else {}), **({"previous_episode_ref": previous_episode_ref} if previous_episode_ref is not None else {}), **({"first_episode": first_episode} if first_episode is not None else {}), "source_file": source["stored_path"], "chapter_context": f"Imported source {source['source_id']} with {len(index['locations'])} indexed source locations; confirm all facts before production.", "role_in_story": role_in_story, "reader_reward": reader_reward, "entry_state": entry_state, "exit_state": exit_state, "before_anchor": {"scene": "IMPORTED", "source_line": before_line, "sha256": sha(b"".join(lines[before_line-1:before_line]))}, "after_anchor": {"scene": "IMPORTED", "source_line": after_line, "sha256": sha(b"".join(lines[after_line-1:after_line]))}, "required_beats": beats, "characters_in_scene": characters or [], "character_knowledge_boundary_ref": "90_canon/canon_candidates.json#status=TODO_CONFIRM", "forbidden_future_revelations": ["Do not use unconfirmed Canon candidates or facts outside the approved Writing Brief."], "voice_sample_refs": ["90_canon/canon_candidates.json#voice-sample-review-required"]},
        "review": {"workflow_template_git_blob": "146ea01a484cc0578cf290478b3941599ad7fb15", "require_cnw_11_stages": True, "require_3_verifiers": True, "require_completeness_critic": True, "require_re_review": True, "cnw_reference_manifest_sha256": sha((ROOT / "runtime/reference/cnw_97ad71fe5e5e/CNW_LOCAL_REFERENCE_MANIFEST.json").read_bytes())},
    }


def write_contract_draft(project_root: str | Path, draft_path: str | Path) -> dict:
    root = Path(project_root).resolve(strict=True)
    if not root.is_relative_to((ROOT / "workspace").resolve()):
        raise ContractError("PROJECT_ROOT_OUTSIDE_PRIVATE_WORKSPACE", str(root))
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
    contract = build_source_bound_contract(root, unit_id=unit_id, pov=draft["pov"], target=draft["target_visible_chars"], minimum=draft["min_visible_chars"], maximum=draft["max_visible_chars"], before_line=draft["before_line"], after_line=draft["after_line"], beat_specs=draft.get("required_beats", []), entry_state=draft["entry_state"], exit_state=draft["exit_state"], role_in_story=draft["role_in_story"], reader_reward=draft["reader_reward"], characters=draft.get("characters_in_scene"), kind=draft.get("kind", "scene"), planning_mode=draft.get("planning_mode", "author_plot"), arc_ref=draft.get("arc_ref"), previous_episode_ref=draft.get("previous_episode_ref"), first_episode=draft.get("first_episode"))
    check_required_fields(contract)
    validate_work_unit(contract)
    manifest = json.loads((root / "_INBOX/source_manifest.json").read_text(encoding="utf-8"))
    validate_source_identity(contract, source_root=root, expected_version=contract["source"]["version"], expected_zip_sha256=manifest["import_id"], expected_manifest_sha256=contract["source"]["source_manifest_sha256"])
    output = root / "contracts" / f"{contract['unit']['id']}.json"
    if output.exists():
        raise ContractError("CONTRACT_OUTPUT_COLLISION", output.name)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "CONTRACT_DRAFT_READY_FOR_HUMAN_PREFLIGHT", "project_id": contract["project_id"], "contract": str(output), "contract_sha256": sha(output.read_bytes()), "source_manifest_sha256": contract["source"]["source_manifest_sha256"], "provider_call": "none"}


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
    manifest_file = root / "_INBOX/source_manifest.json"
    if not manifest_file.is_file():
        raise ContractError("INCREMENTAL_REQUIRES_EXISTING_PROJECT", "run Workflow 01 first")
    if not (root / "00_meta/import_state.json").is_file():
        raise ContractError("INCREMENTAL_REQUIRES_INITIAL_IMPORT", "run initial-import first")
    import_source(workspace_root, project_id, input_file)
    return semantic_import(root, incremental=True)


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


def standard_operation(project_root, operation, *, sources=(), target=None):
    try:
        from .cnw_maintenance import run_maintenance
    except ImportError:
        from cnw_maintenance import run_maintenance
    return run_maintenance(project_root, operation, sources=sources, target=target)


def support_workflow_prompt(project_root: str | Path, number: str) -> dict:
    """Emit the pinned author prompt for operator/AI use. No AI result is fabricated."""
    if number not in SUPPORT_WORKFLOW_SOURCE:
        raise ContractError("SUPPORT_WORKFLOW_UNKNOWN", number)
    root = Path(project_root).resolve(strict=True)
    if not root.is_relative_to((ROOT / "workspace").resolve()):
        raise ContractError("PROJECT_ROOT_OUTSIDE_PRIVATE_WORKSPACE", str(root))
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
    standard.add_argument("--operation", required=True, choices=("decompose", "extract_canon", "jet_diagnostic", "character_os", "revision_plan"))
    standard.add_argument("--source", action="append", default=[])
    standard.add_argument("--target", help="character, time point or other requested scope; source-derived only")
    support = sub.add_parser("support-workflow")
    support.add_argument("--project-root", required=True)
    support.add_argument("--number", required=True, choices=tuple(SUPPORT_WORKFLOW_SOURCE))
    args = parser.parse_args(argv)
    if args.command == "init":
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
        result = standard_operation(args.project_root, args.operation, sources=args.source, target=args.target)
    elif args.command == "support-workflow":
        result = support_workflow_prompt(args.project_root, args.number)
    else:
        result = write_contract_draft(args.project_root, args.draft)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"CNW_PROJECT_FAILED:{exc}", file=sys.stderr)
        raise SystemExit(2)
