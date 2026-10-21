{"n": 10, "title": "Sentinel 장애 전환과 운영 API", "desc": "장애 감지부터 클라이언트 재연결까지 따라가며 Sentinel 조회·변경 API를 안전하게 구분한다."}

실습을 먼저 따라 하려면 아래의 **실습 공통 토대**에서 격리된 환경을 준비하고 정상 상태를 확인한 뒤, 이 장의 개별 실험으로 돌아온다. 코드와 출력 설명은 별도 언급이 없는 한 실행 결과가 아니라 예제와 예상 관찰이다.



## 1. 장애 전환은 한 번의 명령이 아니라 상태 변화다

출고 조회 서비스에서 primary 연결이 끊겼다고 가정하자. Sentinel 하나가 즉시 새 서버를 만드는 것이 아니다. 각 Sentinel이 일정 시간 유효한 응답을 받지 못하면 SDOWN을 표시하고, 충분한 감시자가 primary 장애에 동의하면 ODOWN에 도달한다. 이후 한 Sentinel이 해당 전환을 실행할 권한을 얻고, 적절한 replica를 고르고, 승격 명령을 보내고, 실제 역할 변경을 확인한다. 다른 replica의 복제 대상과 클라이언트 경로도 따라 바뀌어야 한다.

**SDOWN**은 한 감시자의 주관적 장애 판단이고 **ODOWN**은 정족수 기반의 primary 장애 판단이다. 이 장에서는 먼저 흐름의 단계로 이해하고, 구체적인 판정과 선출 규칙은 11~12장에서 다룬다. 중요한 점은 감지, 승인, 승격, 전파, 애플리케이션 복구가 같은 시각에 끝나지 않는다는 것이다. `down-after-milliseconds`를 5초로 설정했다고 고객 오류가 정확히 5초만 지속된다고 약속할 수 없다.

## 2. 먼저 읽기 전용 운영 API로 현황을 파악한다

`SENTINEL MASTERS`는 감시 중인 논리 primary 그룹들을 보여 준다. `SENTINEL MASTER 이름`은 한 그룹의 상세 상태를 보여 준다. `SENTINEL REPLICAS 이름`은 발견한 replica, `SENTINEL SENTINELS 이름`은 다른 감시자, `SENTINEL GET-MASTER-ADDR-BY-NAME 이름`은 현재 primary 주소를 보여 준다. 운영 대시보드에 모든 출력을 무작정 저장하기보다 주소·역할·플래그·quorum·알려진 감시자 수·최근 응답 시각처럼 질문에 답하는 필드를 선택한다.

```bash
redis-cli -p 26379 SENTINEL MASTERS
redis-cli -p 26379 SENTINEL MASTER logistics-main
redis-cli -p 26379 SENTINEL CKQUORUM logistics-main
redis-cli -p 26380 SENTINEL GET-MASTER-ADDR-BY-NAME logistics-main
redis-cli -p 26381 SENTINEL GET-MASTER-ADDR-BY-NAME logistics-main
```

같은 논리 이름을 모든 곳에서 정확히 사용해야 한다. 이름은 DNS 이름이나 Redis의 임의 키가 아니라 Sentinel이 감시 그룹을 식별하는 서비스 이름이다. 클라이언트가 다른 이름을 질의하면 주소를 얻지 못한다. 주소 결과를 영구 캐시하지도 않는다. 장애 전환 이후 기존 주소는 replica가 될 수 있기 때문이다. Sentinel 지원 클라이언트는 접속 실패와 역할 변경을 감지하고 현재 primary를 다시 찾아야 한다.

## 3. 장애 전환 실습: 사라진 포트보다 바뀐 역할을 관찰한다

공통 토대 실습에서 최초 primary가 6379임을 실제 조회로 확인한 뒤, 테스트 데이터만 있는 그 프로세스를 정상 종료한다. 이 실험은 abrupt crash가 아니라 정상 종료 실험이다. 영속성을 꺼 두었으므로 데이터를 보존하는 테스트가 아니다.

