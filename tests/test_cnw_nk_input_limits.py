"""Actual NK shim/budget consumers, entirely fictional and offline."""
import copy
from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tests import test_cnw_live_authorization as fixtures
from tools import cnw_runner as r, cnw_live_authorization as auth, cost_guard
from tools.cnw_nk_adapter import build_nk_payload
from tools.cnw_test_live_transport import _isolated_live_transport
from tools.cnw_contract import ContractError

NODE = shutil.which('node')
SHIM = r.ROOT / 'tools/nk-live-fetch.cjs'
NODE_CONSUMER = r'''
const fs = require('node:fs');
const body = JSON.parse(process.argv[2]);
const calls = [];
globalThis.fetch = async (input, init) => {
  const text = init?.body != null ? String(init.body) : await input.clone().text();
  calls.push(JSON.parse(text));
  return new Response(JSON.stringify({id:'SIMULATED-NK-INPUT',model:'deepseek-flash',
    simulation_status:'SIMULATED',fixture_only:true,
    usage:{prompt_tokens:12,completion_tokens:8},
    choices:[{finish_reason:'stop',message:{content:JSON.stringify({perspectives:[
      {reflection:'MOCK_ONLY controlled NK reflection'}]})}}]}),
    {status:200,headers:{'content-type':'application/json'}});
};
(async () => {
  let error = null;
  try {
    require(process.argv[1]);
    const url = 'https://api.deepseek.com/v1/chat/completions';
    await globalThis.fetch(new Request(url,{method:'POST',body:JSON.stringify(body)}));
  } catch (e) { error = e.message; }
  console.log(JSON.stringify({mode:'MOCK_ONLY',simulation_status:'SIMULATED',
    real_provider_calls:0,terminal_transport_calls:calls.length,
    actual_forwarded_bodies:calls,error}));
})().catch(e => { console.error(e.message);process.exitCode=1; });
'''

def node_consumer(capture, body, cap, request_id='MOCK_ONLY-NK-INPUT'):
    if not NODE:
        raise AssertionError('NODE_REQUIRED_FOR_REAL_SHIM_CONSUMER')
    env = {k:v for k,v in os.environ.items()
           if 'API_KEY' not in k and not k.startswith('STORYSTUDIO_') and k != 'NODE_OPTIONS'}
    env.update(STORYSTUDIO_NK_LIVE_CAPTURE=str(capture),
               STORYSTUDIO_NK_LIVE_REQUEST_ID=request_id)
    if cap is not None:
        env['STORYSTUDIO_NK_MAX_INPUT_TOKENS'] = str(cap)
    result = subprocess.run([NODE, '-e', NODE_CONSUMER, str(SHIM),
        json.dumps(body, ensure_ascii=False)], env=env, capture_output=True,
        text=True, encoding='utf-8', timeout=30, check=True)
    return json.loads(result.stdout)

def wire(messages):
    return {'model':'deepseek-flash','response_format':{'type':'json_object'},
            'reasoning_effort':'none','max_tokens':512,'messages':messages}


