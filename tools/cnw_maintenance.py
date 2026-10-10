"""Run public Workflow 04/05 with private receipts and recoverable publication."""
from __future__ import annotations

import json
import inspect
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from . import cnw_runner as runner
    from .cnw_contract import ContractError, assert_output_within_root
    from .cnw_roles import _pinned_upstream
except ImportError:
    import cnw_runner as runner
    from cnw_contract import ContractError, assert_output_within_root
    from cnw_roles import _pinned_upstream

AUDIT_FOLDERS = ("07_draft", "03_project_design", "90_canon", "06_plot")
HANDOFF_FOLDERS = ("00_meta", "01_theme", "02_logline", "03_project_design", "04_chapter_design",
                   "05_scene_cards", "06_plot", "07_draft", "08_review", "09_revision",
                   "90_canon", "91_jet_engine", "92_style_engine")
HANDOFF_SECTIONS = ("Project One-Liner", "Current Creative Goal", "Protected Core", "Current Draft State",
                    "Canon Warnings", "Open Questions", "Next Best Action", "File Index")
PENDING = "00_meta/maintenance_pending.json"
OUTPUT_CAPS = {"audit": 6000, "handoff": 4000}
OUTPUT_CAPS["arc_review"] = 6000
ARC_SECTIONS = ("Conclusion", "Arc Role", "Start and End States", "Whole Arc Check", "Canon Update Candidates", "Revision Direction", "Next Arc Handoff")


def _adapter_identity(operation):
    return runner.sha(json.dumps({"messages_builder": inspect.getsource(_messages),
        "source_selector": inspect.getsource(_inventory), "transport": inspect.getsource(runner._cnw_live_call_in_slot),
        "model": runner.MODEL, "url": runner.API_URL, "output_cap": OUTPUT_CAPS[operation]}, sort_keys=True).encode())


def _verify_receipt(run, journal):
    receipt = next((row for row in runner.load_state(run).get("provider_requests", [])
                    if row.get("request_id") == journal["request_id"] and row.get("status") == "SUCCEEDED"), None)
    if not receipt or not receipt.get("request_path"):
        raise ContractError("MAINTENANCE_RECEIPT_MISSING", run.name)
    runner._receipt_content(run, receipt)


def _hashes(inventory):
    return {name: row["sha256"] for name, row in inventory.items()}


def _draft_kind(name):
    stem = Path(name).stem.casefold()
    return "draft_support" if "brief" in stem or "index" in stem else "draft_prose"


def _inventory(root, options):
    names = set()
    folders = AUDIT_FOLDERS if options["operation"] == "audit" else HANDOFF_FOLDERS
    if options["operation"] == "arc_review":
        try:
            from .cnw_arc import arc_context
        except ImportError:
            from cnw_arc import arc_context
        arc = arc_context(root, options["target"])
        if arc["status"] != "ARC_READY_FOR_REVIEW":
            raise ContractError("ARC_NOT_READY", arc["status"])
        folders = ("01_theme", "02_logline", "03_project_design", "90_canon", "08_review")
        names.update([arc["arc_ref"], arc["details"], *arc["draft_paths"]])
        for name in ("00_meta/episode_production_manual.md", "00_meta/manuscript_review_rubric.md", "04_chapter_design/arc_index.md"):
            if assert_output_within_root(root, name).is_file():
                names.add(name)
    for folder in folders:
        for path in (root / folder).rglob("*.md"):
            name = path.relative_to(root).as_posix()
            assert_output_within_root(root, name)
            if path.is_file():
                names.add(name)
    extra_names = ("AGENTS.md", "CLAUDE.md") if options["operation"] == "arc_review" else ("AGENTS.md", "CLAUDE.md", "00_meta/ai_work_log.md")
    for name in extra_names:
        if assert_output_within_root(root, name).is_file():
            names.add(name)
    if options["operation"] == "handoff":
        for name in ("94_runtime/current_sprint.md", "94_runtime/current_state.md", "94_runtime/current_state.json",
                     "93_exports/handoff_brief.md"):
            if assert_output_within_root(root, name).is_file():
                names.add(name)
    if options["scope"] == "light":
        chosen = set(options["chapters"])
        if not chosen or not chosen.issubset(names) or any(not name.startswith("07_draft/") or _draft_kind(name) != "draft_prose" for name in chosen):
            raise ContractError("AUDIT_CHAPTER_SELECTION_INVALID", "select existing new draft chapters")
        names = {name for name in names if not name.startswith("07_draft/") or name in chosen or _draft_kind(name) == "draft_support"}
    inventory = {}
    for name in sorted(names):
        data = assert_output_within_root(root, name).read_bytes()
        text = data.decode("utf-8-sig")
        inventory[name] = {"sha256": runner.sha(data), "text": text,
            "line_count": len(text.splitlines()),
            "kind": _draft_kind(name) if name.startswith("07_draft/") else "project_context"}
    return inventory


