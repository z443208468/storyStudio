from pathlib import Path
import os, sys, json, hashlib, subprocess
ROOT = Path('D:/CangqiStudio/StoryStudio')
OUT = Path(__file__).resolve().parent
label, targets = sys.argv[1], sys.argv[2:]
assert targets, 'TEST_TARGETS_REQUIRED'
files = ['tools/cnw_pack_app.py', 'tools/cnw_native_pack.py', 'tools/cnw_input_pack.py',
         'tools/cnw_task_requirements.py', 'tools/cnw_project.py', 'tools/cnw_runner.py',
         'tools/cnw_recovery.py', 'tools/cnw_roles.py', 'tools/cnw_review.py', 'tools/cnw_lint.py',
         'tools/cnw_export.py', 'tools/cnw_critics_adapter.py', 'tools/critics_bridge.py',
         'tools/p2_06_critics_run.py', 'tools/cnw_nk_adapter.py', 'tools/cost_guard.py',
         'tools/p2_cost_guard.py', 'tests/test_cnw_atom06.py', 'tests/test_cnw_task_consumers.py',
         'tests/test_cnw_pack_job.py', 'tests/test_cnw_native_pack_job.py',
         'tests/test_cnw_pack_attempts.py', 'tests/test_cnw_pack_app.py',
         'tests/test_cnw_support_consumers.py', 'tests/test_cnw_role_inputs.py',
         'tests/test_cnw_runner.py', 'tests/test_cnw_adapters.py',
         'plans/MASTER_PLAN_GENERIC_APP_R5.md']
def hashes():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}
before = hashes()
env = dict(os.environ)
for name in ('DEEPSEEK_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY'):
    env.pop(name, None)
env.update(PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1',
           PYTHONPATH=str(ROOT)+os.pathsep+str(ROOT/'tests'),
           ATOM06_EVIDENCE_OUTPUT=str(OUT/(label+'.roles.json')),
           ATOM06_TASK_EVIDENCE_OUTPUT=str(OUT/(label+'.tasks.json')),
           ATOM09_PACK_JOB_EVIDENCE_OUTPUT=str(OUT/(label+'.package.json')),
           ATOM09_NATIVE_JOB_EVIDENCE_OUTPUT=str(OUT/(label+'.native.json')),
           ATOM06_CAPACITY_EVIDENCE_OUTPUT=str(OUT/(label+'.capacity.json')))
bootstrap = ('import sys\nsys.path.insert(0,'+repr(str(ROOT))+')\n'
    'def deny(event,args):\n'
    " if event in ('socket.connect','socket.sendto','socket.getaddrinfo'): raise RuntimeError('OFFLINE_TEST_NETWORK_BLOCKED')\n"
    'sys.addaudithook(deny)\n')
if targets[0] == '--unittest':
    targets = targets[1:]
    bootstrap += ('import unittest\nsuite=unittest.TestLoader().loadTestsFromNames('+repr(targets)+')\n'
        'result=unittest.TextTestRunner(verbosity=2).run(suite)\nraise SystemExit(0 if result.wasSuccessful() else 1)\n')
else:
    bootstrap += 'import pytest\nraise SystemExit(pytest.main('+repr(targets+['-vv'])+'))\n'
command = [sys.executable, '-c', bootstrap]
raw_path = OUT/(label+'.raw.txt')
assert not raw_path.exists(), 'DO_NOT_OVERWRITE_ORIGINAL_TEST_RECORD'
with raw_path.open('xb') as capture:
    result = subprocess.run(command, cwd=ROOT, env=env, stdout=capture, stderr=subprocess.STDOUT)
raw_output = raw_path.read_bytes()
after = hashes()
check = {'label': label, 'command': command, 'targets': targets, 'exit_code': result.returncode,
         'python': sys.executable, 'raw_sha256': hashlib.sha256(raw_output).hexdigest(),
         'source_sha256_before': before, 'source_sha256_after': after, 'source_unchanged': before==after,
         'scope': 'ATOM06_CURRENT_OFFLINE_COMPONENTS_ONLY', 'network_audit': 'DENY_connect_sendto_getaddrinfo',
         'provider_credentials_removed': True}
(OUT/(label+'.check.json')).write_text(json.dumps(check, indent=2)+'\n', encoding='utf-8')
sys.stdout.buffer.write(raw_output)
sys.stdout.buffer.flush()
print('EXIT_CODE='+str(result.returncode))
print('SOURCE_UNCHANGED='+str(before==after))
raise SystemExit(result.returncode if before==after else 97)
