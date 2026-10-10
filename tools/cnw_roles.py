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
    from .cnw_contract import ContractError, check_required_fields, load_contract, validate_episode_budget, validate_output_length, validate_scene_budget, validate_source_identity
except ImportError:  # direct script execution
    from cnw_contract import ContractError, check_required_fields, load_contract, validate_episode_budget, validate_output_length, validate_scene_budget, validate_source_identity

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
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    resolved = candidate.resolve(strict=True)
    allowed = ((project_root or (ROOT / "workspace" / "cangqi")).resolve(), (ROOT / "runs").resolve())
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
        candidate = (project_root / arc_ref).resolve(strict=True)
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


def resolve_author_reads(role: str, project_root: Path, work_id: str, *, arc_ref: str | None = None) -> dict[str, Path]:
    """Resolve the author reading list to concrete private project files."""
    if role not in AUTHOR_ROLE_READS:
        raise ContractError("ROLE_UNKNOWN", role)
    resolved: dict[str, Path] = {}
    for template in AUTHOR_ROLE_READS[role]:
        if "<NN>" in template:
            resolved[template] = resolve_arc(project_root, work_id, arc_ref)
        elif "<work_id>" in template:
            resolved[template] = project_root / template.replace("<work_id>", work_id)
        else:
            resolved[template] = project_root / template
    for template, path in resolved.items():
        if not path.is_file() or path.is_symlink():
            raise ContractError("AUTHOR_READ_MISSING", template)
    return resolved


def read_actual_texts(project_root: Path, role: str, work_id: str, *, arc_ref: str | None = None) -> dict[str, str]:
    return {template: path.read_text(encoding="utf-8-sig") for template, path in resolve_author_reads(role, project_root, work_id, arc_ref=arc_ref).items()}


def read_production_preparation(project_root: Path, contract: dict) -> dict:
    """Read the public production manual's preparation sources before Plot."""
    arc = resolve_arc(project_root, contract["unit"]["id"], contract["story"].get("arc_ref"))
    paths = [project_root / "94_runtime/current_state.md", project_root / "07_draft/manuscript_index.md", arc,
             arc.with_name(arc.stem + "_episode_details.md"),
             project_root / "92_style_engine/character_voice_samples.md", project_root / "90_canon/character_bible.md"]
    previous = contract["story"].get("previous_episode_ref")
    episode = re.fullmatch(r"(ep|ch)(\d+)", contract["unit"]["id"], re.I)
    if not previous and episode and int(episode.group(2)) > 1:
        previous = f"07_draft/episodes/{episode.group(1)}{int(episode.group(2))-1:0{len(episode.group(2))}d}.md"
    if not previous and contract["unit"].get("kind") == "episode" and not episode and not contract["story"].get("first_episode"):
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
    return {"documents": documents, "source_hashes": hashes,
            "source_method": "example_project/00_meta/episode_production_manual.md#production-reading-order",
            "previous_episode": previous or ("FIRST_EPISODE" if episode or contract["story"].get("first_episode") else "SCENE_SOURCE_ANCHORS")}


def relevant_voice_samples(text: str, characters: list[str]) -> str:
    """Select character sections, retaining their nested sample headings only."""
    if not characters:
        raise ContractError("PROSE_CAST_MISSING", "participating characters are required")
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


def build_prose_input_view(contract: dict[str, Any], brief: str, voice_samples: str) -> dict[str, Any]:
    """Return only the brief, relevant voices, and minimum execution bounds."""
    unit = contract["unit"]
    voice_samples = relevant_voice_samples(voice_samples, contract["story"].get("characters_in_scene", []))
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
        "beats": [{"beat_id": beat["beat_id"], "budget_visible_chars": beat["budget_visible_chars"]} for beat in contract["story"].get("required_beats", [])],
    }


