"""Bounded offline pytest run with full source/test byte snapshot."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
OUT = Path(__file__).resolve().parent
label, *targets = sys.argv[1:]
if not targets:
    raise SystemExit('EXPLICIT_TEST_TARGET_REQUIRED')
for target in targets:
    file = ROOT / target.split('::', 1)[0]
    if not file.is_file() or file.parent != ROOT / 'tests' or file.suffix != '.py':
        raise SystemExit('VERIFICATION_TARGET_SOURCE_MISSING')
paths = list((ROOT / 'tools').glob('*.py')) + list((ROOT / 'tests').glob('*.py'))
paths += list((ROOT / 'tools').glob('*.cjs')) + list((ROOT / 'tools').glob('*.ps1'))
paths += [ROOT / name for name in ('AGENTS.md', 'plans/MASTER_PLAN_GENERIC_APP_R5.md', 'tools/studio.ps1')]
for folder in ('config', 'prompts', 'patches'):
    paths += [path for path in (ROOT / folder).rglob('*')
              if path.is_file() and path.suffix in {'.json', '.yml', '.yaml', '.md', '.txt', '.patch'}]
paths = sorted(set(paths))

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
code = '''import sys,runpy,os
sys.path.insert(0,os.path.join(os.getcwd(),'tests'))
def audit(name,args):
    if name in {'socket.connect','socket.sendto','socket.getaddrinfo'}:
        raise RuntimeError('OFFLINE_VERIFICATION_NETWORK_FORBIDDEN')
sys.addaudithook(audit)
sys.argv=['pytest',*sys.argv[1:]]
runpy.run_module('pytest',run_name='__main__')
'''
argv = [sys.executable, '-c', code, *targets, '-vv', '--tb=short']
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
