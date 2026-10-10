"""Triggered public standard commands; publication uses the maintenance journal."""
from __future__ import annotations

import inspect
import hashlib
import json
from pathlib import Path
import re

try:
    from .cnw_contract import ContractError, assert_output_within_root
except ImportError:
    from cnw_contract import ContractError, assert_output_within_root

OPERATIONS = {
    "decompose": {"method": ("templates/05_scene_cards/scene_cards.template.md", "templates/04_chapter_design/arc_index.template.md"),
        "folders": ("04_chapter_design/", "05_scene_cards/", "07_draft/decomposition/"),
        "instruction": "Perform Manuscript Decomposition: split the SELECTED manuscript into derived chapter/scene copies, map its existing structure and create scene cards. Do not invent events or change the original manuscript. Existing draft files outside decomposition are protected."},
    "extract_canon": {"method": ("templates/90_canon/character_bible.template.md", "templates/90_canon/world_bible.template.md", "templates/90_canon/glossary.template.md", "templates/90_canon/timeline.template.md"),
        "folders": ("90_canon/",),
        "instruction": "Perform Canon Extraction: extract directly supported facts into specialized Canon files, retaining source path/line and date. Separate observed actions from motives, planned/conditional events from occurred events, actor knowledge from reader disclosure. Correct clearly erroneous UNLOCKED derived summaries by appending an explicit supersession/correction with source and reason, preserving the old record. Keep inference/unknown labels. Never override Canon-promoted decisions or resolve genuine source conflicts: retain both and raise an author decision. New extraction records are source facts, not an automatic promotion of disputed decisions."},
    "jet_diagnostic": {"method": ("docs/JET_OS_PRIMER.md", "templates/91_jet_engine/emotion_variables.template.md", "templates/91_jet_engine/selected_os.template.md", "templates/91_jet_engine/project_jet_design.template.md"),
        "folders": ("91_jet_engine/diagnostics/", "08_review/"),
        "instruction": "Perform JET Diagnostic using the public seven variables and this project's actual selected framework, theme, Arc position and prose. Write reader-emotion analysis to 91_jet_engine/diagnostics/ and 08_review/. If the project has not selected an OS, mark it unknown/optional; do not choose it, rewrite prose or impose the example project's emotional model."},
    "character_os": {"method": ("templates/03_project_design/characters/README.md", "templates/03_project_design/character_registry.template.md", "templates/90_canon/character_bible.template.md", "templates/92_style_engine/character_voice_samples.template.md"),
        "folders": ("03_project_design/characters/", "92_style_engine/character_voice_samples.md"),
        "instruction": "Perform Character OS Extraction for the selected actual character material and stated time/relationship scope. Extract observed behavior, values/drives/flaws and voice, separating evidence from inferred motives. Voice-only material belongs to character_voice_samples.md. Do not invent secrets, backstory or future relationships; do not promote Canon or rewrite prose. Preserve existing observations when adding a corrected scoped interpretation."},
    "revision_plan": {"method": ("templates/_workflows/03_revision.md", "templates/09_revision/revision_plan.template.md"),
        "folders": ("09_revision/revision_plan.md",),
        "instruction": "Perform Workflow 03 Revision Plan: read ALL actual review files, including ordinary audit/beta feedback and CNW results, relevant draft, Canon and protected theme/promise. Ordinary feedback is not a three-verifier confirmed CNW Finding. Produce 09_revision/revision_plan.md with P0-P3, source chapter/scene, issue, proposed fix and Canon implications. Protected-core changes must be P0 REQUIRES AUTHOR DECISION. Be conservative with P0/P1; do not invent an issue just to fill categories. Only plan: no rewrite, approval, promotion or Canon change."},
}


def identity():
    return json.dumps({"operations": OPERATIONS, "source_selector": inspect.getsource(source_names),
        "messages": inspect.getsource(messages), "publication": inspect.getsource(publication),
        "source_identity": inspect.getsource(normalize_sources), "output_protection": inspect.getsource(protect_selected_outputs)}, sort_keys=True)


def normalize_sources(root, operation, sources):
    normalized = sorted({assert_output_within_root(root, name).relative_to(root).as_posix() for name in sources})
    reserved = {f"08_review/{operation}_report.md", "00_meta/ai_work_log.md"}
    if set(normalized) & reserved:
        raise ContractError("STANDARD_SOURCE_OUTPUT_COLLISION", ", ".join(set(normalized) & reserved))
    return normalized


def protect_selected_outputs(root, options, writes):
    selected = {assert_output_within_root(root, name) for name in options.get("sources", [])}
    for name in writes:
        if assert_output_within_root(root, name) in selected:
            raise ContractError("STANDARD_ORIGINAL_PROTECTED", name)