def _method(root, operation):
    workflow = "04_canon_audit" if operation == "audit" else "05_handoff"
    paths = ["templates/CLAUDE.md", f"templates/_workflows/{workflow}.md"]
    if operation == "arc_review":
        paths = ["templates/CLAUDE.md", "docs/ARCHITECTURE.md", "templates/config/workflow.template.yml",
            "templates/04_chapter_design/arc.template.md", "example_project/00_meta/episode_production_manual.md"]
    if operation == "handoff":
        paths += ["templates/93_exports/handoff_brief.template.md", "docs/HANDOFF.md"]
    references = {}
    for path in paths:
        text, blob = _pinned_upstream(path)
        references[path] = {"text": text, "sha256": runner.sha(text.encode()), "git_blob": blob}
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = assert_output_within_root(root, name)
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            references["project:" + name] = {"text": text, "sha256": runner.sha(path.read_bytes())}
    method_hash = runner.sha(json.dumps(references, ensure_ascii=False, sort_keys=True).encode())
    return references, method_hash


def _messages(inventory, references, options):
    system = "\n\n".join(f"Source: {name}\n{row['text']}" for name, row in references.items())
    system += ("\nTransport only: perform the supplied public workflow in one response. "
               "Supplied project_sources contain complete file text, identity and original line counts. "
               "Use those paths and original line numbers; draft_support files are planning/index material, not events that happened. "
               "Do not modify or resolve Canon. Retain unknown project facts as unknown. Template/example story facts are not this project's facts. ")
    if options["operation"] == "audit":
        system += ('Return JSON {"report_markdown":"full official continuity audit report",'
                   '"action_items":["one unresolved action item in Markdown"]}. '
                   'Each finding in the report must contain the official severity, Source A and B file/line ranges, description and suggested resolution. '
                   'For missing information identify the referencing statement and the relevant source checked, without inventing a missing quotation. '
                   'Do not manufacture findings; if none are found, say so and return an empty action_items list. '
                   'Only action_items will be deduplicated and appended to unresolved_questions; the report is saved verbatim. '
                   'A light audit covers selected new chapters against the supplied Canon/design/Plot; a targeted audit covers the named subsystem across all supplied sources.')
    elif options["operation"] == "arc_review":
        system += ('Perform the public per-Arc completion review in the production manual section 部単位チェック. '
            'Use THIS project Arc Range, Purpose, beats and all actual Arc drafts, including earlier Sprints. '
            'The example protagonist, twenty-episode length, self-evaluation axes and misrecognition model are example facts only; never impose them on this project. '
            'Compare plan/actual, opening/closing character and world state, final payoff, next-Arc readiness, unresolved foreshadowing/Canon candidates and long-term repetition. '
            'Return JSON {"review_markdown":"complete Arc review","status":"pass or revise"}. '
            'Use these exact ## headings with project-language content: ' + ', '.join(ARC_SECTIONS) + '. '
            'Write Status: pass or Status: revise consistent with the JSON status. Canon updates are candidates only; do not approve them or start another Arc.')
    else:
        system += ('Return JSON {"brief_markdown":"compact current-project handoff using the eight sections of the official template"}. '
                   'Keep the official English section headings for publication indexing; content uses the project language. '
                   'Read across the supplied entire project, use recent prose and current indexes to locate the latest chapter, not directory order. '
                   'Statistics below count actual draft files using Unicode visible characters (not words); files may be scenes or chapter drafts. '
                   'Do not treat their count as confirmed chapter completion; use project evidence and distinguish uncertainty. '
                   'If planned total is absent, completion percentage is unknown; do not invent it. '
                   'Use pointers rather than copying full Canon. Add Pipeline Context Pack only when pipeline=true.')
    prose = {name: row for name, row in inventory.items() if row["kind"] == "draft_prose"}
    stats = {"draft_prose_file_count": len(prose), "visible_characters": sum(
        len(re.sub(r"\s", "", row["text"])) for row in prose.values()),
        "draft_files": list(prose), "planned_total_and_completion": "derive only from supplied project evidence; otherwise unknown"}
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps({
        "selection": options, "project_sources": inventory, "draft_statistics": stats,
        "required_handoff_sections": list(HANDOFF_SECTIONS) if options["operation"] == "handoff" else None}, ensure_ascii=False, sort_keys=True)}]


