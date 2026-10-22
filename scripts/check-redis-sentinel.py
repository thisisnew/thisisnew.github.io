#!/usr/bin/env python3
"""Isolated local Sentinel integration: normal shutdown, discovery, rejoin and ACL.
Not a network partition, crash durability or Spring reconnect test.
"""
import argparse, datetime, hashlib, json, os, socket, subprocess, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--bin-dir', required=True, type=Path)
args = parser.parse_args()
processes = []
checks = []
temporary = tempfile.TemporaryDirectory(prefix='redis-sentinel-study-')
base = Path(temporary.name)

def free(port):
    with socket.socket() as connection:
        try:
            connection.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False

ports = next(([first + i for i in range(5)] for first in range(20100, 21000, 10)
              if all(free(first + i) for i in range(5))), None)
if not ports:
    raise SystemExit('No free isolated five-port range')
primary, replica, *sentinels = ports

def cli(port, *command, user=None, secret=None, allow_error=False):
    invocation = [str(args.bin_dir / 'redis-cli'), '-h', '127.0.0.1', '-p', str(port),
                  '--raw', '-e', '--no-auth-warning']
    environment = os.environ.copy()
    if user is not None:
        invocation.extend(['--user', user])
        environment['REDISCLI_AUTH'] = secret
    invocation.extend(map(str, command))
    completed = subprocess.run(invocation, env=environment, text=True,
                               capture_output=True, timeout=5)
    if completed.returncode and not allow_error:
        raise RuntimeError(completed.stdout.strip() + ' ' + completed.stderr.strip())
    return (completed.stdout + completed.stderr).strip()

def until(condition, seconds=25):
    deadline = time.monotonic() + seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            if condition():
                return
        except (RuntimeError, subprocess.SubprocessError, ValueError) as error:
            last_error = str(error)
        time.sleep(.1)
    raise AssertionError('Condition timed out: ' + str(last_error))

def start(config, sentinel=False):
    process = subprocess.Popen([str(args.bin_dir / 'redis-server'), str(config)]
                               + (['--sentinel'] if sentinel else []),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    processes.append(process)
    return process

def address(port):
    lines = cli(port, 'SENTINEL', 'GET-MASTER-ADDR-BY-NAME', 'logistics-main').splitlines()
    if len(lines) != 2:
        raise ValueError('Expected a two-part discovered address')
    return lines[0], int(lines[1])

def master_fields(port):
    lines = cli(port, 'SENTINEL', 'MASTER', 'logistics-main').splitlines()
    return dict(zip(lines[::2], lines[1::2]))

report = {
    'scope': 'Two data Redis processes and three Sentinel processes on one localhost; isolated test keys only',
    'not_tested': ['cross-host failure domains', 'network partitions', 'abrupt process or host crash',
                   'disk-loss durability', 'Spring or Lettuce reconnection', 'secret rotation',
                   'full production ACL policy', 'all failover candidate selection cases', 'performance'],
    'checks': checks,
}
try:
    configs = {}
    for port in [primary, replica]:
        directory = base / str(port)
        directory.mkdir()
        config = directory / 'redis.conf'
        config.write_text(f'bind 127.0.0.1\nprotected-mode yes\nport {port}\n'
                          f'daemonize no\ndir {directory}\nlogfile {directory}/redis.log\n'
                          'save ""\nappendonly yes\nappendfsync always\nmaxmemory 64mb\n'
                          'maxmemory-policy noeviction\nrepl-diskless-sync-delay 0\n'
                          + (f'replicaof 127.0.0.1 {primary}\n' if port == replica else ''))
        configs[port] = config
        start(config)
        until(lambda port=port: cli(port, 'PING') == 'PONG')
    until(lambda: 'master_link_status:up' in cli(replica, 'INFO', 'replication'))
    assert cli(primary, 'SET', 'study:sentinel:before', 'replicated') == 'OK'
    until(lambda: cli(replica, 'GET', 'study:sentinel:before') == 'replicated')
    checks.append('initial_primary_replica_link_and_test_key_replication')
    for port in sentinels:
        directory = base / str(port)
        directory.mkdir()
        config = directory / 'sentinel.conf'
        config.write_text(f'bind 127.0.0.1\nprotected-mode yes\nport {port}\n'
                          f'daemonize no\ndir {directory}\nlogfile {directory}/sentinel.log\n'
                          f'sentinel monitor logistics-main 127.0.0.1 {primary} 2\n'
                          'sentinel down-after-milliseconds logistics-main 500\n'
                          'sentinel failover-timeout logistics-main 3000\n'
                          'sentinel parallel-syncs logistics-main 1\n')
        start(config, sentinel=True)
        until(lambda port=port: cli(port, 'PING') == 'PONG')
    until(lambda: all(address(port) == ('127.0.0.1', primary) for port in sentinels))
    until(lambda: all(int(master_fields(port).get('num-other-sentinels', '0')) == 2
                      for port in sentinels))
    assert all(cli(port, 'SENTINEL', 'CKQUORUM', 'logistics-main').startswith('OK')
               for port in sentinels)
    checks.append('three_sentinels_discover_peers_and_agree_on_initial_primary')
    checks.append('ckquorum_succeeds_for_the_known_local_three_sentinel_group')
    cli(primary, 'SHUTDOWN')
    until(lambda: all(address(port) == ('127.0.0.1', replica) for port in sentinels), 30)
    until(lambda: cli(replica, 'ROLE').splitlines()[0] == 'master')
    assert cli(replica, 'GET', 'study:sentinel:before') == 'replicated'
    assert cli(replica, 'SET', 'study:sentinel:after', 'new-primary') == 'OK'
    checks.append('automatic_failover_after_normal_primary_shutdown_and_new_primary_write')
    start(configs[primary])
    until(lambda: cli(primary, 'ROLE').splitlines()[0] == 'slave', 30)
    until(lambda: 'master_link_status:up' in cli(primary, 'INFO', 'replication'), 30)
    until(lambda: cli(primary, 'GET', 'study:sentinel:after') == 'new-primary', 30)
    checks.append('former_primary_rejoins_as_replica_and_receives_new_test_write')
    secret = 'LocalSentinelDiscoveryOnly_73'
    assert cli(sentinels[0], 'ACL', 'SETUSER', 'study-discovery', 'reset', 'on',
               '>' + secret, '-@all', '+ping', '+sentinel|get-master-addr-by-name') == 'OK'
    found = cli(sentinels[0], 'SENTINEL', 'GET-MASTER-ADDR-BY-NAME', 'logistics-main',
                user='study-discovery', secret=secret).splitlines()
    assert found == ['127.0.0.1', str(replica)]
    denied = cli(sentinels[0], 'SENTINEL', 'FAILOVER', 'logistics-main',
                 user='study-discovery', secret=secret, allow_error=True)
    assert 'NOPERM' in denied
    checks.append('sentinel_discovery_acl_allows_address_lookup_and_denies_manual_failover')
    report.update(status='passed', redisVersion=subprocess.check_output(
        [str(args.bin_dir / 'redis-server'), '--version'], text=True).strip())
except Exception as error:
    report.update(status='failed', error=repr(error))
    raise
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    report['processesStopped'] = all(process.poll() is not None for process in processes)
    temporary.cleanup()
    report['temporaryDataRemoved'] = not base.exists()
    report['scriptSha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['checkedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (ROOT / 'learning/redis/sentinel-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
