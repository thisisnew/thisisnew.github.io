#!/usr/bin/env python3
"""Validate the published GC logging and jcmd/JFR/NMT commands on isolated local JVMs."""
import os, subprocess, tempfile, shutil, json, time, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bin=Path(os.environ['JAVA_HOME'])/'bin' if 'JAVA_HOME' in os.environ else None
def tool(x):return str(bin/x) if bin else x
results=[]
def run(args,cwd,timeout=30):
    r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=timeout)
    assert r.returncode==0,(args,r.stdout,r.stderr)
    return r.stdout+r.stderr
with tempfile.TemporaryDirectory(prefix='jvm-diagnostic-') as temp:
    work=Path(temp)
    for n in [11,12,13,16]:
        f=ROOT/f'examples/jvm/{n:02}/Lesson{n:02}.java';shutil.copy(f,work/f.name)
    run([tool('javac'),'--release','21',*[x.name for x in work.glob('*.java')]],work)
    for n in [11,12,13]:
        args=[tool('java'),'-Xms32m','-Xmx32m','-XX:+UseG1GC']
        if n==13:args+=['-XX:G1HeapRegionSize=1m']
        selector='gc*,safepoint' if n==11 else 'gc*,gc+age=trace' if n==12 else 'gc*,gc+humongous=debug'
        args+=[f'-Xlog:{selector}:file=gc{n}.log:time,uptime,level,tags',f'Lesson{n:02}']
        run(args,work);log=(work/f'gc{n}.log').read_text();assert 'Using G1' in log
        if n==13:assert 'Humongous' in log
        results.append({'check':f'GC log lesson {n}','passed':True,'bytes':len(log)})
    if '--startup-only' in sys.argv:
        run([tool('java'),'-XX:NativeMemoryTracking=summary','-XX:StartFlightRecording=settings=profile,filename=startup.jfr,dumponexit=true','Lesson16','2'],work)
        assert 'jdk.' in run([tool('jfr'),'summary','startup.jfr'],work)
        report={'checks':len(results)+1,'mode':'startup-only; attach checks run in CI','results':results+[{'check':'Startup JFR recording and binary reader','passed':True}]}
        (ROOT/'learning/jvm-local-diagnostics-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'checks':report['checks'],'mode':report['mode'],'status':'passed'}))
        sys.exit(0)
    p=subprocess.Popen([tool('java'),'-Xms32m','-Xmx64m','-XX:NativeMemoryTracking=summary','-XX:+StartAttachListener','-Xlog:gc*,safepoint:file=gc16.log:time,uptime,level,tags','Lesson16','120'],cwd=work,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        first=p.stdout.readline().strip();assert first==f'pid={p.pid}',first
        pid=str(p.pid)
        for command in [['VM.version'],['VM.command_line'],['VM.flags'],['help'],['GC.heap_info'],['Thread.print','-l'],['VM.native_memory','summary','scale=MB'],['VM.native_memory','baseline'],['VM.native_memory','summary.diff','scale=MB'],['Compiler.codecache']]:
            out=run([tool('jcmd'),pid,*command],work);assert not any(x in out for x in ['Unknown diagnostic command','Native memory tracking is not enabled'])
            results.append({'check':' '.join(command),'passed':True})
        out=run([tool('jcmd'),pid,'JFR.start','name=investigate','settings=profile','duration=2s','filename=investigate.jfr'],work);assert 'Started recording' in out,out
        run([tool('jcmd'),pid,'JFR.check'],work)
        deadline=time.monotonic()+15
        summary=None
        while time.monotonic()<deadline:
            f=work/'investigate.jfr'
            if f.exists() and f.stat().st_size>0:
                candidate=subprocess.run([tool('jfr'),'summary','investigate.jfr'],cwd=work,capture_output=True,text=True,timeout=10)
                if candidate.returncode==0:
                    summary=candidate.stdout;break
            time.sleep(.2)
        assert summary and 'jdk.' in summary
        run([tool('jfr'),'print','--events','jdk.ExecutionSample','investigate.jfr'],work)
        results.append({'check':'JFR start/check/file summary and execution event printing','passed':True})
        run([tool('jcmd'),pid,'GC.class_histogram'],work)
        run([tool('jcmd'),pid,'GC.heap_dump',str(work/'local.hprof')],work)
        assert (work/'local.hprof').read_bytes().startswith(b'JAVA PROFILE')
        results.append({'check':'histogram and HPROF dump','passed':True})
    finally:
        p.terminate();p.communicate(timeout=10)
report={'checks':len(results),'results':results}
(ROOT/'learning/jvm-diagnostics-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'checks':len(results),'status':'passed'}))
