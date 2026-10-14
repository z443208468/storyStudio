"""Run with pinned CritiCS Python: actual native methods, simulated final HTTP."""
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from tests import test_cnw_live_authorization as fixtures
from tools import cnw_runner as r, cnw_recovery as recovery, cost_guard
from tools import p2_06_critics_run as native
from tools.cnw_contract import ContractError
from tools.cnw_test_live_transport import _isolated_live_transport


class SignedCriticsConsumerTests(unittest.TestCase):
    def setUp(self):
        self.subject = fixtures.LiveAuthorizationTests()
        self.subject.setUp()
        self.addCleanup(self.subject.doCleanups)
        self.addCleanup(self._capture_terminal_fixture)

    def _capture_terminal_fixture(self):
        s = self.subject
        destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
        if not destination or not s.run.exists():
            return
        files = {p.relative_to(s.root).as_posix(): {'sha256': r.sha(p.read_bytes()),
            'utf8': p.read_bytes().decode('utf-8')} for p in (s.root / 'runs').rglob('*') if p.is_file()}
        ledger = cost_guard.accounting.LEDGER
        Path(destination + '.terminal_capture.json').write_text(json.dumps({
            'status': 'TERMINAL_CAPTURE_NOT_ACCEPTANCE', 'mode': 'MOCK_ONLY',
            'simulation_status': 'SIMULATED', 'real_provider_calls': 0,
            'actual_run_state': r.load_state(s.run), 'actual_files': files,
            'actual_synthetic_ledger': json.loads(ledger.read_bytes()) if ledger.is_file() else None},
            ensure_ascii=False, indent=2), encoding='utf-8')

    def test_native_plot_text_shared_fees_pending_cache_and_refine_consumption(self):
        s = self.subject
        s.fixture.contract['integrations'] = {'nk': 'DISABLED', 'critics': 'ENABLED'}
        s.contract.write_text(json.dumps(s.fixture.contract, ensure_ascii=False), encoding='utf-8')
        # Freeze this fictional account's single-slot resource setting before
        # signing. All Lens/Verifier/native requests remain independent.
        resource_config = json.loads(s.fees.config.read_bytes())
        resource_config['provider']['max_in_flight'] = 1
        s.fees.config.write_bytes(json.dumps(resource_config, ensure_ascii=False).encode('utf-8'))
        terms = s.full_terms()
        # This finite fictional grant covers slow real Windows identity checks.
        # Production expiry checks and all request/token/money limits are kept.
        terms['expires_at'] = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
        for hook in ('critics_plot', 'critics_text'):
            terms['stages'].append(hook)
            terms['roles'][hook] = [hook]
        s.sign(terms=terms)
        s.create()
        with cost_guard.accounting.locked_ledger():
            pass
        outputs = s.fixture._outputs()
        s.fixture.rereview_messages = []
        cnw_calls, native_calls, service_calls = [], [], []
        def cnw_transport(run, *, url, body, request_id):
            stage = request_id.removeprefix('cnw-' + s.run_id + '-').rsplit('-', 1)[0]
            role, extra = None, None
            if stage in {'multi_lens_review', 're_review', 'adversarial_verify'}:
                packet = json.loads(body['messages'][1]['content'])
                role = packet.get('lens_id') or packet.get('verifier_id')
                if 'finding_id' in packet:
                    extra = {'finding_id': packet['finding_id']}
            if stage == 'refine':
                self.assertIn('MOCK_ONLY selected native expression', json.dumps(body['messages']))
            content = s.fixture._response(stage, role, extra, outputs, body['messages'])
            cnw_calls.append({'stage': stage, 'role': role, 'messages': body['messages']})
            return SimpleNamespace(status_code=200, json=lambda: {
                'id': 'SIMULATED-' + request_id, 'model': r.MODEL,
                'choices': [{'finish_reason': 'stop', 'message': {'content': content}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 10}})
        replies = [
            'Expert 1\nStructure persona\nExpert 2\nEnding persona\nExpert 3\nOriginal persona\nLeader\nLeader persona',
            'Question: Is the repair visible?\nWhy: MOCK_ONLY structure.',
            'Question: Is the offer earned?\nWhy: MOCK_ONLY ending.',
            'Question: Does the neighbor choose?\nWhy: MOCK_ONLY original.',
            'Question: Is the offer earned?\nWhy: MOCK_ONLY selection.',
            'MOCK_ONLY native imagery alternative', 'MOCK_ONLY native voice alternative',
            'MOCK_ONLY selected native expression']
        def native_http(client, request, *args, **kwargs):
            self.assertEqual(request.url.host, 'api.deepseek.com')
            body = json.loads(request.read())
            self.assertEqual(body['model'], r.MODEL)
            number = len(native_calls)
            if number >= len(replies):
                raise AssertionError('unexpected native retry')
            native_calls.append({'request': body, 'simulation_status': 'SIMULATED'})
            return httpx.Response(200, request=request, json={
                'id': 'SIMULATED-NATIVE-' + str(number), 'model': r.MODEL,
                'object': 'chat.completion', 'created': 0,
                'simulation_status': 'SIMULATED', 'fixture_only': True,
                'choices': [{'index': 0, 'finish_reason': 'stop',
                            'message': {'role': 'assistant', 'content': replies[number]}}],
                'usage': {'prompt_tokens': 12, 'completion_tokens': 8, 'total_tokens': 20}})
        real_run = subprocess.run
        def service(command, **kwargs):
            if len(command) < 2 or Path(str(command[1])) != r.ROOT / 'tools/p2_06_critics_run.py':
                return real_run(command, **kwargs)
            service_calls.append(list(command))
            # Preserve the service argv; execute its actual main/native methods
            # in this owned test context so simulated parent receipts stay scoped.
            previous = Path.cwd()
            try:
                result = native.main(command[2:])
            finally:
                os.chdir(previous)
            return subprocess.CompletedProcess(command, result, stdout='', stderr='')
        with _isolated_live_transport(s.fixture.temp, data_home=s.fixture.data_home,
                projects=[s.root], runs=[s.run], transport=cnw_transport), \
             patch('subprocess.run', side_effect=service), \
             patch.object(httpx.Client, 'send', native_http):
            for stage in r.CNW_STAGES:
                recovery.execute_checked(s.run, stage)
            state = r.load_state(s.run)
            self.assertEqual(len(native_calls), 8)
            self.assertEqual(len(service_calls), 2)
            self.assertEqual(state['support_hooks']['critics_plot']['result']['inspector'], 'Is the offer earned?')
            self.assertEqual(state['support_hooks']['critics_text']['result']['select'], replies[-1])
            self.assertEqual(state['support_hooks']['critics_text']['mode'], 'MOCK_ONLY')
            before = cost_guard.accounting.LEDGER.read_bytes()
            for input_stage, hook in (('plot', 'critics_plot'), ('prose', 'critics_text')):
                # Pending evidence must be reconsumed, never relaunch the service.
                state = r.load_state(s.run)
                state['support_hooks'][hook]['status'] = 'NATIVE_RESULT_PENDING'
                r.save_state(s.run, state)
                result = r._critics_hook(s.run, input_stage)
                self.assertEqual(result['status'], 'SUCCEEDED')
                r._critics_hook(s.run, input_stage)
            self.assertEqual(len(native_calls), 8)
            self.assertEqual(len(service_calls), 2)
            self.assertEqual(cost_guard.accounting.LEDGER.read_bytes(), before)
            rows = cost_guard.accounting.read_ledger_snapshot()['requests']
            self.assertEqual(sum(row['cost_context']['stage'] == 'critics_plot' for row in rows), 5)
            self.assertEqual(sum(row['cost_context']['stage'] == 'critics_text' for row in rows), 3)
            self.assertTrue(all(row['status'] == 'SETTLED' for row in rows))
            self.assertTrue(all(row['cost_context']['run_id'] == s.run_id for row in rows))
            with self.assertRaisesRegex(ContractError, 'MOCK_RECEIPT_CANNOT_PROVE_LIVE'):
                r.verify_live(SimpleNamespace(run_id=s.run_id, project_root=str(s.root)))
            destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
            if destination:
                files = {p.relative_to(s.root).as_posix(): {'sha256': r.sha(p.read_bytes()),
                    'utf8': p.read_bytes().decode('utf-8')} for p in (s.root / 'runs').rglob('*') if p.is_file()}
                Path(destination + '.critics_signed.json').write_text(json.dumps({
                    'mode': 'MOCK_ONLY', 'simulation_status': 'SIMULATED', 'real_provider_calls': 0,
                    'actual_shared_max_in_flight': json.loads(s.fees.config.read_bytes())['provider']['max_in_flight'],
                    'actual_cnw_requests': cnw_calls, 'actual_native_requests': native_calls,
                    'actual_service_argv': service_calls, 'actual_run_state': r.load_state(s.run),
                    'actual_files': files, 'actual_ledger': rows}, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
