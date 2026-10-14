"""Two real registered signed consumers; only terminal HTTP is simulated."""
from contextlib import contextmanager
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
from tools import cnw_live_authorization as auth, p2_06_critics_run as native
from tools import cnw_critics_adapter as adapter
from tools.cnw_contract import ContractError
from tools.cnw_project import import_source, init_registered_project
from tools.project_paths import create_project
from tools.cnw_test_live_transport import _isolated_live_transport


class SignedCriticsAccountingTests(unittest.TestCase):
    def test_signed_instances_share_slots_settle_and_keep_unknown_without_replay(self):
        first = fixtures.LiveAuthorizationTests()
        first.setUp()
        self.addCleanup(first.doCleanups)
        second = copy.copy(first)
        second.fixture = copy.copy(first.fixture)
        registered = create_project(project_id='TIDELINE-SECOND', data_home=first.fixture.data_home)
        second.root = second.fixture.project = Path(registered['project_root'])
        init_registered_project(second.root)
        second.fixture._prepare_project_inputs()
        second.fixture.source_a = import_source(input_file=first.fixture.source_a_path, project_root=second.root)
        second.fixture.source_b = import_source(input_file=first.fixture.source_b_path, project_root=second.root)
        second.fixture.contract = second.fixture._make_adapt_contract()
        second.contract = second.root / 'contracts/ADAPT-HINGE-01.json'
        second.run_id = 'SIGNED-OTHER-RUN'
        second.run = second.root / 'runs' / second.run_id
        def terminal_capture():
            destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
            if not destination:
                return
            captured, states = {}, []
            for number, subject in enumerate((first, second)):
                if subject.run.exists():
                    states.append(r.load_state(subject.run))
                for path in (subject.root / 'runs').rglob('*'):
                    if path.is_file():
                        raw = path.read_bytes()
                        captured[str(number) + '/' + path.relative_to(subject.root).as_posix()] = {
                            'sha256': r.sha(raw), 'utf8': raw.decode('utf-8')}
            ledger = cost_guard.accounting.LEDGER
            Path(destination + '.critics_accounting.terminal.json').write_text(json.dumps({
                'status': 'TERMINAL_CAPTURE_NOT_ACCEPTANCE', 'mode': 'MOCK_ONLY',
                'simulation_status': 'SIMULATED', 'real_provider_calls': 0,
                'actual_run_states': states, 'actual_files': captured,
                'actual_synthetic_ledger': json.loads(ledger.read_bytes()) if ledger.is_file() else None},
                ensure_ascii=False, indent=2), encoding='utf-8')
        self.addCleanup(terminal_capture)
        for subject in (first, second):
            subject.fixture.contract['integrations'] = {'nk': 'DISABLED', 'critics': 'ENABLED'}
            subject.contract.write_text(json.dumps(subject.fixture.contract, ensure_ascii=False), encoding='utf-8')
            terms = subject.full_terms()
            terms['stages'].append('critics_plot')
            terms['roles']['critics_plot'] = ['critics_plot']
            subject.sign(terms=terms)
            subject.create()
        with cost_guard.accounting.locked_ledger():
            pass
        calls, slots, services = [], [], []
        holding = [False]
        real_slot = cost_guard.accounting.provider_slot
        @contextmanager
        def observed_slot():
            with real_slot():
                self.assertFalse(holding[0])
                holding[0] = True
                slots.append(str(cost_guard.accounting.LEDGER.parent / 'provider-slots'))
                try:
                    yield
                finally:
                    holding[0] = False
        replies = ['Expert 1\nStructure persona\nExpert 2\nEnding persona\nExpert 3\nOriginal persona\nLeader\nLeader persona',
            'Question: Is the repair visible?\nWhy: MOCK_ONLY.',
            'Question: Is the offer earned?\nWhy: MOCK_ONLY.',
            'Question: Does Mira choose?\nWhy: MOCK_ONLY.',
            'Question: Is the offer earned?\nWhy: MOCK_ONLY.']
        def cnw_response(run, *, url, body, request_id):
            self.assertTrue(holding[0])
            return SimpleNamespace(status_code=200, json=lambda: {
                'id': 'SIMULATED-' + request_id, 'model': r.MODEL,
                'choices': [{'finish_reason': 'stop', 'message': {'content': first.fixture._outputs()['plot']}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 10}})
        def native_response(client, request, *args, **kwargs):
            self.assertTrue(holding[0])
            self.assertEqual(request.url.host, 'api.deepseek.com')
            number = len(calls)
            calls.append(json.loads(request.read()))
            if number == 5:
                raise RuntimeError('SIMULATED_TRANSPORT_INTERRUPTION')
            self.assertLess(number, 5, 'unknown outcome must not retry')
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
            services.append(list(command))
            previous_cwd = Path.cwd()
            try:
                result = native.main(command[2:])
            finally:
                os.chdir(previous_cwd)
            return subprocess.CompletedProcess(command, result, stdout='', stderr='')
        with _isolated_live_transport(first.fixture.temp, data_home=first.fixture.data_home,
                projects=[first.root, second.root], runs=[first.run, second.run], transport=cnw_response), \
             patch.object(cost_guard.accounting, 'provider_slot', new=observed_slot), \
             patch('subprocess.run', side_effect=service), patch.object(httpx.Client, 'send', native_response):
            recovery.execute_checked(first.run, 'plot')
            with self.assertRaisesRegex(ContractError, 'CRITICS_INVOCATION_FAILED'):
                recovery.execute_checked(second.run, 'plot')
            self.assertEqual(len(calls), 6)
            self.assertEqual(len(services), 2)
            self.assertEqual(slots, [str(first.fees.ledger.parent / 'provider-slots')] * 8)
            ledger_before = cost_guard.accounting.LEDGER.read_bytes()
            rows = json.loads(ledger_before)['requests']
            self.assertEqual(len(rows), 8)
            ids = [json.loads((subject.root / 'project_identity.json').read_bytes())['project_instance_id']
                   for subject in (first, second)]
            self.assertEqual([r.load_state(subject.run)['source_identity']['project_instance_id']
                              for subject in (first, second)], ids)
            self.assertNotEqual(ids[0], ids[1])
            native_rows = [row for row in rows if row['cost_context']['stage'] == 'critics_plot']
            self.assertEqual(len(native_rows), 6)
            settled = [row for row in native_rows if row['status'] == 'SETTLED']
            unknown = [row for row in native_rows if row['status'] == 'UNKNOWN_NOT_ZERO']
            self.assertEqual(len(settled), 5)
            self.assertEqual(len(unknown), 1)
            self.assertTrue(all(row['cost_context']['project_instance_id'] == ids[0] for row in settled))
            self.assertEqual(unknown[0]['cost_context']['project_instance_id'], ids[1])
            self.assertGreater(float(unknown[0]['reserved_cny']), 0)
            hooks = [r.load_state(subject.run)['support_hooks']['critics_plot'] for subject in (first, second)]
            input_path = first.run / hooks[0]['input_artifact']['path']
            consumed = adapter.read_native_result(hooks[0]['run_dir'], action='plan-critique',
                input_path=input_path, parent_run_dir=first.run, parent_stage='critics_plot')
            self.assertEqual(consumed['result']['inspector'], 'Is the offer earned?')
            with self.assertRaisesRegex(ContractError, 'CRITICS_PARENT_RUN_BINDING_INVALID'):
                adapter.read_native_result(hooks[1]['run_dir'], action='plan-critique',
                    input_path=input_path, parent_run_dir=first.run, parent_stage='critics_plot')
            for subject, hook, count in zip((first, second), hooks, (5, 1)):
                scoped = json.loads((Path(hook['run_dir']) / 'p2-cost-ledger.json').read_bytes())
                self.assertEqual(len(scoped['requests']), count)
                self.assertTrue(all(row['cost_context']['run_id'] == subject.run_id for row in scoped['requests']))
            state_before = (second.run / 'run_state.json').read_bytes()
            second.sign(terms=copy.deepcopy(second.terms))
            self.assertEqual((second.run / 'run_state.json').read_bytes(), state_before)
            self.assertEqual(cost_guard.accounting.LEDGER.read_bytes(), ledger_before)
            self.assertEqual(cost_guard.accounting.read_ledger_snapshot()['requests'][-1], unknown[0])
            self.assertEqual(len(calls), 6)
            self.assertEqual(len(slots), 8)
            destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
            if destination:
                captured = {}
                for number, subject in enumerate((first, second)):
                    for path in (subject.root / 'runs').rglob('*'):
                        if path.is_file():
                            raw = path.read_bytes()
                            captured[str(number) + '/' + path.relative_to(subject.root).as_posix()] = {
                                'sha256': r.sha(raw), 'utf8': raw.decode('utf-8')}
                Path(destination + '.critics_accounting.json').write_text(json.dumps({
                    'mode': 'MOCK_ONLY', 'simulation_status': 'SIMULATED', 'real_provider_calls': 0,
                    'actual_native_requests': calls, 'actual_service_argv': services, 'actual_slot_paths': slots,
                    'actual_run_states': [r.load_state(subject.run) for subject in (first, second)],
                    'actual_ledger': rows, 'actual_files': captured, 'unknown_preserved_on_renewal': True},
                    ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
