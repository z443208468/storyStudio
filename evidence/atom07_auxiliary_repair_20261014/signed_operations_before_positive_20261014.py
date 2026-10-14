"""Real registered operation consumers; signatures/fees real, final HTTP simulated."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_cnw_live_authorization as live_fixtures
from tools import cnw_import_workflow as imports, cnw_maintenance as maintenance
from tools import cnw_operation_authorization as opauth, cnw_live_authorization as auth
from tools import cnw_runner as runner, cost_guard
from tools import cnw_operations as operations
from tools.cnw_contract import ContractError
from tools.cnw_test_live_transport import _isolated_live_transport


class SignedOperationTests(unittest.TestCase):
    def setUp(self):
        self.base = live_fixtures.LiveAuthorizationTests()
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.root, self.owner = self.base.root, self.base.fixture.temp
        self.calls = []
        with cost_guard.accounting.locked_ledger():
            pass

    def sign(self, run, *, terms=None):
        request = opauth.build_request(run)
        bindings = request['bindings']
        now = datetime.now(timezone.utc)
        stage, role = bindings['stage'], bindings['role_id']
        self.terms = terms or {'not_before': (now-timedelta(minutes=1)).isoformat(),
            'expires_at': (now+timedelta(hours=1)).isoformat(), 'max_requests': 4,
            'max_input_tokens': 100000, 'max_output_tokens': 16000,
            'limit_cny': '1.000000', 'stages': [stage], 'roles': {stage: [role]}}
        label = bindings['operation_kind'] + '-' + Path(run).name
        controller = self.base.signed(request['controller_payload'], 'fictional-controller', label+'-controller.json')
        owner = self.base.signed({'purpose': 'CNW_OPERATION_OWNER_LIVE_FEE_AUTHORIZATION', 'decision': 'AUTHORIZE',
            'bindings': bindings, 'identity_sha256': request['identity_sha256'],
            'implementation_sha256': request['implementation_sha256'], 'provider': request['provider'],
            'cost_policy': request['cost_policy'], 'terms': self.terms}, 'fictional-owner', label+'-owner.json')
        bundle = opauth.authorization_path(run)
        bundle.write_bytes(auth.policy._canonical_bytes({'schema_version': auth.SCHEMA,
            'controller': controller, 'owner': owner, 'terms': self.terms}))
        return request

    def reply(self, run, *, url, body, request_id):
        self.calls.append({'run': str(run), 'request_id': request_id, 'body': copy.deepcopy(body)})
        payload = json.loads(body['messages'][1]['content'])
        if 'original_sources' in payload:
            source = next(iter(payload['original_sources']))
            content = {'documents': {name: [{'status': 'CONFIRMED', 'text': '## Fictional source-backed note\n'+
                        payload['original_sources'][source]['text'], 'source_refs': [source]}] for name in imports.DOCUMENTS},
                'source_notes': {name: 'Fictional material consumed.' for name in payload['original_sources']},
                'conflicts': [], 'next_action': 'Review the fictional source-backed notes.'}
        elif payload['selection']['operation'] == 'audit':
            content = {'report_markdown': '# Continuity Audit\nNo conflict in the fictional fixture.', 'action_items': []}
        else:
            content = {'brief_markdown': '\n\n'.join('## '+name+'\nFictional project; no new Canon facts.'
                       for name in maintenance.HANDOFF_SECTIONS)}
        value = {'id': 'SIMULATED-OP-'+str(len(self.calls)), 'model': runner.MODEL,
                 'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(content)}}],
                 'usage': {'prompt_tokens': 10, 'completion_tokens': 10}}
        return SimpleNamespace(status_code=200, json=lambda: value)

    @contextmanager
    def session(self, runs):
        with _isolated_live_transport(self.owner, data_home=self.base.fixture.data_home,
                projects=[self.root], runs=runs, transport=self.reply) as session:
            yield session

    def snapshot(self):
        return {str(path.relative_to(self.root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob('*') if path.is_file() and '94_runtime' not in path.parts
                and not path.name.endswith('.lock')}

    def prepare(self, operation):
        before = self.snapshot()
        ledger = self.base.fees.ledger.read_bytes()
        if operation in {'import', 'update'}:
            result = imports.run_import(self.root, incremental=operation=='update', prepare_only=True)
        else:
            result = maintenance.run_maintenance(self.root, operation, prepare_only=True)
        self.assertEqual(result['status'], 'AUTHORIZATION_PENDING')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.base.fees.ledger.read_bytes(), ledger)
        self.assertFalse(result['provider_call_authorized'])
        return Path(result['run_dir'])

    def test_actual_import_update_audit_handoff_signed_transport_and_cache(self):
        evidence = []
        for operation in ('import', 'update', 'audit', 'handoff'):
            if operation == 'update':
                (self.root/'_INBOX/new-note.md').write_text('A fictional boat arrives at noon.', encoding='utf-8')
            run = self.prepare(operation)
            request = self.sign(run)
            canon_before = (self.root/'90_canon/canon.md').read_bytes()
            with self.session([run]):
                if operation in {'import', 'update'}:
                    result = imports.run_import(self.root, incremental=operation=='update')
                else:
                    result = maintenance.run_maintenance(self.root, operation)
                    calls = len(self.calls)
                    again = maintenance.run_maintenance(self.root, operation)
                    self.assertEqual(again['provider_call'], 'reused')
                    self.assertEqual(len(self.calls), calls)
                    self.assertEqual((self.root/'90_canon/canon.md').read_bytes(), canon_before)
                state = runner.load_state(run)
                self.assertEqual(len(state['provider_requests']), 1)
                receipt = state['provider_requests'][0]
                self.assertEqual(receipt['mode'], 'MOCK_ONLY')
                self.assertEqual(receipt['simulation_status'], 'SIMULATED')
                cost_guard.verify_cached_operation_receipt(run, receipt, stage=request['bindings']['stage'],
                    role_id=request['bindings']['role_id'], output_cap=request['bindings']['output_cap'])
                files = {str(path.relative_to(run)): {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'utf8': path.read_bytes().decode('utf-8')} for path in run.rglob('*')
                         if path.is_file() and not path.name.endswith('.lock')}
                evidence.append({'operation': operation, 'result': result, 'request': request,
                                 'state': state, 'files': files})
            with self.assertRaisesRegex(ContractError, 'SIMULATED_HISTORY_FORBIDDEN'):
                opauth.require_authorization(run)
        self.assertEqual(len(self.calls), 4)
        ledger = cost_guard.accounting.read_ledger_snapshot()
        self.assertEqual(len(ledger['requests']), 4)
        self.assertTrue(all(row['status']=='SETTLED' and 'owner_grant_sha256' in row['live_authorization']
                            for row in ledger['requests']))
        destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
        if destination:
            Path(destination).write_text(json.dumps({'simulation_status': 'SIMULATED', 'real_provider_calls': 0,
                'operations': evidence, 'actual_http': self.calls, 'actual_synthetic_ledger': ledger}, indent=2), encoding='utf-8')

    def test_signed_request_mutations_reject_high_low_before_fee_or_http(self):
        run = self.prepare('audit')
        request = self.sign(run)
        frozen = json.loads((run/'artifacts/cost_operation.json').read_bytes())
        before = self.base.fees.ledger.read_bytes()
        with self.session([run]):
            for entry in (runner.cnw_live_call, runner._cnw_live_call_in_slot):
                for changes in ({'role_id': 'foreign'}, {'output_cap': True}, {'extra': {'foreign': True}},
                                {'messages': [{'role': 'user', 'content': 'Alien Canon'}]}):
                    kwargs = {key: frozen[key] for key in ('stage', 'role_id', 'messages', 'output_cap', 'extra')}
                    kwargs.update(changes)
                    with self.subTest(entry=entry.__name__, changes=changes), self.assertRaises(ContractError):
                        entry(run, **kwargs)
            (self.root/'90_canon/canon.md').write_bytes(b'Altered fictional source.')
            with self.assertRaisesRegex(ContractError, 'INPUT_CHANGED'):
                runner.cnw_live_call(run, **{key: frozen[key] for key in ('stage','role_id','messages','output_cap','extra')})
        self.assertEqual(self.calls, [])
        self.assertEqual(self.base.fees.ledger.read_bytes(), before)

    def test_unrelated_or_duplicate_success_never_skips_current_constructor(self):
        run = self.prepare('audit')
        original = (self.root/'90_canon/canon.md').read_bytes()
        state = runner.load_state(run)
        state['provider_requests'] = [{'status': 'SUCCEEDED', 'request_fingerprint': 'unrelated'}]
        runner.save_state(run, state)
        (self.root/'90_canon/canon.md').write_bytes(b'Changed fictional Canon after preparation.')
        with self.assertRaisesRegex(ContractError, 'INPUT_CHANGED'):
            opauth.build_request(run)
        (self.root/'90_canon/canon.md').write_bytes(original)
        fingerprint = json.loads((run/'artifacts/cost_operation.json').read_bytes())['request_fingerprint']
        state['provider_requests'] = [{'status':'SUCCEEDED', 'request_fingerprint':fingerprint}] * 2
        runner.save_state(run, state)
        with self.assertRaisesRegex(ContractError, 'COST_RECEIPT_BINDING_MISMATCH'):
            opauth.build_request(run)
        self.assertEqual(self.calls, [])
        self.assertEqual(cost_guard.accounting.read_ledger_snapshot()['requests'], [])

    def test_revision_descriptor_rechecks_real_author_decision(self):
        original = '07_draft/episodes/EP001.md'
        plan = '09_revision/revision_plan.md'
        approval = '00_meta/author_decisions/fictional.json'
        (self.root/original).parent.mkdir(parents=True, exist_ok=True)
        (self.root/original).write_text('A fictional draft with no accepted revision.', encoding='utf-8')
        (self.root/plan).parent.mkdir(parents=True, exist_ok=True)
        item = 'EP001: clarify the fictional request without changing Canon.'
        (self.root/plan).write_text('# Revision plan\n'+item+'\n', encoding='utf-8')
        digest = lambda name: hashlib.sha256((self.root/name).read_bytes()).hexdigest()
        identity = json.loads((self.root/'project_identity.json').read_bytes())
        protected = {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for folder in ('01_theme','02_logline','90_canon')
                     for p in (self.root/folder).rglob('*') if p.is_file() and p.suffix.lower() in {'.md','.txt','.json'}}
        decision = {'schema_version':'cnw_workflow03_user_approval_v1',
                    'author_decision':'APPROVE_SELECTED_ITEMS',
                    'project_instance_id':identity['project_instance_id'],
                    'plan_sha256':digest(plan), 'draft_sha256':{original:digest(original)},
                    'approved_items':[{'chapter':original,'plan_excerpt':item}],
                    'protected_sha256':protected}
        (self.root/approval).parent.mkdir(parents=True, exist_ok=True)
        (self.root/approval).write_text(json.dumps(decision), encoding='utf-8')
        binding = operations.revision_approval(self.root, [original], approval)
        options = {'operation':'revision_apply','scope':'full','chapters':[], 'target':None,
                   'pipeline':False,'sources':[original], 'revision_approval':binding}
        self.assertTrue(maintenance._describe_operation(self.root, options)['messages'])
        before = self.base.fees.ledger.read_bytes()
        for field, forged in (('approved_items',[{'chapter':original,'plan_excerpt':'Invented plan item.'}]),
                              ('revision_destinations',{original:'09_revision/approved/foreign.md'})):
            changed = copy.deepcopy(options)
            changed['revision_approval'] = copy.deepcopy(binding)
            changed['revision_approval']['decision'] = copy.deepcopy(decision)
            if field == 'approved_items':
                changed['revision_approval']['decision'][field] = forged
            else:
                changed['revision_approval'][field] = forged
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, 'REVISION_USER_APPROVAL_BINDING_MISMATCH'):
                maintenance._describe_operation(self.root, changed)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.base.fees.ledger.read_bytes(), before)

    def test_signed_high_low_revision_forgery_rejected_before_slot_or_fee(self):
        original = '07_draft/episodes/EP001.md'
        plan = '09_revision/revision_plan.md'
        approval = '00_meta/author_decisions/fictional.json'
        (self.root/original).parent.mkdir(parents=True, exist_ok=True)
        (self.root/original).write_text('A fictional draft awaiting author approval.', encoding='utf-8')
        (self.root/plan).parent.mkdir(parents=True, exist_ok=True)
        item = 'EP001: clarify the fictional request without changing Canon.'
        (self.root/plan).write_text('# Revision plan\n'+item+'\n', encoding='utf-8')
        digest = lambda name: hashlib.sha256((self.root/name).read_bytes()).hexdigest()
        project = json.loads((self.root/'project_identity.json').read_bytes())
        protected = {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for folder in ('01_theme','02_logline','90_canon')
                     for p in (self.root/folder).rglob('*') if p.is_file() and p.suffix.lower() in {'.md','.txt','.json'}}
        decision = {'schema_version':'cnw_workflow03_user_approval_v1',
                    'author_decision':'APPROVE_SELECTED_ITEMS',
                    'project_instance_id':project['project_instance_id'],
                    'plan_sha256':digest(plan), 'draft_sha256':{original:digest(original)},
                    'approved_items':[{'chapter':original,'plan_excerpt':item}],
                    'protected_sha256':protected}
        (self.root/approval).parent.mkdir(parents=True, exist_ok=True)
        (self.root/approval).write_text(json.dumps(decision), encoding='utf-8')
        valid = Path(maintenance.run_maintenance(self.root, 'revision_apply', sources=(original,),
                                                  revision_approval=approval, prepare_only=True)['run_dir'])
        template = self.sign(valid)
        actual = json.loads((valid/'artifacts/cost_operation.json').read_bytes())
        source_snapshot = (valid/'artifacts/source_snapshot.json').read_bytes()
        for index, field in enumerate(('approved_items','revision_destinations')):
            forged = copy.deepcopy(actual)
            selection = json.loads(forged['messages'][1]['content'])
            binding = selection['selection']['revision_approval']
            self.assertEqual(binding['approval_sha256'], digest(approval))
            if field == 'approved_items':
                binding['decision']['approved_items'] = [{'chapter':original,
                    'plan_excerpt':'A plan item never approved by the author.'}]
            else:
                binding['revision_destinations'] = {original:'09_revision/approved/foreign.md'}
            forged['messages'][1]['content'] = json.dumps(selection, ensure_ascii=False, sort_keys=True)
            fake_name = runner.sha(json.dumps(forged['messages'], ensure_ascii=False, sort_keys=True).encode())[:24]
            fake_run = self.root/'94_runtime/maintenance'/fake_name
            fake_run.mkdir(parents=True, exist_ok=True)
            runner.save_state(fake_run, {'run_id':fake_name,'schema_version':'cnw_maintenance_run_v1',
                                         'provider_requests':[]})
            (fake_run/'artifacts').mkdir(exist_ok=True)
            (fake_run/'artifacts/source_snapshot.json').write_bytes(source_snapshot)
            cost_guard.freeze_operation_account(fake_run, stage='project_revision_apply',
                role_id='project_revision_apply', messages=forged['messages'],
                output_cap=forged['output_cap'], snapshots=['artifacts/source_snapshot.json'])
            frozen = json.loads((fake_run/'artifacts/cost_operation.json').read_bytes())
            bindings = {key:frozen[key] for key in ('project_id','project_instance_id','run_id','run_schema',
                'operation_kind','stage','role_id','output_cap','snapshots','environment','request_fingerprint')}
            bindings.update(project_root=str(self.root), run_path=str(fake_run),
                frozen_operation_sha256=digest('94_runtime/maintenance/'+fake_name+'/artifacts/cost_operation.json'))
            request = copy.deepcopy(template)
            request['bindings'] = bindings
            request['identity_sha256'] = auth.policy._canonical_sha256(bindings)
            request['authorization_bundle_path'] = str(opauth.authorization_path(fake_run))
            request['controller_payload'] = {'purpose':'CNW_OPERATION_PREFLIGHT','decision':'ACCEPT',
                'bindings':bindings,'identity_sha256':request['identity_sha256'],
                'implementation_sha256':request['implementation_sha256'], 'provider_call_authorized':False}
            label = f'forged-revision-{index}'
            controller = self.base.signed(request['controller_payload'], 'fictional-controller', label+'-controller.json')
            owner_payload = {'purpose':'CNW_OPERATION_OWNER_LIVE_FEE_AUTHORIZATION', 'decision':'AUTHORIZE',
                'bindings':bindings,'identity_sha256':request['identity_sha256'],
                'implementation_sha256':request['implementation_sha256'],
                'provider':request['provider'],'cost_policy':request['cost_policy'],'terms':self.terms}
            owner = self.base.signed(owner_payload, 'fictional-owner', label+'-owner.json')
            opauth.authorization_path(fake_run).write_bytes(auth.policy._canonical_bytes({
                'schema_version':auth.SCHEMA, 'controller':controller, 'owner':owner, 'terms':self.terms}))
            before_files, before_fee = self.snapshot(), self.base.fees.ledger.read_bytes()
            args = {key:frozen[key] for key in ('stage','role_id','messages','output_cap','extra')}
            with self.session([fake_run]), patch.object(cost_guard.accounting, 'provider_slot',
                    side_effect=AssertionError('slot must remain unopened')):
                for entry in (runner.cnw_live_call, runner._cnw_live_call_in_slot):
                    with self.subTest(field=field, entry=entry.__name__), self.assertRaisesRegex(
                            ContractError, 'REVISION_USER_APPROVAL_BINDING_MISMATCH'):
                        entry(fake_run, **args)
            self.assertEqual(self.snapshot(), before_files)
            self.assertEqual(self.base.fees.ledger.read_bytes(), before_fee)
            self.assertEqual(self.calls, [])

    def test_pending_and_transaction_without_pointer_never_publish_in_prepare(self):
        run = self.prepare('import')
        self.sign(run)
        before = self.snapshot()
        replace = Path.replace
        def interrupt_publication(path, target):
            if str(path).endswith('.import-tmp'):
                raise OSError('SIMULATED publication interruption')
            return replace(path, target)
        with self.session([run]):
            with patch.object(Path, 'replace', interrupt_publication):
                with self.assertRaises(OSError): imports.run_import(self.root)
            self.assertEqual(len(self.calls), 1)
            pending = self.root/imports.PENDING
            pointer = pending.read_bytes()
            pending.unlink()  # Fictional interrupted boundary before pointer publication.
            state = (run/'run_state.json').read_bytes()
            ledger = self.base.fees.ledger.read_bytes()
            with self.assertRaisesRegex(ContractError, 'PENDING_OPERATION'):
                imports.run_import(self.root, prepare_only=True)
            self.assertEqual({k:v for k,v in self.snapshot().items() if not k.endswith('.import-tmp')}, before)
            self.assertEqual((run/'run_state.json').read_bytes(), state)
            self.assertEqual(self.base.fees.ledger.read_bytes(), ledger)
            pending.write_bytes(pointer)
            bundle = opauth.authorization_path(run)
            signed = bundle.read_bytes()
            bundle.unlink()
            with self.assertRaisesRegex(ContractError, 'AUTHORIZATION_REQUIRED'):
                imports.run_import(self.root)
            self.assertEqual(self.calls.__len__(), 1)
            bundle.write_bytes(signed)
            result = imports.run_import(self.root)
            self.assertEqual(result['status'], 'INITIAL_IMPORT_COMPLETE')
            self.assertEqual(len(self.calls), 1)
            self.assertTrue((run/'COMMITTED').is_file())

    def test_renewal_keeps_unknown_and_original_context_settlement(self):
        run = self.prepare('audit')
        request = self.sign(run)
        terms = copy.deepcopy(self.terms)
        terms.update(limit_cny='0.000300', max_input_tokens=100, max_output_tokens=100)
        self.sign(run, terms=terms)
        account = cost_guard.for_run(run, stage='project_audit', model=runner.MODEL)
        original_source = (self.root/'90_canon/canon.md').read_bytes()
        def reserve(name):
            return account.command_reserve(SimpleNamespace(request_id=name, run_id=run.name,
                purpose='SIMULATED', input_token_cap=100, output_token_cap=100), emit=False)
        reserve('SIMULATED-OP-UNKNOWN')
        # Settlement remains attributed even after source/authorization changes.
        (self.root/'90_canon/canon.md').write_bytes(b'Changed fictional source after reserve.')
        account.command_settle(SimpleNamespace(request_id='SIMULATED-OP-UNKNOWN', provider_request_id=None,
            returned_model=None, finish_reason=None, input_tokens=None, output_tokens=None), emit=False)
        (self.root/'90_canon/canon.md').write_bytes(original_source)
        before = self.base.fees.ledger.read_bytes()
        self.sign(run, terms=terms)
        with self.assertRaisesRegex(ContractError, 'BUDGET_EXCEEDED'):
            reserve('SIMULATED-OP-RENEWED')
        self.assertEqual(self.base.fees.ledger.read_bytes(), before)
        self.assertEqual(cost_guard.accounting.read_ledger_snapshot()['requests'][0]['status'], 'UNKNOWN_NOT_ZERO')
