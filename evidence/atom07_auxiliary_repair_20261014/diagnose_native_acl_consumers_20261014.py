"""One bounded real six-stage/one-Lens diagnosis, never an acceptance test."""
import ast
from contextlib import ExitStack
import ctypes
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import threading
import time
import traceback
from unittest.mock import patch

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
OUT = Path(__file__).resolve().parent
PREFIX = 'native_acl_consumers_diagnosis_20261014'
DEST = OUT / (PREFIX+'.json')
EVENTS = OUT / (PREFIX+'.events.jsonl')
DRIVER = OUT / (PREFIX+'.driver.py')
if any(p.exists() for p in (DEST,EVENTS,DRIVER)):
    raise SystemExit('DIAGNOSIS_ALREADY_EXISTS')
for key in list(os.environ):
    if 'API_KEY' in key or key.startswith('STORYSTUDIO_') or key in {'OPENAI_ACCESS_TOKEN','ANTHROPIC_AUTH_TOKEN'}:
        os.environ.pop(key)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['CNW_LIVE_GRANT_TEST_EVIDENCE'] = str(OUT/(PREFIX+'.consumers.json'))
sys.path.insert(0,str(ROOT))
def audit(name,args):
    if name in {'socket.connect','socket.sendto','socket.getaddrinfo'}:
        raise RuntimeError('OFFLINE_DIAGNOSIS_NETWORK_FORBIDDEN')
sys.addaudithook(audit)

from tests import test_cnw_signed_critics_consumers as original
from tools import cnw_request_identity

paths = sorted(set([*(ROOT/'tools').glob('*.py'),*(ROOT/'tools').glob('*.cjs'),
                    *(ROOT/'tools').glob('*.ps1'),*(ROOT/'prompts/cnw').glob('*.md'),
                    ROOT/'AGENTS.md', ROOT/'plans/MASTER_PLAN_GENERIC_APP_R5.md',
                    Path(original.__file__), ROOT/'tests/test_cnw_live_authorization.py',
                    ROOT/'tests/test_cnw_early_e2e.py',ROOT/'tests/test_p2_cost_guard.py']))
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def snapshot():
    return {p.relative_to(ROOT).as_posix():digest(p.read_bytes()) for p in paths}
before = snapshot()
script_before = digest(Path(__file__).read_bytes())
lock = threading.Lock()
count = inflight = peak = 0
started = time.monotonic()
def event(value):
    with lock:
        with EVENTS.open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(value,ensure_ascii=False)+'\n')