class NKInputLimitTests(unittest.TestCase):
    def test_actual_shim_v1_astral_caps_and_invalid_messages(self):
        observations = []
        with tempfile.TemporaryDirectory(prefix='storystudio-nk-shim-') as temporary:
            base = Path(temporary)
            small = [{'role':'user','content':'MOCK_ONLY actual V1 input'}]
            astral = [{'role':'user','content':'MOCK_ONLY \U0001f30a\U0001f308 harbor'}]
            for label, messages, cap, expected in (
                ('v1_legal', small, 10000, None),
                ('astral_exact', astral, r._estimate_input_tokens(astral), None),
                ('astral_one_below', astral, r._estimate_input_tokens(astral)-1, 'NK_LIVE_INPUT_LIMIT_EXCEEDED'),
                ('reservation_limit', [{'role':'user','content':'X'*10000}], 10000, 'NK_LIVE_INPUT_LIMIT_EXCEEDED'),
                ('owner_lower_limit', [{'role':'user','content':'Y'*700}], 600, 'NK_LIVE_INPUT_LIMIT_EXCEEDED'),
                ('empty_messages', [], 10000, 'NK_LIVE_PROVIDER_MESSAGES_INVALID'),
                ('object_messages', {}, 10000, 'NK_LIVE_PROVIDER_MESSAGES_INVALID')):
                with self.subTest(label=label):
                    capture = base / (label + '.jsonl')
                    result = node_consumer(capture, wire(messages), cap)
                    self.assertEqual(result['error'], expected)
                    self.assertEqual(result['terminal_transport_calls'], 0 if expected else 1)
                    self.assertFalse(capture.exists()) if expected else self.assertTrue(capture.is_file())
                    if not expected:
                        record = json.loads(capture.read_bytes())
                        self.assertEqual(record['input_token_cap'], cap)
                        self.assertEqual(record['estimated_input_tokens'], r._estimate_input_tokens(messages))
                        self.assertEqual(result['actual_forwarded_bodies'], [wire(messages)])
                        self.assertEqual(record['response']['simulation_status'], 'SIMULATED')
                    observations.append({'case':label,'cap':cap,'actual_node_result':result})
            for cap in (None, '', '0', '-1', '1.5', 'NaN', 'Infinity', '10001'):
                with self.subTest(invalid_cap=cap):
                    capture = base / ('invalid-' + str(cap) + '.jsonl')
                    result = node_consumer(capture, wire(small), cap)
                    self.assertEqual(result['error'], 'NK_LIVE_INPUT_CAP_INVALID')
                    self.assertEqual(result['terminal_transport_calls'], 0)
                    self.assertFalse(capture.exists())
                    observations.append({'invalid_cap':cap,'actual_node_result':result})
        destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
        if destination:
            Path(destination + '.node_input_boundaries.json').write_text(json.dumps({
                'mode':'MOCK_ONLY','simulation_status':'SIMULATED','real_provider_calls':0,
                'actual_shim_sha256':r.sha(SHIM.read_bytes()),'observations':observations},
                ensure_ascii=False,indent=2),encoding='utf-8')

    def _subject(self):
        s = fixtures.LiveAuthorizationTests()
        s.setUp()
        self.addCleanup(s.doCleanups)
        self.addCleanup(self._capture_terminal_component,s)
        return s

    def _capture_terminal_component(self,s):
        destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
        if not destination or not s.run.exists():
            return
        files = {p.relative_to(s.root).as_posix():{'sha256':r.sha(p.read_bytes()),
            'utf8':p.read_bytes().decode('utf-8')} for p in s.run.rglob('*') if p.is_file()}
        Path(destination+'.nk_cap_terminal.json').write_text(json.dumps({
            'scope':'TERMINAL_COMPONENT_CAPTURE_NOT_ACCEPTANCE','mode':'MOCK_ONLY',
            'simulation_status':'SIMULATED','real_provider_calls':0,
            'actual_run_state':r.load_state(s.run),'actual_files':files,
            'actual_synthetic_ledger':json.loads(s.fees.ledger.read_bytes()) if s.fees.ledger.is_file() else None},
            ensure_ascii=False,indent=2),encoding='utf-8')

    def test_real_signed_owner_lower_cap_reserve_shim_and_unknown(self):
        s = self._subject()
        s.fixture.contract['integrations'] = {'nk':'ENABLED','critics':'DISABLED'}
        s.contract.write_text(json.dumps(s.fixture.contract,ensure_ascii=False),encoding='utf-8')
        terms = s.full_terms()
        terms.update(max_input_tokens=8000)
        terms['stages'].append('support_hook')
        terms['roles']['support_hook'] = ['nk_pov']
        s.sign(terms=terms)
        with patch.object(r,'_assert_support_components_available',return_value=None):
            s.create()
        # One controlled prerequisite is for this budget component only, not E2E.
        cards = '## Scene S1\n### Required beats\n- Mira asks for a screwdriver.\n'
        r._persist_stage(s.run,'scene_cards','artifacts/cards.md',cards)
        cards_artifact = copy.deepcopy(r.load_state(s.run)['stages']['scene_cards']['artifact'])
        cards_original = (s.run/cards_artifact['path']).read_bytes()
        payload = build_nk_payload(s.fixture.contract,cards,r._role_meta('cards',s.fixture.contract))
        with cost_guard.accounting.locked_ledger():
            pass
        process = Mock(pid=4567)
        process.poll.return_value = None
        process.terminate.side_effect = lambda: setattr(process.poll,'return_value',0)
        listener = Mock()
        listener.getsockname.return_value = ('127.0.0.1',49127)
        context = Mock()
        context.__enter__ = Mock(return_value=listener)
        context.__exit__ = Mock(return_value=False)
        launches, observations = [], []
        original_popen, original_which = subprocess.Popen, shutil.which
        def which(command,*args,**kwargs):
            return 'fictional-node.exe' if command == 'node' else original_which(command,*args,**kwargs)
        def launch(command,**kwargs):
            if command[0] != 'fictional-node.exe':
                return original_popen(command,**kwargs)
            launches.append({'capture':kwargs['env']['STORYSTUDIO_NK_LIVE_CAPTURE'],
                'cap':kwargs['env']['STORYSTUDIO_NK_MAX_INPUT_TOKENS'],
                'request_id':kwargs['env']['STORYSTUDIO_NK_LIVE_REQUEST_ID']})
            process.poll.return_value = None
            return process
        def terminal(url,**kwargs):
            self.assertTrue(url.startswith('http://127.0.0.1:'))
            self.assertEqual(kwargs['json'],payload)
            current = launches[-1]
            content = json.dumps(payload,ensure_ascii=False,separators=(',',':'))
            if observations:
                content += 'X'*10000
            messages = [{'role':'user','content':content}]
            cap_path = Path(current['capture'])
            result = node_consumer(cap_path,wire(messages),current['cap'],current['request_id'])
            observations.append({'actual_node_result':result,'service':current})
            return SimpleNamespace(status_code=500 if result['error'] else 200,
                json=lambda: {'error':result['error']} if result['error'] else
                    {'perspectives':[{'reflection':'MOCK_ONLY controlled NK reflection'}]})
        index = json.loads((r.ROOT/'patches/nk/PATCH_INDEX.json').read_bytes())
        build = r.ROOT/'runtime/patched/NK'/index['runtime_build_id']
        original_dir, original_file = Path.is_dir, Path.is_file
        def is_dir(path):
            return True if path == build/'node_modules' else original_dir(path)
        def is_file(path):
            return True if path == build/'node_modules/next/dist/bin/next' else original_file(path)
        with _isolated_live_transport(s.fixture.temp,data_home=s.fixture.data_home,
                projects=[s.root],runs=[s.run],transport=lambda **kwargs: None), \
             patch('shutil.which',side_effect=which), patch('socket.socket',return_value=context), \
             patch('subprocess.Popen',side_effect=launch), patch.object(Path,'is_dir',is_dir), \
             patch.object(Path,'is_file',is_file), patch.object(r.httpx,'get'), \
             patch.object(r.httpx,'post',side_effect=terminal):
            result = r._invoke_nk_service(s.run,payload)
            self.assertEqual(result['receipt']['mode'],'MOCK_ONLY')
            first = cost_guard.accounting.read_ledger_snapshot()['requests']
            self.assertEqual(len(first),1)
            self.assertEqual(first[0]['status'],'SETTLED')
            with self.assertRaisesRegex(ContractError,'NK_PROVIDER_CAPTURE_MISSING_OR_INVALID'):
                r._invoke_nk_service(s.run,payload)
            rows = cost_guard.accounting.read_ledger_snapshot()['requests']
            self.assertEqual(len(rows),2)
            self.assertEqual(rows[0],first[0])
            self.assertEqual(rows[1]['status'],'UNKNOWN_NOT_ZERO')
            self.assertGreater(float(rows[1]['reserved_cny']),0)
            self.assertTrue(all(row['reserved_input_token_cap'] == 8000 for row in rows))
            self.assertTrue(all(row['cost_context']['run_id'] == s.run_id for row in rows))
            self.assertTrue(all(v['cap'] == '8000' for v in launches))
            self.assertEqual([v['actual_node_result']['terminal_transport_calls'] for v in observations],[1,0])
            self.assertEqual(observations[-1]['actual_node_result']['error'],'NK_LIVE_INPUT_LIMIT_EXCEEDED')
            self.assertEqual(r._read_stage_text(s.run,r.load_state(s.run),'scene_cards'),cards)
            self.assertEqual(r.load_state(s.run)['stages']['scene_cards']['artifact'],cards_artifact)
            self.assertEqual((s.run/cards_artifact['path']).read_bytes(),cards_original)
            account = cost_guard.for_run(s.run,stage='support_hook',model=r.MODEL)
            wrong_accounts = [
                ('legacy_guard',r._p2_guard()),
                ('project_instance',replace(account,context=replace(account.context,
                    project_instance_id='00000000-0000-4000-8000-000000000000'))),
                ('run_id',replace(account,context=replace(account.context,run_id='OTHER-RUN'))),
                ('run_path',replace(account,run=s.run.parent/'OTHER-RUN')),
                ('stage',replace(account,context=replace(account.context,stage='plot'))),
                ('model',replace(account,model='OTHER-MODEL')),
            ]
            ledger_before = cost_guard.accounting.LEDGER.read_bytes()
            with patch.object(cost_guard.accounting,'command_reserve',side_effect=AssertionError('reserve forbidden')) as reserve, \
                 patch.object(r.httpx,'post',side_effect=AssertionError('HTTP forbidden')) as http:
                for label,wrong in wrong_accounts:
                    with self.subTest(wrong_account=label):
                        with self.assertRaisesRegex(ContractError,'COST_BINDINGS_CHANGED'):
                            r._invoke_nk_service_in_slot(s.run,payload,wrong)
                reserve.assert_not_called()
                http.assert_not_called()
            self.assertEqual(len(launches),2)
            self.assertEqual(cost_guard.accounting.LEDGER.read_bytes(),ledger_before)
            destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
            if destination:
                files = {p.relative_to(s.root).as_posix():{'sha256':r.sha(p.read_bytes()),
                    'utf8':p.read_bytes().decode('utf-8')} for p in s.run.rglob('*') if p.is_file()}
                Path(destination+'.signed_owner_nk_cap.json').write_text(json.dumps({
                    'scope':'CONTROLLED_BUDGET_COMPONENT_NOT_E2E', 'mode':'MOCK_ONLY',
                    'simulation_status':'SIMULATED','real_provider_calls':0,
                    'actual_observations':observations,'actual_run_state':r.load_state(s.run),
                    'actual_files':files,'actual_ledger':rows,'actual_success_receipt':result['receipt'],
                    'wrong_accounts_refused':[label for label,_ in wrong_accounts],
                    'ledger_unchanged_on_wrong_accounts':True},
                    ensure_ascii=False,indent=2),encoding='utf-8')

    def test_real_isolated_shim_byte_change_invalidates_original_signature(self):
        s = self._subject()
        before, before_sha = auth.implementation_identity()
        dependency_names = ('nk-live-fetch.cjs', 'project_paths.py', 'project_transactions.py')
        originals = {name:(r.ROOT/'tools'/name).read_bytes() for name in dependency_names}
        for name in dependency_names:
            self.assertEqual(before[name],r.sha(originals[name]))
        mirror = s.fixture.temp_root/'isolated-implementation-copy'
        for name in before:
            if name.startswith('prompts/'):
                continue  # PROMPT_ROOT retains the original, identical frozen prompts.
            relative = 'plans/'+name if name == 'MASTER_PLAN_GENERIC_APP_R5.md' else 'tools/'+name
            destination = mirror/relative
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes((r.ROOT/relative).read_bytes())
        provider = 'config/policies/provider_policy.deepseek_flash.v1.json'
        (mirror/provider).parent.mkdir(parents=True,exist_ok=True)
        (mirror/provider).write_bytes((r.ROOT/provider).read_bytes())
        with patch.object(r,'ROOT',mirror):
            self.assertEqual(auth.implementation_identity(),(before,before_sha))
            for name in dependency_names:
                with self.subTest(changed_dependency=name):
                    changed_path = mirror/'tools'/name
                    comment = b'\n// controlled isolated byte change\n' if name.endswith('.cjs') else b'\n# controlled isolated byte change\n'
                    changed_path.write_bytes(originals[name]+comment)
                    changed, changed_sha = auth.implementation_identity()
                    self.assertNotEqual(changed_sha,before_sha)
                    self.assertNotEqual(changed[name],before[name])
                    with self.assertRaisesRegex(ContractError,'ATTESTATION_BINDING_INVALID'):
                        auth.require_authorization(s.root,s.contract,run_id=s.run_id,stage='plot')
                    changed_path.write_bytes(originals[name])
                    self.assertEqual(auth.implementation_identity(),(before,before_sha))
        for name in dependency_names:
            self.assertEqual((r.ROOT/'tools'/name).read_bytes(),originals[name])
        self.assertFalse(s.run.exists())
        self.assertEqual(s.http,[])
        self.assertFalse(s.fees.ledger.exists())

    def test_ready_drift_blocks_generation_preserves_original_reservation(self):
        observations = []
        for case, expected_error in (
                ('cards_changed', 'NK_CURRENT_CARDS_MISMATCH'),
                ('owner_reissued_same_input_cap', 'NK_RESERVATION_BINDING_CHANGED'),
                ('owner_expired', 'LIVE_GRANT_EXPIRED')):
            with self.subTest(ready_drift=case):
                s = fixtures.LiveAuthorizationTests()
                s.setUp()
                clock = None
                try:
                    s.fixture.contract['integrations'] = {'nk':'ENABLED','critics':'DISABLED'}
                    s.contract.write_bytes(json.dumps(s.fixture.contract,ensure_ascii=False).encode('utf-8'))
                    terms = s.full_terms()
                    terms['stages'].append('support_hook')
                    terms['roles']['support_hook'] = ['nk_pov']
                    s.sign(terms=terms)
                    with patch.object(r,'_assert_support_components_available',return_value=None):
                        s.create()
                    cards = '## Scene S1\n### Required beats\n- Mira asks for a screwdriver.\n'
                    r._persist_stage(s.run,'scene_cards','artifacts/cards.md',cards)
                    original_artifact = copy.deepcopy(r.load_state(s.run)['stages']['scene_cards']['artifact'])
                    original_bytes = (s.run/original_artifact['path']).read_bytes()
                    payload = build_nk_payload(s.fixture.contract,cards,r._role_meta('cards',s.fixture.contract))
                    with cost_guard.accounting.locked_ledger():
                        pass
                    process = Mock(pid=4568)
                    process.poll.return_value = None
                    process.terminate.side_effect = lambda: setattr(process.poll,'return_value',0)
                    listener = Mock()
                    listener.getsockname.return_value = ('127.0.0.1',49128)
                    socket_context = Mock()
                    socket_context.__enter__ = Mock(return_value=listener)
                    socket_context.__exit__ = Mock(return_value=False)
                    original_popen, original_which = subprocess.Popen, shutil.which
                    def which(command,*args,**kwargs):
                        return 'fictional-node.exe' if command == 'node' else original_which(command,*args,**kwargs)
                    def launch(command,**kwargs):
                        return process if command[0] == 'fictional-node.exe' else original_popen(command,**kwargs)
                    initial_row = None
                    def ready(url,**kwargs):
                        nonlocal initial_row, clock
                        initial_row = copy.deepcopy(cost_guard.accounting.read_ledger_snapshot()['requests'][0])
                        self.assertEqual(initial_row['status'],'PENDING')
                        if case == 'cards_changed':
                            r._persist_stage(s.run,'scene_cards','artifacts/cards.md',cards+'- A new approved beat.\n')
                        elif case == 'owner_reissued_same_input_cap':
                            renewed = copy.deepcopy(s.terms)
                            renewed['limit_cny'] = '9.000000'
                            s.sign(terms=renewed)
                        else:
                            class ExpiredClock(datetime):
                                @classmethod
                                def now(cls,tz=None):
                                    return super().now(tz)+timedelta(days=1)
                            clock = patch.object(auth,'datetime',ExpiredClock)
                            clock.start()
                        return SimpleNamespace(status_code=200)
                    index = json.loads((r.ROOT/'patches/nk/PATCH_INDEX.json').read_bytes())
                    build = r.ROOT/'runtime/patched/NK'/index['runtime_build_id']
                    original_dir, original_file = Path.is_dir, Path.is_file
                    def is_dir(path):
                        return True if path == build/'node_modules' else original_dir(path)
                    def is_file(path):
                        return True if path == build/'node_modules/next/dist/bin/next' else original_file(path)
                    with _isolated_live_transport(s.fixture.temp,data_home=s.fixture.data_home,
                            projects=[s.root],runs=[s.run],transport=lambda **kwargs: None), \
                         patch('shutil.which',side_effect=which), patch('socket.socket',return_value=socket_context), \
                         patch('subprocess.Popen',side_effect=launch), patch.object(Path,'is_dir',is_dir), \
                         patch.object(Path,'is_file',is_file), patch.object(r.httpx,'get',side_effect=ready), \
                         patch.object(r.httpx,'post',side_effect=AssertionError('generation forbidden')) as generate:
                        with self.assertRaisesRegex(ContractError,expected_error):
                            r._invoke_nk_service(s.run,payload)
                        generate.assert_not_called()
                    rows = cost_guard.accounting.read_ledger_snapshot()['requests']
                    self.assertEqual(len(rows),1)
                    row = rows[0]
                    self.assertEqual(row['request_id'],initial_row['request_id'])
                    self.assertEqual(row['cost_context'],initial_row['cost_context'])
                    self.assertEqual(row['live_authorization'],initial_row['live_authorization'])
                    self.assertEqual(row['reserved_cny'],initial_row['reserved_cny'])
                    self.assertEqual(row['reserved_input_token_cap'],initial_row['reserved_input_token_cap'])
                    self.assertEqual(row['reserved_output_token_cap'],initial_row['reserved_output_token_cap'])
                    self.assertEqual(row['status'],'UNKNOWN_NOT_ZERO')
                    self.assertGreater(float(row['reserved_cny']),0)
                    self.assertEqual((s.run/original_artifact['path']).read_bytes(),original_bytes)
                    process.terminate.assert_called_once()
                    process.wait.assert_called_once()
                    self.assertFalse(list(s.run.glob('nk-provider-*.jsonl')))
                    observations.append({'case':case,'expected_error':expected_error,
                        'actual_original_reservation':initial_row,'actual_terminal_row':row,
                        'generate_calls':generate.call_count,'original_cards_sha256':r.sha(original_bytes),
                        'actual_original_cards_sha256':r.sha((s.run/original_artifact['path']).read_bytes())})
                finally:
                    if clock is not None:
                        clock.stop()
                    s.doCleanups()
        destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
        if destination:
            Path(destination+'.nk_ready_drift.json').write_text(json.dumps({
                'scope':'ACTUAL_SEND_BOUNDARY_COMPONENT_NOT_E2E','mode':'MOCK_ONLY',
                'simulation_status':'SIMULATED','real_provider_calls':0,
                'actual_observations':observations},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