```bash
redis-cli -p 6379 SET shipment:S100:status READY
redis-cli -p 6380 GET shipment:S100:status
# 반드시 현재 primary가 6379이고 일회용 인스턴스인지 확인한 뒤 실행한다.
redis-cli -p 6379 SHUTDOWN NOSAVE
# 다른 터미널에서 로그를 관찰한다.
tail -f "$LAB/26379/sentinel.log"
# 시간이 지난 후 각 Sentinel에서 다시 조회한다.
redis-cli -p 26379 SENTINEL GET-MASTER-ADDR-BY-NAME logistics-main
```

예상 관찰은 6380 또는 6381 가운데 적절한 후보가 primary로 바뀌고, Sentinel이 새 주소를 반환하는 것이다. 어느 포트가 선택된다고 고정해서 기대하지 않는다. 우선순위·복제 진행도·후보 상태가 선택에 영향을 준다. 로그에는 `+sdown`, `+odown`, 선출·승격 관련 이벤트, `+switch-master` 같은 전환 흔적이 나타날 수 있다. 이벤트 이름과 세부 순서는 버전과 경로에 따라 다를 수 있으므로 로그 한 줄만으로 완료를 판정하지 않는다.

새 주소에 `ROLE`과 읽기·쓰기를 실행해 역할과 애플리케이션 경로를 확인한다. 종료했던 6379를 동일 설정으로 다시 시작하면 Sentinel이 현재 논리 구성을 적용해 새 primary의 replica로 재구성하는지 관찰한다. 이때 과거 primary라는 이유로 자동으로 주도권을 되찾는 것이 아니다. 재시작과 재동기화 동안 서비스 지연과 네트워크 사용량도 기록한다.

## 4. 조회 API와 변경 API를 섞지 않는다

`SENTINEL SET`은 감시 그룹의 런타임 설정을 바꾸는 명령이고 `SENTINEL CONFIG SET`은 지원되는 전역 설정을 바꾸는 경로다. 적용 범위와 지원 버전이 다르므로 명령 도움말과 운영 버전을 확인한다. 한 Sentinel에서 바꾼 임의의 정책 설정이 모든 Sentinel에 자동으로 배포된다고 가정해서는 안 된다. 필요한 변경을 각 인스턴스에 적용하고 다시 조회해 일치 여부를 확인한다. 구성 전파와 정책 설정 배포는 같은 의미가 아니다.

`SENTINEL MONITOR`, `REMOVE`, `RESET`, `FAILOVER`는 상태를 바꾸므로 별도의 작업 승인과 롤백 계획이 필요하다. 특히 `SENTINEL FAILOVER 이름`은 운영자가 강제 전환을 요청하는 API이며 정상 자동 장애 판단·과반 동의 경로와 같은 시험이라고 보면 안 된다. 자동 장애 전환이 안 되는 원인을 숨기기 위해 먼저 이 명령을 쓰면, 정작 quorum 문제나 감시자 통신 문제를 검증하지 못한다. 또한 이 명령을 Cluster의 `CLUSTER FAILOVER`와 동일한 안전한 동기화 절차로 이해해서도 안 된다.

## 5. Pub/Sub 이벤트와 운영 자동화의 경계

Sentinel 이벤트를 구독하면 역할 변경을 운영 채널이나 모니터링 시스템에 전달할 수 있다. 그러나 Pub/Sub은 구독자가 연결되지 않았던 동안의 메시지를 자동으로 보관하고 재전달하는 영속 로그가 아니다. 이벤트는 신속한 알림 신호로 사용하고, 정기적인 상태 조회를 함께 사용해 현재 사실을 확정한다. “switch-master 알림을 못 받았으니 전환은 없었다”는 결론은 틀릴 수 있다.

