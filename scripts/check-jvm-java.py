#!/usr/bin/env python3
"""Run the exact published examples under JDK 21, and validate semantic outputs."""
import os, subprocess, tempfile, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bin=Path(os.environ['JAVA_HOME'])/'bin' if 'JAVA_HOME' in os.environ else None
def tool(x):return str(bin/x) if bin else x
def run(args,cwd,timeout=25):
    r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=timeout)
    if r.returncode:raise RuntimeError(f'{args}: {r.stdout}\n{r.stderr}')
    return r.stdout
version=run([tool('java'),'-version'],ROOT) # version is printed on stderr, record below
vm=subprocess.run([tool('java'),'-version'],capture_output=True,text=True,check=True).stderr
expected={2:['init','main','42'],3:['42','true'],4:['42'],5:['42','0','4'],6:['7','empty'],7:['inbound:42','true'],9:['7','loaded without init request','Config init','0','42','8'],10:['42','true','42'],12:['retained slots=128','done'],13:['retained=8','last=-17'],14:['5050','5150'],15:['20000']}
results=[]
walkthroughs={4:['42'],5:['7','36','26'],7:['3'],10:['42','0','false']}
walkthrough_results=[]
with tempfile.TemporaryDirectory(prefix='jvm-study-') as temp:
    for n in range(1,17):
        src=ROOT/f'examples/jvm/{n:02}';work=Path(temp)/str(n);work.mkdir()
        for f in src.glob('*.java'):shutil.copy(f,work/f.name)
        run([tool('javac'),'--release','21','-g',*[x.name for x in work.glob('*.java')]],work)
        name=f'Lesson{n:02}';args=[tool('java'),'-Xms32m','-Xmx64m',name]
        if n==13:args=[tool('java'),'-Xms32m','-Xmx32m','-XX:+UseG1GC','-XX:G1HeapRegionSize=1m',name]
        out=run(args,work).strip().splitlines()
        if n in expected:assert out==expected[n],(n,out,expected[n])
        if n==1:assert out[-1]=='sum=42'
        if n==8:assert out[-3:]==['same name=true','same type=false','assignable=false']
        if n==11:assert out[0]=='cache entries=1' and out[-1]=='cache entries=0'
        if n==16:assert out[0].startswith('pid=') and out[-1]=='done'
        javap=run([tool('javap'),'-v','-c','-p',name],work)
        assert 'major version: 65' in javap
        if n==5:assert all(x in javap for x in ['iload_0','iload_1','iadd','istore_2','ireturn'])
        if n==6:assert all(x in javap for x in ['newarray','iastore','iaload','Exception table:'])
        if n==15:
            virtual=run([tool('java'),'VirtualThreads'],work).strip();assert virtual=='completed=100'
            counter=run([tool('javap'),'-c','-v','-p','Lesson15$Counter'],work)
            assert all(x in counter for x in ['ACC_SYNCHRONIZED','monitorenter','monitorexit'])
        if n in walkthroughs:
            extra=f'Walkthrough{n:02}'
            actual=run([tool('java'),extra],work).strip().splitlines()
            assert actual==walkthroughs[n],(extra,actual)
            bytecode=run([tool('javap'),'-v','-c','-p',extra],work)
            if n==4:
                assert all(x in bytecode for x in ['descriptor: (J)J','locals=5','ladd','lreturn'])
            if n==5:
                assert all(x in bytecode for x in ['isub','imul'])
            if n==7:
                assert all(x in bytecode for x in ['descriptor: (Ljava/lang/String;[I)J','i2l'])
            walkthrough_results.append({'example':extra,'output':actual,'passed':True})
        results.append({'lesson':n,'compiled_release':21,'output':out,'passed':True})
report={'jdk':vm,'examples':21,'lessons':16,'results':results,'walkthroughs':walkthrough_results}
(ROOT/'learning/jvm-java-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'lessons':16,'examples':21,'status':'passed'}))
