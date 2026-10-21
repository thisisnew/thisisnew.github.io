{"n": 11, "title": "Sentinel 인증과 장애 판단", "desc": "인증 경로를 분리하고 SDOWN·ODOWN·replica 선택 규칙을 운영 증거로 해석한다."}

실습을 먼저 따라 하려면 아래의 **실습 공통 토대**에서 격리된 환경을 준비하고 정상 상태를 확인한 뒤, 이 장의 개별 실험으로 돌아온다. 코드와 출력 설명은 별도 언급이 없는 한 실행 결과가 아니라 예제와 예상 관찰이다.



## 1. 인증은 하나의 비밀번호 문제가 아니다

물류센터의 출입증을 떠올려 보자. 고객 상담원은 배송 상태를 조회할 수 있어야 하지만 출고 담당자를 교체할 권한은 필요 없다. 복제 담당자는 장부를 받아 적어야 하고 관리위원은 담당자 변경 명령을 내릴 수 있어야 한다. Redis의 인증·권한도 역할별로 나누어야 한다. **인증**은 누가 접속했는지 확인하는 것이고 **인가**는 그 사람이 어떤 명령과 키·채널을 사용할 수 있는지 정하는 것이다. TLS는 전송 경로의 암호화와 신원 검증을 다루며 비밀번호 설정만으로 대체되지 않는다.

다섯 연결을 도식에 그린다. 애플리케이션에서 데이터 Redis로 가는 연결, 애플리케이션에서 Sentinel로 가는 연결, Sentinel에서 데이터 Redis로 가는 연결, Sentinel끼리의 연결, replica에서 primary로 가는 복제 연결이다. 각 화살표의 사용자·비밀번호·권한·TLS 설정을 따로 적는다. Sentinel 비밀번호를 Redis 비밀번호로 착각하면 주소 발견은 성공하는데 실제 데이터 접속은 실패하거나 그 반대가 된다.

## 2. ACL과 역할 전환을 함께 설계한다

**ACL**은 Access Control List, 즉 접근 제어 목록이다. Redis 데이터 노드의 ACL은 Redis 6부터 제공되며 Sentinel 자체 ACL은 Redis 6.2부터 제공된다는 버전 차이가 있다. 설치 버전과 클라이언트의 username 지원 여부를 먼저 확인한다. Sentinel이 감시 대상 Redis에 접속할 계정은 `sentinel auth-user logistics-main 사용자`와 `sentinel auth-pass logistics-main 비밀번호`로 지정한다. Sentinel들끼리 사용할 계정은 `sentinel sentinel-user`, `sentinel sentinel-pass`이며 같은 대상이 아니다.

```text
애플리케이션 ─ discovery 계정 ─→ Sentinel
애플리케이션 ─ application 계정 → 데이터 Redis
Sentinel ─ monitor/control 계정 → 모든 데이터 Redis
Sentinel ─ sentinel peer 계정 ─→ 다른 Sentinel
replica ─ replication 계정 ───→ 현재 primary
```

승격 가능한 모든 데이터 노드에 필요한 사용자와 권한을 준비한다. 현재 primary에만 계정을 만들면 장애 전환 직후 새 primary에서 `WRONGPASS`나 `NOPERM`이 발생할 수 있다. replica의 복제 인증도 미래의 역할 전환을 고려한다. ACL 사용자와 `masteruser`·`masterauth`를 사용하는 복제 경로, Sentinel의 제어 경로를 혼동하지 않는다. 계정 회전은 새 자격 증명을 준비하고 모든 경로가 수용하도록 한 뒤 클라이언트를 전환하고 이전 자격 증명을 제거하는 순서로 계획한다.

Sentinel 제어 계정은 상태 조회 외에도 역할 변경과 설정 저장 같은 권한이 필요하다. 정확한 명령 허용 목록은 공식 문서와 사용 버전을 기준으로 검증한다. 편의를 위해 애플리케이션 계정에 `+@all`을 주는 방식은 피한다. 특히 감시 대상 데이터 노드의 `__sentinel__:hello`는 Sentinel 내부 발견 채널이다. 일반 애플리케이션에 광범위한 Pub/Sub 채널 권한을 주어 이 채널에 발행할 수 있게 만들지 않는다. 기본 사용자가 남아 있는지도 함께 검토한다.