def _json(text):
    if text.strip().startswith("```"):
        text = "\n".join(text.strip().splitlines()[1:-1])
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ContractError("MAINTENANCE_RESPONSE_INVALID", "expected a transport object")
    return value


def _write(root, name, text):
    path = assert_output_within_root(root, name)
    return {"before_sha256": runner.sha(path.read_bytes()) if path.exists() else None,
            "text": text, "after_sha256": runner.sha(text.encode("utf-8"))}


def _deduplicated_questions(existing, items):
    result = existing
    normalized = re.sub(r"\s+", " ", existing).strip()
    for item in items:
        key = re.sub(r"\s+", " ", item).strip()
        if key and key not in normalized:
            result += "\n\n" + item.strip() + "\n"
            normalized += " " + key
    return result


def _validate_sources(root, journal):
    current = _hashes(_inventory(root, journal["options"]))
    for name in set(current) | set(journal["source_hashes"]):
        allowed = {journal["source_hashes"].get(name)}
        if name in journal["writes"]:
            allowed.add(journal["writes"][name]["after_sha256"])
        if current.get(name) not in allowed:
            raise ContractError("MAINTENANCE_SOURCE_CHANGED", name)
    _, method_hash = _method(root, journal["options"]["operation"])
    if method_hash != journal["method_hash"]:
        raise ContractError("MAINTENANCE_METHOD_CHANGED", "recover with the original method identity")
    if _adapter_identity(journal["options"]["operation"]) != journal["adapter_identity"]:
        raise ContractError("MAINTENANCE_ADAPTER_CHANGED", "recover with the original request adapter identity")


def _apply(root, run, journal):
    _validate_sources(root, journal)
    for name, row in journal["writes"].items():
        path = assert_output_within_root(root, name)
        current = runner.sha(path.read_bytes()) if path.exists() else None
        if current not in (row["before_sha256"], row["after_sha256"]):
            raise ContractError("MAINTENANCE_CONCURRENT_EDIT", name)
    for name, row in journal["writes"].items():
        path = assert_output_within_root(root, name)
        if path.exists() and runner.sha(path.read_bytes()) == row["after_sha256"]:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = assert_output_within_root(root, name + ".maintenance-tmp")
        data = row["text"].encode("utf-8")
        if temporary.exists() and temporary.read_bytes() != data:
            raise ContractError("MAINTENANCE_CONCURRENT_EDIT", name + ".maintenance-tmp")
        temporary.write_bytes(data)
        temporary.replace(path)
    (run / "COMMITTED").write_text("Public maintenance transaction committed.\n", encoding="utf-8")


def run_maintenance(project_root, operation, *, scope="full", chapters=(), target=None, pipeline=False):
    root = Path(project_root).resolve(strict=True)
    if not root.is_relative_to((runner.ROOT / "workspace").resolve()):
        raise ContractError("PROJECT_ROOT_OUTSIDE_PRIVATE_WORKSPACE", str(root))
    if operation not in {"audit", "handoff", "arc_review"} or scope not in {"full", "light", "targeted"}:
        raise ContractError("MAINTENANCE_OPERATION_INVALID", str(operation))
    if scope == "targeted" and (not isinstance(target, str) or not target.strip()):
        raise ContractError("AUDIT_TARGET_REQUIRED", "name the subsystem")
    options = {"operation": operation, "scope": scope, "chapters": sorted(set(chapters)),
               "target": target, "pipeline": bool(pipeline)}
    with runner.locked_run(root):
        return _run(root, options)


