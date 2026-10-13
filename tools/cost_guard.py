"""Project-bound access to the existing shared accounting primitives.

Resolving an account does not authorize a model request. Callers must perform
their production authorization before acquiring a slot or reserving costs.
No module-global configuration or ledger paths are changed here.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import hashlib
import inspect
import os
import uuid
from pathlib import Path

try:
    from . import p2_cost_guard as accounting
    from .cnw_contract import ContractError
    from .project_paths import _assert_no_reparse, resolve_project
except ImportError:
    import p2_cost_guard as accounting
    from cnw_contract import ContractError
    from project_paths import _assert_no_reparse, resolve_project


def _operation_file(run, relative):
    path = Path(relative)
    if path.is_absolute() or path.drive or ".." in path.parts:
        raise ContractError("COST_OPERATION_PATH_INVALID", "snapshot must belong to the operation")
    target = run / path
    _assert_no_reparse(target, code="COST_OPERATION_PATH_INVALID")
    if not target.is_file():
        raise ContractError("COST_OPERATION_SNAPSHOT_MISSING", relative)
    return target


def _operation_environment(root, kind, stage):
    try:
        from . import cnw_runner as runner, cnw_import_workflow as imports, cnw_maintenance as maintenance, cnw_operations as operations
        from .project_paths import _data_home_identity
    except ImportError:
        import cnw_runner as runner, cnw_import_workflow as imports, cnw_maintenance as maintenance, cnw_operations as operations
        from project_paths import _data_home_identity
    constructor = imports._run_import if kind == "imports" else maintenance._run
    operation = stage.removeprefix("project_")
    if kind == "imports":
        workflow = "02_incremental_update" if operation == "update" else "01_first_import"
        method_files = ["templates/CLAUDE.md", f"templates/_workflows/{workflow}.md",
            "templates/90_canon/canon.template.md", "templates/04_chapter_design/arc_index.template.md",
            "templates/90_canon/character_bible.template.md"]
        method_refs = {}
        for name in method_files:
            text, blob = imports._pinned_upstream(name)
            method_refs[name] = {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "git_blob": blob}
        for name in ("AGENTS.md", "CLAUDE.md"):
            path = root / name
            if path.is_file():
                method_refs["project:" + name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    else:
        _, method_sha256 = maintenance._method(root, operation)
        method_refs = {"method_sha256": method_sha256}
    if kind == "imports":
        consumers = (imports._run_import, imports._inventory, imports._record_classification,
            imports._apply, imports._verify_cached_operation, imports._reconsume_bookkeeping_response,
            imports._json, imports._confirmed_canon_sources, imports._document_allowed)
    else:
        consumers = (maintenance._run, maintenance._inventory, maintenance._method,
            maintenance._messages, maintenance._verify_receipt, maintenance._apply,
            maintenance._json, operations.identity)
    consumer_source = "\n".join(inspect.getsource(value) for value in consumers)
    consumer_source += "\n" + inspect.getsource(verify_cached_operation_receipt)
    return {"data_home_id": _data_home_identity(root.parent.parent, create=False),
        "project_identity_sha256": hashlib.sha256((root / "project_identity.json").read_bytes()).hexdigest(),
        "workflow_sha256": hashlib.sha256(runner.WORKFLOW_PATH.read_bytes()).hexdigest(),
        "constructor_sha256": hashlib.sha256(inspect.getsource(constructor).encode()).hexdigest(),
        "method_refs": method_refs,
        "consumer_sha256": hashlib.sha256(consumer_source.encode("utf-8")).hexdigest(),
        "transport_sha256": runner._operation_transport_identity(),
        "cost_policy": accounting._config_snapshot()[2]}


def _publish_operation_snapshot(path, raw):
    """Publish a complete new input snapshot without overwriting prior evidence."""
    temporary = path.with_name(path.name + ".attempt-" + uuid.uuid4().hex)
    with temporary.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if temporary.read_bytes() != raw:
        raise ContractError("COST_OPERATION_SNAPSHOT_WRITE_FAILED", "incomplete temporary input snapshot")
    os.link(temporary, path)  # Exclusive publication; failure retains the attempt.
    temporary.unlink()


def freeze_operation_account(run, *, stage, role_id, messages, output_cap, snapshots, extra=None):
    """Freeze accounting inputs at the real operation's request boundary.

    This grants neither Provider admission nor permission to publish outputs.
    Legacy operations retain their historical accounting route.
    """
    try:
        from . import cnw_runner as runner
    except ImportError:
        import cnw_runner as runner
    run = Path(run).absolute()
    _assert_no_reparse(run, code="COST_RUN_PATH_UNSAFE")
    state = runner.load_state(run)
    root = runner._operation_owner(run, state)
    if root is None:
        raise ContractError("COST_OPERATION_PATH_INVALID", "expected an operation Run")
    registration = runner._operation_project_registration(root)
    if registration is None:
        return
    snapshot_hashes = {name: hashlib.sha256(_operation_file(run, name).read_bytes()).hexdigest()
                       for name in snapshots}
    if not snapshot_hashes:
        raise ContractError("COST_OPERATION_SNAPSHOT_MISSING", "actual source snapshots required")
    kind = run.parent.name.casefold()
    value = {"schema": "cnw_operation_cost_v1", "project_id": registration["project_id"],
        "project_instance_id": registration["project_instance_id"], "run_id": run.name,
        "run_schema": state["schema_version"], "stage": stage, "role_id": role_id,
        "model": runner.MODEL, "api_url": runner.API_URL, "output_cap": output_cap,
        "messages": messages, "extra": extra, "snapshots": snapshot_hashes,
        "operation_kind": kind, "environment": _operation_environment(root, kind, stage)}
    value["request_fingerprint"] = runner.sha(json.dumps({"stage": stage, "role_id": role_id,
        "messages": messages, "output_cap": output_cap, "model": runner.MODEL,
        "url": runner.API_URL, "extra": extra}, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    relative = "artifacts/cost_operation.json"
    path = run / relative
    _assert_no_reparse(path, code="COST_OPERATION_PATH_INVALID")
    path.parent.mkdir(parents=True, exist_ok=True)
    with runner.locked_run(run):
        current = runner.load_state(run)
        digest = hashlib.sha256(raw).hexdigest()
        if (path.exists() and path.read_bytes() != raw) or current.get("cost_operation_sha256", digest) != digest:
            raise ContractError("COST_OPERATION_INPUT_CHANGED", "frozen operation inputs differ")
        if not path.exists():
            _publish_operation_snapshot(path, raw)
        if "cost_operation_sha256" not in current:
            current["cost_operation_sha256"] = digest
            runner.save_state(run, current)


def _operation_account(run, state, registration, *, stage, model):
    try:
        from . import cnw_runner as runner
    except ImportError:
        import cnw_runner as runner
    kind = run.parent.name.casefold()
    raw = _operation_file(run, "artifacts/cost_operation.json").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    value = json.loads(raw)
    expected = {"schema": "cnw_operation_cost_v1", "project_id": registration["project_id"],
        "project_instance_id": registration["project_instance_id"], "run_id": run.name,
        "run_schema": "cnw_import_run_v1" if kind == "imports" else "cnw_maintenance_run_v1",
        "operation_kind": kind, "stage": stage, "model": model, "api_url": runner.API_URL,
        "environment": _operation_environment(Path(registration["project_root"]), kind, stage)}
    if (state.get("run_id") != run.name or state.get("cost_operation_sha256") != digest
            or state.get("schema_version") != expected["run_schema"]
            or any(value.get(k) != v for k, v in expected.items())
            or not value.get("snapshots") or not value.get("messages")):
        raise ContractError("COST_OPERATION_BINDINGS_MISMATCH", "operation ownership or frozen request differs")
    for name, frozen in value["snapshots"].items():
        if hashlib.sha256(_operation_file(run, name).read_bytes()).hexdigest() != frozen:
            raise ContractError("COST_OPERATION_INPUT_CHANGED", name)
    frame = {"stage": value["stage"], "role_id": value["role_id"], "messages": value["messages"],
             "output_cap": value["output_cap"], "model": value["model"],
             "url": value["api_url"], "extra": value.get("extra")}
    fingerprint = hashlib.sha256(json.dumps(frame, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    if value.get("request_fingerprint") != fingerprint:
        raise ContractError("COST_OPERATION_REQUEST_MISMATCH", "frozen request fingerprint differs")
    context = accounting.CostContext(registration["project_instance_id"], registration["project_id"],
                                     run.name, stage, digest)
    context.record()
    return RunAccount(run, context, model)


@dataclass(frozen=True)
class RunAccount:
    run: Path
    context: accounting.CostContext
    model: str

    def provider_slot(self):
        return accounting.provider_slot()

    def verify_request(self, *, messages, role_id, output_cap, extra=None):
        if self.run.parent.name.casefold() in {"imports", "maintenance"}:
            value = json.loads(_operation_file(self.run, "artifacts/cost_operation.json").read_bytes())
            if (value.get("messages") != messages or value.get("role_id") != role_id
                    or value.get("output_cap") != output_cap or value.get("extra") != extra):
                raise ContractError("COST_OPERATION_REQUEST_MISMATCH", "actual request differs from frozen inputs")

    def command_reserve(self, args, *, emit=True):
        # Recheck source/contract/registration before any new reservation.
        current = for_run(self.run, stage=self.context.stage, model=self.model)
        if not isinstance(current, RunAccount) or current.context != self.context:
            raise ContractError("COST_BINDINGS_CHANGED", "run ownership changed before reservation")
        if not accounting.LEDGER.is_file():
            raise ContractError("COST_ACCOUNT_NOT_CONFIGURED", "generic calls require the configured shared account ledger")
        return accounting.command_reserve(args, emit=emit, context=self.context, expected_model=self.model)

    def command_settle(self, args, *, emit=True):
        # Settle against the original reservation even if source files changed
        # during HTTP. Rebinding here could strand a real incurred charge.
        return accounting.command_settle(args, emit=emit, context=self.context)

    def verify_receipt(self, receipt, *, ledger=None):
        _assert_no_reparse(accounting.LEDGER.absolute(), code="COST_LEDGER_PATH_UNSAFE")
        if ledger is None:
            ledger = accounting.read_ledger_snapshot()
        rows = [r for r in ledger["requests"] if r.get("request_id") == receipt.get("request_id")]
        if len(rows) != 1:
            raise ContractError("COST_RECEIPT_BINDING_MISMATCH", "expected one shared-account row")
        row = rows[0]
        verify_row(row, self, request_id=receipt.get("request_id"),
                   provider_request_id=receipt.get("provider_request_id"))
        settlement = receipt.get("ledger_settlement", {})
        if (row.get("status") != "SETTLED" or settlement.get("cost_context") != self.context.record()
                or settlement.get("estimated_request_cny") != row.get("estimated_actual_cny")
                or row.get("requested_model") != self.model or receipt.get("model") != self.model):
            raise ContractError("COST_RECEIPT_BINDING_MISMATCH", "receipt differs from reserved ownership or charge")


def verify_cached_operation_receipt(run, receipt, *, stage, role_id, output_cap, extra=None):
    """Revalidate frozen operation identity and the exact cached response before reuse."""
    try:
        from . import cnw_runner as runner
    except ImportError:
        import cnw_runner as runner
    account = for_run(run, stage=stage, model=runner.MODEL)
    if not isinstance(account, RunAccount):
        raise ContractError("COST_OPERATION_CONTEXT_NOT_READY", "registered operation has no frozen account")
    if runner._OPERATION_SIMULATION.get() is not None:
        runner._verify_operation_simulated_receipt(run, receipt, stage=stage, role_id=role_id,
            output_cap=output_cap, extra=extra)
        return account
    if receipt.get("mode") == "MOCK_ONLY":
        runner._verify_operation_simulated_receipt(run, receipt, stage=stage, role_id=role_id,
            output_cap=output_cap, extra=extra)
        return account
    if receipt.get("mode") != "LIVE" or receipt.get("fixture_only") is not False:
        raise ContractError("COST_RECEIPT_BINDING_MISMATCH", "cached operation mode is not an authenticated Live receipt")
    value = json.loads(_operation_file(Path(run), "artifacts/cost_operation.json").read_text(encoding="utf-8"))
    if (receipt.get("stage") != stage or receipt.get("role_id") != role_id
            or receipt.get("request_fingerprint") != value.get("request_fingerprint")):
        raise ContractError("COST_RECEIPT_BINDING_MISMATCH", "cached receipt differs from frozen operation request")
    account.verify_receipt(receipt)
    return account


def for_run(run_dir, *, stage, model, legacy_root=None):
    """Derive accounting ownership from a registered Run, or retain V1 routing."""
    run = Path(run_dir).absolute()
    _assert_no_reparse(run, code="COST_RUN_PATH_UNSAFE")
    run = run.resolve(strict=True)
    snapshot = run / "artifacts/contract.json"
    _assert_no_reparse(snapshot, code="COST_RUN_PATH_UNSAFE")
    contract = json.loads(snapshot.read_text(encoding="utf-8-sig")) if snapshot.is_file() else {}
    state_path = run / "run_state.json"
    _assert_no_reparse(state_path, code="COST_RUN_PATH_UNSAFE")
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    if (run.parent.name.casefold() in {"imports", "maintenance"} and run.parent.parent.name.casefold() == "94_runtime") or state.get("schema_version") in {"cnw_import_run_v1", "cnw_maintenance_run_v1"}:
        try:
            from . import cnw_runner as runner
        except ImportError:
            import cnw_runner as runner
        root = runner._operation_owner(run, state)
        registration = runner._operation_project_registration(root)
        if registration is not None:
            return _operation_account(run, state, registration, stage=stage, model=model)
    is_generic = (contract.get("schema_version") == "cnw_work_unit_v2"
        or state.get("literary_source_freeze_version") == "literary_source_freeze_v2"
        or state.get("schema_version") == "cnw_generic_sprint_v2")
    app_root = accounting.ROOT if legacy_root is None else Path(legacy_root)
    legacy_root = app_root / "workspace"
    legacy_runs = app_root / "runs"
    if not is_generic and (
            run.is_relative_to(legacy_root.resolve()) or run.is_relative_to(legacy_runs.resolve())):
        return accounting
    if run.parent.name != "runs":
        raise ContractError("COST_OPERATION_CONTEXT_NOT_READY", "this operation has no reviewed accounting binding adapter")
    root = run.parent.parent
    registration = resolve_project(root, data_home=root.parent.parent)
    if contract.get("schema_version") != "cnw_work_unit_v2":
        raise ContractError("COST_CONTRACT_REQUIRED", "registered production requires a frozen V2 contract")
    try:
        from .cnw_project import build_run_contract_preflight
    except ImportError:
        from cnw_project import build_run_contract_preflight
    report = build_run_contract_preflight(root, state["contract_path"], run_id=run.name)
    bindings = report["bindings"]
    if any(bindings[key] != registration[key] for key in ("project_id", "project_instance_id")):
        raise ContractError("COST_PROJECT_MISMATCH", "registration and frozen run disagree")
    context = accounting.CostContext(bindings["project_instance_id"], bindings["project_id"],
        run.name, stage, report["identity_sha256"])
    context.record()
    return RunAccount(run, context, model)


def verify_row(row, account, *, request_id, provider_request_id):
    """Verify attribution when reconsuming a real ledger row."""
    expected = account.context.record() if isinstance(account, RunAccount) else None
    if (row.get("cost_context") != expected or row.get("request_id") != request_id
            or row.get("provider_request_id") != provider_request_id):
        raise ContractError("COST_RECEIPT_BINDING_MISMATCH", "ledger row belongs to another operation")
    if expected is not None and row.get("run_id") != expected["run_id"]:
        raise ContractError("COST_RECEIPT_BINDING_MISMATCH", "ledger Run differs from its project context")