## 3. SDOWN은 관점, ODOWN은 조건부 공동 판단이다

Sentinel은 PING에 대한 유효 응답이 일정 시간 없으면 그 인스턴스를 SDOWN으로 본다. 유효 응답에는 단순 `PONG`뿐 아니라 문서에서 인정하는 `LOADING`, `MASTERDOWN` 응답도 포함된다. 따라서 오류 응답이라는 글자만 보고 전부 장애 판단에 같은 영향을 준다고 생각하면 안 된다. 반대로 TCP 연결이 살아 있어도 올바른 응답이 없거나 논리 primary가 replica라고 보고되는 상태는 문제일 수 있다.

`down-after-milliseconds`가 30000이라면 유효 응답이 없는 구간을 관찰한다. 29초마다 유효 응답이 온다면 단순히 오래 느리다는 이유만으로 같은 방식의 SDOWN 조건을 충족하지 않을 수 있다. 이 때문에 애플리케이션의 1초 timeout과 Sentinel의 장애 판단은 다르게 나타난다. 고객은 이미 실패를 보고 있어도 Sentinel은 프로세스를 살아 있다고 볼 수 있다. 감시 timeout을 서비스 SLA 그 자체로 해석해서는 안 된다.

ODOWN은 primary에 대해 다른 Sentinel의 최근 판단을 수집하여 quorum을 충족한 상태다. replica와 다른 Sentinel에는 SDOWN이 표시될 수 있지만 같은 의미의 ODOWN 승격 절차를 적용하지 않는다. ODOWN에 도달해도 실제 전환 수행자 선출에 필요한 과반 승인과 적절한 replica가 있어야 한다. 인증 오류가 원인이라면 서버가 멀쩡해도 필요한 명령을 수행하지 못하므로 장애처럼 보이는 증상과 실제 원인을 분리한다.

## 4. 가장 최신 replica가 무조건 선택되지는 않는다

후보를 고를 때 먼저 너무 오랫동안 primary와 끊긴 replica나 SDOWN 상태 등 부적격 후보를 제외한다. 공식 설명의 연결 단절 한계는 대략 `down-after-milliseconds × 10 + primary가 SDOWN인 기간`이라는 조건으로 표현된다. 실제 필드의 단위와 구현 버전을 확인해야 하며, 숫자를 작은 지연 허용 정책처럼 임의로 해석하지 않는다. 이것은 후보 적격성을 위한 필터이지 모든 승인 쓰기를 보존했다는 증명이 아니다.

적격 후보 사이에서는 낮은 `replica-priority` 값이 우선한다. 우선순위가 같으면 더 많이 복제한 offset이 유리하고, 그것까지 같으면 run ID의 사전식 순서를 사용하여 결정을 안정적으로 만든다. `replica-priority 0`은 가장 높은 우선순위가 아니라 **승격 금지**다. 이 값의 replica도 새 primary를 따라 재구성될 수 있고 읽기 용도로 쓸 수 있지만 새 primary 후보가 되지 않는다.

예를 들어 R1의 priority가 50이고 offset이 9000, R2의 priority가 100이고 offset이 10000이라면 둘 다 적격일 때 priority가 앞선 R1을 우선할 수 있다. “offset이 큰 서버를 늘 뽑는다”는 설명은 틀린다. 특정 센터를 선호하려고 priority를 바꾸면 데이터 최신성과 가용성에 어떤 영향을 주는지 분석한다. 현재 primary도 나중에 replica가 될 수 있으므로 역할별 설정을 한쪽에만 적용하지 않는다.

## 5. 안전한 권한 실패 실험

