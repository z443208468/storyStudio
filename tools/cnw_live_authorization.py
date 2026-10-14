"""Separate signed preflight and owner spending grants for registered V2 Runs.

No trust roots, keys or permissions are installed here. Production verification
uses the existing deployment-owned trust loader. Requests are read-only reports;
they grant neither Provider access nor manuscript/Canon approval.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

try:
    from .cnw_contract import ContractError
    from . import cnw_project, cnw_w10_policy as policy, p2_cost_guard as accounting
    from .project_paths import _assert_no_reparse
    from .policy_snapshots import resolve_policy_by_sha
except ImportError:
    from cnw_contract import ContractError
    import cnw_project
    import cnw_w10_policy as policy
    import p2_cost_guard as accounting
    from project_paths import _assert_no_reparse
    from policy_snapshots import resolve_policy_by_sha

SCHEMA = "cnw_live_authorization_bundle_v1"
AUXILIARY_SCOPES = {"support_hook": ("writing_brief", "nk", "nk_pov"),
    "critics_plot": ("plot", "critics", "critics_plot"),
    "critics_text": ("refine", "critics", "critics_text")}
PROVIDER_STAGES = frozenset({"plot", "scene_cards", "writing_brief", "prose",
    "lint_layer2", "multi_lens_review", "adversarial_verify", "completeness_critic",
    "refine", "re_review", *AUXILIARY_SCOPES})
STAGE_ALIASES = {"cards": "scene_cards", "brief": "writing_brief", "draft": "prose",
    "lens5": "multi_lens_review", "verifier3": "adversarial_verify", "completeness": "completeness_critic",
    "re-review": "re_review"}


def _runner():
    try:
        from . import cnw_runner
    except ImportError:
        import cnw_runner
    return cnw_runner


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def authorization_path(project, run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", run_id):
        raise ContractError("VALID_RUN_ID_REQUIRED", "authorization needs a legal Run ID")
    path = Path(project) / "08_review/live_authorizations" / (run_id + ".json")
    _assert_no_reparse(path.absolute(), code="LIVE_AUTHORIZATION_PATH_UNSAFE")
    return path


def implementation_identity():
    runner = _runner()
    code_names = ("cnw_live_authorization", "cnw_runner", "cnw_recovery", "cnw_roles", "cnw_review",
        "cnw_contract", "cnw_project", "cnw_input_pack", "cnw_native_pack", "cnw_task_requirements",
        "cnw_nk_adapter", "cnw_critics_adapter", "cnw_live_provider", "cnw_live_executor",
        "cnw_w10_policy", "controller_trust_loader", "cost_guard", "p2_cost_guard",
        "cnw_pack_app", "cnw_request_identity", "cnw_test_live_transport", "policy_snapshots",
        "cnw_generate", "cnw_revision", "cnw_export", "cnw_operation_authorization",
        "cnw_import_workflow", "cnw_maintenance", "cnw_operations",
        "p2_06_critics_run", "critics_bridge", "project_paths", "project_transactions")
    code_sources = {name + ".py": _digest((runner.ROOT / "tools" / (name + ".py")).read_bytes()) for name in code_names}
    code_sources['studio.ps1'] = _digest((runner.ROOT/'tools/studio.ps1').read_bytes())
    code_sources['nk-live-fetch.cjs'] = _digest((runner.ROOT/'tools/nk-live-fetch.cjs').read_bytes())
    for name in runner.STAGE_PROMPTS.values():
        code_sources["prompts/cnw/" + name] = _digest((runner.PROMPT_ROOT / name).read_bytes())
    code_sources["MASTER_PLAN_GENERIC_APP_R5.md"] = _digest((runner.ROOT / "plans/MASTER_PLAN_GENERIC_APP_R5.md").read_bytes())
    implementation_sha = policy._canonical_sha256(code_sources)
    return code_sources, implementation_sha


def build_request(project, contract_path, *, run_id):
    """Bind the same inputs before creation and throughout the actual Run."""
    runner = _runner()
    root = Path(project).resolve(strict=True)
    provider_file = runner.ROOT / "config/policies/provider_policy.deepseek_flash.v1.json"
    provider_raw, workflow_raw = provider_file.read_bytes(), runner.WORKFLOW_PATH.read_bytes()
    provider = resolve_policy_by_sha(_digest(provider_raw), expected_kind="provider_policy")
    run = root / "runs" / run_id
    if run.exists():
        # This report already recomputes the complete preflight before and
        # after validating the frozen Run. Do not add a third computation.
        actual = cnw_project.build_run_contract_preflight(root, contract_path, run_id=run_id)
        bindings = dict(actual["bindings"])
        if (bindings["workflow_template_sha256"] != _digest(workflow_raw)
                or bindings["provider_policy_sha256"] != provider["sha256"]):
            raise ContractError("LIVE_AUTHORIZATION_BINDING_MISMATCH", "Run and current Provider/Workflow bindings differ")
    else:
        planned = cnw_project._compute_contract_preflight(root, contract_path,
            run_id=run_id, existing_run=False)
        contract_file = Path(contract_path)
        contract_file = (contract_file if contract_file.is_absolute() else root / contract_file).resolve(strict=True)
        contract = json.loads(contract_file.read_bytes())
        bindings = {key: planned[key] for key in ("project_id", "project_instance_id", "run_id", "work_id",
            "contract_sha256", "work_intent", "source_identity", "source_root_identity", "selected_scope_sha256",
            "policy_version", "plot_request_sha256", "production_preparation_hashes")}
        bindings.update(workflow_template_sha256=_digest(workflow_raw), provider_policy_sha256=provider["sha256"],
                        literary_source_freeze=runner.literary_source_freeze(contract, root))
    guard, pricing, cost_snapshot = accounting._config_snapshot()
    settings = provider["document"] if "document" in provider else json.loads(provider_raw)
    if (settings["model"] != runner.MODEL or guard["model"] != runner.MODEL
            or runner.API_URL != settings["base_url"].rstrip("/") + "/chat/completions"):
        raise ContractError("LIVE_AUTHORIZATION_PROVIDER_MISMATCH", "actual transport and frozen Provider policy differ")
    if (provider_file.read_bytes() != provider_raw or runner.WORKFLOW_PATH.read_bytes() != workflow_raw
            or accounting._config_snapshot() != (guard, pricing, cost_snapshot)):
        raise ContractError("LIVE_AUTHORIZATION_CHANGED_DURING_READ", "Provider or fee policy changed")
    identity = policy._canonical_sha256(bindings)
    code_sources, implementation_sha = implementation_identity()
    return {"schema_version": "cnw_live_authorization_request_v1", "status": "AUTHORIZATION_PENDING",
        "bindings": bindings, "identity_sha256": identity,
        "implementation_sha256": implementation_sha, "implementation_sources": code_sources,
        "provider": {"model": runner.MODEL, "api_url": runner.API_URL,
                     "provider_policy_sha256": provider["sha256"]},
        "cost_policy": cost_snapshot, "provider_call_authorized": False,
        "authorization_bundle_path": str(authorization_path(root, run_id)),
        "controller_payload": {"purpose": "CNW_V2_RUN_PREFLIGHT", "decision": "ACCEPT",
            "bindings": bindings, "identity_sha256": identity, "implementation_sha256": implementation_sha,
            "provider_call_authorized": False}}


def _terms(value, *, allowed_stages=PROVIDER_STAGES):
    if not isinstance(value, dict) or set(value) != {"not_before", "expires_at", "max_requests",
            "max_input_tokens", "max_output_tokens", "limit_cny", "stages", "roles"}:
        raise ContractError("LIVE_GRANT_TERMS_INVALID", "explicit lifetime, stages and finite spending limits are required")
    for key in ("max_requests", "max_input_tokens", "max_output_tokens"):
        if type(value[key]) is not int or value[key] <= 0:
            raise ContractError("LIVE_GRANT_TERMS_INVALID", "positive integer request and token limits are required")
    limit = value["limit_cny"]
    if not isinstance(limit, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,6})?", limit) or Decimal(limit) <= 0:
        raise ContractError("LIVE_GRANT_TERMS_INVALID", "finite positive CNY limit is required")
    stages = value["stages"]
    if (not isinstance(stages, list) or not stages or any(not isinstance(s, str) for s in stages)
            or len(set(stages)) != len(stages) or not set(stages) <= allowed_stages):
        raise ContractError("LIVE_GRANT_TERMS_INVALID", "grant stages must be distinct supported CNW Provider stages")
    roles = value["roles"]
    if not isinstance(roles, dict) or set(roles) != set(stages):
        raise ContractError("LIVE_GRANT_TERMS_INVALID", "each authorized stage needs explicit role scope")
    for permitted in roles.values():
        if (not isinstance(permitted, list) or not permitted
                or any(role is not None and (not isinstance(role, str) or not re.fullmatch(r"[a-z0-9_]{1,64}", role)) for role in permitted)
                or len(set(permitted)) != len(permitted)):
            raise ContractError("LIVE_GRANT_TERMS_INVALID", "roles must be explicit distinct role IDs")
    for hook, (parent, _, role) in AUXILIARY_SCOPES.items():
        if hook in stages and (parent not in stages or roles[hook] != [role]):
            raise ContractError("LIVE_GRANT_TERMS_INVALID", "auxiliary grant needs its parent stage and exact role")
    try:
        start, end = (datetime.fromisoformat(value[key].replace("Z", "+00:00")) for key in ("not_before", "expires_at"))
        if start.utcoffset() is None or end.utcoffset() is None or start >= end:
            raise ValueError("invalid lifetime")
    except (AttributeError, TypeError, ValueError) as exc:
        raise ContractError("LIVE_GRANT_TERMS_INVALID", "explicit timezone and ordered lifetime are required") from exc
    current = datetime.now(timezone.utc)
    if not start <= current < end:
        raise ContractError("LIVE_GRANT_EXPIRED", "owner grant is not currently valid")
    return value


class _OwnerVerifier:
    """The deployment must explicitly recognize the owner-authority role."""
    def __init__(self, deployment):
        self.deployment = deployment

    def verify(self, signer_id, message, signature):
        verify = getattr(self.deployment, "verify_owner_authorization", None)
        if not callable(verify):
            raise ContractError("W10_ATTESTATION_PENDING", "deployment has no independent owner-authorization verifier")
        return verify(signer_id, message, signature)


def require_authorization(project, contract_path, *, run_id, stage=None):
    """Recompute real bindings and verify both signatures; never change a flag."""
    request = build_request(project, contract_path, run_id=run_id)
    path = authorization_path(project, run_id)
    return _verify_bundle(request, path, rebuild=lambda: build_request(project, contract_path, run_id=run_id),
                          stage=stage)


def _verify_bundle(request, path, *, rebuild, stage=None, allowed_stages=PROVIDER_STAGES,
                   owner_purpose="CNW_OWNER_LIVE_FEE_AUTHORIZATION"):
    """Shared detached-signature checks; the caller supplies the actual subject."""
    if not path.is_file():
        raise ContractError("LIVE_AUTHORIZATION_REQUIRED", "independent preflight and owner Live/fee grant are required")
    value, raw = policy._read_json(path, "LIVE_AUTHORIZATION_INVALID")
    if (value.get("schema_version") != SCHEMA or set(value) != {"schema_version", "controller", "owner", "terms"}):
        raise ContractError("LIVE_AUTHORIZATION_INVALID", "a scoped signed authorization bundle is required")
    terms = _terms(value["terms"], allowed_stages=allowed_stages)
    if stage is not None and stage not in terms["stages"]:
        raise ContractError("LIVE_GRANT_STAGE_FORBIDDEN", stage)
    deployment = policy._deployment_attestation_verifier()
    # Reuse the detached document checker with no caller-selected paths. Each
    # signature is a real external file with a byte hash in this fixed bundle.
    def check(ref, payload, verifier):
        if not isinstance(ref, dict) or set(ref) != {"path", "sha256"}:
            raise ContractError("LIVE_AUTHORIZATION_INVALID", "signed document path and SHA are required")
        signed = Path(ref["path"])
        if not signed.is_absolute() or not policy._no_reparse(signed) or not signed.is_file():
            raise ContractError("LIVE_AUTHORIZATION_PATH_UNSAFE", "signed documents must be explicit safe paths")
        signed_raw = signed.read_bytes()
        if _digest(signed_raw) != ref["sha256"]:
            raise ContractError("LIVE_AUTHORIZATION_SIGNATURE_MISMATCH", "signed document changed")
        doc, digest = policy.verify_controller_attestation_document(signed, expected_payload=payload, verifier=verifier)
        if signed.read_bytes() != signed_raw or digest != ref["sha256"]:
            raise ContractError("LIVE_AUTHORIZATION_CHANGED_DURING_READ", "signed document changed during validation")
        return doc
    controller = check(value["controller"], request["controller_payload"], deployment)
    owner_payload = {"purpose": owner_purpose, "decision": "AUTHORIZE",
        "bindings": request["bindings"], "identity_sha256": request["identity_sha256"],
        "implementation_sha256": request["implementation_sha256"],
        "provider": request["provider"], "cost_policy": request["cost_policy"], "terms": terms}
    owner = check(value["owner"], owner_payload, _OwnerVerifier(deployment))
    if controller["signer_id"] == owner["signer_id"]:
        raise ContractError("LIVE_AUTHORIZATION_ROLES_NOT_INDEPENDENT", "engineering preflight and owner grant require distinct authorities")
    if path.read_bytes() != raw or rebuild() != request:
        raise ContractError("LIVE_AUTHORIZATION_CHANGED_DURING_READ", "authorization or bound inputs changed")
    # Signature and binding reconstruction can outlast the grant. Check the
    # same signed terms again at the point where permission would be returned.
    _terms(terms, allowed_stages=allowed_stages)
    return {"status": "LIVE_AND_FEES_AUTHORIZED", "bindings": request["bindings"],
        "identity_sha256": request["identity_sha256"], "bundle_sha256": _digest(raw),
        "owner_grant_sha256": value["owner"]["sha256"], "terms": terms,
        "provider": request["provider"], "cost_policy": request["cost_policy"]}


def require_run_authorization(run, *, stage, _locked_ledger=None):
    runner = _runner()
    run = Path(run).resolve(strict=True)
    state = runner.load_state(run)
    if state.get("mode") != "live" or state.get("fixture_only") is not False:
        raise ContractError("OFFLINE_PROVIDER_FORBIDDEN", "only a real Live Run can consume an owner grant")
    try:
        from .cnw_test_live_transport import current_session
    except ImportError:
        from cnw_test_live_transport import current_session
    session = current_session()
    if session is not None:
        session.validate(run)
    rows = runner.cached_receipts(state)
    if any(row.get("mode") != "LIVE" or row.get("fixture_only") is not False
            or row.get("simulation_status") == "SIMULATED" for row in rows):
        if session is None:
            raise ContractError("LIVE_SIMULATED_HISTORY_FORBIDDEN", "Live authorization cannot convert simulated receipts")
        session.history(run, rows, ledger=_locked_ledger)
    try:
        from .cnw_critics_adapter import read_native_support_records
        from .cnw_recovery import iter_native_support_records
    except ImportError:
        from cnw_critics_adapter import read_native_support_records
        from cnw_recovery import iter_native_support_records
    records = []
    for name, hook in iter_native_support_records(state):
        artifact = hook.get("input_artifact", {})
        if not hook.get("run_dir") or not artifact.get("path"):
            raise ContractError("CRITICS_NATIVE_RUN_IDENTITY_MISSING", name)
        input_path = runner.assert_output_within_root(run, artifact["path"])
        if not input_path.is_file() or _digest(input_path.read_bytes()) != artifact.get("sha256"):
            raise ContractError("CRITICS_INPUT_CHANGED", name)
        records.append((name, hook, input_path))
    for name, hook, actual in read_native_support_records(run, records, ledger=_locked_ledger):
        if actual.get("mode") == "MOCK_ONLY" and session is None:
            raise ContractError("LIVE_SIMULATED_HISTORY_FORBIDDEN", "native support cannot authorize Live")
    stage = STAGE_ALIASES.get(stage, stage)
    grant = require_authorization(run.parent.parent, state["contract_path"], run_id=run.name,
                                  stage=stage)
    if stage in AUXILIARY_SCOPES:
        parent, integration, _ = AUXILIARY_SCOPES[stage]
        contract = runner._contract_for(run)
        if runner._support_integration_mode(contract, integration) != "ENABLED":
            raise ContractError("LIVE_AUXILIARY_DISABLED", "unused support hook cannot consume an owner grant")
        required = {"support_hook": ("scene_cards",), "critics_plot": ("plot",),
                    "critics_text": ("prose", "completeness_critic")}[stage]
        for predecessor in required:
            runner._read_stage_text(run, state, predecessor)
        if parent not in grant["terms"]["stages"]:
            raise ContractError("LIVE_GRANT_STAGE_FORBIDDEN", parent)
    return grant


def verify_auxiliary_native_input(run, *, stage, action, input_path):
    """Check the actual CritiCS child input against the parent Run before fees."""
    if stage not in {"critics_plot", "critics_text"}:
        raise ContractError("LIVE_AUXILIARY_STAGE_INVALID", str(stage))
    required_action = "plan-critique" if stage == "critics_plot" else "text-refine"
    if action != required_action:
        raise ContractError("LIVE_AUXILIARY_ACTION_MISMATCH", str(action))
    run = Path(run).resolve(strict=True)
    require_run_authorization(run, stage=stage)
    runner = _runner()
    state = runner.load_state(run)
    if stage == "critics_plot":
        runner._read_stage_text(run, state, "plot")
        artifact = state["stages"]["plot"]["artifact"]
        raw = runner.assert_output_within_root(run, artifact["path"]).read_bytes()
    else:
        selection = runner._critics_excerpt_selection(run, state)
        if selection is None:
            raise ContractError("CRITICS_INPUT_MISSING", "current findings have no relevant excerpt")
        raw = selection[0].encode("utf-8")
    digest = _digest(raw)
    expected = run / "artifacts/support" / ("critics-input-" + digest + ".md")
    supplied = Path(input_path).absolute()
    _assert_no_reparse(supplied, code="CRITICS_INPUT_PATH_UNSAFE")
    if (not expected.is_file() or supplied.resolve(strict=True) != expected.resolve(strict=True)
            or expected.read_bytes() != raw):
        raise ContractError("CRITICS_INPUT_CHANGED", "native child input differs from the current parent material")
    return {"parent_run_id": run.name, "hook": stage, "action": action,
            "input_sha256": digest}


def verify_request(run, *, stage, role_id, messages, output_cap, extra=None):
    """Validate actual request scope before slot/cache/Key and again in slot."""
    runner = _runner()
    stage = STAGE_ALIASES.get(stage, stage)
    grant = require_run_authorization(run, stage=stage)
    terms = grant["terms"]
    if role_id not in terms["roles"][stage]:
        raise ContractError("LIVE_GRANT_ROLE_FORBIDDEN", "actual role is outside the owner grant")
    if (type(output_cap) is not int or not 1 <= output_cap <= terms["max_output_tokens"]
            or runner._estimate_input_tokens(messages) > terms["max_input_tokens"]):
        raise ContractError("LIVE_GRANT_TOKEN_LIMIT_EXCEEDED", "actual request exceeds signed token limits")
    state = runner.load_state(Path(run))
    for predecessor in runner.stage_predecessors(stage):
        if not isinstance(state['stages'].get(predecessor, {}).get('artifact'), dict):
            raise ContractError('LIVE_REQUEST_PREDECESSOR_NOT_READY', predecessor)
        runner._read_stage_text(Path(run), state, predecessor)
    try:
        from .cnw_request_identity import expected_requests
    except ImportError:
        from cnw_request_identity import expected_requests
    actual = {"stage": stage, "role_id": role_id, "messages": messages, "output_cap": output_cap, "extra": extra}
    expected = expected_requests(Path(run), stage=stage, role_id=role_id)
    if not any(policy._canonical_bytes(actual) == policy._canonical_bytes(call) for call in expected):
        raise ContractError("LIVE_REQUEST_BINDING_MISMATCH", "request must match the actual CNW role, inputs and bounded variant")
    return grant


def publish_request(project, contract_path, *, run_id):
    """Persist an unsigned content-addressed request for independent authorities."""
    request = build_request(project, contract_path, run_id=run_id)
    raw = policy._canonical_bytes(request)
    directory = authorization_path(project, run_id).parent / "requests"
    _assert_no_reparse(directory.absolute(), code="LIVE_AUTHORIZATION_PATH_UNSAFE")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (_digest(raw) + ".json")
    _assert_no_reparse(target.absolute(), code="LIVE_AUTHORIZATION_PATH_UNSAFE")
    try:
        from .cnw_native_pack import _immutable
    except ImportError:
        from cnw_native_pack import _immutable
    _immutable(target, raw)
    return {"status": "AUTHORIZATION_PENDING", "request_path": str(target),
            "request_sha256": _digest(raw), "bundle_path": request["authorization_bundle_path"],
            "provider_call_authorized": False}


def validate_reservation(run, *, stage, ledger, args, reserve, cost_snapshot):
    """Called under the original shared ledger lock before appending a row."""
    grant = require_run_authorization(run, stage=stage, _locked_ledger=ledger)
    return _validate_grant_reservation(grant, ledger=ledger, args=args, reserve=reserve,
                                       cost_snapshot=cost_snapshot)


def _validate_grant_reservation(grant, *, ledger, args, reserve, cost_snapshot):
    """Use the same stable instance/Run spending attribution for both subjects."""
    if cost_snapshot != grant["cost_policy"]:
        raise ContractError("LIVE_GRANT_COST_POLICY_CHANGED", "accounting and grant policies differ")
    terms, bindings = grant["terms"], grant["bindings"]
    if args.input_token_cap > terms["max_input_tokens"] or args.output_token_cap > terms["max_output_tokens"]:
        raise ContractError("LIVE_GRANT_TOKEN_LIMIT_EXCEEDED", "actual request exceeds signed token limits")
    rows = [row for row in ledger["requests"] if
        row.get("cost_context", {}).get("project_instance_id") == bindings["project_instance_id"]
        and row.get("cost_context", {}).get("run_id") == bindings["run_id"]]
    # Replacement/reissue of a grant never erases prior spending, pending fees
    # or attempts in the same project Run.
    if len(rows) >= terms["max_requests"]:
        raise ContractError("LIVE_GRANT_REQUEST_LIMIT_EXCEEDED", "signed request count exhausted")
    if accounting.amounts({"requests": rows}) + reserve > Decimal(terms["limit_cny"]):
        raise ContractError("LIVE_GRANT_BUDGET_EXCEEDED", "signed Run budget would be exceeded")
    return {"bundle_sha256": grant["bundle_sha256"], "owner_grant_sha256": grant["owner_grant_sha256"],
            "identity_sha256": grant["identity_sha256"]}
