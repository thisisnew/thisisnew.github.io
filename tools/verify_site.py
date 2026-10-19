#!/usr/bin/env python3
"""Validate the static site, including exact local anchors; standard library only."""
import json,re,sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.ids=[];self.links=[];self.text=[];self.details=0;self.summary=0;self.code=0;self.stack=[];self.errors=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id'in a:self.ids.append(a['id'])
  if tag in ['a','link'] and a.get('href'):self.links.append(a['href'])
  if tag in ['script','img'] and a.get('src'):self.links.append(a['src'])
  if tag=='details':self.details+=1
  if tag=='summary':self.summary+=1
  if tag=='code':self.code+=1
 def handle_data(self,s):self.text.append(s)
def verify():
 pages={};errors=[];externals=set();rows=[]
 for p in ROOT.rglob('*.html'):
  if '.git' in p.parts:continue
  parser=Page();parser.feed(p.read_text());pages[p]=parser
  if len(parser.ids)!=len(set(parser.ids)):errors.append(f'{p.relative_to(ROOT)} duplicate IDs')
 for p,x in pages.items():
  for href in x.links:
   u=urlsplit(href)
   if u.scheme in ['http','https']:externals.add(href);continue
   if u.scheme or href.startswith('//'):continue
   target=(ROOT/unquote(u.path).lstrip('/')) if u.path.startswith('/') else p.parent/unquote(u.path)
   if not u.path:target=p
   if target.is_dir():target=target/'index.html'
   target=target.resolve()
   if not target.exists():errors.append(f'{p.relative_to(ROOT)} missing {href}');continue
   if u.fragment and target in pages and unquote(u.fragment) not in pages[target].ids:errors.append(f'{p.relative_to(ROOT)} missing anchor {href}')
 for n in range(1,36):
  p=ROOT/f'posts/kafka-study-{n:02}.html'
  if p not in pages:errors.append(f'missing lesson {n}');continue
  x=pages[p];s=p.read_text()
  for marker in ['revision-map','revision-internals','revision-lab','revision-code','revision-foundations','revision-interview','revision-sources','pixel-quest.css']:
   if marker not in s:errors.append(f'{n} missing {marker}')
  if x.details<15 or x.details!=x.summary:errors.append(f'{n} incomplete details/summary')
  if 'https://kafka.apache.org/43/' not in s:errors.append(f'{n} missing versioned source')
  rows.append({'lesson':n,'bytes':len(s.encode()),'text_chars':len(''.join(x.text)),'questions':x.details,'code_blocks':x.code})
 result={'lessons':len(rows),'pages':len(pages),'errors':errors,'lessons_detail':rows,'external_urls':sorted(externals)}
 (ROOT/'learning/site-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in result.items() if k not in ['lessons_detail','external_urls']},ensure_ascii=False,indent=2));return not errors
if __name__=='__main__':sys.exit(0 if verify() else 1)
