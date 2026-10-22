#!/usr/bin/env python3
"""Compile complete Redis teaching examples and run their main-method assertions.
This is not a Redis integration, durability, failover or performance test.
"""
import argparse, datetime, hashlib, json, re, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--java-home', required=True, type=Path)
parser.add_argument('--spring-classpath', required=True)
args = parser.parse_args()
bin_dir = args.java_home / 'bin'
source_dir = ROOT / 'examples/redis-foundations'
sources = sorted(source_dir.glob('*.java'))
lessons = list((ROOT / 'content/redis').glob('*.md'))
lesson_texts = {p.name: p.read_text() for p in lessons}
source_rows = []
for source in sources:
    code = source.read_text()
    owners = [name for name, text in lesson_texts.items() if code.strip() in text]
    if len(owners) != 1:
        raise RuntimeError(f'{source.name}: expected one verbatim source owner, got {owners}')
    source_rows.append({'file': source.name, 'lesson': owners[0],
                        'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
rows = []
with tempfile.TemporaryDirectory(prefix='redis-foundations-classes-') as directory:
    subprocess.run([str(bin_dir / 'javac'), '--release', '21', '-encoding', 'UTF-8',
                    '-cp', args.spring_classpath, '-d', directory,
                    *[str(source) for source in sources]], check=True)
    for source in sources:
        if not re.search(r'public\s+static\s+void\s+main\s*\(', source.read_text()):
            continue
        completed = subprocess.run([str(bin_dir / 'java'), '-Dfile.encoding=UTF-8',
                                    '-cp', directory, source.stem], check=True,
                                   capture_output=True, text=True, timeout=30)
        rows.append({'class': source.stem, 'status': 'passed',
                     'stdout': completed.stdout.strip()})
version = subprocess.run([str(bin_dir / 'java'), '-version'], capture_output=True,
                         text=True, check=True).stderr.strip()
report = {
    'checkedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'runtime': version, 'compiledClasses': len(sources), 'executedClasses': len(rows),
    'compilation': 'All complete classes compiled with --release 21; Spring examples against Spring Data Redis 3.2.0 and Spring Framework 6.1.1',
    'sources': source_rows, 'executed': rows,
    'limits': [
        'Independent teaching models and checksum example only; not Redis integration tests',
        'Spring GoodsNameCache, GoodsHashCache and SentinelClientConfiguration compiled only; no Spring integration runtime',
        'Sentinel teaching models are not full voting, membership, failure detection or TILT implementations; see separate sentinel-checks.json for local server integration',
        'Cluster budget, outcome, TTL, retry and maintenance models are independent policies, not Redis algorithms or Spring integration; see cluster-checks.json for the separate localhost protocol test',
        'GoodsLookupPolicy compiled only',
        'AOF models do not simulate real filesystem, fsync or Redis implementation',
        'Replication models cover one compatible history and planning arithmetic, not full PSYNC',
        'Existing redis-lab and the separate cluster-checks report describe only their explicitly recorded integration scopes',
    ],
}
(ROOT / 'learning/redis/expansion-code-checks.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'compiled': len(sources), 'executed': len(rows),
                  'status': 'passed', 'classes': [row['class'] for row in rows]},
                 ensure_ascii=False, indent=2))
