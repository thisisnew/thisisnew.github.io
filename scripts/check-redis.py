#!/usr/bin/env python3
"""Redis structural gates only: not an execution or factual-correctness claim."""
import json,re,sys,html,datetime
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
for n in range(31):
 p=ROOT/f'posts/redis-study-{n:02}.html';q=allpages.get(p.resolve());source=list(ROOT.glob(f'content/redis/{n:02}-*.md'))
 if not q or len(source)!=1:errors.append(f'missing source/page {n}');continue
 raw=source[0].read_text();s=p.read_text();meta=json.loads(raw.split('\n\n')[0])
 if meta['n']!=n:errors.append(f'wrong metadata {n}')
 if len(q.ids)!=len(set(q.ids)):errors.append(f'duplicate ids {n}')
 if q.details<(3 if n==0 else 8) or q.details!=q.summary:errors.append(f'Q&A count {n}: {q.details}')
 if len(raw)<(3000 if n==0 else 6000):errors.append(f'undersized chapter {n}: {len(raw)}')
 if '```' in s or '<!-- REDIS-INDEX -->' in s:errors.append(f'unrendered markdown {n}')
 if 'data-series="redis"' not in s or 'pixel-quest.css' not in s:errors.append(f'skin {n}')
 if '<h2' not in s or '공식' not in s:errors.append(f'content structure {n}')
 if not any(urlsplit(u).hostname in ('redis.io','docs.spring.io','github.com') for u in q.links):errors.append(f'no primary source link {n}')
 for href in q.links:
  u=urlsplit(href)
  if u.scheme or href.startswith('//'):continue
  target=(ROOT/unquote(u.path).lstrip('/')) if u.path.startswith('/') else p.parent/unquote(u.path)
  if not u.path:target=p
  if target.is_dir():target=target/'index.html'
  target=target.resolve()
  if not target.exists():errors.append(f'{n} missing {href}')
  elif u.fragment and target in allpages and unquote(u.fragment) not in allpages[target].ids:errors.append(f'{n} anchor {href}')
 rows.append({'n':n,'sourceCharacters':len(raw),'questions':q.details,'sections':len(q.ids)})
home=(ROOT/'index.html').read_text()
if len(re.findall(r'class="post" data-category="redis"',home))!=31:errors.append('home Redis cards')
if 'data-filter="redis"' not in home:errors.append('Redis filter')
result={'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'31 Redis pages: metadata, internal links, anchors, minimum content structure, Q&A and pixel skin; length thresholds are only omission guards, not quality scores','errors':errors,'lessons':rows,'questions':sum(x['questions'] for x in rows),'sourceCharacters':sum(x['sourceCharacters'] for x in rows),'runtimeValidation':'not assessed by this structural checker; consult separate runtime records','browserValidation':'not assessed by this structural checker; consult browser-checks.json if present','externalLinks':'presence only; not HTTP or semantic verification'}
(ROOT/'learning/redis').mkdir(parents=True,exist_ok=True)
(ROOT/'learning/redis/site-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
status='통과' if not errors else '실패'
body=f'<h1>Redis 학습 연재 검증 범위</h1><p>구조 검사: {status}. 검사 시각: {html.escape(result["checkedAt"])}.</p><p>검사 대상: 31편 원고·페이지, 내부 링크·앵커, 메타데이터, 문답 구조와 기존 픽셀 스킨. 글자 수 하한은 누락 탐지일 뿐 깊이나 정확성의 증명이 아닙니다.</p><p><a href="/learning/redis/site-checks.json">상세 구조 검사 결과</a> · <a href="/learning/redis/lesson-audit.json">편별 원고 해시와 출처 링크 목록</a></p><h2>이 검사로 증명하지 않는 것</h2><ul><li>외부 링크의 HTTP 정상 응답이나 문서 내용의 정확한 해석</li><li>Java/Spring 코드의 컴파일·실제 Redis 서버 실행·장애 복구·동시성·성능</li><li>브라우저의 실제 화면·모바일·키보드 동작</li><li>GitHub Pages에 실제 배포되었는지 여부</li></ul><p>별도 실행 결과가 아래 제공되면 해당 기록의 명시된 범위만 확인된 것입니다. 기록이 없는 항목은 미검증입니다.</p>'
for filename,label in [('browser-checks.json','브라우저 실행 기록'),('lab-checks.json','단일 Redis·Java 실행 기록'),('cluster-checks.json','로컬 6노드 Cluster 검사 기록'),('input-manifest.json','제공 자료 범위·해시 기록'),('source-checks.json','공식 출처 확인 기록')]:
 if (ROOT/'learning/redis'/filename).exists():body+=f'<p><a href="/learning/redis/{filename}">{label}</a></p>'
if errors:body+='<h2>남은 오류</h2><ul>'+''.join('<li>'+html.escape(e)+'</li>' for e in errors)+'</ul>'
body+='<p><a href="/posts/redis-study-00.html">Redis 학습 지도</a></p>'
(ROOT/'learning/redis/verification.html').write_text('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Redis 검증 범위 | thisisnew</title><link rel="stylesheet" href="/assets/pixel-quest.css"><link rel="stylesheet" href="/assets/jvm-study.css"><link rel="stylesheet" href="/assets/redis-study.css"></head><body data-series="redis"><main>'+body+'</main></body></html>')
print(json.dumps({k:v for k,v in result.items() if k!='lessons'},ensure_ascii=False,indent=2));sys.exit(bool(errors))
