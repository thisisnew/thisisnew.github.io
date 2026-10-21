#!/usr/bin/env python3
"""Check referenced official URLs. HTTP success is not a content-accuracy audit."""
import concurrent.futures,datetime,hashlib,json,re,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import urlsplit,urldefrag
ROOT=Path(__file__).resolve().parents[1]
urls={}
for f in sorted((ROOT/'content/redis').glob('*.md')):
 for u in re.findall(r'https://[^\s)<>`\"]+',f.read_text()):
  u=urldefrag(u)[0].rstrip('.,;')
  if '/thisisnew/thisisnew.github.io/' in u: continue
  if urlsplit(u).hostname in ('redis.io','docs.spring.io','github.com','raw.githubusercontent.com','lettuce.io','javadoc.io'):
   urls.setdefault(u,[]).append(f.name)
def check(u):
 row={'url':u,'chapters':sorted(set(urls[u]))}
 try:
  req=urllib.request.Request(u,headers={'User-Agent':'RedisStudySourceLinkCheck/1.0'})
  with urllib.request.urlopen(req,timeout=30) as r:
   data=r.read(4_000_000); row.update(status=r.status,finalUrl=r.url,sha256=hashlib.sha256(data).hexdigest(),bytesRead=len(data))
 except urllib.error.HTTPError as e:row.update(status=e.code,error=str(e))
 except Exception as e:row.update(status=None,error=str(e))
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: rows=list(pool.map(check,sorted(urls)))
out={'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'HTTP reachability of official/source links referenced in Redis chapters; does not prove technical claims or fragment targets','results':rows,'notReachable':[x['url'] for x in rows if x.get('status')!=200]}
(ROOT/'learning/redis/source-checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'urls':len(rows),'notReachable':out['notReachable']},ensure_ascii=False,indent=2))
raise SystemExit(bool(out['notReachable']))
