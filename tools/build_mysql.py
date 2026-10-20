#!/usr/bin/env python3
"""Build independent MySQL lessons; preserves the existing shared pixel skin."""
from pathlib import Path
import html,json,re
ROOT=Path(__file__).resolve().parents[1]
TITLES=[
'처음부터 이해하는 MySQL: 서버·연결·SQL의 여행',
'계정과 권한: 접속 성공과 조회 허용은 다르다',
'페이지와 버퍼 풀: 메모리·디스크·캐시의 실제 역할',
'저장 완료의 비밀: redo·undo·커밋·장애 복구',
'트랜잭션과 MVCC: 같은 데이터를 다르게 보는 이유',
'잠금과 데드락: 행·빈 공간·대기 관계를 직접 확인하기',
'B-tree와 InnoDB 인덱스: 기본 키가 저장 구조를 바꾼다',
'복합 인덱스 설계: 조건·정렬·커버링을 함께 생각하기',
'옵티마이저: 통계·조인 순서·힌트가 계획을 만드는 과정',
'실행 계획 해독: EXPLAIN ANALYZE로 느린 이유 찾기',
'데이터 압축: 공간 절감과 CPU·쓰기 비용의 교환',
'암호화와 복구: 데이터·로그·키를 끝까지 보호하기']
CSS='''body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.95}main{max-width:960px;margin:auto;padding:36px 24px 100px}h1{font-size:clamp(30px,5vw,48px);line-height:1.4}h2{margin-top:64px;line-height:1.5}p,li{font-size:17px}a{color:inherit}pre{padding:18px;line-height:1.65;overflow:auto}table{border-collapse:collapse;width:100%}td,th{padding:12px;border:1px solid #a69c80;vertical-align:top}details{border:2px solid #a69c80;margin:16px 0;padding:16px}summary{font-weight:700;cursor:pointer}details p{margin-bottom:0}.meta{font-size:13px}.lesson-nav{display:flex;flex-wrap:wrap;gap:18px;margin-top:50px}.callout{border:2px solid #a69c80;padding:18px;margin:24px 0}.series-grid{display:grid;gap:18px}.series-card{border:2px solid #a69c80;padding:20px}.series-card h2{margin:0;font-size:22px}'''
def shell(title,body):
 return '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+' | thisisnew</title><meta name="description" content="'+html.escape(title)+' — 비유·내부 원리·SQL 실습·장애 분석·면접 답변으로 배우는 MySQL 8.0"><style>'+CSS+'</style><link rel="stylesheet" href="/assets/pixel-quest.css"><script src="/assets/series-category.js" defer></script><link rel="stylesheet" href="/assets/study-reading.css"></head><body><main><a href="/">thisisnew / Engineering Notes</a>'+body+'</main><script src="/assets/study-tools.js"></script></body></html>'
rows=[];cards=[]
for n,title in enumerate(TITLES,1):
 body=(ROOT/f'tools/mysql-source/{n:02}.html').read_text()
 ids=iter(range(100))
 body=re.sub(r'<h2>',lambda m:f'<h2 id="section-{next(ids)}">',body)
 nav=f'<a href="/learning/mysql/">전체 12편 학습 지도</a>'
 if n>1:nav+=f'<a href="/posts/mysql-study-{n-1:02}.html">← 이전 편</a>'
 if n<12:nav+=f'<a href="/posts/mysql-study-{n+1:02}.html">다음 편 →</a>'
 intro=f'<p class="meta">MYSQL DEEP STUDY · {n:02} / 12 · 2026-10-20</p><h1>{html.escape(title)}</h1><div class="callout"><strong>읽는 방법</strong><p>비유로 개념을 잡고 SQL을 실행하기 전 결과를 예상해 보세요. 이번 개정에서는 단계별 동작 추적에 더해, 전편에 네 가지 확장 수업과 심층 면접 답변을 추가했습니다. 본문의 수치 예시는 설명용이고, 실행 환경에 따라 달라지는 값은 따로 표시했습니다. 기준은 MySQL 8.0·InnoDB, 재현용 서버는 8.0.36입니다. 처음 시작한다면 <a href="/posts/mysql-study-01.html">1편의 서버 준비</a>만 먼저 진행하면 됩니다.</p><p><a href="/learning/mysql/">전체 학습 지도·검증 범위</a></p></div>'
 (ROOT/f'posts/mysql-study-{n:02}.html').write_text(shell(title,intro+body+'<nav class="lesson-nav" aria-label="연재 이동">'+nav+'</nav>'))
 cards.append(f'<article class="series-card"><h2><a href="/posts/mysql-study-{n:02}.html">{n:02}. {html.escape(title)}</a></h2><p>개념과 비유 · 내부 원리 · 독립 SQL 실습 · 결과 해석 · 상세 면접 Q&amp;A 12개</p></article>')
 rows.append({'lesson':n,'title':title,'body_chars':len(re.sub('<[^>]+>','',body)),'questions':body.count('<details>'),'sources':re.findall(r'href="(https://dev.mysql.com/[^"]+)"',body)})
