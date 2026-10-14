"""Freeze only public source preimages outside the repository before repair."""
import hashlib
import json
from pathlib import Path

root = Path(r'D:\CangqiStudio\StoryStudio')
destination = Path(__file__).resolve().parent / 'nk_text_boundary_preimages_20261014'
destination.mkdir(exist_ok=False)
names = ['tools/cnw_runner.py','tools/cnw_live_authorization.py','tools/nk-live-fetch.cjs',
         'tools/cnw_w10_nk_live.ps1','tools/p2_06_nk_live_probe.ps1','tools/p2_nk_live_probe.ps1',
         'tests/test_cnw_signed_auxiliary_consumers.py']
records = []
for name in names:
    raw = (root / name).read_bytes()
    backup = destination / name
    backup.parent.mkdir(parents=True,exist_ok=True)
    with backup.open('xb') as stream:
        stream.write(raw)
    assert backup.read_bytes() == raw
    records.append({'path':name,'size':len(raw),
                    'sha256':hashlib.sha256(raw).hexdigest(),'external_backup':str(backup)})
manifest = destination / 'preimages.json'
manifest.write_text(json.dumps({'status':'PUBLIC_SOURCE_PREIMAGE_ONLY','records':records},
                              ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'manifest':str(manifest),'sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
                  'record_count':len(records)}))
