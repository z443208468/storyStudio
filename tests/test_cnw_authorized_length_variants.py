"""Actual bounded V2 executors with the last HTTP boundary simulated.

Predecessors are explicit unit fixtures, not a claim of another complete E2E.
"""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

from tests import test_cnw_live_authorization as grants
from tools import cnw_runner as r, cnw_live_authorization as auth
from tools import cnw_request_identity as identity
from tools.cnw_contract import ContractError
from tools.cnw_test_live_transport import _isolated_live_transport


class AuthorizedLengthVariantTests(unittest.TestCase):
    def setUp(self):
        self.owner = grants.LiveAuthorizationTests()
        self.owner.setUp()
        self.addCleanup(self.owner.doCleanups)
        self.owner.sign(terms=self.owner.full_terms())
        self.owner.create()
        self.run = self.owner.run
        self.outputs = self.owner.fixture._outputs()
        for stage in ('plot', 'scene_cards', 'writing_brief'):
            r._persist_stage(self.run, stage, f'artifacts/unit-{stage}.md', self.outputs[stage])
        with grants.cost_guard.accounting.locked_ledger(): pass
        self.sent = []

    def session(self, replies):
        responses = iter(replies)
        def transport(run, *, url, body, request_id):
            self.sent.append({'body': copy.deepcopy(body), 'request_id': request_id})
            content = next(responses)
            return SimpleNamespace(status_code=200, json=lambda: {
                'id': 'SIMULATED-LENGTH-' + str(len(self.sent)), 'model': r.MODEL,
                'simulation_status': 'SIMULATED', 'fixture_only': True,
                'usage': {'prompt_tokens': 10, 'completion_tokens': 10},
                'choices': [{'finish_reason': 'stop', 'message': {'content': content}}]})
        return _isolated_live_transport(self.owner.fixture.temp, data_home=self.owner.fixture.data_home,
            projects=[self.owner.root], runs=[self.run], transport=transport)

    def evidence(self, name):
        target = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
        if target:
            state = r.load_state(self.run)
            files = {}
            for record in state['stages'].values():
                if record.get('artifact'):
                    path = record['artifact']['path']
                    raw = (self.run / path).read_bytes()
                    files[path] = {'sha256': r.sha(raw), 'utf8': raw.decode('utf-8')}
            Path(target + '.' + name + '.json').write_text(json.dumps({
                'scope': 'ACTUAL_BOUNDED_EXECUTOR_WITH_UNIT_PREDECESSORS',
                'mode': 'MOCK_ONLY', 'simulation_status': 'SIMULATED',
                'requests': self.sent, 'run_state': state, 'files': files,
                'ledger': grants.cost_guard.accounting.read_ledger_snapshot()}, ensure_ascii=False, indent=2), encoding='utf-8')

    def test_advisory_underlength_keeps_original_without_continuation(self):
        short = 'Mira asks for help.'
        continuation = 'The keeper offers a tool. She steadies the door as he tightens the hinge, then thanks him and asks where to return it.'
        with self.session([short, continuation]):
            result = r.execute_prose(self.run)
            self.assertEqual(len(self.sent), 1)
            self.assertEqual(len(result['receipts']), 1)
            self.assertIn('creative guidance', self.sent[0]['body']['messages'][0]['content'])
            body = r._read_stage_text(self.run, r.load_state(self.run), 'prose')
            self.assertEqual(body, short)
            with self.assertRaisesRegex(ContractError, 'LENGTH_RETRY_DISABLED'):
                identity.expected_requests(self.run, stage='prose', role_id='prose_agent_3')
            call = identity.expected_requests(self.run, stage='prose', role_id='prose_agent_1')[0]
            forged = copy.deepcopy(call); forged['messages'][1]['content'] += ' secret Canon'
            with self.assertRaisesRegex(ContractError, 'LIVE_REQUEST_BINDING_MISMATCH'):
                auth.verify_request(self.run, **forged)
        self.evidence('prose_continuation')

    def test_advisory_overlimit_keeps_original_without_rewrite(self):
        oversized = 'A' * 400
        replacement = self.outputs['refine']
        with self.session([oversized, replacement]):
            result = r.execute_prose(self.run)
            self.assertEqual(len(self.sent), 1)
            self.assertNotIn('Rewrite the complete prose', self.sent[0]['body']['messages'][0]['content'])
            body = r._read_stage_text(self.run, r.load_state(self.run), 'prose')
            self.assertEqual(body, oversized)
            self.assertEqual(len(result['receipts']), 1)
            with self.assertRaisesRegex(ContractError, 'LENGTH_RETRY_DISABLED'):
                identity.expected_requests(self.run, stage='prose', role_id='prose_agent_3')
        self.evidence('prose_overlimit')

    def test_advisory_refine_uses_finding_not_length_and_no_change_zero_calls(self):
        r._persist_stage(self.run, 'prose', 'artifacts/unit-prose.md', self.outputs['prose'])
        for stage in ('lint_layer1', 'lint_layer2', 'multi_lens_review'):
            r._persist_stage(self.run, stage, f'artifacts/unit-{stage}.json', '{"findings": []}')
        r._persist_stage(self.run, 'adversarial_verify', 'artifacts/unit-verify.json', json.dumps({'findings': [], 'verdicts': {}}))
        candidate = {'finding_id': 'COMP-1', 'lens_id': 'story_specific', 'issue': 'Missing tool return question.'}
        r._persist_stage(self.run, 'completeness_critic', 'artifacts/unit-completeness.json', json.dumps({'candidate_findings': [candidate]}))
        negative_codes = []
        # Inspect legal requests at the real final transport, after all actual
        # authorization/account checks. No stage or request checker is replaced.
        def check_request(run, *, url, body, request_id):
            self.sent.append({'body': copy.deepcopy(body), 'request_id': request_id})
            calls = identity.expected_requests(self.run, stage='refine', role_id='refine')
            for extra in ({'revision_number': 99}, {'revision_number': 1, 'unapproved': True}):
                forged = copy.deepcopy(calls[-1]); forged['extra'] = extra
                with self.assertRaisesRegex(ContractError, 'LIVE_REQUEST_BINDING_MISMATCH') as caught:
                    auth.verify_request(self.run, **forged)
                negative_codes.append(caught.exception.code)
            content = 'Mira asks.' if len(self.sent) == 1 else self.outputs['refine']
            return SimpleNamespace(status_code=200, json=lambda: {
                'id': 'SIMULATED-REFINE-' + str(len(self.sent)), 'model': r.MODEL,
                'simulation_status': 'SIMULATED', 'fixture_only': True,
                'usage': {'prompt_tokens': 10, 'completion_tokens': 10},
                'choices': [{'finish_reason': 'stop', 'message': {'content': content}}]})
        with _isolated_live_transport(self.owner.fixture.temp, data_home=self.owner.fixture.data_home,
                projects=[self.owner.root], runs=[self.run], transport=check_request):
            result = r.execute_refine(self.run)
            self.assertEqual(len(result['receipts']), 1)
            self.assertNotIn('previous revision was too short', self.sent[0]['body']['messages'][0]['content'])
            self.assertIn('Missing tool return question', self.sent[0]['body']['messages'][1]['content'])
            self.assertEqual(r._read_stage_text(self.run, r.load_state(self.run), 'refine'), 'Mira asks.')
            self.assertEqual(len(negative_codes), 2)
            r._persist_stage(self.run, 'completeness_critic', 'artifacts/unit-no-issues.json', '{"candidate_findings": []}')
            before = len(self.sent)
            no_change = r.execute_refine(self.run)
            self.assertEqual(no_change['status'], 'NO_CHANGE')
            self.assertEqual(len(self.sent), before)
            with self.assertRaisesRegex(ContractError, 'LIVE_REQUEST_NO_REVISION_ISSUES'):
                identity.expected_requests(self.run, stage='refine', role_id='refine')
        self.evidence('refine_restoration')
