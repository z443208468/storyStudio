"""Self-consistent hostile bindings must still select the declared task."""
import copy,json
from pathlib import Path
import unittest
from unittest.mock import patch
from tests import test_cnw_pack_attempts as fixtures
from tests.test_cnw_atom06 import _record_trace
from tools import cnw_pack_app as app, cnw_native_pack as native, cnw_task_requirements as tasks, cnw_runner as runner, cnw_project as projects, p2_cost_guard
from tools.cnw_contract import ContractError


class NativeRebindingTests(unittest.TestCase):
    def test_rehashed_task_locators_and_adapters_cannot_replace_original_declaration(self):
        owner=fixtures.NativeAttemptTests()
        owner.setUp()
        self.addCleanup(owner.doCleanups)
        before=owner.record.read_bytes()
        origin_path=owner.record.parent/'origin.json'
        origin_before=origin_path.read_bytes()
        result=app.execute_package_job(owner.record,data_home=owner.f.home,execution_mode='live')
        self.assertEqual(result['blocking_code'],'LIVE_AUTHORIZATION_REQUIRED')
        row=result['tasks'][0]
        other=next(r for r in result['tasks'] if r['project_alias']==row['project_alias'] and r['task_alias']!=row['task_alias'])
        root=Path(row['project_root'])
        contract=json.loads(Path(row['contract']).read_bytes())
        binding=contract['input_pack']
        index_path=root/binding['index_file']
        original_index=index_path.read_bytes()
        index=json.loads(original_index)
        derived_path=root/index['task_context']['file']
        original_derived=derived_path.read_bytes()
        prefix=f"_INBOX/input_packs/{result['pack_sha256']}"
        extra_index=root/(prefix+'/test-owned-extra-index.json')
        extra_index.write_bytes((root/index['native_index_file']).read_bytes())
        protected_contract=Path(row['contract']).read_bytes()
        results=[]
        with patch.object(runner,'produce',wraps=runner.produce) as create, \
             patch.object(p2_cost_guard,'provider_slot') as slot, \
             patch.object(p2_cost_guard,'command_reserve') as reserve, \
             patch.object(runner.httpx,'post') as http:
            for kind in ('work_order','context_added','context_zero','index','fifth_lens','nk','critics'):
                with self.subTest(kind=kind):
                    changed=copy.deepcopy(index)
                    if kind=='work_order': changed['original_work_order']=prefix+'/'+other['declaration']['requirements']
                    # This fixture declares no context: an existing group's
                    # requirements JSON is a hostile but byte-valid new choice.
                    elif kind=='context_added': changed['native_context_file']=prefix+'/'+other['declaration']['requirements']
                    elif kind=='context_zero': changed['native_context_file']=0
                    elif kind=='index': changed['native_index_file']=extra_index.relative_to(root).as_posix()
                    elif kind=='fifth_lens': changed['adapter_choices']['fifth_lens']['responsibility']='UNAPPROVED_OTHER_TASK_DUTY'
                    else: changed['adapter_choices']['integrations'][kind]='ENABLED'
                    context=tasks.derive_native_task_context(sources=tasks.frozen_task_sources(root,changed),
                        identity={k:row[k] for k in ('project_id','project_instance_id')},index=changed)
                    derived=tasks.encode(context)
                    changed['task_context']['sha256']=app._sha(derived)
                    changed['files'][changed['task_context']['file']]=app._sha(derived)
                    derived_path.write_bytes(derived)
                    altered_index=app._bytes(changed)
                    index_path.write_bytes(altered_index)
                    rebound={**binding,'index_sha256':app._sha(altered_index)}
                    try:
                        draft=native._draft(root,changed)
                        draft['input_pack']=rebound
                        try:
                            forged=projects.build_work_contract_v2(root,draft)
                            native.validate_binding(root,rebound,contract=forged)
                        except ContractError as error:
                            self.assertEqual(error.code,'INPUT_PACK_ATTEMPT_BINDING_CHANGED')
                        else:
                            _record_trace('unexpected_rebinding_accepted_'+kind,{'execution':'MOCK_ONLY',
                                'forged_contract':forged,'forged_contract_sha256':app._sha(app._bytes(forged)),
                                'rehashed_binding_sha256':app._sha(altered_index),
                                'rehashed_derived_sha256':app._sha(derived),'provider':'NOT_RUN'})
                            self.fail('rehashed task routing was accepted by the actual contract constructor: '+kind)
                        results.append({'kind':kind,'rehashed_binding_sha256':app._sha(altered_index),
                            'rehashed_derived_sha256':app._sha(derived),'rejected':True})
                    finally:
                        index_path.write_bytes(original_index)
                        derived_path.write_bytes(original_derived)
            create.assert_not_called(); slot.assert_not_called(); reserve.assert_not_called(); http.assert_not_called()
        self.assertEqual(owner.record.read_bytes(),before)
        self.assertEqual(origin_path.read_bytes(),origin_before)
        self.assertEqual(Path(row['contract']).read_bytes(),protected_contract)
        self.assertFalse((root/'runs'/row['planned_run_id']).exists())
        _record_trace('native_rehashed_declared_task_routing',{'execution':'MOCK_ONLY','cases':results,
            'original_index_sha256':app._sha(original_index),'original_derived_sha256':app._sha(original_derived),
            'original_contract_sha256':app._sha(protected_contract),'origin_sha256':app._sha(origin_before),
            'model_run_and_provider_and_fee_calls':0,'original_inputs_unchanged':True})
