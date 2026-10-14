"""Static source comparison for Controller review, never execution acceptance."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(r'D:\CangqiStudio\StoryStudio')
DEST = Path(__file__).resolve().parent / 'method_source_scope_20261014.json'
if DEST.exists():
    raise SystemExit('EVIDENCE_ALREADY_EXISTS')
ACCEPTED = '84e022de0fee6eb7d7eec4c248703621129491e1'
RETURNED = 'f8c72d59b070a3544047189de0fb31f3b138e6df'
NAMES = ['cnw_roles', 'cnw_review', 'cnw_lint', 'cnw_contract', 'cnw_export',
         'cnw_revision', 'cnw_import_workflow', 'cnw_runner', 'cnw_recovery',
         'cnw_request_identity', 'cnw_project', 'cnw_pack_app', 'cnw_critics_adapter']
TREE_PATHS = {commit: set(subprocess.check_output(['git', 'ls-tree', '-r',
             '--name-only', commit], cwd=ROOT).decode().splitlines())
              for commit in (ACCEPTED, RETURNED)}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def definition_index(b):
    tree = ast.parse(b.decode('utf-8-sig'))
    return {n.name: sha(ast.dump(n, include_attributes=False).encode())
            for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}

records = []
for name in NAMES:
    path = 'tools/' + name + '.py'
    current = (ROOT / path).read_bytes()
    row = {'path': path, 'current_sha256': sha(current), 'comparisons': {}}
    current_index = definition_index(current)
    for label, commit in [('frozen06', ACCEPTED), ('returned07', RETURNED)]:
        if path not in TREE_PATHS[commit]:
            row['comparisons'][label] = {'commit': commit, 'baseline_module': 'ABSENT_IN_EXACT_TREE',
                'identical_universal_newline_text': False, 'changed_definitions': [],
                'added_definitions': sorted(current_index)}
            continue
        old = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)
        old_index = definition_index(old)
        row['comparisons'][label] = {
            'commit': commit, 'source_sha256': sha(old),
            'identical_git_bytes': current == old,
            'identical_universal_newline_text': current.replace(b'\r\n', b'\n') == old.replace(b'\r\n', b'\n'),
            'unchanged_definitions': sorted(k for k in current_index if k in old_index and current_index[k] == old_index[k]),
            'changed_definitions': sorted(k for k in current_index if k in old_index and current_index[k] != old_index[k]),
            'added_definitions': sorted(current_index.keys() - old_index.keys()),
            'removed_definitions': sorted(old_index.keys() - current_index.keys()),
        }
    records.append(row)
report = {'status': 'STATIC_DEFINITION_COMPARISON_NOT_METHOD_ACCEPTANCE',
          'records': records, 'tests_run': 0, 'production_calls': 0,
          'limits': 'Definition hashes exclude line positions. Equality supports evidence scope, not runtime correctness. All changed or added functions remain subject to actual consumer evidence and independent verdict.'}
DEST.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'destination': str(DEST), 'sha256': sha(DEST.read_bytes()),
                  'returned07_changed_definitions': {r['path']: r['comparisons']['returned07']['changed_definitions'] for r in records},
                  'frozen06_identical_modules': [r['path'] for r in records if r['comparisons']['frozen06']['identical_universal_newline_text']]}))
