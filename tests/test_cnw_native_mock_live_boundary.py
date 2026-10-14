"""Native-only Live refusal with actual signed Plot and original native raw."""
import copy
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from tests import test_cnw_live_authorization as fixtures
from tools import cnw_runner as r, cnw_recovery as recovery, cost_guard
from tools import p2_06_critics_run as native, cnw_critics_adapter as adapter
from tools import cnw_live_authorization as auth
from tools.cnw_contract import ContractError
from tools.project_paths import PathResolutionError
from tools.cnw_test_live_transport import _isolated_live_transport


class NativeMockLiveBoundaryTests(unittest.TestCase):
    def test_shared_enumeration_keeps_pending_and_attempts_without_mutation(self):
        current = {'status': 'SUCCEEDED', 'run_dir': 'current'}
        pending = {'status': 'NATIVE_RESULT_PENDING', 'run_dir': 'pending'}
        attempt = {'status': 'SUCCEEDED', 'run_dir': 'attempt'}
        state = {'support_hooks': {'critics_plot': current, 'critics_text': pending,
                 'nk_pov': {'status': 'SUCCEEDED'}},
                 'support_hook_attempts': [{'hook': 'critics_plot', 'evidence': attempt},
                    {'hook': 'critics_text', 'evidence': {'status': 'FAILED'}},
                    {'hook': 'nk_pov', 'evidence': {'status': 'SUCCEEDED'}}]}
        before = copy.deepcopy(state)
        self.assertEqual(list(recovery.iter_native_support_records(state)), [
            ('critics_plot', current), ('critics_text', pending), ('critics_plot', attempt)])
        self.assertEqual(state, before)

    def test_native_current_attempt_pending_relabel_and_context_exit_refuse(self):
        s = fixtures.LiveAuthorizationTests()
        s.setUp()
        self.addCleanup(s.doCleanups)
        calls, refusals = [], []
        def capture():
            destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
            if not destination or not s.run.exists():
                return
            files = {p.relative_to(s.root).as_posix(): {
                'sha256': r.sha(p.read_bytes()), 'utf8': p.read_bytes().decode('utf-8')}
                for p in (s.root / 'runs').rglob('*') if p.is_file()}
            ledger = cost_guard.accounting.LEDGER
            Path(destination + '.native_boundary.json').write_text(json.dumps({
                'status': 'TERMINAL_CAPTURE_NOT_ACCEPTANCE', 'mode': 'MOCK_ONLY',
                'simulation_status': 'SIMULATED', 'real_provider_calls': 0,
                'actual_native_requests': calls, 'actual_refusals': refusals,
                'actual_run_state': r.load_state(s.run), 'actual_files': files,
                'actual_synthetic_ledger': json.loads(ledger.read_bytes()) if ledger.is_file() else None},
                ensure_ascii=False, indent=2), encoding='utf-8')
        self.addCleanup(capture)
        s.fixture.contract['integrations'] = {'nk': 'DISABLED', 'critics': 'ENABLED'}
        s.contract.write_text(json.dumps(s.fixture.contract, ensure_ascii=False), encoding='utf-8')
        terms = s.full_terms()
        terms['stages'].append('critics_plot')
        terms['roles']['critics_plot'] = ['critics_plot']
        s.sign(terms=terms)
        s.create()
        with cost_guard.accounting.locked_ledger():
            pass
        replies = ['Expert 1\nStructure persona\nExpert 2\nEnding persona\nExpert 3\nOriginal persona\nLeader\nLeader persona',
            'Question: Is the repair visible?\nWhy: mock.',
            'Question: Is the offer earned?\nWhy: mock.',
            'Question: Does Mira choose?\nWhy: mock.',
            'Question: Is the offer earned?\nWhy: mock.']
        def cnw_response(run, *, url, body, request_id):
            return SimpleNamespace(status_code=200, json=lambda: {
                'id': 'SIMULATED-' + request_id, 'model': r.MODEL,
                'choices': [{'finish_reason': 'stop', 'message': {'content': s.fixture._outputs()['plot']}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 10}})
        def native_response(client, request, *args, **kwargs):
            self.assertEqual(request.url.host, 'api.deepseek.com')
            number = len(calls)
            calls.append(json.loads(request.read()))
            return httpx.Response(200, request=request, json={
                'id': 'SIMULATED-NATIVE-' + str(number), 'model': r.MODEL,
                'object': 'chat.completion', 'created': 0,
                'simulation_status': 'SIMULATED', 'fixture_only': True,
                'choices': [{'index': 0, 'finish_reason': 'stop',
                            'message': {'role': 'assistant', 'content': replies[number]}}],
                'usage': {'prompt_tokens': 12, 'completion_tokens': 8, 'total_tokens': 20}})
        original_run = subprocess.run
        def service(command, **kwargs):
            if len(command) < 2 or Path(str(command[1])) != r.ROOT / 'tools/p2_06_critics_run.py':
                return original_run(command, **kwargs)
            cwd = Path.cwd()
            try:
                result = native.main(command[2:])
            finally:
                os.chdir(cwd)
            return subprocess.CompletedProcess(command, result, stdout='', stderr='')
        with _isolated_live_transport(s.fixture.temp, data_home=s.fixture.data_home,
                projects=[s.root], runs=[s.run], transport=cnw_response), \
             patch('subprocess.run', side_effect=service), patch.object(httpx.Client, 'send', native_response):
            recovery.execute_checked(s.run, 'plot')
            original = r.load_state(s.run)
            hook = original['support_hooks']['critics_plot']
            self.assertEqual(len(calls), 5)
            native_root = Path(hook['run_dir'])
            receipt_file = native_root / 'run_receipt.json'
            receipt_bytes = receipt_file.read_bytes()
            input_path = s.run / hook['input_artifact']['path']
            raw_before = (native_root / 'provider-calls.json').read_bytes()
            ledger_before = cost_guard.accounting.LEDGER.read_bytes()
            reader = adapter._read_native_result
            pending = copy.deepcopy(hook)
            pending['status'] = 'NATIVE_RESULT_PENDING'
            with patch.object(adapter, '_read_native_result', wraps=reader) as reads:
                consumed = adapter.read_native_support_records(s.run, [
                    ('critics_plot', hook, input_path), ('critics_plot', pending, input_path),
                    ('critics_plot', copy.deepcopy(hook), input_path)])
                self.assertEqual(reads.call_count, 1)
                self.assertEqual(len(consumed), 3)
                self.assertTrue(all(row[2]['result'] == hook['result'] for row in consumed))
            for variant in ('hook_action', 'input_sha', 'input_path'):
                bad, bad_name, bad_path = copy.deepcopy(pending), 'critics_plot', input_path
                if variant == 'hook_action':
                    bad_name = 'critics_text'
                elif variant == 'input_sha':
                    bad['input_artifact']['sha256'] = '0' * 64
                else:
                    bad_path = s.run / 'artifacts/support/wrong-input.md'
                    bad_path.write_text('A different fictional input.', encoding='utf-8')
                with self.subTest(cache_variant=variant), patch.object(
                        adapter, '_read_native_result', wraps=reader) as reads, \
                     self.assertRaises(ContractError) as rejected:
                    adapter.read_native_support_records(s.run, [
                        ('critics_plot', hook, input_path), (bad_name, bad, bad_path)])
                self.assertEqual(reads.call_count, 2 if variant == 'hook_action' else 1)
                refusals.append({'variant': 'cache_' + variant, 'code': rejected.exception.code,
                                 'message': str(rejected.exception)})
            for label, path in (('raw', native_root / 'provider-calls.json'),
                    ('receipt', receipt_file), ('output', native_root / 'critique.json'),
                    ('input', input_path)):
                before_bytes = path.read_bytes()
                def mutate_after_read(*args, **kwargs):
                    result = reader(*args, **kwargs)
                    path.write_bytes(before_bytes + b' ')
                    return result
                try:
                    with self.subTest(end_file=label), patch.object(
                            adapter, '_read_native_result', side_effect=mutate_after_read) as reads, \
                         self.assertRaises(ContractError) as rejected:
                        adapter.read_native_support_records(s.run, [('critics_plot', hook, input_path)])
                    self.assertEqual(reads.call_count, 1)
                    self.assertEqual(rejected.exception.code, 'CRITICS_EVIDENCE_CHANGED')
                    refusals.append({'variant': 'end_' + label, 'code': rejected.exception.code,
                                     'message': str(rejected.exception)})
                finally:
                    path.write_bytes(before_bytes)
            for label, path in (('run_binding', s.run / 'run_state.json'),
                                ('registration', s.root / 'project_identity.json')):
                before_bytes = path.read_bytes()
                original_for_run = cost_guard.for_run
                def drift_after_read(*args, **kwargs):
                    result = reader(*args, **kwargs)
                    if label == 'run_binding':
                        changed = json.loads(before_bytes)
                        changed['project_instance_id'] = 'foreign-instance'
                        path.write_text(json.dumps(changed), encoding='utf-8')
                    else:
                        path.write_bytes(before_bytes + b' ')
                    return result
                try:
                    with self.subTest(end_binding=label), patch.object(
                            adapter, '_read_native_result', side_effect=drift_after_read) as reads, \
                         patch.object(cost_guard, 'for_run', wraps=original_for_run) as accounts, \
                         self.assertRaises((ContractError, PathResolutionError)) as rejected:
                        adapter.read_native_support_records(s.run, [('critics_plot', hook, input_path)])
                    self.assertEqual(reads.call_count, 1)
                    self.assertEqual(accounts.call_count, 2)
                    refusals.append({'variant': 'end_' + label,
                        'code': getattr(rejected.exception, 'code', None),
                        'message': str(rejected.exception)})
                finally:
                    path.write_bytes(before_bytes)
            self.assertEqual(len(calls), 5)
            self.assertEqual(cost_guard.accounting.LEDGER.read_bytes(), ledger_before)
            # Surface parent labels are changed only to reach the native gate;
            # no claim is made that those parent raw responses could prove Live.
            for variant in ('current', 'attempt', 'pending', 'relabel'):
                changed = copy.deepcopy(original)
                for row in changed['provider_requests']:
                    row.update(mode='LIVE', fixture_only=False, simulation_status='LIVE')
                if variant == 'attempt':
                    changed['support_hook_attempts'] = [{'hook': 'critics_plot', 'evidence': hook}]
                    changed['support_hooks']['critics_plot'] = {'status': 'DISABLED'}
                elif variant == 'pending':
                    changed['support_hooks']['critics_plot']['status'] = 'NATIVE_RESULT_PENDING'
                elif variant == 'relabel':
                    changed['support_hooks']['critics_plot'].update(mode='LIVE', fixture_only=False, simulation_status='LIVE')
                    receipt = json.loads(receipt_bytes)
                    receipt.update(mode='LIVE', fixture_only=False, simulation_status='LIVE')
                    receipt_file.write_bytes(json.dumps(receipt).encode('utf-8'))
                r.save_state(s.run, changed)
                with self.subTest(variant=variant), self.assertRaises(ContractError) as rejected:
                    r.verify_live(SimpleNamespace(run_id=s.run_id, project_root=str(s.root)))
                self.assertEqual(rejected.exception.code, 'MOCK_RECEIPT_CANNOT_PROVE_LIVE')
                self.assertTrue('critics_plot' in str(rejected.exception) or native_root.name in str(rejected.exception))
                refusals.append({'variant': variant, 'code': rejected.exception.code,
                                 'message': str(rejected.exception)})
                receipt_file.write_bytes(receipt_bytes)
                self.assertEqual((native_root / 'provider-calls.json').read_bytes(), raw_before)
                self.assertEqual(cost_guard.accounting.LEDGER.read_bytes(), ledger_before)
            r.save_state(s.run, original)
        with self.assertRaisesRegex(ContractError, 'MOCK_RECEIPT_CANNOT_PROVE_LIVE'):
            adapter.read_native_result(native_root, action='plan-critique', input_path=input_path,
                                       parent_run_dir=s.run, parent_stage='critics_plot')
        changed = copy.deepcopy(original)
        for row in changed['provider_requests']:
            row.update(mode='LIVE', fixture_only=False, simulation_status='LIVE')
        r.save_state(s.run, changed)
        with self.assertRaisesRegex(ContractError, 'MOCK_RECEIPT_CANNOT_PROVE_LIVE'):
            auth.require_run_authorization(s.run, stage='plot')
        r.save_state(s.run, original)
        self.assertEqual(len(calls), 5)
        self.assertEqual(receipt_file.read_bytes(), receipt_bytes)
        self.assertEqual((native_root / 'provider-calls.json').read_bytes(), raw_before)
        self.assertEqual(cost_guard.accounting.LEDGER.read_bytes(), ledger_before)


if __name__ == '__main__':
    unittest.main()
