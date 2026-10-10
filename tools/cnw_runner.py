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
import math
import os
from pathlib import Path
import re
import sys
import time
import uuid
from decimal import Decimal, InvalidOperation, ROUND_CEILING

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


def _validate_raw_live_response(raw_path: Path, receipt: dict, usage: dict, index: int) -> None:
    try:
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        # Historical NK provider artifacts wrap the OpenAI-compatible body in an envelope.
        body = payload.get("response", payload) if isinstance(payload, dict) else None
        choices = body.get("choices") if isinstance(body, dict) else None
        raw_usage = body.get("usage") if isinstance(body, dict) else None
        if not choices or not isinstance(choices[0], dict) or not isinstance(raw_usage, dict):
            raise ValueError("missing response fields")
        outer_status = payload.get("status") if isinstance(payload, dict) else None
        outer_model = payload.get("requested_model") if isinstance(payload, dict) else None
        if outer_status is not None and outer_status != 200:
            raise ValueError("HTTP status mismatch")
        if outer_model is not None and outer_model != receipt["model"]:
            raise ValueError("requested model mismatch")
        if (body.get("id") != receipt["provider_request_id"] or body.get("model") != receipt["model"]
                or choices[0].get("finish_reason") != receipt["finish_reason"]
                or raw_usage.get("prompt_tokens") != usage["prompt_tokens"]
                or raw_usage.get("completion_tokens") != usage["completion_tokens"]):
            raise ValueError("raw response fields disagree with receipt")
        if payload.get("request_id") is not None and payload["request_id"] != receipt["request_id"]:
            raise ValueError("request id mismatch")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError, IndexError, AttributeError) as exc:
        raise ContractError("LIVE_RAW_RESPONSE_RECEIPT_MISMATCH", f"request {index}: {exc}") from exc


def _validate_review_call_coverage(receipts: list[dict]) -> None:
    expected = {
        "lens5": {"style", "character", "plot", "canon", "story_specific"},
        "verifier3": {"verifier_1", "verifier_2", "verifier_3"},
    }
    for stage, identities in expected.items():
        selected = [receipt for receipt in receipts if receipt.get("stage") == stage]
        field = "lens_id" if stage == "lens5" else "verifier_id"
        actual = [receipt.get(field) for receipt in selected]
        if (len(actual) != len(identities) or not all(isinstance(item, str) for item in actual)
                or set(actual) != identities):
            raise ContractError("LIVE_REVIEW_CALL_SET_INCOMPLETE", f"{stage}: expected {sorted(identities)}, got {actual}")


def bind_accepted_review_outputs(accepted_review:dict,provider_receipts:list[dict],run_root:Path)->None:
    expected_lenses={"style","character","plot","canon","story_specific"}; expected_verifiers={"verifier_1","verifier_2","verifier_3"}
    review_rows=accepted_review.get("provider_requests",[])
    lenses=[row for row in review_rows if row.get("stage")=="lens5"]; verifiers=[row for row in review_rows if row.get("stage")=="verifier3"]
    if len(lenses)!=5 or {row.get("lens_id") for row in lenses}!=expected_lenses or len(verifiers)!=3 or {row.get("verifier_id") for row in verifiers}!=expected_verifiers:
        raise ContractError("ACCEPTED_REVIEW_CALL_SET_INVALID","five lenses and three verifiers required")
    actual={(row.get("stage"),row.get("lens_id"),row.get("verifier_id"),row.get("provider_request_id")) for row in provider_receipts}
    expected={(row.get("stage"),row.get("lens_id"),row.get("verifier_id"),row.get("provider_request_id")) for row in review_rows}
    if not expected.issubset(actual): raise ContractError("ACCEPTED_REVIEW_PROVIDER_RECEIPTS_UNBOUND","review requests must belong to this verified run")
    receipt_by_id={row.get("provider_request_id"):row for row in provider_receipts}
    for review_receipt in verifiers:
        receipt=receipt_by_id[review_receipt["provider_request_id"]]
        raw_path=assert_output_within_root(run_root,receipt["raw_response_path"])
        try:
            raw_payload=json.loads(raw_path.read_text(encoding="utf-8")); body=raw_payload.get("response",raw_payload)
            content=body["choices"][0]["message"]["content"]
        except (OSError,UnicodeError,json.JSONDecodeError,KeyError,TypeError,IndexError) as exc:
            raise ContractError("ACCEPTED_VERIFIER_RAW_OUTPUT_INVALID",review_receipt.get("verifier_id","unknown")) from exc
        if review_receipt.get("response_content")!=content or review_receipt.get("output_sha256")!=sha(content.encode("utf-8")):
            raise ContractError("ACCEPTED_VERIFIER_OUTPUT_MISMATCH",review_receipt.get("verifier_id","unknown"))


