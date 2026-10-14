"""Index real captured stage/request/review consumers; not Controller acceptance."""
from collections import Counter
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
LABEL = 'consolidated_final_native_full_chain_after_preflight'
DEST = OUT/(LABEL+'.consumer_index_v2.json')
if DEST.exists(): raise SystemExit('CONSUMER_INDEX_ALREADY_EXISTS')
capture_path = OUT/(LABEL+'.consumers.json.critics_signed.json')
value = json.loads(capture_path.read_bytes())
state,files = value['actual_run_state'],value['actual_files']
prefix = 'runs/'+state['run_id']+'/'
def digest(raw): return hashlib.sha256(raw).hexdigest()
def stage_raw(name):
    item = state['stages'][name]['artifact']
    captured = files[prefix+item['path']]
    raw = captured['utf8'].encode('utf-8')
    if digest(raw)!=item['sha256'] or digest(raw)!=captured['sha256']:
        raise SystemExit('STAGE_CAPTURE_HASH_MISMATCH:'+name)
    return raw
stages = [{'stage':name,'status':row['status'],'artifact_path':row['artifact']['path'],
    'sha256':digest(stage_raw(name)),'byte_count':len(stage_raw(name)),
    'execution_input_identity':row.get('execution_input_identity')}
    for name,row in state['stages'].items()]
requests = value['actual_cnw_requests']
counts = dict(Counter(row['stage'] for row in requests))
lens = json.loads(stage_raw('multi_lens_review'))
verify = json.loads(stage_raw('adversarial_verify'))
complete = json.loads(stage_raw('completeness_critic'))
rereview = json.loads(stage_raw('re_review'))
refined_sha = digest(stage_raw('refine'))
verifier_packets = [json.loads(row['messages'][1]['content']) for row in requests if row['stage']=='adversarial_verify']
rereview_packets = [json.loads(row['messages'][1]['content']) for row in requests if row['stage']=='re_review']
plot_wire = json.dumps([row['messages'] for row in requests if row['stage']=='plot'])
prose_wire = json.dumps([row['messages'] for row in requests if row['stage']=='prose'])
refine_wire = json.dumps([row['messages'] for row in requests if row['stage']=='refine'])
report = {'status':'CAPTURED_CONSUMER_INDEX_NOT_ACCEPTANCE',
    'capture_sha256':digest(capture_path.read_bytes()),'simulation_status':value['simulation_status'],
    'real_provider_calls':value['real_provider_calls'],'stages':stages,
    'actual_cnw_request_counts':counts,
    'actual_lens_roles':[row['role'] for row in requests if row['stage']=='multi_lens_review'],
    'actual_verifier_subjects':[{'finding_id':p['finding_id'],'verifier_id':p['verifier_id']} for p in verifier_packets],
    'findings':lens['findings'],'actual_aggregated_verdicts':verify['verdicts'],
    'completeness_candidate_findings':complete['candidate_findings'],
    'refine_contains_native_selected_expression':'MOCK_ONLY selected native expression' in refine_wire,
    'refine_contains_completeness_id':all(row['finding_id'] in refine_wire for row in complete['candidate_findings']),
    'selected_b_in_plot':'loose hinge' in plot_wire,'unselected_a_absent':'A_ONLY_SECRET_CANARY' not in plot_wire,
    'actual_prose_user_payload_keys':[sorted(json.loads(row['messages'][1]['content'])) for row in requests if row['stage']=='prose'],
    'actual_prose_direct_keys_legal':all(set(json.loads(row['messages'][1]['content']))=={'writing_brief','voice_samples'} for row in requests if row['stage']=='prose'),
    'original_summary_correction':'The original index checked a CANON_SECRET string that this fixture never supplied. That observation is invalid and is not used as canary evidence. This version reports actual Prose payload keys; frozen independent canary tests retain their own scope.',
    'prose_sha256':digest(stage_raw('prose')),'refine_sha256':refined_sha,
    'rereview_report':rereview,
    'rereview_consumes_refined_sha':all(p['changed_context']['v1_sha256']==refined_sha for p in rereview_packets),
    'actual_native_requests':len(value['actual_native_requests']),
    'actual_native_service_calls':len(value['actual_service_argv']),
    'actual_ledger_rows_by_stage':dict(Counter(row['cost_context']['stage'] for row in value['actual_ledger'])),
    'ledger_all_settled':all(row['status']=='SETTLED' for row in value['actual_ledger']),
    'all_cnw_receipts_mock_only':all(row.get('mode')=='MOCK_ONLY' and row.get('simulation_status')=='SIMULATED'
        and row.get('fixture_only') is True for row in state['provider_requests']),
    'limits':'This indexes the actual enabled-native eleven-stage Run; it does not run Export. Existing disabled EARLY gate/export evidence and exact unchanged-source reuse require separate Controller review. No Live, migration, Atom acceptance or next-stage permission.'}
DEST.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({key:report[key] for key in ('actual_cnw_request_counts','actual_native_requests',
    'actual_native_service_calls','refine_contains_native_selected_expression','refine_contains_completeness_id',
    'selected_b_in_plot','unselected_a_absent','actual_prose_direct_keys_legal',
    'rereview_consumes_refined_sha','ledger_all_settled','all_cnw_receipts_mock_only')}))
