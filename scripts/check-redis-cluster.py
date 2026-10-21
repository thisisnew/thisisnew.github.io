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
report={'scope':'Six isolated Redis processes on one localhost; cluster routing and coordinated failover smoke test only','not_tested':['network partitions','crash/unclean failover','cross-host durability','Sentinel','Spring client topology refresh','throughput'], 'checks':checks}
try:
 for p in ports:
  d=base/str(p);d.mkdir();conf=d/'redis.conf';conf.write_text(f'bind 127.0.0.1\nprotected-mode yes\nport {p}\ncluster-enabled yes\ncluster-config-file nodes.conf\ncluster-node-timeout 2000\nappendonly no\nsave ""\ndir {d}\nlogfile {d}/redis.log\n')
  procs.append(subprocess.Popen([str(bins/'redis-server'),str(conf)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
 for p in ports:until(lambda p=p:cli(p,'PING')=='PONG')
 result=subprocess.run([str(bins/'redis-cli'),'--cluster','create',*[f'127.0.0.1:{p}' for p in ports],'--cluster-replicas','1','--cluster-yes'],text=True,capture_output=True,timeout=40)
 if result.returncode:raise RuntimeError(result.stdout+result.stderr)
 until(lambda:all('cluster_state:ok' in cli(p,'CLUSTER','INFO') for p in ports),30)
 checks.append('six_nodes_cluster_state_ok')
 slots=[cli(ports[0],'CLUSTER','KEYSLOT',k) for k in ['study:{cart42}:items','study:{cart42}:version']]
 assert slots[0]==slots[1];assert cli(ports[0],'MSET','study:{cart42}:items','a','study:{cart42}:version','1',follow=True)=='OK'
 checks.append('same_hash_tag_mset_succeeds')
 assert cli(ports[0],'MSET','study:a','1','study:b','2',follow=True).startswith('CROSSSLOT')
 checks.append('cross_slot_mset_rejected')
 replies=[cli(p,'GET','study:{cart42}:items') for p in ports]
 assert any(x.startswith('MOVED ') for x in replies)
 assert cli(ports[0],'GET','study:{cart42}:items',follow=True)=='a';checks.append('moved_and_cluster_aware_read')
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