운영 계정을 잠그지 말고 별도 로컬 ACL 실습 환경을 준비한다. 읽기 전용 애플리케이션 사용자로 `GET`은 허용하고 제어 명령은 거부되는지 확인한다. Sentinel 발견 사용자로 현재 primary 주소 조회는 가능하지만 강제 전환은 거부되는지 확인한다. 비밀번호를 명령행에 직접 적으면 셸 기록과 프로세스 목록에 남을 수 있으므로 비밀 입력을 지원하는 클라이언트 방식을 사용한다. `ACL LOG`를 지원하는 환경에서는 거부 사유와 대상을 확인하되 로그 접근 권한도 제한한다.

권한 검증표의 각 칸에 “성공해야 함”과 “실패해야 함”을 함께 적는다. 보안 시험은 정상 작업이 되는지만 보는 시험이 아니다. 불필요한 제어 명령과 내부 채널 접근이 실패한다는 증거도 필요하다. 마지막에는 실제 역할 전환 후 같은 표를 다시 검사한다. 전환 전 테스트만 통과한 ACL은 HA 보안 설정의 완성이 아니다.

## 실습 공통 토대: 감시망과 데이터망을 따로 확인하기

이 절은 09~12장을 각각 독립적으로 읽어도 실습 전제를 놓치지 않도록 제공하는 복습이다. Sentinel은 데이터를 저장하는 Redis의 다른 이름이 아니다. 데이터 Redis는 주문 상태를 읽고 쓰는 **데이터 평면**이고, Sentinel은 현재 쓰기를 받을 주 서버를 알려 주고 장애 전환을 조정하는 **제어 평면**이다. 운영자는 두 평면의 정상 여부를 각각 확인해야 한다. 감시가 정상이어도 Redis의 디스크가 가득 찰 수 있고, 데이터 읽기가 정상이어도 Sentinel 사이의 연결이 끊어져 다음 장애를 처리하지 못할 수 있다.

물류센터에 비유하면 Redis primary는 출고 장부를 수정하는 현재 담당자, replica는 그 장부를 받아 적는 대기 담당자, Sentinel은 담당자 교체를 결정하는 관리위원이다. 장부 복사는 비동기다. 원 담당자가 출고 승인 도장을 찍은 순간 대기 담당자가 마지막 줄까지 받아 적었다는 뜻은 아니다. 관리위원 세 명이 교체에 동의해도 복사되지 않은 장부 한 줄을 복원할 수는 없다. 이 비유의 한계도 분명하다. Redis는 사람처럼 빠진 주문의 의미를 추론하거나 장부 두 권을 자동 병합하지 않는다. 어느 서버를 기준으로 삼을지 결정하고 나면 이전 서버는 새 기준의 데이터를 복제하게 된다.

### 격리된 실습 환경 만들기

아래는 로컬의 일회용 테스트 환경을 만드는 예제다. 이 교재에서 실행한 결과가 아니며 명령 뒤의 관찰 설명은 **예상되는 관찰**이다. 이미 같은 포트를 쓰는 서비스가 있으면 중단하고 빈 포트로 바꾼다. 인증을 생략하는 이유는 오직 loopback 실습의 복잡도를 낮추기 위해서다. 공유 호스트, 외부 공개 VM, 운영 서버에서는 그대로 사용하지 않는다. 방화벽으로 외부 접근을 차단하고 로컬 사용자에게도 민감한 데이터가 없는 환경을 쓴다. 운영 도입에는 인증, TLS, 비밀 관리, 독립 장애 도메인 배치가 추가로 필요하다.

