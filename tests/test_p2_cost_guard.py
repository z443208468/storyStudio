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

    @staticmethod
    def denied_publish():
        error = PermissionError("SIMULATED Windows publish refusal")
        error.winerror = 5
        return error

    def test_atomic_publish_retries_same_reservation_once(self):
        original = g.os.replace
        calls = []
        def replace(src, dst):
            calls.append((src, dst))
            if len(calls) == 1:
                raise self.denied_publish()
            original(src, dst)
        with patch.object(g.os, 'replace', side_effect=replace):
            self.reserve()
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(len(g.read_ledger_snapshot()['requests']), 1)

    def test_persistent_publish_refusal_preserves_original_and_pending_file(self):
        self.reserve()
        before = self.ledger.read_bytes()
        with patch.object(g.os, 'replace', side_effect=self.denied_publish()) as publish:
            with self.assertRaises(PermissionError):
                self.reserve('MOCK-2')
        self.assertEqual(publish.call_count, 3)
        self.assertEqual(self.ledger.read_bytes(), before)
        files = list(self.root.glob('ledger.json.tmp-*'))
        self.assertEqual(len(files), 1)
        self.assertEqual(len(json.loads(files[0].read_bytes())['requests']), 2)

    def test_publish_refuses_changed_preimage_and_temp(self):
        self.reserve()
        foreign = b'{"external": true}'
        def replace(src, dst):
            self.ledger.write_bytes(foreign)
            raise self.denied_publish()
        with patch.object(g.os, 'replace', side_effect=replace) as publish:
            with self.assertRaisesRegex(ValueError, 'COST_LEDGER_PREIMAGE_CHANGED'):
                self.reserve('MOCK-2')
        self.assertEqual(publish.call_count, 1)
        self.assertEqual(self.ledger.read_bytes(), foreign)
        tmp = next(self.root.glob('ledger.json.tmp-*'))
        with self.assertRaisesRegex(ValueError, 'COST_LEDGER_TEMP_CHANGED'):
            g._publish_ledger(tmp, foreign, b'different')

    def test_readonly_snapshot_waits_for_writer_without_republish(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        self.reserve()
        before = self.ledger.read_bytes()
        entered = Event()
        def read():
            entered.set()
            return g.read_ledger_snapshot()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with g._ledger_lock():
                future = pool.submit(read)
                self.assertTrue(entered.wait(2))
                self.assertFalse(future.done())
            with patch.object(g.os, 'replace', side_effect=AssertionError('read must not publish')):
                result = future.result(timeout=3)
        self.assertEqual(len(result['requests']), 1)
        self.assertEqual(self.ledger.read_bytes(), before)

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

    def bound_reserve(self, context, request_id):
        return g.command_reserve(SimpleNamespace(request_id=request_id, run_id=context.run_id,
            purpose='fictional accounting test', input_token_cap=1000000,
            output_token_cap=1000000), context=context, emit=False)

    def bound_settle(self, context, request_id, *, unknown=False):
        return g.command_settle(SimpleNamespace(request_id=request_id,
            provider_request_id=None if unknown else 'SIMULATED-' + request_id,
            returned_model=None if unknown else 'deepseek-flash', finish_reason='stop',
            input_tokens=None if unknown else 1000000,
            output_tokens=None if unknown else 1000000), context=context, emit=False)

    def test_same_run_across_instances_cannot_settle_another_reservation(self):
        a = g.CostContext('instance-a', 'harbor', 'SAME-RUN', 'plot', 'a' * 64)
        b = g.CostContext('instance-b', 'harbor', 'SAME-RUN', 'plot', 'b' * 64)
        self.bound_reserve(a, 'a-request')
        self.bound_reserve(b, 'b-request')
        before = self.ledger.read_bytes()
        for context in (b, None, g.CostContext('instance-a', 'harbor', 'SAME-RUN', 'prose', 'a' * 64)):
            with self.subTest(context=context), self.assertRaisesRegex(ValueError, 'COST_CONTEXT_SETTLEMENT_MISMATCH'):
                self.bound_settle(context, 'a-request')
            self.assertEqual(before, self.ledger.read_bytes())
        self.assertEqual(self.bound_settle(a, 'a-request')['status'], 'SETTLED')
        self.assertEqual(self.bound_settle(b, 'b-request', unknown=True)['status'], 'UNKNOWN_NOT_ZERO')
        ledger = json.loads(self.ledger.read_bytes())
        self.assertEqual(g.amounts(ledger), Decimal('6.000000'))
        self.assertEqual(ledger['requests'][0]['cost_context'], a.record())
        self.assertEqual(ledger['requests'][1]['cost_context'], b.record())

    def test_bound_settlement_uses_reserved_pricing_and_preserves_legacy_rows(self):
        self.reserve('legacy')
        self.settle('legacy', input_tokens=None, output_tokens=None)
        legacy = json.loads(self.ledger.read_bytes())['requests'][0]
        context = g.CostContext('instance-a', 'harbor', 'SAME-RUN', 'plot', 'a' * 64)
        self.bound_reserve(context, 'new')
        prices = json.loads(self.pricing.read_bytes())
        prices['output_usd_per_million_peak'] = 200
        self.pricing.write_text(json.dumps(prices), encoding='utf-8')
        self.assertEqual(self.bound_settle(context, 'new')['estimated_request_cny'], '3.000000')
        rows = json.loads(self.ledger.read_bytes())['requests']
        self.assertEqual(rows[0], legacy)
        self.assertNotIn('cost_context', rows[0])
        before = self.ledger.read_bytes()
        with self.assertRaisesRegex(ValueError, 'COST_CONTEXT_SETTLEMENT_MISMATCH'):
            self.bound_settle(context, 'legacy')
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_bound_projects_share_one_finite_budget(self):
        a = g.CostContext('instance-a', 'harbor', 'RUN', 'plot', 'a' * 64)
        b = g.CostContext('instance-b', 'mountain', 'RUN', 'plot', 'b' * 64)
        with g.locked_ledger() as ledger:
            ledger['limit'] = '5'
        self.bound_reserve(a, 'a-request')
        before = self.ledger.read_bytes()
        with self.assertRaisesRegex(ValueError, 'CAMPAIGN_ESTIMATE_LIMIT_WOULD_BE_EXCEEDED'):
            self.bound_reserve(b, 'b-request')
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertEqual(len(g.read_ledger_snapshot()['requests']), 1)

    def test_provider_fee_wrappers_keep_parallel_results_separate(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        import sys
        from tools import cnw_live_provider as provider
        reserve_core, settle_core = g.command_reserve, g.command_settle
        original_stdout = sys.stdout
        rendezvous = Barrier(2)
        def reserve(args, **kwargs):
            self.assertIs(sys.stdout, original_stdout)
            self.assertIs(kwargs.get('emit'), False)
            rendezvous.wait(timeout=3)
            return reserve_core(args, **kwargs)
        def settle(args, **kwargs):
            self.assertIs(sys.stdout, original_stdout)
            self.assertIs(kwargs.get('emit'), False)
            rendezvous.wait(timeout=3)
            return settle_core(args, **kwargs)
        def call(index):
            request = 'parallel-' + str(index)
            admitted = provider._reserve(request, 'MOCK_ONLY', 'plot', 100, 100)
            settled = provider._settle(request, {'id': 'SIMULATED-' + request,
                'model': 'deepseek-flash', 'choices': [{'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': index + 1, 'completion_tokens': index + 2}})
            return admitted, settled
        with patch.object(g, 'command_reserve', side_effect=reserve), \
                patch.object(g, 'command_settle', side_effect=settle), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(call, range(2)))
        for index, (admitted, settled) in enumerate(results):
            self.assertEqual(admitted['request_id'], 'parallel-' + str(index))
            self.assertEqual(settled['request_id'], admitted['request_id'])
            self.assertEqual(settled['status'], 'SETTLED')
        self.assertIs(sys.stdout, original_stdout)
        self.assertEqual(len(g.read_ledger_snapshot()['requests']), 2)

    def test_raw_snapshot_preserves_exact_original_bytes(self):
        raw = b'{  "requests": [], "limit": "5" }\r\n'
        self.ledger.write_bytes(raw)
        with patch.object(g.os, 'replace', side_effect=AssertionError('readonly')):
            self.assertEqual(g.read_ledger_bytes(), raw)
        self.assertEqual(self.ledger.read_bytes(), raw)

    def test_bound_model_drift_refuses_without_mutating_ledger(self):
        context = g.CostContext('instance-a', 'harbor', 'RUN', 'plot', 'a' * 64)
        self.bound_reserve(context, 'existing')
        before = self.ledger.read_bytes()
        args = SimpleNamespace(request_id='changed', run_id='RUN', purpose='MOCK_ONLY',
                               input_token_cap=10, output_token_cap=10)
        with self.assertRaisesRegex(ValueError, 'COST_PROVIDER_MODEL_MISMATCH'):
            g.command_reserve(args, context=context, expected_model='different-model', emit=False)
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_invalid_context_or_wrong_run_refuses_before_ledger_creation(self):
        for context in (g.CostContext('../escape', 'harbor', 'RUN', 'plot', 'a' * 64),
                        g.CostContext('instance', 'harbor', 'RUN', 'plot', 'invalid'), {}):
            with self.subTest(context=context), self.assertRaisesRegex(ValueError, 'COST_CONTEXT_INVALID'):
                g.command_reserve(SimpleNamespace(run_id='RUN'), context=context, emit=False)
            self.assertFalse(self.ledger.exists())
        with self.assertRaisesRegex(ValueError, 'COST_CONTEXT_RUN_MISMATCH'):
            g.command_reserve(SimpleNamespace(run_id='OTHER'), emit=False,
                context=g.CostContext('instance', 'harbor', 'RUN', 'plot', 'a' * 64))
        self.assertFalse(self.ledger.exists())


if __name__ == '__main__':
    unittest.main()
