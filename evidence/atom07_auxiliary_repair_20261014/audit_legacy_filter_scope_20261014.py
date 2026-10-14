"""Read-only baseline and actual signed-source scope for all filter differences."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
OUT = Path(__file__).resolve().parent
DEST = OUT/'legacy_filter_scope_20261014.json'
if DEST.exists(): raise SystemExit('LEGACY_FILTER_AUDIT_ALREADY_EXISTS')
sys.path.insert(0,str(ROOT))
from tools import cnw_live_authorization as auth
signed_sources, implementation_sha = auth.implementation_identity()
diagnosis = json.loads((OUT/'final_source_identity_mismatches_20261014.json').read_bytes())
rows = []
for item in diagnosis['all_mismatches']:
    name = item['path']
    raw = (ROOT/name).read_bytes()
    baseline = {}
    for label,commit in [('returned07','f8c72d59b070a3544047189de0fb31f3b138e6df'),
                         ('frozen06','84e022de0fee6eb7d7eec4c248703621129491e1')]:
        old = subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT)
        record = {'commit':commit,'git_blob_sha256':hashlib.sha256(old).hexdigest(),
            'same_exact_bytes':raw==old,'same_universal_newline_bytes':raw.replace(b'\r\n',b'\n')==old.replace(b'\r\n',b'\n')}
        if name.endswith('.py'):
            record['same_python_ast']=ast.dump(ast.parse(raw),include_attributes=False)==ast.dump(ast.parse(old),include_attributes=False)
        baseline[label]=record
    key = name.removeprefix('tools/')
    rows.append({**item,'listed_in_actual_signed_implementation_sources':key in signed_sources,
        'baselines':baseline})
signed = []
for key,digest in signed_sources.items():
    name = key if key.startswith('prompts/') else 'plans/'+key if key=='MASTER_PLAN_GENERIC_APP_R5.md' else 'tools/'+key
    raw = (ROOT/name).read_bytes()
    def oid(*args): return subprocess.check_output(['git',*args],cwd=ROOT,input=raw).decode().strip()
    signed.append({'path':name,'sha256':digest,'physical_equals_git_filter':oid('hash-object','--stdin')==oid('hash-object','--path='+name,'--stdin')})
value = {'status':'LEGACY_FILTER_SCOPE_NOT_ACCEPTANCE','legacy_filter_differences':rows,
    'actual_signed_implementation_sha256':implementation_sha,'actual_signed_sources':signed,
    'all_signed_sources_physical_equal_git_filter':all(row['physical_equals_git_filter'] for row in signed),
    'source_changed_by_audit':False,'tests_run_by_audit':0,
    'limits':'Reports exact raw differences and declared scope; does not authorize normalization, alter any test result, or sign candidate acceptance.'}
DEST.write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({'path':str(DEST),'sha256':hashlib.sha256(DEST.read_bytes()).hexdigest(),
    'difference_count':len(rows),'signed_difference_count':sum(row['listed_in_actual_signed_implementation_sources'] for row in rows),
    'all_legacy_same_universal_newline':all(all(record['same_universal_newline_bytes'] for record in row['baselines'].values()) for row in rows),
    'all_signed_sources_physical_equal_git_filter':value['all_signed_sources_physical_equal_git_filter']}))
