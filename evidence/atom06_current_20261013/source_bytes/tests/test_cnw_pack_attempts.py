"""Actual package attempts reach the closed Runner; no authorization is mocked."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_cnw_pack_app as legacy_fixtures
from tests import test_cnw_native_pack_job as native_fixtures
from tests import test_cnw_runner as legacy_runner
from tests.test_cnw_atom06 import _record_trace
from tools import cnw_pack_app as app, cnw_native_pack as native, cnw_runner as runner, p2_cost_guard
from tools.cnw_contract import ContractError


class PackageAttemptTests(unittest.TestCase):
    def setUp(self):
        self.owner = legacy_fixtures.PackApplicationTests()
        self.owner.setUp()
        self.addCleanup(self.owner.tearDown)
        self.f = self.owner.fixture
        result = app.import_package(self.f.pack, data_home=self.f.home, local_source=self.f.repo, offline=True)
        self.record = Path(result['job_record'])

    def start(self, **kwargs):
        return app.execute_package_job(self.record, data_home=self.f.home, execution_mode='live', **kwargs)

    def test_actual_main_closed_gate_keeps_source_and_same_attempt(self):
        original = self.record.read_bytes()
        original_get = os.environ.get
        def get(key, *defaults):
            if key == 'DEEPSEEK_API_KEY':
                self.fail('production rejection read a Key')
            return original_get(key, *defaults)
        with patch.object(os.environ, 'get', side_effect=get), \
             patch.object(runner, 'produce', wraps=runner.produce) as create, \
             patch.object(p2_cost_guard, 'provider_slot') as slot, \
             patch.object(p2_cost_guard, 'command_reserve') as reserve, \
             patch.object(runner.httpx, 'post') as http:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = app.main(['--job', str(self.record), '--data-home', str(self.f.home),
                                 '--execute-job', '--execution-mode', 'live'])
            self.assertEqual(code, 2)
            first = json.loads(output.getvalue())
            self.assertEqual(first['blocking_code'], 'LIVE_AUTHORIZATION_REQUIRED')
            declaration = Path(first['attempt_record']).with_name('declaration.json').read_bytes()
            second = self.start()
            self.assertEqual(second['attempt_id'], first['attempt_id'])
            self.assertEqual(Path(second['attempt_record']).with_name('declaration.json').read_bytes(), declaration)
            self.assertEqual(create.call_count, 2)
            self.assertTrue(all(call.args[0].mode == 'live' for call in create.call_args_list))
            slot.assert_not_called(); reserve.assert_not_called(); http.assert_not_called()
        self.assertEqual(self.record.read_bytes(), original)
        self.assertTrue(all(not (Path(r['project_root'])/'runs'/r['planned_run_id']).exists() for r in second['tasks']))

    def test_publication_interrupt_and_new_attempt_preserve_old_plan(self):
        original_rename = os.rename
        def interrupted(src, dst):
            if Path(src).name.startswith('.prepare-'):
                raise OSError('SIMULATED_ATTEMPT_PUBLICATION_INTERRUPTION')
            return original_rename(src, dst)
        with patch.object(app.os, 'rename', side_effect=interrupted):
            with self.assertRaisesRegex(OSError, 'SIMULATED_ATTEMPT_PUBLICATION'):
                self.start()
        first = self.start()
        old_record = Path(first['attempt_record'])
        old_bytes = old_record.read_bytes()
        second = self.start(new_attempt=True)
        self.assertNotEqual(second['attempt_id'], first['attempt_id'])
        self.assertEqual(old_record.read_bytes(), old_bytes)
        self.assertNotEqual(second['tasks'][0]['planned_run_id'], first['tasks'][0]['planned_run_id'])

    def test_attempt_mode_contract_and_pointer_tampering_reject(self):
        first = self.start()
        path = Path(first['attempt_record'])
        raw = path.read_bytes()
        for mutate in (lambda r: r.update(execution_mode='offline'),
                       lambda r: r['tasks'][0].update(contract=r['tasks'][1]['contract'])):
            changed = copy.deepcopy(first); mutate(changed)
            path.write_bytes(app._bytes(changed))
            with self.assertRaisesRegex(ContractError, 'INPUT_PACK_ATTEMPT_BINDING_CHANGED'):
                self.start()
            path.write_bytes(raw)
        pointer = self.record.parent/'current-live-attempt.json'
        pointer_raw = pointer.read_bytes()
        pointer.write_bytes(b'{"tampered":true}')
        with self.assertRaisesRegex(ContractError, 'INPUT_PACK_ATTEMPT_BINDING_CHANGED'):
            self.start()
        self.assertEqual(pointer.read_bytes(), b'{"tampered":true}')
        pointer.write_bytes(pointer_raw)

    def test_new_attempt_cannot_recreate_a_missing_previous_pointer(self):
        first = self.start()
        pointer = self.record.parent/'current-live-attempt.json'
        original_replace = os.replace
        lost = pointer.with_name('test-owned-lost-pointer.json')
        def missing(src, dst):
            if Path(dst) == self.record.parent/'live-attempt-intent.json':
                original_replace(src, dst)
                pointer.rename(lost)
                return
            return original_replace(src, dst)
        with patch.object(app.os, 'replace', side_effect=missing):
            with self.assertRaisesRegex(ContractError, 'INPUT_PACK_ATTEMPT_BINDING_CHANGED'):
                self.start(new_attempt=True)
        self.assertFalse(pointer.exists())
        self.assertEqual(json.loads(lost.read_bytes())['attempt_id'], first['attempt_id'])
        self.assertTrue(Path(first['attempt_record']).is_file())


class NativeAttemptTests(unittest.TestCase):
    def setUp(self):
        self.owner = native_fixtures.NativePackageTests()
        self.owner.setUp()
        self.addCleanup(self.owner.doCleanups)
        self.f = self.owner.f
        result = app.import_package(self.owner.package, data_home=self.f.home, offline=True)
        self.record = Path(result['job_record'])

    def test_native_main_namespaced_contract_reaches_real_gate_without_replacing_offline(self):
        source = json.loads(self.record.read_bytes())
        protected = {Path(row['contract']): Path(row['contract']).read_bytes()
                     for row in source['tasks'] if row.get('contract')}
        protected.update({Path(row['run_preparation']['run_path'])/'run_state.json':
            (Path(row['run_preparation']['run_path'])/'run_state.json').read_bytes()
            for row in source['tasks'] if row.get('run_preparation')})
        source_raw = self.record.read_bytes()
        first = app.execute_package_job(self.record, data_home=self.f.home, execution_mode='live')
        self.assertEqual(first['blocking_code'], 'LIVE_AUTHORIZATION_REQUIRED')
        row = first['tasks'][0]
        contract = json.loads(Path(row['contract']).read_bytes())
        self.assertEqual(contract['input_pack']['schema_version'], native.ATTEMPT_BINDING_SCHEMA)
        self.assertIn(first['attempt_id'], row['contract'])
        index = native.validate_binding(Path(row['project_root']), contract['input_pack'], contract=contract)
        self.assertIn(first['attempt_id'], index['task_context']['file'])
        self.assertFalse((Path(row['project_root'])/'runs'/row['planned_run_id']).exists())
        second = app.execute_package_job(self.record, data_home=self.f.home, execution_mode='live')
        self.assertEqual(second['attempt_id'], first['attempt_id'])
        self.assertEqual(self.record.read_bytes(), source_raw)
        for path, raw in protected.items():
            self.assertEqual(path.read_bytes(), raw)
        changed = copy.deepcopy(contract['input_pack'])
        changed['execution_attempt']['attempt_id'] = '00000000-0000-0000-0000-000000000000'
        with self.assertRaises(ContractError):
            native.validate_binding(Path(row['project_root']), changed, contract=contract)
        index_path = Path(row['project_root'])/contract['input_pack']['index_file']
        original_index = index_path.read_bytes()
        for kind in ('source_remap', 'missing_material', 'extra_material'):
            altered = copy.deepcopy(index)
            if kind == 'source_remap':
                altered['source_aliases']['B'] = altered['source_aliases']['A']
            elif kind == 'missing_material':
                altered['files'].pop(altered['original_work_order'])
            else:
                altered['files']['fake-canon.md'] = '0'*64
            index_path.write_bytes(app._bytes(altered))
            rebound = copy.deepcopy(contract['input_pack'])
            rebound['index_sha256'] = app._sha(index_path.read_bytes())
            with self.subTest(kind=kind), self.assertRaisesRegex(ContractError, 'INPUT_PACK_ATTEMPT_BINDING_CHANGED'):
                native.validate_binding(Path(row['project_root']), rebound)
            index_path.write_bytes(original_index)
        _record_trace('native_live_attempt_isolation', {'execution':'MOCK_ONLY',
            'blocking_code':first['blocking_code'], 'attempt_id':first['attempt_id'],
            'contract_sha256':app._sha(Path(row['contract']).read_bytes()),
            'index_sha256':app._sha(original_index), 'selected_source_id':contract['source']['source_id'],
            'old_contracts_and_runs_unchanged':True, 'source_remap_and_material_set_rejected':True})

    def test_simulated_predecessor_and_unready_live_predecessor_are_not_materialized(self):
        source = app.prepare_package_runs(self.record, data_home=self.f.home, _validate_only=True)
        with app.project_write_lock(self.record.parent):
            record, report = app._live_attempt(self.record.parent, source)
        row = next(r for r in report['tasks'] if r['task_alias'] == 'EP002')
        root = Path(row['project_root'])
        with self.assertRaisesRegex(ContractError, 'NATIVE_PACK_SIMULATED_PREDECESSOR_FORBIDDEN'):
            native.validate_previous(root, {'status': 'SIMULATED_CARRY_FORWARD'},
                attempt=report['execution_attempt'], expected_task='EP001')
        self.assertFalse(native.materialize_task(report, row, record.parent, data_home=self.f.home))
        self.assertEqual(row['status'], 'WAITING_PREDECESSOR')
        self.assertFalse((root/native.contract_relative(native._task_index(root, report, row))).exists())


class ProductionExportEvidenceTests(unittest.TestCase):
    def test_actual_live_validator_blocks_export_without_receipts(self):
        owner = legacy_runner.RunnerTests()
        owner.setUp()
        self.addCleanup(owner.tearDown)
        run = owner.base/'runs/FICT_SCENE_A'
        before = (run/'run_state.json').read_bytes()
        with patch.object(runner, 'export_run', wraps=runner.export_run) as export:
            with self.assertRaisesRegex(ContractError, 'LIVE_PROVIDER_EVIDENCE_MISSING'):
                app._export_package_run(run, owner.base, job_id='fictional-job', execution_mode='live')
            export.assert_not_called()
        self.assertEqual((run/'run_state.json').read_bytes(), before)
        _record_trace('live_export_evidence_rejection', {'execution':'MOCK_ONLY',
            'validator':'actual verify_live', 'blocking_code':'LIVE_PROVIDER_EVIDENCE_MISSING',
            'export_calls':0, 'state_unchanged':True, 'live_success':'NOT_VERIFIED'})


class NativeDeclarationOrderTests(unittest.TestCase):
    def test_existing_native_parser_orders_predecessors_without_rewriting_declarations(self):
        files = {'materials/90_canon/canon.md':b'A fictional coastal community.',
                 'requirements.json':app._bytes({'kind':'episode', 'language_locale':'en-US',
                     'min_visible_chars':10, 'target_visible_chars':20, 'max_visible_chars':30})}
        index = {'schema':'cnw_workpack_index_v2',
                 'projects':[{'alias':'coast', 'project_id':'TEST_COAST', 'materials':'materials',
                              'sources':[], 'fifth_lens':{'id':'promise','responsibility':'Check the promise.'}}],
                 'tasks':[{'alias':'EP002','project':'coast','work_intent':'ORIGINAL_EPISODE',
                           'first_episode':False,'previous_task':'EP001','requirements':'requirements.json'},
                          {'alias':'EP001','project':'coast','work_intent':'ORIGINAL_EPISODE',
                           'first_episode':True,'requirements':'requirements.json'}]}
        original = app._bytes(index)
        parsed = native.validate_declarations(files, index)
        self.assertEqual([r['alias'] for r in parsed['tasks']], ['EP001','EP002'])
        self.assertEqual([r['index_ordinal'] for r in parsed['tasks']], [2,1])
        self.assertEqual(app._bytes(index), original)
        source = {'schema_version':'cnw_input_pack_job_v2', 'job_id':'00000000-0000-0000-0000-000000000001',
                  'pack_sha256':'a'*64, 'origin_sha256':'b'*64, 'projects':{},
                  'tasks':[{**r, 'task_alias':r['alias'], 'project_alias':'coast',
                            'project_id':'TEST_COAST','project_instance_id':'fictional-instance',
                            'project_root':'fictional-root','unit_id':native._unit_id(r['alias'])}
                           for r in parsed['tasks']]}
        declaration = app._live_attempt_declaration(source, '00000000-0000-0000-0000-000000000002')
        self.assertEqual([r['task_key'] for r in declaration['tasks']], ['EP001','EP002'])
        self.assertEqual(app._bytes(index), original)
        cyclic = copy.deepcopy(index)
        cyclic['tasks'][1].update(first_episode=False, previous_task='EP002')
        with self.assertRaisesRegex(ContractError, 'NATIVE_PACK_DEPENDENCY_INVALID'):
            native.validate_declarations(files, cyclic)
        _record_trace('native_declared_dependency_order', {'execution':'MOCK_ONLY',
            'original_order':['EP002','EP001'], 'actual_parser_and_attempt_order':['EP001','EP002'],
            'original_index_bytes_unchanged':True, 'cycle_rejected':True,
            'live_predecessor_success':'NOT_VERIFIED'})
