"""Read-only terminal observation with original stopped diagnostic comparison."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

OUT = Path(__file__).resolve().parent
PREFIX = 'native_acl_consumers_after_preflight_20261014'
DEST = OUT/(PREFIX+'.summary.json')
if DEST.exists():
    raise SystemExit('SUMMARY_ALREADY_EXISTS')
report_path = OUT/(PREFIX+'.json')
report = json.loads(report_path.read_bytes())
events = [json.loads(line) for line in (OUT/(PREFIX+'.events.jsonl')).read_text(encoding='utf-8').splitlines()]
rows = [row for row in events if row['kind']=='cli' and row['status']!='STARTED']
durations = [row['duration_s'] for row in rows]
capture = json.loads((OUT/(PREFIX+'.consumers.json.terminal_capture.json')).read_bytes())
milestones = [row for row in events if row['kind']=='milestone']
state = capture['actual_run_state']
old = json.loads((OUT/'native_acl_consumers_diagnosis_20261014.summary.json').read_bytes())
value = {'status':'OBSERVATION_SUMMARY_NOT_ACCEPTANCE',
    'diagnostic_report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),
    'commands':dict(Counter(row['basename'] for row in rows)),
    'cli_returncodes':dict(Counter(str(row.get('returncode')) for row in rows)),
    'cli_error_types':dict(Counter(row['error_type'] for row in rows if 'error_type' in row)),
    'duration_s':{'mean':statistics.mean(durations),'median':statistics.median(durations),
        'maximum':max(durations),'total':sum(durations)},
    'stack_outer_functions':dict(Counter(row['stack_functions'][0] for row in rows)),
    'milestones':milestones, 'terminal_stages':{name:item['status'] for name,item in state['stages'].items()},
    'actual_provider_receipt_count':len(state.get('provider_requests',[])),
    'actual_synthetic_ledger_rows':len(capture['actual_synthetic_ledger']['requests']),
    'original_bounded_observation':{'commands':old['commands'],'duration_s':old['duration_s'],
        'terminal_stages':old['terminal_stages'],'limitations':old['limitations']},
    'comparison_limitations':'Different stopping points: original stopped before Plot at 2000 CLI calls; current explicitly bounds 60000 calls/1200 seconds. Counts/times are observations, not equivalent-work speedup or an explanation of the earlier timeouts. Function group counts are CLI event attribution, not full preflight invocation counts. No full-chain acceptance.',
    'diagnostic_error':report['error'], 'source_unchanged':report['source_unchanged']}
DEST.write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value))