```bash
# 필요한 프로그램이 설치되어 있는지와 실제 버전을 먼저 기록한다.
redis-server --version
redis-cli --version
LAB=$(mktemp -d /tmp/redis-sentinel-study.XXXXXX)
printf '%s\n' "$LAB"

for p in 6379 6380 6381; do
  mkdir -p "$LAB/$p"
  cat > "$LAB/$p/redis.conf" <<EOF
port $p
bind 127.0.0.1
protected-mode yes
dir $LAB/$p
pidfile $LAB/$p/redis.pid
logfile $LAB/$p/redis.log
daemonize yes
save ""
appendonly no
EOF
  if [ "$p" != 6379 ]; then
    printf 'replicaof 127.0.0.1 6379\n' >> "$LAB/$p/redis.conf"
  fi
  redis-server "$LAB/$p/redis.conf"
done

for p in 26379 26380 26381; do
  mkdir -p "$LAB/$p"
  cat > "$LAB/$p/sentinel.conf" <<EOF
port $p
bind 127.0.0.1
protected-mode yes
dir $LAB/$p
pidfile $LAB/$p/sentinel.pid
logfile $LAB/$p/sentinel.log
daemonize yes
sentinel monitor logistics-main 127.0.0.1 6379 2
sentinel down-after-milliseconds logistics-main 5000
sentinel failover-timeout logistics-main 60000
sentinel parallel-syncs logistics-main 1
EOF
  redis-server "$LAB/$p/sentinel.conf" --sentinel
done
```

여기서 `save ""`와 `appendonly no`는 실습을 단순화하기 위한 **영속성 비활성화**다. 재시작하면 데이터가 남는다고 기대하지 않는다. 운영에 이 설정을 복사해서는 안 된다. 세 Redis와 세 Sentinel이 한 컴퓨터에서 실행되므로 프로토콜은 관찰할 수 있지만 실제 고가용성은 제공하지 않는다. 컴퓨터 하나가 멈추면 여섯 프로세스가 동시에 사라진다. `daemonize`를 지원하지 않는 배포 환경이라면 각 프로세스를 별도 터미널에서 foreground로 시작하고 종료할 대상을 직접 추적한다.

### 정상 상태를 숫자와 관계로 기록하기

```bash
redis-cli -p 6379 INFO replication
redis-cli -p 6380 INFO replication
redis-cli -p 26379 SENTINEL MASTER logistics-main
redis-cli -p 26379 SENTINEL REPLICAS logistics-main
redis-cli -p 26379 SENTINEL SENTINELS logistics-main
redis-cli -p 26379 SENTINEL CKQUORUM logistics-main
redis-cli -p 26379 SENTINEL GET-MASTER-ADDR-BY-NAME logistics-main
```

처음에는 6379가 master이고 다른 두 인스턴스가 그 서버를 복제하는 관계가 예상된다. 일부 출력 필드에는 호환성 때문에 과거 용어 `slave`가 남아 있다. 단어보다 역할과 연결 대상 주소를 읽는다. `master_link_status:up`은 복제 링크가 연결되었다는 뜻이지 데이터 유실 가능성이 없다는 증명은 아니다. `SENTINEL SENTINELS`는 요청받은 Sentinel 자신을 제외한 다른 감시자를 보여 주므로 정상적인 세 감시자 구성에서 목록의 두 항목을 보고 한 대가 사라졌다고 오해하지 않는다.

`CKQUORUM`은 현재 관점에서 장애 판단 정족수와 장애 전환 승인을 받을 수 있는지 검사하는 운영 진단이다. 이 결과가 정상이라고 미래의 복제 지연, 데이터 노드 장애, 클라이언트의 재연결 실패까지 검증되지는 않는다. 따라서 관찰 기록에는 Sentinel 응답만 쓰지 말고 Redis 역할, replica 연결, 애플리케이션 성공률을 함께 적는다. 서로 다른 Sentinel에 같은 조회를 반복해 인식이 일치하는지도 비교한다. 발견 정보가 전파되는 동안 짧은 차이가 있을 수 있으므로 한 번의 서로 다른 응답만으로 영구 분할을 선언하지 않는다.

### 실습을 마친 뒤의 정리

실습 전 포트가 비어 있었고 이 절에서만 생성한 인스턴스라는 것을 확인한 뒤, 테스트 데이터가 필요 없을 때만 각 포트를 종료한다. `killall redis-server`처럼 호스트의 모든 Redis를 종료하는 명령은 쓰지 않는다. 아래 종료 명령도 운영 포트에 그대로 실행하면 장애를 만들므로 현재 실습 대상임을 다시 확인한다.

