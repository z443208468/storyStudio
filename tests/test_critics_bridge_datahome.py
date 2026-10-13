"""Offline path-scope regressions for CritiCS in registered projects."""
from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from types import ModuleType
import sys
from unittest.mock import patch

from tools import critics_bridge, cnw_w10_critics, p2_06_critics_run, p2_cost_guard
from tools.project_paths import create_project, setup_data_home


class CriticsBridgeDataHomeTests(unittest.TestCase):
    def test_registered_project_inputs_and_run_output_are_scoped_to_instance(self):
        with tempfile.TemporaryDirectory(prefix="critics-data-home-") as temp_name:
            temp = Path(temp_name).resolve()
            data_home = temp / "selected-data-home"
            setup_data_home(data_home, pointer_path=temp / "setup.json")
            registration = create_project(project_id="CRITICS-SYNTHETIC", data_home=data_home)
            project = Path(registration["project_root"])
            runs = project / "runs"
            runs.mkdir()
            source = project / "drafts" / "synthetic.md"
            source.parent.mkdir()
            source.write_text("fictional test input", encoding="utf-8")

            self.assertEqual(critics_bridge.project_path(str(source)), source.resolve())

            candidate = runs / "SYNTHETIC-CRITICS"
            self.assertEqual(critics_bridge.project_path(str(candidate), directory=True), candidate)
            self.assertEqual(critics_bridge.create_run_directory(candidate), candidate.resolve())
            self.assertTrue(candidate.is_dir())
            parent_run = runs / "SYNTHETIC-PARENT-RUN"
            parent_run.mkdir()
            evidence_root, critics_run = cnw_w10_critics._critics_run_path(parent_run, "plan-critique")
            self.assertEqual(evidence_root, project)
            self.assertEqual(critics_run, runs / "SYNTHETIC-PARENT-RUN-critics-plan-critique")

            unregistered = temp / "projects" / "unregistered" / "draft.md"
            unregistered.parent.mkdir(parents=True)
            unregistered.write_text("not an application project", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "INPUT_MUST_BE_UNDER_PRIVATE_WORKSPACE_OR_REGISTERED_PROJECT"):
                critics_bridge.project_path(str(unregistered))
            unsafe_run = unregistered.parent / "runs" / "UNREGISTERED"
            with self.assertRaisesRegex(ValueError, "RUN_DIR_MUST_BE_UNDER_REGISTERED_RUNS"):
                critics_bridge.project_path(str(unsafe_run), directory=True)
            with self.assertRaisesRegex(ValueError, "RUNS_ROOT_NOT_REGISTERED"):
                critics_bridge.create_run_directory(unsafe_run)
            self.assertFalse(unsafe_run.exists())

    def test_p2_runner_rejects_unbound_registered_run_before_provider_or_cost(self):
        with tempfile.TemporaryDirectory(prefix="critics-run-route-") as temp_name:
            temp = Path(temp_name).resolve()
            data_home = temp / "selected-data-home"
            setup_data_home(data_home, pointer_path=temp / "setup.json")
            registration = create_project(project_id="CRITICS-RUN-ROUTE", data_home=data_home)
            project = Path(registration["project_root"])
            (project / "runs").mkdir()
            source = project / "source.md"
            source.write_text("fictional isolated input", encoding="utf-8")
            target = project / "runs" / "SYNTHETIC-CRITICS-RUN"
            ledger = temp / "ledger.json"
            ledger.write_text(json.dumps({"requests": []}), encoding="utf-8")
            observed = {}

            def create_bridge_run(command):
                observed["command"] = command
                parsed_dir = command[command.index("--run-dir") + 1]
                self.assertEqual(Path(parsed_dir), target)
                critics_bridge.create_run_directory(parsed_dir)
                return 0

            with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "synthetic-offline-test-key"}), \
                 patch.object(p2_06_critics_run.p2_cost_guard, "LEDGER", ledger), \
                 patch.object(p2_06_critics_run.critics_bridge, "main", side_effect=create_bridge_run):
                self.assertEqual(critics_bridge.project_path(str(target), directory=True), target)
                with self.assertRaisesRegex(SystemExit, "CRITICS_PARENT_RUN_BINDING_REQUIRED"):
                    p2_06_critics_run.main(["--action", "plan-critique", "--input", str(source),
                        "--run-dir", str(target), "--ledger-run-id", "SYNTHETIC-PARENT"])

            self.assertFalse(target.exists())
            self.assertEqual(observed, {})
            self.assertEqual(json.loads(ledger.read_text(encoding="utf-8")), {"requests": []})
            self.assertFalse((Path(p2_06_critics_run.ROOT) / "runs" / target.name).exists())

    def test_legacy_output_cannot_downgrade_registered_input_or_critique(self):
        from tools import cost_guard
        with tempfile.TemporaryDirectory(prefix="critics-route-downgrade-") as temp_name:
            temp = Path(temp_name).resolve()
            data_home = temp / "selected-data-home"
            setup_data_home(data_home, pointer_path=temp / "setup.json")
            project = Path(create_project(project_id="ROUTE-BOUNDARY", data_home=data_home)["project_root"])
            registered_input = project / "input.md"
            registered_critique = project / "critique.json"
            registered_input.write_text("registered fictional input", encoding="utf-8")
            registered_critique.write_text("{}", encoding="utf-8")
            repo = temp / "legacy-repo"
            (repo / "workspace").mkdir(parents=True)
            (repo / "runs").mkdir()
            legacy_input = repo / "workspace/input.md"
            legacy_critique = repo / "workspace/critique.json"
            legacy_input.write_text("legacy fictional input", encoding="utf-8")
            legacy_critique.write_text("{}", encoding="utf-8")
            originals = {path: path.read_bytes() for path in
                         (registered_input, registered_critique, legacy_input, legacy_critique)}
            original_get = os.environ.get

            def environment_get(key, *defaults):
                if key == "DEEPSEEK_API_KEY":
                    self.fail("downgraded route reached Key access")
                return original_get(key, *defaults)

            with patch.object(p2_06_critics_run, "ROOT", repo), \
                 patch.object(critics_bridge, "ROOT", repo), \
                 patch.object(os.environ, "get", side_effect=environment_get), \
                 patch.object(cost_guard, "for_run", wraps=cost_guard.for_run) as account, \
                 patch.object(p2_cost_guard, "provider_slot") as slot, \
                 patch.object(p2_cost_guard, "command_reserve") as reserve, \
                 patch.object(critics_bridge, "main") as native:
                pairs = [(registered_input, legacy_critique),
                         (legacy_input, registered_critique),
                         (registered_input, registered_critique)]
                for output in (["--run-name", "LEGACY"], ["--run-dir", str(repo / "runs/EXPLICIT")]):
                    for source, critique in pairs:
                        with self.subTest(output=output[0], source=source.name, critique=str(critique)):
                            with self.assertRaisesRegex(SystemExit, "CRITICS_PARENT_RUN_BINDING_REQUIRED"):
                                p2_06_critics_run.main(["--action", "plan-revise", "--input", str(source),
                                    "--critique", str(critique), *output])
                            args = SimpleNamespace(action="plan-revise", input=str(source), critique=str(critique))
                            with self.assertRaisesRegex(SystemExit, "CRITICS_PARENT_RUN_BINDING_REQUIRED"):
                                p2_06_critics_run._execute_native(args, repo / "runs/DIRECT")
                    with self.assertRaisesRegex(SystemExit, "CRITICS_PARENT_RUN_BINDING_REQUIRED"):
                        p2_06_critics_run.main(["--action", "plan-critique", "--input", str(registered_input), *output])
                account.assert_not_called()
                slot.assert_not_called()
                reserve.assert_not_called()
                native.assert_not_called()
            self.assertEqual(list((repo / "runs").iterdir()), [])
            for path, raw in originals.items():
                self.assertEqual(path.read_bytes(), raw)

    def test_true_legacy_input_and_output_keep_actual_native_route(self):
        from tests.test_p2_cost_guard import CampaignLimitTests
        fees = CampaignLimitTests()
        fees.setUp()
        self.addCleanup(fees.doCleanups)
        with p2_cost_guard.locked_ledger():
            pass
        with tempfile.TemporaryDirectory(prefix="critics-legacy-compat-") as temp_name:
            repo = Path(temp_name).resolve()
            (repo / "workspace").mkdir()
            (repo / "runs").mkdir()
            source = repo / "workspace/input.md"
            critique = repo / "workspace/critique.json"
            source.write_text("unchanged fictional V1 material", encoding="utf-8")
            critique.write_text("{}", encoding="utf-8")
            ledger_before = fees.ledger.read_bytes()
            consumed = []

            def native_boundary(text, feedback):
                consumed.append((text.encode('utf-8'), feedback))
                return text

            from unittest.mock import Mock
            native = Mock(side_effect=native_boundary)
            native_module = ModuleType('critics.plan.plan')
            native_module.modifiedStoryline = native
            build = repo / 'runtime/patched/CritiCS' / critics_bridge.PATCH_INDEX['runtime_build_id']
            build.mkdir(parents=True)

            with patch.object(p2_06_critics_run, "ROOT", repo), \
                 patch.object(critics_bridge, "ROOT", repo), \
                 patch.object(critics_bridge, 'BUILD', build), \
                 patch.dict(sys.modules, {'critics.plan.plan': native_module}), \
                 patch.dict(os.environ, {"DEEPSEEK_API_KEY": "synthetic-offline-test-key",
                     'STORYSTUDIO_MODEL': 'deepseek-flash', 'STORYSTUDIO_BASE_URL': 'https://api.deepseek.com/v1'}):
                for output in (["--run-name", "V1-NAMED"], ["--run-dir", str(repo / "runs/V1-EXPLICIT")]):
                    previous_cwd, previous_path = os.getcwd(), list(sys.path)
                    try:
                        result = p2_06_critics_run.main(["--action", "plan-revise", "--input", str(source),
                            "--critique", str(critique), *output])
                    finally:
                        os.chdir(previous_cwd)
                        sys.path[:] = previous_path
                    self.assertEqual(result, 0)
                self.assertEqual(native.call_count, 2)
            self.assertEqual(consumed, [(source.read_bytes(), {})] * 2)
            self.assertEqual(fees.ledger.read_bytes(), ledger_before)
            for name in ("V1-NAMED", "V1-EXPLICIT"):
                self.assertEqual((repo / "runs" / name / "modified_plot.md").read_bytes(), source.read_bytes())
                receipt_path = repo / 'runs' / name / 'run_receipt.json'
                receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
                receipt.update(mode='MOCK_ONLY', simulation_status='SIMULATED', fixture_only=True)
                receipt_path.write_text(json.dumps(receipt), encoding='utf-8')
                self.assertEqual(json.loads((repo / "runs" / name / "provider-calls.json").read_text()), [])
                self.assertEqual((repo / "runs" / name / "p2-cost-ledger.json").read_bytes(), ledger_before)

    def test_direct_bridge_rejects_registered_material_before_key_or_output(self):
        import subprocess
        with tempfile.TemporaryDirectory(prefix='critics-direct-guard-') as temp_name:
            temp = Path(temp_name).resolve()
            data_home = temp / 'selected-data-home'
            setup_data_home(data_home, pointer_path=temp / 'setup.json')
            project = Path(create_project(project_id='DIRECT-BRIDGE', data_home=data_home)['project_root'])
            (project / 'runs').mkdir()
            source, critique = project / 'input.md', project / 'critique.json'
            source.write_text('registered fictional text', encoding='utf-8')
            critique.write_text('{}', encoding='utf-8')
            target = project / 'runs/DIRECT'
            repo = temp / 'legacy-repo'
            (repo / 'workspace').mkdir(parents=True)
            (repo / 'runs').mkdir()
            legacy_source = repo / 'workspace/input.md'
            legacy_source.write_text('legacy fictional text', encoding='utf-8')
            legacy_target = repo / 'runs/DIRECT'
            original = source.read_bytes(), critique.read_bytes(), legacy_source.read_bytes()
            script = str(Path(critics_bridge.__file__).resolve())
            cases = [
                ['plan-critique', '--plot', str(source), '--run-dir', str(target)],
                ['plan-critique', '--plot', str(source), '--run-dir', str(legacy_target)],
                ['plan-critique', '--plot', str(legacy_source), '--run-dir', str(target)],
                ['plan-revise', '--plot', str(legacy_source), '--critique', str(critique), '--run-dir', str(legacy_target)],
                ['plan-revise', '--plot', str(source), '--critique', str(critique), '--run-dir', str(target)],
                ['text-refine', '--excerpt', str(source), '--run-dir', str(target)],
            ]
            with patch.object(critics_bridge, 'ROOT', repo), \
                 patch.object(critics_bridge, 'configure_provider') as key, \
                 patch.object(critics_bridge, 'create_run_directory', wraps=critics_bridge.create_run_directory) as mkdir, \
                 patch.object(p2_cost_guard, 'provider_slot') as slot, \
                 patch.object(p2_cost_guard, 'command_reserve') as reserve:
                for command in cases:
                    with self.subTest(command=command):
                        with self.assertRaisesRegex(ValueError, 'CRITICS_REGISTERED_INVOCATION_REQUIRED'):
                            critics_bridge.main(command)
                for forged in (True, {'accepted': True}):
                    with self.assertRaisesRegex(ValueError, 'CRITICS_REGISTERED_INVOCATION_REQUIRED'):
                        critics_bridge.main(cases[0], _registered_invocation=forged)
                key.assert_not_called()
                mkdir.assert_not_called()
                slot.assert_not_called()
                reserve.assert_not_called()
            # Exercise the actual __main__ entry in a credential-free, network-denied child.
            bootstrap = ("import sys,runpy\n"
                "def deny(event,args):\n"
                " if event in ('socket.connect','socket.sendto','socket.getaddrinfo'): raise RuntimeError('OFFLINE_NETWORK_DENIED')\n"
                "sys.addaudithook(deny)\n"
                + 'sys.path.insert(0,' + repr(str(Path(script).parent)) + ')\n'
                + 'sys.argv=' + repr([script, *cases[0]]) + '\n'
                + 'runpy.run_path(' + repr(script) + ',run_name="__main__")\n')
            env = dict(os.environ)
            for name in ('DEEPSEEK_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY'):
                env.pop(name, None)
            result = subprocess.run([sys.executable, '-c', bootstrap], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b'CRITICS_REGISTERED_INVOCATION_REQUIRED', result.stdout)
            self.assertFalse(target.exists())
            self.assertFalse(legacy_target.exists())
            self.assertEqual((source.read_bytes(), critique.read_bytes(), legacy_source.read_bytes()), original)

    def test_bridge_keeps_existing_dynamic_import_without_module_registration(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('isolated_critics_bridge', critics_bridge.__file__)
        module = importlib.util.module_from_spec(spec)
        self.assertNotIn('isolated_critics_bridge', sys.modules)
        spec.loader.exec_module(module)
        self.assertTrue(callable(module.main))
        self.assertEqual(module._RegisteredNativeInvocation._fields[0], 'account')

    def test_native_component_uses_real_shared_accounts_and_preserves_unknown(self):
        from tests.test_cnw_run_bindings import ExistingRunBindingTests
        from tests.test_p2_cost_guard import CampaignLimitTests
        from tools import cost_guard, cnw_critics_adapter
        from tools.cnw_contract import ContractError

        fixtures = [ExistingRunBindingTests(), ExistingRunBindingTests()]
        for fixture in fixtures:
            fixture.setUp()
            self.addCleanup(fixture.doCleanups)
        fees = CampaignLimitTests()
        fees.setUp()
        self.addCleanup(fees.doCleanups)
        with p2_cost_guard.locked_ledger():
            pass
        parents = [fixture.run for fixture in fixtures]
        states = [(parent / 'run_state.json').read_bytes() for parent in parents]
        accounts = [cost_guard.for_run(parent, stage='critics_plot', model='deepseek-flash')
                    for parent in parents]
        self.assertNotEqual(accounts[0].context.project_instance_id, accounts[1].context.project_instance_id)
        inputs, critiques, children = [], [], []
        for parent in parents:
            support = parent / 'artifacts/support'
            support.mkdir(parents=True, exist_ok=True)
            source = support / 'fictional-plot.md'
            source.write_text('A fictional reversible choice.', encoding='utf-8')
            critique = support / 'fictional-critique.json'
            critique.write_text(json.dumps({'inspector': 'Preserve the fictional choice.'}), encoding='utf-8')
            inputs.append(source)
            critiques.append(critique)
            children.append(parent.parent / 'NATIVE-COMPONENT')

        calls, slots, holding = [], [], [False]
        original_slot = p2_cost_guard.provider_slot
        @contextmanager
        def observed_slot():
            with original_slot():
                holding[0] = True
                slots.append(str(p2_cost_guard.LEDGER.parent / 'provider-slots'))
                try:
                    yield
                finally:
                    holding[0] = False

        def network_mock(client, request, *args, **kwargs):
            self.assertTrue(holding[0])
            calls.append(request)
            if len(calls) == 2:
                raise RuntimeError('SIMULATED_TRANSPORT_INTERRUPTION')
            return p2_06_critics_run.httpx.Response(200, request=request, json={
                'id': 'MOCK-PROVIDER-A', 'model': 'deepseek-flash',
                'choices': [{'finish_reason': 'stop', 'message': {'content': 'Fictional revised choice.'}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 5}})

        def native_method(storyline, final_critic):
            template = cnw_critics_adapter.native_templates('storyline_template.py', {'applyQA'})['applyQA']
            messages = [{'role': 'user', 'content': template.format(
                storyline=storyline, final_critic=final_critic)}]
            request = p2_06_critics_run.httpx.Request('POST', 'https://api.deepseek.com/v1/chat/completions',
                json={'model': 'deepseek-flash', 'messages': messages})
            with p2_06_critics_run.httpx.Client() as client:
                response = client.send(request).json()
            return response['choices'][0]['message']['content']

        from unittest.mock import Mock
        native = Mock(side_effect=native_method)
        native_module = ModuleType('critics.plan.plan')
        native_module.modifiedStoryline = native

        with patch.object(p2_cost_guard, 'provider_slot', new=observed_slot), \
             patch.object(p2_06_critics_run.httpx.Client, 'send', new=network_mock), \
             patch.dict(sys.modules, {'critics.plan.plan': native_module}), \
             patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'synthetic-offline-test-key',
                 'STORYSTUDIO_MODEL': 'deepseek-flash', 'STORYSTUDIO_BASE_URL': 'https://api.deepseek.com/v1'}):
            for index in range(2):
                args = SimpleNamespace(action='plan-revise', input=str(inputs[index]),
                    critique=str(critiques[index]), ledger_run_id=parents[index].name,
                    parent_stage='critics_plot')
                previous_cwd, previous_path = os.getcwd(), list(sys.path)
                try:
                    result = p2_06_critics_run._execute_native(args, children[index],
                        account=accounts[index], parent_run_dir=parents[index])
                finally:
                    os.chdir(previous_cwd)
                    sys.path[:] = previous_path
                self.assertEqual(result, 0 if index == 0 else 1)
                if index == 0:
                    receipt_path = children[index] / 'run_receipt.json'
                    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
                    receipt.update(mode='MOCK_ONLY', simulation_status='SIMULATED', fixture_only=True)
                    receipt_path.write_text(json.dumps(receipt), encoding='utf-8')
            ledger = p2_cost_guard.read_ledger_snapshot()
            self.assertEqual(len(ledger['requests']), 2)
            for index, row in enumerate(ledger['requests']):
                self.assertEqual(row['cost_context'], accounts[index].context.record())
                self.assertEqual(row['run_id'], parents[index].name)
            self.assertEqual(ledger['requests'][0]['status'], 'SETTLED')
            self.assertEqual(ledger['requests'][1]['status'], 'UNKNOWN_NOT_ZERO')
            self.assertGreater(float(ledger['requests'][1]['reserved_cny']), 0)
            unknown = json.loads(json.dumps(ledger['requests'][1]))
            self.assertEqual(slots, [str(fees.ledger.parent / 'provider-slots')] * 2)
            consumed = cnw_critics_adapter.read_native_result(children[0], action='plan-revise',
                input_path=inputs[0], critique_path=critiques[0], parent_run_dir=parents[0],
                parent_stage='critics_plot')
            self.assertEqual(consumed['result'], 'Fictional revised choice.')
            self.assertEqual(consumed['provider_request_ids'], ['MOCK-PROVIDER-A'])
            with self.assertRaisesRegex(ContractError, 'CRITICS_PARENT_RUN_BINDING_INVALID'):
                cnw_critics_adapter.read_native_result(children[0], action='plan-revise',
                    input_path=inputs[1], critique_path=critiques[1], parent_run_dir=parents[1],
                    parent_stage='critics_plot')
            scoped = json.loads((children[0] / 'p2-cost-ledger.json').read_text(encoding='utf-8'))
            self.assertEqual(len(scoped['requests']), 1)
            self.assertEqual(scoped['cost_context'], accounts[0].context.record())
            failed_calls = json.loads((children[1] / 'provider-calls.json').read_text(encoding='utf-8'))
            self.assertEqual(failed_calls[0]['ledger_settlement']['status'], 'UNKNOWN_NOT_ZERO')
            with self.assertRaisesRegex(ContractError, 'OFFLINE_PROVIDER_FORBIDDEN'):
                p2_06_critics_run.main(['--action', 'plan-revise', '--input', str(inputs[0]),
                    '--critique', str(critiques[0]), '--run-dir', str(parents[0].parent / 'CLI-DENIED'),
                    '--ledger-run-id', parents[0].name, '--parent-run-dir', str(parents[0]),
                    '--parent-stage', 'critics_plot'])
            with self.assertRaisesRegex(SystemExit, 'CRITICS_PARENT_RUN_BINDING_INVALID'):
                p2_06_critics_run.main(['--action', 'plan-revise', '--input', str(inputs[0]),
                    '--critique', str(critiques[0]), '--run-dir', str(parents[1].parent / 'CROSS-PROJECT'),
                    '--ledger-run-id', parents[0].name, '--parent-run-dir', str(parents[0]),
                    '--parent-stage', 'critics_plot'])
            self.assertEqual(native.call_count, 2)
            self.assertEqual(len(calls), 2)
            self.assertEqual(p2_cost_guard.read_ledger_snapshot()['requests'][1], unknown)
            for parent, original in zip(parents, states):
                self.assertEqual((parent / 'run_state.json').read_bytes(), original)
            from tests.test_cnw_work_intent_v2 import _record_atom07_evidence
            import hashlib
            _record_atom07_evidence('atom05_critics_account_effect', {
                'execution': 'MOCK_ONLY', 'ledger': ledger['requests'],
                'consumed': consumed, 'scoped_ledger': scoped, 'failed_calls': failed_calls,
                'files': [{'label': label, 'bytes_hex': path.read_bytes().hex(),
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for label, path in (
                        ('input', inputs[0]), ('critique', critiques[0]),
                        ('output', children[0]/'modified_plot.md'),
                        ('receipt', children[0]/'run_receipt.json'),
                        ('calls', children[0]/'provider-calls.json'),
                        ('scoped_ledger', children[0]/'p2-cost-ledger.json'),
                        ('failed_calls', children[1]/'provider-calls.json'))],
                'production_admission_rejected': True, 'cross_project_replay_rejected': True,
                'unknown_preserved': True, 'parent_states_unchanged': True})


if __name__ == "__main__":
    unittest.main()
