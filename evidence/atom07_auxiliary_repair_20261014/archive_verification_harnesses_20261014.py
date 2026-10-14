"""Preserve current harnesses and SHA-verified recoveries of their prior bytes."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DEST = BASE/'verification_harness_archive_20261014'
DEST.mkdir(exist_ok=False)
specs = [
    ('verify_current_v2.py','lf_final_identity_revision_consumers.check.json',
     ["paths += list((ROOT / 'tools').glob('*.cjs')) + list((ROOT / 'tools').glob('*.ps1'))\n"]),
    ('verify_native_v2.py','lf_final_native_full_chain_finite_grant.check.json',
     ["paths += list((ROOT / 'tools').glob('*.cjs')) + list((ROOT / 'tools').glob('*.ps1'))\n",
      "paths += [path for path in (ROOT/'prompts/cnw').glob('*.md')]\n"]),
]
records=[]
for name, check_name, added in specs:
    current=(BASE/name).read_bytes()
    (DEST/('current-'+name)).write_bytes(current)
    check=json.loads((BASE/check_name).read_bytes())
    expected=check['harness_sha256_before']
    assert expected==check['harness_sha256_after']
    text=current.decode('utf-8').replace('\r\n','\n')
    for line in added:
        assert text.count(line)==1
        text=text.replace(line,'',1)
    recovered=None
    for candidate in (text.encode('utf-8'),text.replace('\n','\r\n').encode('utf-8')):
        if hashlib.sha256(candidate).hexdigest()==expected:
            recovered=candidate
            break
    if recovered is None:
        raise SystemExit('PRIOR_HARNESS_NOT_RECOVERABLE:'+name)
    path=DEST/('sha-verified-prior-'+name)
    path.write_bytes(recovered)
    records.append({'name':name,'current_sha256':hashlib.sha256(current).hexdigest(),
        'prior_recorded_sha256':expected,'recovered_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'recovery_method':'EXPLICIT_PATCH_REVERSAL_MATCHED_RECORDED_SHA_NOT_UNTOUCHED_ORIGINAL',
        'reference_check_sha256':hashlib.sha256((BASE/check_name).read_bytes()).hexdigest()})
manifest=DEST/'manifest.json'
manifest.write_text(json.dumps({'status':'HARNESS_PROVENANCE_NOT_TEST_RESULT','records':records},indent=2),encoding='utf-8')
print(json.dumps({'manifest':str(manifest),'sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'records':len(records)}))