def produce(args) -> dict:
    if args.mode == "live":
        raise ContractError("LIVE_EXECUTOR_NOT_AVAILABLE", "provider execution is gated for W10; W05 creates offline run state only")
    run_id = safe_run_id(args.run_id)
    unit_id = args.work_id or ""
    project_root = Path(args.project_root).resolve() if args.project_root else ROOT
    contract_file = Path(args.contract)
    if not contract_file.is_absolute():
        project_relative = project_root / contract_file
        contract_file = project_relative if project_relative.is_file() else ROOT / contract_file
    contract_candidate = contract_file.absolute()
    for ancestor in (contract_candidate, *contract_candidate.parents):
        if ancestor.is_symlink():
            raise ContractError("CONTRACT_PATH_UNSAFE", "contract path contains a symlink")
    contract_file = contract_file.resolve(strict=True)
    if not contract_file.is_relative_to(project_root):
        raise ContractError("CONTRACT_PATH_OUTSIDE_PROJECT", str(contract_file))
    contract = load_contract(contract_file)
    check_required_fields(contract)
    is_fixture = str(contract.get("project_id", "")).startswith("FICT_")
    private_workspace = (ROOT / "workspace").resolve()
    if not project_root.is_relative_to(private_workspace) and not is_fixture:
        raise ContractError("PROJECT_ROOT_OUTSIDE_PRIVATE_WORKSPACE", str(project_root))
    source = contract.get("source", {})
    if source.get("identity_type") == "imported_project":
        source_root = (project_root / source.get("source_root", ".")).resolve()
        if not source_root.is_relative_to(project_root):
            raise ContractError("SOURCE_PATH_UNSAFE", "import source root escapes the private project")
        validate_source_identity(contract, source_root=source_root, expected_version=source["version"], expected_zip_sha256=source["import_id"], expected_manifest_sha256=source["source_manifest_sha256"])
    elif not is_fixture:
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
    path = run_path(args.run_id, runs_root_for(args))
    state = load_state(path)
    candidate = state.get("editorial_candidate")
    if not candidate:
        raise ContractError("EDITORIAL_CANDIDATE_NOT_READY", "stage request artifacts are not a prose candidate")
    target = assert_output_within_root(path, candidate.get("path", ""))
    if not target.is_file() or sha(target.read_bytes()) != candidate.get("sha256"):
        raise ContractError("EDITORIAL_CANDIDATE_HASH_MISMATCH", args.run_id)
    return {"status": "READY_FOR_EDITORIAL_REVIEW", "run_id": args.run_id, "candidate": candidate, "review_evidence": "external_controller_or_author_required", "self_acceptance": False, "promote_allowed": False}


