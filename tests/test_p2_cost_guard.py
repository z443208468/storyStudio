"""Offline tests of explicit unlimited accounting and finite compatibility."""
import json
from decimal import Decimal
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools import p2_cost_guard as g, cnw_review


class CampaignLimitTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.config = self.root / 'config.json'
        self.pricing = self.root / 'pricing.json'
        self.ledger = self.root / 'ledger.json'
        self.config.write_text(json.dumps({'provider': {'model': 'deepseek-flash', 'max_in_flight': 1},
            'cost_guard': {'currency': 'CNY', 'persist_across_run_ids': True,
                           'estimated_campaign_limit': None, 'scope': 'MOCK_ONLY'}}), encoding='utf-8')
        self.pricing.write_text(json.dumps({'requested_model': 'deepseek-flash', 'currency': 'CNY',
            'input_cache_miss_usd_per_million_peak': 1, 'output_usd_per_million_peak': 2,
            'usd_to_cny_estimate': 1}), encoding='utf-8')
        self.patches = [patch.object(g, 'CONFIG', self.config), patch.object(g, 'PRICING', self.pricing), patch.object(g, 'LEDGER', self.ledger)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def reserve(self, identity='MOCK-1', input_cap=1000000, output_cap=1000000):
        return g.command_reserve(SimpleNamespace(request_id=identity, run_id='MOCK_ONLY', purpose='offline',
            input_token_cap=input_cap, output_token_cap=output_cap), emit=False)

    def settle(self, identity='MOCK-1', input_tokens=1000000, output_tokens=1000000):
        return g.command_settle(SimpleNamespace(request_id=identity, provider_request_id='MOCK-PROVIDER',
            returned_model='deepseek-flash', finish_reason='stop',
            input_tokens=input_tokens, output_tokens=output_tokens), emit=False)

    def test_new_unlimited_ledger_reserves_and_settles_without_money_cap(self):
        result = self.reserve(input_cap=100000000, output_cap=100000000)
        self.assertIsNone(result['limit_cny'])
        self.assertEqual(result['reserved_cny'], '300.000000')
        result = self.settle(input_tokens=100000000, output_tokens=100000000)
        self.assertEqual(result['status'], 'SETTLED')
        self.assertEqual(result['campaign_committed_cny'], '300.000000')
        self.assertFalse(json.loads(self.ledger.read_text())['requests'][0]['budget_exceeded']['campaign_limit'])

    def test_existing_finite_ledger_is_not_silently_changed_by_default(self):
        with g.locked_ledger() as ledger:
            ledger['limit'] = '2'
        before = self.ledger.read_bytes()
        with self.assertRaisesRegex(ValueError, 'CAMPAIGN_ESTIMATE_LIMIT_WOULD_BE_EXCEEDED'):
            self.reserve()
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_explicit_unlimited_change_preserves_unknown_and_charge_history(self):
        self.reserve()
        self.settle(input_tokens=None, output_tokens=None)
        with g.locked_ledger() as ledger:
            ledger['limit'] = '10'
        before = json.loads(self.ledger.read_text())
        result = g.command_set_limit(SimpleNamespace(unlimited=True, limit_cny=None, reason='MOCK explicit authorization'), emit=False)
        after = json.loads(self.ledger.read_text())
        self.assertIsNone(result['limit_cny'])
        self.assertEqual(after['requests'], before['requests'])
        self.assertEqual(g.amounts(after), Decimal('3.000000'))
        self.assertEqual(after['limit_changes'][0]['old_limit_cny'], '10')
        self.assertIsNone(after['limit_changes'][0]['new_limit_cny'])
        self.assertEqual(after['requests'][0]['status'], 'UNKNOWN_NOT_ZERO')
        g.command_set_limit(SimpleNamespace(unlimited=True, limit_cny=None, reason='MOCK repeated'), emit=False)
        self.assertEqual(len(json.loads(self.ledger.read_text())['limit_changes']), 1)
        self.reserve('MOCK-2', input_cap=100000000, output_cap=100000000)

    def test_invalid_limits_and_missing_change_reason_are_rejected(self):
        for value in ('NaN', 'Infinity', '-Infinity', 0, -1, True, 'bad', {}):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'CAMPAIGN_LIMIT_INVALID'):
                g.campaign_limit(value)
        with self.assertRaisesRegex(ValueError, 'CAMPAIGN_LIMIT_CHANGE_REASON_REQUIRED'):
            g.command_set_limit(SimpleNamespace(unlimited=True, limit_cny=None, reason=' '), emit=False)
        with self.assertRaisesRegex(ValueError, 'CAMPAIGN_LIMIT_INVALID'):
            g.command_set_limit(SimpleNamespace(unlimited=False, limit_cny=None, reason='MOCK'), emit=False)

    def test_unlimited_does_not_disable_token_cap_or_duplicate_request_checks(self):
        self.reserve(input_cap=1, output_cap=1)
        with self.assertRaisesRegex(ValueError, 'REQUEST_ID_ALREADY_RECORDED'):
            self.reserve()
        self.assertEqual(self.settle(input_tokens=2, output_tokens=2)['status'], 'SETTLED_OVER_BUDGET')
        with self.assertRaisesRegex(ValueError, 'TOKEN_CAPS_MUST_BE_POSITIVE'):
            self.reserve('MOCK-2', input_cap=0)

    def test_dry_run_unlimited_keeps_ledger_unchanged(self):
        self.reserve()
        before = self.ledger.read_bytes()
        result = cnw_review.dry_run_cost_reservation([{'task_key': 'MOCK', 'purpose': 'offline',
            'input_token_cap': 100000000, 'output_token_cap': 100000000}])
        self.assertFalse(result['ledger_written'])
        self.assertEqual(self.ledger.read_bytes(), before)
        with g.locked_ledger() as ledger:
            ledger['limit'] = '10'
        with self.assertRaisesRegex(ValueError, 'COST_RESERVATION_WOULD_EXCEED_LIMIT'):
            cnw_review.dry_run_cost_reservation([{'task_key': 'MOCK', 'purpose': 'offline',
                'input_token_cap': 100000000, 'output_token_cap': 100000000}])


if __name__ == '__main__':
    unittest.main()