```bash
# 일회용 실습 인스턴스만 대상으로 한다.
for p in 26379 26380 26381 6379 6380 6381; do
  redis-cli -h 127.0.0.1 -p "$p" SHUTDOWN NOSAVE
done
# 로그 분석이 끝날 때까지 $LAB 디렉터리는 보존한다.
```

종료 도중 연결이 닫혔다는 메시지는 종료 요청이 수락된 상황에서도 보일 수 있다. 프로세스와 포트 상태로 후속 확인한다. 로그에는 실제 주소와 운영 정보가 남으므로 공유 전에 확인한다. 이 실습의 목적은 명령을 외우는 것이 아니라, **설정 → 발견 → 판단 → 승인 → 승격 → 재연결**을 서로 다른 증거로 확인하는 습관을 만드는 것이다.


## 진단 워크숍: 새 primary에서만 로그인에 실패하는 이유

장애 전에는 배송 서비스가 정상인데 전환 직후 `WRONGPASS`가 발생했다고 하자. 운영자는 “Sentinel이 잘못된 서버를 골랐다”고 생각하기 쉽다. 그러나 새 primary가 올바른 후보이며 역할 전환도 성공했을 수 있다. 현재 primary에만 애플리케이션 ACL을 적용했고 replica에는 빠뜨렸다면 데이터 경로 인증만 실패한다. 서버 선택과 자격 증명 배포는 서로 다른 문제다.

| 연결 방향 | 시험할 정상 작업 | 의도적으로 거부되어야 할 작업 | 실패 시 영향 |
|---|---|---|---|
| 앱→Sentinel | primary 주소 조회 | 수동 FAILOVER | 서비스 발견 불가 또는 권한 과다 |
| 앱→Redis | 허용 키의 GET/SET | REPLICAOF·CONFIG 변경 | 업무 요청 실패 또는 제어권 노출 |
| Sentinel→Redis | INFO·PING·필요 제어 명령 | 불필요 업무 키 조작 | 감시·전환 실패 |
| replica→primary | 복제 연결 | 일반 앱 업무 처리 | 복제 지연·단절 |
| Sentinel→Sentinel | 감시자 상호 통신 | 비인가 외부 접속 | 승인 경로 상실 |

실제 권한 명령 목록은 사용하는 Redis 버전과 클라이언트가 연결 초기에 보내는 `HELLO`, `CLIENT SETNAME` 같은 명령을 포함해 검토한다. 최소 권한을 선언했어도 라이브러리가 반드시 필요한 초기 명령을 거부하면 정상 연결이 되지 않는다. 그렇다고 해결책을 `+@all`로 고정하지 않는다. `ACL LOG` 같은 진단 정보로 어떤 명령·키·채널이 거부되었는지 확인한 뒤 필요한 범위만 추가한다.

### 오류 메시지의 의미를 분리한다

`NOAUTH`는 인증하지 않은 상태에서 명령을 실행했다는 방향으로, `WRONGPASS`는 제공한 사용자·비밀번호나 사용자 활성 상태를 확인해야 한다는 방향으로, `NOPERM`은 인증된 사용자의 명령·키·채널 권한을 확인해야 한다는 방향으로 진단을 이끈다. 실제 메시지는 버전에 따라 다를 수 있지만 TCP timeout과는 다른 계층이다. 네트워크가 멀쩡한 상황에서 비밀번호를 잘못 넣었다고 서버 재시작을 반복해도 해결되지 않는다.

또한 애플리케이션이 Sentinel 인증에는 성공했는데 데이터 노드 인증에는 실패할 수 있다. 로그의 대상 주소·포트와 연결 단계가 중요하다. 자격 증명 자체는 남기지 않고 사용자 식별자도 조직의 보안 기준에 맞게 마스킹한다. 연결 pool이 옛 비밀번호를 계속 보유하는지, 회전된 비밀번호가 모든 애플리케이션 인스턴스에 반영되었는지 확인한다. 재연결 시험 없이 secret 파일만 교체하고 끝내면 다음 연결 생성 시점에 장애가 나타날 수 있다.

