"""Execute pinned CNW import/update prompts with source-linked classifications.

All source, model output, receipts and transaction journals stay in workspace.
The transport uses the existing DeepSeek campaign ledger and receipt cache.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from .cnw_contract import ContractError, assert_output_within_root
    from .cnw_roles import _pinned_upstream
    from .cnw_runner import ROOT, cnw_live_call, locked_run, sha, save_state
    from . import cnw_runner as runner
except ImportError:
    from cnw_contract import ContractError, assert_output_within_root
    from cnw_roles import _pinned_upstream
    from cnw_runner import ROOT, cnw_live_call, locked_run, sha, save_state
    import cnw_runner as runner

DOCUMENTS = (
    "00_meta/project_index.md", "01_theme/theme.md", "02_logline/logline.md",
    "03_project_design/project_design.md", "04_chapter_design/arc_index.md",
    "90_canon/canon.md", "90_canon/character_bible.md", "93_exports/handoff_brief.md",
)
STATUSES = {"CONFIRMED", "INFERRED", "TODO_CONFIRM"}
STATE = "00_meta/import_state.json"
PENDING = "00_meta/import_pending.json"
DESIGN_FOLDERS = {"01_theme", "02_logline", "03_project_design", "04_chapter_design", "90_canon"}
UPDATE_FOLDERS = DESIGN_FOLDERS | {"05_scene_cards", "06_plot", "08_review"}
# Adapter capacity, not an author method rule. The shared ledger reserves the
# entire ceiling; truncated responses are retained and never parsed as success.
IMPORT_OUTPUT_CAP = 12000
FACT_SOURCE_KINDS = {"original", "confirmed_canon"}


def _internal_inbox_metadata(name: str) -> bool:
    """Source registries and frozen identity snapshots are not manuscripts."""
    return name in {"_INBOX/source_manifest.json", "_INBOX/source_index.json"} or name.startswith(("_INBOX/revisions/", "_INBOX/input_packs/"))


def _confirmed_canon_sources(previous: dict, existing: dict[str, str]) -> dict[str, dict]:
    """Expose only retained, source-backed Canon claims, never a whole mixed file."""
    def fact_backed(claim, trail):
        for ref, kind in claim.get("source_kinds", {}).items():
            if ref not in claim.get("sources", {}) or _internal_inbox_metadata(ref):
                continue
            if kind == "original":
                return True
            if kind == "confirmed_canon" and ref.startswith("confirmed_canon:"):
                parent_id = ref.rsplit(":", 1)[-1]
                parent = previous.get("claims", {}).get(parent_id, {})
                if (parent_id not in trail and parent.get("status") == "CONFIRMED"
                        and parent.get("source_role", "story_fact") == "story_fact"
                        and ref == f"confirmed_canon:{parent.get('document')}:{parent_id}"
                        and claim["sources"][ref] == sha(parent.get("text", "").encode("utf-8"))
                        and fact_backed(parent, trail | {parent_id})):
                    return True
        return False
    result = {}
    for claim_id, claim in previous.get("claims", {}).items():
        name, text = claim.get("document", ""), claim.get("text", "")
        if (claim.get("status") != "CONFIRMED" or claim.get("source_role", "story_fact") != "story_fact"
                or not name.startswith("90_canon/")
                or name == "90_canon/unresolved_questions.md" or not text
                or f"{text}\n\nClassification: CONFIRMED\nSource:" not in existing.get(name, "")
                or not fact_backed(claim, {claim_id})):
            continue
        ref = f"confirmed_canon:{name}:{claim_id}"
        result[ref] = {"text": text, "sha256": sha(text.encode("utf-8")),
                       "kind": "confirmed_canon", "document": name, "claim_id": claim_id,
                       "document_text_sha256": sha(existing[name].encode("utf-8"))}
    return result


def _document_allowed(name: str, *, incremental=False) -> bool:
    path = Path(name)
    return (isinstance(name, str) and not path.anchor and not path.drive and ".." not in path.parts
            and path.suffix.lower() == ".md" and (name in (*DOCUMENTS, "00_meta/source_log.md", "00_meta/ai_work_log.md") or path.parts[0] in (UPDATE_FOLDERS if incremental else DESIGN_FOLDERS)))


def _json(text: str) -> dict:
    if text.strip().startswith("```"):
        text = "\n".join(text.strip().splitlines()[1:-1])
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ContractError("IMPORT_RESPONSE_INVALID", "expected JSON object")
    return value


def _inventory(root: Path) -> dict[str, dict]:
    inbox = root / "_INBOX"
    result = {}
    for file in sorted(inbox.rglob("*")):
        relative = file.relative_to(root).as_posix()
        assert_output_within_root(root, relative)
        if not file.is_file() or _internal_inbox_metadata(relative):
            continue
        if file.suffix.lower() not in {".md", ".txt", ".json"}:
            raise ContractError("IMPORT_NEEDS_FORMAT_ADAPTER", relative)
        raw = file.read_bytes()
        result[relative] = {"sha256": sha(raw), "text": raw.decode("utf-8-sig")}
    if not result:
        raise ContractError("IMPORT_SOURCE_EMPTY", "no supported inbox material")
    return result


def _record_classification(run_dir: Path, kind: str, data: dict) -> None:
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    digest = sha(raw)
    relative = f"artifacts/{kind}-{digest}.json"
    path = assert_output_within_root(run_dir, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != raw:
        raise ContractError("IMPORT_CLASSIFICATION_CHANGED", relative)
    if not path.exists():
        path.write_bytes(raw)
    state = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))
    row = {"kind": kind, "path": relative, "sha256": digest}
    if row not in state.setdefault("import_artifacts", []):
        state["import_artifacts"].append(row)
        save_state(run_dir, state)


def _apply(root: Path, run_dir: Path, journal: dict) -> None:
    """Idempotent recovery: each file must equal its preimage or postimage."""
    for relative, row in journal["writes"].items():
        path = assert_output_within_root(root, relative)
        current = sha(path.read_bytes()) if path.exists() else None
        if current not in (row["before_sha256"], sha(row["text"].encode("utf-8"))):
            raise ContractError("IMPORT_CONCURRENT_EDIT", relative)
    for relative, row in journal["writes"].items():
        path = assert_output_within_root(root, relative)
        if path.exists() and sha(path.read_bytes()) == sha(row["text"].encode("utf-8")):
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = assert_output_within_root(root, relative + ".import-tmp")
        if temporary.exists() and temporary.read_bytes() != row["text"].encode("utf-8"):
            raise ContractError("IMPORT_CONCURRENT_EDIT", relative + ".import-tmp")
        temporary.write_text(row["text"], encoding="utf-8", newline="")
        temporary.replace(path)
    (run_dir / "COMMITTED").write_text("Import transaction committed.\n", encoding="utf-8")


def run_import(project_root: str | Path, *, incremental: bool = False) -> dict:
    root = Path(project_root).resolve(strict=True)
    if not root.is_relative_to((ROOT / "workspace").resolve()):
        try:
            from .cnw_project import _registered_project_identity
        except ImportError:
            from cnw_project import _registered_project_identity
        _registered_project_identity(root)
    try:
        from .project_transactions import project_write_lock
    except ImportError:
        from project_transactions import project_write_lock
    with project_write_lock(root):
        return _run_import(root, incremental=incremental)


def _reconsume_bookkeeping_response(run, stage, messages):
    """A log-output whitelist correction does not require new story generation."""
    current = json.loads(messages[1]["content"])
    for row in runner.cached_receipts(runner.load_state(run)):
        if row.get("status") != "SUCCEEDED" or row.get("stage") != stage or row.get("role_id") != "project_organization" or not row.get("request_path"):
            continue
        content = runner._receipt_content(run, row)
        old_body = json.loads(assert_output_within_root(run, row["request_path"]).read_text(encoding="utf-8"))
        old_messages = old_body.get("messages", [])
        if len(old_messages) != 2 or old_messages[0] != messages[0] or old_body.get("model") != runner.MODEL or old_body.get("max_tokens") != IMPORT_OUTPUT_CAP:
            continue
        expected = sha(json.dumps({"stage": stage, "role_id": "project_organization", "messages": old_messages,
            "output_cap": IMPORT_OUTPUT_CAP, "model": runner.MODEL, "url": runner.API_URL, "extra": None}, ensure_ascii=False, sort_keys=True).encode())
        if row.get("request_fingerprint") != expected:
            continue
        old = json.loads(old_messages[1]["content"])
        old_allowed, new_allowed = set(old.get("allowed_existing_documents", [])), set(current.get("allowed_existing_documents", []))
        if old_allowed == new_allowed or not old_allowed.issubset(new_allowed) or not (new_allowed - old_allowed).issubset({"00_meta/source_log.md", "00_meta/ai_work_log.md"}):
            continue
        if {k: v for k, v in old.items() if k != "allowed_existing_documents"} != {k: v for k, v in current.items() if k != "allowed_existing_documents"}:
            continue
        _record_classification(run, "response_reconsume", {"provider_request_id": row["provider_request_id"],
            "original_request_sha256": row["request_sha256"], "original_output_sha256": row["output_sha256"],
            "current_message_sha256": sha(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()),
            "reason": "Only allowed bookkeeping output paths expanded; source text and complete method unchanged. Original receipt identity retained."})
        return content, row
    return None


def _run_import(root: Path, *, incremental: bool) -> dict:
    pending = assert_output_within_root(root, PENDING)
    pending.parent.mkdir(parents=True, exist_ok=True)
    if pending.exists():
        pointer = _json(pending.read_text(encoding="utf-8"))
        journal_path = assert_output_within_root(root, pointer["journal"])
        journal = _json(journal_path.read_text(encoding="utf-8"))
        if {k: v["sha256"] for k, v in _inventory(root).items()} != journal["source_hashes"]:
            raise ContractError("IMPORT_SOURCE_CHANGED", "cannot recover against changed sources")
        _apply(root, journal_path.parent, journal)
        pending.unlink()
        return journal["result"]
    state_path = assert_output_within_root(root, STATE)
    previous = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    if incremental and not previous:
        raise ContractError("INCREMENTAL_REQUIRES_INITIAL_IMPORT", "complete semantic import first")
    if not incremental and previous:
        raise ContractError("INITIAL_IMPORT_ALREADY_COMPLETE", "use incremental update")
    inventory = _inventory(root)
    selected = {name: item for name, item in inventory.items()
                if previous.get("sources", {}).get(name) != item["sha256"]}
    if not selected:
        return {"status": "NO_NEW_OR_CHANGED_SOURCES", "provider_call": "none"}
    existing = {}
    existing_names = set((*DOCUMENTS, "90_canon/unresolved_questions.md", "00_meta/source_log.md", "00_meta/ai_work_log.md"))
    folders = UPDATE_FOLDERS if incremental else DESIGN_FOLDERS
    for folder in folders:
        for path in (root / folder).rglob("*.md"):
            existing_names.add(path.relative_to(root).as_posix())
    for name in sorted(existing_names):
        path = assert_output_within_root(root, name)
        existing[name] = path.read_text(encoding="utf-8") if path.exists() else ""
    identity = sha(json.dumps({"sources": {k: v["sha256"] for k, v in selected.items()},
        "previous": previous, "existing": existing, "incremental": incremental}, ensure_ascii=False, sort_keys=True).encode())
    run_dir = assert_output_within_root(root, "94_runtime/imports/" + identity[:24])
    run_dir.mkdir(parents=True, exist_ok=True)
    journal_path = run_dir / "transaction.json"
    if journal_path.exists():
        journal = _json(journal_path.read_text(encoding="utf-8"))
        pending.write_text(json.dumps({"journal": journal_path.relative_to(root).as_posix()}), encoding="utf-8")
        _apply(root, run_dir, journal)
        pending.unlink()
        return journal["result"]
    if not (run_dir / "run_state.json").exists():
        save_state(run_dir, {"run_id": run_dir.name, "schema_version": "cnw_import_run_v1", "provider_requests": []})
    snapshots = run_dir / "artifacts/source_snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    for name, item in selected.items():
        raw = assert_output_within_root(root, name).read_bytes()
        if sha(raw) != item["sha256"]:
            raise ContractError("IMPORT_SOURCE_CHANGED", name)
        snapshot = snapshots / (item["sha256"] + ".bin")
        if snapshot.exists() and sha(snapshot.read_bytes()) != item["sha256"]:
            raise ContractError("IMPORT_SOURCE_SNAPSHOT_CHANGED", name)
        if not snapshot.exists():
            snapshot.write_bytes(raw)
    method = "02_incremental_update" if incremental else "01_first_import"
    workflow_path = f"templates/_workflows/{method}.md"
    upstream, _ = _pinned_upstream(workflow_path)
    stage = "project_update" if incremental else "project_import"
    instruction, _ = _pinned_upstream("templates/CLAUDE.md")
    author_sources = {}
    for name in ("templates/CLAUDE.md", workflow_path,
        "templates/90_canon/canon.template.md",
        "templates/04_chapter_design/arc_index.template.md",
        "templates/90_canon/character_bible.template.md"):
        text, blob = _pinned_upstream(name)
        author_sources["author:" + name] = {"text": text, "sha256": sha(text.encode()),
                                           "kind": "public_method", "upstream_git_blob": blob}
    project_instruction = next((root / name for name in ("AGENTS.md", "CLAUDE.md") if (root / name).is_file()), None)
    extension = ""
    if project_instruction:
        text = project_instruction.read_text(encoding="utf-8-sig")
        name = "project:" + project_instruction.name
        author_sources[name] = {"text": text, "sha256": sha(text.encode()), "kind": "project_instructions"}
        if text != instruction:
            extension = "\nProject instruction extensions:\n" + text
    reference_templates = "\n".join(f"{name}\n{row['text']}" for name, row in author_sources.items()
                                    if name not in {"author:templates/CLAUDE.md", "author:" + workflow_path}
                                    and row["kind"] == "public_method")
    source_bindings = {**{name: {**row, "kind": "original"} for name, row in selected.items()}, **author_sources}
    for name, text in existing.items():
        if text:
            source_bindings[name] = {"text": text, "sha256": sha(assert_output_within_root(root, name).read_bytes()), "kind": "project_context"}
    confirmed_canon = _confirmed_canon_sources(previous, existing)
    source_bindings.update(confirmed_canon)
    messages = [
        {"role": "system", "content": instruction + extension + "\nOfficial workflow:\n" + upstream + '\nTransport format for the official workflow: read every supplied original in full and perform its internal passes, then return JSON {"source_notes":{"source path":"brief inventory description"},"documents":{"allowed/path.md":[{"status":"CONFIRMED|INFERRED|TODO_CONFIRM","text":"organized Markdown section","source_refs":["original source or author reference identifier"]}]},"conflicts":[{"old_file":"existing or generated document","old_quote":"literal old passage","new_file":"generated document path","new_entry":0,"reason":"actual contradiction"}],"next_action":"one specific action"}. No preliminary line-by-line transcription or separate claim inventory is required. Use the source language for Markdown prose; copy all file and source identifiers exactly without translating them. Bind story assertions to original_sources, and operating instructions to author_reference_sources; template placeholders are not story facts. Use each document\'s purpose: project index, rough concept/design, confirmed canon/character index and calling rules, complete chapter/scene structure, theme/logline, unresolved author decisions, work handoff. Classify information as the author specifies; faithful paraphrase is allowed. Canon sections must be CONFIRMED and supported by their original source_refs. Inferences and gaps belong in design or unresolved questions, not canon. Distinguish conditional routes/design instructions from events that happened; preserve actors, conditions, time, negation and attribution. Reconcile information across all originals before calling something an author question. Do not invent facts. For an update, append only relevant new conclusions and preserve old ones. Judge contradictions by meaning, not string differences, synonyms or distinct events; cite both versions and do not resolve them. For conflicts within new output also supply old_entry, the old section index in documents[old_file]. new_entry is the zero-based index of the new conflicting section within documents[new_file]; it will be withheld and logged as a conflict. Reference templates (placeholders/examples are not project facts):\n' + reference_templates},
        {"role": "user", "content": json.dumps({**({"required_initial_documents": list(DOCUMENTS)} if not incremental else {}), "allowed_existing_documents": [name for name in existing if _document_allowed(name, incremental=incremental)], "allowed_new_markdown_folders": sorted(folders), "original_sources": selected, "author_reference_sources": author_sources, "existing_documents": existing, **({"confirmed_canon_sources": confirmed_canon} if confirmed_canon else {})}, ensure_ascii=False)},
    ]
    messages[0]["content"] += (
        "\nEach entry may include source_role=story_fact (default) or method_metadata; this is provenance scope, "
        "not an extra certainty class or workflow stage. Story CONFIRMED requires original_sources or an exact "
        "confirmed_canon_sources identifier. Ordinary existing_documents are context, not confirmed story facts. "
        "confirmed_canon_sources contains only retained, previously confirmed source-backed Canon sections. "
        "Method metadata may be CONFIRMED from author_reference_sources of kind public_method/project_instructions, "
        "but must have source_role=method_metadata and be written only outside 90_canon. "
        "Operating templates or project instructions never confirm story facts."
    )
    _record_classification(run_dir, "import_request", {"messages": messages, "sources": {
        name: {key: value for key, value in row.items() if key != "text"} for name, row in source_bindings.items()}})
    reused_response = _reconsume_bookkeeping_response(run_dir, stage, messages)
    content, _ = reused_response or cnw_live_call(run_dir, stage=stage, role_id="project_organization", messages=messages, output_cap=IMPORT_OUTPUT_CAP)
    organized = _json(content)
    documents, conflicts, source_notes = (organized.get(key) for key in ("documents", "conflicts", "source_notes"))
    if (not isinstance(documents, dict) or not isinstance(conflicts, list) or not isinstance(source_notes, dict)
            or not isinstance(organized.get("next_action"), str) or not organized["next_action"].strip()):
        raise ContractError("IMPORT_RESPONSE_INVALID", "documents, conflicts, source_notes and next_action required")
    if set(source_notes) != set(selected) or any(not isinstance(note, str) or not note.strip() for note in source_notes.values()):
        raise ContractError("IMPORT_RESPONSE_INVALID", "inventory notes required for all selected originals")
    if not incremental and not set(DOCUMENTS).issubset(documents):
        raise ContractError("IMPORT_DOCUMENT_MISSING", "all author bootstrap outputs required")
    date = datetime.now(timezone.utc).isoformat(timespec="seconds")
    additions, claims, classified = {}, {}, {}
    for name, entries in documents.items():
        if not _document_allowed(name, incremental=incremental) or not isinstance(entries, list):
            raise ContractError("IMPORT_DOCUMENT_INVALID", str(name))
        assert_output_within_root(root, name)
        if not entries:
            if name in ("90_canon/canon.md", "90_canon/character_bible.md"):
                additions.setdefault(name, []).append("No additional CONFIRMED source statements extracted in this import.")
                continue
            raise ContractError("IMPORT_DOCUMENT_INVALID", name)
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ContractError("IMPORT_ENTRY_INVALID", name)
            status, refs, text = (entry.get(key) for key in ("status", "source_refs", "text"))
            source_role = entry.get("source_role", "story_fact")
            if (status not in STATUSES or not isinstance(refs, list)
                    or source_role not in {"story_fact", "method_metadata"}
                    or any(not isinstance(ref, str) or not ref.strip() for ref in refs)
                    or not isinstance(text, str) or not text.strip()
                    or (status != "TODO_CONFIRM" and not any(ref in source_bindings for ref in refs))):
                raise ContractError("IMPORT_ENTRY_INVALID", name)
            if Path(name).parts[0] == "90_canon" and name != "90_canon/unresolved_questions.md" and status != "CONFIRMED":
                raise ContractError("IMPORT_UNCONFIRMED_CANON", name)
            fact_sources = {ref: source_bindings[ref]["sha256"] for ref in refs
                            if ref in source_bindings and source_bindings[ref]["kind"] in FACT_SOURCE_KINDS}
            method_sources = {ref: source_bindings[ref]["sha256"] for ref in refs
                              if ref in source_bindings and source_bindings[ref]["kind"] in {"public_method", "project_instructions"}}
            if source_role == "method_metadata" and Path(name).parts[0] == "90_canon":
                raise ContractError("IMPORT_METHOD_METADATA_IN_CANON", name)
            if status == "CONFIRMED" and source_role == "story_fact" and not fact_sources:
                raise ContractError("IMPORT_CONFIRMED_FACT_SOURCE_REQUIRED", name)
            if status == "CONFIRMED" and source_role == "method_metadata" and not method_sources:
                raise ContractError("IMPORT_CONFIRMED_METHOD_SOURCE_REQUIRED", name)
            claim = {"document": name, "entry": index, "status": status, "source_role": source_role, "text": text,
                     "sources": {ref: source_bindings[ref]["sha256"] for ref in refs if ref in source_bindings},
                     "story_fact_sources": fact_sources if source_role == "story_fact" else {},
                     "operating_rule_sources": method_sources if source_role == "method_metadata" else {},
                     "source_kinds": {ref: source_bindings[ref]["kind"] for ref in refs if ref in source_bindings},
                     "unverified_source_refs": [ref for ref in refs if ref not in source_bindings]}
            claim["id"] = sha(json.dumps(claim, ensure_ascii=False, sort_keys=True).encode())[:24]
            claims[claim["id"]] = claim
            classified[name, index] = claim
    _record_classification(run_dir, "classification_organized", claims)
    conflicted = set()
    for conflict in conflicts:
        if not isinstance(conflict, dict):
            raise ContractError("IMPORT_CONFLICT_UNSUPPORTED", "expected conflict object")
        old_file, old_quote, new_file, new_entry, reason = (conflict.get(key) for key in (
            "old_file", "old_quote", "new_file", "new_entry", "reason"))
        if (not isinstance(old_file, str) or not isinstance(old_quote, str) or not old_quote.strip()
                or not isinstance(new_file, str) or type(new_entry) is not int
                or (new_file, new_entry) not in classified or not isinstance(reason, str) or not reason.strip()):
            raise ContractError("IMPORT_CONFLICT_UNSUPPORTED", "both versions and semantic reason required")
        old_entry = conflict.get("old_entry")
        if old_entry is not None:
            if type(old_entry) is not int or (old_file, old_entry) not in classified:
                raise ContractError("IMPORT_CONFLICT_UNSUPPORTED", "old entry must bind a classified document section")
            old = classified[old_file, old_entry]
            old_text = old["text"]
            if not old["sources"]:
                raise ContractError("IMPORT_CONFLICT_UNSUPPORTED", "old entry must bind original sources")
            conflicted.add(old["id"])
        else:
            old_text = existing.get(old_file)
        if not isinstance(old_text, str) or old_quote not in old_text:
            raise ContractError("IMPORT_CONFLICT_UNSUPPORTED", "old version must bind existing conclusions or a classified section")
        new = classified[new_file, new_entry]
        if not new["sources"]:
            raise ContractError("IMPORT_CONFLICT_UNSUPPORTED", "new version must bind original sources")
        conflicted.add(new["id"])
        provenance = "; ".join(f"{ref}@{digest}" for ref, digest in new["sources"].items())
        additions.setdefault("90_canon/unresolved_questions.md", []).append(
            f"## CONFLICT — {date}\nOld ({old_file}):\n{old_quote}\n\nNew ({provenance}):\n{new['text']}\n\nReason: {reason}\n\nStatus: TODO_CONFIRM — author decision required.")
    for claim in claims.values():
        if claim["id"] in conflicted:
            continue
        provenance = "; ".join(f"{ref}@{digest}" for ref, digest in claim["sources"].items())
        rendered = f"{claim['text']}\n\nClassification: {claim['status']}\nSource: {provenance or 'TODO_CONFIRM — no supporting material'}"
        if claim["unverified_source_refs"]:
            rendered += "\nUnverified source citations (not supporting provenance): " + "; ".join(claim["unverified_source_refs"])
        additions.setdefault(claim["document"], []).append(rendered)
        if claim["status"] == "TODO_CONFIRM" and claim["document"] != "90_canon/unresolved_questions.md":
            additions.setdefault("90_canon/unresolved_questions.md", []).append(rendered)

    if not incremental:
        for name in DOCUMENTS:
            additions.setdefault(name, ["No nonconflicting entries available; see 90_canon/unresolved_questions.md."])
    additions.setdefault("00_meta/source_log.md", []).extend(f"- {name} SHA256={item['sha256']} processed {date}\n  Inventory notes: {source_notes[name]}" for name, item in selected.items())
    additions.setdefault("00_meta/ai_work_log.md", []).append(f"Workflow {method}; sources={len(selected)}; classified={len(claims)}; conflicts={len(conflicts)}; created/appended={', '.join(sorted(additions))}.\nNext action: {organized['next_action']}")
    writes = {}
    for name, sections in additions.items():
        path = assert_output_within_root(root, name)
        if name not in existing and path.exists():
            raise ContractError("IMPORT_CONCURRENT_EDIT", name)
        writes[name] = {"before_sha256": sha(path.read_bytes()) if path.exists() else None,
                       "text": existing.get(name, "") + f"\n\n<!-- CNW import {identity} {date} -->\n\n" + "\n\n".join(sections) + "\n"}
    next_state = {"sources": {**previous.get("sources", {}), **{k: v["sha256"] for k, v in selected.items()}},
                  "claims": {**previous.get("claims", {}), **claims}, "last_import": identity, "updated_at": date}
    writes[STATE] = {"before_sha256": sha(state_path.read_bytes()) if state_path.exists() else None, "text": json.dumps(next_state, ensure_ascii=False, indent=2) + "\n"}
    if _inventory(root) != inventory:
        raise ContractError("IMPORT_SOURCE_CHANGED", "source changed during processing")
    for name, old in existing.items():
        path = assert_output_within_root(root, name)
        if (path.read_text(encoding="utf-8") if path.exists() else "") != old:
            raise ContractError("IMPORT_CONCURRENT_EDIT", name)
    result = {"status": "INCREMENTAL_IMPORT_COMPLETE" if incremental else "INITIAL_IMPORT_COMPLETE", "source_count": len(selected), "claim_count": len(claims), "conflicts": len(conflicts), "next_action": organized["next_action"], "run_dir": str(run_dir), "provider_call": "performed"}
    if reused_response:
        result.update(provider_call="reconsumed_existing_response", original_provider_request_id=reused_response[1]["provider_request_id"])
    journal = {"writes": writes, "result": result, "source_hashes": {k: v["sha256"] for k, v in inventory.items()}}
    journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")
    pending.write_text(json.dumps({"journal": journal_path.relative_to(root).as_posix()}), encoding="utf-8")
    _apply(root, run_dir, journal)
    pending.unlink()
    return result
