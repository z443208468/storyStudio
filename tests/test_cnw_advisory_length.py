"""Owner-requested advisory length, retaining historical strict identities."""
import copy
import json
import unittest
from types import SimpleNamespace

from tests.test_cnw_runner import synthetic_contract
from tests import test_cnw_early_e2e as early
from tools import cnw_contract as contracts, cnw_roles as roles, cnw_project
from tools import cnw_runner as runner, cnw_review as review, cnw_revision as revision, cnw_export
from tools.cnw_contract import ContractError


class AdvisoryLengthTests(unittest.TestCase):
    def contract(self):
        value = synthetic_contract()
        value['schema_version'] = 'cnw_work_unit_v2'
        value['unit'].update(length_policy='ADVISORY', language_locale='zh-CN')
        return value

    def test_over_one_character_far_over_and_under_are_only_observations(self):
        value = self.contract()
        for text, status in (('字' * (value['unit']['max_visible_chars'] + 1), 'ABOVE_REFERENCE'),
                             ('字' * 8000, 'ABOVE_REFERENCE'), ('短', 'BELOW_REFERENCE')):
            with self.subTest(actual=len(text)):
                record = contracts.validate_output_length(value, text)
                self.assertEqual(record['visible_chars'], len(text))
                self.assertEqual(record['length_reference_status'], status)
                roles.validate_role_output('prose', value, text)
        with self.assertRaisesRegex(ContractError, 'PROSE_OUTPUT_EMPTY'):
            contracts.validate_output_length(value, '   ')

    def test_old_v1_and_v2_without_field_keep_original_length_oracle(self):
        old = synthetic_contract()
        for version in ('cnw_work_unit_v1', 'cnw_work_unit_v2'):
            old['schema_version'] = version
            with self.subTest(version=version):
                with self.assertRaisesRegex(ContractError, 'RETURN_UNDERPRODUCED'):
                    contracts.validate_output_length(old, '短')
                with self.assertRaisesRegex(ContractError, 'RETURN_OVER_LIMIT'):
                    contracts.validate_output_length(old, '字' * 2101)
                self.assertFalse(contracts.uses_advisory_length(old))

    def test_unknown_policy_rejected_and_creative_view_preserves_target(self):
        value = self.contract()
        view = roles.creative_assignment(value)
        self.assertEqual(view['unit']['target_visible_chars'], 1800)
        self.assertNotIn('min_visible_chars', view['unit'])
        self.assertNotIn('max_visible_chars', view['unit'])
        self.assertEqual(value['unit']['max_visible_chars'], 2100)
        value['unit']['length_policy'] = True
        with self.assertRaisesRegex(ContractError, 'LENGTH_POLICY_INVALID'):
            contracts.validate_output_length(value, '字' * 1800)

    def test_new_real_v2_builder_defaults_advisory_and_no_character_capacity_gate(self):
        owner = early.EarlyCNWE2EGateTests()
        owner.setUp(); self.addCleanup(owner.doCleanups)
        self.assertEqual(owner.contract['unit']['length_policy'], 'ADVISORY')
        original = (owner.project / 'contracts/ADAPT-HINGE-01.json').read_bytes()
        draft = json.loads((owner.project / 'contracts/ADAPT-HINGE-01.draft.json').read_bytes())
        draft.update(target_visible_chars=5000, min_visible_chars=4900, max_visible_chars=6000)
        current = cnw_project.build_work_contract_v2(owner.project, draft)
        self.assertEqual(current['unit']['max_visible_chars'], 6000)
        self.assertEqual(current['unit']['length_policy'], 'ADVISORY')
        self.assertEqual(original, (owner.project / 'contracts/ADAPT-HINGE-01.json').read_bytes())
        del draft['min_visible_chars']; del draft['max_visible_chars']
        without_bounds = cnw_project.build_work_contract_v2(owner.project, draft)
        self.assertEqual(without_bounds['unit']['length_policy'], 'ADVISORY')
        self.assertEqual(without_bounds['unit']['target_visible_chars'], 5000)

    def test_revision_count_decrease_is_not_regression_but_dropped_beat_still_is(self):
        value = self.contract()
        value['story']['required_beats'] = [{'beat_id': 'B1', 'goal': 'Event'}]
        old = '字' * 200 + '事件'
        new = '起事件说动终'
        args = dict(finish_reason='stop', v0_beat_evidence={'B1': '事件'},
            v1_beat_evidence={'B1': '事件'}, v1_dialogue_evidence=['说'], v1_action_evidence=['动'],
            start_state_evidence='起', end_state_evidence='终')
        kept = revision.validate_revision(value, old, new, **args)
        self.assertEqual(kept['status'], 'CONTENT_VALID')
        args['v1_beat_evidence'] = {}
        dropped = revision.validate_revision(value, old, new, **args)
        self.assertEqual(dropped['status'], 'CONTENT_RETURN')
        self.assertIn('RETURN_MISSING_BEAT', dropped['failure_codes'])
        self.assertIn('REVISION_REGRESSION', dropped['failure_codes'])

    def test_actual_review_builders_carry_policy_and_export_observes_over_one_char(self):
        owner = early.EarlyCNWE2EGateTests()
        owner.setUp(); self.addCleanup(owner.doCleanups)
        created = runner.produce(SimpleNamespace(mode='offline', unit='scene', run_id=owner.run_id,
            work_id=owner.contract['unit']['id'], contract=str(owner.project/'contracts/ADAPT-HINGE-01.json'),
            project_root=str(owner.project), create_only=True))
        from pathlib import Path
        run = Path(created['path'])
        # Export unit input: use the real preparation builder's selected B,
        # not a fabricated source or a claim that Plot was executed here.
        preparation = runner.build_plot_request(owner.project, owner.contract)['production_preparation']
        (run/'artifacts/production_preparation.json').write_text(json.dumps(preparation), encoding='utf-8')
        outputs = owner._outputs()
        for stage in ('scene_cards', 'writing_brief'):
            runner._persist_stage(run, stage, 'artifacts/unit-'+stage+'.md', outputs[stage])
        text = 'X' * (owner.contract['unit']['max_visible_chars'] + 1)
        runner._persist_stage(run, 'prose', 'artifacts/unit-prose.md', text)
        state = runner.load_state(run)
        sources = runner._review_sources(run, state, owner.contract, owner.project)
        self.assertEqual(sources['effective_length_policy']['mode'], 'ADVISORY')
        old_requirement = json.dumps({'work_order': {'min_visible_chars': 100, 'max_visible_chars': 250}})
        sources['task_constraints:story_specific'] = old_requirement
        finding = {'finding_id': 'LENGTH-1', 'lens_id': 'story_specific', 'issue': 'One character over old maximum.'}
        for lens in runner.LENS_IDS:
            packet = review.build_lens_input(lens, text, sources)
            self.assertIn('不得仅因字数', review.lens_messages(packet)[0]['content'])
            self.assertEqual(packet['effective_length_policy']['mode'], 'ADVISORY')
        votes = []
        for verifier in runner.VERIFIER_IDS:
            for rereview in (False, True):
                packet = review.build_verifier_packet(finding, verifier, text,
                    review.verifier_sources(finding, sources, rereview=rereview))
                self.assertIn('refute a claim supported only by a character count', review.verifier_messages(packet)[0]['content'])
            # Deterministic response fixture: this checks the real tally and
            # policy message, without claiming a model's semantic judgement.
            votes.append({'verifier_id': verifier, 'execution_mode': 'MOCK_ONLY', 'provider_request_id': None,
                          'votes': [{'finding_id': 'LENGTH-1', 'verdict': 'refuted'}]})
        self.assertEqual(review.tally_verifiers(votes)['LENGTH-1']['status'], 'REFUTED_OR_UNCERTAIN')
        packet = review.build_completeness_input(text, [], [finding], review.completeness_sources(sources))
        self.assertIn('Continue reviewing actual missing story content', review.completeness_messages(packet)[0]['content'])
        package = cnw_export.export_reading_package(run, state, project_root=owner.project)
        self.assertEqual(package['length_policy'], 'ADVISORY')
        self.assertEqual(package['actual_visible_chars'], len(text))
        self.assertEqual((Path(package['deliverables'])/'02_修订稿.txt').read_text(encoding='utf-8'), text)
        legacy_sources = {k: v for k, v in sources.items() if k != 'effective_length_policy'}
        self.assertNotIn('effective_length_policy', review.lens_messages(review.build_lens_input('style', text, legacy_sources))[0]['content'])
