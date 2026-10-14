"""Preserve preimages and create one explicitly bounded observation driver."""
import hashlib
import json
from pathlib import Path

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
OUT = Path(__file__).resolve().parent
manifest = OUT/'preflight_expiry_preimages_20261014'/'manifest.json'
if manifest.exists():
    raise SystemExit('PREIMAGE_MANIFEST_ALREADY_EXISTS')
expected = {
    'cnw_live_authorization.py':'d3398a17a91e46b3bb86a1f24d30579bc9a7275198d451a86d47055721b931ac',
    'test_cnw_live_authorization.py':'8b543be8bd8219c9c24a9a94d251c0416bd1df83563ce03f3490c6ebdb5f8982',
    'test_cnw_signed_operations.py':'d28d992507db6c4fdfc8c923c579ff7d36ba1e43ab6dc23c3de5b85b4f2f7d2c'}
records = []
for name, sha in expected.items():
    path = manifest.parent/name
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise SystemExit('PREIMAGE_HASH_MISMATCH:'+name)
    records.append({'relative_source':('tools/' if name.startswith('cnw_') else 'tests/')+name,
        'backup_file':str(path),'byte_count':len(raw),'sha256':sha})
manifest.write_text(json.dumps({'records':records,'purpose':'Controller approved repeated-preflight and terminal expiry fixes only'},indent=2),encoding='utf-8')

original = OUT/'diagnose_native_acl_consumers_20261014.py'
target = OUT/'diagnose_native_acl_consumers_after_preflight_20261014.py'
if target.exists():
    raise SystemExit('NEW_DIAGNOSTIC_ALREADY_EXISTS')
source = original.read_text(encoding='utf-8')
changes = {
    "PREFIX = 'native_acl_consumers_diagnosis_20261014'":"PREFIX = 'native_acl_consumers_after_preflight_20261014'",
    'count >= 2000':'count >= 60000',
    "exec(compile(tree,str(DRIVER),'exec'),namespace)":"exec(compile(DRIVER.read_text(encoding='utf-8'),str(DRIVER),'exec'),namespace)",
    "'elapsed_s':time.monotonic()-started,'real_provider_calls':0,":"'elapsed_s':time.monotonic()-started,'real_provider_calls':0,\n          'explicit_bounds':{'cli_calls':60000,'wall_seconds':1200},\n          'comparison_original_script_sha256':digest(original_script.read_bytes()),"}
for old,new in changes.items():
    if source.count(old) != 1:
        raise SystemExit('DIAGNOSTIC_TRANSFORM_MISMATCH')
    source = source.replace(old,new)
source = source.replace("OUT = Path(__file__).resolve().parent", "OUT = Path(__file__).resolve().parent\noriginal_script = OUT/'diagnose_native_acl_consumers_20261014.py'",1)
target.write_text(source,encoding='utf-8')
compile(source,str(target),'exec')
print(json.dumps({'preimage_manifest':str(manifest),'diagnostic':str(target),
    'diagnostic_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
    'cli_bound':60000,'wall_bound_seconds':1200}))
