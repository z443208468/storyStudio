"""Native writing packages: declared groups, selected sources and chapter dependencies.

No embedded code, registry, receipt or authorization is installed. Original
declarations remain immutable; contracts and carry-forward are appended later.
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace

try:
    from .cnw_contract import ContractError, _safe_source_file, validate_v2_source_identity
    from .cnw_input_pack import _bytes, _json, _sha, _safe_name, _active_seed, _source_bytes
    from .project_paths import create_project, resolve_project, _assert_no_reparse, _ensure_private_directory
    from .project_transactions import project_write_lock
    from . import cnw_project as projects, cnw_task_requirements as tasks
except ImportError:
    from cnw_contract import ContractError, _safe_source_file, validate_v2_source_identity
    from cnw_input_pack import _bytes, _json, _sha, _safe_name, _active_seed, _source_bytes
    from project_paths import create_project, resolve_project, _assert_no_reparse, _ensure_private_directory
    from project_transactions import project_write_lock
    import cnw_project as projects, cnw_task_requirements as tasks

JOB_SCHEMA = "cnw_input_pack_job_v2"
BINDING_SCHEMA = "cnw_native_input_binding_v1"
ATTEMPT_BINDING_SCHEMA = "cnw_native_input_binding_v2"
BINDING_SCHEMAS = {BINDING_SCHEMA, ATTEMPT_BINDING_SCHEMA}
RESERVED_REQUIREMENTS = {"schema_version", "unit_id", "project_id", "project_instance_id", "source_id", "source_revision_id",
    "source_manifest_revision_sha256", "source_index_revision_sha256", "input_pack", "previous_episode_ref", "policy", "provider",
    "execution", "provider_call_authorized", "integrations", "review", "work_intent", "first_episode"}


def _alias(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value):
        raise ContractError("NATIVE_PACK_ALIAS_INVALID", "aliases must be unique portable names")
    return _safe_name(value)


def _unit_id(alias):
    # Every alias uses the same injective mapping, including one-character names.
    return _safe_name("TASK-" + _alias(alias))


def validate_declarations(files: dict, index: dict) -> dict:
    if (not isinstance(index, dict) or index.get("schema") != "cnw_workpack_index_v2"
            or not isinstance(index.get("projects"), list) or not index["projects"]
            or not isinstance(index.get("tasks"), list) or not index["tasks"]):
        raise ContractError("INPUT_PACK_INDEX_INVALID", "native package needs declared projects and tasks")
    groups, seen = {}, set()
    for group in index["projects"]:
        if not isinstance(group, dict):
            raise ContractError("INPUT_PACK_INDEX_INVALID", "project declaration must be an object")
        alias = _alias(group.get("alias"))
        if alias.casefold() in seen:
            raise ContractError("NATIVE_PACK_ALIAS_DUPLICATE", "duplicate project alias")
        seen.add(alias.casefold()); groups[alias] = group
        if not isinstance(group.get("project_id"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", group["project_id"]):
            raise ContractError("INPUT_PACK_TASK_ID_INVALID", "project display ID must be a safe component")
        prefix = _safe_name(group.get("materials", "")) + "/"
        material = {n[len(prefix):]: raw for n, raw in files.items() if n.startswith(prefix)}
        if not material:
            raise ContractError("PRE_FLIGHT_MISSING_PROJECT_INPUT", "declared project materials are missing")
        for name in material:
            if not _active_seed(name) or name.startswith("94_runtime/") or Path(name).name.casefold() in {
                    "project_identity.json", "run_state.json", "cost_ledger.json", "cost_ledger.jsonl"}:
                raise ContractError("INPUT_PACK_PRIVATE_RUNTIME_UNSUPPORTED", "native materials must be writing inputs only")
        fifth = group.get("fifth_lens")
        if not isinstance(fifth, dict) or not all(isinstance(fifth.get(k), str) and fifth[k].strip() for k in ("id", "responsibility")):
            raise ContractError("PRE_FLIGHT_MISSING_PROJECT_INPUT", "declare the project's fifth Lens duties")
        sources = group.get("sources", [])
        if not isinstance(sources, list):
            raise ContractError("NATIVE_PACK_SOURCE_INVALID", "sources must be explicit declarations")
        aliases = set()
        for source in sources:
            if not isinstance(source, dict):
                raise ContractError("NATIVE_PACK_SOURCE_INVALID", "source declaration must be an object")
            key = _alias(source.get("alias"))
            if key.casefold() in aliases:
                raise ContractError("NATIVE_PACK_ALIAS_DUPLICATE", "duplicate source alias")
            aliases.add(key.casefold())
            if source.get("format") not in {"md", "txt", "json"}:
                raise ContractError("SOURCE_TYPE_UNSUPPORTED", "declare md, txt or json source format")
            if ("file" in source) == ("authority" in source):
                raise ContractError("NATIVE_PACK_SOURCE_INVALID", "select package bytes or a pinned Git authority")
            if "file" in source and (_safe_name(source["file"]) not in files or Path(source["file"]).suffix.lower() != "." + source["format"]):
                raise ContractError("NATIVE_PACK_SOURCE_INVALID", "declared source file or format differs")
    by_alias, task_seen, unit_seen = {}, set(), set()
    for number, task in enumerate(index["tasks"], 1):
        if not isinstance(task, dict):
            raise ContractError("INPUT_PACK_INDEX_INVALID", "task declaration must be an object")
        alias = _alias(task.get("alias"))
        if alias.casefold() in task_seen:
            raise ContractError("NATIVE_PACK_ALIAS_DUPLICATE", "duplicate task alias")
        task_seen.add(alias.casefold())
        if task.get("project") not in groups or task.get("work_intent") not in {"INSERT_BETWEEN", "ADAPT_SOURCE", "ORIGINAL_EPISODE"}:
            raise ContractError("WORK_INTENT_UNSUPPORTED", "task needs its declared project and intent")
        unit_key = (task["project"], _unit_id(alias).casefold())
        if unit_key in unit_seen:
            raise ContractError("NATIVE_PACK_ALIAS_DUPLICATE", "tasks cannot share a generated contract path")
        unit_seen.add(unit_key)
        required_path = _safe_name(task.get("requirements", ""))
        req = _json(files.get(required_path, b"{}"))
        if not isinstance(req, dict) or not req or set(req) & RESERVED_REQUIREMENTS:
            raise ContractError("NATIVE_PACK_REQUIREMENTS_INVALID", "writing requirements cannot supply internal identities or permissions")
        tasks.encode(req)
        if task.get("context"):
            context = _safe_name(task["context"])
            if context not in files or not isinstance(_json(files[context]), dict):
                raise ContractError("NATIVE_PACK_REQUIREMENTS_INVALID", "declared task context must be a package JSON object")
        bounds = [req.get(k) for k in ("min_visible_chars", "target_visible_chars", "max_visible_chars")]
        if any(type(n) is not int for n in bounds) or not 1 <= bounds[0] <= bounds[1] <= bounds[2]:
            raise ContractError("SCENE_BUDGET_INVALID", "preserve three explicit ordered writing bounds")
        if req.get("language_locale") not in {"zh-CN", "en-US"}:
            raise ContractError("LOCALE_UNSUPPORTED", "declare a tested locale")
        source_aliases = {s["alias"] for s in groups[task["project"]].get("sources", [])}
        if task.get("previous_task") is not None:
            _alias(task["previous_task"])
        if task["work_intent"] == "ORIGINAL_EPISODE":
            if "source" in task or "selection" in task or req.get("kind") != "episode" or type(task.get("first_episode")) is not bool:
                raise ContractError("NATIVE_PACK_ORIGINAL_INVALID", "original episodes have no source or anchor and declare first/continuation")
            if task["first_episode"] == bool(task.get("previous_task")):
                raise ContractError("NATIVE_PACK_DEPENDENCY_INVALID", "first episodes have no predecessor; continuations must select one")
        elif task.get("source") not in source_aliases:
            code = "SOURCE_SELECTION_AMBIGUOUS" if len(source_aliases) > 1 and not task.get("source") else "SOURCE_SELECTION_REQUIRED"
            raise ContractError(code, "explicitly select a source alias from this project")
        elif not isinstance(task.get("selection"), dict) or not task["selection"]:
            raise ContractError("SOURCE_SELECTION_REQUIRED", "declare source anchors, line range or JSON Pointer")
        if task["work_intent"] != "ORIGINAL_EPISODE" and "previous_task" in task:
            raise ContractError("NATIVE_PACK_DEPENDENCY_INVALID", "only same-project original continuation is supported")
        by_alias[alias] = {**task, "index_ordinal": number}
    order, visiting, done = [], set(), set()
    def visit(alias):
        if alias in visiting:
            raise ContractError("NATIVE_PACK_DEPENDENCY_INVALID", "self references and dependency cycles are refused")
        if alias in done:
            return
        visiting.add(alias)
        previous = by_alias[alias].get("previous_task")
        if previous:
            if previous not in by_alias or by_alias[previous]["project"] != by_alias[alias]["project"] or by_alias[previous]["work_intent"] != "ORIGINAL_EPISODE":
                raise ContractError("NATIVE_PACK_DEPENDENCY_INVALID", "predecessor must be an original task in the same project")
            visit(previous)
        visiting.remove(alias); done.add(alias); order.append(by_alias[alias])
    for alias in by_alias:
        visit(alias)
    return {"projects": index["projects"], "tasks": order, "declarations": index}


def _immutable(path: Path, raw: bytes):
    _assert_no_reparse(path, code="NATIVE_PACK_PATH_UNSAFE")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if not path.is_file() or path.read_bytes() != raw:
            raise ContractError("NATIVE_PACK_IMMUTABLE_CHANGED", "existing declaration or materialization differs")
        return
    attempts = path.parent / ".native-write-attempts"
    _assert_no_reparse(attempts, code="NATIVE_PACK_PATH_UNSAFE")
    attempts.mkdir(exist_ok=True)
    # A failed write is never published under the authoritative filename.
    with tempfile.NamedTemporaryFile(mode="wb", dir=attempts, delete=False, prefix="write-") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        pending = Path(stream.name)
    if pending.read_bytes() != raw:
        raise ContractError("NATIVE_PACK_WRITE_INCOMPLETE", "staged immutable bytes differ")
    _assert_no_reparse(path, code="NATIVE_PACK_PATH_UNSAFE")
    # Atomic exclusive creation: unlike replace/rename on POSIX, no existing
    # final file can be overwritten. Attempts remain available for diagnosis.
    try:
        os.link(pending, path)
    except FileExistsError:
        _assert_no_reparse(path, code="NATIVE_PACK_PATH_UNSAFE")
        if not path.is_file() or path.read_bytes() != raw:
            raise ContractError("NATIVE_PACK_IMMUTABLE_CHANGED", "existing declaration or materialization differs")


def import_native(pack: dict, input_file, *, data_home, local_source=None, offline=False) -> dict:
    try:
        from . import cnw_pack_app as app
    except ImportError:
        import cnw_pack_app as app
    raw_archive = Path(input_file).read_bytes()
    if _sha(raw_archive) != pack["pack_sha256"]:
        raise ContractError("INPUT_PACK_CHANGED", "package changed after validation")
    home = app._home(data_home)
    if shutil.disk_usage(home).free < len(raw_archive) * (len(pack["projects"]) + 2) + 16 * 1024 * 1024:
        raise ContractError("DATA_HOME_CAPACITY_INSUFFICIENT", "insufficient capacity for isolated materials")
    source_bytes = {}
    for group in pack["projects"]:
        for source in group.get("sources", []):
            if "file" in source:
                source_bytes[(group["alias"], source["alias"])] = pack["files"][source["file"]]
            else:
                repo = app.source_repository(home, source["authority"], local=local_source, offline=offline)
                source_bytes[(group["alias"], source["alias"])] = _source_bytes(repo, source["authority"])
    job_id = str(uuid.uuid4())
    job = _ensure_private_directory(home / "shared/input_pack_jobs" / job_id, root=home, code="INPUT_PACK_JOB_UNSAFE")
    _immutable(job / "input.zip", raw_archive)
    report = {"schema_version": JOB_SCHEMA, "job_id": job_id, "pack_sha256": pack["pack_sha256"],
              "job_record": str(job / "result.json"), "status": "IMPORTING", "projects": {}, "tasks": [],
              "provider_call": "none", "production_status": "NOT_AUTHORIZED"}
    def save():
        if (job / "result.json").exists():
            app._save_job_progress(job / "result.json", (job / "result.json").read_bytes(), report)
        else:
            _immutable(job / "result.json", _bytes(report))
    save()
    try:
        for group in pack["projects"]:
            registered = create_project(project_id=group["project_id"], data_home=home)
            root = Path(registered["project_root"])
            prefix = group["materials"] + "/"
            selected_files = {"PACK_MANIFEST.json": pack["files"]["PACK_MANIFEST.json"], "workpack_index.json": pack["files"]["workpack_index.json"]}
            selected_files.update({n: raw for n, raw in pack["files"].items() if n.startswith(prefix)})
            group_tasks = [t for t in pack["tasks"] if t["project"] == group["alias"]]
            for task in group_tasks:
                selected_files[task["requirements"]] = pack["files"][task["requirements"]]
                if task.get("context"):
                    selected_files[task["context"]] = pack["files"][task["context"]]
            for source in group.get("sources", []):
                if "file" in source:
                    selected_files[source["file"]] = pack["files"][source["file"]]
            frozen = f"_INBOX/input_packs/{pack['pack_sha256']}"
            file_hashes = {}
            aliases = {}
            with project_write_lock(root):
                for name, raw in selected_files.items():
                    _immutable(root / frozen / name, raw)
                    file_hashes[f"{frozen}/{name}"] = _sha(raw)
                for name, raw in selected_files.items():
                    if name.startswith(prefix):
                        _immutable(root / name[len(prefix):], raw)
                projects._initialize_project_root(root, registered["project_id"], new_project=True)
                for source in group.get("sources", []):
                    staged = job / "source_staging" / group["alias"] / (source["alias"] + "." + source["format"])
                    _immutable(staged, source_bytes[(group["alias"], source["alias"])])
                    aliases[source["alias"]] = projects._import_source_unlocked(input_file=staged, project_root=root)
            info = {**registered, "alias": group["alias"], "declaration": group, "files": file_hashes, "sources": aliases}
            report["projects"][group["alias"]] = info
            save()
        for task in pack["tasks"]:
            group = report["projects"][task["project"]]
            req = _json(pack["files"][task["requirements"]])
            report["tasks"].append({"task_alias": task["alias"], "project_alias": task["project"], "declaration": task,
                "declaration_sha256": _sha(_bytes(task)), "requirements_sha256": _sha(pack["files"][task["requirements"]]),
                **{k: group[k] for k in ("project_id", "project_instance_id", "project_root")},
                "unit_id": _unit_id(task["alias"]),
                "planned_run_id": f"PACK-{pack['pack_sha256'][:12]}-{task['index_ordinal']:02d}",
                "requested_max_visible_chars": req["max_visible_chars"],
                "status": "WAITING_PREDECESSOR" if task.get("previous_task") else "TASK_DECLARED"})
        origin = {"schema_version": "cnw_native_job_origin_v1", "job_id": job_id, "pack_sha256": pack["pack_sha256"],
                  "projects": report["projects"], "tasks": copy.deepcopy(report["tasks"])}
        _immutable(job / "origin.json", _bytes(origin)); report["origin_sha256"] = _sha(_bytes(origin))
        report["status"] = "NATIVE_TASKS_DECLARED"; save()
    except Exception as exc:
        report.update(status="IMPORT_INCOMPLETE", blocking_code=getattr(exc, "code", "INPUT_PACK_PREPARATION_FAILED"), error_type=type(exc).__name__)
        save()
        return report
    # The declaration is sealed. Later publication failures belong to task
    # preparation and must leave this same job resumable.
    return prepare_native_runs(job / "result.json", data_home=home)


def load_job(job_record, *, data_home):
    try:
        from .cnw_input_pack import read_input_pack
    except ImportError:
        from cnw_input_pack import read_input_pack
    if not data_home or not Path(data_home).is_absolute():
        raise ContractError("DATA_HOME_REQUIRED", "select an explicit absolute DataHome")
    home = Path(data_home).absolute()
    record = Path(job_record).absolute()
    for path in (home, record):
        _assert_no_reparse(path, code="INPUT_PACK_JOB_UNSAFE")
    home, record = home.resolve(strict=True), record.resolve(strict=True)
    if record.name != "result.json" or record.parent.parent != home / "shared/input_pack_jobs":
        raise ContractError("INPUT_PACK_JOB_UNSAFE", "job must belong to the explicit DataHome")
    raw = record.read_bytes(); report = _json(raw)
    if report.get("schema_version") != JOB_SCHEMA or report.get("job_id") != record.parent.name or report.get("status") == "IMPORT_INCOMPLETE":
        raise ContractError("INPUT_PACK_JOB_NOT_READY", "native declarations are incomplete")
    origin_raw = _safe_source_file(record.parent, "origin.json").read_bytes()
    origin = _json(origin_raw)
    archive = _safe_source_file(record.parent, "input.zip")
    pack = read_input_pack(archive)
    if (_sha(origin_raw) != report.get("origin_sha256") or pack["pack_sha256"] != report.get("pack_sha256")
            or origin.get("pack_sha256") != pack["pack_sha256"] or origin.get("job_id") != report["job_id"]
            or _bytes(report.get("projects")) != _bytes(origin.get("projects"))
            or len(report.get("tasks", [])) != len(origin.get("tasks", []))):
        raise ContractError("INPUT_PACK_JOB_BINDINGS_CHANGED", "native job no longer selects its original archive and projects")
    declared_groups = {g["alias"]: g for g in pack["projects"]}
    for alias, group in report["projects"].items():
        registered = resolve_project(group["project_root"], data_home=home)
        if (registered["project_instance_id"] != group["project_instance_id"] or registered["project_id"] != group["project_id"]
                or _bytes(group["declaration"]) != _bytes(declared_groups.get(alias))):
            raise ContractError("INPUT_PACK_JOB_BINDINGS_CHANGED", "native project declaration or registered instance differs")
        for name, digest in group["files"].items():
            if _sha(_safe_source_file(Path(group["project_root"]), name).read_bytes()) != digest:
                raise ContractError("INPUT_PACK_MATERIAL_CHANGED", "native archived material changed")
    for row, initial, declared in zip(report["tasks"], origin["tasks"], pack["tasks"]):
        if (_bytes({k: row.get(k) for k in initial if k != "status"}) != _bytes({k:v for k,v in initial.items() if k != "status"})
                or _bytes(row["declaration"]) != _bytes(declared)
                or row["requirements_sha256"] != _sha(pack["files"][declared["requirements"]])):
            raise ContractError("INPUT_PACK_JOB_BINDINGS_CHANGED", "native task declaration or instance routing changed")
    return record, raw, report


def _task_index(root: Path, report: dict, row: dict, *, previous=None) -> dict:
    group = report["projects"][row["project_alias"]]
    declaration = row["declaration"]
    snapshot = f"_INBOX/input_packs/{report['pack_sha256']}"
    return {"schema_version": ATTEMPT_BINDING_SCHEMA if report.get("execution_attempt") else BINDING_SCHEMA,
            **({"execution_attempt": report["execution_attempt"]} if report.get("execution_attempt") else {}),
            "pack_sha256": report["pack_sha256"],
            **{k: row[k] for k in ("project_id", "project_instance_id", "unit_id", "task_alias")},
            "scene_root": f"tasks/{row['task_alias']}", "files": copy.deepcopy(group["files"]),
            "original_work_order": f"{snapshot}/{declaration['requirements']}",
            "native_context_file": f"{snapshot}/{declaration['context']}" if declaration.get("context") else None,
            "native_declaration": declaration, "native_group": group["declaration"],
            "native_index_file": f"{snapshot}/workpack_index.json",
            "adapter_choices": {"fifth_lens": group["declaration"]["fifth_lens"], "integrations": {"nk": "DISABLED", "critics": "DISABLED"}},
            "source_aliases": group["sources"], "previous_binding": previous}


def binding_prefix(index: dict) -> str:
    prefix = f"_INBOX/input_packs/{index['pack_sha256']}"
    if index.get("schema_version") == ATTEMPT_BINDING_SCHEMA:
        metadata = index.get("execution_attempt", {})
        if (set(metadata) != {"job_id", "attempt_id", "declaration_sha256"}
                or any(str(uuid.UUID(metadata[k])) != metadata[k] for k in ("job_id", "attempt_id"))):
            raise ContractError("INPUT_PACK_ATTEMPT_BINDING_INVALID", "invalid native attempt namespace")
        prefix += f"/attempts/{metadata['attempt_id']}"
    return prefix + f"/tasks/{_alias(index['task_alias'])}"


def contract_relative(index: dict) -> str:
    if index.get("schema_version") == ATTEMPT_BINDING_SCHEMA:
        return f"contracts/input_pack_attempts/{index['execution_attempt']['attempt_id']}/{_unit_id(index['task_alias'])}.json"
    return f"contracts/{index['unit_id']}.json"


def _draft(root: Path, index: dict) -> dict:
    req = _json(_safe_source_file(root, index["original_work_order"]).read_bytes())
    task = index["native_declaration"]
    result = {**req, "schema_version": "cnw_work_unit_draft_v2", "unit_id": index["unit_id"],
              "work_intent": task["work_intent"], "review": {"fifth_lens": index["adapter_choices"]["fifth_lens"]},
              "integrations": index["adapter_choices"]["integrations"]}
    if task["work_intent"] == "ORIGINAL_EPISODE":
        result["first_episode"] = task["first_episode"]
        if not task["first_episode"]:
            if not index.get("previous_binding"):
                raise ContractError("NATIVE_PACK_PREDECESSOR_NOT_READY", "continuation waits for actual prior output")
            result["previous_episode_ref"] = index["previous_binding"]["path"]
    else:
        source = index["source_aliases"][task["source"]]
        allowed = {"before_line", "before_line_end", "after_line", "after_line_end", "before_scene", "after_scene"} if task["work_intent"] == "INSERT_BETWEEN" else {"start_line", "end_line", "json_pointer"}
        if set(task["selection"]) - allowed:
            raise ContractError("SOURCE_SELECTION_INVALID", "selection cannot supply identities or another intent's anchors")
        result.update(task["selection"], source_id=source["source_id"], source_revision_id=source["source_revision_id"],
                      source_manifest_revision_sha256=source["source_manifest_sha256"], source_index_revision_sha256=source["source_index_sha256"])
    return result


def validate_draft(root: Path, index: dict, draft: dict) -> None:
    expected = _draft(root, index)
    if _bytes({k: draft.get(k) for k in expected}) != _bytes(expected):
        raise ContractError("INPUT_PACK_REQUIREMENT_MISMATCH", "native draft changes declared requirements or selected sources")


def validate_binding(root: Path, binding: dict, *, contract=None) -> dict:
    pack_sha, alias = binding.get("pack_sha256"), binding.get("task_alias")
    if not isinstance(pack_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", pack_sha):
        raise ContractError("INPUT_PACK_BINDING_INVALID", "native input pack hash is invalid")
    _alias(alias)
    if binding.get("schema_version") not in BINDING_SCHEMAS:
        raise ContractError("INPUT_PACK_BINDING_INVALID", "invalid native binding schema")
    expected_file = binding_prefix(binding) + "/binding.json"
    if binding.get("index_file") != expected_file:
        raise ContractError("INPUT_PACK_BINDING_INVALID", "native task must select its own binding file")
    raw = _safe_source_file(root, expected_file).read_bytes()
    index = _json(raw)
    identity = projects._registered_project_identity(root)
    if (_sha(raw) != binding.get("index_sha256") or index.get("schema_version") != binding["schema_version"]
            or index.get("task_alias") != alias or index.get("pack_sha256") != pack_sha
            or any(index.get(k) != identity[k] for k in ("project_id", "project_instance_id"))):
        raise ContractError("INPUT_PACK_BINDING_HASH_MISMATCH", "native task binding or instance changed")
    if index["schema_version"] == ATTEMPT_BINDING_SCHEMA:
        try:
            from .cnw_pack_app import validate_attempt_metadata
        except ImportError:
            from cnw_pack_app import validate_attempt_metadata
        if binding.get("execution_attempt") != index.get("execution_attempt"):
            raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "native contract selects another attempt")
        checked = validate_attempt_metadata(root, index["execution_attempt"], task_key=alias)
        if index["unit_id"] != checked["row"]["unit_id"]:
            raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "native unit differs from original declaration")
        group = checked["projects"][checked["source_task"]["project_alias"]]
        derived_file = binding_prefix(index) + "/derived/task_requirements.v1.json"
        if (index.get("source_aliases") != group["sources"]
                or index.get("native_group") != group["declaration"]
                or index.get("native_declaration") != checked["source_task"]["declaration"]
                or set(index["files"]) != set(group["files"]) | {derived_file}
                or any(index["files"].get(name) != digest for name, digest in group["files"].items())):
            raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "native source mapping or original material set changed")
    for name, digest in index["files"].items():
        if _sha(_safe_source_file(root, name).read_bytes()) != digest:
            raise ContractError("INPUT_PACK_MATERIAL_CHANGED", "frozen native material differs")
    original = _json(_safe_source_file(root, index["native_index_file"]).read_bytes())
    task = next((t for t in original["tasks"] if t.get("alias") == alias), None)
    declared = {**task, "index_ordinal": original["tasks"].index(task) + 1} if task else None
    group = next((g for g in original["projects"] if g.get("alias") == index["native_declaration"]["project"]), None)
    if _bytes(declared) != _bytes(index["native_declaration"]) or _bytes(group) != _bytes(index["native_group"]):
        raise ContractError("INPUT_PACK_REQUIREMENT_MISMATCH", "native binding no longer describes the original declaration")
    tasks.verify_bound_task_context(root, index)
    if contract is not None:
        expected = _draft(root, index)
        unit, story = contract["unit"], contract["story"]
        def equal(a, b):
            if _bytes(a) != _bytes(b):
                raise ContractError("INPUT_PACK_REQUIREMENT_MISMATCH", "native contract no longer represents its original task")
        equal(contract["work_intent"], expected["work_intent"])
        for field in ("kind", "language_locale", "pov", "target_visible_chars", "min_visible_chars", "max_visible_chars"):
            value = expected[field]; equal(unit[field], value.strip() if isinstance(value, str) else value)
        equal(unit["id"], expected["unit_id"])
        for field in ("chapter_context", "role_in_story", "reader_reward", "entry_state", "exit_state", "required_beats",
                      "characters_in_scene", "character_knowledge_boundary_ref", "forbidden_future_revelations", "voice_sample_refs", "arc_ref"):
            value = expected.get(field, [] if field == "required_beats" else None)
            equal(story.get(field), value.strip() if isinstance(value, str) else value)
        equal(contract["integrations"], expected["integrations"])
        for field in ("id", "responsibility"):
            equal(contract["review"]["fifth_lens"][field], expected["review"]["fifth_lens"][field].strip())
        if expected["work_intent"] == "ORIGINAL_EPISODE":
            equal(story["first_episode"], expected["first_episode"])
            if not expected["first_episode"]:
                equal(story["previous_episode_ref"], expected["previous_episode_ref"])
                equal(story["previous_episode_sha256"], index["previous_binding"]["sha256"])
                validate_previous(root, index["previous_binding"], attempt=index.get("execution_attempt"),
                                  expected_task=index["native_declaration"].get("previous_task"))
        else:
            equal(contract["source"]["source_id"], expected["source_id"])
            equal(contract["source"]["source_revision_id"], expected["source_revision_id"])
            equal(contract["source"]["source_manifest_sha256"], expected["source_manifest_revision_sha256"])
            equal(contract["source"]["source_index_sha256"], expected["source_index_revision_sha256"])
            if expected["work_intent"] == "ADAPT_SOURCE":
                for field in ("start_line", "end_line", "json_pointer"):
                    if field in expected:
                        equal(story["source_selection"].get(field), expected[field])
            else:
                for kind in ("before", "after"):
                    equal(story[kind + "_anchor"]["source_line"], expected[kind + "_line"])
                    equal(story[kind + "_anchor"]["source_line_end"], expected.get(kind + "_line_end", expected[kind + "_line"]))
    return index


def validate_previous(root: Path, previous: dict, *, attempt=None, expected_task=None) -> None:
    try:
        from . import cnw_runner as runner, cnw_recovery as recovery
    except ImportError:
        import cnw_runner as runner, cnw_recovery as recovery
    live = attempt is not None
    if live:
        if previous.get("status") != "LIVE_VALIDATED_CARRY_FORWARD" or previous.get("execution_attempt") != attempt:
            raise ContractError("NATIVE_PACK_SIMULATED_PREDECESSOR_FORBIDDEN", "production requires this attempt's actual Live predecessor")
        try:
            from .cnw_pack_app import validate_attempt_metadata
        except ImportError:
            from cnw_pack_app import validate_attempt_metadata
        planned = validate_attempt_metadata(root, attempt, task_key=expected_task)["row"]
        if previous.get("task_alias") != expected_task or previous.get("run_id") != planned["planned_run_id"]:
            raise ContractError("NATIVE_PACK_PREDECESSOR_INVALID", "predecessor belongs to another task or attempt")
    run = root / "runs" / previous["run_id"]
    _assert_no_reparse(run, code="NATIVE_PACK_PREDECESSOR_INVALID")
    state = runner.load_state(run)
    recovery.verify_contract(run, state); recovery.verify_evidence(run, state)
    identity = projects._registered_project_identity(root)
    if (previous.get("status") != ("LIVE_VALIDATED_CARRY_FORWARD" if live else "SIMULATED_CARRY_FORWARD") or previous.get("promoted") is not False
            or previous["project_instance_id"] != identity["project_instance_id"] or state["mode"] != ("live" if live else "offline")
            or any(s["status"] not in runner._MATERIALIZED for s in state["stages"].values())):
        raise ContractError("NATIVE_PACK_PREDECESSOR_INVALID", "predecessor is not this instance's completed candidate in the selected mode")
    if live:
        runner.verify_live(SimpleNamespace(project_root=str(root), run_id=run.name))
    review = json.loads(runner._read_stage_text(run, state, "re_review"))
    body = _safe_source_file(root, previous["path"]).read_bytes()
    candidate = runner._read_stage_text(run, state, "refine").encode("utf-8")
    if (review.get("status") not in {"CLEAN", "NO_CHANGED_TEXT"} or body != candidate or _sha(body) != previous["sha256"]
            or state["contract_sha256"] != previous["contract_sha256"]
            or state["stages"]["refine"]["artifact"] != previous["source_artifact"]
            or state["stages"]["re_review"]["artifact"]["sha256"] != previous["review_sha256"]
            or not state.get("provider_requests")
            or (not live and any(r.get("mode") != "MOCK_ONLY" or r.get("simulation_status") != "SIMULATED" or r.get("fixture_only") is not True for r in state["provider_requests"]))):
        raise ContractError("NATIVE_PACK_PREDECESSOR_INVALID", "predecessor body, review or receipts differ")
    if _json(_safe_source_file(root, previous["record"]).read_bytes()) != previous:
        raise ContractError("NATIVE_PACK_PREDECESSOR_INVALID", "carry-forward record changed")


def _previous_binding(root: Path, report: dict, row: dict) -> dict | None:
    task = row["declaration"]
    if not task.get("previous_task"):
        return None
    preceding = next(r for r in report["tasks"] if r["task_alias"] == task["previous_task"])
    attempt = report.get("execution_attempt")
    if preceding.get("status") != ("LIVE_STORY_EXPORTED" if attempt else "MOCK_STORY_EXPORTED"):
        return None
    if attempt and preceding.get("execution_attempt") != attempt:
        raise ContractError("NATIVE_PACK_PREDECESSOR_INVALID", "predecessor belongs to another attempt")
    try:
        from . import cnw_runner as runner, cnw_recovery as recovery
    except ImportError:
        import cnw_runner as runner, cnw_recovery as recovery
    run = root / "runs" / preceding["planned_run_id"]
    state = runner.load_state(run)
    recovery.verify_contract(run, state); recovery.verify_evidence(run, state)
    review = json.loads(runner._read_stage_text(run, state, "re_review"))
    if review.get("status") not in {"CLEAN", "NO_CHANGED_TEXT"}:
        return None
    if attempt:
        runner.verify_live(SimpleNamespace(project_root=str(root), run_id=run.name))
    relative = f"94_runtime/cnw_candidate_carry_forward/{report['job_id']}/{preceding['task_alias']}"
    if attempt:
        relative = f"94_runtime/cnw_candidate_carry_forward/{report['job_id']}/{attempt['attempt_id']}/{preceding['task_alias']}"
    body = runner._read_stage_text(run, state, "refine").encode("utf-8")
    previous = {"status": "LIVE_VALIDATED_CARRY_FORWARD" if attempt else "SIMULATED_CARRY_FORWARD", "promoted": False,
                **({"execution_attempt": attempt} if attempt else {}), "job_id": report["job_id"],
                "project_instance_id": row["project_instance_id"], "task_alias": preceding["task_alias"],
                "run_id": preceding["planned_run_id"], "contract_sha256": state["contract_sha256"],
                "source_stage": "refine", "source_artifact": state["stages"]["refine"]["artifact"],
                "review_sha256": state["stages"]["re_review"]["artifact"]["sha256"],
                "path": relative + ".md", "record": relative + ".json", "sha256": _sha(body)}
    _immutable(root / previous["path"], body); _immutable(root / previous["record"], _bytes(previous))
    validate_previous(root, previous, attempt=attempt, expected_task=task["previous_task"])
    return previous


def materialize_task(report: dict, row: dict, job: Path, *, data_home) -> bool:
    """Append one actual contract; never edit original task/project declarations."""
    root = Path(resolve_project(row["project_root"], data_home=data_home)["project_root"])
    layout = _task_index(root, report, row)
    expected_contract = root / contract_relative(layout)
    record = job / "materializations" / (row["task_alias"] + ".json")
    with project_write_lock(root):
        if record.exists():
            material = _json(_safe_source_file(job, record.relative_to(job).as_posix()).read_bytes())
            contract_path = expected_contract
            if (material.get("task_declaration_sha256") != row["declaration_sha256"]
                    or material.get("project_instance_id") != row["project_instance_id"]
                    or material.get("contract") != str(contract_path) or _sha(_safe_source_file(root, contract_path.relative_to(root).as_posix()).read_bytes()) != material.get("contract_sha256")):
                raise ContractError("INPUT_PACK_JOB_BINDINGS_CHANGED", "native materialized contract changed")
            contract = _json(contract_path.read_bytes())
            validate_binding(root, contract["input_pack"], contract=contract)
            validate_v2_source_identity(contract, source_root=root)
        else:
            previous = _previous_binding(root, report, row)
            if row["declaration"].get("previous_task") and previous is None:
                row["status"] = "WAITING_PREDECESSOR"
                return False
            index = _task_index(root, report, row, previous=previous)
            descriptor = binding_prefix(index)
            derived_file = descriptor + "/derived/task_requirements.v1.json"
            context = tasks.derive_native_task_context(sources=tasks.frozen_task_sources(root, index),
                identity={k: row[k] for k in ("project_id", "project_instance_id")}, index=index)
            derived = tasks.encode(context); _immutable(root / derived_file, derived)
            index["files"][derived_file] = _sha(derived)
            index["task_context"] = {"schema_version": tasks.SCHEMA, "recipe_version": tasks.NATIVE_RECIPE,
                                     "file": derived_file, "sha256": _sha(derived)}
            binding_file = descriptor + "/binding.json"
            index_raw = _bytes(index); _immutable(root / binding_file, index_raw)
            draft = _draft(root, index)
            draft["input_pack"] = {"schema_version": index["schema_version"],
                **({"execution_attempt": report["execution_attempt"]} if report.get("execution_attempt") else {}),
                "pack_sha256": report["pack_sha256"],
                "task_alias": row["task_alias"], "index_file": binding_file, "index_sha256": _sha(index_raw)}
            draft_path = expected_contract.with_suffix(".draft.json")
            _immutable(draft_path, _bytes(draft))
            contract_path = expected_contract
            if not contract_path.exists():
                try:
                    projects.write_contract_draft(root, draft_path)
                except ContractError as exc:
                    if exc.code != "UNIT_CAPACITY_UNVALIDATED":
                        raise
                    row.update(status="CAPACITY_PENDING", draft=str(draft_path), blocking_code=exc.code)
                    return False
            contract = _json(_safe_source_file(root, contract_path.relative_to(root).as_posix()).read_bytes())
            validate_binding(root, contract["input_pack"], contract=contract)
            validate_v2_source_identity(contract, source_root=root)
            material = {"schema_version": "cnw_native_task_materialization_v1", "task_declaration_sha256": row["declaration_sha256"],
                        "project_instance_id": row["project_instance_id"], "contract": str(contract_path),
                        "contract_sha256": _sha(contract_path.read_bytes()), "draft": str(draft_path),
                        "binding": draft["input_pack"], "previous_binding": previous}
            _immutable(record, _bytes(material))
        for key in ("contract", "contract_sha256", "draft"):
            if row.get(key) is not None and row[key] != material[key]:
                raise ContractError("INPUT_PACK_JOB_BINDINGS_CHANGED", "task contract routing changed")
            row[key] = material[key]
        row["materialization"] = {"record": str(record), "sha256": _sha(record.read_bytes())}
        if not row.get("execution"):
            row["status"] = "CONTRACT_READY_FOR_PREFLIGHT"
        return True


def prepare_native_task(report: dict, row: dict, job: Path, *, data_home) -> bool:
    if not materialize_task(report, row, job, data_home=data_home):
        return False
    try:
        from . import cnw_runner as runner
    except ImportError:
        import cnw_runner as runner
    root = Path(row["project_root"])
    run = root / "runs" / row["planned_run_id"]
    with project_write_lock(root):
        _assert_no_reparse(run, code="INPUT_PACK_RUN_UNSAFE")
        contract = _json(_safe_source_file(root, str(Path(row["contract"]).relative_to(root))).read_bytes())
        if not run.exists():
            projects.build_contract_preflight(root, row["contract"], run_id=row["planned_run_id"])
            runner.produce(SimpleNamespace(mode="live" if report.get("execution_attempt") else "offline", unit=contract["unit"]["kind"], work_id=row["unit_id"],
                contract=row["contract"], project_root=str(root), run_id=row["planned_run_id"], create_only=True))
        if report.get("execution_attempt"):
            try:
                from .cnw_pack_app import _job_run
            except ImportError:
                from cnw_pack_app import _job_run
            _job_run(run, "live")
        bindings = projects.build_run_contract_preflight(root, row["contract"], run_id=row["planned_run_id"])
        recorded = job / "run_bindings" / (row["task_alias"] + ".json")
        if recorded.exists():
            old = _json(_safe_source_file(job, recorded.relative_to(job).as_posix()).read_bytes())
            if _bytes(old["bindings"]) != _bytes(bindings["bindings"]):
                raise ContractError("INPUT_PACK_RUN_BINDINGS_CHANGED", "native Run inputs differ from their first preparation")
        else:
            _immutable(recorded, _bytes(bindings))
        row["run_preparation"] = {"status": "LIVE_BINDINGS_VALIDATED" if report.get("execution_attempt") else "OFFLINE_BINDINGS_VALIDATED", "run_id": row["planned_run_id"], "run_path": str(run),
            "identity_sha256": bindings["identity_sha256"], "record": str(recorded), "record_sha256": _sha(recorded.read_bytes()),
            "provider_call_authorized": False, "controller_attestation_status": "ATTESTATION_PENDING", "live_authorization_status": "NOT_AUTHORIZED"}
        if not row.get("execution"):
            row["status"] = "RUN_PREPARED_PENDING_AUTHORIZATION"
        if "preparation" in row:
            row["preparation"]["status"] = "PREPARED"
            row["preparation"].pop("blocking_code", None)
            row["preparation"].pop("interrupted_stage", None)
        return True


def record_preparation_failure(report: dict, row: dict, exc: Exception) -> None:
    """Record an actual preparation failure after the caller validates the job."""
    code = getattr(exc, "code", "INPUT_PACK_TASK_PREPARATION_INTERRUPTED")
    preparation = row.setdefault("preparation", {})
    preparation.update(status="PREPARATION_INCOMPLETE", blocking_code=code, interrupted_stage="task_preparation")
    preparation.setdefault("interruptions", []).append({"stage": "task_preparation", "blocking_code": code,
        "error_type": type(exc).__name__, "detail": str(exc)[:2048]})
    row["status"] = "TASK_PREPARATION_INCOMPLETE"
    report.update(status="JOB_PREPARATION_INCOMPLETE", blocking_code=code, interrupted_task=row["task_alias"],
                  production_status="NOT_AUTHORIZED")


def prepare_native_runs(job_record, *, data_home) -> dict:
    try:
        from . import cnw_pack_app as app
    except ImportError:
        import cnw_pack_app as app
    record, _, _ = load_job(job_record, data_home=data_home)
    with project_write_lock(record.parent):
        record, raw, report = load_job(record, data_home=data_home)
        recovering_preparation = report["status"] == "JOB_PREPARATION_INCOMPLETE"
        for row in report["tasks"]:
            try:
                prepare_native_task(report, row, record.parent, data_home=data_home)
            except Exception as exc:
                record_preparation_failure(report, row, exc)
                app._save_job_progress(record, raw, report)
                return report
            raw = app._save_job_progress(record, raw, report)
        if not any(row.get("execution") for row in report["tasks"]):
            report["status"] = "RUNS_PREPARED_WITH_PENDING_TASKS" if any(r["status"] in {"WAITING_PREDECESSOR", "CAPACITY_PENDING"} for r in report["tasks"]) else "RUNS_PREPARED_PENDING_AUTHORIZATION"
        elif report["status"] == "JOB_PREPARATION_INCOMPLETE":
            report["status"] = "JOB_READY_TO_RESUME"
        if recovering_preparation:
            report.pop("blocking_code", None)
            report.pop("interrupted_task", None)
        app._save_job_progress(record, raw, report)
        return report