외부 스크립트는 실패해도 Sentinel 본체와 별도로 조사한다. 알림 웹훅의 timeout을 Redis 데이터 장애와 혼동하지 않는다. 스크립트가 다시 실행될 수 있음을 고려해 멱등하게 작성하고 비밀 값이 인자나 로그에 노출되지 않게 한다. 애플리케이션은 알림을 받아 내부 주소를 직접 덮어쓰는 임시 구현보다, 검증된 Sentinel 지원 클라이언트의 발견·재연결 기능을 활용하는 편이 안전하다.

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


## 실행 추적 워크숍: 주문 조회 요청 하나를 끝까지 따라가기

요청 `lookup-827`이 배송 상태를 읽는 중 primary 연결이 끊겼다고 하자. 로그에 연결 예외가 나타난 시각과 Sentinel의 SDOWN 시각을 같은 것으로 취급하지 않는다. 애플리케이션의 timeout이 더 짧으면 고객은 먼저 오류를 경험한다. 반대로 연결 풀에 남은 연결이 잠시 살아 있어 일부 요청은 성공할 수도 있다. 측정할 대상은 평균 응답 시간이 아니라 시간대별 성공률과 오류 종류다.

| 상대 시점 | Sentinel 관찰 | 클라이언트 관찰 | 해석 |
|---|---|---|---|
| T0 | 아직 기존 primary를 가리킴 | 한 요청에서 timeout | 명령 미실행 여부는 모름 |
| T1 | 한 감시자의 SDOWN | 기존 연결 반복 실패 | 국소 감지 단계 |
| T2 | ODOWN·선출 시도 | 새 연결도 실패할 수 있음 | 판단과 전환 수행이 진행 중 |
| T3 | 후보 승격을 INFO로 확인 | 일부 클라이언트가 새 주소 발견 | 서버 전환과 클라이언트 전환이 겹침 |
| T4 | 새 주소 인식이 수렴 | 새 연결의 조회 성공 | 서비스 회복 증거 확보 |
| T5 | 나머지 replica 재구성 | 정상 성공률 유지 | 보호 수준 복구 확인 |

표의 시간은 실측 결과가 아니라 순서를 설명하는 논리 시점이다. 실제 로그에서는 네트워크 지연 때문에 순서가 엇갈려 보일 수 있고, 서로 다른 호스트의 시계 차이도 있다. 로그에는 wall clock과 함께 요청 경과 시간을 기록하고, correlation ID로 애플리케이션 요청을 묶는다. 전환 전체를 한 스톱워치 숫자로만 표현하면 어느 단계가 느렸는지 알 수 없다.

### 재연결 상태를 애플리케이션 코드로 생각하기

```java
// 라이브러리 구현을 대체하는 코드가 아닌 장애 처리 상태 모델이다.
enum RedisPathState {
    CONNECTED, REQUEST_UNCERTAIN, DISCOVERING,
    VERIFYING_ROLE, RECONNECTING, RECOVERED, DEADLINE_EXCEEDED
}
```

`REQUEST_UNCERTAIN`은 중요하다. 쓰기 명령을 보낸 뒤 연결이 끊겼다면 “실패했으니 다시 쓰자”가 아니라 “적용됐는지 모른다”는 상태를 먼저 표현한다. 읽기 요청은 같은 조건으로 재시도하기가 상대적으로 쉽지만, 출고 수량 `INCR`는 재실행할 때 한 번 더 증가할 수 있다. 업무 요청 ID로 원장 결과를 조회하거나 멱등하게 처리 가능한 형태로 바꿔야 한다. 연결 회복 로직과 업무 재실행 로직을 같은 catch 블록에 숨기지 않는다.

