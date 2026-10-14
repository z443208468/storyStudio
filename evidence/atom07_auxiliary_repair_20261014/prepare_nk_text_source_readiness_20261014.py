"""Approved LF/source-byte preparation, without executing project functions."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
OUT = Path(__file__).resolve().parent
PRE = OUT/'nk_text_boundary_preimages_20261014'
DEST = OUT/'nk_text_source_readiness_20261014.json'
if DEST.exists():
    raise SystemExit('EVIDENCE_ALREADY_EXISTS')
recorded = json.loads((ROOT/'evidence/atom07_auxiliary_repair_20261014/candidate_lf_normalization_20261014.json').read_bytes())
names = {r['path'] for r in recorded['records']}
names.update(['tools/nk-live-fetch.cjs','tools/cnw_w10_nk_live.ps1',
    'tools/p2_06_nk_live_probe.ps1','tools/p2_nk_live_probe.ps1',
    'tests/test_cnw_nk_input_limits.py','tests/test_cnw_critics_text_input_bytes.py'])
records = []
for name in sorted(names):
    path = ROOT/name
    raw = path.read_bytes()
    lf = raw.replace(b'\r\n',b'\n')
    if name.endswith('.py'):
        assert ast.dump(ast.parse(raw.decode('utf-8-sig'))) == ast.dump(ast.parse(lf.decode('utf-8-sig')))
    if name in {'tools/cnw_w10_nk_live.ps1','tools/p2_06_nk_live_probe.ps1','tools/p2_nk_live_probe.ps1'}:
        old = (PRE/name).read_bytes().replace(b'\r\n',b'\n').decode('utf-8')
        expected = old.replace(
            "'STORYSTUDIO_NK_LIVE_REQUEST_ID')",
            "'STORYSTUDIO_NK_LIVE_REQUEST_ID','STORYSTUDIO_NK_MAX_INPUT_TOKENS')")
        expected = expected.replace('    $env:STORYSTUDIO_NK_LIVE_REQUEST_ID = $RequestId\n',
            "    $env:STORYSTUDIO_NK_LIVE_REQUEST_ID = $RequestId\n    $env:STORYSTUDIO_NK_MAX_INPUT_TOKENS = '10000'\n")
        if lf.decode('utf-8') != expected:
            raise SystemExit('UNEXPECTED_LEGACY_SCRIPT_DIFF:'+name)
    if raw != lf:
        path.write_bytes(lf)
    raw_oid = subprocess.check_output(['git','hash-object','--stdin'],input=lf,cwd=ROOT).decode().strip()
    filtered = subprocess.check_output(['git','hash-object','--path='+name,'--stdin'],input=lf,cwd=ROOT).decode().strip()
    if raw_oid != filtered:
        raise SystemExit('GIT_FILTER_MISMATCH:'+name)
    records.append({'path':name,'before_sha256':hashlib.sha256(raw).hexdigest(),
        'final_sha256':hashlib.sha256(lf).hexdigest(),'crlf_only_conversion':raw!=lf,
        'git_blob_oid':raw_oid,'physical_equals_git_filtered_bytes':True})
DEST.write_text(json.dumps({'status':'BYTE_READINESS_NOT_ACCEPTANCE','records':records,
    'legacy_script_allowed_edits':'add cap env save/restore name and assign 10000 only',
    'tests_run':0,'production_calls':0},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'destination':str(DEST),'sha256':hashlib.sha256(DEST.read_bytes()).hexdigest(),
    'records':len(records),'converted':[r['path'] for r in records if r['crlf_only_conversion']]}))
