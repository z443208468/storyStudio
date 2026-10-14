"""Prepare only the externally approved provenance-scope correction."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
original = OUT/'audit_final07_candidate_inputs_after_preflight_20261014.py'
target = OUT/'audit_final07_candidate_inputs_scope_v3_20261014.py'
if target.exists(): raise SystemExit('SCOPED_PROVENANCE_ALREADY_PREPARED')
source = original.read_text(encoding='utf-8')
old = "if not all(row['equals_full_chain_source'] and row['physical_equals_git_filter'] for row in sources):\n    raise SystemExit('CANDIDATE_SOURCE_BYTES_CHANGED')"
new = '''legacy_report = json.loads((OUT/'legacy_filter_scope_20261014.json').read_bytes())
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
'''
if source.count(old)!=1: raise SystemExit('SCOPED_PROVENANCE_TRANSFORM_MISMATCH')
source = source.replace(old,new)
source = source.replace("DEST = OUT / 'final07_candidate_input_audit_after_preflight_20261014.json'",
    "DEST = OUT / 'final07_candidate_input_audit_scope_v3_20261014.json'")
source = source.replace("'full_chain_source_inputs': sources, 'raw_evidence_index': tests,",
    "'full_chain_source_inputs': sources, 'actual_signed_sources': signed,\n          'legacy_filter_scope_sha256':sha((OUT/'legacy_filter_scope_20261014.json').read_bytes()),\n          'comparison_policy':'All 67 current physical SHA match terminal test; actual signed/modified sources are byte exact; 12 unchanged legacy raw differences are explicit LF equivalence, not new execution.',\n          'raw_evidence_index': tests,")
compile(source,str(target),'exec')
target.write_text(source,encoding='utf-8')
print(json.dumps({'prepared_audit':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
    'production_source_changed':False,'original_failed_audit_preserved':True}))