Sentinel 지원 클라이언트는 알려진 Sentinel에서 현재 primary를 다시 발견하고, 연결한 서버의 역할이 기대한 것인지 확인하는 절차를 가져야 한다. 특정 Sentinel 하나가 안 된다고 전체 발견을 즉시 실패시키기보다 다른 seed를 시도할 수 있어야 한다. 반대로 오래된 주소를 무제한 반복해서 붙잡으면 새 primary가 정상이어도 업무는 회복되지 않는다. 실제 라이브러리의 timeout·재연결·풀 재생성 동작은 사용하는 버전으로 테스트한다.

### 운영 API 출력에서 다음 행동을 고르기

`CKQUORUM`이 실패하고 replica는 정상이라면 먼저 감시자 통신과 멤버십 인식을 조사한다. 이때 replica를 강제로 승격하는 명령부터 실행하면 원인을 숨기고 이중 쓰기 위험을 만들 수 있다. `CKQUORUM`은 정상인데 후보 선택이 실패한다면 후보의 SDOWN·연결 단절 시간·priority·인증을 조사한다. 새 주소가 반환되지만 애플리케이션만 실패한다면 ACL·광고 주소·네트워크·클라이언트 모드를 조사한다. 같은 “전환 실패”라도 다음 명령이 달라진다.

운영자가 `SENTINEL FAILOVER`를 실행했다면 작업 기록에 반드시 **수동 강제 요청**이라고 적는다. 이 명령은 다른 Sentinel의 정상 자동 합의를 동일하게 거치는 시험이 아니다. 자동 전환 시험의 성공 횟수에 섞지 않는다. 기존 primary가 살아 있는 상태에서 일으킨 강제 Sentinel 전환을 정상 협력형 Cluster 전환과 동일한 무손실 유지보수 방식으로 설명해서도 안 된다.

### 감시자 수를 바꾸는 작업의 완료 조건

새 Sentinel을 추가할 때는 현재 primary를 가리키는 초기 설정으로 시작하고 다른 Sentinel들이 그 존재를 발견한 뒤 다음 추가를 진행한다. 제거할 때는 단순히 프로세스를 끄는 일과 남은 감시자의 알려진 멤버십을 정리하는 일을 구분한다. 오래된 replica나 감시자 정보를 자동으로 즉시 잊을 것이라 기대하지 않는다. RESET 같은 상태 변경 명령은 발견 정보를 지우고 다시 채우게 할 수 있으므로 현재 인식과 복구 절차를 확인한 뒤 한 인스턴스씩 수행한다.

완료 선언에는 세 증거가 필요하다. 첫째, 여러 Sentinel의 현재 primary 조회가 같은 역할 변경을 반영한다. 둘째, 애플리케이션이 새 경로에서 실제 명령을 성공시킨다. 셋째, 의도한 replica 수가 새 primary를 정상 복제한다. 첫 번째만 충족하면 제어 평면은 회복했지만 고객 경로는 미확인이고, 두 번째만 충족하면 다음 장애를 버틸 보호 수준이 부족할 수 있다.

## 면접 질문과 깊이 있는 답변

답을 펼치기 전에 원리, 장애 반례, 운영 확인 방법의 세 순서로 말해 보자. 짧은 정의만 외우기보다 어떤 조건에서 그 설명이 깨지는지를 덧붙이는 것이 중요하다.

<details><summary>SDOWN 로그가 보이면 장애 전환이 완료된 건가요?</summary>

아닙니다. 한 감시자가 응답을 신뢰하지 못하는 단계입니다. 정족수 판단, 전환 수행자 승인, 적격 후보 선택, 실제 승격, 구성 전파, 클라이언트 재연결이 남을 수 있습니다. 로그와 역할 조회 및 실제 업무 요청을 연결해 단계별 완료를 판정해야 합니다.

</details>

<details><summary>down-after를 5초로 하면 RTO도 5초인가요?</summary>

이 값은 감지 조건의 일부이지 전체 복구 시간 보장이 아닙니다. 승인과 후보 선택, 재구성, DNS·연결 timeout, 클라이언트 재시도 때문에 더 길어질 수 있습니다. RTO는 업무 요청이 다시 성공하는 기준으로 측정하며 감지 시간과 따로 기록합니다.

