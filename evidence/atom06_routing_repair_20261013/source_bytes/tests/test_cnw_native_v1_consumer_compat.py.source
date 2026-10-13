"""Affected old native binding consumers use the real checked four-role chain."""
import json,unittest
from functools import wraps
from pathlib import Path
from unittest.mock import patch
from tests import test_cnw_native_pack_job as fixtures
from tests.test_cnw_atom06 import _record_trace
from tools import cnw_pack_app as app, cnw_native_pack as native, cnw_runner as runner, cnw_recovery as recovery, p2_cost_guard


class NativeV1ConsumerCompatibilityTests(unittest.TestCase):
    def test_old_native_binding_consumes_selected_materials_and_reuses_actual_stages(self):
        owner=fixtures.NativePackageTests()
        owner.setUp()
        self.addCleanup(owner.doCleanups)
        report=app.import_package(owner.package,data_home=owner.f.home,offline=True)
        row=report['tasks'][0]
        root=Path(row['project_root'])
        run=root/'runs'/row['planned_run_id']
        contract_raw=Path(row['contract']).read_bytes()
        contract=json.loads(contract_raw)
        self.assertEqual(contract['input_pack']['schema_version'],native.BINDING_SCHEMA)
        archive=owner.package.read_bytes()
        stages=('plot','scene_cards','writing_brief','prose')
        counts={'slot':0,'reserve':0}
        original_slot=p2_cost_guard.provider_slot
        original_reserve=p2_cost_guard.command_reserve
        @wraps(original_slot)
        def slot(*args,**kwargs):
            counts['slot']+=1
            return original_slot(*args,**kwargs)
        @wraps(original_reserve)
        def reserve(*args,**kwargs):
            counts['reserve']+=1
            return original_reserve(*args,**kwargs)
        with owner.owner.disconnected(), patch.object(runner,'cnw_live_call',side_effect=owner.transport), \
             patch.object(p2_cost_guard,'provider_slot',new=slot), \
             patch.object(p2_cost_guard,'command_reserve',new=reserve), \
             patch.object(runner.httpx,'post') as http:
            for stage in stages: recovery.execute_checked(run,stage)
            state=runner.load_state(run)
            captured=[]
            for stage in stages:
                record=state['stages'][stage]
                raw=(run/record['artifact']['path']).read_bytes()
                self.assertEqual(app._sha(raw),record['artifact']['sha256'])
                captured.append({'stage':stage,'utf8':raw.decode('utf-8'),'sha256':app._sha(raw),
                                 'execution_identity':record['execution_identity']})
            requests=len(owner.model.requests)
            for stage in stages:
                self.assertEqual(recovery.execute_checked(run,stage)['status'],'STAGE_REUSED')
            self.assertEqual(len(owner.model.requests),requests)
            self.assertTrue(all(r['mode']=='MOCK_ONLY' and r['simulation_status']=='SIMULATED'
                                and r['fixture_only'] is True for r in state['provider_requests']))
            self.assertEqual(counts,{'slot':0,'reserve':0}); http.assert_not_called()
        self.assertEqual(Path(row['contract']).read_bytes(),contract_raw)
        self.assertEqual(owner.package.read_bytes(),archive)
        calls=[]
        for actual in owner.model.requests:
            encoded=json.loads(json.dumps(actual,default=str))
            for key,value in actual.items():
                if isinstance(value,Path) and value.is_file():
                    raw=value.read_bytes()
                    encoded[key+'_bytes_hex']=raw.hex()
                    encoded[key+'_sha256']=app._sha(raw)
            calls.append(encoded)
        _record_trace('old_native_v1_four_role_consumers',{'execution':'MOCK_ONLY','contract':contract,
            'actual_calls':calls,'artifacts':captured,'matching_stages_reused':True,
            'original_contract_and_archive_unchanged':True,'provider_and_fee_calls':0})
