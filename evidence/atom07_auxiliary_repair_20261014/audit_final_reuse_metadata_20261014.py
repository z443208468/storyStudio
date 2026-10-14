"""Read-only evidence provenance audit; does not execute tests or sign acceptance."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
OUT = Path(__file__).resolve().parent
EV = ROOT / 'evidence/atom07_auxiliary_repair_20261014'
DEST = OUT / 'final_reuse_metadata_20261014.json'
if DEST.exists():
    raise SystemExit('EVIDENCE_ALREADY_EXISTS')

def sha(b):
    return hashlib.sha256(b).hexdigest()

norm_bytes = (EV / 'candidate_lf_normalization_20261014.json').read_bytes()
norm = json.loads(norm_bytes)
normalizations = {r['path']: r for r in norm['records']}
labels = [
    'signed_v2_nk_consumer_launcher_fixed', 'native_actual_input_limit_negative',
    'signed_native_shared_account_unknown', 'old_account_only_admission_refusal',
    'shared_fanout_capacity_regression', 'native_record_enumeration_regression',
    'native_batch_legacy_smoke', 'native_batch_direct_read_compat_fixed',
    'legacy_native_export_compat_final', 'native_mock_boundaries_action_guard_fixed',
    'final_operation_consumers_batch', 'final_shared_consumers_batch',
    'lf_final_identity_revision_consumers', 'auxiliary_mock_receipt_corrected',
    'critics_mock_boundary_fast_regression',
]
results = []
for label in labels:
    check_path = EV / (label + '.check.json')
    raw_path = EV / (label + '.raw.txt')
    check_bytes = check_path.read_bytes()
    check = json.loads(check_bytes)
    if not check['source_unchanged']:
        raise SystemExit('NON_PASS_SELECTED:' + label)
    if check['exit_code'] != 0 and label != 'legacy_native_export_compat_final':
        raise SystemExit('NON_PASS_SELECTED:' + label)
    raw_hash = sha(raw_path.read_bytes())
    if raw_hash != check['raw_sha256']:
        raise SystemExit('RAW_HASH_MISMATCH:' + label)
    exact, lf, changed = [], [], []
    for name, old_hash in check['source_after'].items():
        path = ROOT / name
        if not path.is_file():
            changed.append({'path': name, 'reason': 'MISSING'})
            continue
        current = sha(path.read_bytes())
        if current == old_hash:
            exact.append(name)
        elif (name in normalizations
              and old_hash == normalizations[name]['before_sha256']
              and current == normalizations[name]['after_sha256']):
            lf.append(name)
        else:
            changed.append({'path': name, 'evidence_sha256': old_hash,
                            'current_sha256': current})
    results.append({'label': label, 'check_sha256': sha(check_bytes),
                    'raw_sha256': raw_hash, 'exit_code': check['exit_code'],
                    'source_unchanged_during_run': True,
                    'exact_final_byte_paths': exact,
                    'recorded_lf_only_paths': lf,
                    'other_differences_requiring_scope_comparison': changed,
                    'interpretation': ('PARTIAL_19_PASS_1_FAIL_NOT_BATCH_PASS'
                        if check['exit_code'] != 0 else 'PROVENANCE_ONLY_NOT_RERUN_OR_ACCEPTANCE')})

physical = []
for name in sorted(normalizations):
    b = (ROOT / name).read_bytes()
    raw_oid = subprocess.check_output(['git', 'hash-object', '--stdin'], input=b,
                                     cwd=ROOT).decode().strip()
    filtered_oid = subprocess.check_output(['git', 'hash-object', '--path=' + name,
                                           '--stdin'], input=b, cwd=ROOT).decode().strip()
    physical.append({'path': name, 'physical_sha256': sha(b),
                     'raw_blob_oid': raw_oid, 'filtered_blob_oid': filtered_oid,
                     'physical_equals_git_filter': raw_oid == filtered_oid})
if not all(r['physical_equals_git_filter'] for r in physical):
    raise SystemExit('PHYSICAL_GIT_FILTER_DIFFERENCE')

protected = [
    ('workspace/CQ_F01_TS_INPUT_V5/runs/F01-TS-V5-20261011-01/run_state.json',
     '3bae0722506641f1c14840d2f2568f03484cd6b1298c972baf3700d0de42ee0d'),
    ('runtime/private/p2-cost-ledger.json',
     'c8b0705f491ef824db01be0b7991f4db9db7d84e153c26481e93a4fdcd0eab9b'),
]
anchors = [{'object': name, 'sha256': sha((ROOT / name).read_bytes()),
            'frozen_sha256': value} for name, value in protected]
if not all(r['sha256'] == r['frozen_sha256'] for r in anchors):
    raise SystemExit('PROTECTED_ORIGINAL_CHANGED')
report = {'status': 'READ_ONLY_PROVENANCE_NOT_ACCEPTANCE',
          'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
          'normalization_report_sha256': sha(norm_bytes), 'completed_evidence': results,
          'final_physical_identity_inputs': physical, 'protected_original_anchors': anchors,
          'native_full_chain': 'RUNNING_NOT_INCLUDED', 'tests_executed_by_this_audit': 0,
          'production_api_calls': 0}
DEST.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'destination': str(DEST), 'sha256': sha(DEST.read_bytes()),
                  'completed_evidence_count': len(results), 'identity_inputs': len(physical),
                  'other_differences_by_label': {
                      r['label']: [x['path'] for x in r['other_differences_requiring_scope_comparison']]
                      for r in results}, 'protected_originals_equal': True}))
