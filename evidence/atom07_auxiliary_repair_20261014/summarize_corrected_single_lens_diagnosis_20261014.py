"""Summarize the corrected diagnostic without changing its originals."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
original = OUT/'summarize_native_acl_after_preflight_20261014.py'
source = original.read_text(encoding='utf-8')
old = "PREFIX = 'native_acl_consumers_after_preflight_20261014'"
new = "PREFIX = 'native_acl_consumers_single_lens_corrected_20261014'"
if source.count(old)!=1:
    raise SystemExit('SUMMARY_SOURCE_MISMATCH')
source = source.replace(old,new)
exec(compile(source,str(original),'exec'),{'__file__':str(Path(__file__))})
