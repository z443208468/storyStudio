"""Read-only audit of the three-file Plot subset and expiry observations."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
PREFIX = 'consolidated_preflight_expiry_consumers'
capture = OUT/(PREFIX+'.consumers.json')
dest = OUT/(PREFIX+'.subset_audit.json')
if dest.exists():
    raise SystemExit('AUDIT_ALREADY_EXISTS')
value = json.loads(capture.read_bytes())
files = value['actual_files']
rows = [{'path':name,'sha256':item['sha256'],
    'byte_hash_matches':hashlib.sha256(item['utf8'].encode('utf-8')).hexdigest()==item['sha256']}
    for name,item in files.items()]
state = value['actual_run_state']
artifact = state['stages']['plot']['artifact']
receipt = state['provider_requests'][0]
ledger = value['actual_synthetic_ledger']['requests']
expiry = {}
for kind in ('chapter','operation'):
    path = Path(str(capture)+'.'+kind+'_verification_expiry.json')
    data = json.loads(path.read_bytes())
    expiry[kind] = {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'two_entries_with_terminal_expiry':len(data['observations'])==2 and all(
            len(item['clock'])==2 and item['clock'][0]<item['clock'][1] for item in data['observations']),
        'actual_transport_calls':len(data['actual_transport_calls'])}
report = {'status':'SUBSET_BYTE_AUDIT_NOT_ACCEPTANCE',
    'source_sha256':hashlib.sha256(capture.read_bytes()).hexdigest(),
    'simulation_status':value['simulation_status'], 'mode':value['mode'],
    'files':rows, 'plot_matches':files[artifact['path']]['sha256']==artifact['sha256'],
    'request_matches':files[receipt['request_path']]['sha256']==receipt['request_sha256'],
    'raw_response_matches':files[receipt['raw_response_path']]['sha256']==receipt['raw_response_sha256'],
    'ledger_rows':len(ledger),'ledger_statuses':[row['status'] for row in ledger],
    'expiry_observations':expiry,
    'limitations':'The generic whole-Run capture audit raised KeyError because this pre-existing Plot capture contains exactly artifact/request/raw response, not the contract. No whole-Run or contract-byte audit is claimed. Production assertions and raw test log remain unchanged.'}
dest.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
if (any(not row['byte_hash_matches'] for row in rows) or not all(report[key] for key in
        ('plot_matches','request_matches','raw_response_matches')) or any(
        not row['two_entries_with_terminal_expiry'] or row['actual_transport_calls'] for row in expiry.values())):
    raise SystemExit(1)
