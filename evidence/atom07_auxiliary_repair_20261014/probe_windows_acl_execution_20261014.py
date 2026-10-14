"""Bounded real CLI/ACL diagnosis; only a newly owned fictional directory."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
sys.path.insert(0, str(ROOT))
from tools import project_paths

OUT = Path(__file__).resolve().parent
DEST = OUT / 'windows_acl_execution_probe_20261014.json'
if DEST.exists():
    raise SystemExit('PROBE_ALREADY_EXISTS')
before = hashlib.sha256(Path(project_paths.__file__).read_bytes()).hexdigest()
records, commands = [], []
real_run = subprocess.run

def timed_run(command, **kwargs):
    start = time.monotonic()
    try:
        result = real_run(command, **kwargs)
        commands.append({'executable': Path(command[0]).name, 'elapsed_s': time.monotonic()-start,
                         'returncode': result.returncode,
                         'stdout_sha256': hashlib.sha256(result.stdout.encode('utf-8')).hexdigest(),
                         'stdout_characters': len(result.stdout),
                         'stderr_sha256': hashlib.sha256(result.stderr.encode('utf-8')).hexdigest()})
        return result
    except Exception as exc:
        commands.append({'executable': Path(command[0]).name, 'elapsed_s': time.monotonic()-start,
                         'error_type': type(exc).__name__})
        raise

with tempfile.TemporaryDirectory(prefix='storystudio-acl-diagnosis-') as temporary:
    target = Path(temporary) / 'ExplicitFictionalDataHome'
    target.mkdir()
    with patch('subprocess.run', side_effect=timed_run):
        for label, worker, create in [('main_create',False,True), ('main_read',False,False),
                                      ('worker_read_1',True,False), ('worker_read_2',True,False)]:
            start = time.monotonic()
            count = len(commands)
            error = None
            try:
                if worker:
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        pool.submit(project_paths._windows_private_acl, target,
                                    create=False, require_independent=False).result()
                else:
                    project_paths._windows_private_acl(target,create=create,require_independent=False)
            except Exception as exc:
                error = {'type':type(exc).__name__,'message':str(exc)}
            records.append({'case':label,'elapsed_s':time.monotonic()-start,
                            'error':error,'actual_commands':commands[count:]})

report = {'status':'BOUNDED_DIAGNOSIS_NOT_ACCEPTANCE','timestamp_utc':datetime.now(timezone.utc).isoformat(),
          'source_sha256_before':before,
          'source_sha256_after':hashlib.sha256(Path(project_paths.__file__).read_bytes()).hexdigest(),
          'records':records,'real_provider_calls':0,'original_project_or_ledger_changes':0,
          'limitations':'Four actual ACL checks in an owned temporary directory only; cannot explain the complete-chain timeout by itself.'}
DEST.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'report':str(DEST),'sha256':hashlib.sha256(DEST.read_bytes()).hexdigest(),
                  'records':[{'case':r['case'],'elapsed_s':r['elapsed_s'],'error':r['error']} for r in records]}))
