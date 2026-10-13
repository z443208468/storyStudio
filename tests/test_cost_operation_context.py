"""Actual registered operations, simulated model output, isolated accounting."""
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from tests import test_cnw_operation_authorization as operations
from tests import test_p2_cost_guard as fees
from tools import cost_guard as cost
from tools.cnw_contract import ContractError


class OperationCostTests(unittest.TestCase):
    def setUp(self):
        self.fixture = operations.OperationAuthorizationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fees = fees.CampaignLimitTests()
        self.fees.setUp()
        self.addCleanup(self.fees.doCleanups)
        with cost.accounting.locked_ledger():
            pass

    def test_uppercase_namespace_and_state_save_failure_recover(self):
        run = self.fixture._run(kind='IMPORTS', name='uppercase-operation')
        state = operations.runner.load_state(run)
        state['schema_version'] = 'cnw_import_run_v1'
        operations.runner.save_state(run, state)
        operations._write(run, 'artifacts/input.json', '{"fictional": true}')
        kwargs = dict(stage='project_import', role_id='project_organization',
            messages=[{'role': 'user', 'content': 'Fictional material'}], output_cap=100,
            snapshots=['artifacts/input.json'])
        with patch.object(operations.runner, 'save_state', side_effect=OSError('SIMULATED state save failure')):
            with self.assertRaises(OSError):
                cost.freeze_operation_account(run, **kwargs)
        snapshot = run / 'artifacts/cost_operation.json'
        frozen = snapshot.read_bytes()
        cost.freeze_operation_account(run, **kwargs)
        self.assertEqual(snapshot.read_bytes(), frozen)
        account = cost.for_run(run, stage='project_import', model=operations.runner.MODEL)
        self.assertEqual(account.context.run_id, run.name)
        self.assertEqual(json.loads(frozen)['operation_kind'], 'imports')

    def test_real_import_update_and_maintenance_bind_frozen_requests(self):
        fixture = self.fixture
        accounts = []
        original = fixture._record
        def simulated(run, **kwargs):
            account = cost.for_run(run, stage=kwargs['stage'], model=operations.runner.MODEL)
            account.verify_request(messages=kwargs['messages'], role_id=kwargs['role_id'],
                output_cap=kwargs['output_cap'], extra=kwargs.get('extra'))
            request_id = 'SIMULATED-FEE-' + str(len(accounts))
            account.command_reserve(SimpleNamespace(request_id=request_id, run_id=run.name,
                purpose='MOCK_ONLY', input_token_cap=100, output_token_cap=100), emit=False)
            accounts.append((account, request_id))
            return original(run, **kwargs)
        fixture._record = simulated
        with fixture._session(projects=fixture.projects):
            operations.imports.run_import(fixture.root)
            operations._write(fixture.root, '_INBOX/additional.md', 'A fictional blue sail arrives.')
            operations.imports.run_import(fixture.root, incremental=True)
            operations.maintenance.run_maintenance(fixture.root, 'audit')
            operations.imports.run_import(fixture.other)
        self.assertEqual([a.context.stage for a, _ in accounts],
                         ['project_import', 'project_update', 'project_audit', 'project_import'])
        self.assertNotEqual(accounts[0][0].context.project_instance_id,
                            accounts[-1][0].context.project_instance_id)
        for account, request_id in accounts:
            # Successful publication changed project documents, not frozen inputs.
            current = cost.for_run(account.run, stage=account.context.stage, model=account.model)
            self.assertEqual(current.context, account.context)
            settled = account.command_settle(SimpleNamespace(request_id=request_id,
                provider_request_id='SIMULATED-' + request_id, returned_model=account.model,
                finish_reason='stop', input_tokens=10, output_tokens=10), emit=False)
            receipt = {'request_id': request_id, 'provider_request_id': 'SIMULATED-' + request_id,
                       'model': account.model, 'ledger_settlement': settled}
            current.verify_receipt(receipt)
        first, request_id = accounts[0]
        foreign, _ = accounts[-1]
        # Both real registered owners use one budget, not a budget per project.
        from decimal import Decimal
        with cost.accounting.locked_ledger() as ledger:
            ledger['limit'] = str(cost.accounting.amounts(ledger) + Decimal('0.000300'))
        pending = SimpleNamespace(request_id='pending-after-publish', run_id=first.run.name,
            purpose='MOCK_ONLY', input_token_cap=100, output_token_cap=100)
        first.command_reserve(pending, emit=False)
        before = self.fees.ledger.read_bytes()
        with self.assertRaisesRegex(ValueError, 'COST_CONTEXT_SETTLEMENT_MISMATCH'):
            foreign.command_settle(SimpleNamespace(request_id=pending.request_id,
                provider_request_id=None, returned_model=None, finish_reason=None,
                input_tokens=None, output_tokens=None), emit=False)
        self.assertEqual(before, self.fees.ledger.read_bytes())
        with self.assertRaisesRegex(ValueError, 'CAMPAIGN_ESTIMATE_LIMIT_WOULD_BE_EXCEEDED'):
            foreign.command_reserve(SimpleNamespace(request_id='other-project-over-budget',
                run_id=foreign.run.name, purpose='MOCK_ONLY', input_token_cap=100,
                output_token_cap=100), emit=False)
        self.assertEqual(before, self.fees.ledger.read_bytes())
        # max_in_flight=1 belongs to the shared account, even across projects.
        from concurrent.futures import ThreadPoolExecutor, TimeoutError
        from threading import Event
        entered = Event()
        def enter_other_slot():
            entered.set()
            with foreign.provider_slot():
                return 'admitted'
        with ThreadPoolExecutor(max_workers=1) as pool:
            with first.provider_slot():
                future = pool.submit(enter_other_slot)
                self.assertTrue(entered.wait(2))
                with self.assertRaises(TimeoutError):
                    future.result(timeout=0.15)
            self.assertEqual(future.result(timeout=3), 'admitted')
        with self.assertRaisesRegex(ContractError, 'COST_RECEIPT_BINDING_MISMATCH'):
            foreign.verify_receipt({'request_id': request_id, 'provider_request_id': 'SIMULATED-' + request_id})
        manifest = json.loads((first.run / 'artifacts/cost_operation.json').read_bytes())
        with self.assertRaisesRegex(ContractError, 'COST_OPERATION_REQUEST_MISMATCH'):
            first.verify_request(messages=manifest['messages'], role_id='different',
                                 output_cap=manifest['output_cap'])
        state = operations.runner.load_state(first.run)
        state['schema_version'] = 'legacy'
        operations.runner.save_state(first.run, state)
        with self.assertRaisesRegex(ContractError, 'COST_OPERATION_BINDINGS_MISMATCH'):
            cost.for_run(first.run, stage=first.context.stage, model=first.model)
        state['schema_version'] = manifest['run_schema']
        operations.runner.save_state(first.run, state)
        snapshot = first.run / next(iter(manifest['snapshots']))
        snapshot.write_bytes(snapshot.read_bytes() + b'changed')
        before = self.fees.ledger.read_bytes()
        with self.assertRaisesRegex(ContractError, 'COST_OPERATION_INPUT_CHANGED'):
            first.command_reserve(SimpleNamespace(request_id='forbidden', run_id=first.run.name,
                purpose='MOCK_ONLY', input_token_cap=10, output_token_cap=10), emit=False)
        self.assertEqual(self.fees.ledger.read_bytes(), before)
        # An incurred reservation still settles against its original context.
        held = first.command_settle(SimpleNamespace(request_id=pending.request_id,
            provider_request_id=None, returned_model=None, finish_reason=None,
            input_tokens=None, output_tokens=None), emit=False)
        self.assertEqual(held['status'], 'UNKNOWN_NOT_ZERO')
        fixture._assert_no_real_transport()


