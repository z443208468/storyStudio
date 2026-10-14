"""Real V2 excerpt producer and native preflight; no Provider execution."""
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from tests import test_cnw_live_authorization as fixtures
from tools import cnw_runner as r, cnw_live_authorization as auth, cost_guard
from tools.cnw_contract import ContractError


class CriticsTextInputBytesTests(unittest.TestCase):
    def test_v2_actual_hook_snapshot_and_native_preflight_share_canonical_bytes(self):
        s = fixtures.LiveAuthorizationTests()
        s.setUp()
        self.addCleanup(s.doCleanups)
        s.fixture.contract['integrations'] = {'nk':'DISABLED','critics':'ENABLED'}
        s.contract.write_text(json.dumps(s.fixture.contract,ensure_ascii=False),encoding='utf-8')
        terms = s.full_terms()
        terms['stages'].append('critics_text')
        terms['roles']['critics_text'] = ['critics_text']
        s.sign(terms=terms)
        s.create()
        prose = 'Mira asks for help. The keeper offers a screwdriver. Mira returns the tool.'
        findings = {'findings':[{'finding_id':'CANON-1','evidence':'Mira asks for help.'}],
                    'verdicts':{'CANON-1':{'status':'CONFIRMED'}}}
        completeness = {'candidate_findings':[{'evidence':'Mira returns the tool.'}]}
        for stage, value in (('prose',prose),('adversarial_verify',json.dumps(findings)),
                             ('completeness_critic',json.dumps(completeness))):
            r._persist_stage(s.run,stage,'artifacts/'+stage+'.md',value)
        # These are explicit component prerequisites, not an eleven-stage run.
        probes = []
        actual_run = subprocess.run
        def service(command,**kwargs):
            if len(command) < 2 or Path(str(command[1])) != r.ROOT/'tools/p2_06_critics_run.py':
                return actual_run(command,**kwargs)
            path = Path(command[command.index('--input')+1])
            binding = auth.verify_auxiliary_native_input(s.run,stage='critics_text',
                action='text-refine',input_path=path)
            probes.append({'input_path':str(path),'binding':binding})
            raise RuntimeError('CONTROLLED_STOP_AFTER_REAL_NATIVE_PREFLIGHT')
        with patch('subprocess.run',side_effect=service):
            with self.assertRaisesRegex(ContractError,'CRITICS_INVOCATION_FAILED'):
                r._critics_hook(s.run,'prose')
        self.assertEqual(len(probes),1)
        state = r.load_state(s.run)
        snapshot = Path(probes[0]['input_path'])
        excerpt = s.run/'artifacts/support/critics-excerpt.md'
        metadata = json.loads(excerpt.with_suffix('.sources.json').read_bytes())
        expected = r._critics_excerpt_selection(s.run,state)[0].encode('utf-8')
        self.assertEqual(excerpt.read_bytes(),expected)
        self.assertEqual(snapshot.read_bytes(),expected)
        self.assertNotIn(b'\r\n',expected)
        self.assertEqual(metadata['excerpt_sha256'],r.sha(expected))
        self.assertEqual(probes[0]['binding']['input_sha256'],r.sha(expected))
        self.assertEqual(state['support_hooks']['critics_text']['input_artifact']['sha256'],r.sha(expected))
        refusals = []
        for label, changed in (('body',expected+b'changed'),('crlf',expected.replace(b'\n',b'\r\n'))):
            with self.subTest(label=label):
                path = snapshot.parent/('critics-input-'+r.sha(changed)+'.md')
                path.write_bytes(changed)
                with self.assertRaisesRegex(ContractError,'CRITICS_INPUT_CHANGED'):
                    auth.verify_auxiliary_native_input(s.run,stage='critics_text',
                        action='text-refine',input_path=path)
                refusals.append(label)
        replacement = {'candidate_findings':[{'evidence':'The keeper offers a screwdriver.'}]}
        r._persist_stage(s.run,'completeness_critic','artifacts/completeness-changed.json',json.dumps(replacement))
        with self.assertRaisesRegex(ContractError,'CRITICS_INPUT_CHANGED'):
            auth.verify_auxiliary_native_input(s.run,stage='critics_text',
                action='text-refine',input_path=snapshot)
        refusals.append('source_selection_changed')
        self.assertEqual(snapshot.read_bytes(),expected)
        self.assertEqual(s.http,[])
        self.assertFalse(cost_guard.accounting.LEDGER.exists())
        self.assertEqual(r.load_state(s.run)['provider_requests'],[])
        destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
        if destination:
            files = {p.relative_to(s.root).as_posix():{'sha256':r.sha(p.read_bytes()),
                'utf8':p.read_bytes().decode('utf-8')} for p in s.run.rglob('*') if p.is_file()}
            Path(destination+'.text_input_bytes.json').write_text(json.dumps({
                'scope':'PRE_SEND_COMPONENT_NOT_E2E', 'mode':'MOCK_ONLY',
                'simulation_status':'SIMULATED','real_provider_calls':0,
                'actual_preflight':probes[0], 'actual_files':files,
                'actual_run_state':r.load_state(s.run),'actual_metadata':metadata,
                'actual_canonical_excerpt_sha256':r.sha(expected),'refusals':refusals},
                ensure_ascii=False,indent=2),encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
