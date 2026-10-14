"""Apply only reviewed LF conversion to frozen production/test preimages."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
OUT = Path(__file__).parent
report_path = OUT / 'candidate_lf_normalization_20261014.json'
if report_path.exists():
    raise SystemExit('NORMALIZATION_REPORT_ALREADY_EXISTS')
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
manifests = [OUT / 'identity_byte_preimages_20261014/identity_bytes.json',
             OUT / 'candidate_test_preimages_20261014/test_bytes.json']
records = [row for file in manifests for row in json.loads(file.read_bytes())['records']]
preimages = {}
for row in records:
    path = ROOT / row['path']
    raw = path.read_bytes()
    if sha(raw) != row['physical_sha256']:
        raise SystemExit('FROZEN_SOURCE_HAS_CHANGED: ' + row['path'])
    normalized = raw.replace(b'\r\n', b'\n')
    if row['path'].endswith('.py'):
        if ast.dump(ast.parse(raw.decode('utf-8')), include_attributes=False) != ast.dump(
                ast.parse(normalized.decode('utf-8')), include_attributes=False):
            raise SystemExit('AST_CHANGE_REJECTED: ' + row['path'])
    elif row['path'].endswith('.md'):
        if path.read_text(encoding='utf-8-sig') != normalized.decode('utf-8-sig'):
            raise SystemExit('READ_TEXT_CHANGE_REJECTED: ' + row['path'])
    preimages[row['path']] = (raw, normalized)
result = []
for relative, (raw, normalized) in preimages.items():
    path = ROOT / relative
    if path.read_bytes() != raw:
        raise SystemExit('FROZEN_SOURCE_HAS_CHANGED: ' + relative)
    if raw != normalized:
        path.write_bytes(normalized)
    filtered = subprocess.run(['git', 'hash-object', '--path=' + relative, '--stdin'],
        cwd=ROOT, input=normalized, check=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE).stdout.decode().strip()
    literal_oid = hashlib.sha1(('blob ' + str(len(normalized)) + '\0').encode() + normalized).hexdigest()
    if filtered != literal_oid or path.read_bytes() != normalized:
        raise SystemExit('LF_PHYSICAL_FILTERED_BYTES_MISMATCH: ' + relative)
    result.append({'path': relative, 'before_sha256': sha(raw), 'after_sha256': sha(normalized),
        'changed_only_crlf': raw != normalized, 'candidate_git_blob_oid': filtered,
        'physical_equals_filtered_git_bytes': True})
report_path.write_text(json.dumps({'status': 'LF_CONVERSION_NOT_ACCEPTANCE',
    'source_manifest_sha256': {str(p): sha(p.read_bytes()) for p in manifests},
    'records': result}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'paths_checked': len(result), 'crlf_only_converted':
    sum(row['changed_only_crlf'] for row in result), 'manifest': str(report_path),
    'manifest_sha256': sha(report_path.read_bytes())}))