class SnapshotPublicationTests(unittest.TestCase):
    def test_partial_write_preserved_and_retry_publishes_complete_snapshot(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'cost_operation.json'
            original_open = Path.open
            class PartialWriter:
                def __init__(self, stream):
                    self.stream = stream
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    self.stream.close()
                def write(self, raw):
                    self.stream.write(raw[:4])
                    raise OSError('SIMULATED partial write')
            def failing_open(path, mode='r', *args, **kwargs):
                stream = original_open(path, mode, *args, **kwargs)
                return PartialWriter(stream) if mode == 'xb' else stream
            with patch.object(Path, 'open', failing_open), self.assertRaises(OSError):
                cost._publish_operation_snapshot(target, b'complete snapshot')
            self.assertFalse(target.exists())
            attempts = list(Path(directory).glob('*.attempt-*'))
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0].read_bytes(), b'comp')
            cost._publish_operation_snapshot(target, b'complete snapshot')
            self.assertEqual(target.read_bytes(), b'complete snapshot')
            self.assertEqual(attempts[0].read_bytes(), b'comp')
            with self.assertRaises(FileExistsError):
                cost._publish_operation_snapshot(target, b'replacement forbidden')
            self.assertEqual(target.read_bytes(), b'complete snapshot')


if __name__ == '__main__':
    unittest.main()
