#!/usr/bin/env python3
"""Isolated 6-process localhost cluster smoke test, not a durability proof."""
import argparse,json,hashlib,pathlib,subprocess,tempfile,time,socket,datetime,os
P=pathlib.Path;root=P(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--bin-dir',required=True);a=a.parse_args();bins=P(a.bin_dir)
procs=[];temp=tempfile.TemporaryDirectory(prefix='redis-cluster-study-');base=P(temp.name);checks=[]
def free(p):
 with socket.socket() as s:
  try:s.bind(('127.0.0.1',p));return True
  except OSError:return False
ports=next(([p+i for i in range(6)] for p in range(18000,19000,10) if all(free(p+i) and free(p+i+10000) for i in range(6))),None)
if not ports:raise SystemExit('No free six-port range')
def cli(p,*args,follow=False):
 cmd=[str(bins/'redis-cli'),'-h','127.0.0.1','-p',str(p),'--raw']+(['-c'] if follow else [])+list(map(str,args))
 r=subprocess.run(cmd,text=True,capture_output=True,timeout=12)
 if r.returncode:raise RuntimeError(r.stderr)
 return r.stdout.strip()
def until(fn,seconds=20):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  try:
   if fn():return
  except (RuntimeError,subprocess.SubprocessError):pass
  time.sleep(.1)
 raise AssertionError('Condition timed out')
report={'scope':'Six isolated Redis 7.2.5 processes on one localhost; routing, one two-key slot migration with ASK/TRYAGAIN/TTL observations, and coordinated manual failover only','not_tested':['network partitions','automatic or crash/unclean failover','cross-host durability','Sentinel','Spring client topology refresh','production load or large keys','all data types or expiry races','FORCE or TAKEOVER','node addition/removal or binary upgrades','throughput'], 'checks':checks}
try:
 for p in ports:
  d=base/str(p);d.mkdir();conf=d/'redis.conf';conf.write_text(f'bind 127.0.0.1\nprotected-mode yes\nport {p}\ncluster-enabled yes\ncluster-config-file nodes.conf\ncluster-node-timeout 2000\nappendonly no\nsave ""\ndir {d}\nlogfile {d}/redis.log\n')
  procs.append(subprocess.Popen([str(bins/'redis-server'),str(conf)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
 for p in ports:until(lambda p=p:cli(p,'PING')=='PONG')
 result=subprocess.run([str(bins/'redis-cli'),'--cluster','create',*[f'127.0.0.1:{p}' for p in ports],'--cluster-replicas','1','--cluster-yes'],text=True,capture_output=True,timeout=40)
 if result.returncode:raise RuntimeError(result.stdout+result.stderr)
 until(lambda:all('cluster_state:ok' in cli(p,'CLUSTER','INFO') for p in ports),30)
 # cluster_state:ok can precede propagation of the initial replica roles.
 # Wait for all six views to agree that three slot-owning primaries and
 # three replicas exist before selecting any process for a role-specific task.
 def initial_roles_ready(p):
  rows=[line.split() for line in cli(p,'CLUSTER','NODES').splitlines()]
  return len(rows)==6 and sum('master' in row[2] and any(r[0].isdigit() for r in row[8:])
                              for row in rows)==3 and sum('slave' in row[2] for row in rows)==3
 until(lambda:all(initial_roles_ready(p) for p in ports),30)
 checks.append('six_nodes_cluster_state_ok')
 slots=[cli(ports[0],'CLUSTER','KEYSLOT',k) for k in ['study:{cart42}:items','study:{cart42}:version']]
 assert slots[0]==slots[1];assert cli(ports[0],'MSET','study:{cart42}:items','a','study:{cart42}:version','1',follow=True)=='OK'
 checks.append('same_hash_tag_mset_succeeds')
 assert cli(ports[0],'MSET','study:a','1','study:b','2',follow=True).startswith('CROSSSLOT')
 checks.append('cross_slot_mset_rejected')
 replies=[cli(p,'GET','study:{cart42}:items') for p in ports]
 assert any(x.startswith('MOVED ') for x in replies)
 assert cli(ports[0],'GET','study:{cart42}:items',follow=True)=='a';checks.append('moved_and_cluster_aware_read')
 # Deliberately hold a migration midpoint in this disposable lab only.
 # Observe both one-key ASK and two-key TRYAGAIN instead of inferring them
 # from a final successful read. No user data or host networking is modified.
 def owner(node_lines,slot):
  return next(x.split() for x in node_lines if 'master' in x.split()[2]
   and any(int(r.split('-')[0])<=slot<=int(r.split('-')[-1])
           for r in x.split()[8:] if r[0].isdigit()))
 nodes=cli(ports[0],'CLUSTER','NODES').splitlines();slot=int(slots[0])
 source=owner(nodes,slot)
 target=next(x.split() for x in nodes if 'master' in x.split()[2]
             and x.split()[0]!=source[0] and any(r[0].isdigit() for r in x.split()[8:]))
 def port_of(node):return int(node[1].split('@')[0].rsplit(':',1)[1])
 sp,tp=port_of(source),port_of(target)
 key1,key2='study:{cart42}:items','study:{cart42}:version'
 assert cli(sp,'PEXPIRE',key1,120000)=='1'
 ttl_started=time.monotonic();ttl_before=int(cli(sp,'PTTL',key1))
 assert cli(tp,'CLUSTER','SETSLOT',slot,'IMPORTING',source[0])=='OK'
 assert cli(sp,'CLUSTER','SETSLOT',slot,'MIGRATING',target[0])=='OK'
 assert cli(sp,'MIGRATE','127.0.0.1',tp,key1,0,5000)=='OK'
 assert cli(sp,'GET',key1).startswith(f'ASK {slot} ')
 assert cli(sp,'GET',key2)=='1'
 assert cli(sp,'MGET',key1,key2).startswith('TRYAGAIN ')
 assert cli(tp,'GET',key1).startswith(f'MOVED {slot} ')
 # redis-cli consumes these lines on one TCP connection. ASKING only applies
 # to the immediately following command; a later GET is redirected again.
 asking=subprocess.run([str(bins/'redis-cli'),'-h','127.0.0.1','-p',str(tp),'--raw'],
   input=f'ASKING\nGET {key1}\nGET {key1}\n',text=True,capture_output=True,timeout=5)
 assert asking.returncode==0,asking.stderr
 lines=asking.stdout.strip().splitlines()
 assert lines[0:2]==['OK','a'] and lines[2].startswith(f'MOVED {slot} '),lines
 checks.append('migration_midpoint_ask_tryagain_and_one_connection_asking_scope_observed')
 assert cli(sp,'MIGRATE','127.0.0.1',tp,key2,0,5000)=='OK'
 assert cli(sp,'CLUSTER','COUNTKEYSINSLOT',slot)=='0'
 primaries=[x.split() for x in nodes if 'master' in x.split()[2]
            and any(r[0].isdigit() for r in x.split()[8:])]
 for node in sorted(primaries,key=lambda row:row[0]!=target[0]):
  reply=cli(port_of(node),'CLUSTER','SETSLOT',slot,'NODE',target[0])
  assert reply=='OK',f'finalize slot on {node[0]}: {reply}'
 until(lambda:all(owner(cli(p,'CLUSTER','NODES').splitlines(),slot)[0]==target[0]
                  and not any(f'[{slot}-' in line for line in cli(p,'CLUSTER','NODES').splitlines())
                  for p in ports),30)
 assert cli(sp,'GET',key1).startswith(f'MOVED {slot} ')
 assert cli(ports[0],'GET',key1,follow=True)=='a'
 assert cli(tp,'TYPE',key1)=='string' and cli(tp,'GET',key2)=='1'
 ttl_after=int(cli(tp,'PTTL',key1));elapsed_ms=int((time.monotonic()-ttl_started)*1000)
 assert ttl_after>0 and ttl_before-elapsed_ms-2000<=ttl_after<=ttl_before+2000
 checks.append('migrated_slot_views_converge_and_test_values_type_positive_ttl_preserved')
 nodes=cli(ports[0],'CLUSTER','NODES').splitlines();primary=next(x.split()[0] for x in nodes if 'master' in x.split()[2] and any(int(r.split('-')[0])<=int(slots[0])<=int(r.split('-')[-1]) for r in x.split()[8:] if r[0].isdigit()))
 until(lambda:any(x.split()[3]==primary and 'slave' in x.split()[2] for x in cli(ports[0],'CLUSTER','NODES').splitlines()),30)
 nodes=cli(ports[0],'CLUSTER','NODES').splitlines()
 replica=next(x.split() for x in nodes if x.split()[3]==primary and 'slave' in x.split()[2]);rp=int(replica[1].split('@')[0].rsplit(':',1)[1]);rid=replica[0]
 until(lambda:'master_link_status:up' in cli(rp,'INFO','replication'),30)
 assert cli(rp,'CLUSTER','FAILOVER')=='OK'
 until(lambda:any(x.split()[0]==rid and 'master' in x.split()[2] for x in cli(rp,'CLUSTER','NODES').splitlines()),30)
 until(lambda:cli(ports[0],'GET','study:{cart42}:items',follow=True)=='a',30);checks.append('coordinated_replica_failover_preserves_test_key_after_topology_convergence')
 report.update(status='passed',redisVersion=subprocess.check_output([str(bins/'redis-server'),'--version'],text=True).strip())
except Exception as e:
 report.update(status='failed',error=repr(e));raise
finally:
 for p in procs:
  if p.poll() is None:p.terminate()
 for p in procs:
  try:p.wait(timeout=8)
  except subprocess.TimeoutExpired:p.kill();p.wait()
 report['scriptSha256']=hashlib.sha256(P(__file__).read_bytes()).hexdigest();report['processesStopped']=all(p.poll() is not None for p in procs);temp.cleanup();report['temporaryDataRemoved']=not base.exists();report['checkedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 (root/'learning/redis/cluster-checks.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
