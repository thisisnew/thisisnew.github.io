#!/usr/bin/env python3
"""Structural publication gates; not a claim of AWS integration testing."""
import json,re,sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.links=[];self.details=0;self.summary=0;self.text=[]
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if t in ('a','link') and a.get('href'):self.links.append(a['href'])
  if t in ('script','img') and a.get('src'):self.links.append(a['src'])
  self.details+=t=='details';self.summary+=t=='summary'
 def handle_data(self,s):self.text.append(s)
errors=[];rows=[];allpages={}
for p in [ROOT/'index.html',*ROOT.glob('posts/*.html'),*ROOT.glob('learning/**/*.html')]:
 q=Page();q.feed(p.read_text());allpages[p.resolve()]=q
manifest=json.loads((ROOT/'learning/aws/pdf-manifest.json').read_text())
assert len(manifest)==23
for n in range(23):
 p=ROOT/f'posts/aws-study-{n:02}.html';q=allpages.get(p.resolve());source=list(ROOT.glob(f'content/aws/{n:02}-*.md'))
 if not q or len(source)!=1:errors.append(f'missing source/page {n}');continue
 raw=source[0].read_text();s=p.read_text();meta=json.loads(raw.split('\n\n')[0])
 if meta['n']!=n:errors.append(f'wrong metadata {n}')
 if len(q.ids)!=len(set(q.ids)):errors.append(f'duplicate ids {n}')
 if q.details<4 or q.details!=q.summary:errors.append(f'Q&A {n}')
 if len(raw)<3500:errors.append(f'undersized chapter {n}')
 if '## ' in ''.join(q.text) or '```' in s or '<!-- AWS-INDEX -->' in s:errors.append(f'unrendered markdown {n}')
 if 'data-series="aws"' not in s or 'pixel-quest.css' not in s:errors.append(f'skin {n}')
 if '<h2' not in s or '공식 문서' not in s:errors.append(f'content structure {n}')
 for href in q.links:
  u=urlsplit(href)
  if u.scheme or href.startswith('//'):continue
  target=(ROOT/unquote(u.path).lstrip('/')) if u.path.startswith('/') else p.parent/unquote(u.path)
  if not u.path:target=p
  if target.is_dir():target=target/'index.html'
  target=target.resolve()
  if not target.exists():errors.append(f'{n} missing {href}')
  elif u.fragment and target in allpages and unquote(u.fragment) not in allpages[target].ids:errors.append(f'{n} anchor {href}')
 for code in re.findall(r'```json\n(.*?)```',raw,re.S):
  try:json.loads(code)
  except Exception as e:errors.append(f'{n} invalid JSON: {e}')
 rows.append({'n':n,'sourceCharacters':len(raw),'questions':q.details,'pdf':manifest[n]['file'],'pdfPages':manifest[n]['pages']})
home=(ROOT/'index.html').read_text()
if len(re.findall(r'class="post" data-category="aws"',home))!=23:errors.append('home AWS cards')
if 'data-filter="aws"' not in home:errors.append('AWS filter')
r={'scope':'23 authored AWS lessons, local links, anchors, source mapping, JSON snippet, skin and Q&A structure','errors':errors,'lessons':rows,'questions':sum(x['questions'] for x in rows),'sourceCharacters':sum(x['sourceCharacters'] for x in rows),'awsIntegrationTests':'not run; no AWS credentials or resources used'}
(ROOT/'learning/aws/site-checks.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='lessons'},ensure_ascii=False,indent=2));sys.exit(bool(errors))
