"""Private, source-preserving import tools for new CNW projects.

Imports never infer confirmed Canon. Every extracted passage is a source-linked
candidate marked TODO_CONFIRM until a human establishes project facts.
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
    from .cnw_contract import ContractError, check_required_fields, validate_scene_budget, validate_source_identity
except ImportError:  # direct script execution
    from cnw_contract import ContractError, check_required_fields, validate_scene_budget, validate_source_identity

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
    for folder in ("_INBOX/originals", "90_canon", "contracts", "06_plot", "05_scene_cards", "07_draft", "runs"):
        (root / folder).mkdir(parents=True, exist_ok=True)
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
    inbox = root / "_INBOX"
    (inbox / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (inbox / "source_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    canon_path = root / "90_canon" / "canon_candidates.json"
    canon_path.write_text(json.dumps({"schema_version": "cnw_canon_candidates_v1", "project_id": project_id, "source_manifest_sha256": sha((inbox / "source_manifest.json").read_bytes()), "policy": "Every entry requires human confirmation; importer makes no Canon inference.", "candidates": candidates}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "SOURCE_IMPORTED_FOR_REVIEW", "project_id": project_id, "project_root": str(root), "source_manifest": "_INBOX/source_manifest.json", "source_index": "_INBOX/source_index.json", "canon_candidates": "90_canon/canon_candidates.json", "source_sha256": digest, "source_locations": len(locations), "canon_candidate_count": len(candidates), "canon_status": "TODO_CONFIRM", "provider_call": "none"}


def build_source_bound_contract(project_root: str | Path, *, unit_id: str, pov: str, target: int, minimum: int, maximum: int, before_line: int, after_line: int, beat_specs: list[dict], entry_state: str, exit_state: str, role_in_story: str, reader_reward: str, characters: list[str] | None = None) -> dict:
    root = Path(project_root).resolve()
    manifest_file = root / "_INBOX/source_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    index = json.loads((root / "_INBOX/source_index.json").read_text(encoding="utf-8"))
    source = manifest["sources"][0]
    raw_path = root / source["stored_path"]
    lines = raw_path.read_bytes().splitlines(keepends=True)
    if min(before_line, after_line) < 1 or max(before_line, after_line) > len(lines) or after_line <= before_line:
        raise ContractError("SOURCE_ANCHOR_INVALID", "line anchors must exist and after_line must follow before_line")
    beats = [{"beat_id": item["beat_id"], "goal": item["goal"], "min_coverage": item.get("min_coverage", "source_supported_action"), "budget_visible_chars": item["budget_visible_chars"]} for item in beat_specs]
    if sum(item["budget_visible_chars"] for item in beats) != target:
        raise ContractError("SCENE_BUDGET_SUM_MISMATCH", "explicit beat budgets must sum to target")
    return {
        "schema_version": "cnw_work_unit_v1", "project_id": manifest["project_id"], "status": "PROPOSED_FOR_HUMAN_PREFLIGHT",
        "source": {"identity_type": "imported_project", "version": "IMPORTED-SOURCE-v1", "import_id": manifest["import_id"], "source_file_sha256": source["sha256"], "source_manifest_sha256": sha(manifest_file.read_bytes()), "manifest_file": "_INBOX/source_manifest.json", "source_root": "."},
        "unit": {"id": unit_id, "kind": "scene", "language": "zh-CN", "pov": pov, "target_visible_chars": target, "min_visible_chars": minimum, "max_visible_chars": maximum, "policy_sha256": sha((ROOT / "config/cnw_production_policy.json").read_bytes())},
        "story": {"source_file": source["stored_path"], "chapter_context": f"Imported source {source['source_id']} with {len(index['locations'])} indexed source locations; confirm all facts before production.", "role_in_story": role_in_story, "reader_reward": reader_reward, "entry_state": entry_state, "exit_state": exit_state, "before_anchor": {"scene": "IMPORTED", "source_line": before_line, "sha256": sha(b"".join(lines[before_line-1:before_line]))}, "after_anchor": {"scene": "IMPORTED", "source_line": after_line, "sha256": sha(b"".join(lines[after_line-1:after_line]))}, "required_beats": beats, "characters_in_scene": characters or [], "character_knowledge_boundary_ref": "90_canon/canon_candidates.json#status=TODO_CONFIRM", "forbidden_future_revelations": ["Do not use unconfirmed Canon candidates or facts outside the approved Writing Brief."], "voice_sample_refs": ["90_canon/canon_candidates.json#voice-sample-review-required"]},
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
    contract = build_source_bound_contract(root, unit_id=unit_id, pov=draft["pov"], target=draft["target_visible_chars"], minimum=draft["min_visible_chars"], maximum=draft["max_visible_chars"], before_line=draft["before_line"], after_line=draft["after_line"], beat_specs=draft["required_beats"], entry_state=draft["entry_state"], exit_state=draft["exit_state"], role_in_story=draft["role_in_story"], reader_reward=draft["reader_reward"], characters=draft.get("characters_in_scene"))
    check_required_fields(contract)
    validate_scene_budget(contract)
    manifest = json.loads((root / "_INBOX/source_manifest.json").read_text(encoding="utf-8"))
    validate_source_identity(contract, source_root=root, expected_version=contract["source"]["version"], expected_zip_sha256=manifest["import_id"], expected_manifest_sha256=contract["source"]["source_manifest_sha256"])
    output = root / "contracts" / f"{contract['unit']['id']}.json"
    if output.exists():
        raise ContractError("CONTRACT_OUTPUT_COLLISION", output.name)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "CONTRACT_DRAFT_READY_FOR_HUMAN_PREFLIGHT", "project_id": contract["project_id"], "contract": str(output), "contract_sha256": sha(output.read_bytes()), "source_manifest_sha256": contract["source"]["source_manifest_sha256"], "provider_call": "none"}


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
    draft = sub.add_parser("draft-contract")
    draft.add_argument("--project-root", required=True)
    draft.add_argument("--draft", required=True, help="private JSON containing source line anchors, explicit beat budgets, and scene facts")
    args = parser.parse_args(argv)
    if args.command == "init":
        result = init_project(args.workspace_root, args.project_id)
    elif args.command == "import-source":
        if args.format and Path(args.input).suffix.lower().lstrip(".") != args.format:
            raise ContractError("IMPORT_FORMAT_MISMATCH", args.format)
        result = import_source(args.workspace_root, args.project_id, args.input)
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
