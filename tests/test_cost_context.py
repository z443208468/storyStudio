"""Registered fictional Run ownership through the real shared accounting core."""
import json
from types import SimpleNamespace
import unittest

from tests import test_cnw_run_bindings as runs
from tests import test_p2_cost_guard as fees
from tools import cost_guard as cost, cnw_runner
from tools.cnw_contract import ContractError


class RunCostContextTests(unittest.TestCase):
    def setUp(self):
        self.run_fixture = runs.ExistingRunBindingTests()
        self.run_fixture.setUp()
        self.addCleanup(self.run_fixture.doCleanups)
        self.fees = fees.CampaignLimitTests()
        self.fees.setUp()
        self.addCleanup(self.fees.doCleanups)

    def account(self):
        return cost.for_run(self.run_fixture.run, stage='plot', model='deepseek-flash')

    def args(self, identity='request-a'):
        return SimpleNamespace(request_id=identity, run_id=self.run_fixture.run.name,
            purpose='MOCK_ONLY accounting', input_token_cap=100, output_token_cap=100)

    def test_real_registration_and_frozen_contract_define_context_without_spend(self):
        account = self.account()
        report = self.run_fixture.report()
        self.assertEqual(account.context.binding_sha256, report['identity_sha256'])
        self.assertEqual(account.context.project_instance_id, report['bindings']['project_instance_id'])
        self.assertEqual(account.context.project_id, report['bindings']['project_id'])
        self.assertFalse(self.fees.ledger.exists())
        with self.assertRaisesRegex(ContractError, 'COST_ACCOUNT_NOT_CONFIGURED'):
            account.command_reserve(self.args(), emit=False)
        self.assertFalse(self.fees.ledger.exists())

    def test_changed_contract_cannot_reserve_but_incurred_charge_can_still_settle(self):
        with cost.accounting.locked_ledger():
            pass  # Only this fixture creates a synthetic shared account.
        account = self.account()
        account.command_reserve(self.args(), emit=False)
        original = self.fees.ledger.read_bytes()
        self.run_fixture.path.write_bytes(self.run_fixture.path.read_bytes() + b'\n')
        with self.assertRaises(ContractError):
            account.command_reserve(self.args('request-b'), emit=False)
        self.assertEqual(self.fees.ledger.read_bytes(), original)
        result = account.command_settle(SimpleNamespace(request_id='request-a',
            provider_request_id=None, returned_model=None, finish_reason=None,
            input_tokens=None, output_tokens=None), emit=False)
        self.assertEqual(result['status'], 'UNKNOWN_NOT_ZERO')
        self.assertEqual(result['cost_context'], account.context.record())

    def test_receipt_replay_from_another_instance_is_rejected(self):
        account = self.account()
        with cost.accounting.locked_ledger():
            pass
        account.command_reserve(self.args(), emit=False)
        settlement = account.command_settle(SimpleNamespace(request_id='request-a',
            provider_request_id='SIMULATED-ID', returned_model='deepseek-flash',
            finish_reason='stop', input_tokens=10, output_tokens=10), emit=False)
        receipt = {'stage': 'plot', 'request_id': 'request-a', 'provider_request_id': 'SIMULATED-ID',
                   'model': 'deepseek-flash', 'ledger_settlement': settlement}
        account.verify_receipt(receipt)
        snapshot = cost.accounting.read_ledger_snapshot()
        cnw_runner._verify_cost_receipt(self.run_fixture.run, receipt, snapshot)
        for field in ('project_instance_id', 'project_id', 'run_id', 'stage', 'binding_sha256'):
            changed = json.loads(json.dumps(snapshot))
            changed['requests'][0]['cost_context'][field] = 'foreign'
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, 'COST_RECEIPT_BINDING_MISMATCH'):
                cnw_runner._verify_cost_receipt(self.run_fixture.run, receipt, changed)
        with cost.accounting.locked_ledger() as ledger:
            ledger['requests'][0]['cost_context']['project_instance_id'] = 'foreign-instance'
        before = self.fees.ledger.read_bytes()
        with self.assertRaisesRegex(ContractError, 'COST_RECEIPT_BINDING_MISMATCH'):
            account.verify_receipt(receipt)
        self.assertEqual(before, self.fees.ledger.read_bytes())


if __name__ == '__main__':
    unittest.main()
