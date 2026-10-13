"""Private owned-fixture transport for signed Live-interface offline tests.

No CLI/environment/contract switch enables this context. It grants no signature,
Provider permission or budget, and never relaxes Live acceptance or publication.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import json
from pathlib import Path

try:
    from .cnw_contract import ContractError
    from .project_paths import _assert_no_reparse
except ImportError:
    from cnw_contract import ContractError
    from project_paths import _assert_no_reparse

_SESSION = ContextVar("cnw_owned_live_interface_test_transport", default=None)


def _modules():
    try:
        from . import cnw_runner as runner, p2_cost_guard as accounting
    except ImportError:
        import cnw_runner as runner, p2_cost_guard as accounting
    return runner, accounting


class _Session:
    def __init__(self, owner, *, data_home, projects, runs, transport):
        runner, accounting = _modules()
        self.scope = runner._OperationSimulationSession(owner, data_home, projects, transport)
        self.active, self.transport = True, transport
        self.paths = {key: Path(getattr(accounting, key)).absolute() for key in ("CONFIG", "PRICING", "LEDGER")}
        self.frozen_config = {}
        for key, path in self.paths.items():
            _assert_no_reparse(path, code="LIVE_TEST_ACCOUNT_PATH_UNSAFE")
            if not path.resolve().is_relative_to(self.scope.fixture_root):
                raise ContractError("LIVE_TEST_ACCOUNT_NOT_OWNED", "config, pricing, ledger and slots must belong to the owned fixture")
            if key != "LEDGER": self.frozen_config[key] = path.read_bytes()
        self.runs = set()
        for path in runs:
            candidate = Path(path).absolute()
            _assert_no_reparse(candidate, code="LIVE_TEST_RUN_UNSAFE")
            candidate = candidate.resolve()
            operation = candidate.parent.name.casefold() in {"imports", "maintenance"} and candidate.parent.parent.name == "94_runtime"
            project = candidate.parents[2] if operation else candidate.parent.parent
            if (not operation and candidate.parent.name != "runs") or str(project) not in self.scope.projects:
                raise ContractError("LIVE_TEST_RUN_NOT_OWNED", "each Run must belong to an exact registered fixture instance")
            self.runs.add(candidate)
        if not self.runs:
            raise ContractError("LIVE_TEST_RUN_NOT_OWNED", "bind actual fixture Runs")

    def validate(self, run):
        runner, accounting = _modules()
        supplied = Path(run).absolute()
        _assert_no_reparse(supplied, code="LIVE_TEST_RUN_UNSAFE")
        run = supplied.resolve(strict=True)
        if not self.active or run not in self.runs:
            raise ContractError("LIVE_TEST_SESSION_EXPIRED_OR_FOREIGN", "Run is outside this active fixture")
        state = runner.load_state(run)
        operation_owner = runner._operation_owner(run, state)
        registration = runner._operation_project_registration(operation_owner or run.parent.parent)
        self.scope.validate(registration)
        for key, path in self.paths.items():
            actual = Path(getattr(accounting, key)).absolute()
            _assert_no_reparse(actual, code="LIVE_TEST_ACCOUNT_PATH_UNSAFE")
            if actual != path or (key in self.frozen_config and actual.read_bytes() != self.frozen_config[key]):
                raise ContractError("LIVE_TEST_ACCOUNT_CHANGED", "test accounting ownership or configuration changed")
        _assert_no_reparse(self.paths["LEDGER"].parent / "provider-slots", code="LIVE_TEST_ACCOUNT_PATH_UNSAFE")
        operation_schema = "cnw_import_run_v1" if run.parent.name == "imports" else "cnw_maintenance_run_v1"
        if (state.get("run_id") != run.name or
                (operation_owner is not None and state.get("schema_version") != operation_schema) or
                (operation_owner is None and (state.get("project_id") != registration["project_id"]
                    or state.get("mode") != "live" or state.get("fixture_only") is not False))):
            raise ContractError("LIVE_TEST_RUN_NOT_OWNED", "actual Run identity differs from its owned fixture")
        return run

    def history(self, run, rows, *, ledger=None):
        runner, accounting = _modules()
        run = self.validate(run)
        if not rows:
            return
        for key in ("request_id", "provider_request_id"):
            identities = [row.get(key) for row in rows]
            if any(not isinstance(value, str) or not value for value in identities) or len(set(identities)) != len(identities):
                raise ContractError("LIVE_TEST_RECEIPT_ID_DUPLICATE", "fixture history must have unique actual request and Provider IDs")
        try:
            from . import cost_guard
        except ImportError:
            import cost_guard
        from dataclasses import replace
        account = cost_guard.for_run(run, stage=rows[0]["stage"], model=runner.MODEL)
        if not isinstance(account, cost_guard.RunAccount):
            raise ContractError("LIVE_TEST_ACCOUNT_NOT_OWNED", "fixture must use actual registered Run accounting")
        snapshot = ledger if ledger is not None else accounting.read_ledger_snapshot()
        for row in rows:
            if (row.get("mode") != "MOCK_ONLY" or row.get("simulation_status") != "SIMULATED"
                    or row.get("fixture_only") is not True):
                raise ContractError("LIVE_TEST_RECEIPT_INVALID", "only explicitly simulated owned receipts can be consumed")
            runner._receipt_content(run, row)
            # The binding is Run-wide; only the actual stage attribution varies.
            # Reuse this invocation's verified binding, never a cross-call cache.
            attributed = replace(account, context=replace(account.context, stage=row["stage"]))
            attributed.verify_receipt(row, ledger=snapshot)
        current = cost_guard.for_run(run, stage=rows[0]["stage"], model=runner.MODEL)
        if current != account:
            raise ContractError("LIVE_TEST_ACCOUNT_CHANGED", "Run binding changed during history validation")
        self.validate(run)

    def response(self, run, *, url, body, request_id):
        from types import SimpleNamespace
        run = self.validate(run)
        response = self.transport(run, url=url, body=body, request_id=request_id)
        # A test context cannot fall back to HTTP or create unmarked evidence.
        payload = response.json()
        if not isinstance(payload, dict):
            raise ContractError("LIVE_TEST_RESPONSE_INVALID", "fixture response must be an object")
        payload = dict(payload, simulation_status="SIMULATED", fixture_only=True)
        return SimpleNamespace(status_code=response.status_code, json=lambda: payload,
                               content=json.dumps(payload).encode("utf-8"))


@contextmanager
def _isolated_live_transport(owner, *, data_home, projects, runs, transport):
    if _SESSION.get() is not None:
        raise ContractError("LIVE_TEST_SESSION_NESTED", "nested live-interface simulations are forbidden")
    session = _Session(owner, data_home=data_home, projects=projects, runs=runs, transport=transport)
    token = _SESSION.set(session)
    try:
        yield session
    finally:
        session.active = False
        _SESSION.reset(token)


def current_session():
    return _SESSION.get()