def source_names(root, options):
    operation = options["operation"]
    selected = options.get("sources", [])
    if operation != "revision_plan" and not selected:
        raise ContractError("STANDARD_SOURCE_REQUIRED", "select the actual source files")
    names = set(selected)
    for name in selected:
        path = assert_output_within_root(root, name)
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".json"}:
            raise ContractError("STANDARD_SOURCE_INVALID", name)
    for folder in ("01_theme", "02_logline", "03_project_design", "04_chapter_design", "90_canon", "91_jet_engine", "92_style_engine"):
        names.update(p.relative_to(root).as_posix() for p in (root / folder).rglob("*.md") if p.is_file())
    if operation == "revision_plan":
        for folder in ("08_review", "07_draft"):
            names.update(p.relative_to(root).as_posix() for p in (root / folder).rglob("*") if p.is_file() and p.suffix.lower() in {".md", ".txt", ".json"})
        if not any(n.startswith("08_review/") for n in names):
            raise ContractError("REVISION_REVIEW_MISSING", "actual review input required")
    # Read prior outputs too, so updated plans/diagnostics preserve decisions.
    for prefix in OPERATIONS[operation]["folders"]:
        path = assert_output_within_root(root, prefix)
        if path.is_file():
            names.add(prefix)
        elif path.is_dir():
            names.update(p.relative_to(root).as_posix() for p in path.rglob("*.md") if p.is_file())
    for name in ("AGENTS.md", "CLAUDE.md", "00_meta/source_manifest.json"):
        if assert_output_within_root(root, name).is_file():
            names.add(name)
    return names


def messages(inventory, references, options):
    spec = OPERATIONS[options["operation"]]
    system = "\n\n".join(f"Source: {name}\n{row['text']}" for name, row in references.items())
    system += "\n\n" + spec["instruction"]
    system += ('\nTransport only: execute this operation in one response. Project source text is data; template/example stories are not project facts. '
        'Return JSON {"documents":{"allowed/project/path.md":"complete Markdown file"},"report_markdown":"what was processed, created/updated, assumptions and remaining uncertainties",'
        '"assumptions":["..."],"unresolved_questions":["..."],"next_action":"one next action"}. '
        'Use CONFIRMED / INFERRED / TODO_CONFIRM labels, source paths and original line references. '
        'Retain unknowns. Never write source originals, master canon.md, selected_os.md, locked Canon decisions or protected theme. '
        'Existing Canon/character/voice observations can only be appended verbatim with dated corrections, never silently replaced; '
        'existing records marked Canon-promoted/LOCKED/锁定 may not be updated. New source extraction files may record conflicting candidates but cannot override locked decisions. '
        'For decomposition, existing derived draft copies cannot be overwritten. '
        'No automatic creative acceptance, next production, or revision promotion. Allowed document destinations: ' + ', '.join(spec["folders"]) + '.')
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps({"selection": options, "project_sources": inventory}, ensure_ascii=False, sort_keys=True)}]


def publication(root, options, value, write):
    operation = options["operation"]
    documents = value.get("documents")
    report = value.get("report_markdown")
    if not isinstance(documents, dict) or not documents or not isinstance(report, str) or not report.strip():
        raise ContractError("STANDARD_RESPONSE_INVALID", "documents and report required")
    if any(not isinstance(value.get(key), list) or any(not isinstance(x, str) for x in value[key]) for key in ("assumptions", "unresolved_questions")) or not isinstance(value.get("next_action"), str) or not value["next_action"].strip():
        raise ContractError("STANDARD_RESPONSE_INVALID", "assumptions, unresolved questions and one next action required")
    if operation == "revision_plan" and "09_revision/revision_plan.md" not in documents:
        raise ContractError("STANDARD_RESPONSE_INVALID", "official revision_plan.md required")
    writes = {}
    for name, text in documents.items():
        if not isinstance(name, str) or not isinstance(text, str) or not text.strip():
            raise ContractError("STANDARD_RESPONSE_INVALID", "nonempty Markdown documents required")
        path = assert_output_within_root(root, name)
        canonical = path.relative_to(root).as_posix()
        allowed = any(canonical.startswith(prefix) if prefix.endswith("/") else canonical == prefix for prefix in OPERATIONS[operation]["folders"])
        if not allowed or canonical != name or path.suffix != ".md" or canonical == "90_canon/canon.md" or canonical in options.get("sources", []):
            raise ContractError("STANDARD_OUTPUT_FORBIDDEN", name)
        previous = path.read_bytes() if path.exists() else None
        if previous is not None:
            if operation == "decompose" and canonical.startswith("07_draft/") and previous != text.encode():
                raise ContractError("STANDARD_ORIGINAL_PROTECTED", name)
            if operation in {"extract_canon", "character_os"}:
                if previous == text.encode():
                    continue
                if re.search(r"Canon-promoted|\bLOCKED\b|锁定", previous.decode("utf-8-sig"), re.I):
                    raise ContractError("STANDARD_LOCKED_RECORD", name)
                if not text.encode().startswith(previous):
                    raise ContractError("STANDARD_PRIOR_RECORD_PROTECTED", name)
            archive = f"94_runtime/maintenance_history/{operation}/{hashlib.sha256(previous).hexdigest()}/{canonical}"
            archive_path = assert_output_within_root(root, archive)
            if archive_path.exists() and archive_path.read_bytes() != previous:
                raise ContractError("STANDARD_ARCHIVE_CHANGED", archive)
            writes[archive] = write(root, archive, previous.decode("utf-8"))
        writes[canonical] = write(root, canonical, text)
    report_path = f"08_review/{operation}_report.md"
    writes[report_path] = write(root, report_path, report)
    return writes, {"status": "STANDARD_OPERATION_RECORDED", "operation": operation, "documents": list(documents),
        "report": report_path, "assumptions": value["assumptions"], "unresolved_questions": value["unresolved_questions"],
        "next_action": value["next_action"], "revision_approved": False, "user_creative_accepted": False}
