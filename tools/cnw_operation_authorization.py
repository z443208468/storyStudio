"""Independent preflight and Owner grants for actual import/maintenance Runs.

These subjects have no chapter contract. Their existing frozen operation request,
snapshots, registered namespace and original shared account are the identity.
Unsigned preparation grants no model, publication or creative approval.
"""
from pathlib import Path
import json

try:
    from . import cnw_runner as runner, cnw_live_authorization as auth, cost_guard
    from .cnw_contract import ContractError, assert_output_within_root
    from .project_paths import _assert_no_reparse
except ImportError:
    import cnw_runner as runner, cnw_live_authorization as auth, cost_guard
    from cnw_contract import ContractError, assert_output_within_root
    from project_paths import _assert_no_reparse


def _frozen(run, *, ledger=None):
    run = Path(run).absolute()
    _assert_no_reparse(run, code="OPERATION_RUN_PATH_INVALID")
    run = run.resolve(strict=True)
    state = runner.load_state(run)
    root = runner._operation_owner(run, state)
    if root is None or runner._operation_project_registration(root) is None:
        raise ContractError("OPERATION_REGISTERED_RUN_REQUIRED", "select a real registered operation Run")
    raw = cost_guard._operation_file(run, "artifacts/cost_operation.json").read_bytes()
    value = json.loads(raw)
    _canonical_frame(run, value, ledger=ledger)
    account = cost_guard.for_run(run, stage=value["stage"], model=runner.MODEL)
    if not isinstance(account, cost_guard.RunAccount):
        raise ContractError("COST_OPERATION_CONTEXT_NOT_READY", "frozen registered accounting required")
    return run, root, state, value, raw, account


def _verified_cached_receipt(run, value, state, *, ledger=None):
    """Only this operation's one fee-backed, byte-backed success permits postimage reuse."""
    matches = [row for row in runner.cached_receipts(state)
               if row.get("status") == "SUCCEEDED"
               and row.get("request_fingerprint") == value["request_fingerprint"]]
    if not matches:
        return False
    if len(matches) != 1:
        raise ContractError("COST_RECEIPT_BINDING_MISMATCH", "operation needs one matching receipt")
    row = matches[0]
    if not isinstance(row.get("request_path"), str) or not row["request_path"]:
        raise ContractError("COST_RECEIPT_BINDING_MISMATCH", "cached request bytes are required")
    input_sha = runner.sha(json.dumps(value["messages"], ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":")).encode("utf-8"))
    if (row.get("stage") != value["stage"] or row.get("role_id") != value["role_id"]
            or row.get("input_sha256") != input_sha):
        raise ContractError("COST_RECEIPT_BINDING_MISMATCH", "cached request differs from frozen operation")
    account = cost_guard.for_run(run, stage=value["stage"], model=runner.MODEL)
    if not isinstance(account, cost_guard.RunAccount):
        raise ContractError("COST_OPERATION_CONTEXT_NOT_READY", "registered operation has no frozen account")
    account.verify_receipt(row, ledger=ledger)
    runner._receipt_content(run, row)
    request = json.loads(cost_guard._operation_file(run, row["request_path"]).read_bytes())
    if (request.get("messages") != value["messages"] or request.get("model") != runner.MODEL
            or request.get("max_tokens") != value["output_cap"]):
        raise ContractError("COST_RECEIPT_BINDING_MISMATCH", "cached wire request differs from frozen operation")
    return True


