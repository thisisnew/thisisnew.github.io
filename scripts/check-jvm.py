#!/usr/bin/env python3
"""Validate JVM content and exact links. Only Python standard library is required."""
import json, re, sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=[]; self.links=[]; self.questions=0; self.summaries=0; self.text=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag in ('a','link') and a.get('href'):self.links.append(a['href'])
        if tag in ('script','img') and a.get('src'):self.links.append(a['src'])
        if tag=='details':self.questions+=1
        if tag=='summary':self.summaries+=1
    def handle_data(self,s): self.text.append(s)
pages={};errors=[];rows=[];sources=set()
for f in [ROOT/'index.html',*sorted((ROOT/'posts').glob('jvm-study-*.html'))]:
    p=Page();p.feed(f.read_text());pages[f.resolve()]=p
for f,p in pages.items():
    if len(p.ids)!=len(set(p.ids)):errors.append(f'{f.name}: duplicate ids')
    for href in p.links:
        u=urlsplit(href)
        if u.scheme in ('http','https'):
            if 'jvm-study-' in f.name and ('oracle.com' in u.netloc or 'openjdk' in u.netloc):sources.add(href)
            continue
        if u.scheme:continue
        dest=(ROOT/u.path.lstrip('/')) if u.path.startswith('/') else f.parent/u.path
        if not u.path:dest=f
        if dest.is_dir():dest=dest/'index.html'
        dest=dest.resolve()
        if not dest.exists():errors.append(f'{f.name}: missing {href}')
        if u.fragment and dest in pages and unquote(u.fragment) not in pages[dest].ids:errors.append(f'{f.name}: missing anchor {href}')
    if f.name.startswith('jvm-study-'):
        n=int(f.stem[-2:]);text=''.join(p.text)
        if n and (p.questions<6 or p.questions!=p.summaries):errors.append(f'{f.name}: incomplete Q&A')
        if n and len(text)<3500:errors.append(f'{f.name}: insufficient body')
        if '/assets/pixel-quest.css' not in p.links:errors.append(f'{f.name}: missing existing skin')
        rows.append({'lesson':n,'text_chars':len(text),'questions':p.questions})
if len(rows)!=17:errors.append('expected 00 + 16 lessons')
report={'pages':len(rows),'questions':sum(x['questions'] for x in rows),'errors':errors,'lessons':rows,'sources':sorted(sources)}
(ROOT/'learning/jvm-site-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['pages','questions','errors']},ensure_ascii=False))
sys.exit(bool(errors))
