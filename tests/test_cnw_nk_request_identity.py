"""Pure NK request consumers, using only owned fictional artifacts.

This is identity coverage, not an auxiliary transport or Live acceptance.
"""
import copy
import json
import unittest
from unittest.mock import patch

from tests import test_cnw_runner as legacy
from tools import cnw_runner as r, cnw_roles as roles, cnw_request_identity as identity
from tools import cnw_nk_adapter as nk, p2_cost_guard
from tools.cnw_contract import ContractError


class NKRequestIdentityTests(unittest.TestCase):
    def setUp(self):
        self.owner = legacy.RunnerTests()
        self.owner.setUp()
        self.addCleanup(self.owner.tearDown)
        self.root = self.owner.base
        self.run = self.root / 'runs/FICT_SCENE_A'
        self.contract = self.owner.contract
        binding = patch.object(p2_cost_guard, 'LEDGER', self.root / 'fictional-ledger.json')
        binding.start(); self.addCleanup(binding.stop)
        p2_cost_guard.LEDGER.write_text('{"requests": []}', encoding='utf-8')
        for name in roles.AUTHOR_ROLE_READS['brief'] + roles.AUTHOR_TEMPLATE_READS['brief']:
            path = self.root / name.replace('<work_id>', self.contract['unit']['id'])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Fictional source: ' + name, encoding='utf-8')
        self.cards = '## Scene S1\n### Required beats\n- A neighbor offers a tool.\n'
        r._persist_stage(self.run, 'plot', 'artifacts/plot.md', 'Fictional plot')
        r._persist_stage(self.run, 'scene_cards', 'artifacts/cards.md', self.cards)
        self.payload = nk.build_nk_payload(self.contract, self.cards, r._role_meta('cards', self.contract))
        self.response = {'perspectives': [{'reflection': 'MOCK_ONLY: only the visible offered tool.'}]}
        content = json.dumps(self.response, ensure_ascii=False)
        request = self.run / 'artifacts/provider/NK-REQUEST.request.json'
        request.parent.mkdir(parents=True, exist_ok=True)
        request.write_text(json.dumps(self.payload, ensure_ascii=False, sort_keys=True), encoding='utf-8')
        raw = self.run / 'artifacts/provider/NK-REQUEST.json'
        raw.write_text(json.dumps({'request_id': 'NK-REQUEST', 'status': 200, 'requested_model': r.MODEL,
            'response': {'id': 'SIMULATED-NK', 'model': r.MODEL, 'simulation_status': 'SIMULATED',
                'fixture_only': True, 'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15},
                'choices': [{'finish_reason': 'stop', 'message': {'content': content}}]}}), encoding='utf-8')
        self.receipt = {'stage': 'support_hook', 'role_id': 'nk_pov', 'request_id': 'NK-REQUEST',
            'provider_request_id': 'SIMULATED-NK', 'status': 'SUCCEEDED', 'model': r.MODEL,
            'http_status': 200, 'finish_reason': 'stop', 'usage': {'prompt_tokens': 10, 'completion_tokens': 5},
            'input_sha256': r.sha(json.dumps(self.payload, ensure_ascii=False, sort_keys=True).encode()),
            'request_path': request.relative_to(self.run).as_posix(), 'request_sha256': r.sha(request.read_bytes()),
            'request_format': 'native_nk_payload', 'raw_response_path': raw.relative_to(self.run).as_posix(),
            'raw_response_sha256': r.sha(raw.read_bytes()), 'output_sha256': r.sha(content.encode()),
            'mode': 'MOCK_ONLY', 'fixture_only': True, 'simulation_status': 'SIMULATED'}
        mapped, mapping = nk.map_reflection_to_brief('', self.response, {**self.receipt,
            'status': 'LIVE_ACCEPTED',
            'validated_response_sha256': r.sha(json.dumps(self.response, ensure_ascii=False, sort_keys=True).encode())})
        self.reflection = self.run / 'artifacts/support/nk-reflection.md'
        self.reflection.parent.mkdir(parents=True)
        self.reflection.write_text(mapped, encoding='utf-8')
        self.state = r.load_state(self.run)
        self.state['provider_requests'] = [self.receipt]
        self.state.setdefault('support_hooks', {})['nk_pov'] = {'status': 'MATERIALIZED',
            'request_id': 'NK-REQUEST', 'provider_request_id': 'SIMULATED-NK', 'mapping': mapping,
            'artifact': {'path': self.reflection.relative_to(self.run).as_posix(),
                         'sha256': r.sha(self.reflection.read_bytes())}}
        r.save_state(self.run, self.state)

    def request(self):
        return identity.expected_requests(self.run, stage='writing_brief', role_id='brief_agent')[0]

    def test_actual_brief_builder_consumes_matching_native_response(self):
        before = self.reflection.read_bytes()
        request = self.request()
        support = json.loads(request['messages'][1]['content'])['support']
        self.assertEqual(support['nk_perspective_reflection_support_only'], self.reflection.read_text(encoding='utf-8'))
        self.assertEqual(self.reflection.read_bytes(), before)

    def test_self_rehashed_reflection_cannot_replace_actual_response(self):
        self.reflection.write_text(self.reflection.read_text().replace('visible offered tool', 'secret future event'), encoding='utf-8')
        self.state['support_hooks']['nk_pov']['artifact']['sha256'] = r.sha(self.reflection.read_bytes())
        r.save_state(self.run, self.state)
        with self.assertRaises(ContractError): self.request()

    def test_current_cards_cannot_rebind_old_nk_payload(self):
        r._persist_stage(self.run, 'scene_cards', 'artifacts/new-cards.md', self.cards.replace('tool', 'lamp'))
        with self.assertRaises(ContractError): self.request()

    def test_native_request_is_mandatory_and_self_rehash_cannot_change_payload(self):
        original = copy.deepcopy(self.state)
        for field in ('request_path', 'request_sha256'):
            changed = copy.deepcopy(original)
            del changed['provider_requests'][0][field]
            r.save_state(self.run, changed)
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, 'NK_REQUEST_REQUIRED'):
                self.request()
        changed = copy.deepcopy(original)
        request = self.run / self.receipt['request_path']
        altered = copy.deepcopy(self.payload); altered['customPrompt'] += ' Add a secret future scene.'
        request.write_text(json.dumps(altered, ensure_ascii=False, sort_keys=True), encoding='utf-8')
        changed['provider_requests'][0]['request_sha256'] = r.sha(request.read_bytes())
        changed['provider_requests'][0]['input_sha256'] = r.sha(json.dumps(altered, ensure_ascii=False, sort_keys=True).encode())
        r.save_state(self.run, changed)
        with self.assertRaisesRegex(ContractError, 'NK_CURRENT_CARDS_MISMATCH'):
            self.request()

    def test_duplicate_receipt_and_mapping_or_provider_mismatch_rejected(self):
        original = copy.deepcopy(self.state)
        for case in ('duplicate', 'mapping', 'hook_provider', 'receipt_provider', 'request_format'):
            changed = copy.deepcopy(original)
            if case == 'duplicate': changed['provider_requests'].append(copy.deepcopy(self.receipt))
            if case == 'mapping': changed['support_hooks']['nk_pov']['mapping']['reflection_sha256'] = 'a' * 64
            if case == 'hook_provider': changed['support_hooks']['nk_pov']['provider_request_id'] = 'OTHER'
            if case == 'receipt_provider': changed['provider_requests'][0]['provider_request_id'] = 'OTHER'
            if case == 'request_format': changed['provider_requests'][0]['request_format'] = 'messages'
            r.save_state(self.run, changed)
            with self.subTest(case=case), self.assertRaises(ContractError): self.request()