</details>

<details><summary>GET-MASTER-ADDR-BY-NAME 결과를 계속 써도 되나요?</summary>

현재 알려진 주소를 반환하는 조회이므로 영구 불변값이 아닙니다. 장애 전환 뒤 주소와 역할이 달라질 수 있습니다. Sentinel 지원 클라이언트를 사용하고 연결 실패 또는 역할 오류 때 새 주소를 발견하는 경로를 시험해야 합니다. 기존 커넥션 풀도 변화에 대응해야 합니다.

</details>

<details><summary>CKQUORUM 성공은 어떤 의미인가요?</summary>

현재 Sentinel 관점에서 장애 판단과 전환 승인을 위한 감시자 조건을 점검한 결과입니다. 새 primary의 데이터 최신성이나 애플리케이션 ACL, 클라이언트 재연결까지 검증한 결과는 아닙니다. 예방 점검에 유용하지만 실제 전환 시험을 대체하지 않습니다.

</details>

<details><summary>SENTINEL FAILOVER로 자동 장애 전환을 검증할 수 있나요?</summary>

강제 전환 요청과 정상 자동 판단 경로는 다릅니다. 이 명령은 자동 ODOWN·승인 경로의 모든 조건을 같은 방식으로 시험하지 않으므로 통신이나 quorum 문제가 가려질 수 있습니다. 강제 전환 시험은 별도로 표시하고 자동 전환은 실제 격리된 장애 조건에서 관찰해야 합니다.

</details>

<details><summary>한 Sentinel의 SET 변경이 모든 곳에 배포되나요?</summary>

임의의 감시 정책 변경이 모든 Sentinel에 자동 동기화된다고 가정하면 안 됩니다. 전환 결과의 구성 전파와 운영 설정 배포는 다릅니다. 각 인스턴스에 필요한 변경을 적용하고 조회로 일치 여부를 확인하며 재시작 후 상태도 점검합니다.

</details>

<details><summary>switch-master 알림을 받으면 모든 replica도 준비됐나요?</summary>

새 primary 정보가 알려지는 시점과 나머지 replica의 재동기화 완료 시점은 다릅니다. 주소 전환 후에도 복제 여유가 부족할 수 있습니다. 애플리케이션 회복과 redundancy 회복을 별도 지표로 관리하고 다음 유지보수는 보호 수준이 회복된 뒤 진행합니다.

</details>

<details><summary>Pub/Sub 알림이 없으면 전환이 없었던 건가요?</summary>

아닙니다. 구독 연결이 끊겨 있던 동안 이벤트를 놓칠 수 있습니다. Pub/Sub은 영속 재생 로그가 아니므로 상태 조회와 서버 로그를 함께 사용합니다. 이벤트는 빠른 신호이고 현재 역할·주소·epoch 같은 조회는 사실을 확정하는 증거로 활용합니다.

</details>


## 원문과 공식 확인 자료

이 장은 제공된 `Redis_Senior_Study/chapters/10_` 원문의 해당 주제를 한국어로 재구성하고 독립적인 학습 예제와 판단 절차를 추가했다. 제공 원문은 최신 버전 보증 자료가 아니므로 운영 적용 전 실제 Redis와 클라이언트 버전을 확인한다. 공식 링크는 2026-10-21 집필 시 확인했으며 이 장의 실습 명령을 실행했다는 뜻은 아니다.

- [Redis 공식 Sentinel 문서](https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/) — 배치·전환·인증·정족수·epoch의 기준.
- [Sentinel 클라이언트 구현 지침](https://redis.io/docs/latest/develop/reference/sentinel-clients/) — 발견과 재연결을 검토할 때 참고.
- [WAIT 명령의 보장 범위](https://redis.io/docs/latest/commands/wait/) — 복제 확인과 강한 일관성을 구분할 때 참고.
