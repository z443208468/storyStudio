"""Signed V2 auxiliary consumers: real executors and fees, terminal simulation."""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tests import test_cnw_live_authorization as authorization_fixtures
from tools import cnw_runner as r, cnw_recovery as recovery, cost_guard
from tools import cnw_live_authorization as auth
from tools.cnw_contract import ContractError
from tools.cnw_test_live_transport import _isolated_live_transport


class SignedAuxiliaryConsumerTests(unittest.TestCase):
    def setUp(self):
        self.subject = authorization_fixtures.LiveAuthorizationTests()
        self.subject.setUp()
        self.addCleanup(self.subject.doCleanups)

    def test_signed_nk_service_shared_account_brief_cache_and_mock_rejection(self):
        s = self.subject
        s.fixture.contract['integrations'] = {'nk': 'ENABLED', 'critics': 'DISABLED'}
        s.contract.write_text(json.dumps(s.fixture.contract, ensure_ascii=False), encoding='utf-8')
        terms = s.full_terms()
        terms['stages'].append('support_hook')
        terms['roles']['support_hook'] = ['nk_pov']
        s.sign(terms=terms)
        # Dependency availability is explicit simulation, never a deployed runtime claim.
        with patch.object(r, '_assert_support_components_available', return_value=None):
            s.create()
        with cost_guard.accounting.locked_ledger():
            pass
        outputs = s.fixture._outputs()
        outputs['scene_cards'] += '\n\n## Scene S1\n### Required beats\n- Mira asks for a screwdriver.\n'
        calls, native_calls, launches = [], [], []
        reflection = 'MOCK_ONLY: Mira may observe the offered screwdriver, not hidden motives.'
        native_result = {'perspectives': [{'reflection': reflection}]}
        def transport(run, *, url, body, request_id):
            stage = request_id.removeprefix('cnw-' + s.run_id + '-').rsplit('-', 1)[0]
            calls.append({'stage': stage, 'messages': body['messages'], 'mode': 'MOCK_ONLY'})
            content = outputs[stage]
            return SimpleNamespace(status_code=200, json=lambda: {
                'id': 'SIMULATED-' + request_id, 'model': r.MODEL,
                'choices': [{'finish_reason': 'stop', 'message': {'content': content}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 10}})
        process = Mock(pid=4567)
        process.poll.return_value = None
        process.terminate.side_effect = lambda: setattr(process.poll, 'return_value', 0)
        listener = Mock()
        listener.getsockname.return_value = ('127.0.0.1', 49127)
        socket_context = Mock()
        socket_context.__enter__ = Mock(return_value=listener)
        socket_context.__exit__ = Mock(return_value=False)
        import subprocess
        import shutil
        real_popen = subprocess.Popen
        real_which = shutil.which
        def launcher_path(command, *args, **kwargs):
            return 'fictional-node.exe' if command == 'node' else real_which(command, *args, **kwargs)
        def launch(command, **kwargs):
            executable = Path(str(command[0])).name.casefold()
            if executable in {'whoami', 'whoami.exe', 'icacls', 'icacls.exe'}:
                return real_popen(command, **kwargs)
            if executable != 'fictional-node.exe':
                raise AssertionError('unexpected subprocess')
            launches.append({'command': command, 'capture': kwargs['env']['STORYSTUDIO_NK_LIVE_CAPTURE'],
                             'request_id': kwargs['env']['STORYSTUDIO_NK_LIVE_REQUEST_ID'],
                             'input_token_cap': kwargs['env']['STORYSTUDIO_NK_MAX_INPUT_TOKENS']})
            process.poll.return_value = None
            return process
        def native_http(url, **kwargs):
            self.assertTrue(url.startswith('http://127.0.0.1:'))
            native_calls.append(copy.deepcopy(kwargs['json']))
            launch_record = launches[-1]
            response = {'id': 'SIMULATED-NK-' + launch_record['request_id'], 'model': r.MODEL,
                'simulation_status': 'SIMULATED', 'fixture_only': True,
                'usage': {'prompt_tokens': 12, 'completion_tokens': 8},
                'choices': [{'finish_reason': 'stop',
                    'message': {'content': json.dumps(native_result, ensure_ascii=False)}}]}
            Path(launch_record['capture']).write_bytes(json.dumps({
                'request_id': launch_record['request_id'], 'response': response}).encode('utf-8'))
            return SimpleNamespace(status_code=200, json=lambda: native_result)
        index = json.loads((r.ROOT / 'patches/nk/PATCH_INDEX.json').read_bytes())
        build = r.ROOT / 'runtime/patched/NK' / index['runtime_build_id']
        real_is_dir, real_is_file = Path.is_dir, Path.is_file
        def is_dir(path):
            return True if path == build / 'node_modules' else real_is_dir(path)
        def is_file(path):
            return True if path == build / 'node_modules/next/dist/bin/next' else real_is_file(path)
        with _isolated_live_transport(s.fixture.temp, data_home=s.fixture.data_home,
                projects=[s.root], runs=[s.run], transport=transport), \
             patch('shutil.which', side_effect=launcher_path), \
             patch('socket.socket', return_value=socket_context), \
             patch('subprocess.Popen', side_effect=launch), \
             patch.object(Path, 'is_dir', is_dir), patch.object(Path, 'is_file', is_file), \
             patch.object(r.httpx, 'get'), patch.object(r.httpx, 'post', side_effect=native_http):
            for stage in ('plot', 'scene_cards', 'writing_brief'):
                recovery.execute_checked(s.run, stage)
            state = r.load_state(s.run)
            hook = state['support_hooks']['nk_pov']
            self.assertEqual(hook['mapping']['source_status'], 'SIMULATED')
            brief_message = next(call['messages'] for call in calls if call['stage'] == 'writing_brief')
            self.assertIn(reflection, json.dumps(brief_message, ensure_ascii=False))
            self.assertEqual(native_calls[0]['eventSequence'][0]['description'], 'Mira asks for a screwdriver.')
            ledger_before = cost_guard.accounting.LEDGER.read_bytes()
            artifact = state['stages']['writing_brief']['artifact']
            brief_before = (s.run / artifact['path']).read_bytes()
            self.assertEqual(recovery.execute_checked(s.run, 'writing_brief')['status'], 'STAGE_REUSED')
            self.assertEqual(r._nk_pov(s.run, r.load_state(s.run), s.fixture.contract)['provider_call'], 'reused')
            self.assertEqual(len(native_calls), 1)
            self.assertEqual(len(calls), 3)
            self.assertEqual(cost_guard.accounting.LEDGER.read_bytes(), ledger_before)
            self.assertEqual((s.run / artifact['path']).read_bytes(), brief_before)
            ledger = cost_guard.accounting.read_ledger_snapshot()
            self.assertEqual(len(ledger['requests']), 4)
            self.assertTrue(all(row['status'] == 'SETTLED' for row in ledger['requests']))
            nk_row = next(row for row in ledger['requests'] if row['cost_context']['stage'] == 'support_hook')
            self.assertEqual(nk_row['reserved_input_token_cap'], 10000)
            self.assertEqual(launches[0]['input_token_cap'], '10000')
            self.assertEqual(sum(row['cost_context']['stage'] == 'support_hook' for row in ledger['requests']), 1)
            self.assertTrue(all(row['cost_context']['run_id'] == s.run_id for row in ledger['requests']))
            self.assertTrue(all(row['mode'] == 'MOCK_ONLY' and row['fixture_only'] is True
                                for row in state['provider_requests']))
            with self.assertRaisesRegex(ContractError, 'MOCK_RECEIPT_CANNOT_PROVE_LIVE'):
                r.verify_live(SimpleNamespace(run_id=s.run_id, project_root=str(s.root)))
            bad = dict(native_calls[0], fictional_tamper=True)
            with patch.object(cost_guard.accounting, 'provider_slot', side_effect=AssertionError('slot forbidden')):
                for entry in (lambda: r._invoke_nk_service(s.run, bad),
                        lambda: r._invoke_nk_service_in_slot(s.run, bad,
                            cost_guard.for_run(s.run, stage='support_hook', model=r.MODEL))):
                    with self.assertRaisesRegex(ContractError, 'NK_CURRENT_CARDS_MISMATCH'):
                        entry()
            self.assertEqual(cost_guard.accounting.LEDGER.read_bytes(), ledger_before)
            destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
            if destination:
                files = {p.relative_to(s.run).as_posix(): {'sha256': r.sha(p.read_bytes()),
                    'utf8': p.read_bytes().decode('utf-8')} for p in s.run.rglob('*') if p.is_file()}
                Path(destination + '.nk_signed.json').write_text(json.dumps({
                    'mode': 'MOCK_ONLY', 'simulation_status': 'SIMULATED', 'real_provider_calls': 0,
                    'actual_requests': calls, 'actual_nk_payloads': native_calls,
                    'actual_run_state': state, 'actual_files': files, 'actual_ledger': ledger},
                    ensure_ascii=False, indent=2), encoding='utf-8')
        with self.assertRaisesRegex(ContractError, 'LIVE_SIMULATED_HISTORY_FORBIDDEN'):
            auth.require_run_authorization(s.run, stage='writing_brief')


if __name__ == '__main__':
    unittest.main()
