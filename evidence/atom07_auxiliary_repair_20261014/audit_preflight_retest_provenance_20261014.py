"""Read-only source/copy provenance for this consolidated round, not ACCEPT."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
OUT = Path(__file__).resolve().parent
EV = ROOT/'evidence/atom07_auxiliary_repair_20261014'
DEST = OUT/'consolidated_preflight_expiry_provenance.json'
if DEST.exists():
    raise SystemExit('PROVENANCE_ALREADY_EXISTS')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def defs(raw):
    return {node.name:sha(ast.dump(node,include_attributes=False).encode())
        for node in ast.parse(raw.decode('utf-8-sig')).body if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
old = defs((OUT/'preflight_expiry_preimages_20261014/cnw_live_authorization.py').read_bytes())
new = defs((ROOT/'tools/cnw_live_authorization.py').read_bytes())
changed = sorted(name for name in old.keys() & new.keys() if old[name]!=new[name])
if changed != ['_verify_bundle','build_request'] or old.keys()!=new.keys():
    raise SystemExit('UNEXPECTED_ROUND_SOURCE_SCOPE')
copies = []
for pattern in ('consolidated_preflight_expiry_consumers.*','native_acl_consumers_after_preflight_20261014.*'):
    for path in sorted(OUT.glob(pattern)):
        copied = EV/path.name
        copies.append({'name':path.name,'sha256':sha(path.read_bytes()),
            'exact_public_copy':copied.is_file() and copied.read_bytes()==path.read_bytes()})
sources = []
for name in ('consolidated_preflight_expiry_consumers.check.json','native_acl_consumers_after_preflight_20261014.json'):
    report = json.loads((OUT/name).read_bytes())
    sources.append({'report':name,'source_unchanged_during_run':report['source_unchanged'],
        'source_current_matches_report':all(sha((ROOT/key).read_bytes())==value
            for key,value in report['source_after'].items())})
value = {'status':'ROUND_PROVENANCE_NOT_ACCEPTANCE','changed_production_functions':changed,
    'copies':copies,'source_observations':sources,
    'actual_test_exit_code':json.loads((OUT/'consolidated_preflight_expiry_consumers.check.json').read_bytes())['exit_code'],
    'diagnosis_error':json.loads((OUT/'native_acl_consumers_after_preflight_20261014.json').read_bytes())['error'],
    'tests_run_by_audit':0,'real_provider_calls':0}
DEST.write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({'path':str(DEST),'sha256':sha(DEST.read_bytes()),'changed_production_functions':changed,
    'copy_count':len(copies),'copies_equal':all(row['exact_public_copy'] for row in copies),'source_observations':sources}))
if any(not row['exact_public_copy'] for row in copies) or any(not row['source_current_matches_report'] for row in sources):
    raise SystemExit(1)
