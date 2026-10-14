"""Report every current-source/Git-filter difference without changing bytes."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
OUT = Path(__file__).resolve().parent
DEST = OUT/'final_source_identity_mismatches_20261014.json'
if DEST.exists(): raise SystemExit('MISMATCH_REPORT_ALREADY_EXISTS')
check = json.loads((OUT/'consolidated_final_native_full_chain_after_preflight.check.json').read_bytes())
rows = []
for name,sha in check['source_after'].items():
    raw = (ROOT/name).read_bytes()
    def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT,input=raw).decode().strip()
    actual = hashlib.sha256(raw).hexdigest()
    raw_oid = git('hash-object','--stdin')
    filtered_oid = git('hash-object','--path='+name,'--stdin')
    if actual!=sha or raw_oid!=filtered_oid:
        rows.append({'path':name,'current_sha256':actual,'full_chain_sha256':sha,
            'current_matches_test':actual==sha,'physical_equals_git_filter':raw_oid==filtered_oid,
            'raw_oid':raw_oid,'filtered_oid':filtered_oid,
            'crlf_count':raw.count(b'\r\n'),'lf_count':raw.count(b'\n')})
value = {'status':'IDENTITY_DIAGNOSIS_NOT_ACCEPTANCE','all_mismatches':rows,
    'source_count':len(check['source_after']),'production_files_changed_by_diagnosis':0}
DEST.write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value))