def _canonical_frame(run, value, *, ledger=None):
    """A signature cannot authorize a fabricated constructor/namespace/frame."""
    stage = value.get('stage')
    kind = run.parent.name.casefold()
    if kind == 'imports':
        try:
            from .cnw_import_workflow import IMPORT_OUTPUT_CAP
        except ImportError:
            from cnw_import_workflow import IMPORT_OUTPUT_CAP
        if stage not in {'project_import', 'project_update'}:
            raise ContractError('OPERATION_CONSTRUCTOR_MISMATCH', 'import namespace supports only import/update')
        role, cap = 'project_organization', IMPORT_OUTPUT_CAP
    elif kind == 'maintenance':
        try:
            from .cnw_maintenance import OUTPUT_CAPS
        except ImportError:
            from cnw_maintenance import OUTPUT_CAPS
        options = json.loads(value['messages'][1]['content'])['selection']
        operation = options.get('operation')
        if operation not in OUTPUT_CAPS or stage != 'project_' + operation:
            raise ContractError('OPERATION_CONSTRUCTOR_MISMATCH', 'maintenance stage must match selected operation')
        role, cap = stage, OUTPUT_CAPS[operation]
    else:
        raise ContractError('OPERATION_CONSTRUCTOR_MISMATCH', 'actual operation namespace required')
    if (value.get('operation_kind') != kind or value.get('role_id') != role or
            type(value.get('output_cap')) is not int or value['output_cap'] != cap or value.get('extra') is not None):
        raise ContractError('OPERATION_CONSTRUCTOR_MISMATCH', 'actual constructor fixes stage, role, cap and extras')
    state = runner.load_state(run)
    if not _verified_cached_receipt(run, value, state, ledger=ledger):
        if kind == 'imports':
            try:
                from .cnw_import_workflow import _describe_import
            except ImportError:
                from cnw_import_workflow import _describe_import
            current = _describe_import(run.parents[2], incremental=stage == 'project_update')
            current_run = current['run_dir'] if current is not None else None
        else:
            try:
                from .cnw_maintenance import _describe_operation
            except ImportError:
                from cnw_maintenance import _describe_operation
            current = _describe_operation(run.parents[2], options)
            current_run = current['run']
        if current is None or current_run != run or current['messages'] != value['messages']:
            raise ContractError('COST_OPERATION_INPUT_CHANGED', 'actual Run and full request must match the original constructor')


def authorization_path(run):
    # Namespace and physical root are also signed; same display Run IDs in two
    # kinds or installations cannot consume each other's grant.
    return assert_output_within_root(Path(run), "artifacts/live_authorization.json")


def build_request(run, *, _locked_ledger=None):
    run, root, state, value, raw, account = _frozen(run, ledger=_locked_ledger)
    sources, implementation = auth.implementation_identity()
    config, pricing, cost_policy = auth.accounting._config_snapshot()
    provider_path = runner.ROOT / "config/policies/provider_policy.deepseek_flash.v1.json"
    provider_raw = provider_path.read_bytes()
    provider = json.loads(provider_raw)
    if (config["model"] != runner.MODEL or provider["model"] != runner.MODEL
            or provider["base_url"].rstrip("/") + "/chat/completions" != runner.API_URL):
        raise ContractError("LIVE_AUTHORIZATION_PROVIDER_MISMATCH", "frozen operation and Provider configuration differ")
    bindings = {key: value[key] for key in ("project_id", "project_instance_id", "run_id", "run_schema",
        "operation_kind", "stage", "role_id", "output_cap", "snapshots", "environment", "request_fingerprint")}
    bindings.update(project_root=str(root), run_path=str(run), frozen_operation_sha256=auth._digest(raw))
    identity = auth.policy._canonical_sha256(bindings)
    request = {"schema_version": "cnw_operation_live_authorization_request_v1",
        "status": "AUTHORIZATION_PENDING", "bindings": bindings, "identity_sha256": identity,
        "implementation_sha256": implementation, "implementation_sources": sources,
        "provider": {"model": runner.MODEL, "api_url": runner.API_URL,
                     "provider_policy_sha256": auth._digest(provider_raw)},
        "cost_policy": cost_policy, "provider_call_authorized": False,
        "authorization_bundle_path": str(authorization_path(run)),
        "controller_payload": {"purpose": "CNW_OPERATION_PREFLIGHT", "decision": "ACCEPT",
            "bindings": bindings, "identity_sha256": identity, "implementation_sha256": implementation,
            "provider_call_authorized": False}}
    if (cost_guard._operation_file(run, "artifacts/cost_operation.json").read_bytes() != raw
            or provider_path.read_bytes() != provider_raw
            or auth.accounting._config_snapshot() != (config, pricing, cost_policy)):
        raise ContractError("LIVE_AUTHORIZATION_CHANGED_DURING_READ", "operation inputs changed")
    return request


