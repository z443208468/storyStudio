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
    from .cnw_contract import ContractError
    from .cnw_input_pack import read_input_pack, prepare_scene_input, _json, _sha, _bytes, _source_bytes, _scene_anchor
    from .cnw_project import write_contract_draft, build_contract_preflight
    from .project_paths import (_prepare_data_home, _ensure_private_directory, _data_home_identity,
                                _assert_no_reparse, create_project, PathResolutionError, DATA_HOME_SCHEMA)
    from .project_transactions import project_write_lock
except ImportError:
    from cnw_contract import ContractError
    from cnw_input_pack import read_input_pack, prepare_scene_input, _json, _sha, _bytes, _source_bytes, _scene_anchor
    from cnw_project import write_contract_draft, build_contract_preflight
    from project_paths import (_prepare_data_home, _ensure_private_directory, _data_home_identity,
                               _assert_no_reparse, create_project, PathResolutionError, DATA_HOME_SCHEMA)
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
                preflight = build_contract_preflight(registered["project_root"], result["contract"], run_id=f"PACK-{pack['pack_sha256'][:12]}-{number:02d}")
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
    save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--data-home", required=True)
    parser.add_argument("--source-repository")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    result = import_package(args.input, data_home=args.data_home, local_source=args.source_repository, offline=args.offline)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] == "IMPORT_INCOMPLETE" else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, PathResolutionError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "INPUT_PACK_IMPORT_FAILED", "blocking_code": getattr(exc, "code", "INPUT_PACK_PREPARATION_FAILED"),
                          "provider_call": "none"}, ensure_ascii=False))
        raise SystemExit(2)