def build_author_role_messages(role: str, contract: dict[str, Any], materials: dict[str, str], *, extra: dict[str, Any] | None = None) -> list[dict]:
    """Reproduce the author template + reading list, then the project values."""
    if role not in ROLE_TO_AUTHOR_TEMPLATE:
        raise ContractError("ROLE_UNKNOWN", role)
    if role == "prose":
        brief_key, voice_key = AUTHOR_ROLE_READS["prose"]
        brief = materials[brief_key]
        voices = relevant_voice_samples(materials[voice_key], contract["story"]["characters_in_scene"])
        # Canon, plot, contract.story, and review rules must reach prose only
        # through the Brief. The orchestrator retains validation metadata.
        return [
            {"role": "system", "content": "Write the complete story prose specified by the Writing Brief, using the participating characters' voice samples. Output only the prose, without planning notes or commentary."},
            {"role": "user", "content": json.dumps({"writing_brief": brief, "voice_samples": voices}, ensure_ascii=False)},
        ]
    template_text, blob = _pinned_upstream(ROLE_TO_AUTHOR_TEMPLATE[role])
    reads_text, _ = _pinned_upstream("templates/config/ai_roles.template.yml")
    header = f"[pinned_author_template: {ROLE_TO_AUTHOR_TEMPLATE[role]} blob={blob}]\n"
    system = header + template_text + "\n\n[pinned_author_reading_contract: templates/config/ai_roles.template.yml]\n" + reads_text
    if role in ROLE_REQUIRED_SECTIONS:
        headings = " / ".join(ROLE_REQUIRED_SECTIONS[role])
        beat_ids = "、".join(beat["beat_id"] for beat in contract["story"].get("required_beats", []))
        system += (
            "\n\n[project_output_contract]\n"
            f"请严格按作者模板的章节标题输出，至少包含这些标题：{headings}。\n"
            f"每个合同必需节拍必须以其 ID 出现于正文结构：{beat_ids}。\n"
            "只输出该角色的 Markdown 产物，不要输出解释或 JSON 包装。\n"
        )
    payload = {
        "contract": {k: contract[k] for k in ("project_id", "unit", "story") if k in contract},
        "materials": materials,
        "machine_metadata_sidecar": role_metadata(role, contract),
    }
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
    if not contract_file.is_relative_to((ROOT / "workspace").resolve()):
        raise ContractError("ROLE_INPUT_PATH_UNSAFE", "contract must belong to a private workspace project")
    contract = load_contract(contract_path)
    check_required_fields(contract)
    source = contract["source"]
    if source.get("identity_type") == "imported_project":
        release_root = (project_root / source.get("source_root", ".")).resolve()
        version = source["version"]
        import_id = source["import_id"]
        manifest_hash = source["source_manifest_sha256"]
    else:
        release_root = ROOT / "inputs" / "private" / "release" / source["zip_sha256"].lower() / "Cangqi_Jun_Release_2_3"
        version = source["version"]
        import_id = source["zip_sha256"]
        manifest_hash = source["local_private_source_manifest_sha256"]
    validate_source_identity(
        contract,
        source_root=release_root,
        expected_version=version,
        expected_zip_sha256=import_id,
        expected_manifest_sha256=manifest_hash,
    )
    policy_path = ROOT / "config" / "cnw_production_policy.json"
    if contract["unit"].get("policy_sha256", "").lower() != sha256_file(policy_path):
        raise ContractError("PRODUCTION_POLICY_IDENTITY_MISMATCH", "policy SHA256 differs from the frozen contract")
    cnw_manifest = ROOT / "runtime" / "reference" / "cnw_97ad71fe5e5e" / "CNW_LOCAL_REFERENCE_MANIFEST.json"
    expected_cnw_manifest = contract.get("review", {}).get("cnw_reference_manifest_sha256", "").lower()
    if not cnw_manifest.is_file() or sha256_file(cnw_manifest) != expected_cnw_manifest:
        raise ContractError("CNW_REFERENCE_IDENTITY_MISMATCH", "captured CNW reference manifest differs")
    if contract["unit"]["kind"] == "scene":
        validate_scene_budget(contract)
    elif contract["unit"]["kind"] == "episode":
        validate_episode_budget(contract["unit"])
    else:
        raise ContractError("WORK_UNIT_KIND_INVALID", str(contract["unit"].get("kind")))
    allowed_inputs = {
        "plot": ("canon_scope", "source_anchors"),
        "cards": ("plot", "canon_scope"),
        "brief": ("plot", "cards", "canon_scope", "style_guide", "voice_samples", "nk_reflection"),
        "prose": ("brief", "voice_samples"),
    }[role]
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
        packet["contract"] = contract
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
