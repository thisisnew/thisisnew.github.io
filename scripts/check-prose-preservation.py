#!/usr/bin/env python3
"""Compare editorial changes with a Git revision without executing examples.

This checks structural and technical content preservation. It cannot prove that
two prose passages make exactly the same claims; that still needs editorial review.
"""
import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = '1921d310e3f8be8fe15c6d7250c7742f28358a9a'


class TechnicalContent(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.tags = []
        self.code = []
        self.depth = 0
        self.data = []
        self.questions = 0

    def handle_starttag(self, tag, attrs):
        if tag != 'p':
            self.tags.append(('start', tag, attrs))
        elif attrs:
            self.tags.append(('paragraph-attributes', attrs))
        self.questions += tag == 'details'
        if tag in ('pre', 'code', 'script', 'style'):
            self.depth += 1

    def handle_startendtag(self, tag, attrs):
        self.tags.append(('void', tag, attrs))

    def handle_endtag(self, tag):
        if tag != 'p':
            self.tags.append(('end', tag))
        if tag in ('pre', 'code', 'script', 'style'):
            self.depth -= 1

    def handle_data(self, data):
        self.data.append(data)
        if self.depth:
            self.code.append(('text', data))

    def handle_entityref(self, name):
        if self.depth:
            self.code.append(('entity', name))

    def handle_charref(self, name):
        if self.depth:
            self.code.append(('char', name))


def original(path, base):
    return subprocess.check_output(
        ['git', 'show', f'{base}:{path.relative_to(ROOT).as_posix()}'],
        cwd=ROOT,
    ).decode('utf-8')


def numbers(text):
    return Counter(re.findall(r'\d+(?:[.,]\d+)*', text))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default=DEFAULT_BASE)
    args = parser.parse_args()
    errors = []
    rows = []
    paths = sorted(ROOT.glob('posts/*.html'))
    for path in paths:
        before = original(path, args.base)
        after = path.read_text()
        a, b = TechnicalContent(), TechnicalContent()
        a.feed(before)
        b.feed(after)
        checks = {
            'structureAttributesLinksAndTables': a.tags == b.tags,
            'codeScriptsAndStyles': a.code == b.code,
            'numericValues': numbers(before) == numbers(after),
            'questionCount': a.questions == b.questions,
            'quotedPhrases': all(
                not (Counter(re.findall(pattern, ''.join(a.data))) -
                     Counter(re.findall(pattern, ''.join(b.data))))
                for pattern in (r'“[^”]*”', r'‘[^’]*’')
            ),
            'nonempty': len(''.join(b.data).strip()) > 100,
        }
        for label, passed in checks.items():
            if not passed:
                errors.append(f'{path.name}: {label}')
        rows.append({
            'file': path.relative_to(ROOT).as_posix(),
            'changed': before != after,
            'questions': b.questions,
            'checks': checks,
        })
    source_count = 0
    for path in sorted(ROOT.glob('content/**/*.md')):
        before, after = original(path, args.base), path.read_text()
        comparisons = {
            'metadata': (before.split('\n\n', 1)[0], after.split('\n\n', 1)[0]),
            'inlineCode': (re.findall(r'`[^`\n]+`', before), re.findall(r'`[^`\n]+`', after)),
            'markdownLinkTargets': (
                re.findall(r'\]\(([^)]*)\)', before),
                re.findall(r'\]\(([^)]*)\)', after),
            ),
            'tables': (
                re.findall(r'^\|.*$', before, re.M), re.findall(r'^\|.*$', after, re.M),
            ),
            'numericValues': (numbers(before), numbers(after)),
        }
        # Capture complete fenced blocks, including the actual code, rather than
        # just the delimiter capture used for locating a matching closing fence.
        fence = r'^(`{3,}|~{3,})[^\n]*\n[\s\S]*?^\1[ \t]*$'
        comparisons['fencedCode'] = (
            [m.group(0) for m in re.finditer(fence, before, re.M)],
            [m.group(0) for m in re.finditer(fence, after, re.M)],
        )
        for label, (a, b) in comparisons.items():
            if a != b:
                errors.append(f'{path.relative_to(ROOT)}: {label}')
        source_count += 1
    report = {
        'baseCommit': args.base,
        'posts': len(rows),
        'changedPosts': sum(row['changed'] for row in rows),
        'markdownSources': source_count,
        'questions': sum(row['questions'] for row in rows),
        'errors': errors,
        'scope': 'Exact technical and structural preservation; paragraph breaks may change.',
        'limitation': 'Automatic checks do not prove semantic equivalence of prose.',
        'lessons': rows,
    }
    (ROOT / 'learning/prose-preservation-checks.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    )
    print(json.dumps({k: v for k, v in report.items() if k != 'lessons'}, ensure_ascii=False, indent=2))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