### 후보 선택 계산 문제

아래 숫자는 이해를 위한 가상 관찰값이다. R1·R2·R3가 모두 적격성 필터를 통과했으며 복제 offset의 단위는 처리한 복제 스트림 위치라고 가정한다.

| 후보 | replica-priority | 처리 offset | 승격 고려 |
|---|---:|---:|---|
| R1 | 100 | 120000 | 일반 후보 |
| R2 | 50 | 119900 | 더 낮은 priority 값으로 우선 |
| R3 | 0 | 121000 | 가장 최신이어도 승격 금지 |

이 경우 R2가 우선될 수 있다. R3의 숫자 0을 가장 좋은 순위라고 읽으면 완전히 반대 결론이 된다. R1과 R2의 priority가 같다면 offset 120000인 R1이 유리하다. 둘이 같은 priority와 offset을 가지면 run ID 비교가 결정성을 높인다. run ID가 작다는 사실은 서버가 더 빠르거나 더 안전하다는 뜻이 아니다. 선택 기준을 설명할 때 필터, 우선순위, 최신성, tie-break 순서를 지킨다.

이제 R2가 너무 오래 primary와 끊겨 적격성에서 제외되었다고 바꿔 보자. priority가 낮아도 후보가 될 수 없으므로 R1이 고려된다. 이 반례가 중요한 이유는 “priority 50이면 항상 승격” 같은 단순 운영 규칙이 틀리기 때문이다. 실제 로그와 `SENTINEL REPLICAS`의 상태를 후보별로 표에 적고 선택이 왜 이루어졌는지 역으로 설명해 본다.

### 응답 지연과 장애 판단의 차이

서비스의 요청 timeout이 800ms인데 Redis가 2초마다 유효한 PING 응답을 보내고 Sentinel의 down-after가 5초라면 고객 요청은 실패하면서도 SDOWN은 아닐 수 있다. 이것은 Sentinel의 버그라고 단정할 수 없다. 서비스 지연 목표와 생존 감시 조건이 다르기 때문이다. CPU·긴 명령·네트워크 지연을 조사하고 감시 timeout을 무작정 줄이기 전에 오탐·반복 전환 위험을 측정한다.

긴 Lua 실행에 따른 `BUSY`도 일반 연결 끊김과 구분한다. Sentinel은 특정 조건에서 `SCRIPT KILL`을 시도할 수 있지만 이미 쓰기를 수행한 스크립트를 안전하게 취소하여 모든 변경을 되돌리는 기능은 아니다. 권한과 스크립트 상태에 따라 결과가 다르다. 운영자가 임의로 프로세스를 종료하기 전에 실행 중인 스크립트와 업무 영향을 분석해야 한다. 제어 계정에 필요한 명령 권한이 빠졌다면 이 경로도 달라질 수 있다.

## 면접 질문과 깊이 있는 답변

답을 펼치기 전에 원리, 장애 반례, 운영 확인 방법의 세 순서로 말해 보자. 짧은 정의만 외우기보다 어떤 조건에서 그 설명이 깨지는지를 덧붙이는 것이 중요하다.

<details><summary>Sentinel 인증과 Redis 인증을 왜 분리하나요?</summary>

주소를 알아내는 권한과 데이터를 읽고 쓰는 권한은 다르기 때문입니다. 애플리케이션→Sentinel, 애플리케이션→Redis, Sentinel→Redis, Sentinel→Sentinel, replica→primary 연결을 따로 설계합니다. 한 비밀번호를 모든 설정에 복사하면 경로별 실패를 찾기 어렵고 권한도 과도해집니다.

</details>

<details><summary>현재 primary에만 ACL을 설정하면 되나요?</summary>

안 됩니다. 승격된 replica가 새 primary가 되므로 필요한 사용자가 모든 잠재적 primary에 준비되어야 합니다. 이전 primary도 replica가 될 수 있어 복제 인증까지 고려해야 합니다. 전환 전후 동일한 허용·거부 테스트를 수행해야 HA 조건에서의 권한 설계가 완성됩니다.