def publish_request(run):
    try:
        from .cnw_native_pack import _immutable
    except ImportError:
        from cnw_native_pack import _immutable
    request = build_request(run)
    raw = auth.policy._canonical_bytes(request)
    relative = "artifacts/authorization_requests/" + auth._digest(raw) + ".json"
    path = assert_output_within_root(Path(run), relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    _immutable(path, raw)
    return {"status": "AUTHORIZATION_PENDING", "run_dir": str(Path(run).resolve()),
        "request_path": str(path), "request_sha256": auth._digest(raw),
        "bundle_path": request["authorization_bundle_path"], "provider_call_authorized": False}


def require_authorization(run, *, stage=None, _locked_ledger=None):
    request = build_request(run, _locked_ledger=_locked_ledger)
    actual_stage = request["bindings"]["stage"]
    if stage is not None and stage != actual_stage:
        raise ContractError("LIVE_GRANT_STAGE_FORBIDDEN", "grant belongs to the original operation")
    # Production cannot reconsume a test's simulated history after its physical
    # owner/context has ended, even with newly valid signatures.
    state = runner.load_state(Path(run))
    rows = runner.cached_receipts(state)
    try:
        from .cnw_test_live_transport import current_session
    except ImportError:
        from cnw_test_live_transport import current_session
    session = current_session()
    if session is not None:
        session.validate(run)
    if any(row.get("mode") != "LIVE" or row.get("fixture_only") is not False
           or row.get("simulation_status") == "SIMULATED" for row in rows):
        if session is None:
            raise ContractError("LIVE_SIMULATED_HISTORY_FORBIDDEN", "operation grant cannot turn simulated history into Live")
        session.history(run, rows, ledger=_locked_ledger)
    grant = auth._verify_bundle(request, authorization_path(run),
        rebuild=lambda: build_request(run, _locked_ledger=_locked_ledger),
        stage=actual_stage, allowed_stages={actual_stage}, owner_purpose="CNW_OPERATION_OWNER_LIVE_FEE_AUTHORIZATION")
    return dict(grant, authorization_route="SIGNED_OPERATION_LIVE")


def verify_request(run, *, stage, role_id, messages, output_cap, extra=None):
    grant = require_authorization(run, stage=stage)
    run, root, state, value, raw, account = _frozen(run)
    terms = grant["terms"]
    if role_id not in terms["roles"][stage]:
        raise ContractError("LIVE_GRANT_ROLE_FORBIDDEN", "operation role is outside the Owner scope")
    if (type(output_cap) is not int or not 1 <= output_cap <= terms["max_output_tokens"]
            or runner._estimate_input_tokens(messages) > terms["max_input_tokens"]):
        raise ContractError("LIVE_GRANT_TOKEN_LIMIT_EXCEEDED", "operation request exceeds signed limits")
    if any(value.get(key) != actual for key, actual in {
            "stage": stage, "role_id": role_id, "messages": messages, "output_cap": output_cap, "extra": extra}.items()):
        raise ContractError("COST_OPERATION_REQUEST_MISMATCH", "operation must consume its exact prepared request")
    # Before the first send, derive inputs using the same original constructor.
    # Subsequent reuse is possible only for the frozen successful receipt, with
    # the transaction's preimage/postimage validation still performed by caller.
    if not _verified_cached_receipt(run, value, state):
        if value["operation_kind"] == "imports":
            try:
                from .cnw_import_workflow import _describe_import
            except ImportError:
                from cnw_import_workflow import _describe_import
            current = _describe_import(root, incremental=stage == "project_update")
        else:
            try:
                from .cnw_maintenance import _describe_operation
            except ImportError:
                from cnw_maintenance import _describe_operation
            options = json.loads(messages[1]["content"])["selection"]
            current = _describe_operation(root, options)
        if current is None or current["messages"] != messages:
            raise ContractError("COST_OPERATION_INPUT_CHANGED", "current input no longer matches the signed preparation")
    return grant


def validate_reservation(run, *, stage, ledger, args, reserve, cost_snapshot):
    grant = require_authorization(run, stage=stage, _locked_ledger=ledger)
    return auth._validate_grant_reservation(grant, ledger=ledger, args=args,
                                           reserve=reserve, cost_snapshot=cost_snapshot)
