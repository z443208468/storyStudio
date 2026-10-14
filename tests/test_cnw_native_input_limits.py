"""Fault injection into the real native capture; no native-method success claim."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from tests import test_cnw_live_authorization as fixtures
from tools import cnw_runner as r, cost_guard, p2_06_critics_run as native


class NativeInputLimitTests(unittest.TestCase):
    def setUp(self):
        self.subject = fixtures.LiveAuthorizationTests()
        self.subject.setUp()
        self.addCleanup(self.subject.doCleanups)

    def test_registered_signed_native_capture_refuses_actual_oversize_before_fees(self):
        s = self.subject
        s.fixture.contract['integrations'] = {'nk': 'DISABLED', 'critics': 'ENABLED'}
        s.contract.write_text(json.dumps(s.fixture.contract, ensure_ascii=False), encoding='utf-8')
        terms = s.full_terms()
        terms['stages'].append('critics_plot')
        terms['roles']['critics_plot'] = ['critics_plot']
        s.sign(terms=terms)
        with patch.object(r, '_assert_support_components_available', return_value=None):
            s.create()
        artifact = r._persist_stage(s.run, 'plot', 'artifacts/plot.md', 'A legal fictional repair plan.\n')
        raw = (s.run / artifact['path']).read_bytes()
        source = s.run / 'artifacts/support' / ('critics-input-' + r.sha(raw) + '.md')
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(raw)
        with cost_guard.accounting.locked_ledger():
            pass
        ledger_before = cost_guard.accounting.LEDGER.read_bytes()
        for number, (characters, signed_limit) in enumerate(((13000, 100000), (2000, 1000))):
            limited = copy.deepcopy(terms)
            limited['max_input_tokens'] = signed_limit
            s.sign(terms=limited)
            child = s.root / 'runs' / ('fictional-oversize-child-' + str(number))
            account = cost_guard.for_run(s.run, stage='critics_plot', model=r.MODEL)
            args = SimpleNamespace(action='plan-critique', input=str(source), critique=None,
                ledger_run_id=s.run_id, parent_stage='critics_plot')
            observed = []
            def emit_fault(command, *, _registered_invocation):
                self.assertEqual(_registered_invocation.account, account)
                self.assertEqual(_registered_invocation.input_path, source)
                self.assertEqual(_registered_invocation.input_sha256, r.sha(raw).upper())
                child.mkdir()
                request = httpx.Request('POST', 'https://api.deepseek.com/v1/chat/completions',
                    json={'model': r.MODEL, 'max_tokens': 100,
                          'messages': [{'role': 'user', 'content': 'x' * characters}]})
                try:
                    httpx.Client.send(None, request)
                except RuntimeError as error:
                    observed.append(str(error))
                    raise
            with self.subTest(signed_limit=signed_limit), \
                 patch.object(native.critics_bridge, 'main', side_effect=emit_fault), \
                 patch.object(httpx.Client, 'send', side_effect=AssertionError('HTTP forbidden')) as send, \
                 patch.object(cost_guard.accounting, 'provider_slot', side_effect=AssertionError('slot forbidden')) as slot, \
                 patch.object(cost_guard.RunAccount, 'command_reserve', side_effect=AssertionError('reserve forbidden')) as reserve:
                self.assertEqual(native._execute_native(args, child, account=account, parent_run_dir=s.run), 1)
                self.assertEqual(observed, ['CRITICS_PROVIDER_INPUT_LIMIT_EXCEEDED'])
                send.assert_not_called()
                slot.assert_not_called()
                reserve.assert_not_called()
            self.assertEqual(cost_guard.accounting.LEDGER.read_bytes(), ledger_before)
            self.assertEqual(json.loads((child / 'provider-calls.json').read_bytes()), [])


if __name__ == '__main__':
    unittest.main()
