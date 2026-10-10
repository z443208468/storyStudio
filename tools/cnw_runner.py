"""Persistent, offline-first dispatcher for CNW production runs.

This layer records run identity, stage dependencies and artifacts. Provider
execution is deliberately delegated to later production adapters.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid

try:
    from .cnw_contract import ContractError, assert_output_within_root, check_required_fields, load_contract, validate_episode_budget, validate_scene_budget, validate_source_identity
except ImportError:  # direct script execution from PowerShell
    from cnw_contract import ContractError, assert_output_within_root, check_required_fields, load_contract, validate_episode_budget, validate_scene_budget, validate_source_identity

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("plot", "cards", "brief", "pov", "draft", "lint1", "lint2", "lens5", "verifier3", "completeness", "refine", "re-review", "promote", "export")
STAGE_ALIASES = {"scene_cards": "cards", "writing_brief": "brief", "prose": "draft", "lint_layer1": "lint1", "lint_layer2": "lint2", "multi_lens_review": "lens5", "adversarial_verify": "verifier3", "completeness_critic": "completeness", "re_review": "re-review"}
WORKFLOW_PATH = ROOT / "runtime/reference/cnw_97ad71fe5e5e/templates/config/workflow.template.yml"
PROMPT_ROOT = ROOT / "prompts/cnw"
STAGE_PROMPTS = {"plot": "plot.md", "cards": "scene_cards.md", "brief": "brief.md", "draft": "prose.md"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def safe_run_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", value) or value in {".", ".."}:
        raise ContractError("VALID_RUN_ID_REQUIRED", value)
    return value


def normalize_stage(value: str) -> str:
    stage = STAGE_ALIASES.get(value, value)
    if stage not in STAGES:
        raise ContractError("UNKNOWN_STAGE", value)
    return stage


def run_path(run_id: str, runs_root: Path | None = None) -> Path:
    run_id = safe_run_id(run_id)
    base_candidate = (runs_root or ROOT / "runs").absolute()
    cursor = base_candidate
    while cursor != cursor.parent:
        if cursor.is_symlink():
            raise ContractError("RUN_ROOT_SYMLINK_REJECTED", str(cursor))
        cursor = cursor.parent
    base = base_candidate.resolve()
    target = base / run_id
    if target.is_symlink():
        raise ContractError("RUN_PATH_SYMLINK_REJECTED", run_id)
    resolved = target.resolve()
    if not resolved.is_relative_to(base):
        raise ContractError("RUN_PATH_UNSAFE", run_id)
    for parent in (target, *target.parents):
        if parent == base.parent:
            break
        if parent.is_symlink():
            raise ContractError("RUN_PATH_SYMLINK_REJECTED", str(parent))
    return target


def runs_root_for(args) -> Path:
    project_root = getattr(args, "project_root", None)
    return (Path(project_root).resolve() if project_root else ROOT) / "runs"


def safe_run_input(path: str | Path, run_directory: Path) -> Path:
    base = run_directory.resolve()
    candidate = Path(path).absolute()
    cursor = candidate
    while cursor != cursor.parent:
        if cursor.is_symlink():
            raise ContractError("STAGE_INPUT_UNSAFE", "input path contains a symlink")
        cursor = cursor.parent
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(base) or not resolved.is_file():
        raise ContractError("STAGE_INPUT_OUTSIDE_RUN", str(candidate))
    return resolved


def load_state(path: Path) -> dict:
    state_path = path / "run_state.json"
    if not state_path.is_file() or state_path.is_symlink():
        raise ContractError("RUN_STATE_MISSING_OR_UNSAFE", str(state_path))
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("RUN_STATE_INVALID", str(exc)) from exc
    if state.get("run_id") != path.name:
        raise ContractError("RUN_IDENTITY_MISMATCH", path.name)
    if state.get("schema_version") == "cnw_run_state_v1" and "provider_config_sha256" not in state:
        production_config = ROOT / "config/production.example.json"
        cost_guard_runner = ROOT / "tools/p2_cost_guard.py"
        state["provider_config_sha256"] = sha(production_config.read_bytes())
        state["cost_guard_runner_sha256"] = sha(cost_guard_runner.read_bytes())
        state.setdefault("state_migrations", []).append("W05-provider-cost-policy-hashes")
    return state


def save_state(path: Path, state: dict) -> None:
    state_path = path / "run_state.json"
    if state_path.is_symlink():
        raise ContractError("RUN_STATE_SYMLINK_REJECTED", str(state_path))
    temp = state_path.with_name(f"run_state.json.tmp-{uuid.uuid4().hex}")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, state_path)


@contextmanager
def locked_run(path: Path):
    lock_path = path / "run.lock"
    if lock_path.is_symlink():
        raise ContractError("RUN_LOCK_SYMLINK_REJECTED", str(lock_path))
    stream = open(lock_path, "a+b")
    try:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        deadline = time.monotonic() + 15
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    raise ContractError("RUN_LOCK_TIMEOUT", path.name)
                time.sleep(0.05)
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    finally:
        stream.close()


def stage_predecessors(stage: str, unit_kind: str) -> tuple[str, ...]:
    if unit_kind == "scene":
        workflow = ["plot", "cards", "brief", "pov", "draft", "lint1", "lint2", "lens5", "verifier3", "completeness", "refine", "re-review", "promote", "export"]
    else:
        workflow = ["plot", "cards", "brief", "draft", "lint1", "lint2", "lens5", "verifier3", "completeness", "refine", "re-review", "promote", "export"]
    try:
        index = workflow.index(stage)
    except ValueError:
        raise ContractError("STAGE_NOT_IN_UNIT_WORKFLOW", stage)
    return tuple(workflow[:index])


def stage_prompt_hash(stage: str) -> str | None:
    filename = STAGE_PROMPTS.get(stage)
    if not filename:
        return None
    prompt = PROMPT_ROOT / filename
    if prompt.is_symlink() or not prompt.is_file():
        raise ContractError("STAGE_PROMPT_MISSING_OR_UNSAFE", str(prompt))
    return sha(prompt.read_bytes())


def produce(args) -> dict:
    if args.mode == "live":
        raise ContractError("LIVE_EXECUTOR_NOT_AVAILABLE", "provider execution is gated for W10; W05 creates offline run state only")
    run_id = safe_run_id(args.run_id)
    unit_id = args.work_id or ""
    contract_file = Path(args.contract)
    if not contract_file.is_absolute():
        contract_file = ROOT / contract_file
    contract_candidate = contract_file.absolute()
    for ancestor in (contract_candidate, *contract_candidate.parents):
        if ancestor.is_symlink():
            raise ContractError("CONTRACT_PATH_UNSAFE", "contract path contains a symlink")
    contract_file = contract_file.resolve(strict=True)
    project_root = Path(args.project_root).resolve() if args.project_root else ROOT
    if not contract_file.is_relative_to(project_root):
        raise ContractError("CONTRACT_PATH_OUTSIDE_PROJECT", str(contract_file))
    contract = load_contract(contract_file)
    check_required_fields(contract)
    is_fixture = str(contract.get("project_id", "")).startswith("FICT_")
    if not is_fixture:
        source = contract["source"]
        release_root = project_root / "inputs/private/release" / source["zip_sha256"].lower() / "Cangqi_Jun_Release_2_3"
        validate_source_identity(contract, source_root=release_root, expected_version=source["version"], expected_zip_sha256=source["zip_sha256"], expected_manifest_sha256=source["local_private_source_manifest_sha256"])
    kind = args.unit or contract["unit"].get("kind")
    if kind != contract["unit"].get("kind"):
        raise ContractError("UNIT_KIND_MISMATCH", f"requested {kind}; contract has {contract['unit'].get('kind')}")
    if not unit_id:
        unit_id = str(contract["unit"].get("id", ""))
    if unit_id != contract["unit"].get("id"):
        raise ContractError("WORK_ID_MISMATCH", unit_id)
    if kind == "scene":
        validate_scene_budget(contract)
    elif kind == "episode":
        validate_episode_budget(contract["unit"])
    else:
        raise ContractError("WORK_UNIT_KIND_INVALID", str(kind))
    production_config = ROOT / "config/production.example.json"
    cost_guard_runner = ROOT / "tools/p2_cost_guard.py"
    provider_settings = json.loads(production_config.read_text(encoding="utf-8-sig"))
    if provider_settings.get("provider", {}).get("max_in_flight") != 1:
        raise ContractError("MAX_IN_FLIGHT_POLICY_MISMATCH", "W05 requires max_in_flight=1")
    if provider_settings.get("cost_guard", {}).get("persist_across_run_ids") is not True:
        raise ContractError("COST_GUARD_POLICY_MISMATCH", "persistent campaign accounting is required")
    path = run_path(run_id, project_root / "runs")
    try:
        path.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ContractError("RUN_ID_COLLISION", run_id) from exc
    try:
        (path / "artifacts").mkdir()
        contract_copy = path / "artifacts" / "contract.json"
        contract_bytes = contract_file.read_bytes()
        contract_copy.write_bytes(contract_bytes)
        stages = {stage: {"status": "NOT_RUN", "dependencies": [], "artifact": None} for stage in STAGES}
        state = {
            "schema_version": "cnw_run_state_v1", "run_id": run_id, "work_id": unit_id,
            "unit_kind": kind, "project_id": contract["project_id"],
            "contract_path": str(contract_file.relative_to(project_root)).replace("\\", "/"),
            "contract_sha256": sha(contract_bytes), "source_identity": contract["source"], "fixture_only": is_fixture,
            "created_at": now(), "updated_at": now(), "status": "RUN_CREATED", "mode": args.mode,
            "workflow_template_sha256": sha(WORKFLOW_PATH.read_bytes()),
            "provider_requests": [], "stages": stages, "max_in_flight": 1,
            "provider_config_sha256": sha(production_config.read_bytes()),
            "cost_guard_runner_sha256": sha(cost_guard_runner.read_bytes()),
        }
        save_state(path, state)
        # A changed contract for the same work unit invalidates old cache claims,
        # but preserves every prior run and artifact for audit/recovery.
        for previous_path in (project_root / "runs").iterdir():
            if previous_path == path or previous_path.is_symlink() or not previous_path.is_dir():
                continue
            previous_state_path = previous_path / "run_state.json"
            if not previous_state_path.is_file() or previous_state_path.is_symlink():
                continue
            try:
                previous = json.loads(previous_state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if previous.get("work_id") == unit_id and previous.get("contract_sha256") != state["contract_sha256"]:
                previous["status"] = "INVALIDATED"
                previous["updated_at"] = now()
                for record in previous.get("stages", {}).values():
                    if record.get("status") in {"ACCEPTED", "READY_FOR_EXECUTION"}:
                        record["status"] = "INVALIDATED"
                save_state(previous_path, previous)
    except Exception:
        # Only clean up the directory created by this invocation; never replace a prior run.
        import shutil
        shutil.rmtree(path, ignore_errors=True)
        raise
    return {"status": "RUN_CREATED", "run_id": run_id, "work_id": unit_id, "contract_sha256": state["contract_sha256"], "path": str(path), "next_stage": "plot", "provider_call": "none"}


def step(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    with locked_run(path):
        return _step_locked(args, path)


def _step_locked(args, path: Path) -> dict:
    stage = normalize_stage(args.stage)
    state = load_state(path)
    if args.work_id and args.work_id != state["work_id"]:
        raise ContractError("WORK_ID_MISMATCH", args.work_id)
    requested_input = safe_run_input(args.input, path) if args.input else None
    predecessors = stage_predecessors(stage, state["unit_kind"])
    for dependency in predecessors:
        if state["stages"][dependency]["status"] != "ACCEPTED":
            raise ContractError("STAGE_DEPENDENCY_NOT_ACCEPTED", dependency)
    input_hashes = {"contract": state["contract_sha256"]}
    for dependency in predecessors:
        record = state["stages"][dependency]
        if record.get("artifact"):
            input_hashes[dependency] = record["artifact"]["sha256"]
    if requested_input:
        input_hashes["provided_input"] = sha(requested_input.read_bytes())
    existing = state["stages"][stage]
    prompt_hash = stage_prompt_hash(stage)
    fingerprint = sha(json.dumps({"stage": stage, "contract": state["contract_sha256"], "dependencies": input_hashes, "prompt_sha256": prompt_hash, "workflow_template_sha256": state["workflow_template_sha256"], "provider_config_sha256": state["provider_config_sha256"], "cost_guard_runner_sha256": state["cost_guard_runner_sha256"]}, sort_keys=True).encode())
    if existing.get("fingerprint") == fingerprint and existing["status"] == "ACCEPTED":
        return {"status": "STAGE_REUSED", "run_id": args.run_id, "stage": stage, "fingerprint": fingerprint, "provider_call": "none"}
    if existing.get("fingerprint") == fingerprint and existing["status"] == "READY_FOR_EXECUTION":
        return {"status": "STAGE_REUSED", "run_id": args.run_id, "stage": stage, "fingerprint": fingerprint, "provider_call": "none"}
    if existing["status"] not in ("NOT_RUN", "INVALIDATED"):
        unit_order = ["plot", "cards", "brief", "pov", "draft", "lint1", "lint2", "lens5", "verifier3", "completeness", "refine", "re-review", "promote", "export"]
        start = unit_order.index(stage)
        for downstream in unit_order[start:]:
            record = state["stages"][downstream]
            if record["status"] not in {"NOT_RUN", "INVALIDATED"}:
                record.setdefault("invalidated_attempts", []).append({key: value for key, value in record.items() if key != "invalidated_attempts"})
                record["status"] = "INVALIDATED"
                record.pop("fingerprint", None)
    artifact_rel = f"artifacts/{stage}.{fingerprint[:12]}.json"
    artifact_path = assert_output_within_root(path, artifact_rel)
    artifact = {"schema_version": "cnw_stage_request_v1", "run_id": args.run_id, "work_id": state["work_id"], "stage": stage, "contract_sha256": state["contract_sha256"], "prompt_sha256": prompt_hash, "input_hashes": input_hashes, "fingerprint": fingerprint, "status": "READY_FOR_EXECUTION", "provider_call": "not_performed_by_W05_runner"}
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    attempts = existing.get("invalidated_attempts", [])
    state["stages"][stage] = {"status": "READY_FOR_EXECUTION", "fingerprint": fingerprint, "prompt_sha256": prompt_hash, "input_hashes": input_hashes, "artifact": {"path": artifact_rel, "sha256": sha(artifact_path.read_bytes())}, "updated_at": now(), "invalidated_attempts": attempts}
    state["status"] = "RUNNING"
    state["updated_at"] = now()
    save_state(path, state)
    return {"status": "READY_FOR_EXECUTION", "run_id": args.run_id, "stage": stage, "artifact": artifact_rel, "fingerprint": fingerprint, "provider_call": "none"}


def mark_stage(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    with locked_run(path):
        return _mark_stage_locked(args, path)


def _mark_stage_locked(args, path: Path) -> dict:
    state = load_state(path)
    stage = normalize_stage(args.stage)
    record = state["stages"][stage]
    if record["status"] != "READY_FOR_EXECUTION":
        raise ContractError("STAGE_NOT_READY", stage)
    # W05 has no provider adapter. Only explicitly supplied local fixture artifacts
    # can close a stage until W06+ adds verified production receipts.
    if args.accept_fixture is None:
        raise ContractError("STAGE_EXECUTOR_NOT_IMPLEMENTED", "W05 records requests; no provider or fixture execution is implicit")
    fixture = safe_run_input(args.accept_fixture, path)
    record["status"] = "ACCEPTED"
    record["fixture_only"] = True
    record["request_artifact"] = record.get("artifact")
    record["artifact"] = {"path": fixture.relative_to(path).as_posix(), "sha256": sha(fixture.read_bytes())}
    state["updated_at"] = now()
    state["status"] = "RUNNING"
    save_state(path, state)
    return {"status": "FIXTURE_STAGE_ACCEPTED", "run_id": args.run_id, "stage": stage, "provider_call": "none"}


def show_run(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    state = load_state(path)
    return {"status": state["status"], "run_id": state["run_id"], "work_id": state["work_id"], "contract_sha256": state["contract_sha256"], "stages": {key: value["status"] for key, value in state["stages"].items()}, "provider_requests": len(state["provider_requests"])}


def review_run(args) -> dict:
    state = load_state(run_path(args.run_id, runs_root_for(args)))
    candidates = [name for name, record in state["stages"].items() if record["status"] == "READY_FOR_EXECUTION"]
    if not candidates:
        raise ContractError("REVIEW_CANDIDATE_MISSING", args.run_id)
    return {"status": "REVIEW_REQUIRED", "run_id": args.run_id, "ready_stages": candidates, "self_acceptance": False}


def promote_run(args) -> dict:
    state = load_state(run_path(args.run_id, runs_root_for(args)))
    if state["stages"].get("re-review", {}).get("status") != "ACCEPTED":
        raise ContractError("PROMOTION_GATE_NOT_ACCEPTED", "re-review")
    return {"status": "PROMOTION_READY", "run_id": args.run_id, "self_acceptance": False}


def export_run(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    state = load_state(path)
    if state["stages"].get("promote", {}).get("status") != "ACCEPTED":
        raise ContractError("EXPORT_GATE_NOT_ACCEPTED", "promote")
    return {"status": "EXPORT_READY", "run_id": args.run_id, "artifact_count": len(list((path / "artifacts").glob("*")))}


def sprint_run(args) -> dict:
    return {"status": "SPRINT_QUEUE_REQUIRED", "run_id": args.run_id, "provider_call": "none"}


def verify_history(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    state = load_state(path)
    for record in state["stages"].values():
        artifacts = [record.get("artifact"), record.get("request_artifact"), *[attempt.get("artifact") for attempt in record.get("invalidated_attempts", [])], *[attempt.get("request_artifact") for attempt in record.get("invalidated_attempts", [])]]
        for artifact in artifacts:
            if not artifact:
                continue
            target = assert_output_within_root(path, artifact["path"])
            if not target.is_file() or sha(target.read_bytes()) != artifact["sha256"]:
                raise ContractError("RUN_ARTIFACT_HASH_MISMATCH", artifact["path"])
    return {"status": "HISTORICAL_EVIDENCE_FOUND", "run_id": args.run_id, "provider_call": "none", "provider_requests": len(state["provider_requests"])}


def verify_live(args) -> dict:
    state = load_state(run_path(args.run_id, runs_root_for(args)))
    if not state["provider_requests"]:
        raise ContractError("LIVE_PROVIDER_EVIDENCE_MISSING", args.run_id)
    return {"status": "NEW_PROVIDER_CALL_PASSED", "run_id": args.run_id, "provider_requests": len(state["provider_requests"])}


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("produce")
    create.add_argument("--unit", choices=("scene", "episode"))
    create.add_argument("--contract", required=True)
    create.add_argument("--work-id")
    create.add_argument("--run-id", required=True)
    create.add_argument("--mode", choices=("offline", "live"), required=True)
    create.add_argument("--project-root")
    create.set_defaults(func=produce)
    run = sub.add_parser("step")
    run.add_argument("--run-id", required=True)
    run.add_argument("--work-id")
    run.add_argument("--stage", required=True)
    run.add_argument("--input")
    run.add_argument("--project-root")
    run.set_defaults(func=step)
    run = sub.add_parser("record-fixture")
    run.add_argument("--run-id", required=True)
    run.add_argument("--stage", required=True)
    run.add_argument("--accept-fixture", required=True)
    run.add_argument("--project-root")
    run.set_defaults(func=mark_stage)
    for command, func in (("show-run", show_run), ("resume", show_run), ("verify-history", verify_history), ("verify-live", verify_live)):
        item = sub.add_parser(command)
        item.add_argument("--run-id", required=True)
        item.add_argument("--project-root")
        item.set_defaults(func=func)
    for command, func in (("review", review_run), ("promote", promote_run), ("export", export_run), ("sprint", sprint_run)):
        item = sub.add_parser(command)
        item.add_argument("--run-id", required=True)
        item.add_argument("--project-root")
        item.set_defaults(func=func)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    result = args.func(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, ValueError) as exc:
        print(f"CNW_RUNNER_FAILED:{exc}", file=sys.stderr)
        raise SystemExit(2)
