"""Source-derived task data, separate from Canon and execution authorization."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .cnw_contract import ContractError, _safe_source_file
except ImportError:
    from cnw_contract import ContractError, _safe_source_file


SCHEMA = "cnw_task_requirements_v1"
RECIPE = "legacy_scene_requirements_v1"

# These are engine bindings or old input-review claims. They remain archived;
# the writing model cannot use them as permissions or source-authority aliases.
WORK_ORDER_TECHNICAL_FIELDS = {
    "schema_version", "unit_id", "project_id", "source_pin", "author_method_pin",
    "source_context_file", "original_authority", "input_source_preflight_required",
    "original_manuscript_byte_binding", "input_preflight_v5", "input_pack",
    "review", "integrations", "execution", "provider", "policy", "policy_sha256",
}
PACKET_SOURCE_COPIES = {"id", "before_anchor", "after_anchor", "original_before", "original_after"}
KNOWN_WORK_ORDER_FIELDS = {
    "kind", "planning_mode", "pov", "language", "language_locale", "target_visible_chars",
    "min_visible_chars", "max_visible_chars", "required_beats", "entry_state", "exit_state",
    "role_in_story", "reader_reward", "characters_in_scene", "arc_ref",
    "character_knowledge_boundary_ref", "voice_sample_refs", "forbidden_future_revelations",
    "knowledge_snapshot", "gameplay_snapshot", "focus_characters", "fact_provenance",
    "new_plot_pre_designed", "scope_of_new_plot", "creative_freedom", "allowed_local_change",
    "standalone_trial", "speaking_cast_interpretation",
}


def encode(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContractError("TASK_REQUIREMENTS_VALUE_INVALID", "task data must preserve finite JSON values and types") from exc


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ContractError("TASK_REQUIREMENTS_JSON_AMBIGUOUS", "duplicate task field")
        result[key] = value
    return result


def decode(raw: bytes) -> dict:
    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("TASK_REQUIREMENTS_SOURCE_INVALID", "task source must be UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ContractError("TASK_REQUIREMENTS_SOURCE_INVALID", "task source must be an object")
    encode(value)
    return value


def _pointer(key: str) -> str:
    return "/" + key.replace("~", "~0").replace("/", "~1")


class TaskRequirementConflict(ContractError):
    def __init__(self, code: str, *, work_id: str, field: str, left: dict, right: dict):
        super().__init__(code, f"本任务的两处明确要求在 {field} 不一致，需要决定采用哪份输入。")
        self.task_conflict = {"status": "INPUT_REQUIREMENTS_CONFLICT", "work_id": work_id,
            "resolution": "USER_CREATIVE_DECISION_NEEDED", "conflicts": [
                {"kind": code, "field": field, "sources": [left, right]}]}


def _require_same_declaration(a, b, *, field: str, work_id: str, sources: dict,
                              left_category: str, left_pointer: str,
                              right_category: str, right_pointer: str, code: str) -> None:
    if encode(a) == encode(b):
        return
    def location(category, pointer, value):
        name, raw = sources[category]
        return {"file": name, "sha256": sha(raw), "pointer": pointer, "declared_value": value}
    raise TaskRequirementConflict(code, work_id=work_id, field=field,
        left=location(left_category, left_pointer, a), right=location(right_category, right_pointer, b))


def _check_gameplay_declarations(order: dict, documents: dict, sources: dict) -> None:
    left = order.get("gameplay_snapshot")
    right = documents.get("gameplay_snapshot")
    if not isinstance(left, dict) or not isinstance(right, dict):
        return
    # Both were explicitly supplied as this task's snapshots. Different
    # explicit temporal scopes are separate assertions, never merged here.
    for scope in ("scope", "time_scope", "as_of"):
        if scope in left and scope in right and encode(left[scope]) != encode(right[scope]):
            return
    def compare(a, b, pointer=""):
        for key in sorted(set(a) & set(b)):
            av, bv = a[key], b[key]
            current = pointer + _pointer(key)
            if isinstance(av, dict) and isinstance(bv, dict):
                compare(av, bv, current)
            elif av is not None and bv is not None and (
                    type(av) in {bool, int, float} or type(bv) in {bool, int, float}
                    or key == "id" or key.endswith("_id")):
                _require_same_declaration(av, bv, field="gameplay_snapshot" + current,
                    work_id=order["unit_id"], sources=sources, left_category="work_order",
                    left_pointer="/gameplay_snapshot" + current, right_category="gameplay_snapshot",
                    right_pointer=current, code="TASK_REQUIREMENTS_DUPLICATE_CONFLICT")
    compare(left, right)


def derive_task_context(*, sources: dict[str, tuple[str, bytes]], identity: dict,
                        scene_root: str, pack_sha256: str) -> dict:
    """Pure recipe: values and locators come only from frozen input bytes.

    The caller supplies explicit archive paths, not file names taken from a
    model or an opaque writing field. This function opens no files or tools.
    """
    if set(sources) - {"work_order", "scene_packet", "temporal_envelope", "gameplay_snapshot"}:
        raise ContractError("TASK_REQUIREMENTS_SOURCE_INVALID", "undeclared task source category")
    if not {"work_order", "scene_packet"} <= set(sources):
        raise ContractError("TASK_REQUIREMENTS_SOURCE_MISSING", "task needs its frozen work order and scene packet")
    documents = {name: decode(raw) for name, (_, raw) in sources.items()}
    order, packet = documents["work_order"], documents["scene_packet"]
    for key in ("pov", "new_plot_pre_designed", "standalone_trial"):
        if key not in order or key not in packet:
            continue
        a, b = order[key], packet[key]
        # Missing and null are not assertions. Free-text differences and
        # distinct points of view/knowledge scopes cannot be judged here.
        if a is None or b is None:
            continue
        discrete = key == "pov" or (type(a) is bool and type(b) is bool)
        if discrete:
            _require_same_declaration(a, b, field=key, work_id=order["unit_id"], sources=sources,
                left_category="work_order", left_pointer=_pointer(key), right_category="scene_packet",
                right_pointer=_pointer(key), code="TASK_REQUIREMENTS_DISCRETE_CONFLICT")
    _check_gameplay_declarations(order, documents, sources)
    projected = {}
    provenance = []
    for name, document in documents.items():
        excluded = WORK_ORDER_TECHNICAL_FIELDS if name == "work_order" else PACKET_SOURCE_COPIES if name == "scene_packet" else set()
        selected = {key: value for key, value in document.items() if key not in excluded}
        projected[name] = selected
        path, raw = sources[name]
        for key in selected:
            provenance.append({"task_pointer": f"/data/{name}{_pointer(key)}", "source_file": path,
                               "source_sha256": sha(raw), "source_pointer": _pointer(key)})
    unknown = sorted(set(projected["work_order"]) - KNOWN_WORK_ORDER_FIELDS)
    return {"schema_version": SCHEMA, "recipe_version": RECIPE,
            "project_id": identity["project_id"], "project_instance_id": identity["project_instance_id"],
            "work_id": order["unit_id"], "original_project_id": order["project_id"],
            "scene_root": scene_root, "pack_sha256": pack_sha256,
            "authority": "SCOPED_WRITING_TASK_DATA_NOT_CANON_OR_EXECUTION_PERMISSION",
            "data": projected, "provenance": provenance,
            "opaque_work_order_fields": unknown,
            "opaque_semantic_status": "UNPROVEN_EXTENSION" if unknown else "NO_OPAQUE_WORK_ORDER_FIELDS"}


def validate_derivation(context: dict, *, sources: dict[str, tuple[str, bytes]], identity: dict,
                        scene_root: str, pack_sha256: str) -> None:
    if context.get("schema_version") != SCHEMA or context.get("recipe_version") != RECIPE:
        raise ContractError("TASK_REQUIREMENTS_RECIPE_UNSUPPORTED", "unknown derivation schema or recipe")
    expected = derive_task_context(sources=sources, identity=identity, scene_root=scene_root, pack_sha256=pack_sha256)
    # Canonical JSON comparison distinguishes False from 0, null from missing,
    # and numeric/string types, unlike Python dict equality.
    if encode(context) != encode(expected):
        raise ContractError("TASK_REQUIREMENTS_DERIVATION_MISMATCH", "task values, types, identities or locators differ from the frozen sources")


def frozen_task_sources(project_root: Path, index: dict) -> dict[str, tuple[str, bytes]]:
    snapshot = f"_INBOX/input_packs/{index['pack_sha256']}"
    seed = f"{snapshot}/{index['scene_root']}/project_seed/"
    names = {"work_order": f"{snapshot}/{index['scene_root']}/work_order.draft.json",
             "scene_packet": seed + "scene_packet.json"}
    if index.get("original_work_order") != names["work_order"]:
        raise ContractError("TASK_REQUIREMENTS_SOURCE_INVALID", "task must select its own archived work order")
    for key, relative in (("temporal_envelope", "93_data/temporal_envelope.json"),
                          ("gameplay_snapshot", "93_data/gameplay_snapshot.json")):
        name = seed + relative
        if name in index["files"]:
            names[key] = name
    result = {}
    for key, name in names.items():
        if name not in index["files"]:
            raise ContractError("TASK_REQUIREMENTS_SOURCE_MISSING", "task source is absent from its immutable binding")
        raw = _safe_source_file(project_root, name).read_bytes()
        if sha(raw) != index["files"][name]:
            raise ContractError("TASK_REQUIREMENTS_SOURCE_CHANGED", "frozen task source failed its byte hash")
        result[key] = (name, raw)
    return result


def verify_bound_task_context(project_root: Path, index: dict) -> tuple[str, dict] | None:
    descriptor = index.get("task_context")
    if descriptor is None:
        # Existing contracts/bindings retain their historical input semantics.
        return None
    expected_name = f"_INBOX/input_packs/{index['pack_sha256']}/derived/task_requirements.v1.json"
    if (not isinstance(descriptor, dict) or descriptor.get("schema_version") != SCHEMA or
            descriptor.get("recipe_version") != RECIPE or descriptor.get("file") != expected_name or
            descriptor.get("sha256") != index["files"].get(expected_name)):
        raise ContractError("TASK_REQUIREMENTS_BINDING_INVALID", "task context must bind its declared recipe and private derived file")
    raw = _safe_source_file(project_root, expected_name).read_bytes()
    if sha(raw) != descriptor["sha256"]:
        raise ContractError("TASK_REQUIREMENTS_DERIVATION_MISMATCH", "derived task file changed")
    context = decode(raw)
    identity = {key: index[key] for key in ("project_id", "project_instance_id")}
    validate_derivation(context, sources=frozen_task_sources(project_root, index), identity=identity,
                        scene_root=index["scene_root"], pack_sha256=index["pack_sha256"])
    if raw != encode(context):
        raise ContractError("TASK_REQUIREMENTS_DERIVATION_MISMATCH", "derived file is not the exact recipe serialization")
    return expected_name, context


def read_bound_task_context(project_root: Path, contract: dict) -> tuple[str, dict] | None:
    if contract.get("schema_version") != "cnw_work_unit_v2" or "input_pack" not in contract:
        return None
    try:
        from .cnw_input_pack import validate_input_pack_binding
    except ImportError:
        from cnw_input_pack import validate_input_pack_binding
    index = validate_input_pack_binding(project_root, contract["input_pack"], contract=contract)
    return verify_bound_task_context(project_root, index)


def lens_task_view(context: dict, lens_id: str) -> dict | None:
    """Select task constraints for one review duty; never other Lens opinions."""
    if lens_id == "style":
        return None
    if lens_id not in {"character", "plot", "canon", "story_specific"}:
        raise ContractError("TASK_REQUIREMENTS_LENS_UNKNOWN", lens_id)
    data = context["data"]
    if lens_id == "story_specific":
        selected = data
    elif lens_id == "character":
        order_fields = {"pov", "characters_in_scene", "focus_characters", "knowledge_snapshot",
                        "character_knowledge_boundary_ref", "voice_sample_refs", "forbidden_future_revelations"}
        packet_fields = {"pov", "cast", "speaking_cast", "speaking_cast_interpretation", "role_states", "reader_knowledge", "forbidden_future"}
        selected = {"work_order": {k: v for k, v in data["work_order"].items() if k in order_fields},
                    "scene_packet": {k: v for k, v in data["scene_packet"].items() if k in packet_fields}}
    elif lens_id == "plot":
        order_fields = {"kind", "planning_mode", "scope_of_new_plot", "new_plot_pre_designed", "required_beats",
                        "entry_state", "exit_state", "role_in_story", "reader_reward", "focus_characters",
                        "creative_freedom", "allowed_local_change", "standalone_trial"}
        packet_fields = {"available_time", "current_location", "entry_state", "exit_invariants", "allowed_local_change",
                         "reader_reward", "creative_freedom", "next_fixed_event", "standalone_trial", "required_beats", "new_plot_pre_designed"}
        selected = {"work_order": {k: v for k, v in data["work_order"].items() if k in order_fields},
                    "scene_packet": {k: v for k, v in data["scene_packet"].items() if k in packet_fields}}
    else:
        selected = {name: value for name, value in data.items() if name == "temporal_envelope"}
        selected["work_order"] = {k: v for k, v in data["work_order"].items() if k == "fact_provenance"}
    pointers = {f"/data/{name}{_pointer(key)}" for name, values in selected.items() for key in values}
    return {"schema_version": SCHEMA, "recipe_version": RECIPE, "lens_id": lens_id,
            "project_instance_id": context["project_instance_id"], "work_id": context["work_id"],
            "authority": context["authority"], "data": selected,
            "provenance": [record for record in context["provenance"] if record["task_pointer"] in pointers]}


def review_task_sources(project_root: Path, contract: dict) -> dict[str, str]:
    """Revalidate frozen inputs and expose only the current task's review views."""
    bound = read_bound_task_context(project_root, contract)
    if bound is None:
        return {}
    name, context = bound
    source = {"file": name, "sha256": sha(encode(context))}
    result = {"task_requirements": encode({**context, "context_source": source}).decode("utf-8")}
    for lens_id in ("character", "plot", "canon", "story_specific"):
        view = lens_task_view(context, lens_id)
        result[f"task_constraints:{lens_id}"] = encode({**view, "context_source": source}).decode("utf-8")
    return result
