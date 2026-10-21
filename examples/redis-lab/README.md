# Redis Java 21 실습 — 독립 프로세스에서 검증

운영 Redis에 연결하지 않습니다. 실행기는 임의 포트·임의 비밀번호·임시 데이터
디렉터리를 사용하는 **새로운 로컬 Redis 프로세스**만 생성합니다. RDB/AOF를 끄고
자신이 시작한 PID만 종료합니다. `FLUSHALL`, 기존 인스턴스 종료, 소프트웨어 자동
설치가 없습니다. Java 코드는 UUID 접두사 키만 사용합니다.

검증에 사용한 Redis 7.2.5는 동작 재현용 고정 버전이며 최신 버전이나 운영 배포 권장 버전이 아닙니다. 운영에는 지원 상태와 보안 패치를 따로 검토하세요.

## 실행

Java 21 (`jdk.compiler` 모듈 포함)과 직접 준비한 `redis-server`가 필요합니다.
외부 Java 의존성·Maven은 필요 없습니다. 저장소 `blog` 디렉터리에서:

```bash
python3 scripts/check-redis-lab.py --redis-server /absolute/path/to/redis-server
```

검사기는 컴파일 → 격리 서버 시작 → 실제 TCP/RESP2 요청 → 명시적 assertion →
서버 종료 → 임시 파일 제거를 수행합니다. 실패하면 0이 아닌 종료 코드를 반환하고
`learning/redis/lab-checks.json`에 오류를 기록합니다. 기존 결과 파일을 덮어씁니다.
컴파일은 실행 중인 Java 21의 `-source 21 -target 21`을 사용합니다. 이 환경의
축소 JDK에는 `javac` 실행 파일과 `ct.sym`이 없어 `--release 21` 대신 compiler
모듈을 직접 실행했습니다. Java 21이 아닌 컴파일러는 거부합니다.

## 실제 assertion

1. UTF-8 SET/GET, TTL -1/-2, PX 만료, 없는 숫자 키의 INCR.
2. 요청을 먼저 보내는 pipeline과 순서대로 읽는 응답. **성능 benchmark나
   다른 클라이언트와의 비원자성 재현 실험은 아닙니다.**
3. MULTI/EXEC 안에서 INCR 실행 오류가 나더라도 앞선 SET은 남고 다음 SET도 실행됨.
4. Lua 재고 검사: 정상 차감, 동일 업무 토큰 재시도, 토큰의 다른 수량 재사용 거부,
   재고 부족·음수 수량 거부. 이 테스트는 순차 요청이며 동시성 부하 실험은 아닙니다.
5. Lua도 쓰기 후 실행 오류가 나면 앞선 쓰기를 자동 롤백하지 않음.

## Lua 예제의 경계

`KEYS[1]`은 재고, `KEYS[2]`는 주문 토큰입니다. **네트워크 재시도마다 새 토큰을
만들면 안 됩니다.** 같은 업무 요청은 같은 토큰과 동일 수량으로 재전송해야 합니다.
다른 상품에는 별도 키 공간을 사용해야 합니다. 재고와 토큰을 MSET 한 번으로 쓰고
토큰에 60초 TTL을 붙입니다. 토큰이 만료·evict·삭제되거나 장애로 유실되면 재시도가
다시 차감될 수 있습니다. 업무상 허용 재시도 기간 및 영속 주문 원장을 별도로
설계해야 하며 이 예제는 결제/DB와의 exactly-once 보장이 아닙니다.

수량·재고는 학습용 1,000,000 상한의 정수입니다. 실제 서비스에는 직렬화·금액 및
큰 정수 정밀도·타입 정책·메모리 부족·재시도 정책 검증이 더 필요합니다. MSET 이후
EXPIRE 오류는 자동 롤백되지 않습니다. 여기서는 사전 입력 검사와 단순 쓰기만으로
범위를 제한했습니다. TTL은 업무 완료 증거의 영구 보존 수단이 아닙니다.

키에 같은 hash tag를 썼지만 **Cluster를 실행하거나 검증한 것은 아닙니다.**

## 운영 코드와 다릅니다

`Resp`는 RESP2 문자열/정수/배열/오류만 지원하는 작은 동기 클라이언트입니다.
연결 2초·읽기 3초 timeout, 응답 크기 상한을 둡니다. ACL 사용자명, TLS, 커넥션 풀,
RESP3, reconnect, topology discovery, 재시도/timeout의 불확실한 실행 결과 처리를
구현하지 않습니다. Spring Data Redis/Lettuce 대체품이 아닙니다. 프로덕션에서는
공식 클라이언트 문서와 버전별 동작을 검토하세요.

## 재현에 사용한 서버

검증 서버: Redis **7.2.5**. 최신/보안 권장 버전이라는 뜻이 아니라 재현 기준입니다.
공식 릴리스 `https://download.redis.io/releases/redis-7.2.5.tar.gz`를 임시 디렉터리에
받아 `make -j2 MALLOC=libc BUILD_TLS=no OPT='-O2' redis-server`로 빌드했습니다.
다운로드 파일의 실제 SHA-256:

```
5981179706f8391f03be91d951acafaeda91af7fac56beffb2701963103e423d
```

이는 받은 파일의 측정값이며 독립 서명 검증을 수행했다는 주장은 아닙니다.
실제 실행 버전·stdout·검사 범위·미검증 항목은 JSON 결과가 기준입니다.
Sentinel, Cluster, 복제 내구성, RDB/AOF 복구, Spring 통합, TLS/ACL 정책, 네트워크
분할, 부하 성능은 이 실습의 검증 범위가 아닙니다.

공식 참고:
- [트랜잭션과 오류 처리](https://redis.io/docs/latest/develop/using-commands/transactions/)
- [Lua 실행 및 원자성](https://redis.io/docs/latest/develop/programmability/eval-intro/)
- [Pipeline](https://redis.io/docs/latest/develop/using-commands/pipelining/)

## 추가 Cluster smoke test

`python3 scripts/check-redis-cluster.py --bin-dir /path/to/redis-7.2.5/src`를 저장소 루트에서 실행합니다. redis-server와 redis-cli가 필요합니다. 스크립트는 비어 있는 로컬 포트 6개와 cluster bus 포트를 확인하고, 임시 디렉터리에서 3 primary + 3 replica를 생성한 뒤 종료합니다. 기존 Redis에 연결하지 않습니다.

해시 태그의 같은 슬롯 MSET, CROSSSLOT 거부, MOVED와 클러스터-aware 조회, 수동 coordinated failover 뒤 토폴로지 수렴 및 테스트 키 조회를 검사합니다. failover 직후 모든 노드가 동시에 새 상태를 보는 것으로 가정하지 않습니다. 이 테스트는 네트워크 분할·강제 종료·다른 호스트 장애·일반적인 무손실 보장을 검증하지 않습니다. 결과는 learning/redis/cluster-checks.json에 기록됩니다.