def mark(label):
    handles = ctypes.c_ulong()
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.GetProcessHandleCount.argtypes = [ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
    ok = kernel.GetProcessHandleCount(kernel.GetCurrentProcess(),ctypes.byref(handles))
    event({'kind':'milestone','label':label,'elapsed_s':time.monotonic()-started,
           'python_threads':threading.active_count(),'own_process_handles':handles.value if ok else None,
           'cli_calls':count,'max_cli_inflight':peak})

real_run = subprocess.run
def delegated_run(command,**kwargs):
    global count,inflight,peak
    basename = Path(str(command[0])).name.lower()
    if basename not in {'whoami.exe','icacls.exe'}:
        return real_run(command,**kwargs)
    if time.monotonic()-started > 1200 or count >= 2000:
        raise RuntimeError('BOUNDED_ACL_DIAGNOSIS_LIMIT_REACHED')
    begin = time.monotonic()
    with lock:
        count += 1
        number = count
        inflight += 1
        peak = max(peak,inflight)
    row = {'kind':'cli','number':number,'basename':basename,'start_elapsed_s':begin-started,
           'thread_name':threading.current_thread().name,'thread_id':threading.get_ident(),
           'timeout_s':kwargs.get('timeout'),
           'stack_functions':[frame.name for frame in traceback.extract_stack(limit=14)]}
    event({**row,'status':'STARTED'})
    try:
        result = real_run(command,**kwargs)
        for field in ('stdout','stderr'):
            data = getattr(result,field) or ''
            raw = data.encode('utf-8') if isinstance(data,str) else data
            row[field+'_sha256'] = digest(raw)
            row[field+'_byte_count'] = len(raw)
        row.update(status='COMPLETED',returncode=result.returncode)
        return result
    except Exception as exc:
        row.update(status='FAILED',error_type=type(exc).__name__)
        raise
    finally:
        row['duration_s'] = time.monotonic()-begin
        with lock:
            inflight -= 1
        event(row)

# Reuse the existing deterministic transport/service boundary callbacks.
# Only the external diagnostic driver is bounded; no project test, actual
# stage, authorization, permission or provider consumer function is replaced.
source = textwrap.dedent(inspect.getsource(original.SignedCriticsConsumerTests.
    test_native_plot_text_shared_fees_pending_cache_and_refine_consumption))
tree = ast.parse(source)
fn = tree.body[0]
fn.name = 'run_bounded_diagnosis'
for node in fn.body:
    if isinstance(node,ast.FunctionDef) and node.name == 'service':
        for statement in node.body:
            if isinstance(statement,ast.Try):
                statement.body.append(ast.parse("mark('native_service_finished')").body[0])
transport = next(node for node in fn.body if isinstance(node,ast.With)
    and any(isinstance(item.context_expr,ast.Call)
            and isinstance(item.context_expr.func,ast.Name)
            and item.context_expr.func.id == '_isolated_live_transport' for item in node.items))
transport.body = ast.parse('''
for stage in r.CNW_STAGES[:6]:
    recovery.execute_checked(s.run, stage)
mark('before_one_lens')
requests = cnw_request_identity.expected_requests(s.run, stage='multi_lens_review', role_id='style')
if len(requests) != 1:
    raise RuntimeError('DIAGNOSTIC_EXPECTED_ONE_LEGITIMATE_LENS')
r._parallel_provider_calls(s.run, requests)
mark('after_one_lens')
''').body
fn.body = fn.body[:fn.body.index(transport)+1]
ast.fix_missing_locations(tree)
DRIVER.write_text(ast.unparse(tree)+'\n',encoding='utf-8')
namespace = dict(original.__dict__)
namespace.update(mark=mark,cnw_request_identity=cnw_request_identity)
exec(compile(tree,str(DRIVER),'exec'),namespace)
case = original.SignedCriticsConsumerTests()
error = None
mark('start')
try:
    with patch('subprocess.run',side_effect=delegated_run):
        case.setUp()
        namespace['run_bounded_diagnosis'](case)
except Exception as exc:
    error = {'type':type(exc).__name__,'message':str(exc),
             'traceback':traceback.format_exc()}
finally:
    mark('terminal_before_cleanup')
    case.doCleanups()
    mark('terminal_after_cleanup')
after = snapshot()
report = {'status':'BOUNDED_CONSUMER_DIAGNOSIS_NOT_ACCEPTANCE','error':error,
          'source_before':before,'source_after':after,'source_unchanged':before==after,
          'diagnostic_script_sha256_before':script_before,
          'diagnostic_script_sha256_after':digest(Path(__file__).read_bytes()),
          'original_test_source_sha256':digest(Path(original.__file__).read_bytes()),
          'generated_driver_sha256':digest(DRIVER.read_bytes()),
          'events_sha256':digest(EVENTS.read_bytes()),'cli_calls':count,'max_cli_inflight':peak,
          'elapsed_s':time.monotonic()-started,'real_provider_calls':0,
          'scope':'Actual first six stages/native Plot five calls and one legitimate style request only. No five-Lens stage materialization, Verifiers, Refine or full E2E acceptance.'}
DEST.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'report':str(DEST),'sha256':digest(DEST.read_bytes()),'error':error,
                  'cli_calls':count,'max_cli_inflight':peak,'source_unchanged':before==after}))
raise SystemExit(1 if error is not None or before != after else 0)
