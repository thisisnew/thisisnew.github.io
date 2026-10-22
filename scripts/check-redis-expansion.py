#!/usr/bin/env python3
"""Check per-lesson expansion against the immutable pre-expansion baseline.
--require-all exits nonzero while any lesson is still below twice its baseline.
Length is a scope gate, never a claim about readability or factual correctness.
"""
import argparse, datetime, hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
args = argparse.ArgumentParser()
args.add_argument('--require-all', action='store_true')
options = args.parse_args()
baseline = json.loads((ROOT / 'learning/redis/expansion-baseline.json').read_text())
rows = []
for original in baseline['lessons']:
    row = dict(original)
    raw = (ROOT / 'content/redis' / row['file']).read_text()
    row['currentCharacters'] = len(raw.split('\n\n', 1)[1])
    row['currentSha256'] = hashlib.sha256(raw.encode()).hexdigest()
    row['ratio'] = round(row['currentCharacters'] / row['baselineCharacters'], 3)
    row['expanded'] = row['currentCharacters'] >= row['minimumCharacters']
    rows.append(row)
result = {
    'checkedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'baselineCommit': baseline['baseCommit'],
    'measurement': baseline['measurement'],
    'goal': 'Each of the 31 lessons individually at least twice its baseline body length; length alone does not prove teaching quality',
    'complete': all(row['expanded'] for row in rows),
    'expandedCount': sum(row['expanded'] for row in rows),
    'totalCount': len(rows),
    'lessons': rows,
}
(ROOT / 'learning/redis/expansion-progress.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'lessons'}, ensure_ascii=False, indent=2))
if options.require_all and not result['complete']:
    raise SystemExit(1)
