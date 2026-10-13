"""Formal package entry: declared inputs to isolated projects and contracts."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    from .cnw_contract import ContractError, _safe_source_file
    from .cnw_input_pack import read_input_pack, prepare_scene_input, _json, _sha, _bytes, _source_bytes, _scene_anchor
    from .cnw_project import write_contract_draft, build_contract_preflight, build_run_contract_preflight
    from .project_paths import (_prepare_data_home, _ensure_private_directory, _data_home_identity,
                                _assert_no_reparse, create_project, resolve_project, PathResolutionError, DATA_HOME_SCHEMA)
    from .project_transactions import project_write_lock
except ImportError:
    from cnw_contract import ContractError, _safe_source_file
    from cnw_input_pack import read_input_pack, prepare_scene_input, _json, _sha, _bytes, _source_bytes, _scene_anchor
    from cnw_project import write_contract_draft, build_contract_preflight, build_run_contract_preflight
    from project_paths import (_prepare_data_home, _ensure_private_directory, _data_home_identity,
                               _assert_no_reparse, create_project, resolve_project, PathResolutionError, DATA_HOME_SCHEMA)
    from project_transactions import project_write_lock


def _home(path: str | Path) -> Path:
    home = _prepare_data_home(path)
    marker = home / "shared/data_home_identity.json"
    if marker.exists():
        _assert_no_reparse(marker, code="DATA_HOME_REPARSE_POINT")
        value = _json(marker.read_bytes())
        if not isinstance(value, dict) or value.get("schema_version") != DATA_HOME_SCHEMA:
            raise ContractError("DATA_HOME_IDENTITY_INVALID", "selected root is not a registered StoryStudio DataHome")
        try:
            uuid.UUID(value["data_home_id"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ContractError("DATA_HOME_IDENTITY_INVALID", "DataHome identity is invalid") from exc
        _data_home_identity(home, create=False)
    elif any(home.iterdir()):
        raise ContractError("DATA_HOME_OCCUPIED", "nonempty unregistered directory cannot be adopted")
    else:
        _ensure_private_directory(home / "shared", root=home, code="DATA_HOME_REPARSE_POINT")
        _data_home_identity(home, create=True)
    return home


def derive_fifth_lens(pack: dict, scene: str) -> dict:
    """Read explicit seed duties, preserving their exact source and locator."""
    prefix = scene + "/project_seed/"
    candidates = []
    for name in ("config/project_policy.v1.json", "config/policies/project_policy.v1.json"):
        raw = pack["files"].get(prefix + name)
        if raw is None:
            continue
        document = _json(raw)
        if not isinstance(document, dict) or document.get("schema_version") != "storystudio_project_policy_v1":
            raise ContractError("INPUT_PACK_LENS_DUTIES_INVALID", "explicit project policy has an unsupported schema")
        lens = document.get("review", {}).get("fifth_lens", {}) if isinstance(document, dict) else {}
        if not all(isinstance(lens.get(key), str) and lens[key].strip() for key in ("id", "responsibility")):
            raise ContractError("INPUT_PACK_LENS_DUTIES_INVALID", "explicit project fifth Lens configuration is incomplete")
        candidates.append({"id": lens["id"].strip(), "responsibility": lens["responsibility"].strip(),
                           "derivation": {"source_file": name, "source_sha256": _sha(raw),
                                          "locator": {"json_pointer": "/review/fifth_lens/responsibility"},
                                          "original_text": lens["responsibility"],
                                          "derived_responsibility": lens["responsibility"].strip()}})
    if candidates:
        if len({(v["id"], v["responsibility"]) for v in candidates}) != 1:
            raise ContractError("INPUT_PACK_LENS_DUTIES_CONFLICT", "explicit project configurations disagree")
        return candidates[0]
    name = "00_meta/OUTPUT_REQUIREMENTS.md"
    raw = pack["files"].get(prefix + name, b"")
    try:
        lines = raw.decode("utf-8-sig").splitlines()
    except UnicodeError as exc:
        raise ContractError("INPUT_PACK_LENS_DUTIES_INVALID", "review duties must be UTF-8") from exc
    for number, line in enumerate(lines, 1):
        cells = [value.strip() for value in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0].casefold() in {"story-specific lens", "story_specific lens", "第五 lens"} and cells[2]:
            candidates.append({"id": "pack-story-specific", "responsibility": cells[2],
                               "derivation": {"source_file": name, "source_sha256": _sha(raw),
                                              "locator": {"line": number}, "original_text": line,
                                              "derived_responsibility": cells[2]}})
    if len(candidates) != 1:
        raise ContractError("INPUT_PACK_LENS_DUTIES_MISSING_OR_AMBIGUOUS", "one explicit story-specific responsibility is required")
    return candidates[0]


def _git(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    return subprocess.run(["git", "--no-pager", "-c", "core.hooksPath=" + str(cwd / "disabled_hooks"),
                           "-c", "protocol.file.allow=never", "-C", str(cwd), *args],
                          env=env, capture_output=True, timeout=60)


def source_repository(home: Path, authority: dict, *, local: str | Path | None, offline: bool) -> Path:
    if local is not None:
        repo = Path(local).resolve(strict=True)
        try:
            _source_bytes(repo, authority)
        except ContractError as exc:
            if offline and exc.code == "PINNED_SOURCE_UNAVAILABLE":
                raise ContractError("SOURCE_OBJECT_MISSING_OFFLINE", "selected local repository lacks the exact object; fetching is disabled") from exc
            raise
        return repo
    repository, commit = authority.get("repo"), authority.get("commit")
    if (not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", repository) or
            not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit)):
        raise ContractError("INPUT_PACK_REPOSITORY_INVALID", "network sources require a declared GitHub owner/repository and exact commit")
    url = f"https://github.com/{repository}.git"
    cache = home / "tool_cache/input_sources" / _sha(_bytes({"url": url, "commit": commit}))
    _assert_no_reparse(cache, code="INPUT_SOURCE_CACHE_UNSAFE")
    marker = cache / "source_cache_identity.json"
    _assert_no_reparse(marker, code="INPUT_SOURCE_CACHE_UNSAFE")
    expected = {"schema_version": "cnw_input_source_cache_v1", "url": url, "commit": commit}
    if not cache.exists() and offline:
        raise ContractError("SOURCE_OBJECT_MISSING_OFFLINE", "declared source is absent; offline mode cannot fetch it")
    if cache.exists() and (not marker.is_file() or _json(marker.read_bytes()) != expected):
        raise ContractError("INPUT_SOURCE_CACHE_IDENTITY_MISMATCH", "existing source cache is unknown or belongs to another identity")
    cache = _ensure_private_directory(cache, root=home, code="INPUT_SOURCE_CACHE_UNSAFE")
    with project_write_lock(cache):
        _assert_no_reparse(marker, code="INPUT_SOURCE_CACHE_UNSAFE")
        if marker.exists() and _json(marker.read_bytes()) != expected:
            raise ContractError("INPUT_SOURCE_CACHE_IDENTITY_MISMATCH", "cache identity changed before its lock was acquired")
        objects = cache / "objects.git"
        if not marker.exists():
            with marker.open("xb") as stream:
                stream.write(_bytes(expected))
            objects.mkdir()
            if _git(["init", "--bare", "--template=", str(objects)], cwd=cache).returncode:
                raise ContractError("INPUT_SOURCE_CACHE_INCOMPLETE", "source cache initialization failed; existing progress was retained")
        _assert_no_reparse(objects, code="INPUT_SOURCE_CACHE_UNSAFE")
        if not objects.is_dir():
            raise ContractError("INPUT_SOURCE_CACHE_INCOMPLETE", "cached repository is absent; retained cache requires investigation")
        bare = subprocess.run(["git", "-c", "protocol.allow=never", "--git-dir=" + str(objects),
                               "rev-parse", "--is-bare-repository"],
                              env=dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0"), capture_output=True, timeout=30)
        if bare.returncode or bare.stdout.strip() != b"true":
            raise ContractError("INPUT_SOURCE_CACHE_INCOMPLETE", "cache repository is not a valid bare object store")
        try:
            _source_bytes(objects, authority)
        except ContractError as exc:
            if exc.code != "PINNED_SOURCE_UNAVAILABLE":
                raise
            if offline:
                raise ContractError("SOURCE_OBJECT_MISSING_OFFLINE", "exact pinned object is absent; network fallback is disabled") from exc
            attempt_dir = _ensure_private_directory(cache / "fetch_attempts", root=home, code="INPUT_SOURCE_CACHE_UNSAFE")
            attempt_file = attempt_dir / f"{uuid.uuid4()}.json"
            attempt = {"url": url, "commit": commit, "status": "FETCH_STARTED",
                       "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "provider_call": "none"}
            attempt_file.write_bytes(_bytes(attempt))
            try:
                result = _git(["fetch", "--no-tags", "--depth=1", "--no-write-fetch-head", url, commit], cwd=objects)
            except subprocess.TimeoutExpired:
                attempt.update(status="FETCH_TIMED_OUT")
                attempt_file.write_bytes(_bytes(attempt))
                raise
            attempt.update(status="FETCH_SUCCEEDED" if result.returncode == 0 else "FETCH_FAILED", exit_code=result.returncode)
            attempt_file.write_bytes(_bytes(attempt))
            if result.returncode:
                raise ContractError("INPUT_SOURCE_FETCH_FAILED", "could not obtain the declared exact commit; cache progress was retained")
            _source_bytes(objects, authority)
    return objects


def import_package(input_file: str | Path, *, data_home: str | Path,
                   local_source: str | Path | None = None, offline: bool = False) -> dict:
    pack = read_input_pack(input_file)
    if pack.get("format") == "native_v2":
        try:
            from .cnw_native_pack import import_native
        except ImportError:
            from cnw_native_pack import import_native
        return import_native(pack, input_file, data_home=data_home, local_source=local_source, offline=offline)
    archive = Path(input_file).read_bytes()
    if _sha(archive) != pack["pack_sha256"]:
        raise ContractError("INPUT_PACK_CHANGED", "selected package changed during validation")
    tasks = []
    for scene in pack["scenes"]:
        order = _json(pack["files"][scene + "/work_order.draft.json"])
        if not isinstance(order, dict) or not isinstance(order.get("original_authority"), dict):
            raise ContractError("INPUT_PACK_WORK_ORDER_UNSUPPORTED", "task authority is missing")
        if (not isinstance(order.get("project_id"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", order["project_id"]) or
                not isinstance(order.get("unit_id"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,95}", order["unit_id"])):
            raise ContractError("INPUT_PACK_TASK_ID_INVALID", "declared task and display project IDs must be safe components")
        budgets = [order.get(k) for k in ("min_visible_chars", "target_visible_chars", "max_visible_chars")]
        if any(type(value) is not int for value in budgets) or not 1 <= budgets[0] <= budgets[1] <= budgets[2]:
            raise ContractError("SCENE_BUDGET_INVALID", "all original writing bounds must be explicit and ordered")
        tasks.append({"scene_root": scene, "order": order, "fifth_lens": derive_fifth_lens(pack, scene)})
    home = _home(data_home)
    if shutil.disk_usage(home).free < len(archive) * (len(tasks) + 2) + 16 * 1024 * 1024:
        raise ContractError("DATA_HOME_CAPACITY_INSUFFICIENT", "not enough capacity for private archive and isolated input copies")
    for task in tasks:
        repo = source_repository(home, task["order"]["original_authority"], local=local_source, offline=offline)
        raw = _source_bytes(repo, task["order"]["original_authority"])
        before = _scene_anchor(raw, task["order"]["original_authority"].get("before_scene"))
        after = _scene_anchor(raw, task["order"]["original_authority"].get("after_scene"))
        if before["source_line_end"] >= after["source_line"]:
            raise ContractError("SOURCE_ANCHOR_INVALID", "declared scenes overlap or are reversed")
        task["repo"] = repo
        task["source_sha256"] = _sha(raw)
    job_id = str(uuid.uuid4())
    job = _ensure_private_directory(home / "shared/input_pack_jobs" / job_id, root=home, code="INPUT_PACK_JOB_UNSAFE")
    snapshot = job / "input.zip"
    with snapshot.open("xb") as stream:
        stream.write(archive)
    report = {"schema_version": "cnw_input_pack_job_v1", "job_id": job_id, "pack_sha256": pack["pack_sha256"],
              "status": "IMPORTING", "tasks": [], "provider_call": "none", "production_status": "NOT_AUTHORIZED",
              "field_consumption_status": "PENDING_ROLE_CONSUMPTION_VALIDATION", "job_record": str(job / "result.json")}
    def save():
        # Only this newly created job owns this result; never touch prior jobs.
        (job / "result.json").write_bytes(_bytes(report))
    save()
    try:
        for number, task in enumerate(tasks, 1):
            order = task["order"]
            registered = create_project(project_id=order["project_id"], data_home=home)
            row = {**registered, "scene_root": task["scene_root"], "unit_id": order["unit_id"],
                   "status": "REGISTERED", "requested_max_visible_chars": order["max_visible_chars"],
                   "source": {"repository": order["original_authority"].get("repo"),
                              "commit": order["original_authority"]["commit"],
                              "blob_sha1": order["original_authority"]["blob_sha1"], "sha256": task["source_sha256"]}}
            report["tasks"].append(row); save()
            prepared = prepare_scene_input(snapshot, scene_root=task["scene_root"], project_root=registered["project_root"],
                                           source_repo=task["repo"], fifth_lens=task["fifth_lens"], source_staging_root=job / "source_staging")
            row.update(draft=prepared["draft"], fifth_lens_derivation=task["fifth_lens"]["derivation"], status="DRAFT_READY")
            try:
                result = write_contract_draft(registered["project_root"], prepared["draft"])
            except ContractError as exc:
                if exc.code != "UNIT_CAPACITY_UNVALIDATED":
                    raise
                row.update(status="CAPACITY_PENDING", blocking_code=exc.code)
            else:
                row.update(contract=result["contract"], contract_sha256=result["contract_sha256"], status="CONTRACT_READY_FOR_PREFLIGHT")
                row["planned_run_id"] = f"PACK-{pack['pack_sha256'][:12]}-{number:02d}"
                preflight = build_contract_preflight(registered["project_root"], result["contract"], run_id=row["planned_run_id"])
                record = job / f"{registered['project_instance_id']}.preflight.json"
                with record.open("xb") as stream:
                    stream.write(_bytes(preflight))
                row["preflight"] = {"status": "OFFLINE_BINDINGS_VALIDATED",
                                     "provider_call_authorized": False, "record": str(record),
                                     "record_sha256": _sha(_bytes(preflight)),
                                     **{k: preflight[k] for k in ("project_instance_id", "contract_sha256", "evidence_digest")}}
            save()
    except Exception as exc:
        report.update(status="IMPORT_INCOMPLETE", blocking_code=getattr(exc, "code", "INPUT_PACK_PREPARATION_FAILED"), error_type=type(exc).__name__)
        if getattr(exc, "task_conflict", None):
            report["input_conflict"] = exc.task_conflict
            report["action_required"] = "两处写作要求不一致，请选择新输入或明确批准差分；已有材料和进度已保留。"
        if report["tasks"]:
            report["tasks"][-1].update(status="FAILED", blocking_code=report["blocking_code"])
        save()
        return report
    report["status"] = "INPUTS_PREPARED_WITH_CAPACITY_PENDING" if any(t["status"] == "CAPACITY_PENDING" for t in report["tasks"]) else "CONTRACTS_READY_FOR_PREFLIGHT"
    origin = {"schema_version": "cnw_input_pack_job_origin_v1", "job_id": job_id,
              "pack_sha256": report["pack_sha256"], "tasks": [_task_job_identity(row) for row in report["tasks"]]}
    with (job / "origin.json").open("xb") as stream:
        stream.write(_bytes(origin))
    report["origin_sha256"] = _sha(_bytes(origin))
    save()
    return report


def _task_job_identity(row: dict) -> dict:
    return {key: row.get(key) for key in ("project_id", "project_instance_id", "project_root", "scene_root",
            "unit_id", "contract", "contract_sha256", "planned_run_id", "requested_max_visible_chars")}


def _save_job_progress(record_path: Path, previous: bytes, report: dict) -> bytes:
    """CAS persistence with original job bytes retained; caller owns job lock."""
    import tempfile
    _assert_no_reparse(record_path, code="INPUT_PACK_JOB_UNSAFE")
    if record_path.read_bytes() != previous:
        raise ContractError("INPUT_PACK_JOB_WRITE_CONFLICT", "job changed during processing")
    history = record_path.parent / "history"
    _assert_no_reparse(history, code="INPUT_PACK_JOB_UNSAFE")
    history.mkdir(exist_ok=True)
    old = history / (_sha(previous) + ".json")
    _assert_no_reparse(old, code="INPUT_PACK_JOB_UNSAFE")
    if old.exists():
        if old.read_bytes() != previous:
            raise ContractError("INPUT_PACK_JOB_HISTORY_CHANGED", "prior job bytes changed")
    else:
        with old.open("xb") as stream:
            stream.write(previous)
    new = _bytes(report)
    with tempfile.NamedTemporaryFile(mode="wb", dir=record_path.parent, delete=False, prefix=".result.") as stream:
        stream.write(new); stream.flush(); os.fsync(stream.fileno())
        pending = Path(stream.name)
    _assert_no_reparse(record_path, code="INPUT_PACK_JOB_UNSAFE")
    if record_path.read_bytes() != previous:
        raise ContractError("INPUT_PACK_JOB_WRITE_CONFLICT", "job changed before persistence; temporary bytes retained")
    os.replace(pending, record_path)
    return new


def prepare_package_runs(job_record: str | Path, *, data_home: str | Path, _validate_only=False) -> dict:
    """Prepare/recheck this job's offline Runs without executing any stage.

    All contract paths, Run IDs and signed-review request data are internal.
    Progress and original inputs survive interruption; existing Runs are only
    checked, never overwritten or reset.
    """
    from types import SimpleNamespace
    try:
        from . import cnw_runner
    except ImportError:
        import cnw_runner
    if not data_home or not Path(data_home).is_absolute():
        raise ContractError("DATA_HOME_REQUIRED", "select an explicit registered DataHome")
    _assert_no_reparse(Path(data_home), code="INPUT_PACK_JOB_UNSAFE")
    home = Path(data_home).resolve(strict=True)
    _data_home_identity(home, create=False)
    supplied = Path(job_record).absolute()
    _assert_no_reparse(supplied, code="INPUT_PACK_JOB_UNSAFE")
    record_path = supplied.resolve(strict=True)
    job = record_path.parent
    if record_path.name != "result.json" or job.parent != home / "shared/input_pack_jobs":
        raise ContractError("INPUT_PACK_JOB_UNSAFE", "select a job owned by this DataHome")
    if _json(_safe_source_file(job, "result.json").read_bytes()).get("schema_version") == "cnw_input_pack_job_v2":
        try:
            from .cnw_native_pack import prepare_native_runs, load_job
        except ImportError:
            from cnw_native_pack import prepare_native_runs, load_job
        if _validate_only:
            return load_job(record_path, data_home=home)[2]
        return prepare_native_runs(record_path, data_home=home)
    with project_write_lock(job):
        _assert_no_reparse(record_path, code="INPUT_PACK_JOB_UNSAFE")
        raw = record_path.read_bytes()
        report = _json(raw)
        if (not isinstance(report, dict) or report.get("schema_version") != "cnw_input_pack_job_v1" or report.get("job_id") != job.name
                or report.get("status") not in {"CONTRACTS_READY_FOR_PREFLIGHT", "INPUTS_PREPARED_WITH_CAPACITY_PENDING", "RUNS_PREPARED_PENDING_AUTHORIZATION", "RUNS_PREPARED_WITH_CAPACITY_PENDING", "JOB_EXECUTION_INCOMPLETE", "JOB_AWAITING_AUTHOR", "MOCK_STORIES_EXPORTED", "MOCK_STORIES_EXPORTED_WITH_CAPACITY_PENDING"}
                or not isinstance(report.get("tasks"), list) or not report["tasks"]):
            raise ContractError("INPUT_PACK_JOB_NOT_READY", "job inputs are incomplete or its identity differs")
        archive = _safe_source_file(job, "input.zip").read_bytes()
        if not (job / "origin.json").is_file():
            raise ContractError("INPUT_PACK_JOB_ORIGIN_UNAVAILABLE", "older job is retained; automatic preparation requires its original task binding record")
        origin_raw = _safe_source_file(job, "origin.json").read_bytes()
        origin = _json(origin_raw)
        if (_sha(archive) != report.get("pack_sha256") or _sha(origin_raw) != report.get("origin_sha256")
                or _bytes(origin) != _bytes({"schema_version": "cnw_input_pack_job_origin_v1", "job_id": job.name,
                             "pack_sha256": report["pack_sha256"], "tasks": [_task_job_identity(row) for row in report["tasks"]]})):
            raise ContractError("INPUT_PACK_JOB_BINDINGS_CHANGED", "job no longer binds its original tasks and archive")
        checked = []
        for row in report["tasks"]:
            if row.get("status") == "CAPACITY_PENDING":
                continue
            registered = resolve_project(row["project_root"], data_home=home)
            root = Path(registered["project_root"])
            contract_path = _safe_source_file(root, str(Path(row["contract"]).relative_to(root)))
            contract_raw = contract_path.read_bytes()
            contract = _json(contract_raw)
            if (registered["project_instance_id"] != row["project_instance_id"]
                    or registered["project_id"] != row["project_id"]
                    or _sha(contract_raw) != row["contract_sha256"]
                    or contract["unit"]["id"] != row["unit_id"]
                    or contract.get("input_pack", {}).get("pack_sha256") != report["pack_sha256"]):
                raise ContractError("INPUT_PACK_JOB_BINDINGS_CHANGED", "task instance, contract or source package changed")
            checked.append((row, root, contract_path, contract))

        if _validate_only:
            return report

        def save_progress():
            nonlocal raw
            raw = _save_job_progress(record_path, raw, report)

        for row, root, contract_path, contract in checked:
            with project_write_lock(root):
                run_id = row["planned_run_id"]
                run = root / "runs" / run_id
                _assert_no_reparse(run, code="INPUT_PACK_RUN_UNSAFE")
                if not run.exists():
                    build_contract_preflight(root, contract_path, run_id=run_id)
                    cnw_runner.produce(SimpleNamespace(mode="offline", unit=contract["unit"]["kind"],
                        work_id=contract["unit"]["id"], contract=str(contract_path), project_root=str(root),
                        run_id=run_id, create_only=True))
                bindings = build_run_contract_preflight(root, contract_path, run_id=run_id)
                identity = bindings["identity_sha256"]
                binding_path = job / f"{row['project_instance_id']}.{identity}.run-bindings.json"
                _assert_no_reparse(binding_path, code="INPUT_PACK_JOB_UNSAFE")
                if binding_path.exists():
                    previous = _json(binding_path.read_bytes())
                    if _bytes(previous["bindings"]) != _bytes(bindings["bindings"]):
                        raise ContractError("INPUT_PACK_RUN_BINDINGS_CHANGED", "stored Run bindings differ")
                else:
                    with binding_path.open("xb") as stream:
                        stream.write(_bytes(bindings))
                row["run_preparation"] = {"status": "OFFLINE_BINDINGS_VALIDATED", "run_id": run_id,
                    "run_path": str(run), "identity_sha256": identity, "record": str(binding_path),
                    "record_sha256": _sha(binding_path.read_bytes()), "provider_call_authorized": False,
                    "controller_attestation_status": "ATTESTATION_PENDING", "live_authorization_status": "NOT_AUTHORIZED"}
                if not row.get("execution"):
                    row["status"] = "RUN_PREPARED_PENDING_AUTHORIZATION"
            save_progress()
        capacity_pending = any(row.get("status") == "CAPACITY_PENDING" for row in report["tasks"])
        if not any(row.get("execution") for row in report["tasks"]):
            report["status"] = ("RUNS_PREPARED_WITH_CAPACITY_PENDING" if checked else "INPUTS_PREPARED_WITH_CAPACITY_PENDING") if capacity_pending else "RUNS_PREPARED_PENDING_AUTHORIZATION"
        report["production_status"] = "NOT_AUTHORIZED"
        save_progress()
        return report


def _offline_job_run(run: Path) -> dict:
    try:
        from . import cnw_runner
    except ImportError:
        import cnw_runner
    state = cnw_runner.load_state(run)
    if state.get("mode") != "offline" or state.get("fixture_only") is not False:
        raise ContractError("INPUT_PACK_RUN_MODE_INVALID", "this job executor supports only normally validated offline Runs")
    receipts = state.get("provider_requests", [])
    if any(row.get("mode") != "MOCK_ONLY" or row.get("simulation_status") != "SIMULATED"
           or row.get("fixture_only") is not True for row in receipts):
        raise ContractError("INPUT_PACK_SIMULATION_RECEIPT_INVALID", "offline job cannot consume Live or unmarked receipts")
    if len({row.get("request_id") for row in receipts}) != len(receipts):
        raise ContractError("INPUT_PACK_SIMULATION_RECEIPT_INVALID", "receipt IDs must be unique within the actual Run")
    return state


def _job_run(run: Path, execution_mode: str) -> dict:
    """Read the actual Run without converting its mode or receipt history."""
    if execution_mode == "offline":
        return _offline_job_run(run)
    try:
        from . import cnw_runner
    except ImportError:
        import cnw_runner
    state = cnw_runner.load_state(run)
    if state.get("mode") != "live" or state.get("fixture_only") is not False:
        raise ContractError("INPUT_PACK_RUN_MODE_INVALID", "production cannot consume an offline or fixture Run")
    if any(row.get("mode") != "LIVE" or row.get("fixture_only") is not False
           or row.get("simulation_status") == "SIMULATED" for row in state.get("provider_requests", [])):
        raise ContractError("INPUT_PACK_LIVE_RECEIPT_INVALID", "production cannot consume simulated or unmarked receipts")
    cnw_runner._require_generic_provider_authorization(run, stage="plot")
    return state


def _attempt_source_projection(report: dict) -> dict:
    native = report.get("schema_version") in {"cnw_input_pack_job_v2", "cnw_native_job_origin_v1"}
    keys = ("task_alias", "project_alias", "declaration", "declaration_sha256", "requirements_sha256",
            "project_id", "project_instance_id", "project_root", "unit_id", "planned_run_id", "requested_max_visible_chars")
    return {"job_id": report["job_id"], "pack_sha256": report["pack_sha256"],
            "projects": report.get("projects") if native else None,
            "tasks": [{key: row.get(key) for key in keys} if native else _task_job_identity(row)
                      for row in report["tasks"]]}


def _live_attempt_declaration(source: dict, attempt_id: str) -> dict:
    if str(uuid.UUID(attempt_id)) != attempt_id:
        raise ContractError("INPUT_PACK_ATTEMPT_ID_INVALID", "attempt ID must be canonical")
    return {"schema_version": "cnw_pack_attempt_declaration_v1", "attempt_id": attempt_id,
            "execution_mode": "live", "job_id": source["job_id"], "pack_sha256": source["pack_sha256"],
            "origin_sha256": source["origin_sha256"], "source_schema": source["schema_version"],
            "source_projection": _attempt_source_projection(source),
            "tasks": [{"task_key": row.get("task_alias", row["unit_id"]),
                **{key: row[key] for key in ("project_id", "project_instance_id", "project_root", "unit_id")},
                "planned_run_id": f"LIVE-{uuid.UUID(attempt_id).hex}-{number:04d}"}
                for number, row in enumerate(source["tasks"], 1)]}


def validate_attempt_metadata(root: Path, metadata: dict, *, task_key: str) -> dict:
    """Recompute owned attempt paths and declarations; this grants no authority."""
    if not isinstance(metadata, dict) or set(metadata) != {"job_id", "attempt_id", "declaration_sha256"}:
        raise ContractError("INPUT_PACK_ATTEMPT_BINDING_INVALID", "invalid attempt binding")
    for key in ("job_id", "attempt_id"):
        if str(uuid.UUID(metadata[key])) != metadata[key]:
            raise ContractError("INPUT_PACK_ATTEMPT_BINDING_INVALID", "invalid canonical attempt identity")
    registered = resolve_project(root, data_home=root.parent.parent)
    job = root.parent.parent / "shared/input_pack_jobs" / metadata["job_id"]
    directory = job / "attempts" / metadata["attempt_id"]
    declaration_raw = _safe_source_file(directory, "declaration.json").read_bytes()
    declaration = _json(declaration_raw)
    source = _json(_safe_source_file(directory, "source.json").read_bytes())
    origin_raw = _safe_source_file(job, "origin.json").read_bytes()
    if (metadata["declaration_sha256"] != _sha(declaration_raw)
            or _sha(origin_raw) != source["origin_sha256"]
            or _attempt_source_projection(_json(origin_raw)) != _attempt_source_projection(source)
            or _sha(_safe_source_file(job, "input.zip").read_bytes()) != source["pack_sha256"]
            or _bytes(declaration) != _bytes(_live_attempt_declaration(source, metadata["attempt_id"]))):
        raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "attempt no longer represents original declarations")
    rows = [r for r in declaration["tasks"] if r["task_key"] == task_key
            and r["project_instance_id"] == registered["project_instance_id"]]
    if len(rows) != 1 or rows[0]["project_root"] != str(root) or rows[0]["project_id"] != registered["project_id"]:
        raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "attempt task belongs to another instance")
    source_rows = [r for r in source["tasks"] if r.get("task_alias", r["unit_id"]) == task_key
                   and r["project_instance_id"] == registered["project_instance_id"]]
    if len(source_rows) != 1:
        raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "original task ownership changed")
    return {"declaration": declaration, "row": rows[0], "source_task": source_rows[0],
            "projects": source.get("projects"), "directory": directory}


def _live_attempt(job: Path, source: dict, *, new_attempt=False) -> tuple[Path, dict]:
    """Publish a recoverable application plan before any Run or Provider call."""
    try:
        from .cnw_native_pack import _immutable
    except ImportError:
        from cnw_native_pack import _immutable
    intent_path = job / "live-attempt-intent.json"
    current_path = job / "current-live-attempt.json"
    if new_attempt or not intent_path.exists():
        attempt_id = str(uuid.uuid4())
        declaration = _live_attempt_declaration(source, attempt_id)
        intent = {"schema_version": "cnw_pack_attempt_intent_v1", "source": source, "declaration": declaration,
                  "previous_pointer_sha256": _sha(_safe_source_file(job, current_path.name).read_bytes()) if current_path.exists() else None}
        if intent_path.exists():
            _save_job_progress(intent_path, _safe_source_file(job, intent_path.name).read_bytes(), intent)
        else:
            _immutable(intent_path, _bytes(intent))
    intent = _json(_safe_source_file(job, intent_path.name).read_bytes())
    original = intent["source"]
    declaration = intent["declaration"]
    if (_attempt_source_projection(original) != _attempt_source_projection(source)
            or original["origin_sha256"] != source["origin_sha256"]
            or _bytes(declaration) != _bytes(_live_attempt_declaration(original, declaration["attempt_id"]))):
        raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "attempt intent or immutable task selection changed")
    metadata = {"job_id": source["job_id"], "attempt_id": declaration["attempt_id"],
                "declaration_sha256": _sha(_bytes(declaration))}
    directory = job / "attempts" / declaration["attempt_id"]
    _assert_no_reparse(directory, code="INPUT_PACK_ATTEMPT_UNSAFE")
    if not directory.exists():
        prepared = directory.with_name(".prepare-" + declaration["attempt_id"])
        _immutable(prepared / "source.json", _bytes(original))
        _immutable(prepared / "declaration.json", _bytes(declaration))
        rows = []
        for original_row, planned in zip(original["tasks"], declaration["tasks"]):
            row = json.loads(_bytes(original_row))
            for key in ("execution", "run_preparation", "materialization", "preparation"):
                row.pop(key, None)
            if original["schema_version"] == "cnw_input_pack_job_v2":
                for key in ("contract", "contract_sha256", "draft"):
                    row.pop(key, None)
            row.update(planned_run_id=planned["planned_run_id"], execution_attempt=metadata, status="TASK_PLANNED")
            rows.append(row)
        report = {"schema_version": "cnw_pack_execution_attempt_v1", "job_id": source["job_id"],
                  "source_schema": original["schema_version"], "pack_sha256": source["pack_sha256"],
                  "origin_sha256": source["origin_sha256"], "attempt_id": declaration["attempt_id"],
                  "execution_mode": "live", "execution_attempt": metadata, "projects": original.get("projects"),
                  "tasks": rows, "status": "ATTEMPT_PLANNED", "production_status": "NOT_AUTHORIZED"}
        _immutable(prepared / "result.json", _bytes(report))
        os.rename(prepared, directory)
    if (_safe_source_file(directory, "source.json").read_bytes() != _bytes(original)
            or _safe_source_file(directory, "declaration.json").read_bytes() != _bytes(declaration)):
        raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "published attempt differs from its intent")
    record = directory / "result.json"
    report = _json(_safe_source_file(directory, record.name).read_bytes())
    if (report.get("execution_mode") != "live" or report.get("execution_attempt") != metadata
            or report.get("source_schema") != source["schema_version"]
            or report.get("projects") != original.get("projects") or len(report.get("tasks", [])) != len(declaration["tasks"])):
        raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "attempt mode or declared task set changed")
    for row, planned, original_row in zip(report["tasks"], declaration["tasks"], original["tasks"]):
        if (any(row.get(k) != v for k, v in planned.items() if k != "task_key")
                or row.get("execution_attempt") != metadata
                or row.get("declaration") != original_row.get("declaration")):
            raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "attempt task routing changed")
        if source["schema_version"] == "cnw_input_pack_job_v1":
            expected = _task_job_identity(original_row)
            expected["planned_run_id"] = planned["planned_run_id"]
            if _task_job_identity(row) != expected:
                raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "attempt changed its frozen legacy contract")
        else:
            for key in ("task_alias", "project_alias", "declaration_sha256", "requirements_sha256", "requested_max_visible_chars"):
                if row.get(key) != original_row.get(key):
                    raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "attempt changed its frozen native requirement")
    pointer = {"attempt_id": declaration["attempt_id"], "declaration_sha256": metadata["declaration_sha256"]}
    if current_path.exists():
        current = _safe_source_file(job, current_path.name).read_bytes()
        if _json(current) != pointer:
            if _sha(current) != intent.get("previous_pointer_sha256"):
                raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "attempt pointer changed outside its planned publication")
            _save_job_progress(current_path, current, pointer)
    else:
        if intent.get("previous_pointer_sha256") is not None:
            raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "previous attempt pointer disappeared")
        _immutable(current_path, _bytes(pointer))
    return record, report


def _execute_live_package_job(job_record, *, data_home, new_attempt=False) -> dict:
    from types import SimpleNamespace
    try:
        from . import cnw_runner, cnw_native_pack
    except ImportError:
        import cnw_runner, cnw_native_pack
    source = prepare_package_runs(job_record, data_home=data_home, _validate_only=True)
    home, job = Path(data_home).resolve(strict=True), Path(job_record).resolve(strict=True).parent
    with project_write_lock(job):
        source = prepare_package_runs(job_record, data_home=home, _validate_only=True)
        record, report = _live_attempt(job, source, new_attempt=new_attempt)
        for key in ("provider_call", "provider_request_count", "fee_reservation_count"):
            report.pop(key, None)
        raw = _safe_source_file(record.parent, record.name).read_bytes()
        def save():
            nonlocal raw
            raw = _save_job_progress(record, raw, report)
        for row in report["tasks"]:
            root = Path(resolve_project(row["project_root"], data_home=home)["project_root"])
            stage = "run_preparation"
            execution = row.setdefault("execution", {"mode": "LIVE", "requested_execution_mode": "live", "stages": {}})
            if execution.get("mode") != "LIVE" or execution.get("requested_execution_mode") != "live":
                raise ContractError("INPUT_PACK_EXECUTION_MODE_CHANGED", "a Live attempt cannot adopt offline execution")
            try:
                with project_write_lock(root):
                    if report["source_schema"] == "cnw_input_pack_job_v2":
                        if not cnw_native_pack.prepare_native_task(report, row, record.parent, data_home=home):
                            save()
                            continue
                    else:
                        contract_path = _safe_source_file(root, str(Path(row["contract"]).relative_to(root)))
                        contract = _json(contract_path.read_bytes())
                        if _sha(contract_path.read_bytes()) != row["contract_sha256"]:
                            raise ContractError("INPUT_PACK_ATTEMPT_BINDING_CHANGED", "legacy contract changed")
                        run = root / "runs" / row["planned_run_id"]
                        if not run.exists():
                            build_contract_preflight(root, contract_path, run_id=run.name)
                            try:
                                from .cnw_live_authorization import publish_request
                            except ImportError:
                                from cnw_live_authorization import publish_request
                            row["authorization_request"] = publish_request(root, contract_path, run_id=run.name)
                            cnw_runner.produce(SimpleNamespace(mode="live", unit=contract["unit"]["kind"],
                                work_id=row["unit_id"], contract=str(contract_path), project_root=str(root), run_id=run.name, create_only=True))
                        _job_run(run, "live")
                        bindings = build_run_contract_preflight(root, contract_path, run_id=run.name)
                        bound = record.parent / "run_bindings" / (row["project_instance_id"] + "." + row["unit_id"] + ".json")
                        cnw_native_pack._immutable(bound, _bytes(bindings))
                        row["run_preparation"] = {"identity_sha256": bindings["identity_sha256"],
                            "record": str(bound), "record_sha256": _sha(bound.read_bytes()), "run_path": str(run)}
                    run = root / "runs" / row["planned_run_id"]
                    with cnw_runner.locked_run(run, lock_name="execution.lock"):
                        _execute_package_task(run, root, row, execution, report, execution_mode="live", save=save)
            except Exception as exc:
                code = getattr(exc, "code", "INPUT_PACK_STAGE_INTERRUPTED")
                stage = execution.get("active_stage", stage)
                execution.update(status="EXECUTION_INCOMPLETE", blocking_code=code, interrupted_stage=stage)
                execution.setdefault("interruptions", []).append({"stage": stage, "blocking_code": code, "error_type": type(exc).__name__})
                row["status"] = "TASK_EXECUTION_INCOMPLETE"
                report.update(status="JOB_EXECUTION_INCOMPLETE", blocking_code=code, requested_execution_mode="live",
                    production_status="NOT_AUTHORIZED", attempt_record=str(record), job_record=str(job_record))
                if code == "LIVE_AUTHORIZATION_REQUIRED" and not any(
                        (Path(r["project_root"])/"runs"/r["planned_run_id"]).exists() for r in report["tasks"]):
                    report.update(provider_call="none", provider_request_count=0, fee_reservation_count=0)
                save()
                return report
        complete = all(row.get("status") == "LIVE_STORY_EXPORTED" for row in report["tasks"])
        report.update(status="LIVE_STORIES_EXPORTED" if complete else "JOB_WAITING_PREDECESSOR",
                      production_status="LIVE_EXECUTED" if complete else "NOT_AUTHORIZED",
                      attempt_record=str(record), user_creative_accepted=False)
        save()
        return report


def _export_package_run(run: Path, root: Path, *, job_id: str, execution_mode: str) -> dict:
    """A production completion requires the full actual Live evidence validator."""
    from types import SimpleNamespace
    try:
        from . import cnw_runner
    except ImportError:
        import cnw_runner
    if execution_mode == "live":
        validated = cnw_runner.verify_live(SimpleNamespace(project_root=str(root), run_id=run.name))
        if validated.get("status") != "LIVE_EVIDENCE_VALIDATED":
            raise ContractError("INPUT_PACK_LIVE_RECEIPT_INVALID", "complete Live evidence was not validated")
    elif execution_mode != "offline":
        raise ContractError("INPUT_PACK_EXECUTION_MODE_INVALID", "unknown export execution mode")
    return cnw_runner.export_run(SimpleNamespace(project_root=str(root), run_id=run.name,
                                                _export_job_id=job_id))


def _execute_package_task(run: Path, root: Path, row: dict, execution: dict,
                          report: dict, *, execution_mode: str, save) -> None:
    """One shared checked CNW chain and export; admission remains in the Runner."""
    from types import SimpleNamespace
    try:
        from . import cnw_runner, cnw_recovery
    except ImportError:
        import cnw_runner, cnw_recovery
    bindings = build_run_contract_preflight(root, row["contract"], run_id=run.name)
    if bindings["identity_sha256"] != row["run_preparation"]["identity_sha256"]:
        raise ContractError("INPUT_PACK_RUN_BINDINGS_CHANGED", "Run inputs differ from the prepared task")
    existing = _job_run(run, execution_mode)
    review = existing["stages"]["re_review"]
    if review.get("status") == "REVISION_REQUIRED" and any(
            f.get("error_code") == "REREVIEW_REQUIRES_REVISION" for f in review.get("execution_failures", [])):
        execution["active_stage"] = "re_review"
        raise ContractError("REREVIEW_REQUIRES_REVISION", "bounded revision exhausted; author decision required, existing candidates retained")
    for stage in cnw_runner.CNW_STAGES:
        execution["active_stage"] = stage
        result = cnw_recovery.execute_checked(run, stage)
        state = _job_run(run, execution_mode)
        material = state["stages"][stage]
        if material.get("status") not in cnw_runner._MATERIALIZED:
            raise ContractError("INPUT_PACK_STAGE_NOT_COMPLETE", stage)
        text = cnw_runner._read_stage_text(run, state, stage)
        if not text.strip():
            raise ContractError("INPUT_PACK_STAGE_EMPTY", stage)
        execution["stages"][stage] = {"status": material["status"], "artifact": material["artifact"],
            "execution_identity": material["execution_identity"],
            "execution_input_identity": material["execution_input_identity"],
            "provider_request_ids": material.get("provider_request_ids", []),
            "last_result": result["status"] if "status" in result else "STAGE_EXECUTED"}
        row["status"] = "TASK_EXECUTING"
        save()
    execution["active_stage"] = "export"
    state = _job_run(run, execution_mode)
    cnw_recovery.verify_evidence(run, state)
    if not state.get("provider_requests"):
        code = "INPUT_PACK_SIMULATION_RECEIPT_INVALID" if execution_mode == "offline" else "INPUT_PACK_LIVE_RECEIPT_INVALID"
        raise ContractError(code, "a complete model chain needs actual receipts")
    # Bounded Re-review can create more Refine versions; re-read the final Run.
    for name in cnw_runner.CNW_STAGES:
        material = state["stages"][name]
        if material.get("status") not in cnw_runner._MATERIALIZED:
            raise ContractError("INPUT_PACK_STAGE_NOT_COMPLETE", name)
        cnw_runner._read_stage_text(run, state, name)
        execution["stages"][name].update(artifact=material["artifact"],
            execution_identity=material["execution_identity"],
            execution_input_identity=material["execution_input_identity"],
            provider_request_ids=material.get("provider_request_ids", []))
    inputs_sha = _sha(_bytes({name: state["stages"][name]["artifact"] for name in cnw_runner.CNW_STAGES}))
    prior = execution.get("export")
    if prior and prior["inputs_sha256"] != inputs_sha:
        raise ContractError("INPUT_PACK_EXPORT_INPUT_CHANGED", "previous export retained; changed candidate requires explicit handling")
    output = _export_package_run(run, root, job_id=report["job_id"], execution_mode=execution_mode)
    target = root / "deliverables" / row["project_instance_id"] / run.name
    _assert_no_reparse(target, code="INPUT_PACK_EXPORT_UNSAFE")
    if Path(output["deliverables"]) != target:
        raise ContractError("INPUT_PACK_EXPORT_BINDINGS_CHANGED", "export target differs from the actual task")
    file_hashes = {p.relative_to(root).as_posix(): _sha(_safe_source_file(root, p.relative_to(root).as_posix()).read_bytes())
                   for p in sorted(target.iterdir()) if p.is_file()}
    exported = {"inputs_sha256": inputs_sha, "result": output, "file_sha256": file_hashes}
    if prior and _bytes(prior) != _bytes(exported):
        raise ContractError("INPUT_PACK_EXPORT_BINDINGS_CHANGED", "cached export metadata differs from actual bound outputs")
    execution["export"] = exported
    if execution_mode == "offline":
        execution.update(mode="MOCK_ONLY", simulation_status="SIMULATED", status="MOCK_STORY_EXPORTED")
    else:
        execution.update(mode="LIVE", simulation_status="NOT_SIMULATED", status="LIVE_STORY_EXPORTED",
                         user_creative_accepted=False)
    execution.pop("blocking_code", None)
    execution.pop("active_stage", None)
    row["status"] = execution["status"]
    save()


def execute_package_job(job_record: str | Path, *, data_home: str | Path, execution_mode: str, new_attempt=False) -> dict:
    """Application-owned fixed CNW chain and export, retaining interruption.

    Source acquisition and model execution are independent choices. Live is
    carried explicitly to this boundary and fails closed until the reviewed
    production grant/fee adapters are installed. R5 tests inject only the
    final model interface for offline execution.
    """
    if execution_mode not in {"offline", "live"}:
        raise ContractError("INPUT_PACK_EXECUTION_MODE_INVALID", "execution mode must be explicit: offline or live")
    if new_attempt and execution_mode != "live":
        raise ContractError("INPUT_PACK_ATTEMPT_MODE_INVALID", "new independent attempts require explicit Live intent")
    if execution_mode == "live":
        return _execute_live_package_job(job_record, data_home=data_home, new_attempt=new_attempt)
    from types import SimpleNamespace
    try:
        from . import cnw_runner, cnw_recovery
    except ImportError:
        import cnw_runner, cnw_recovery
    prepared = prepare_package_runs(job_record, data_home=data_home)
    if prepared.get("status") == "JOB_PREPARATION_INCOMPLETE":
        return prepared
    home = Path(data_home).resolve(strict=True)
    record = Path(job_record).resolve(strict=True)
    with project_write_lock(record.parent):
        raw = _safe_source_file(record.parent, record.name).read_bytes()
        report = _json(raw)
        if _bytes(report) != _bytes(prepared):
            raise ContractError("INPUT_PACK_JOB_WRITE_CONFLICT", "job changed after identity validation")
        def save():
            nonlocal raw
            raw = _save_job_progress(record, raw, report)
        for row in report["tasks"]:
            if row.get("status") == "CAPACITY_PENDING":
                continue
            if report.get("schema_version") == "cnw_input_pack_job_v2" and not row.get("run_preparation"):
                try:
                    from .cnw_native_pack import prepare_native_task, record_preparation_failure
                except ImportError:
                    from cnw_native_pack import prepare_native_task, record_preparation_failure
                try:
                    ready = prepare_native_task(report, row, record.parent, data_home=home)
                except Exception as exc:
                    record_preparation_failure(report, row, exc)
                    save()
                    return report
                if not ready:
                    save()
                    continue
                save()
            root = Path(resolve_project(row["project_root"], data_home=home)["project_root"])
            run = root / "runs" / row["planned_run_id"]
            _assert_no_reparse(run, code="INPUT_PACK_RUN_UNSAFE")
            execution = row.setdefault("execution", {"mode": "OFFLINE", "simulation_status": "NOT_EXECUTED", "stages": {}})
            requested_mode = execution.get("requested_execution_mode")
            if requested_mode not in {None, "offline"}:
                raise ContractError("INPUT_PACK_EXECUTION_MODE_CHANGED", "offline executor cannot resume a job requested in another mode")
            if execution.get("mode") not in {"offline", "OFFLINE", "MOCK_ONLY"}:
                raise ContractError("INPUT_PACK_EXECUTION_MODE_CHANGED", "offline executor cannot resume a non-offline job")
            execution["requested_execution_mode"] = "offline"
            stage = "preflight"
            try:
                with project_write_lock(root), cnw_runner.locked_run(run, lock_name="execution.lock"):
                    _execute_package_task(run, root, row, execution, report, execution_mode="offline", save=save)
            except Exception as exc:
                stage = execution.get("active_stage", stage)
                code = getattr(exc, "code", "INPUT_PACK_STAGE_INTERRUPTED")
                awaiting = code in {"REREVIEW_REQUIRES_REVISION", "AUTHOR_INPUT_CONFLICT", "INPUT_PACK_STAGE_NOT_COMPLETE"}
                execution.update(status="AWAITING_AUTHOR" if awaiting else "EXECUTION_INCOMPLETE", blocking_code=code, interrupted_stage=stage)
                execution.setdefault("interruptions", []).append({"stage": stage, "blocking_code": code, "error_type": type(exc).__name__, "detail": str(exc)[:2048]})
                row["status"] = "TASK_AWAITING_AUTHOR" if awaiting else "TASK_EXECUTION_INCOMPLETE"
                report.update(status="JOB_AWAITING_AUTHOR" if awaiting else "JOB_EXECUTION_INCOMPLETE", blocking_code=code)
                if awaiting:
                    report["action_required"] = "已保留稿件、审稿与未决问题；需要作者处置。重复启动不会重新授予修订次数。"
                save()
                return report
        completed = any(r.get("status") == "MOCK_STORY_EXPORTED" for r in report["tasks"])
        report["status"] = ("MOCK_STORIES_EXPORTED_WITH_PENDING_TASKS" if completed else "INPUTS_PREPARED_WITH_PENDING_TASKS") if any(r.get("status") == "WAITING_PREDECESSOR" for r in report["tasks"]) else ("MOCK_STORIES_EXPORTED_WITH_CAPACITY_PENDING" if completed else "INPUTS_PREPARED_WITH_CAPACITY_PENDING") if any(r.get("status") == "CAPACITY_PENDING" for r in report["tasks"]) else "MOCK_STORIES_EXPORTED"
        report.update(execution_mode="offline", simulation_status="SIMULATED" if completed else "NOT_EXECUTED", live_validation_status="NOT_LIVE_VALIDATED", production_status="NOT_AUTHORIZED")
        report.pop("blocking_code", None)
        save()
        return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input")
    source.add_argument("--job")
    parser.add_argument("--data-home", required=True)
    parser.add_argument("--source-repository")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--prepare-runs", action="store_true")
    parser.add_argument("--execute-job", action="store_true")
    parser.add_argument("--execution-mode", choices=("offline", "live"))
    parser.add_argument("--new-attempt", action="store_true", help="plan a separate Live execution attempt; never converts an offline Run")
    args = parser.parse_args(argv)
    if args.execute_job and not args.execution_mode:
        parser.error("--execute-job requires an explicit --execution-mode offline|live")
    if args.execution_mode and not args.execute_job:
        parser.error("--execution-mode is valid only with --execute-job")
    if args.new_attempt and (not args.execute_job or args.execution_mode != "live"):
        parser.error("--new-attempt requires --execute-job --execution-mode live")
    if args.job:
        if args.source_repository:
            parser.error("a stored job does not fetch or reimport sources")
        result = execute_package_job(args.job, data_home=args.data_home, execution_mode=args.execution_mode, new_attempt=args.new_attempt) if args.execute_job else prepare_package_runs(args.job, data_home=args.data_home)
    else:
        result = import_package(args.input, data_home=args.data_home, local_source=args.source_repository, offline=args.offline)
        if result["status"] not in {"IMPORT_INCOMPLETE", "JOB_PREPARATION_INCOMPLETE"}:
            if args.execute_job:
                result = execute_package_job(result["job_record"], data_home=args.data_home, execution_mode=args.execution_mode, new_attempt=args.new_attempt)
            elif args.prepare_runs:
                result = prepare_package_runs(result["job_record"], data_home=args.data_home)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] in {"IMPORT_INCOMPLETE", "JOB_PREPARATION_INCOMPLETE", "JOB_EXECUTION_INCOMPLETE", "JOB_AWAITING_AUTHOR", "LIVE_ROUTE_NOT_READY"} else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, PathResolutionError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "INPUT_PACK_IMPORT_FAILED", "blocking_code": getattr(exc, "code", "INPUT_PACK_PREPARATION_FAILED"),
                          "provider_call": "none"}, ensure_ascii=False))
        raise SystemExit(2)
