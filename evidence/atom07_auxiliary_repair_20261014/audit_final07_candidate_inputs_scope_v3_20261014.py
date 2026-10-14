"""Read-only candidate provenance. No test execution or acceptance authority."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
OUT = Path(__file__).resolve().parent
EV = ROOT / 'evidence/atom07_auxiliary_repair_20261014'
LABEL = 'consolidated_final_native_full_chain_after_preflight'
DEST = OUT / 'final07_candidate_input_audit_scope_v3_20261014.json'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(*args, input=None, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, input=input)

def defs(raw):
    return {node.name: sha(ast.dump(node, include_attributes=False).encode())
            for node in ast.parse(raw.decode('utf-8-sig')).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}

if DEST.exists():
    raise SystemExit('AUDIT_ALREADY_EXISTS')
complete = json.loads((OUT / (LABEL + '.check.json')).read_bytes())
if complete['exit_code'] or not complete['source_unchanged']:
    raise SystemExit('FULL_CHAIN_NOT_TERMINAL_PASS')

sources = []
for name, recorded in complete['source_after'].items():
    raw = (ROOT / name).read_bytes()
    raw_oid = git('hash-object', '--stdin', input=raw).decode().strip()
    filtered_oid = git('hash-object', '--path=' + name, '--stdin', input=raw).decode().strip()
    sources.append({'path': name, 'sha256': sha(raw),
                    'equals_full_chain_source': sha(raw) == recorded,
                    'physical_equals_git_filter': raw_oid == filtered_oid})
legacy_report = json.loads((OUT/'legacy_filter_scope_20261014.json').read_bytes())
legacy = {row['path']:row for row in legacy_report['legacy_filter_differences']}
if len(legacy) != 12 or not all(row['equals_full_chain_source'] for row in sources):
    raise SystemExit('CURRENT_SOURCE_DIFFERS_FROM_FULL_TEST')
signed = legacy_report['actual_signed_sources']
candidate_source_paths = set(git('diff','--name-only').decode().splitlines())
candidate_source_paths.update(row['path'] for row in json.loads(
    (OUT/'atom07_candidate_path_preparation_20261014.json').read_bytes())['paths']
    if row['path'].startswith('tests/') and row['path'].endswith('.py'))
for row in signed:
    raw = (ROOT/row['path']).read_bytes()
    if (sha(raw) != row['sha256'] or git('hash-object','--stdin',input=raw) !=
            git('hash-object','--path='+row['path'],'--stdin',input=raw)):
        raise SystemExit('SIGNED_IMPLEMENTATION_GIT_BYTE_MISMATCH')
for name in candidate_source_paths:
    if not name.startswith(('tools/','tests/')) or not name.endswith(('.py','.ps1','.cjs')):
        continue
    raw = (ROOT/name).read_bytes()
    if git('hash-object','--stdin',input=raw) != git('hash-object','--path='+name,'--stdin',input=raw):
        raise SystemExit('MODIFIED_SOURCE_GIT_BYTE_MISMATCH:'+name)
for row in sources:
    if row['physical_equals_git_filter']:
        row['comparison_mode'] = 'RAW_BYTE_IDENTICAL_TO_GIT'
        continue
    old = legacy.get(row['path'])
    if (old is None or old['current_sha256'] != row['sha256']
            or old['listed_in_actual_signed_implementation_sources']
            or row['path'] in candidate_source_paths
            or not all(item['same_universal_newline_bytes'] for item in old['baselines'].values())):
        raise SystemExit('UNAPPROVED_LEGACY_FILTER_DIFFERENCE:'+row['path'])
    row['comparison_mode'] = 'DECLARED_UNMODIFIED_LEGACY_LF_EQUIVALENCE_NOT_REEXECUTION'
    row['legacy_baselines'] = old['baselines']
    row['original_raw_oid'], row['git_filtered_oid'] = old['raw_oid'], old['filtered_oid']


tests = []
for check_path in sorted(EV.glob('*.check.json')):
    check = json.loads(check_path.read_bytes())
    raw_path = check_path.with_name(check_path.name.removesuffix('.check.json') + '.raw.txt')
    raw_digest = sha(raw_path.read_bytes()) if raw_path.exists() else None
    tests.append({'check_path': check_path.relative_to(ROOT).as_posix(),
                  'check_sha256': sha(check_path.read_bytes()),
                  'raw_sha256': raw_digest,
                  'raw_matches_record': raw_digest == check.get('raw_sha256'),
                  'exit_code': check.get('exit_code'),
                  'source_unchanged_during_run': check.get('source_unchanged'),
                  'interpretation': 'PROVENANCE_ONLY_EACH_RESULT_RETAINS_ORIGINAL_SCOPE'})
if any(not row['raw_matches_record'] for row in tests):
    raise SystemExit('RAW_EVIDENCE_HASH_MISMATCH')

comparisons = []
for name in ('cnw_roles', 'cnw_review', 'cnw_lint', 'cnw_contract', 'cnw_export',
             'cnw_revision', 'cnw_import_workflow', 'cnw_runner', 'cnw_recovery',
             'cnw_request_identity', 'cnw_project', 'cnw_pack_app', 'cnw_critics_adapter',
             'cnw_live_authorization', 'cnw_nk_adapter', 'p2_06_critics_run'):
    path = 'tools/' + name + '.py'
    now_raw = (ROOT / path).read_bytes()
    now = defs(now_raw)
    comparison = {'path': path, 'current_sha256': sha(now_raw), 'baselines': {}}
    for label, commit in [('frozen06', '84e022de0fee6eb7d7eec4c248703621129491e1'),
                          ('returned07', 'f8c72d59b070a3544047189de0fb31f3b138e6df')]:
        tree_paths = git('ls-tree', '-r', '--name-only', commit).decode().splitlines()
        if path not in tree_paths:
            comparison['baselines'][label] = {'commit': commit, 'status': 'ABSENT_IN_EXACT_TREE'}
            continue
        old_raw = git('show', commit + ':' + path)
        old = defs(old_raw)
        comparison['baselines'][label] = {
            'commit': commit, 'sha256': sha(old_raw),
            'same_universal_newline_text': now_raw.replace(b'\r\n', b'\n') == old_raw.replace(b'\r\n', b'\n'),
            'unchanged_definitions': sorted(key for key in now if now.get(key) == old.get(key)),
            'changed_definitions': sorted(key for key in now.keys() & old.keys() if now[key] != old[key]),
            'added_definitions': sorted(now.keys() - old.keys()),
            'removed_definitions': sorted(old.keys() - now.keys())}
    comparisons.append(comparison)

anchors = []
for path, expected in [
    ('workspace/CQ_F01_TS_INPUT_V5/runs/F01-TS-V5-20261011-01/run_state.json',
     '3bae0722506641f1c14840d2f2568f03484cd6b1298c972baf3700d0de42ee0d'),
    ('runtime/private/p2-cost-ledger.json',
     'c8b0705f491ef824db01be0b7991f4db9db7d84e153c26481e93a4fdcd0eab9b')]:
    digest = sha((ROOT / path).read_bytes())
    anchors.append({'object': path, 'sha256': digest, 'frozen_sha256': expected,
                    'unchanged': digest == expected})
if not all(row['unchanged'] for row in anchors):
    raise SystemExit('PROTECTED_ORIGINAL_CHANGED')

frozen = Path(r'D:\CangqiStudio\StoryStudio_CNW_REFERENCE_PRE_R5')
reference = {'commit': git('rev-parse', 'HEAD', cwd=frozen).decode().strip(),
             'tree': git('rev-parse', 'HEAD^{tree}', cwd=frozen).decode().strip(),
             'porcelain': git('status', '--porcelain', cwd=frozen).decode()}
if (reference['commit'] != '26b72cea21dce45eede21cffddd4e75307d75652'
        or reference['tree'] != '535496ba3b8a331e12d0e5e161b15bf21a25393e'
        or reference['porcelain']):
    raise SystemExit('FROZEN_BASELINE_CHANGED')

frozen_copies = []
for original, copy in [('ATOM06_CONTROLLER_ACCEPT_84e022d_20261013.md', 'frozen_atom06_controller_original.md'),
                       ('ATOM06_FREEZE_84e022d_20261013.json', 'frozen_atom06_record_original.json')]:
    original_raw = (ROOT / 'evidence' / original).read_bytes()
    copied_raw = (EV / copy).read_bytes()
    if original_raw != copied_raw:
        raise SystemExit('FROZEN06_COPY_CHANGED')
    frozen_copies.append({'original': original, 'copy': copy, 'sha256': sha(copied_raw)})

report = {'status': 'CANDIDATE_INPUT_PROVENANCE_NOT_ACCEPTANCE',
          'head_before_candidate': git('rev-parse', 'HEAD').decode().strip(),
          'full_chain_source_inputs': sources, 'actual_signed_sources': signed,
          'legacy_filter_scope_sha256':sha((OUT/'legacy_filter_scope_20261014.json').read_bytes()),
          'comparison_policy':'All 67 current physical SHA match terminal test; actual signed/modified sources are byte exact; 12 unchanged legacy raw differences are explicit LF equivalence, not new execution.',
          'raw_evidence_index': tests,
          'definition_comparisons': comparisons, 'protected_anchors': anchors,
          'frozen_reference': reference, 'frozen06_exact_copies': frozen_copies,
          'tests_run_by_this_audit': 0, 'real_provider_calls': 0,
          'limits': 'Static equality and test metadata do not confer method fidelity, production authorization, candidate acceptance or next Atom permission.'}
DEST.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'path': str(DEST), 'sha256': sha(DEST.read_bytes()),
                  'source_count': len(sources), 'raw_evidence_count': len(tests),
                  'protected_anchors_unchanged': True, 'frozen_reference_unchanged': True}))
