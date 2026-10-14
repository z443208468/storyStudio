"""Read-only statistics of the bounded diagnostic event log."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

OUT = Path(__file__).resolve().parent
PREFIX = 'native_acl_consumers_diagnosis_20261014'
DEST = OUT/(PREFIX+'.summary.json')
if DEST.exists():
    raise SystemExit('SUMMARY_ALREADY_EXISTS')
events = [json.loads(line) for line in (OUT/(PREFIX+'.events.jsonl')).read_text(encoding='utf-8').splitlines()]
rows = [row for row in events if row['kind']=='cli' and row['status']!='STARTED']
durations = sorted(row['duration_s'] for row in rows)
capture = json.loads((OUT/(PREFIX+'.consumers.json.terminal_capture.json')).read_bytes())
report = {'status':'OBSERVATION_SUMMARY_NOT_ACCEPTANCE',
          'diagnostic_report_sha256':hashlib.sha256((OUT/(PREFIX+'.json')).read_bytes()).hexdigest(),
          'commands':dict(Counter(row['basename'] for row in rows)),
          'cli_returncodes':dict(Counter(str(row.get('returncode')) for row in rows)),
          'cli_error_types':dict(Counter(row['error_type'] for row in rows if 'error_type' in row)),
          'duration_s':{'mean':statistics.mean(durations),'median':statistics.median(durations),
                        'maximum':max(durations),'total':sum(durations)},
          'stack_outer_functions':dict(Counter(row['stack_functions'][0] for row in rows)),
          'milestones':[row for row in events if row['kind']=='milestone'],
          'terminal_stages':{name:record['status'] for name,record in capture['actual_run_state']['stages'].items()},
          'actual_provider_receipt_count':len(capture['actual_run_state'].get('provider_requests',[])),
          'actual_synthetic_ledger_rows':len(capture['actual_synthetic_ledger']['requests']),
          'limitations':'The explicit 2000-CLI safety bound was reached before Plot. No real CLI timeout was reproduced; repeated load is measured but not proven the timeout cause.'}
DEST.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