</details>

<details><summary>SDOWN과 ODOWN을 한 문장씩 설명해 보세요.</summary>

SDOWN은 특정 Sentinel 하나가 인스턴스를 사용할 수 없다고 판단한 상태입니다. ODOWN은 primary에 대해 충분한 감시자의 최근 장애 의견을 모아 quorum을 충족한 상태입니다. ODOWN이 곧 전환 완료는 아니며 과반 승인과 후보 선택이 추가로 필요합니다.

</details>

<details><summary>PING에 오류가 오면 항상 SDOWN인가요?</summary>

아닙니다. 공식 판단에서 PONG뿐 아니라 LOADING·MASTERDOWN 같은 유효 응답도 인정됩니다. 오류 문자열 전체를 같은 부류로 처리하면 잘못 이해할 수 있습니다. 반대로 TCP 연결만 유지된다고 정상은 아니므로 응답 종류와 유효 응답이 없었던 시간을 함께 봅니다.

</details>

<details><summary>가장 큰 replication offset의 replica가 항상 승격되나요?</summary>

아닙니다. 먼저 부적격 후보를 제외하고, 적격 후보에서는 replica-priority가 앞섭니다. 같은 우선순위에서 offset을 비교하고 그마저 같으면 run ID 순으로 결정합니다. 특정 위치 선호를 위해 우선순위를 조정하면 더 최신 후보보다 덜 최신 후보가 선호될 가능성을 검토해야 합니다.

</details>

<details><summary>replica-priority 0은 가장 높은 우선순위인가요?</summary>

일반적으로 낮은 숫자가 선호되지만 0은 특별하게 승격 금지를 의미합니다. 그 replica가 복제 자체를 하지 않는다는 뜻은 아니며 전환 후 새 primary를 따라 재구성될 수 있습니다. 전용 조회 서버 등으로 쓸 때 유용하지만 남은 승격 후보 수가 충분한지 확인해야 합니다.

</details>

<details><summary>인증 오류도 HA 장애를 만들 수 있나요?</summary>

네. 감시자가 상태 조회나 제어 명령을 수행하지 못하거나 replica가 새 primary에 인증하지 못하면 프로세스가 살아 있어도 전환과 복제가 실패합니다. WRONGPASS·NOPERM·네트워크 timeout을 분리하고 ACL 로그와 연결 방향을 확인해야 합니다. 재시작은 잘못된 권한을 고치지 못합니다.

</details>

<details><summary>애플리케이션에 모든 Pub/Sub 채널을 허용해도 되나요?</summary>

Sentinel 감시 데이터 노드에서는 특히 주의해야 합니다. 내부 발견 채널인 __sentinel__:hello는 일반 애플리케이션이 발행할 수 없도록 제한합니다. 필요한 업무 채널만 허용하고 default 사용자와 광범위한 채널 패턴을 검토합니다. 인증된 사용자라는 이유만으로 제어 정보 채널까지 신뢰해서는 안 됩니다.

</details>


## 원문과 공식 확인 자료

이 장은 제공된 `Redis_Senior_Study/chapters/11_` 원문의 해당 주제를 한국어로 재구성하고 독립적인 학습 예제와 판단 절차를 추가했다. 제공 원문은 최신 버전 보증 자료가 아니므로 운영 적용 전 실제 Redis와 클라이언트 버전을 확인한다. 공식 링크는 2026-10-21 집필 시 확인했으며 이 장의 실습 명령을 실행했다는 뜻은 아니다.

- [Redis 공식 Sentinel 문서](https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/) — 배치·전환·인증·정족수·epoch의 기준.
- [Sentinel 클라이언트 구현 지침](https://redis.io/docs/latest/develop/reference/sentinel-clients/) — 발견과 재연결을 검토할 때 참고.
- [WAIT 명령의 보장 범위](https://redis.io/docs/latest/commands/wait/) — 복제 확인과 강한 일관성을 구분할 때 참고.
