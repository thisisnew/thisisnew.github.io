#!/usr/bin/env python3
"""Compile Java 21 and test only a newly spawned, password-protected Redis."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ["get-set-utf8-ttl-incr", "pipeline-ordered-replies", "multi-exec-runtime-error-no-rollback", "lua-stock-guard-idempotent-token", "lua-runtime-error-no-rollback"]

def run(command, timeout=30):
    p = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"Command failed ({p.returncode}): {command[0]}\n{p.stdout}")
    return p.stdout.strip()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--redis-server', default=os.environ.get('REDIS_SERVER', 'redis-server'))
    parser.add_argument('--java', default=os.environ.get('JAVA', 'java'))
    args = parser.parse_args()
    report = {'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'failed',
              'scope': 'isolated standalone Redis; Java 21 dependency-free RESP2 teaching client',
              'not_tested': ['Spring Data Redis/Lettuce integration', 'Sentinel failover', 'Redis Cluster', 'replication durability', 'RDB/AOF recovery', 'TLS/ACL policy', 'load/performance', 'network partitions/concurrent oversell stress'],
              'source_sha256': hashlib.sha256((ROOT/'examples/redis-lab/RedisLab.java').read_bytes()).hexdigest()}
    proc = None
    try:
        java = shutil.which(args.java)
        redis = shutil.which(args.redis_server)
        if not java or not redis:
            raise RuntimeError('Need Java 21 with jdk.compiler and an explicitly supplied redis-server executable; nothing is installed automatically.')
        report['java_version'] = run([java, '-version'])
        report['compiler_version'] = run([java, '-m', 'jdk.compiler/com.sun.tools.javac.Main', '-version'])
        if not report['compiler_version'].startswith('javac 21.'):
            raise RuntimeError('This lab requires Java 21, not another major version')
        report['redis_version'] = run([redis, '--version'])
        with tempfile.TemporaryDirectory(prefix='redis-learning-') as temp:
            work = Path(temp)
            run([java, '-m', 'jdk.compiler/com.sun.tools.javac.Main', '-source', '21', '-target', '21', '-d', temp, str(ROOT/'examples/redis-lab/RedisLab.java')])
            report['compile'] = 'passed'
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            # A port race only causes failure: random AUTH prevents touching an unrelated Redis.
            password = secrets.token_hex(32)
            config = work/'redis.conf'
            config.write_text(f'bind 127.0.0.1\nport {port}\nprotected-mode yes\nrequirepass {password}\nsave ""\nappendonly no\ndaemonize no\ndir {temp}\nmaxmemory 32mb\nmaxmemory-policy noeviction\n')
            config.chmod(0o600)
            with (work/'redis.log').open('w+') as log:
                proc = subprocess.Popen([redis, str(config)], stdout=log, stderr=subprocess.STDOUT)
                deadline = time.monotonic() + 10
                while True:
                    if proc.poll() is not None:
                        log.seek(0)
                        raise RuntimeError('Disposable Redis exited: ' + log.read())
                    log.flush()
                    if 'Ready to accept connections' in (work/'redis.log').read_text():
                        break
                    if time.monotonic() > deadline:
                        raise RuntimeError('Disposable Redis startup timed out')
                    time.sleep(.05)
                try:
                    output = run([java, '-cp', temp, 'RedisLab', str(port), password], timeout=30)
                    report['stdout'] = output
                    observed = [line[5:] for line in output.splitlines() if line.startswith('PASS ')]
                    if observed != EXPECTED:
                        raise RuntimeError('Missing or unexpected checks: ' + repr(observed))
                    report['checks'] = [{'name': name, 'status': 'passed'} for name in observed]
                    report['status'] = 'passed'
                finally:
                    # Never send SHUTDOWN/FLUSHALL to a network endpoint. Terminate only our child PID.
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
                    report['own_server_stopped'] = proc.poll() is not None
        report['temporary_data_removed'] = not work.exists()
    except Exception as exc:
        report['error'] = str(exc)
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
    destination = ROOT/'learning/redis/lab-checks.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'passed' else 1

if __name__ == '__main__':
    raise SystemExit(main())
