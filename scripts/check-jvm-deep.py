#!/usr/bin/env python3
"""Verify published Deep01..16 outputs and selected bytecode contracts."""
import json, os, re, shutil, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def tool(name):
    return str(Path(os.environ['JAVA_HOME']) / 'bin' / name) if os.environ.get('JAVA_HOME') else name
def run(args, cwd, ok=True, timeout=30):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    if ok and result.returncode:
        raise AssertionError((args, result.stdout, result.stderr))
    return result
version = run([tool('java'), '-version'], ROOT).stderr
release = '21'
expected = {
 1:['GIMPO'], 2:['main entered','type found','printer initialized','label=42','label=43'],
 4:['finally=20','result=10','element=20'], 5:['-1794967296','2500000000','overflow detected'],
 6:['inbound'], 7:['label:42'], 8:['same=true','definedByParent=true','requesterIsDefiner=false'],
 9:['loading config','ExceptionInInitializerError','NoClassDefFoundError'],
 10:['original size=1','quantity=20','fixed quantity=30'], 11:['request-A','null'],
 12:['retained slots=8','last=31'], 13:['slots=512','last=119'],
 14:['5050','5950'], 15:['broken=-1','first=true','second=false','fixed=0']}
bytecode = {4:('Deep04',['Exception table:','ireturn','areturn']),
 5:('Deep05',['imul','i2l','lmul']),6:('Deep06',['checkcast','invokeinterface']),
 7:('Deep07$Labels',['ACC_BRIDGE','ACC_SYNTHETIC','(Ljava/lang/Object;)Ljava/lang/Object;'])}
rows=[]
with tempfile.TemporaryDirectory(prefix='jvm-deep-') as tmp:
    for n in range(1,17):
        work=Path(tmp)/str(n);work.mkdir()
        name=f'Deep{n:02}'
        shutil.copy(ROOT/f'examples/jvm/{n:02}/{name}.java',work)
        run([tool('javac'),'--release',release,'-g',name+'.java'],work)
        if n==16:
            for mode in ['cpu','lock','memory']:
                proc=subprocess.Popen([tool('java'),'-Xms64m','-Xmx64m','-XX:NativeMemoryTracking=summary',name,mode],cwd=work,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                try:
                    pidline=proc.stdout.readline().strip()
                    assert pidline.startswith('pid='),pidline
                    assert proc.stdout.readline().strip()=='mode='+mode
                    pid=pidline.split('=')[1]
                    # Attach evidence from the actual running demonstration.
                    dump=run([tool('jcmd'),pid,'Thread.print','-l'],work).stdout
                    if mode=='lock':
                        assert 'lock-waiter' in dump and 'BLOCKED (on object monitor)' in dump
                    if mode=='cpu':assert 'Deep16.main' in dump
                    if mode=='memory':assert 'Deep16.main' in dump
                    nmt=run([tool('jcmd'),pid,'VM.native_memory','summary'],work).stdout
                    assert 'Native Memory Tracking:' in nmt
                    out,err=proc.communicate(timeout=25)
                    assert proc.returncode==0 and out.strip().endswith('done'),(mode,out,err)
                    rows.append({'lesson':16,'mode':mode,'status':'passed','attach':True})
                finally:
                    if proc.poll() is None:proc.kill();proc.wait()
            continue
        out=run([tool('java'),'-Xms64m','-Xmx64m',name],work).stdout.strip().splitlines()
        if n==3:
            values=dict(line.split('=') for line in out)
            assert int(values['capacity'])>=4*1024*1024 and int(values['used'])>0
            assert values['value']=='42'
        else:assert out==expected[n],(n,out,expected[n])
        if n==1:
            result=run([tool('javac'),'--release','17',name+'.java'],work,ok=False)
            assert result.returncode!=0 and 'getFirst' in result.stderr
        if n in bytecode:
            target,needles=bytecode[n]
            output=run([tool('javap'),'-c','-v','-p',target],work).stdout
            assert all(x in output for x in needles),(n,needles)
        if n==12:
            large=run([tool('java'),'-Xms64m','-Xmx64m',name,'1024'],work).stdout.strip().splitlines()
            assert large==['retained slots=1024','last=31']
        if n==15:
            # The latch makes the bad interleaving deterministic, not probabilistic.
            for _ in range(2):assert run([tool('java'),name],work).stdout.strip().splitlines()==expected[n]
        rows.append({'lesson':n,'status':'passed','output':out})
report={'jdk':version,'release':release,'results':rows}
(ROOT/'learning/jvm-deep-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'release':release,'checks':len(rows),'status':'passed'}))
