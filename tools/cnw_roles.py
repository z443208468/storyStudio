"""CNW role packets, provenance receipts, and offline structural gates.

The four author roles (plot / scene cards / writing brief / prose) read the
files named in the pinned ``templates/config/ai_roles.template.yml``. Machine
markers (contract budgets, beat budgets) live in a same-stage ``*.meta.json``
sidecar and never pollute the literary Markdown the author template defines.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from .cnw_contract import ContractError, check_required_fields, load_contract, validate_episode_budget, validate_output_length, validate_scene_budget, validate_source_identity, validate_work_unit
except ImportError:  # direct script execution
    from cnw_contract import ContractError, check_required_fields, load_contract, validate_episode_budget, validate_output_length, validate_scene_budget, validate_source_identity, validate_work_unit

ROOT = Path(__file__).resolve().parents[1]
PROMPT_DIR = ROOT / "prompts" / "cnw"
ROLE_FILES = {"plot": "plot.md", "cards": "scene_cards.md", "brief": "brief.md", "prose": "prose.md"}
# Author-published per-role reading contract (ai_roles.template.yml).
AUTHOR_ROLE_READS: dict[str, tuple[str, ...]] = {
    "plot": (
        "04_chapter_design/arc_<NN>.md",
        "90_canon/canon.md",
        "90_canon/character_bible.md",
    ),
    "cards": (
        "06_plot/<work_id>_plot.md",
        "90_canon/character_bible.md",
    ),
    "brief": (
        "06_plot/<work_id>_plot.md",
        "05_scene_cards/<work_id>_scene_cards.md",
        "90_canon/character_bible.md",
        "92_style_engine/style_guide.md",
    ),
    "prose": (
        "07_draft/<work_id>_writing_brief.md",
        "92_style_engine/character_voice_samples.md",
    ),
}
# The concise role table is supplemented by the public templates' explicit
# Brief duties (Active Canon, glossary/world details and previous story time).
AUTHOR_TEMPLATE_READS = {
    "brief": ("90_canon/canon.md", "90_canon/timeline.md",
              "90_canon/world_bible.md", "90_canon/glossary.md"),
}
AUTHOR_TEMPLATE_READ_SOURCES = {
    "brief": ("templates/90_canon/canon.template.md",
              "templates/90_canon/timeline.template.md",
              "templates/90_canon/world_bible.template.md",
              "templates/90_canon/glossary.template.md"),
}
# Author template each role prompt reproduces (S5.3).
ROLE_TO_AUTHOR_TEMPLATE = {
    "plot": "templates/06_plot/plot.template.md",
    "cards": "templates/05_scene_cards/scene_cards.template.md",
    "brief": "templates/07_draft/writing_brief.template.md",
    "prose": "templates/config/ai_roles.template.yml",
}
REFERENCE_ROOT = ROOT / "runtime" / "reference" / "cnw_97ad71fe5e5e"
REFERENCE_MANIFEST = REFERENCE_ROOT / "CNW_LOCAL_REFERENCE_MANIFEST.json"

# Author template section headings that the literary Markdown must contain.
ROLE_REQUIRED_SECTIONS = {
    "plot": ("## Identity", "## Role in the Arc", "## Key Scenes", "## Hook", "## Required Story Beats", "## Forbidden Items", "## Connections", "## Target Length"),
    "cards": ("### Identity", "### Cast", "### Start state", "### End state", "### Required beats", "### Forbidden items for this scene", "### Sensory anchor", "### Tone / pacing", "### Connection to next scene"),
    "brief": ("## Quick Header", "## Active Canon", "## Scene-by-Scene Instructions", "## Voice References", "## Hard Constraints", "## Style Targets", "## What NOT to include in the prose"),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _read_project_file(path: str | Path, project_root: Path | None = None) -> tuple[Path, str]:
    if project_root is None:
        raise ContractError("PROJECT_REQUIRED", "role inputs require an explicit project root")
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path(project_root) / candidate
    resolved = candidate.resolve(strict=True)
    allowed = (Path(project_root).resolve(), (ROOT / "runs").resolve())
    if not any(resolved.is_relative_to(root) for root in allowed) or not resolved.is_file():
        raise ContractError("ROLE_INPUT_PATH_UNSAFE", "role input must be a private project or run file")
    return resolved, resolved.read_text(encoding="utf-8-sig")


def _hash_inputs(inputs: dict[str, str | Path], project_root: Path) -> dict[str, str]:
    result = {}
    for name, value in sorted(inputs.items()):
        path, _ = _read_project_file(value, project_root)
        result[name] = sha256_file(path)
    return result


def _pinned_upstream(source_path: str) -> tuple[str, str | None]:
    template = REFERENCE_ROOT / source_path
    if not template.is_file() or template.is_symlink():
        raise ContractError("AUTHOR_TEMPLATE_MISSING", source_path)
    blob = None
    if REFERENCE_MANIFEST.is_file():
        try:
            manifest = json.loads(REFERENCE_MANIFEST.read_text(encoding="utf-8"))
            blob = next((item.get("upstream_git_blob") for item in manifest.get("references", []) if item.get("source_path") == source_path), None)
        except (OSError, json.JSONDecodeError):
            blob = None
    return template.read_text(encoding="utf-8-sig"), blob


def resolve_arc(project_root: Path, work_id: str, arc_ref: str | None = None) -> Path:
    """Resolve the work's Arc from an explicit reference or the author's index."""
    directory = project_root / "04_chapter_design"
    if arc_ref:
        raw_candidate = project_root / arc_ref
        if raw_candidate.is_symlink():
            raise ContractError("ARC_REFERENCE_UNSAFE", arc_ref)
        candidate = raw_candidate.resolve(strict=True)
        if (not candidate.is_relative_to(directory.resolve()) or not candidate.is_file()
                or not re.fullmatch(r"arc_[A-Za-z0-9_-]+\.md", candidate.name)
                or candidate.name == "arc_index.md" or candidate.stem.endswith("_episode_details")):
            raise ContractError("ARC_REFERENCE_UNSAFE", arc_ref)
        return candidate
    episode = re.fullmatch(r"(?:ep|ch)(\d+)", work_id, re.I)
    index = directory / "arc_index.md"
    matches = []
    indexed_ranges = 0
    if episode and index.is_file():
        for line in index.read_text(encoding="utf-8-sig").splitlines():
            cells = [part.strip() for part in line.strip().strip("|").split("|")]
            if len(cells) < 3 or not re.fullmatch(r"\d+", cells[0]):
                continue
            bounds = re.fullmatch(r"(?:ep)?(\d+)(?:\s*[-–—]\s*(?:ep)?(\d+))?", cells[2], re.I)
            if bounds:
                indexed_ranges += 1
            if bounds and int(bounds.group(1)) <= int(episode.group(1)) <= int(bounds.group(2) or bounds.group(1)):
                matches.append(directory / f"arc_{cells[0]}.md")
        if len(matches) == 1 and matches[0].is_file():
            return matches[0]
        if matches or indexed_ranges:
            raise ContractError("ARC_INDEX_INVALID", f"{work_id}: missing or overlapping Arc reference")
    candidates = sorted(path for path in directory.glob("arc_*.md")
                        if path.name != "arc_index.md" and not path.stem.endswith("_episode_details"))
    if len(candidates) == 1:
        return candidates[0]
    raise ContractError("AUTHOR_READ_AMBIGUOUS" if candidates else "AUTHOR_READ_MISSING",
                        f"Arc for {work_id}; supply story.arc_ref or an Arc Index episode range")


def resolve_author_reads(project_root: Path, role: str, work_id: str, *, arc_ref: str | None = None,
                         content_overrides: dict[str, str] | None = None) -> dict[str, Path]:
    """Resolve the author reading list to concrete private project files."""
    if role not in AUTHOR_ROLE_READS:
        raise ContractError("ROLE_UNKNOWN", role)
    resolved: dict[str, Path] = {}
    for template in AUTHOR_ROLE_READS[role] + AUTHOR_TEMPLATE_READS.get(role, ()):
        if "<NN>" in template:
            resolved[template] = resolve_arc(project_root, work_id, arc_ref)
        elif "<work_id>" in template:
            resolved[template] = project_root / template.replace("<work_id>", work_id)
        else:
            resolved[template] = project_root / template
    overrides = content_overrides or {}
    unauthorized = set(overrides) - set(resolved)
    if unauthorized:
        raise ContractError("ROLE_INPUT_OVERRIDE_UNAUTHORIZED", ", ".join(sorted(unauthorized)))
    for template, path in resolved.items():
        if template in overrides:
            continue
        if not path.is_file() or path.is_symlink():
            raise ContractError("AUTHOR_READ_MISSING", template)
    return resolved


def read_actual_texts(project_root: Path, role: str, work_id: str, *, arc_ref: str | None = None,
                      content_overrides: dict[str, str] | None = None) -> dict[str, str]:
    overrides = content_overrides or {}
    paths = resolve_author_reads(project_root, role, work_id, arc_ref=arc_ref, content_overrides=overrides)
    return {template: overrides[template] if template in overrides else path.read_text(encoding="utf-8-sig")
            for template, path in paths.items()}


def read_production_preparation(project_root: Path, contract: dict) -> dict:
    """Read the public production manual's preparation sources before Plot."""
    story = contract.get("story", {})
    intent = contract.get("work_intent")
    arc_ref = story.get("arc_ref")
    if intent == "ORIGINAL_EPISODE" and not arc_ref:
        raise ContractError("PRE_FLIGHT_MISSING_PROJECT_INPUT", "story.arc_ref")
    arc = resolve_arc(project_root, contract["unit"]["id"], arc_ref)
    paths = [project_root / "94_runtime/current_state.md", project_root / "07_draft/manuscript_index.md", arc,
             arc.with_name(arc.stem + "_episode_details.md"),
             project_root / "92_style_engine/character_voice_samples.md", project_root / "90_canon/character_bible.md"]
    if contract.get("schema_version") == "cnw_work_unit_v2" and "input_pack" in contract:
        try:
            from .cnw_task_requirements import read_bound_task_context
        except ImportError:
            from cnw_task_requirements import read_bound_task_context
        task_context = read_bound_task_context(project_root, contract)
        if task_context is not None:
            paths.append(project_root / task_context[0])
    previous = story.get("previous_episode_ref")
    episode = re.fullmatch(r"(ep|ch)(\d+)", contract["unit"]["id"], re.I)
    if not previous and episode and int(episode.group(2)) > 1:
        previous = f"07_draft/episodes/{episode.group(1)}{int(episode.group(2))-1:0{len(episode.group(2))}d}.md"
    if not previous and contract["unit"].get("kind") == "episode" and not episode and not story.get("first_episode"):
        raise ContractError("PREVIOUS_EPISODE_REFERENCE_REQUIRED", contract["unit"]["id"])
    if previous:
        paths.append(project_root / previous)
    documents, hashes = {}, {}
    for path in paths:
        if not path.is_file():
            raise ContractError("PRODUCTION_CONTEXT_MISSING", str(path.relative_to(project_root)))
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(project_root.resolve()) or path.is_symlink() or not resolved.is_file():
            raise ContractError("PRODUCTION_CONTEXT_PATH_UNSAFE", str(path))
        relative = resolved.relative_to(project_root.resolve()).as_posix()
        documents[relative] = resolved.read_text(encoding="utf-8-sig")
        hashes[relative] = sha256_file(resolved)
    if intent == "ORIGINAL_EPISODE":
        required_authority = ("90_canon/canon.md", "90_canon/character_bible.md", "90_canon/world_bible.md",
                              "90_canon/timeline.md", "90_canon/glossary.md", "92_style_engine/style_guide.md",
                              "92_style_engine/forbidden_patterns.md", "92_style_engine/character_voice_samples.md")
        for relative in required_authority:
            path = project_root / relative
            if not path.is_file() or path.is_symlink():
                raise ContractError("PRE_FLIGHT_MISSING_PROJECT_INPUT", relative)
            text = path.read_text(encoding="utf-8-sig").strip()
            if not text or re.search(r"^\s*TODO(?:_CONFIRM)?\s*:", text, re.I | re.M):
                raise ContractError("PRE_FLIGHT_MISSING_PROJECT_INPUT", relative)
            documents[relative] = text
            hashes[relative] = sha256_file(path)
        previous_ref = story.get("previous_episode_ref")
        if previous_ref:
            path = (project_root / previous_ref).resolve(strict=True)
            if not path.is_relative_to(project_root.resolve()) or path.is_symlink() or sha256_file(path) != story.get("previous_episode_sha256"):
                raise ContractError("PREVIOUS_EPISODE_IDENTITY_MISMATCH", previous_ref)
        elif story.get("first_episode") is not True:
            raise ContractError("PREVIOUS_EPISODE_REFERENCE_REQUIRED", contract["unit"]["id"])
    if intent in {"INSERT_BETWEEN", "ADAPT_SOURCE"}:
        try:
            from .cnw_contract import _safe_source_file, resolve_json_pointer
            from .cnw_runner import _source_root
        except ImportError:
            from cnw_contract import _safe_source_file, resolve_json_pointer
            from cnw_runner import _source_root
        source_root = _source_root(contract, project_root)
        source_file = _safe_source_file(source_root, story.get("source_file", ""))
        source_bytes = source_file.read_bytes()
        source_hash = sha256_bytes(source_bytes)
        if source_hash != contract["source"].get("source_revision_id"):
            raise ContractError("SOURCE_IDENTITY_MISMATCH", "selected source bytes changed before Plot")
        if intent == "ADAPT_SOURCE":
            selection = story.get("source_selection", {})
            if source_file.suffix.lower() == ".json":
                parsed = json.loads(source_bytes.decode("utf-8-sig"))
                selected = resolve_json_pointer(parsed, selection.get("json_pointer"))
                excerpt = json.dumps(selected, ensure_ascii=False, sort_keys=True, indent=2)
                canonical_raw = json.dumps(selected, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                canonical_sha = sha256_bytes(canonical_raw)
                excerpt_sha = sha256_bytes(excerpt.encode("utf-8"))
                if (selection.get("canonical_selected_value_sha256") != canonical_sha or
                        selection.get("selected_sha256") != canonical_sha or
                        selection.get("wire_excerpt_sha256") != excerpt_sha):
                    raise ContractError("SOURCE_WIRE_EXCERPT_HASH_MISMATCH", "canonical value or Plot excerpt bytes changed")
            else:
                lines = source_bytes.splitlines(keepends=True)
                excerpt = b"".join(lines[selection["start_line"]-1:selection["end_line"]]).decode("utf-8-sig")
                excerpt_sha = selection["selected_sha256"]
        else:
            lines = source_bytes.splitlines(keepends=True)
            before, after = story["before_anchor"], story["after_anchor"]
            excerpt = json.dumps({"before_anchor": b"".join(lines[before["source_line"]-1:before["source_line_end"]]).decode("utf-8-sig"),
                                  "after_anchor": b"".join(lines[after["source_line"]-1:after["source_line_end"]]).decode("utf-8-sig")}, ensure_ascii=False)
            excerpt_sha = sha256_bytes(excerpt.encode("utf-8"))
        documents["selected_source_excerpt"] = excerpt
        hashes["selected_source_excerpt"] = excerpt_sha
        documents["selected_source_identity"] = json.dumps({"source_id": contract["source"]["source_id"],
            "source_revision_id": source_hash, "manifest_revision_sha256": contract["source"]["manifest_revision_sha256"],
            "source_index_sha256": contract["source"]["source_index_sha256"],
            "canonical_selected_value_sha256": story.get("source_selection", {}).get("canonical_selected_value_sha256",
                                                                                      story.get("source_selection", {}).get("selected_sha256")),
            "wire_excerpt_sha256": excerpt_sha}, sort_keys=True)
        hashes["selected_source_identity"] = sha256_bytes(documents["selected_source_identity"].encode("utf-8"))
    return {"documents": documents, "source_hashes": hashes,
            "source_method": "example_project/00_meta/episode_production_manual.md#production-reading-order",
            "previous_episode": previous or ("FIRST_EPISODE" if episode or story.get("first_episode") else "SCENE_SOURCE_ANCHORS")}


def relevant_voice_samples(text: str, characters: list[str]) -> str:
    """Select character sections, retaining their nested sample headings only."""
    if not characters:
        return ""
    headings = list(re.finditer(r"^(#{1,6})\s+(.+?)\s*$", text, re.MULTILINE))
    sections = []
    found = set()
    for index, heading in enumerate(headings):
        title = heading.group(2).strip().strip("*")
        if title not in characters:
            continue
        level = len(heading.group(1))
        end = next((other.start() for other in headings[index + 1:]
                    if len(other.group(1)) <= level), len(text))
        sections.append(text[heading.start():end].strip())
        found.add(title)
    missing = set(characters) - found
    if missing:
        raise ContractError("VOICE_SAMPLE_CHARACTER_MISSING", ", ".join(sorted(missing)))
    return "\n\n".join(sections)


def brief_voice_characters(brief: str) -> list[str]:
    """Read the author's Voice References list; cast membership is not speech.

    Accept ordinary Markdown lists, links, emphasis and registry tables. An
    empty list or explicit no-dialogue entry needs no voice samples. Missing
    references are reported rather than replaced with the entire cast.
    """
    headings = list(re.finditer(r"^(#{1,6})\s+(.+?)\s*$", brief, re.MULTILINE))
    section = next((i for i, h in enumerate(headings)
                    if h.group(2).strip().strip("*").casefold().startswith("voice references")), None)
    if section is None:
        raise ContractError("BRIEF_VOICE_REFERENCES_MISSING", "use the author's Voice References section")
    heading = headings[section]
    end = next((h.start() for h in headings[section + 1:]
                if len(h.group(1)) <= len(heading.group(1))), len(brief))
    characters = []
    for line in brief[heading.end():end].splitlines():
        value = line.strip()
        if not value:
            continue
        if value.startswith("|"):
            value = value.strip("|").split("|", 1)[0].strip()
            value = re.sub(r"\[([^\]]+)\]\([^\n)]+\)", r"\1", value)
            value = re.sub(r"[*`_]", "", value).strip()
            if re.fullmatch(r"[:\-\s]+", value) or value.casefold() in {"character", "character name", "name", "角色", "人物"}:
                continue
        else:
            listed = re.match(r"^(?:[-*+]\s+|\d+[.)]\s+)(.+)$", value)
            if listed:
                value = listed.group(1)
            else:
                # Plain prose explaining where samples are loaded is not a name.
                continue
        value = re.sub(r"\[([^\]]+)\]\([^\n)]+\)", r"\1", value)
        name = re.split(r"\s*[—–：:]\s*|\s+-\s+", value, maxsplit=1)[0]
        name = re.sub(r"[*`_]", "", name).strip()
        if re.match(r"^(?:none\b|n/a\b|no (?:speakers|dialogue)\b|无(?:对白|说话角色)?(?:\s|$|[（(]))", name, re.I):
            continue
        # The public template does not require one unannotated name per row.
        # Preserve explicit listed speakers, including grouped references.
        for character in re.split(r"\s*[/／]\s*", name):
            character = re.sub(r"\s*[（(]\s*POV\s*[）)]\s*$", "", character, flags=re.I).strip()
            if character and character not in characters:
                characters.append(character)
    return characters


def brief_voice_samples(brief: str, voice_samples: str) -> str:
    """One selection rule for both the actual Prose API and packet paths."""
    return relevant_voice_samples(voice_samples, brief_voice_characters(brief))


def build_prose_input_view(contract: dict[str, Any], brief: str, voice_samples: str) -> dict[str, Any]:
    """Return only the brief, relevant voices, and minimum execution bounds."""
    unit = contract["unit"]
    voice_samples = brief_voice_samples(brief, voice_samples)
    return {
        "execution_contract": {
            "unit_id": unit["id"],
            "language": unit["language"],
            "pov": unit["pov"],
            "target_visible_chars": unit["target_visible_chars"],
            "min_visible_chars": unit["min_visible_chars"],
            "max_visible_chars": unit["max_visible_chars"],
            "required_beat_ids": [beat["beat_id"] for beat in contract["story"].get("required_beats", [])],
        },
        "inputs": {"brief": brief, "voice_samples": voice_samples},
    }


def role_metadata(role: str, contract: dict[str, Any]) -> dict[str, Any]:
    """Machine-checkable budget metadata, kept out of the literary Markdown."""
    unit = contract["unit"]
    return {
        "role": role,
        "work_id": unit["id"],
        "target_visible_chars": unit["target_visible_chars"],
        "min_visible_chars": unit["min_visible_chars"],
        "max_visible_chars": unit["max_visible_chars"],
        "planning_mode": unit.get("planning_mode", "legacy_frozen"),
        "beats": [({"beat_id": beat["beat_id"]} if unit.get("planning_mode") == "author_plot"
                   else {"beat_id": beat["beat_id"], "budget_visible_chars": beat["budget_visible_chars"]})
                  for beat in contract["story"].get("required_beats", [])],
    }


def plot_structure(output: str, contract: dict[str, Any]) -> dict[str, Any]:
    """Index the author's actual Markdown design, without inventing allocations."""
    sections: dict[str, list[str]] = {}
    current = None
    for line in output.splitlines():
        heading = re.match(r"^##\s+(.+)", line)
        if heading:
            title = heading.group(1).casefold()
            current = next((name for name in ("key scenes", "required story beats") if title.startswith(name)), None)
            if current:
                sections.setdefault(current, [])
        elif current:
            item = re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(\S.*)", line)
            if item:
                sections[current].append(item.group(1).strip())
    if not sections.get("key scenes") or not sections.get("required story beats"):
        raise ContractError("PLOT_DESIGN_MISSING", "Plot must design nonempty Key Scenes and Required Story Beats lists")
    return {"source": "plot_markdown", "plot_sha256": sha256_bytes(output.encode("utf-8")),
            "key_scenes": sections["key scenes"], "required_story_beats": sections["required story beats"]}


def creative_assignment(contract: dict[str, Any]) -> dict[str, Any]:
    """Separate literary requirements from historical execution allocations."""
    assignment = json.loads(json.dumps({k: contract[k] for k in ("project_id", "unit", "story") if k in contract}))
    assignment["unit"].pop("scenes", None)
    for beat in assignment["story"].get("required_beats", []):
        beat.pop("budget_visible_chars", None)
    return assignment


def _project_language_instruction(contract: dict[str, Any]) -> str:
    # V1 requests predate project locale instructions; retain their exact
    # historical prompt bytes even if a legacy display field says en-US.
    if contract.get("schema_version") != "cnw_work_unit_v2":
        return ""
    locale = contract.get("unit", {}).get("language_locale", contract.get("unit", {}).get("language"))
    if locale == "zh-CN":
        return ("[project_language_contract]\n本工作单元的输出语言为简体中文（zh-CN）。"
                "长度按 NFC 规范化后、剔除 Markdown 控制符与空白的可见 Unicode 码点计数；这不是词数。")
    if locale == "en-US":
        return ("[project_language_contract]\nWrite this work unit in English (en-US). "
                "Length is measured as visible Unicode code points after NFC normalization and removal of Markdown control syntax and whitespace; it is not a word count.")
    raise ContractError("LOCALE_UNSUPPORTED", str(locale))


def build_author_role_messages(role: str, contract: dict[str, Any], materials: dict[str, str], *, extra: dict[str, Any] | None = None) -> list[dict]:
    """Reproduce the author template + reading list, then the project values."""
    if role not in ROLE_TO_AUTHOR_TEMPLATE:
        raise ContractError("ROLE_UNKNOWN", role)
    language_instruction = _project_language_instruction(contract)
    if role == "prose":
        brief_key, voice_key = AUTHOR_ROLE_READS["prose"]
        brief = materials[brief_key]
        voices = brief_voice_samples(brief, materials[voice_key])
        # Canon, plot, contract.story, and review rules must reach prose only
        # through the Brief. The orchestrator retains validation metadata.
        return [
            {"role": "system", "content": "Write the complete story prose specified by the Writing Brief, using the voice samples selected by its Voice References. Output only the prose, without planning notes or commentary." + ("\n" + language_instruction if language_instruction else "")},
            {"role": "user", "content": json.dumps({"writing_brief": brief, "voice_samples": voices}, ensure_ascii=False)},
        ]
    template_text, blob = _pinned_upstream(ROLE_TO_AUTHOR_TEMPLATE[role])
    reads_text, _ = _pinned_upstream("templates/config/ai_roles.template.yml")
    header = f"[pinned_author_template: {ROLE_TO_AUTHOR_TEMPLATE[role]} blob={blob}]\n"
    system = header + template_text + "\n\n[pinned_author_reading_contract: templates/config/ai_roles.template.yml]\n" + reads_text
    if language_instruction:
        system += "\n\n" + language_instruction + "\n"
    for source in AUTHOR_TEMPLATE_READ_SOURCES.get(role, ()):
        text, source_blob = _pinned_upstream(source)
        system += f"\n\n[pinned_author_supplementary_reading: {source} blob={source_blob}]\n{text}"
    if role in ROLE_REQUIRED_SECTIONS:
        headings = " / ".join(ROLE_REQUIRED_SECTIONS[role])
        beat_ids = "、".join(beat["beat_id"] for beat in contract["story"].get("required_beats", []))
        system += (
            "\n\n[project_output_contract]\n"
            f"请严格按作者模板的章节标题输出，至少包含这些标题：{headings}。\n"
            f"每个合同必需节拍必须以其 ID 出现于正文结构：{beat_ids}。\n"
            "只输出该角色的 Markdown 产物，不要输出解释或 JSON 包装。\n"
        )
    if role == "plot":
        intent = contract.get("work_intent")
        if intent == "INSERT_BETWEEN":
            source_scope = "所有新增动作必须与合同指定的前后锚点和原文连续；不得把来源中已有的位置和动作改写成未经支持的离场或返场。"
        elif intent == "ADAPT_SOURCE":
            source_scope = "仅依据合同明确选定的来源修订与选段设计改编；保留选段中可确认的来源事实，不把未选来源或未选范围当作事实。"
        elif intent == "ORIGINAL_EPISODE":
            source_scope = "这是无导入来源的原创工作：依据所选项目 Arc、Canon、人物资料和合法前章上下文设计；不得要求或臆造不存在的来源前后锚点。"
        else:
            # Preserve the pinned historical prompt semantics for legacy contracts.
            source_scope = "所有动作必须与所给前后原文连续；不得把来源中已有的位置和动作改写成未经支持的离场或返场。"
        system += (
            "\n[plot_design_responsibility]\n"
            "依据 Arc、Canon、人物资料和创作前准备，实际设计 Key Scenes、因果推进、"
            "Required Story Beats、Hook、伏笔与章节衔接。已有必需节拍是必须覆盖的要求，"
            "不构成完整结构；可以设计额外的动作、反应与节拍。不要仅把输入换成模板标题。"
            "遵守明确的事实、知识边界、入场和出场条件、全篇篇幅及本次工作范围。"
            "scene 工作单元仍限于同一场；episode 的场景安排由章节设计需要决定。"
            "按作者模板区分 Key Scenes（场景概要）与 Required Story Beats（必须发生的事件），"
            "本次叙事范围由工作单元及来源约束决定，不能仅用列表条目数判定是否越范围。"
            "输入 required_beats 为空仅表示没有预先指定节拍，仍必须由 Plot 设计具体 Required Story Beats；"
            "不能只列‘不越界’‘不解决线索’等合规条件来代替实际发生的故事事件。"
            + source_scope
            + "他人的动机、等待什么、故意给谁台阶等，不能仅凭可见动作写成 POV 已知事实。"
            "不得从执行器的记账元数据推导创作要求。\n"
        )
    payload = {
        "assignment": creative_assignment(contract),
        "materials": materials,
    }
    preparation_documents = (extra or {}).get("production_preparation", {}).get("documents", {})
    if role == "plot" and any(name.endswith("/derived/task_requirements.v1.json") for name in preparation_documents):
        system += ("\n[scoped_task_requirements]\n"
                   "封存任务快照中的要求须进入本次情节设计和后续岗位交付；保留 False、0、null 与缺失的差别。"
                   "快照和固定试验假定不是 Canon 晋升或执行许可。人物私有、未知或误信不等于 POV 或读者可知。"
                   "未决时间、冲突或缺失不能自行补成既定事实；不要因自由文字措辞不同判冲突。\n")
    if extra:
        payload["support"] = extra
    user = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_role_packet(role: str, contract_path: str | Path, inputs: dict[str, str | Path], *, accepted_receipts: list[dict[str, Any]] | None = None, mode: str = "offline") -> dict[str, Any]:
    if role not in ROLE_FILES:
        raise ContractError("ROLE_UNKNOWN", role)
    if mode not in {"offline", "live"}:
        raise ContractError("ROLE_MODE_INVALID", mode)
    raw_contract = Path(contract_path)
    if not raw_contract.is_absolute():
        raw_contract = ROOT / raw_contract
    contract_file = raw_contract.resolve(strict=True)
    contract_path = contract_file
    project_root = contract_file.parent.parent
    contract = load_contract(contract_path)
    if not contract_file.is_relative_to((ROOT / "workspace").resolve()):
        if contract.get("schema_version") != "cnw_work_unit_v2":
            raise ContractError("ROLE_INPUT_PATH_UNSAFE", "legacy contracts must remain inside their private workspace project")
        try:
            try:
                from .project_paths import resolve_project
            except ImportError:
                from project_paths import resolve_project
            registered = resolve_project(project_root, data_home=project_root.parent.parent)
        except Exception as exc:
            raise ContractError("PROJECT_ROOT_NOT_REGISTERED", str(project_root)) from exc
        if (registered.get("project_instance_id") != contract.get("project_instance_id") or
                registered.get("project_id") != contract.get("project_id")):
            raise ContractError("PROJECT_INSTANCE_IDENTITY_MISMATCH", "role packet contract differs from registered project")
    check_required_fields(contract)
    source = contract["source"]
    if contract.get("schema_version") == "cnw_work_unit_v2":
        try:
            from .cnw_contract import validate_v2_source_identity
        except ImportError:
            from cnw_contract import validate_v2_source_identity
        validate_v2_source_identity(contract, source_root=project_root)
    elif source.get("identity_type") == "imported_project":
        release_root = (project_root / source.get("source_root", ".")).resolve()
        version = source["version"]
        import_id = source["import_id"]
        manifest_hash = source["source_manifest_sha256"]
    elif source.get("identity_type") is None and "zip_sha256" in source:
        raise ContractError("LEGACY_MIGRATION_REQUIRED", "legacy Release role reads require a selected, pinned migration context")
    else:
        raise ContractError("SOURCE_TYPE_UNSUPPORTED", str(source.get("identity_type")))
    if contract.get("schema_version") != "cnw_work_unit_v2":
        validate_source_identity(
            contract,
            source_root=release_root,
            expected_version=version,
            expected_zip_sha256=import_id,
            expected_manifest_sha256=manifest_hash,
        )
    policy_path = ROOT / "config" / "cnw_production_policy.json"
    if contract.get("schema_version") == "cnw_work_unit_v2":
        policy_path = ROOT / "config" / "policies" / "app_policy.v1.json"
    if contract["unit"].get("policy_sha256", "").lower() != sha256_file(policy_path):
        raise ContractError("PRODUCTION_POLICY_IDENTITY_MISMATCH", "policy SHA256 differs from the frozen contract")
    cnw_manifest = ROOT / "runtime" / "reference" / "cnw_97ad71fe5e5e" / "CNW_LOCAL_REFERENCE_MANIFEST.json"
    expected_cnw_manifest = contract.get("review", {}).get("cnw_reference_manifest_sha256", "").lower()
    if not cnw_manifest.is_file() or sha256_file(cnw_manifest) != expected_cnw_manifest:
        raise ContractError("CNW_REFERENCE_IDENTITY_MISMATCH", "captured CNW reference manifest differs")
    validate_work_unit(contract)
    allowed_inputs = {
        "plot": ("canon_scope", "source_anchors"),
        "cards": ("plot", "canon_scope"),
        "brief": ("plot", "cards", "canon_scope", "style_guide", "voice_samples", "nk_reflection"),
        "prose": ("brief", "voice_samples"),
    }[role]
    if (role == "brief" and contract.get("schema_version") == "cnw_work_unit_v2"
            and contract.get("integrations", {}).get("nk", "DISABLED") == "DISABLED"):
        # NK is an opt-in support component for V2. The core CNW Brief role
        # must remain usable without a POV stage or any NK-derived material.
        allowed_inputs = tuple(name for name in allowed_inputs if name != "nk_reflection")
    expected = allowed_inputs
    missing = [name for name in expected if name not in inputs]
    if missing:
        raise ContractError("ROLE_DEPENDENCY_MISSING", ", ".join(missing))
    extra = set(inputs) - set(allowed_inputs)
    if extra:
        raise ContractError("ROLE_INPUT_SCOPE_VIOLATION", f"{role} may not receive {sorted(extra)}")
    required_receipts = {"plot": (), "cards": ("plot",), "brief": ("plot", "cards"), "prose": ("plot", "cards", "brief")}[role]
    if required_receipts:
        receipts = accepted_receipts or []
        verify_stage_chain(receipts, required_receipts, allow_fixtures=role != "prose" and mode == "offline")
        if any(receipt.get("work_id") != contract["unit"]["id"] for receipt in receipts):
            raise ContractError("CNW_STAGE_WORK_ID_MISMATCH", contract["unit"]["id"])
        contract_digest = sha256_file(contract_path)
        for prior_role in required_receipts:
            match = next(receipt for receipt in receipts if receipt.get("role") == prior_role)
            if match.get("contract_sha256") != contract_digest:
                raise ContractError("CNW_STAGE_CONTRACT_MISMATCH", prior_role)
            input_name = {"plot": "plot", "cards": "cards", "brief": "brief"}[prior_role]
            if input_name in inputs:
                input_path, _ = _read_project_file(inputs[input_name], project_root)
                if match.get("output_sha256") != sha256_file(input_path):
                    raise ContractError("CNW_DEPENDENCY_OUTPUT_MISMATCH", prior_role)
    prompt_path = PROMPT_DIR / ROLE_FILES[role]
    prompt = prompt_path.read_text(encoding="utf-8")
    hashes = _hash_inputs(inputs, project_root)
    packet = {
        "role": role,
        "work_id": contract["unit"]["id"],
        "contract_sha256": sha256_file(contract_path),
        "upstream_method": contract.get("review", {}).get("workflow_template_git_blob", "pinned"),
        "author_template_source": ROLE_TO_AUTHOR_TEMPLATE[role],
        "prompt_sha256": sha256_file(prompt_path),
        "input_hashes": hashes,
        "target_visible_chars": contract["unit"].get("target_visible_chars"),
        "required_beat_ids": [b["beat_id"] for b in contract["story"].get("required_beats", [])],
        "prompt": prompt,
        "inputs": {name: _read_project_file(path, project_root)[1] for name, path in inputs.items()},
    }
    if mode == "offline":
        packet["execution_mode"] = "MOCK_ONLY"
        packet["provider_call"] = "not_performed_by_role_packet_builder"
    else:
        packet["execution_mode"] = "LIVE_REQUEST_READY"
        packet["provider_call"] = "not_performed_by_role_packet_builder"
    if role == "prose":
        packet.update(build_prose_input_view(contract, packet["inputs"]["brief"], packet["inputs"]["voice_samples"]))
    else:
        packet["assignment"] = creative_assignment(contract)
    return packet


def validate_role_output(role: str, contract: dict[str, Any], output: str, metadata: dict[str, Any] | None = None) -> None:
    if role not in {"plot", "cards", "brief", "prose"}:
        raise ContractError("ROLE_UNKNOWN", role)
    if not output.strip() or output.lstrip().startswith("RETURN:"):
        raise ContractError("ROLE_OUTPUT_INVALID", "empty output or role returned a failure")
    beat_ids = [beat["beat_id"] for beat in contract["story"].get("required_beats", [])]
    if role in ("plot", "cards", "brief"):
        required_sections = ROLE_REQUIRED_SECTIONS[role]
        missing_sections = [section for section in required_sections if section.casefold() not in output.casefold()]
        if missing_sections:
            raise ContractError("ROLE_TEMPLATE_SECTION_MISSING", ", ".join(missing_sections))
        missing = [beat_id for beat_id in beat_ids if beat_id not in output]
        if missing:
            raise ContractError("ROLE_BEAT_ID_DROPPED", ", ".join(missing))
        if role == "plot" and contract["unit"].get("planning_mode") == "author_plot":
            plot_structure(output, contract)
        # Machine markers belong in the sidecar, not the literary Markdown. When the
        # sidecar is supplied its budgets are checked against the frozen contract.
        if metadata is not None:
            _validate_sidecar_budget(contract, metadata)
        elif re.search(r"^CNW_CONTRACT target_visible_chars=", output, re.MULTILINE):
            _validate_legacy_markers(contract, output)
    if role == "prose":
        validate_output_length(contract, output)


def _validate_sidecar_budget(contract: dict[str, Any], metadata: dict[str, Any]) -> None:
    unit = contract["unit"]
    expected = {"target_visible_chars": unit["target_visible_chars"], "min_visible_chars": unit["min_visible_chars"], "max_visible_chars": unit["max_visible_chars"]}
    actual = {key: metadata.get(key) for key in expected}
    if actual != expected:
        raise ContractError("ROLE_CONTRACT_LENGTH_MISMATCH", f"expected {expected}, got {actual}")
    if unit.get("planning_mode") == "author_plot":
        expected_requirements = [{"beat_id": beat["beat_id"]} for beat in contract["story"].get("required_beats", [])]
        if metadata.get("planning_mode") != "author_plot" or metadata.get("beats") != expected_requirements:
            raise ContractError("ROLE_REQUIREMENTS_MISMATCH", "assignment requirements differ")
        return
    expected_beats = {beat["beat_id"]: beat["budget_visible_chars"] for beat in contract["story"].get("required_beats", [])}
    actual_beats = {row.get("beat_id"): row.get("budget_visible_chars") for row in metadata.get("beats", [])}
    if actual_beats != expected_beats:
        raise ContractError("ROLE_BEAT_BUDGET_MISMATCH", f"expected {expected_beats}, got {actual_beats}")


def _validate_legacy_markers(contract: dict[str, Any], output: str) -> None:
    unit = contract["unit"]
    marker = re.search(r"^CNW_CONTRACT target_visible_chars=(\d+) min_visible_chars=(\d+) max_visible_chars=(\d+)$", output, re.MULTILINE)
    expected = (unit["target_visible_chars"], unit["min_visible_chars"], unit["max_visible_chars"])
    if not marker:
        raise ContractError("ROLE_CONTRACT_MANIFEST_MISSING", "required CNW_CONTRACT marker not found")
    actual = tuple(int(value) for value in marker.groups())
    if actual != expected:
        raise ContractError("ROLE_CONTRACT_LENGTH_MISMATCH", f"expected {expected}, got {actual}")
    beat_markers = re.findall(r"^CNW_BEAT ([A-Za-z0-9_.-]+) budget_visible_chars=(\d+)$", output, re.MULTILINE)
    expected_beats = {beat["beat_id"]: beat["budget_visible_chars"] for beat in contract["story"].get("required_beats", [])}
    actual_beats = {beat_id: int(budget) for beat_id, budget in beat_markers}
    if actual_beats != expected_beats or len(beat_markers) != len(expected_beats):
        raise ContractError("ROLE_BEAT_BUDGET_MISMATCH", f"expected {expected_beats}, got {actual_beats}")


def role_receipt(role: str, packet: dict[str, Any], output: str, *, status: str, provider_request_ids: list[str] | None = None, controller_accept_ref: str | None = None) -> dict[str, Any]:
    if status not in {"FIXTURE_ONLY", "PROVIDER_RESULT_PENDING_REVIEW", "STAGE_MATERIALIZED", "CONTROLLER_ACCEPTED"}:
        raise ContractError("ROLE_RECEIPT_STATUS_INVALID", status)
    if status in {"STAGE_MATERIALIZED", "CONTROLLER_ACCEPTED"} and not provider_request_ids:
        raise ContractError("ROLE_ACCEPTANCE_EVIDENCE_MISSING", "a real provider request is required")
    if status == "CONTROLLER_ACCEPTED" and not controller_accept_ref:
        raise ContractError("ROLE_ACCEPTANCE_EVIDENCE_MISSING", "a Controller acceptance reference is required")
    return {
        "role": role,
        "work_id": packet["work_id"],
        "status": status,
        "contract_sha256": packet["contract_sha256"],
        "prompt_sha256": packet["prompt_sha256"],
        "input_hashes": packet["input_hashes"],
        "output_sha256": sha256_bytes(output.encode("utf-8")),
        "provider_request_ids": provider_request_ids or [],
        "controller_accept_ref": controller_accept_ref,
    }


def verify_stage_chain(receipts: list[dict[str, Any]], required_roles: tuple[str, ...] = ("plot", "cards", "brief"), *, allow_fixtures: bool = False) -> None:
    roles = tuple(receipt.get("role") for receipt in receipts)
    if roles != required_roles:
        raise ContractError("CNW_STAGE_CHAIN_INCOMPLETE", f"expected {required_roles}, got {roles}")
    work_ids = {receipt.get("work_id") for receipt in receipts}
    if len(work_ids) != 1:
        raise ContractError("CNW_STAGE_WORK_ID_MISMATCH", "role receipts have different work IDs")
    fixture_chain = allow_fixtures and all(receipt.get("status") == "FIXTURE_ONLY" and not receipt.get("provider_request_ids") for receipt in receipts)
    if fixture_chain:
        contract_hashes = {receipt.get("contract_sha256") for receipt in receipts}
        if len(contract_hashes) != 1 or None in contract_hashes:
            raise ContractError("CNW_STAGE_CONTRACT_MISMATCH", "fixture receipts do not share a frozen contract")
        return
    if any(str(request_id).lower().startswith(("fixture", "test", "mock")) for receipt in receipts for request_id in receipt.get("provider_request_ids", [])):
        raise ContractError("CNW_FIXTURE_CANNOT_UNLOCK_PROSE", "fixture request IDs cannot satisfy a production stage gate")
    # A normal production step materializes a real provider artifact; it does not
    # require a separate external Controller sign-off for every writing role.
    materialized = {"STAGE_MATERIALIZED", "CONTROLLER_ACCEPTED"}
    if any(receipt.get("status") not in materialized for receipt in receipts):
        raise ContractError("CNW_STAGE_CHAIN_INCOMPLETE", "each planning role needs a materialized provider artifact")
    contract_hashes = {receipt.get("contract_sha256") for receipt in receipts}
    if len(contract_hashes) != 1 or None in contract_hashes:
        raise ContractError("CNW_STAGE_CONTRACT_MISMATCH", "role receipts do not share one frozen contract")
    if any(not receipt.get("provider_request_ids") for receipt in receipts):
        raise ContractError("CNW_ACCEPTANCE_EVIDENCE_MISSING", "each planning role needs a real provider request")
