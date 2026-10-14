"""Correct an unsupported summary canary observation; preserve the original."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
original = OUT/'index_final_native_chain_consumers_20261014.py'
target = OUT/'index_final_native_chain_consumers_v2_20261014.py'
if target.exists(): raise SystemExit('CONSUMER_INDEX_V2_ALREADY_PREPARED')
raw = original.read_bytes()
source = raw.decode('utf-8')
changes = {
    "DEST = OUT/(LABEL+'.consumer_index.json')":"DEST = OUT/(LABEL+'.consumer_index_v2.json')",
    "'prose_direct_canon_canary_absent':'CANON_SECRET_NEIGHBORS_NOT_SIBLINGS' not in prose_wire,":"'actual_prose_user_payload_keys':[sorted(json.loads(row['messages'][1]['content'])) for row in requests if row['stage']=='prose'],\n    'actual_prose_direct_keys_legal':all(set(json.loads(row['messages'][1]['content']))=={'writing_brief','voice_samples'} for row in requests if row['stage']=='prose'),\n    'original_summary_correction':'The original index checked a CANON_SECRET string that this fixture never supplied. That observation is invalid and is not used as canary evidence. This version reports actual Prose payload keys; frozen independent canary tests retain their own scope.',",
    "'selected_b_in_plot','unselected_a_absent','prose_direct_canon_canary_absent',":"'selected_b_in_plot','unselected_a_absent','actual_prose_direct_keys_legal',"}
for old,new in changes.items():
    if source.count(old)!=1: raise SystemExit('CONSUMER_INDEX_V2_TRANSFORM_MISMATCH')
    source = source.replace(old,new)
compile(source,str(target),'exec')
target.write_text(source,encoding='utf-8')
print(json.dumps({'original_summary_script_sha256':hashlib.sha256(raw).hexdigest(),
    'corrected_script_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
    'production_or_test_changes':0,'original_preserved':True}))
