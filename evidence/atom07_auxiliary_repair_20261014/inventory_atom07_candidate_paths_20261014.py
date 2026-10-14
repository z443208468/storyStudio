"""Read-only, explicit candidate preparation; no staging or acceptance."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
OUT = Path(__file__).resolve().parent
DEST = OUT/'atom07_candidate_path_preparation_20261014.json'
if DEST.exists():
    raise SystemExit('PATH_INVENTORY_ALREADY_EXISTS')
def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf-8').splitlines()
def sha(raw): return hashlib.sha256(raw).hexdigest()
tracked = git('diff','--name-only')
allowed = {'.gitattributes','AGENTS.md'}
allowed.update('tools/'+name for name in (
    'cnw_critics_adapter.py','cnw_live_authorization.py','cnw_nk_adapter.py','cnw_recovery.py',
    'cnw_request_identity.py','cnw_runner.py','cnw_w10_nk_live.ps1','nk-live-fetch.cjs',
    'p2_06_critics_run.py','p2_06_nk_live_probe.ps1','p2_nk_live_probe.ps1'))
allowed.update('tests/'+name for name in (
    'test_cnw_adapters.py','test_cnw_live_authorization.py','test_cnw_nk_request_identity.py',
    'test_cnw_operation_authorization.py','test_cnw_runner.py','test_cnw_signed_operations.py',
    'test_cnw_support_consumers.py','test_critics_bridge_datahome.py'))
if set(tracked)-allowed:
    raise SystemExit('UNEXPECTED_TRACKED_SCOPE')
new_tests = ['tests/'+name for name in (
    'test_cnw_critics_text_input_bytes.py','test_cnw_native_input_limits.py',
    'test_cnw_native_mock_live_boundary.py','test_cnw_nk_input_limits.py',
    'test_cnw_signed_auxiliary_consumers.py','test_cnw_signed_critics_accounting.py',
    'test_cnw_signed_critics_consumers.py')]
untracked = git('ls-files','--others','--exclude-standard')
documents = [name for name in untracked if name.startswith('evidence/ATOM07_') and name.endswith('.md')]
evidence = [path.relative_to(ROOT).as_posix() for path in (ROOT/'evidence/atom07_auxiliary_repair_20261014').iterdir() if path.is_file()]
selected = sorted(set(tracked+new_tests+documents+evidence))
rows, flags = [], []
for name in selected:
    path = ROOT/name
    if not path.is_file() or path.is_symlink() or any(part in {'.env','workspace','runtime','runs','deliverables'} for part in Path(name).parts):
        raise SystemExit('FORBIDDEN_OR_MISSING_CANDIDATE_PATH:'+name)
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig')
    # Heuristic flags are never verdicts; no match content is printed.
    for number,line in enumerate(text.splitlines(),1):
        for category,pattern in (('credential_shape',r'\bsk-[A-Za-z0-9_-]{32,}\b'),
                                 ('private_key_shape',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')):
            if re.search(pattern,line): flags.append({'path':name,'line':number,'category':category})
    rows.append({'path':name,'byte_count':len(raw),'sha256':sha(raw)})
report = {'status':'PREPARATION_NOT_CANDIDATE_NOT_ACCEPTANCE',
    'head':git('rev-parse','HEAD')[0],'paths':rows,'path_count':len(rows),
    'total_bytes':sum(row['byte_count'] for row in rows),
    'sensitive_shape_flags':flags,
    'preserved_untracked_outside_selection':sorted(set(untracked)-set(selected)),
    'source_staged':False,'tests_run_by_inventory':0,
    'limits':'The full-chain result is pending and its new evidence is not in this snapshot. Pattern scanning is only a flag check; fixture provenance and independent Controller privacy/scope review remain required. Nothing staged, committed or pushed.'}
DEST.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'path':str(DEST),'sha256':sha(DEST.read_bytes()),'path_count':len(rows),
    'total_bytes':report['total_bytes'],'flags':flags,
    'preserved_untracked_count':len(report['preserved_untracked_outside_selection'])}))
