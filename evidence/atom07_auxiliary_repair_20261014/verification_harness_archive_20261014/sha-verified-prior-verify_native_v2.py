"""Pinned native offline verification with target and harness byte identities."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
OUT = Path(__file__).resolve().parent
label, target = sys.argv[1:]
module = '.'.join(target.split('.')[:2])
target_path = ROOT / (module.replace('.', '/') + '.py')
if not target.startswith('tests.test_') or not target_path.is_file():
    raise SystemExit('VERIFICATION_TARGET_SOURCE_MISSING')
paths = sorted((ROOT / 'tools').glob('*.py'))
paths += [ROOT / name for name in ('plans/MASTER_PLAN_GENERIC_APP_R5.md',
    'tests/test_cnw_live_authorization.py', 'tests/test_cnw_early_e2e.py',
    'tests/test_p2_cost_guard.py')]
paths = sorted(set(paths + [target_path]))

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def snapshot():
    return {path.relative_to(ROOT).as_posix(): digest(path.read_bytes()) for path in paths}

before = snapshot()
harness_before = digest(Path(__file__).read_bytes())
raw = OUT / (label + '.raw.txt')
if raw.exists():
    raise SystemExit('EVIDENCE_ALREADY_EXISTS')
env = dict(os.environ)
for key in list(env):
    if 'API_KEY' in key or key.startswith('STORYSTUDIO_') or key in {'OPENAI_ACCESS_TOKEN', 'ANTHROPIC_AUTH_TOKEN'}:
        env.pop(key)
env['PYTHONDONTWRITEBYTECODE'] = '1'
env['CNW_LIVE_GRANT_TEST_EVIDENCE'] = str(OUT / (label + '.consumers.json'))
code = '''import sys,runpy
def audit(name,args):
    if name in {'socket.connect','socket.sendto','socket.getaddrinfo'}:
        raise RuntimeError('OFFLINE_VERIFICATION_NETWORK_FORBIDDEN')
sys.addaudithook(audit)
sys.argv=['unittest','-v',sys.argv[1]]
runpy.run_module('unittest',run_name='__main__')
'''
argv = [sys.executable, '-c', code, target]
with raw.open('xb') as stream:
    result = subprocess.run(argv, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
report = {'label': label, 'command_argv': argv, 'exit_code': result.returncode,
    'source_before': before, 'source_after': snapshot(), 'raw_sha256': digest(raw.read_bytes()),
    'harness_sha256_before': harness_before, 'harness_sha256_after': digest(Path(__file__).read_bytes()),
    'simulation_status': 'SIMULATED', 'real_provider_calls': 0}
report['source_unchanged'] = (report['source_before'] == report['source_after']
    and report['harness_sha256_before'] == report['harness_sha256_after'])
(OUT / (label + '.check.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({key: report[key] for key in ('label', 'exit_code', 'raw_sha256', 'source_unchanged')}))
print(raw.read_text(encoding='utf-8', errors='replace')[-6000:])
raise SystemExit(result.returncode)
