"""Apply only the Controller-approved external request selection correction."""
import ast
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
original = OUT/'diagnose_native_acl_consumers_after_preflight_20261014.py'
target = OUT/'diagnose_native_acl_consumers_single_lens_corrected_20261014.py'
if target.exists():
    raise SystemExit('CORRECTED_DIAGNOSTIC_ALREADY_EXISTS')
raw = original.read_bytes()
if hashlib.sha256(raw).hexdigest()!='49e36c36af0367259153c26b9b18cc3bf02f3805d115ead31991fcfa15d2e349':
    raise SystemExit('ORIGINAL_DIAGNOSTIC_CHANGED')
source = raw.decode('utf-8')
old = "requests = cnw_request_identity.expected_requests(s.run, stage='multi_lens_review', role_id='style')"
new = old.replace('requests =','candidates =')+"\nrequests = [call for call in candidates if call['stage'] == 'multi_lens_review' and call['role_id'] == 'style']"
if source.count(old)!=1:
    raise SystemExit('REQUEST_SELECTOR_SOURCE_MISMATCH')
source = source.replace(old,new)
source = source.replace("PREFIX = 'native_acl_consumers_after_preflight_20261014'", "PREFIX = 'native_acl_consumers_single_lens_corrected_20261014'")
compile(source,str(target),'exec')
target.write_text(source,encoding='utf-8')
value = {'status':'EXTERNAL_DRIVER_CORRECTION_NOT_ACCEPTANCE','original_script_sha256':hashlib.sha256(raw).hexdigest(),
    'corrected_script_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
    'only_change':'New observation label; select unique actual style candidate from complete legitimate five-Lens list.',
    'production_source_changes':0,'cli_bound':60000,'wall_bound_seconds':1200}
(OUT/'corrected_single_lens_driver_change_20261014.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value))
