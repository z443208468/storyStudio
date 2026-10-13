"""W10 V2 adapters consume the original CNW engine, with owned simulation."""
from contextlib import redirect_stdout, contextmanager
import copy
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_cnw_live_authorization as grants
from tools import cnw_runner as r, cnw_live_provider as provider, cnw_live_executor as executor
from tools import cost_guard, cnw_request_identity as requests
from tools.cnw_contract import ContractError
from tools.cnw_test_live_transport import _isolated_live_transport


class W10V2ConsumerTests(unittest.TestCase):
    def setUp(self):
        self.owner = grants.LiveAuthorizationTests()
        self.owner.setUp(); self.addCleanup(self.owner.doCleanups)
        self.owner.sign(terms=self.owner.full_terms()); self.owner.create()
        self.run = self.owner.run
        with cost_guard.accounting.locked_ledger(): pass
        call = requests.expected_requests(self.run, stage='plot', role_id='plot_agent')[0]
        self.args = {'stage': 'plot', 'role_id': 'plot_agent', 'messages': call['messages'],
            'input_sha256': r.sha(json.dumps(call['messages'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()),
            'input_token_cap': r._estimate_input_tokens(call['messages']) + 100,
            'output_token_cap': call['output_cap']}
        self.sent = []

    def session(self):
        def reply(run, *, url, body, request_id):
            self.sent.append({'body': copy.deepcopy(body), 'request_id': request_id})
            return SimpleNamespace(status_code=200, json=lambda: {
                'id': 'SIMULATED-W10-' + str(len(self.sent)), 'model': r.MODEL,
                'simulation_status': 'SIMULATED', 'fixture_only': True,
                'choices': [{'finish_reason': 'stop', 'message': {'content': self.owner.fixture._outputs()[
                    'scene_cards' if '-scene_cards-' in request_id else 'plot']}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 10}})
        return _isolated_live_transport(self.owner.fixture.temp, data_home=self.owner.fixture.data_home,
            projects=[self.owner.root], runs=[self.run], transport=reply)

    def save_evidence(self, name):
        destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
        if destination:
            state = r.load_state(self.run)
            files = {}
            for row in state.get('provider_requests', []):
                for key in ('request_path', 'raw_response_path'):
                    raw = (self.run/row[key]).read_bytes()
                    files[row[key]] = {'sha256': r.sha(raw), 'utf8': raw.decode('utf-8')}
            Path(destination+'.'+name+'.json').write_text(json.dumps({'mode': 'MOCK_ONLY',
                'simulation_status': 'SIMULATED', 'http': self.sent, 'run_state': state, 'files': files,
                'synthetic_ledger': cost_guard.accounting.read_ledger_snapshot()}, ensure_ascii=False, indent=2), encoding='utf-8')

    def positive(self, operation, name):
        with self.session():
            content, receipt = operation(self.run, **self.args)
            self.assertIn('Key Scenes', content)
            self.assertEqual(len(self.sent), 1)
            self.assertEqual(receipt['stage'], 'plot')
            self.assertEqual(receipt['role_id'], 'plot_agent')
            self.assertEqual(receipt['mode'], 'MOCK_ONLY')
            self.assertTrue(receipt['fixture_only'])
            self.assertEqual(receipt['simulation_status'], 'SIMULATED')
            reused, prior = operation(self.run, **self.args)
            self.assertEqual(content, reused)
            self.assertEqual(receipt['request_id'], prior['request_id'])
            self.assertEqual(len(self.sent), 1)
            row = cost_guard.accounting.read_ledger_snapshot()['requests'][0]
            self.assertEqual(row['status'], 'SETTLED')
            self.assertEqual(row['cost_context']['stage'], 'plot')
            self.assertEqual(row['cost_context']['project_instance_id'], self.owner.fixture.contract['project_instance_id'])
        self.save_evidence(name)

    def test_actual_high_entry_calls_shared_transport_and_reuses_exact_receipt(self):
        self.positive(provider.complete, 'high')

    def test_actual_low_entry_calls_shared_transport_and_reuses_exact_receipt(self):
        self.positive(provider._complete_in_slot, 'low')

    def test_both_entries_reject_wrong_request_before_slot_fee_or_http(self):
        invalid = []
        for field, value in (('role_id', None), ('role_id', 'prose_agent_1'), ('input_sha256', 'a'*64),
                             ('input_token_cap', True), ('input_token_cap', 1),
                             ('output_token_cap', True), ('output_token_cap', 4001)):
            changed = copy.deepcopy(self.args); changed[field] = value; invalid.append((field, changed))
        changed = copy.deepcopy(self.args); changed['extra'] = {'unapproved': True}; invalid.append(('extra', changed))
        changed = copy.deepcopy(self.args); changed['messages'][1]['content'] += ' Unselected secret Canon.'
        changed['input_sha256'] = r.sha(json.dumps(changed['messages'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
        invalid.append(('self_rehashed_messages', changed))
        with self.session(), patch.object(cost_guard.accounting, 'provider_slot', side_effect=AssertionError('slot reached')):
            for operation in (provider.complete, provider._complete_in_slot):
                for name, args in invalid:
                    with self.subTest(operation=operation.__name__, case=name), self.assertRaises(ContractError):
                        operation(self.run, **args)
                with self.assertRaisesRegex(ContractError, 'LIVE_OWNED_TRANSPORT_REQUIRED'):
                    operation(self.run, **self.args, transport=lambda *args: None)
            with self.assertRaisesRegex(ContractError, 'COST_BINDINGS_CHANGED'):
                provider._complete_in_slot(self.run, **self.args, account=object())
        self.assertEqual(self.sent, [])
        self.assertEqual(cost_guard.accounting.read_ledger_snapshot()['requests'], [])

    def test_actual_cli_prepares_executes_checked_plot_and_reuses_same_identity(self):
        with self.session():
            output = io.StringIO()
            with redirect_stdout(output):
                executor.main(['--run-dir', str(self.run), '--prepare-generic-stage', 'plot'])
            prepared = json.loads(output.getvalue())
            path = self.run / prepared['packet']
            original = path.read_bytes()
            self.assertFalse(json.loads(original)['self_authorization'])
            self.assertEqual(self.sent, [])
            output = io.StringIO()
            with redirect_stdout(output):
                executor.main(['--run-dir', str(self.run), '--stage', 'plot', '--execute-generic-stage', '--packet', prepared['packet']])
            result = json.loads(output.getvalue())
            self.assertEqual(result['status'], 'STAGE_MATERIALIZED')
            self.assertEqual(len(self.sent), 1)
            state = r.load_state(self.run)
            artifact = state['stages']['plot']['artifact']
            raw = (self.run/artifact['path']).read_bytes()
            self.assertTrue(raw)
            self.assertEqual(r.sha(raw), artifact['sha256'])
            reused = executor.execute_v2_stage(self.run, stage='plot', packet_path=prepared['packet'])
            self.assertEqual(reused['status'], 'STAGE_REUSED')
            self.assertEqual(reused['provider_requests_added'], 0)
            self.assertEqual(len(self.sent), 1)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual((self.run/artifact['path']).read_bytes(), raw)
            corrupted = json.loads(original); corrupted['project_instance_id'] = 'OTHER'
            path.write_text(json.dumps(corrupted), encoding='utf-8')
            with self.assertRaisesRegex(ContractError, 'LIVE_STAGE_PACKET_STALE'):
                executor.execute_v2_stage(self.run, stage='plot', packet_path=prepared['packet'])
            path.write_bytes(original)
            self.assertEqual(len(self.sent), 1)
        self.save_evidence('cli_plot')

    def test_v2_legacy_manual_acceptance_and_pov_paths_reject_without_writes(self):
        before = (self.run/'run_state.json').read_bytes()
        with self.session():
            for action in (
                lambda: provider.accept_validated_stage(self.run, stage='plot', content='False success', validation={'status': 'CONTENT_VALID'}),
                lambda: executor.accept_controller_role_output(self.run, stage='plot', evidence_path='nonexistent.json'),
                lambda: provider.record_nk_pov_receipt(self.run, {}),
                lambda: executor.bind_nk_receipt(self.run, 'nonexistent.json'),
                lambda: executor.record_nk_budget_failure(self.run, 'UNKNOWN'),
            ):
                with self.assertRaises(ContractError): action()
        self.assertEqual(before, (self.run/'run_state.json').read_bytes())
        self.assertEqual(self.sent, [])

    def test_v2_snapshot_missing_or_relabelled_cannot_enter_legacy_acceptance(self):
        path = self.run/'artifacts/contract.json'
        raw = path.read_bytes()
        for mode in ('missing', 'relabelled'):
            if mode == 'missing': path.rename(path.with_suffix('.preserved.json'))
            else:
                changed = json.loads(raw); changed['schema_version'] = 'cnw_work_unit_v1'
                path.write_text(json.dumps(changed), encoding='utf-8')
            try:
                for action in (
                    lambda: provider.complete(self.run, **self.args),
                    lambda: provider.accept_validated_stage(self.run, stage='plot', content='False success', validation={'status': 'CONTENT_VALID'}),
                    lambda: executor.accept_controller_role_output(self.run, stage='plot', evidence_path='fake.json'),
                ):
                    with self.subTest(mode=mode), self.assertRaisesRegex(ContractError, 'LIVE_RUN_CONTRACT_CHANGED'):
                        action()
            finally:
                if mode == 'missing': path.with_suffix('.preserved.json').rename(path)
                else: path.write_bytes(raw)
        self.assertEqual(self.sent, [])
        self.assertEqual(cost_guard.accounting.read_ledger_snapshot()['requests'], [])

    def test_stage_packet_rechecked_inside_the_existing_execution_lock(self):
        prepared = executor.prepare_v2_stage(self.run, stage='plot')
        original_packet = (self.run/prepared['packet']).read_bytes()
        entered = []
        actual_lock = r.locked_run
        @contextmanager
        def observe_lock(run, *args, **kwargs):
            # Real lock, no replacement executor. At lock acquisition the
            # test changes the prepared packet's operation identity, modelling
            # a change while the caller waited to enter its critical section.
            with actual_lock(run, *args, **kwargs):
                if kwargs.get('lock_name') == 'execution.lock' and not entered:
                    entered.append(True)
                    value = json.loads(original_packet)
                    value['stage_identity']['prepared_input_changed'] = True
                    (self.run/prepared['packet']).write_text(json.dumps(value), encoding='utf-8')
                yield
        with self.session(), patch.object(r, 'locked_run', side_effect=observe_lock):
            with self.assertRaisesRegex(ContractError, 'LIVE_STAGE_PACKET_STALE'):
                executor.execute_v2_stage(self.run, stage='plot', packet_path=prepared['packet'])
        self.assertEqual(entered, [True])
        self.assertEqual(self.sent, [])
        self.assertEqual(cost_guard.accounting.read_ledger_snapshot()['requests'], [])
        (self.run/prepared['packet']).write_bytes(original_packet)
        with self.session():
            result = executor.execute_v2_stage(self.run, stage='plot', packet_path=prepared['packet'])
            self.assertEqual(result['status'], 'STAGE_MATERIALIZED')
        self.assertEqual(len(self.sent), 1)

    def test_changed_real_predecessor_rejects_old_packet_and_new_packet_reads_new_artifact(self):
        with self.session():
            executor.execute_v2_stage(self.run, stage='plot')
            prepared = executor.prepare_v2_stage(self.run, stage='cards')
            original = r.load_state(self.run)['stages']['plot']['artifact']
            original_raw = (self.run/original['path']).read_bytes()
            count = len(self.sent)
            actual_lock = r.locked_run
            changed = []
            @contextmanager
            def update_before_entry(run, *args, **kwargs):
                with actual_lock(run, *args, **kwargs):
                    if kwargs.get('lock_name') == 'execution.lock' and not changed:
                        changed.append(True)
                        # Controlled unit-input publication in this owned Run;
                        # not a claim of another model-generated Plot.
                        r._persist_stage(self.run, 'plot', 'artifacts/unit-updated-plot.md',
                            self.owner.fixture._outputs()['plot']+'\nUNIT_CHANGED_PLOT_INPUT')
                    yield
            with patch.object(r, 'locked_run', side_effect=update_before_entry):
                with self.assertRaisesRegex(ContractError, 'LIVE_STAGE_PACKET_STALE'):
                    executor.execute_v2_stage(self.run, stage='cards', packet_path=prepared['packet'])
            self.assertEqual(len(self.sent), count)
            self.assertEqual(len(cost_guard.accounting.read_ledger_snapshot()['requests']), count)
            fresh = executor.prepare_v2_stage(self.run, stage='scene_cards')
            result = executor.execute_v2_stage(self.run, stage='scene_cards', packet_path=fresh['packet'])
            self.assertEqual(result['status'], 'STAGE_MATERIALIZED')
            self.assertEqual(len(self.sent), count+1)
            self.assertIn('UNIT_CHANGED_PLOT_INPUT', json.dumps(self.sent[-1]['body']['messages']))
            self.assertEqual((self.run/original['path']).read_bytes(), original_raw)
        self.save_evidence('changed_predecessor')

    def test_direct_low_entry_cannot_skip_an_exhausted_shared_slot(self):
        config = json.loads(cost_guard.accounting.CONFIG.read_bytes())
        config['provider']['max_in_flight'] = 1
        cost_guard.accounting.CONFIG.write_text(json.dumps(config), encoding='utf-8')
        self.owner.sign(terms=self.owner.full_terms())
        counter = [0]
        def virtual_clock():
            counter[0] += 300
            return counter[0]
        with self.session(), cost_guard.accounting.provider_slot():
            with patch.object(cost_guard.accounting.time, 'monotonic', side_effect=virtual_clock):
                with self.assertRaisesRegex(TimeoutError, 'PROVIDER_SLOT_TIMEOUT'):
                    provider._complete_in_slot(self.run, **self.args)
        self.assertEqual(self.sent, [])
        self.assertEqual(cost_guard.accounting.read_ledger_snapshot()['requests'], [])