def register_editorial_candidate(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    with locked_run(path):
        state = load_state(path)
        if state.get("fixture_only") or state.get("mode") != "live":
            raise ContractError("MOCK_CANDIDATE_CANNOT_REQUEST_EDITORIAL_REVIEW", args.run_id)
        verify_live(args)
        target = safe_run_input(args.candidate, path)
        candidate = {"path": target.relative_to(path).as_posix(), "sha256": sha(target.read_bytes()), "status": "READY_FOR_EDITORIAL_REVIEW", "provider_evidence": "validated"}
        state["editorial_candidate"] = candidate
        state["status"] = "READY_FOR_EDITORIAL_REVIEW"
        state["updated_at"] = now()
        save_state(path, state)
        return {"status": "READY_FOR_EDITORIAL_REVIEW", "run_id": args.run_id, "candidate": candidate, "self_acceptance": False}


def promote_run(args) -> dict:
    path = run_path(args.run_id, runs_root_for(args))
    state = load_state(path)
    if state["stages"].get("re-review", {}).get("status") != "ACCEPTED":
        raise ContractError("PROMOTION_GATE_NOT_ACCEPTED", "re-review")
    candidate_arg=getattr(args,"candidate",None); evidence_arg=getattr(args,"review_evidence",None)
    if not candidate_arg or not evidence_arg:
        raise ContractError("EXTERNAL_REVIEW_EVIDENCE_REQUIRED", "supply --candidate and --review-evidence under this run")
    if state.get("mode") != "live" or state.get("fixture_only"):
        raise ContractError("MOCK_CANDIDATE_CANNOT_PROMOTE", args.run_id)
    verify_live(args)
    candidate_value=Path(candidate_arg); evidence_value=Path(evidence_arg)
    candidate=safe_run_input(candidate_value if candidate_value.is_absolute() else path/candidate_value,path)
    evidence_path=safe_run_input(evidence_value if evidence_value.is_absolute() else path/evidence_value,path)
    project_root=Path(getattr(args,"project_root",None) or ROOT).resolve(strict=True)
    contract_path=(project_root/state["contract_path"]).resolve(strict=True)
    if not contract_path.is_relative_to(project_root) or contract_path.is_symlink(): raise ContractError("CONTRACT_PATH_UNSAFE",state["contract_path"])
    contract=load_contract(contract_path)
    evidence=json.loads(evidence_path.read_text(encoding="utf-8"))
    accepted_review=evidence.get("accepted_review")
    if not isinstance(accepted_review,dict): raise ContractError("ACCEPTED_REVIEW_EVIDENCE_REQUIRED","promotion record must include the reviewed provider receipts")
    bind_accepted_review_outputs(accepted_review,state["provider_requests"],path)
    try:
        from .cnw_revision import promote_revision
    except ImportError:
        from cnw_revision import promote_revision
    result=promote_revision(project_root,path,candidate,contract,evidence)
    with locked_run(path):
        state=load_state(path)
        state["editorial_review"]={**evidence,"evidence_sha256":sha(evidence_path.read_bytes()),"candidate_path":candidate.relative_to(path).as_posix()}
        state["stages"]["promote"]["status"]="ACCEPTED"
        state["stages"]["promote"]["artifact"]={"path":candidate.relative_to(path).as_posix(),"sha256":sha(candidate.read_bytes())}
        state["updated_at"]=now(); state["status"]="PROMOTED"
        save_state(path,state)
    return {**result,"run_id":args.run_id,"self_acceptance":False}


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
    run_root = run_path(args.run_id, runs_root_for(args))
    state = load_state(run_root)
    if not state["provider_requests"]:
        raise ContractError("LIVE_PROVIDER_EVIDENCE_MISSING", args.run_id)
    if any(receipt.get("mode") == "MOCK_ONLY" or receipt.get("fixture_only") is True for receipt in state["provider_requests"]):
        raise ContractError("MOCK_RECEIPT_CANNOT_PROVE_LIVE", args.run_id)
    pipeline = ["plot", "cards", "brief"]
    if state["unit_kind"] == "scene":
        pipeline.append("pov")
    pipeline += ["draft", "lint1", "lint2", "lens5", "verifier3", "completeness", "refine", "re-review"]
    receipts_by_stage = {}
    for receipt in state["provider_requests"]:
        stage = receipt.get("stage")
        if stage not in pipeline:
            raise ContractError("LIVE_PIPELINE_INCOMPLETE", f"unexpected stage: {stage}")
        receipts_by_stage.setdefault(stage, []).append(receipt)
    multi_call_stages = {"lens5", "verifier3"}
    missing_stages = [stage for stage in pipeline if stage not in receipts_by_stage or state["stages"].get(stage, {}).get("status") != "ACCEPTED"]
    duplicate_stages = [stage for stage, stage_receipts in receipts_by_stage.items() if stage not in multi_call_stages and len(stage_receipts) != 1]
    if duplicate_stages:
        raise ContractError("LIVE_PIPELINE_INCOMPLETE", f"duplicate stages: {', '.join(duplicate_stages)}")
    if missing_stages:
        raise ContractError("LIVE_PIPELINE_INCOMPLETE", ", ".join(missing_stages))
    _validate_review_call_coverage(state["provider_requests"])
    required = {"stage", "request_id", "provider_request_id", "model", "status", "http_status", "finish_reason", "usage", "input_sha256", "output_sha256", "raw_response_path", "raw_response_sha256", "cost_cny", "ledger_settlement"}
    seen_provider_ids = set()
    seen_request_ids = set()
    ledger_path = ROOT / "runtime/private/p2-cost-ledger.json"
    if ledger_path.is_symlink() or not ledger_path.is_file():
        raise ContractError("LIVE_COST_LEDGER_MISSING", str(ledger_path))
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("LIVE_COST_LEDGER_INVALID", str(exc)) from exc
    for index, receipt in enumerate(state["provider_requests"], 1):
        if receipt.get("mode") == "MOCK_ONLY" or receipt.get("fixture_only") is True:
            raise ContractError("MOCK_RECEIPT_CANNOT_PROVE_LIVE", f"request {index}")
        missing = sorted(required - set(receipt))
        if missing:
            raise ContractError("LIVE_RECEIPT_INCOMPLETE", f"request {index} missing {', '.join(missing)}")
        if not all(isinstance(receipt.get(key), str) and receipt[key].strip() for key in ("stage", "request_id", "provider_request_id")):
            raise ContractError("LIVE_RECEIPT_IDENTITY_INVALID", f"request {index}")
        role_field = "lens_id" if receipt["stage"] == "lens5" else "verifier_id" if receipt["stage"] == "verifier3" else None
        if role_field and (not isinstance(receipt.get(role_field), str) or not receipt[role_field].strip()):
            raise ContractError("LIVE_RECEIPT_IDENTITY_INVALID", f"request {index} missing {role_field}")
        if receipt["provider_request_id"] in seen_provider_ids or receipt["request_id"] in seen_request_ids:
            raise ContractError("LIVE_PROVIDER_REQUEST_ID_DUPLICATE", receipt["provider_request_id"])
        seen_provider_ids.add(receipt["provider_request_id"])
        seen_request_ids.add(receipt["request_id"])
        if receipt["status"] != "SUCCEEDED" or receipt["http_status"] != 200 or receipt["model"] != "deepseek-flash" or receipt["finish_reason"] != "stop":
            raise ContractError("LIVE_RECEIPT_STATUS_INVALID", f"request {index}")
        usage = receipt["usage"]
        if not isinstance(usage, dict) or not all(isinstance(usage.get(key), int) and usage[key] > 0 for key in ("prompt_tokens", "completion_tokens")):
            raise ContractError("LIVE_USAGE_MISSING", f"request {index}")
        if not all(re.fullmatch(r"[0-9a-fA-F]{64}", str(receipt[key])) for key in ("input_sha256", "output_sha256", "raw_response_sha256")):
            raise ContractError("LIVE_RECEIPT_HASH_INVALID", f"request {index}")
        raw_response = assert_output_within_root(run_root, receipt["raw_response_path"])
        if not raw_response.is_file() or sha(raw_response.read_bytes()) != receipt["raw_response_sha256"].lower():
            raise ContractError("LIVE_RAW_RESPONSE_HASH_MISMATCH", f"request {index}")
        _validate_raw_live_response(raw_response, receipt, usage, index)
        if not isinstance(receipt["cost_cny"], (int, float)) or isinstance(receipt["cost_cny"], bool) or not math.isfinite(receipt["cost_cny"]) or receipt["cost_cny"] < 0:
            raise ContractError("LIVE_COST_MISSING", f"request {index}")
        settlement = receipt["ledger_settlement"]
        if not isinstance(settlement, dict) or settlement.get("status") != "SETTLED" or settlement.get("request_id") != receipt["request_id"]:
            raise ContractError("LIVE_COST_NOT_SETTLED", f"request {index}")
        rows = [row for row in ledger.get("requests", []) if row.get("request_id") == receipt["request_id"]]
        if len(rows) != 1:
            raise ContractError("LIVE_COST_LEDGER_ROW_MISSING", receipt["request_id"])
        row = rows[0]
        usage_matches = row.get("usage") == {"input_tokens": usage["prompt_tokens"], "output_tokens": usage["completion_tokens"]}
        try:
            settled_cost = Decimal(str(row.get("estimated_actual_cny")))
            receipt_cost = Decimal(str(receipt["cost_cny"])).quantize(Decimal("0.000001"), rounding=ROUND_CEILING)
        except (InvalidOperation, ValueError):
            raise ContractError("LIVE_COST_MISSING", f"request {index}")
        if row.get("status") != "SETTLED" or row.get("provider_request_id") != receipt["provider_request_id"] or row.get("finish_reason") != "stop" or not usage_matches or settled_cost != receipt_cost:
            raise ContractError("LIVE_COST_SETTLEMENT_MISMATCH", f"request {index}")
    return {"status": "LIVE_EVIDENCE_VALIDATED", "run_id": args.run_id, "provider_requests": len(state["provider_requests"]), "all_receipts_settled": True}


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
    candidate = sub.add_parser("register-candidate")
    candidate.add_argument("--run-id", required=True)
    candidate.add_argument("--candidate", required=True)
    candidate.add_argument("--project-root")
    candidate.set_defaults(func=register_editorial_candidate)
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
        if command=="promote":
            item.add_argument("--candidate")
            item.add_argument("--review-evidence")
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