def _run(root, options):
    pending = assert_output_within_root(root, PENDING)
    latest_path = assert_output_within_root(root, f"00_meta/maintenance_{options['operation']}_state.json")
    if pending.exists():
        pointer = _json(pending.read_text(encoding="utf-8"))
        journal_path = assert_output_within_root(root, pointer["journal"])
        journal = _json(journal_path.read_text(encoding="utf-8"))
        if journal["options"] != options:
            raise ContractError("MAINTENANCE_PENDING_OPERATION", "resume the recorded operation first")
        run = journal_path.parent
        _verify_receipt(run, journal)
        _apply(root, run, journal)
        result = {**journal["result"], "provider_call": "reused", "recovered": True}
    else:
        inventory = _inventory(root, options)
        references, method_hash = _method(root, options["operation"])
        adapter_identity = _adapter_identity(options["operation"])
        current_hashes = _hashes(inventory)
        latest = _json(latest_path.read_text(encoding="utf-8")) if latest_path.exists() else None
        if latest and latest["options"] == options and latest["method_hash"] == method_hash and latest["adapter_identity"] == adapter_identity and latest["source_after_hashes"] == current_hashes:
            journal = _json(assert_output_within_root(root, latest["journal"]).read_text(encoding="utf-8"))
            _verify_receipt(assert_output_within_root(root, latest["journal"]).parent, journal)
            for name, row in journal["writes"].items():
                path = assert_output_within_root(root, name)
                if not path.exists() or runner.sha(path.read_bytes()) != row["after_sha256"]:
                    # A later handoff/Sprint appends its own log entry. The Arc
                    # input set does not consume this work log; preserving the
                    # complete old prefix is compatible with its committed run.
                    if options["operation"] == "arc_review" and name == "00_meta/ai_work_log.md" and path.is_file() and path.read_bytes().startswith(row["text"].encode("utf-8")):
                        continue
                    raise ContractError("MAINTENANCE_COMMITTED_OUTPUT_CHANGED", name)
            return {**journal["result"], "provider_call": "reused"}
        messages = _messages(inventory, references, options)
        target_name = ("08_review/continuity_audit.md" if options["operation"] == "audit" else
            f"08_review/{Path(options['target']).stem}_review.md" if options["operation"] == "arc_review" else "93_exports/handoff_brief.md")
        target_path = assert_output_within_root(root, target_name)
        target_before = runner.sha(target_path.read_bytes()) if target_path.exists() else None
        identity = runner.sha(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode())
        run = assert_output_within_root(root, "94_runtime/maintenance/" + identity[:24])
        run.mkdir(parents=True, exist_ok=True)
        if not (run / "run_state.json").exists():
            runner.save_state(run, {"run_id": run.name, "schema_version": "cnw_maintenance_run_v1", "provider_requests": []})
        snapshot = run / "artifacts/source_snapshot.json"
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps({"sources": inventory, "method": references}, ensure_ascii=False, sort_keys=True).encode()
        if snapshot.exists() and snapshot.read_bytes() != data:
            raise ContractError("MAINTENANCE_SNAPSHOT_CHANGED", identity)
        snapshot.write_bytes(data)
        content, receipt = runner.cnw_live_call(run, stage="project_" + options["operation"], role_id="project_" + options["operation"],
            messages=messages, output_cap=OUTPUT_CAPS[options["operation"]])
        value = _json(content)
        writes = {}
        if options["operation"] == "audit":
            report, items = value.get("report_markdown"), value.get("action_items")
            if not isinstance(report, str) or not report.strip() or not isinstance(items, list) or any(not isinstance(item, str) or not item.strip() for item in items):
                raise ContractError("MAINTENANCE_RESPONSE_INVALID", "audit report and action items required")
            report_path = "08_review/continuity_audit.md"
            writes[report_path] = _write(root, report_path, report)
            questions = "90_canon/unresolved_questions.md"
            previous_questions = (root / questions).read_bytes().decode("utf-8") if (root / questions).exists() else ""
            next_questions = _deduplicated_questions(previous_questions, items)
            if next_questions != previous_questions:
                writes[questions] = _write(root, questions, next_questions)
            result = {"status": "CANON_AUDIT_RECORDED", "report": report_path, "action_items": len(items),
                "canon_modified": False, "unresolved_questions_updated": questions in writes}
        elif options["operation"] == "arc_review":
            report, status = value.get("review_markdown"), value.get("status")
            if not isinstance(report, str) or not report.strip() or status not in {"pass", "revise"}:
                raise ContractError("ARC_REVIEW_RESPONSE_INVALID", "report and pass/revise required")
            headings = re.findall(r"^##\s+(.+?)\s*$", report, re.M)
            if not all(any(section.casefold() == heading.casefold() for heading in headings) for section in ARC_SECTIONS) or not re.search(r"\bStatus:\s*" + status + r"\b", report, re.I):
                raise ContractError("ARC_REVIEW_RESPONSE_INVALID", "public review sections and consistent status required")
            writes[target_name] = _write(root, target_name, report)
            result = {"status": "ARC_REVIEW_RECORDED", "arc_status": status, "report": target_name, "canon_modified": False, "next_arc_started": False}
        else:
            brief = value.get("brief_markdown")
            if not isinstance(brief, str) or not brief.strip():
                raise ContractError("MAINTENANCE_RESPONSE_INVALID", "handoff brief required")
            headings = re.findall(r"^#{1,6}\s+(.+?)\s*$", brief, re.M)
            if not all(any(section.casefold() in h.casefold() for h in headings) for section in HANDOFF_SECTIONS):
                raise ContractError("HANDOFF_SECTION_MISSING", "eight public template sections required")
            if options["pipeline"] and not any("context pack" in h.casefold() for h in headings):
                raise ContractError("HANDOFF_SECTION_MISSING", "Pipeline Context Pack required")
            path = "93_exports/handoff_brief.md"
            if (root / path).exists():
                old = (root / path).read_bytes()
                archive = f"93_exports/archive/handoff_{runner.sha(old)}.md"
                archive_path = assert_output_within_root(root, archive)
                if archive_path.exists() and archive_path.read_bytes() != old:
                    raise ContractError("HANDOFF_ARCHIVE_CHANGED", archive)
                writes[archive] = _write(root, archive, old.decode("utf-8"))
            writes[path] = _write(root, path, brief)
            result = {"status": "HANDOFF_WRITTEN", "path": path, "archive": archive if (root / path).exists() else None}
        writes[target_name]["before_sha256"] = target_before
        if _hashes(_inventory(root, options)) != current_hashes:
            raise ContractError("MAINTENANCE_SOURCE_CHANGED", "project changed during the call")
        log_name = "00_meta/ai_work_log.md"
        old_log = (root / log_name).read_bytes().decode("utf-8") if (root / log_name).exists() else ""
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        writes[log_name] = _write(root, log_name, old_log + f"\n- {stamp} Workflow {options['operation']}; scope={options['scope']}; run={run.name}; provider={receipt['provider_request_id']}.\n")
        result.update(run_dir=str(run), provider_call="performed", provider_request_id=receipt["provider_request_id"])
        journal = {"options": options, "source_hashes": current_hashes, "method_hash": method_hash,
            "adapter_identity": adapter_identity, "request_id": receipt["request_id"], "writes": writes, "result": result}
        journal_path = run / "transaction.json"
        journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")
        pending.parent.mkdir(parents=True, exist_ok=True)
        pending.write_text(json.dumps({"journal": journal_path.relative_to(root).as_posix()}), encoding="utf-8")
        _apply(root, run, journal)
    latest_path.write_text(json.dumps({"options": options, "method_hash": journal["method_hash"],
        "adapter_identity": journal["adapter_identity"],
        "source_after_hashes": _hashes(_inventory(root, options)), "journal": journal_path.relative_to(root).as_posix()}, indent=2), encoding="utf-8")
    pending.unlink()
    return result