status='<h2>검증 범위와 재현 조건</h2><p>모든 글은 독립적으로 작성한 설명과 예제를 사용합니다. 시판 교재의 번역·전재·장별 재구성물이 아닙니다. 아래 공식 문서 링크를 각 주제의 근거로 제공합니다. 8.4·9.x 또는 MySQL 호환 제품에 동일한 동작을 자동 적용하지 마세요.</p><p>SQL 실습은 격리된 mysql_school 스키마를 사용합니다. DROP TABLE은 해당 학습 테이블만 초기화합니다. 운영 DB에서 실행하지 마세요. 실습 서버는 1편을 따라 한 번 준비하며, 여러 세션 실습은 실행 순서를 지켜야 합니다.</p><p>자동 검증은 HTML 구조·내부 링크·Q&amp;A·대표 SQL 결과·버전 충돌·커서 동률·JOIN/EXISTS 결과 차이·RR/RC·잠금·데드락·정상 재시작·논리 백업 복원을 대상으로 구성했습니다. <strong>실제 전원 차단 내구성, 운영 부하 성능, 저장장치별 페이지 압축 절감률, keyring 설치·키 회전·암호화 복원은 자동 검증 범위에 포함하지 않습니다.</strong> 해당 절에는 필요한 전제를 표시했습니다.</p><p><a href="https://github.com/thisisnew/thisisnew.github.io/actions">GitHub Actions에서 해당 커밋의 실행 결과 확인</a> · <a href="/learning/mysql-audit.json">전편 구조·출처 목록</a> · <a href="/learning/mysql-source-link-checks.json">공식 문서 링크 확인 기록</a></p>'
(ROOT/'learning/mysql/index.html').write_text(shell('MySQL을 쉽고 깊게 이해하는 12편', '<p class="meta">MYSQL LEARNING MAP</p><h1>MySQL을 쉽고 깊게<br>이해하는 12편</h1><p>용어 암기보다 원인과 결과를 연결합니다. 서버에 요청이 들어와 페이지를 읽고, 잠금을 잡고, 변경을 확정하고, 장애에서 복구하는 과정까지 따라갑니다.</p><p>처음에는 1→3→4→5→6편으로 데이터가 움직이는 원리를 잡고, 7→8→9→10편으로 성능을 이해하세요. 계정·권한은 2편, 저장 정책과 복구는 11→12편입니다. 각 편은 필요한 배경을 다시 설명합니다.</p><div class="series-grid">'+''.join(cards)+'</div>'+status))
(ROOT/'learning/mysql-audit.json').write_text(json.dumps({'date':'2026-10-20','baseline':'MySQL 8.0.36','lessons':rows},ensure_ascii=False,indent=2))
# Only add dedicated entries; never replace biography or other series.
p=ROOT/'index.html';s=p.read_text()
start='<!-- MYSQL-SERIES-START -->';end='<!-- MYSQL-SERIES-END -->'
# Replace in place so other series retain their existing order.
links=[f'<a class="post" data-category="mysql" data-order="{n}" href="posts/mysql-study-{n:02}.html"><div class="number">M{n:02}</div><div><div class="tags">BACKEND · MYSQL DEEP STUDY · {n:02}/12</div><h3>{html.escape(t)}</h3><p>쉬운 비유부터 내부 원리·SQL 실습·상세 면접 답변까지</p><div class="date">2026.10.20 개정 · MySQL 8.0 심화 학습</div></div><div class="arrow">↗</div></a>' for n,t in enumerate(TITLES,1)]
assert '<div id="articles">' in s
if start in s:
 s=s[:s.index(start)]+start+''.join(links)+end+s[s.index(end)+len(end):]
else:
 s=s.replace('<div id="articles">','<div id="articles">'+start+''.join(links)+end,1)
p.write_text(s)
print(json.dumps({'lessons':len(rows),'body_chars':sum(x['body_chars'] for x in rows),'questions':sum(x['questions'] for x in rows)},ensure_ascii=False))
