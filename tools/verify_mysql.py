#!/usr/bin/env python3
"""Static verification plus optional real MySQL 8.0.36 integration checks.
Run: python tools/verify_mysql.py [--database]
Only isolated mysql_school lab tables are modified.
"""
import concurrent.futures,html,json,os,re,subprocess,sys,time
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
 def __init__(self):
  super().__init__();self.links=[];self.ids=[];self.details=0;self.summary=0;self.blocks=[];self.in_pre=False;self.current='';self.text=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if tag in ('a','link') and a.get('href'):self.links.append(a['href'])
  if tag=='script' and a.get('src'):self.links.append(a['src'])
  if tag=='details':self.details+=1
  if tag=='summary':self.summary+=1
  if tag=='pre':self.in_pre=True;self.current=''
 def handle_endtag(self,tag):
  if tag=='pre':self.blocks.append(self.current);self.in_pre=False
 def handle_data(self,data):
  self.text.append(data)
  if self.in_pre:self.current+=data

def parse(path):
 p=Page();p.feed(path.read_text());return p

def static():
 errors=[];rows=[]
 paths=list(ROOT.glob('posts/mysql-study-*.html'))+[ROOT/'learning/mysql/index.html']
 pages={p.resolve():parse(p) for p in paths}
 for p,x in pages.items():
  if len(x.ids)!=len(set(x.ids)):errors.append(f'{p.name}: duplicate ids')
  if p.name.startswith('mysql-study'):
   if x.details!=6 or x.summary!=6:errors.append(f'{p.name}: Q&A count')
   if len(''.join(x.text))<4000:errors.append(f'{p.name}: incomplete text')
   if not any('/assets/pixel-quest.css'==u for u in x.links):errors.append(f'{p.name}: skin')
  for link in x.links:
   u=urlsplit(link)
   if u.scheme or link.startswith('//'):continue
   t=(ROOT/unquote(u.path).lstrip('/')) if u.path.startswith('/') else p.parent/unquote(u.path)
   if not u.path:t=p
   if t.is_dir():t=t/'index.html'
   if not t.exists():errors.append(f'{p.name}: missing {link}')
   elif u.fragment and t.resolve() in pages and unquote(u.fragment) not in pages[t.resolve()].ids:errors.append(f'{p.name}: anchor {link}')
  rows.append({'file':str(p.relative_to(ROOT)),'questions':x.details,'text_chars':len(''.join(x.text))})
 assert len(paths)==13, len(paths)
 report={'static':'passed' if not errors else 'failed','errors':errors,'pages':rows}
 (ROOT/'learning/mysql-static-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 assert not errors,errors
 print('Static: 12 lessons + learning map; links, anchors, 72 answers passed',flush=True)

def database():
 import pymysql
 password=os.environ.get('MYSQL_LAB_PASSWORD','LocalStudyOnly_83')
 def conn(user='root',pw=password):return pymysql.connect(host='127.0.0.1',port=int(os.environ.get('MYSQL_LAB_PORT','3307')),user=user,password=pw,autocommit=True,charset='utf8mb4',read_timeout=15,write_timeout=15)
 c=conn(); results=[]
 def sql(s,db=c):
  with db.cursor() as cur:cur.execute(s);return cur.fetchall()
 def runblock(block):
  # Examples contain no stored routines or semicolons inside values except the compression payload.
  # Small SQL splitter honors quoted strings, escaped characters and line comments.
  buf='';quote=None;esc=False;comment=False;i=0
  while i<len(block):
   ch=block[i]
   if comment:
    if ch=='\n':comment=False;buf+='\n'
    i+=1;continue
   if quote:
    buf+=ch
    if esc:esc=False
    elif ch=='\\':esc=True
    elif ch==quote:quote=None
   elif ch in "'\"`":quote=ch;buf+=ch
   elif block[i:i+2]=='--' and (i+2==len(block) or block[i+2].isspace()):comment=True;i+=1
   elif ch==';':
    if buf.strip():sql(buf.strip())
    buf=''
   else:buf+=ch
   i+=1
  if buf.strip():sql(buf.strip())
 def blocks(n):return parse(ROOT/f'tools/mysql-source/{n:02}.html').blocks
 version=sql('SELECT VERSION()')[0][0];assert version.startswith('8.0.36'),version
 # Execute the actual published SQL blocks rather than a rewritten approximation.
 selections={1:[1,2],2:[1],3:[0],4:[0,1],5:[0],6:[0],7:[0],8:[0,1,2,3],9:[0,1,2],10:[0,1],11:[0,1],12:[0,2]}
 for n,indices in selections.items():
  for i in indices:runblock(blocks(n)[i])
  results.append(f'article-{n:02}-sql-blocks')
 assert sql('SELECT qty FROM stock WHERE sku=101')==((10,),)
 assert sql('SELECT SUM(LENGTH(payload)) FROM buffer_demo')==((180000,),)
 assert sql('SELECT qty FROM durability_demo')==((8,),)
 assert sql("SELECT COUNT(*) FROM join_order_demo WHERE warehouse_id=1 AND status='WAITING'")==((4,),)
 for t in ['compress_plain','compress_zip','compress_page']:
  assert sql(f'SELECT COUNT(*),SUM(LENGTH(payload)) FROM {t}')==((1000,720000),)
 # Role behavior: localhost account via server TCP may match localhost or IP; use Docker socket client.
 def docker_mysql(statement,user='root',pw=password):
  return subprocess.run(['docker','exec','-e',f'MYSQL_PWD={pw}','mysql-school','mysql','-N','-B',f'-u{user}','-e',statement],capture_output=True,text=True)
 r=docker_mysql('SELECT note FROM mysql_school.account_demo','school_reader','LocalReaderOnly_83');assert r.returncode==0,r.stderr
 r=docker_mysql("UPDATE mysql_school.account_demo SET note='x' WHERE id=1",'school_reader','LocalReaderOnly_83');assert r.returncode!=0 and '1142' in r.stderr,r.stderr
 r=docker_mysql('SET ROLE NONE; SELECT * FROM mysql_school.account_demo','school_reader','LocalReaderOnly_83');assert r.returncode!=0,r.stdout
 results.append('roles-select-allowed-update-denied-role-none-denied')
 a=conn();b=conn()
 for d in (a,b):sql('USE mysql_school',d)
 for isolation,expected in [('REPEATABLE READ',10),('READ COMMITTED',20)]:
  sql('UPDATE mvcc_demo SET qty=10 WHERE id=1')
  sql('SET SESSION TRANSACTION ISOLATION LEVEL '+isolation,a);sql('START TRANSACTION',a)
  assert sql('SELECT qty FROM mvcc_demo WHERE id=1',a)==((10,),)
  sql('UPDATE mvcc_demo SET qty=20 WHERE id=1',b)
  assert sql('SELECT qty FROM mvcc_demo WHERE id=1',a)==((expected,),)
  assert sql('SELECT qty FROM mvcc_demo WHERE id=1 FOR UPDATE',a)==((20,),)
  sql('ROLLBACK',a)
 results.append('RR-RC-snapshot-and-locking-read')
 # Atomic stock guard: 20 requests compete for ten units.
 sql('UPDATE mvcc_demo SET qty=10 WHERE id=1')
 def decrement(_):
  d=conn()
  try:
   sql('USE mysql_school',d)
   with d.cursor() as q:q.execute('UPDATE mvcc_demo SET qty=qty-1 WHERE id=1 AND qty>=1');return q.rowcount
  finally:d.close()
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:assert sum(pool.map(decrement,range(20)))==10
 assert sql('SELECT qty FROM mvcc_demo WHERE id=1')==((0,),)
 results.append('20-concurrent-decrements-only-10-success')
 def wait_for_lock():
  deadline=time.monotonic()+5
  while time.monotonic()<deadline:
   if sql('SELECT COUNT(*) FROM performance_schema.data_lock_waits')[0][0]>0:return
   time.sleep(.05)
  raise AssertionError('Expected a visible lock wait')
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  sql('SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ',a)
  sql('START TRANSACTION',a);sql('SELECT * FROM lock_demo WHERE id=20 FOR UPDATE',a)
  f=pool.submit(sql,'UPDATE lock_demo SET qty=qty-1 WHERE id=20',b)
  wait_for_lock();assert not f.done();sql('ROLLBACK',a);f.result()
  results.append('record-lock-wait-release')
  sql('START TRANSACTION',a);sql('SELECT * FROM lock_demo WHERE id BETWEEN 10 AND 20 FOR UPDATE',a)
  f=pool.submit(sql,'INSERT INTO lock_demo VALUES(15,15)',b)
  wait_for_lock();assert not f.done();sql('ROLLBACK',a);f.result();sql('DELETE FROM lock_demo WHERE id=15')
  results.append('range-lock-blocks-gap-insert')
  sql('START TRANSACTION',a);sql('START TRANSACTION',b)
  sql('UPDATE lock_demo SET qty=qty+1 WHERE id=10',a);sql('UPDATE lock_demo SET qty=qty+1 WHERE id=20',b)
  f=pool.submit(sql,'UPDATE lock_demo SET qty=qty+1 WHERE id=20',a);wait_for_lock();errors=[]
  try:sql('UPDATE lock_demo SET qty=qty+1 WHERE id=10',b)
  except pymysql.MySQLError as e:errors.append(e.args[0])
  try:f.result(timeout=10)
  except pymysql.MySQLError as e:errors.append(e.args[0])
  assert errors==[1213],errors
  sql('ROLLBACK',a);sql('ROLLBACK',b)
  results.append('deadlock-cycle-one-victim-1213')
 # Logical backup and restore of the article's non-encrypted fixture.
 dump=subprocess.run(['docker','exec','-e',f'MYSQL_PWD={password}','mysql-school','mysqldump','-uroot','--single-transaction','--no-tablespaces','--set-gtid-purged=OFF','mysql_school','backup_demo'],capture_output=True,text=True,check=True).stdout
 subprocess.run(['docker','exec','-i','-e',f'MYSQL_PWD={password}','mysql-school','mysql','-uroot','mysql_school_restore'],input=dump,text=True,check=True,capture_output=True)
 assert sql('SELECT * FROM mysql_school_restore.backup_demo')==((1,'restore-test'),)
 results.append('logical-backup-restore')
 for d in (a,b,c):d.close()
 subprocess.run(['docker','restart','mysql-school'],check=True,capture_output=True)
 deadline=time.monotonic()+60
 while True:
  try:c=conn();break
  except pymysql.MySQLError:
   if time.monotonic()>deadline:raise
   time.sleep(.5)
 assert sql('SELECT qty FROM mysql_school.durability_demo',c)==((8,),)
 c.close();results.append('normal-restart-committed-data-preserved')
 report={'mysql_version':version,'passed':results,'not_tested':['power-loss durability','production performance','keyring installation / key rotation / encrypted restore','filesystem-specific page-compression savings']}
 (ROOT/'learning/mysql-runtime-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':
 static()
 if '--database' in sys.argv:database()
