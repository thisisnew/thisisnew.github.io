{"n":8,"title":"복제 운영과 쓰기 제한 — 연결됨과 안전함을 구별하기","desc":"복제본 읽기·인증·메모리·만료·주소 알림과 min-replicas 쓰기 제한을 실제 운영 판단으로 연결한다."}

## 이 장의 출발점

앞 장에서 복제 스트림, 전체 동기화, 부분 재동기화를 배웠다. 이제 운영자의 질문은 달라진다. “복제가 되나요?”만으로는 부족하다. **이 복제본에서 읽어도 되는가, 장애 때 계속 쓰기를 받아도 되는가, 복제본이 새 원본이 되어도 자원과 보안 정책이 안전한가**를 물어야 한다.

제공 자료 08장의 운영 설정을 중심으로, 원문에서 서로 떨어져 있는 읽기 전용·인증·메모리·만료·주소 문제를 하나의 운영 모델로 연결한다. 설정 이름과 기본 동작은 실제 바이너리 버전과 배포 방식에서 확인한다. Redis Open Source의 설정을 관리형 서비스에 그대로 적용할 수 있다고 가정하지 않는다. 이 장에서는 원본을 primary, 복제본을 replica라고 부르되 `masterauth`, `master_link_status`처럼 실제 설정·출력 이름은 그대로 쓴다. [공식 복제 문서](https://redis.io/docs/latest/operate/oss_and_stack/management/replication/)

## 먼저 이해할 바탕. 초록 불 하나로 복제본의 모든 상태를 표현할 수 없다

서버가 살아 있다는 말에는 여러 뜻이 숨어 있다. 프로세스가 존재하는지, 네트워크 연결이 되는지, Redis 명령에 응답하는지, 복제 데이터를 따라오는지, 지금 읽어도 되는지, 새 primary로 써도 되는지가 다르다. 처음에는 이 모든 것을 “정상”이라고 묶기 쉽다. 운영에서는 어떤 질문에 정상인지 나누어야 한다.

병원에 비유하면 접수 창구가 열려 있다는 사실과 의사가 진료할 준비가 됐다는 사실, 응급 수술이 가능하다는 사실이 다른 것과 같다. PING에 응답하는 replica라도 초기 동기화 중일 수 있고, 큰 조회 때문에 복제 적용이 늦을 수 있다. 현재 읽기에는 쓸 수 있어도 승격 후의 쓰기와 영속성 부하를 감당하지 못할 수 있다. 비유는 준비 수준을 구별하는 데 쓰고 실제 판단은 Redis와 시스템의 상태로 한다.

복제본에 기대하는 기능도 분리하자. 읽기 분산용 서버는 오래된 값을 어느 정도 허용할 수 있다. 장애 전환 후보는 primary의 쓰기를 이어 받아야 한다. 분석 조회용 서버는 큰 요청을 처리하느라 자원을 많이 사용할 수 있다. 한 서버가 여러 역할을 맡으면 비용과 목적이 충돌할 수 있다. 역할을 나누는 것은 반드시 서버 수를 늘리라는 말이 아니라 **서로 다른 요구를 같은 정상 기준으로 숨기지 말라는 뜻**이다.

이 장의 설정들은 이런 질문의 일부에 답한다. read-only는 잘못된 데이터 쓰기를 막는 역할이고, stale-data 정책은 특정 연결 상태에서 오래된 데이터 제공을 어떻게 다룰지와 관련되며, 최소 replica 조건은 쓰기 수락의 보호 조건이다. 인증과 메모리, 광고 주소는 또 다른 축이다. 설정 하나가 전체 안전성을 대신하지 않는다는 관점으로 읽으면 많은 옵션이 정리된다.


## 1. 복제본의 역할부터 명확히 하기

복제본에는 여러 기대가 붙는다. 읽기 요청을 나눠 처리하는 서버, 원본 장애 때 승격할 예비 서버, 백업 파일을 만드는 서버, 무거운 조회를 대신 처리하는 서버가 그것이다. 하나의 복제본이 여러 역할을 맡을 수 있지만 역할들이 항상 잘 어울리는 것은 아니다. 대량 조회로 CPU가 바쁜 복제본은 복제 스트림 적용이 늦어질 수 있고, 그 순간 승격 후보로서의 품질도 떨어질 수 있다.

복제본은 책을 베껴 적는 보조 서기와 비슷하다. 원본 서기가 새 문장을 쓰면 보조 서기가 뒤따라 쓴다. 보조 서기가 같은 방에 있고 펜을 들고 있다는 사실만으로 마지막 문장까지 다 썼다고 보장할 수 없다. 또 보조 서기가 자기 생각대로 문장을 고치면 다음 복사 내용과 충돌한다. 이것이 비동기 지연과 writable replica 문제를 이해하는 비유다. 다만 실제 Redis는 문장이 아니라 순서가 있는 복제 스트림과 상태를 관리하며, 재동기화와 복제 ID를 사용한다는 한계도 기억한다.

운영 설계서에는 다음을 적는다.

- 어떤 요청은 primary에서만 읽어야 하는가.
- 얼마만큼 오래된 값을 허용하는가.
- 복제 연결이 끊겼을 때 오래된 값으로 계속 응답할 것인가, 오류를 낼 것인가.
- 복제본의 CPU·메모리·디스크 용량은 승격 뒤의 쓰기까지 감당하는가.
- 누구에게 승격 권한이 있고, 클라이언트는 새 primary를 어떻게 찾는가.
- 복제본 한 대를 점검 중 내려도 쓰기 제한 조건을 만족하는가.

복제 자체는 자동 재연결을 제공하지만, 이 질문들의 업무상 정답까지 결정해 주지는 않는다.

## 2. 읽기 전용은 실수 방지 장치이지 보안 경계가 아니다

`replica-read-only yes`는 일반 클라이언트가 복제본에 데이터 쓰기를 보내는 실수를 막는다. primary로 가야 할 `SET`이 replica로 잘못 라우팅되면 쓰기 거절을 받아 문제를 발견할 수 있다. 이를 꺼서 오류를 없애면 연결 설정 오류를 데이터 불일치 문제로 바꾸는 셈이다.

읽기 전용 상태에서도 민감한 데이터를 읽을 수 있고, 허용된 관리 명령은 별도의 권한 문제다. 버전에 따라 위험한 관리 명령의 기본 제한이 강화되어 있을 수 있지만, **read-only 설정 자체가 사용자 인증이나 명령별 권한을 부여하는 것은 아니다.** 따라서 인터넷에 노출해도 안전하다는 결론을 내리면 안 된다. 네트워크 경계, ACL, TLS, 비밀 관리, 관리 명령 제한은 따로 설계한다.

ACL은 Access Control List의 약자다. 누가 어떤 명령과 키에 접근할 수 있는지를 정하는 규칙이다. 예를 들어 애플리케이션 읽기 계정은 자신의 키 패턴에 필요한 조회만 허용하고, 운영 계정은 별도 경로로 관리한다. 복제용 계정도 애플리케이션 관리자 계정과 분리할 수 있다. “서버가 replica니까 안전하다”가 아니라 “이 연결의 주체가 어떤 권한을 가졌는가”를 확인한다.

복제본을 writable로 만드는 것은 보통 읽기 확장의 해법이 아니다. 원본의 `INCR counter`가 복제될 때 복제본에서 `counter`를 문자열 이름으로 바꿔 놓았다면 같은 명령이 다른 결과를 만들거나 실패한다. 로컬 쓰기가 자동으로 원본으로 합쳐지는 다중 쓰기 시스템도 아니다. 재동기화 때 사라질 수 있으면서, 그 전까지는 원본과 다른 데이터를 제공할 수 있다. 임시 작업 결과가 필요하면 별도의 인스턴스나 지원되는 읽기 전용 명령·계산 경로를 검토한다.

## 3. replica 읽기에서 발생하는 read-after-write 문제

사용자가 닉네임을 변경했다. 애플리케이션은 primary에 새 값을 저장하고 다음 화면의 조회는 replica로 보냈다. 복제 적용이 아직 끝나지 않았다면 사용자는 옛 닉네임을 본다. 쓰기는 성공했지만 방금 쓴 값을 읽지 못하는 상황이며, 이를 read-after-write 일관성 문제로 설명할 수 있다.

이때 “복제는 보통 아주 빠르다”는 답은 해결책이 아니다. 평소에는 드물어도 네트워크 정체, 전체 동기화, CPU 경합, 큰 명령 처리 중에는 쉽게 드러날 수 있다. 업무 요구에 따라 다음 선택을 비교한다.

1. 변경 직후의 중요한 조회는 primary로 보낸다.
2. 해당 사용자의 일정한 흐름을 primary 읽기에 묶되, 전환 기준과 기간을 설계한다.
3. 오래된 값이 허용되는 조회만 replica로 분리한다.
4. 버전 번호나 갱신 시각으로 낡은 응답을 감지하고 필요한 경우 더 최신 경로로 재조회한다.

단순히 일정 시간 sleep을 넣는 방법은 지연 상한을 증명하지 못하고 모든 요청을 느리게 만들 수 있다. `WAIT`로 일부 복제본의 확인을 받아도 그 뒤 조회가 임의의 다른 replica로 간다면 동일한 보장이 아니다. 어떤 복제본이 확인했는지, 읽기 라우팅이 어디로 가는지, failover가 사이에 일어나는지까지 생각해야 한다.

Spring이나 Java에서 “read from replica” 옵션을 켜는 것은 성능 최적화가 아니라 일관성 정책 변경이다. 연결 팩토리나 드라이버의 읽기 라우팅 설정을 바꿀 때 서비스 메서드별 요구를 분류한다. 권한 변경 직후 확인, 잔액 검증, 중복 처리 판단을 단순 통계 조회와 같은 경로로 보내지 않는다. 프레임워크의 편리한 옵션이 업무 보장을 대신 결정해 주지는 않는다.

## 4. 연결이 끊겼을 때 오래된 데이터를 제공할 것인가

`replica-serve-stale-data`는 복제 연결이 끊겼거나 동기화 중인 상황에서 데이터 요청을 어떻게 다룰지에 영향을 준다. 오래된 데이터를 허용하면 가용성은 높아질 수 있지만 신선도는 떨어진다. 허용하지 않으면 오류를 통해 문제를 드러내지만 애플리케이션이 대체 경로를 준비해야 한다. 정확한 명령 예외와 로딩 동작은 버전별 설정 문서를 확인한다.

중요한 오해는 이 설정을 `no`로 두면 언제나 최신 읽기가 된다고 생각하는 것이다. 연결이 살아 있는 상태에서도 비동기 적용 지연이 있을 수 있다. 이 옵션은 모든 읽기를 primary의 특정 offset과 비교해 선형화하는 기능이 아니다. “연결이 끊어진 데이터는 내주지 않겠다”는 정책과 “마지막 쓰기를 반드시 읽겠다”는 보장은 다르다.

건강 점검도 `PING` 하나로 끝내지 않는다. replica가 요청에는 응답하면서 오래된 데이터만 보유할 수 있다. 읽기 대상 선정에는 역할, 링크 상태, 동기화 진행, 지연 지표, 애플리케이션이 허용하는 신선도 기준을 함께 반영한다. 반대로 링크가 잠시 불안정하다고 모든 읽기를 primary로 한꺼번에 몰면 원본의 부하가 급증할 수 있으므로 트래픽 전환의 용량도 준비한다.

## 5. min-replicas 쓰기 제한이 실제로 확인하는 것

다음 설정을 생각해 보자. 숫자는 설명용이며 운영 권장값이 아니다.

```conf
min-replicas-to-write 1
min-replicas-max-lag 3
```

의도는 “허용 가능한 최근 응답 상태의 replica가 적어도 한 대 있을 때만 쓰기를 받자”다. primary는 replica가 주기적으로 보내는 복제 진행 확인을 보고 최근 상태를 판단한다. 조건을 만족하지 않으면 쓰기를 거절한다. 이것은 primary가 장시간 혼자 쓰기를 계속 받아 나중에 그 기록을 잃는 위험을 줄이는 안전장치다.

하지만 **지금 막 들어온 그 쓰기를 replica가 처리했다는 ACK를 받고 성공 응답하는 동기 복제는 아니다.** 다음 타임라인이 반례다.

```text
t0: replica가 이전 offset까지 처리했다고 확인
 t1: primary가 최근 확인 상태를 보고 새 쓰기 허용
 t2: primary가 클라이언트에 성공 응답
 t3: 새 쓰기가 replica에 도착하기 전에 primary 장애
```

t1의 조건은 만족했지만 t3에서 새 쓰기는 아직 복제되지 않았을 수 있다. `min-replicas-max-lag`를 몇 초로 설정했다고 개별 데이터의 나이가 그 숫자 이하임을 직접 검사하는 것도 아니다. heartbeat/ACK의 최근성과 스트림 offset 차이를 구분해야 한다. offset 차이는 바이트 단위 진행 차이이며 그 자체가 업무상 지연 시간도 아니다.

이 기능은 다수결 합의 프로토콜이나 fencing을 대신하지 않는다. 네트워크가 갈라졌을 때 옛 primary가 얼마나 오래 쓰기를 받을지 줄일 수 있지만, 모든 split-brain 기록의 충돌을 해소하거나 어떤 노드가 정당한 리더인지 전역적으로 증명하지는 않는다. Sentinel·Cluster의 장애 전환과 클라이언트 라우팅, 애플리케이션 멱등성을 함께 고려한다.

## 6. 안전성과 가용성의 교환을 계산하기

primary 1대와 replica 1대에서 최소 replica 수를 1로 두면 replica를 점검하려고 내리는 순간 쓰기가 막힐 수 있다. 데이터 보호 목적에는 맞지만, 점검 중 쓰기를 계속해야 한다는 요구와 충돌한다. replica가 2대이고 최소 수가 1이면 한 대 점검 동안 나머지가 정상이라는 조건 아래 여유가 생긴다. 단순 대수뿐 아니라 실제로 동기화 완료된 상태인지 확인해야 한다.

운영자는 다음 세 가지 선택을 문서화한다.

- 안전 조건을 유지한 채 충분한 replica를 확보하고 점검한다.
- 쓰기 중단을 서비스의 계획된 유지보수로 받아들인다.
- 위험을 명시적으로 승인받아 제한을 일시 완화하고, 복원 조건과 감시를 둔다.

세 번째를 장애 때 습관적으로 실행하면 안전장치는 가장 필요할 때 항상 꺼지는 장식이 된다. `NOREPLICAS` 오류를 없애는 것이 목적이 아니라 왜 보호 조건이 깨졌는지 고치는 것이 우선이다. 네트워크 오류, 인증 실패, replica 자원 부족, 전체 동기화 반복 중 어느 경로인지 진단한다.

클라이언트는 이런 오류를 무제한 즉시 재시도하지 않는다. 원인이 몇 초 이상 지속되면 재시도 폭증이 primary와 네트워크를 더 바쁘게 만든다. 지수 백오프, 최대 재시도 시간, 업무 큐 또는 명확한 실패 응답을 설계한다. 시간 초과와 명시적 쓰기 거절은 의미가 다르므로 같은 예외로 뭉뚱그려 처리하지 않는다.

## 7. 인증: masterauth와 masteruser를 올바른 방향에 두기

복제 연결은 일반적으로 replica가 primary로 연결을 시작한다. 따라서 replica가 primary에 인증할 자격 증명을 가져야 한다. `masterauth`라는 이름의 설정은 **replica가 상위 서버에 제시할 비밀번호**다. replica에 들어오는 애플리케이션 연결의 비밀번호를 정하는 설정과 다르다.

Redis 6부터 ACL 사용자 이름을 사용하는 인증이 도입되었다. 지원 버전에서는 `masteruser`로 복제용 사용자 이름을 지정하고 `masterauth`에 그 비밀을 전달할 수 있다. `requirepass` 기반의 이전 방식은 default 사용자 인증과 관련된다. 실제 사용 방식은 설치된 버전과 ACL 구성을 확인한다. Redis 7.2의 공식 예제 설정에서도 이 두 설정과 인증 방향을 확인할 수 있다. [버전 고정 공식 설정 예제](https://raw.githubusercontent.com/redis/redis/7.2/redis.conf)

개념적인 replica 설정은 다음과 같다. 꺾쇠 안의 값은 실제 값이 아니라 설명용 자리표시자다.

```conf
replicaof <primary-private-address> <primary-port>
masteruser <replication-user>
masterauth <secret-from-approved-secret-store>
replica-read-only yes
```

공식 ACL 문서는 복제용 사용자에게 필요한 명령으로 `PSYNC`, `REPLCONF`, `PING`을 설명한다. 애플리케이션의 모든 키 접근이나 광범위한 관리 권한을 복제 계정에 부여할 필요는 없다. 그러나 복제 권한 자체로 데이터 전체를 전달받을 수 있으므로 이를 낮은 민감도의 계정으로 취급해서도 안 된다. “일반 GET 권한이 없으니 데이터 유출 위험도 없다”는 결론은 틀리다. [공식 ACL의 복제 계정 설명](https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/)

비밀번호를 명령행 인자로 그대로 넣으면 셸 기록과 프로세스 관찰에 노출될 수 있다. 운영 예시를 블로그에 옮길 때도 비밀을 가린다. 인증은 암호화를 뜻하지 않으므로 복제 구간의 TLS 여부도 별도 확인한다. 인증 실패가 나면 무작정 `+@all`을 주기보다 잘못된 사용자, 비밀번호, 명령 권한, 대상 주소, TLS 설정을 나누어 확인한다.

## 8. replica의 maxmemory가 예상과 다른 이유

primary에서 키를 eviction하는 결정은 복제 스트림으로 전달되어 replica가 같은 논리 상태를 따라가게 한다. replica가 제멋대로 다른 키를 축출하면 다음 명령의 입력 상태가 달라질 수 있다. 이런 이유로 기본적인 replica 동작은 `maxmemory`를 독립적인 축출 한도로 적용하지 않는 방향이다. `replica-ignore-maxmemory`가 관련 설정이다.

`replica-ignore-maxmemory yes`라는 동작을 메모리가 무한하다는 뜻으로 읽으면 안 된다. OS와 컨테이너는 여전히 물리 한도를 가진다. replica의 버퍼, allocator 상태, 로딩 중 두 데이터셋의 겹침 등으로 primary보다 더 큰 순간 메모리가 필요할 수 있다. primary의 maxmemory와 같은 RAM만 주면 충분하다고 단정하지 않는다.

`replica-ignore-maxmemory no`로 바꾸면 메모리 문제를 해결하는 것처럼 보일 수 있지만 독립적인 축출이 데이터 관계에 미칠 영향을 이해해야 한다. 정상 복제본 운영에서 먼저 할 일은 충분한 자원 확보, 버퍼와 지연 원인 분석, 데이터 모델·primary 한도 검토다. 안전하지 않은 독립 축출을 일반적인 용량 관리 방법처럼 적용하지 않는다.

승격 뒤도 중요하다. replica가 primary로 바뀌면 쓰기를 직접 받고 해당 역할의 메모리 정책을 적용한다. 평소 무시되던 한도가 승격 직후 쓰기 거절 또는 대량 eviction의 원인이 될 수 있다. 따라서 승격 후보는 현재 복제 상태뿐 아니라 **승격 후 적용될 maxmemory와 정책, 영속성, 디스크, 인증 구성**까지 검증해야 한다.

## 9. 만료는 왜 원본 중심으로 전파되는가

TTL은 시간이 지나면 키를 유효하지 않게 하는 기능이다. replica마다 독립적으로 물리 삭제를 결정하면 시계와 실행 시점 차이 때문에 상태가 갈라질 수 있다. Redis는 primary가 만료·축출 효과를 복제 스트림에 전달하게 하여 데이터 상태를 맞추는 방향으로 동작한다.

그렇다고 replica 읽기가 만료된 값을 무조건 돌려준다는 뜻은 아니다. 논리적으로 만료된 키를 읽기에서 없는 것으로 취급하는 동작과 메모리에서 실제 제거하는 시점은 구분된다. primary의 만료 효과가 아직 전달되지 않아 메모리에 남은 키도 읽기에서 보이지 않을 수 있다. 그래서 메모리와 키 개수, 조회 결과를 항상 같은 의미로 해석하지 않는다.

복제본이 primary로 승격되면 독립적으로 만료를 관리하는 역할을 맡는다. 따라서 시간 동기화와 시스템 시계 운영도 중요하다. 원문에는 Lua 실행과 만료의 관계에 대한 설명이 있지만, 스크립트 복제 방식은 버전에 따라 발전했으므로 “모든 버전에서 스크립트 문자열을 그대로 전달한다”는 일반화는 피한다. 운영에서 필요한 핵심은 스크립트의 원자적 실행 경계와 복제되는 효과를 해당 버전 기준으로 이해하는 것이다.

TTL을 한 서버에서 확인하고 다른 서버의 키 개수를 즉시 비교하여 손상이라고 결론 내리지 않는다. 먼저 같은 시점과 역할인지, 복제 연결이 정상인지, 논리 만료와 실제 정리 중 무엇을 관찰하는지 확인한다. 복제 지연과 정상적인 만료 처리 차이를 구분하는 것이 진단의 시작이다.

## 10. NAT와 컨테이너: 연결 주소와 알려 주는 주소가 다르다

NAT는 Network Address Translation, 즉 네트워크 주소 변환이다. 컨테이너 내부에서 Redis는 6379 포트로 듣지만 호스트에서는 26379로 전달할 수 있다. primary가 관찰한 replica의 접속 주소와, Sentinel이나 클라이언트가 실제로 접속해야 할 주소가 다를 수 있다.

`replica-announce-ip`와 `replica-announce-port`는 replica가 자신의 접근 주소를 알릴 때 사용하는 설정이다. 이것은 bind 주소를 바꾸거나 방화벽에 구멍을 내거나 네트워크 경로를 자동 생성하는 기능이 아니다. “명함에 적을 주소”를 정하는 일에 가깝다. 잘못된 주소를 적으면 복제는 연결되어 있어도 발견된 replica에 접근하거나 승격 뒤 접속하는 단계에서 실패할 수 있다.

주소 검증은 primary에서만 하면 안 된다. Sentinel이 있는 위치, 애플리케이션이 있는 위치, 운영 관리망에서 각각 접근 가능한지 확인한다. 내부 IP를 외부 클라이언트에 알려 주거나, 외부 IP를 내부 네트워크에서 접근할 수 없는 구조일 수 있다. TLS를 사용하면 알려 주는 호스트 이름과 인증서 검증 기준도 맞아야 한다.

운영 점검표에는 “현재 복제 연결 성공”과 “광고된 주소로 실제 연결 성공”을 다른 항목으로 둔다. 전자는 이미 만들어진 방향의 연결을 검증하고, 후자는 장애 전환과 서비스 발견에 필요한 새 연결을 검증한다. 두 가지를 하나의 초록색 상태로 뭉치면 failover 때만 드러나는 장애를 놓친다.

## 11. 격리 실습: read-only와 쓰기 보호를 관찰하기

이 실습은 Redis 7.x 계열에서도 사용할 수 있는 설정을 기준으로 하며, 설치 버전의 지원을 먼저 확인한다. **일회용 로컬 서버 두 대만** 만든다. primary 포트는 16390, replica 포트는 16391다. 영속성은 실습을 위해 끈다. 이 구성은 운영 권장안이 아니며, 특히 빈 primary가 자동 재시작하면 replica까지 빈 상태를 따라갈 위험이 있으므로 primary를 중간에 재시작하지 않는다.

### 11.1 두 설정 파일 준비

첫 번째 터미널에서 실행한다. 루프백만 열고 다른 네트워크에는 노출하지 않는다.

```bash
LAB=$(mktemp -d /tmp/redis-repl-ops.XXXXXX)
mkdir "$LAB/primary" "$LAB/replica"
printf '실습 경로: %s\n' "$LAB"
cat > "$LAB/primary.conf" <<CONF
bind 127.0.0.1
port 16390
protected-mode yes
daemonize no
dir $LAB/primary
save ""
appendonly no
min-replicas-to-write 1
min-replicas-max-lag 3
CONF
cat > "$LAB/replica.conf" <<CONF
bind 127.0.0.1
port 16391
protected-mode yes
daemonize no
dir $LAB/replica
save ""
appendonly no
replicaof 127.0.0.1 16390
replica-read-only yes
replica-serve-stale-data yes
CONF
redis-server --version
redis-server "$LAB/primary.conf"
```

두 번째 터미널에서 쓰기를 시도한다. 아직 replica가 없으므로 조건이 활성화된 상태에서는 `NOREPLICAS` 계열의 쓰기 거절이 예상된다. 정확한 오류 문자열은 버전에 따라 확인한다.

```bash
redis-cli -h 127.0.0.1 -p 16390 SET lab:state before-replica
redis-cli -h 127.0.0.1 -p 16390 INFO replication
```

거절된 쓰기가 반영되지 않았는지도 `GET lab:state`로 확인한다. 이것은 의도적으로 조건을 만족하지 않게 만든 안전한 실습이며 데이터를 삭제하지 않는다.

### 11.2 replica를 연결하고 정상 상태 확인

두 번째 터미널에서 첫 번째 터미널에 출력된 실제 경로를 사용한다.

```bash
LAB=/tmp/redis-repl-ops.실제접미사
redis-server "$LAB/replica.conf"
```

세 번째 터미널에서 상태를 확인한다.

```bash
redis-cli -h 127.0.0.1 -p 16391 INFO replication
redis-cli -h 127.0.0.1 -p 16390 INFO replication
redis-cli -h 127.0.0.1 -p 16391 ROLE
```

replica의 `master_link_status`가 up이고 초기 동기화가 끝났는지, primary가 정상 replica를 인식했는지 확인한다. 첫 연결은 전체 동기화와 설정된 지연이 있을 수 있으므로 정해진 1초가 지나면 성공이라고 가정하지 않는다. 로그와 상태가 충족된 후 다음을 실행한다.

```bash
redis-cli -h 127.0.0.1 -p 16390 SET lab:state replicated
redis-cli -h 127.0.0.1 -p 16391 GET lab:state
redis-cli -h 127.0.0.1 -p 16391 SET lab:state local-write
```

primary 쓰기는 조건 충족 시 성공하고, replica에서 값이 보이게 되는 것이 예상 관찰이다. 즉시 한 번 읽어서 값이 안 보일 수 있다는 점도 비동기 복제의 일부다. 반면 replica에 대한 쓰기는 read-only 오류로 거절되어야 한다. 이 오류를 없애려고 읽기 전용을 끄지 않는다.

### 11.3 replica를 내렸을 때 쓰기 제한 확인

자신이 만든 replica만 정상 종료한다.

```bash
redis-cli -h 127.0.0.1 -p 16391 SHUTDOWN NOSAVE
redis-cli -h 127.0.0.1 -p 16390 INFO replication
redis-cli -h 127.0.0.1 -p 16390 SET lab:state while-alone
```

연결 종료를 primary가 인지하고 조건이 불충족이 되면 쓰기 거절이 예상된다. 이 실습은 정상 연결 종료이므로 네트워크 단절 때의 최대 감지 지연을 측정하지 않는다. 종료 직후의 순간값만 보고 정책이 무효라고 단정하지 말고 상태가 갱신되었는지 확인한다.

두 번째 터미널에서 같은 replica 설정으로 다시 시작한 뒤 링크와 동기화 상태를 확인한다. 조건이 회복되면 primary의 새 쓰기가 성공하는지 확인한다. 이 단계는 replica 재시작과 재연결 시험이지 자동 primary 승격 시험이 아니다. Sentinel은 구성하지 않았으므로 primary 장애 때 자동으로 승격된다고 기대하면 안 된다.

마지막으로 두 실습 서버를 명시적으로 종료한다. replica를 먼저 종료하고 primary를 종료하면 된다.

```bash
redis-cli -h 127.0.0.1 -p 16391 SHUTDOWN NOSAVE
redis-cli -h 127.0.0.1 -p 16390 SHUTDOWN NOSAVE
```

이 글은 위 실습을 실제 수행했다고 주장하지 않는다. 실행할 때는 버전, 상태 변화, 오류, 관찰 시간을 직접 기록한다. 데이터 유실을 증명하려는 실험과 정책이 쓰기를 막는지 보는 실험은 목적이 다르다.

## 12. 장애 진단 순서: 상태에서 원인으로

복제가 끊겼을 때 첫 조치로 `REPLICAOF`를 반복하거나 전체 동기화를 강제하지 않는다. 대상 변경은 데이터셋에 큰 영향을 줄 수 있다. 다음 순서로 읽기 중심 진단을 한다.

1. **역할과 대상**: `ROLE`, `INFO replication`으로 정말 기대한 primary/replica인지 확인한다.
2. **네트워크와 인증**: 연결 실패인지 인증 실패인지 로그에서 구분한다. 주소·포트·TLS·ACL을 확인한다.
3. **동기화 단계**: 연결은 되었지만 전체 동기화가 진행 중인지, 반복 실패하는지 확인한다.
4. **진행 차이**: 같은 복제 이력인지 확인한 후 offset 변화와 처리 속도를 관찰한다.
5. **자원 압력**: replica CPU, 메모리, 디스크, 큰 조회와 클라이언트 버퍼를 살핀다.
6. **서비스 정책**: 오래된 읽기 허용 여부와 최소 replica 쓰기 조건이 현재 증상에 어떻게 연결되는지 확인한다.

`master_link_status:up`은 필요하지만 충분한 증거가 아니다. 링크는 살아 있어도 스트림 적용이 뒤처질 수 있다. 반대로 순간적인 offset 차이는 쓰기가 계속되는 시스템에서 자연스러울 수 있다. 한 시점의 차이보다 변화 추세와 업무상 허용 범위를 본다. primary와 replica의 복제 ID가 다른 상황에서 숫자 offset만 무조건 빼는 것도 피한다.

## 13. 운영 사고 세 가지를 연결해서 보기

**사고 A: 인증 비밀 교체 후 쓰기가 막혔다.** 애플리케이션 인증은 정상인데 replica의 상위 인증 비밀이 갱신되지 않아 복제 링크가 끊길 수 있다. 최소 replica 조건이 깨지면서 primary 쓰기가 거절된다. 보호 기능을 끄기 전에 복제 계정과 비밀 교체 순서를 확인한다. 새 비밀을 병행 허용할 수 있는 방식, replica 재연결 확인, 이전 비밀 폐기 순서를 승인된 절차로 설계한다.

**사고 B: 분석 조회를 replica에 보냈더니 failover 후보가 늦어졌다.** 무거운 조회를 원본에서 떼어내는 것은 도움이 될 수 있지만 replica가 복제 적용과 같은 자원을 공유한다. 쿼리 크기와 빈도, 응답 버퍼, CPU를 제한하고 예비 승격용 replica와 분석용 역할을 분리할지 판단한다. “읽기니까 복제에는 영향이 없다”는 가정이 문제다.

**사고 C: 승격 직후 OOM 오류가 발생했다.** replica 시절에는 maxmemory를 독립적으로 적용하지 않다가 primary가 되면서 작은 한도와 `noeviction` 정책이 영향을 줄 수 있다. 역할 전환 전후 설정을 비교하고, 후보의 자원이 실제 primary 부하를 감당하는지 확인한다. failover 시험은 역할만 바뀌는지 보는 테스트가 아니라 쓰기·영속성·메모리·클라이언트 연결까지 포함해야 한다.

## 상태 읽기 보충. 생존·연결·진행·신선도·승격 준비를 다섯 칸으로 나누기

첫 칸은 생존이다. 프로세스가 살아 있고 기본 명령을 처리하는가? 두 번째 칸은 연결이다. 기대한 primary와 복제 연결이 유지되는가? 세 번째 칸은 진행이다. 새 복제 스트림을 계속 적용하고 따라잡는가? 네 번째 칸은 신선도다. 이 업무 요청이 필요한 버전의 값을 읽을 수 있는가? 마지막 칸은 승격 준비다. 역할이 바뀐 뒤 실제 primary 부하와 정책을 감당하는가?

각 칸은 이전 칸이 초록이라고 자동으로 초록이 되지 않는다. 소켓이 열려도 진행이 멈출 수 있고, 전체적으로 잘 따라와도 지금 막 쓴 특정 값은 아직 없을 수 있다. 모든 데이터를 최신으로 읽을 수 있더라도 승격 후 디스크 쓰기나 인증 구성은 실패할 수 있다. 그래서 건강 점검을 하나의 PING 결과로 끝내기 어렵다.

| 상태 칸 | 대표 질문 | 가능한 관찰 | 이 관찰만으로 남는 한계 |
|---|---|---|---|
| 생존 | 요청을 받을 수 있는가? | 프로세스·PING·오류 | 올바른 복제 대상인지는 모름 |
| 연결 | 기대한 primary와 이어져 있는가? | 역할·링크·주소 | 실제 적용이 충분히 빠른지는 모름 |
| 진행 | 이력을 계속 따라가는가? | 같은 이력의 offset 변화·로그 | 특정 업무의 신선도는 별도 |
| 신선도 | 이 요청의 최소 버전을 만족하는가? | 업무 버전·라우팅 계약 | 장애 후 내구성은 별도 |
| 승격 준비 | 쓰기 역할로 전환해도 되는가? | 자원·구성·클라이언트 검증 | 모든 장애에서 무손실을 증명하지 않음 |

운영 경보도 이 구분에 맞춰 표현하면 조치가 쉬워진다. “Redis 이상”이라는 알림보다 “읽기 후보가 초기 동기화 중이라 제외됐다”와 “최소 replica 조건이 깨져 쓰기를 거절한다”는 알림이 다음 행동을 더 잘 안내한다. 다만 알림을 잘 나누는 것만으로 원인이 확정되는 것은 아니다. 상태와 원인을 구별해 조사한다.


## 읽기 정책 보충. 모든 GET이 같은 신선도를 요구하지 않는다

입고 작업의 통계 화면과 확정 직후의 상세 화면을 비교해 보자. 통계는 최근 몇 초의 변화가 늦게 반영되어도 업무상 허용될 수 있다. 반면 확정 버튼을 누른 직후 다시 대기 상태를 보여 주면 사용자가 버튼을 다시 누르거나 작업이 실패했다고 판단할 수 있다. 둘 다 GET이지만 사용자에게 필요한 의미는 다르다.

이 차이는 읽기 전용 트랜잭션이라는 말만으로 결정되지 않는다. DB의 읽기 전용 표시와 Redis replica 라우팅은 서로 다른 설정과 실행 경로일 수 있다. “수정하지 않는 메서드니까 replica로 보내도 된다”는 분류는 최신성 요구를 빠뜨린다. 읽기 여부와 오래된 결과의 허용 여부를 별도의 속성으로 본다.

가장 이해하기 쉬운 설계는 기능별로 계약을 적는 것이다. 상품 소개는 어느 정도 오래됨을 허용한다. 권한 변경 직후 확인은 최신 근거가 필요하다. 중복 처리 판정은 업무 확정 기록과 연결한다. 통계는 별도 집계 시점에 맞는 결과를 보여 준다. 실제 허용 범위는 서비스가 정하지만, 기술 옵션이 그 값을 대신 정하지는 않는다.

읽기 경로를 바꾸면 장애 시 부하 이동도 바뀐다. replica를 모두 제외한 순간 모든 요청이 primary로 몰리면 쓰기 지연까지 악화될 수 있다. fallback이 있다는 사실과 fallback이 전체 트래픽을 감당한다는 사실은 다르다. 요청 제한과 중요도, 용량을 함께 계획해야 한다. 일관성 정책은 라우팅 설정인 동시에 부하 정책이다.


## Java 사고 실험. 업무 버전으로 오래된 읽기를 구별하기

아래 코드는 실제 Redis 클라이언트가 아니다. 요청자가 필요한 최소 업무 버전과 읽기 후보의 값을 비교해 primary 재조회를 선택하는 작은 정책 모델이다. 이 버전은 애플리케이션이 의미를 정한 번호이며 replication offset이 아니다. Java 21에서 독립 실행한다.

```java
public final class ReadFreshnessLesson {
    enum Target { REPLICA, PRIMARY }
    record Request(boolean replicaAllowed, long minimumBusinessVersion) {
        Request {
            if (minimumBusinessVersion < 0) throw new IllegalArgumentException("version");
        }
    }
    record Replica(boolean connected, boolean initialSyncInProgress,
                   long observedBusinessVersion) {}

    static Target choose(Request request, Replica replica) {
        if (!request.replicaAllowed()) return Target.PRIMARY;
        if (!replica.connected() || replica.initialSyncInProgress()) return Target.PRIMARY;
        if (replica.observedBusinessVersion() < request.minimumBusinessVersion()) {
            return Target.PRIMARY;
        }
        return Target.REPLICA;
    }

    static void expect(Target expected, Target actual, String label) {
        if (actual != expected) throw new AssertionError(label);
    }

    public static void main(String[] args) {
        Request afterWrite = new Request(true, 42);
        expect(Target.PRIMARY, choose(afterWrite, new Replica(true, false, 41)),
                "older than the version returned by the write");
        expect(Target.REPLICA, choose(afterWrite, new Replica(true, false, 42)),
                "minimum version satisfied");
        expect(Target.PRIMARY, choose(afterWrite, new Replica(true, true, 100)),
                "initial synchronization is not a ready candidate");
        expect(Target.PRIMARY, choose(afterWrite, new Replica(false, false, 100)),
                "disconnected candidate excluded by this policy");
        expect(Target.PRIMARY, choose(new Request(false, 0),
                new Replica(true, false, 100)), "primary-only business flow");
        expect(Target.REPLICA, choose(new Request(true, 0),
                new Replica(true, false, 10)), "stale-tolerant example");
        System.out.println("6 read-routing policy cases passed");
    }
}
```

이 모델은 replica에서 읽은 업무 버전이 쓰기 응답의 42보다 작으면 primary 경로를 선택한다. 그러나 실제 구현에는 더 많은 계약이 필요하다. 버전과 값이 같은 상태로 읽혀야 하고, 모든 writer가 같은 버전 규칙을 지켜야 하며, failover 뒤 버전의 의미가 유지되어야 한다. 단순히 숫자 필드를 추가했다고 최신성 보장이 완성되는 것은 아니다.

또한 primary로 재조회해도 해당 업무의 최종 진실이 다른 DB에 있다면 그 DB와의 관계가 남는다. 이 예제의 Target.PRIMARY는 정책 선택의 결과일 뿐, 외부 시스템 전체의 최신성을 선언하는 값이 아니다. 실제 라우팅은 요청 시간 예산과 실패 처리, 연결 대상 확인까지 구현해야 한다.

연결이나 동기화 상태를 읽은 직후 상황이 바뀔 수도 있다. 건강 점검의 한 시점 결과를 영원한 보장으로 사용하지 않는다. 실행 오류와 시간 초과를 처리하고, 응답 데이터의 조건을 가능한 범위에서 확인한다. 사전 후보 선정과 실제 요청 결과 검증은 서로 보완하는 단계다.


## 쓰기 보호 보충. 최근에 대답한 replica와 지금 쓰기를 받은 replica는 다르다

최소 replica 설정은 최근 상태를 보고 새 쓰기를 받아도 되는지 판단하는 보호 조건으로 이해하면 쉽다. 시험장 출입구에서 감독관이 있는지 확인하는 것과, 방금 제출한 답안지를 감독관이 실제로 보관했다고 확인하는 것은 다른 사건이다. 감독관이 근처에 있다는 사실이 특정 답안의 전달 완료를 뜻하지 않는다.

복제에서도 최근 ACK가 있었다면 그 시점까지의 진행을 알 수 있다. 그 뒤 새 쓰기를 받았을 때 그 쓰기가 replica에 도달하기 전에 장애가 생길 수 있다. 따라서 최소 수 조건이 충족되어 쓰기가 성공했다는 사실을 해당 쓰기의 복제 완료 확인으로 바꾸어 말하면 안 된다. WAIT와도 목적을 구별해야 한다.

`min-replicas-max-lag`의 시간은 특정 업무 키의 갱신 나이를 직접 재는 타이머가 아니다. replica의 확인 상태를 판단하는 기준과 관련된다. primary가 쓰기를 거의 만들지 않는 동안의 ACK 최근성과, 대량 쓰기 중의 적용 바이트 차이는 다른 관찰이다. “3초로 설정했으니 모든 값은 3초 이내 최신”이라는 문장은 성립하지 않는다.

조건을 강하게 잡으면 홀로 쓰는 위험 구간을 줄이는 데 도움이 될 수 있지만, replica 점검이나 네트워크 문제로 정상적인 업무 쓰기도 거절할 수 있다. 이것은 보호 장치의 고장이 아니라 정책이 선택한 동작일 수 있다. 오류를 없애기 전에 어떤 조건을 지키려 했는지 확인해야 한다.


## Java 사고 실험. 쓰기 수락 조건과 개별 복제 완료를 분리하기

아래 모델은 최근 상태가 좋은 복제본의 수로 쓰기 수락 여부를 결정한다. Redis의 실제 내부 검사 주기와 모든 설정 의미를 구현하지 않으며, 교육용 정책에서 연결·초기 동기화·최근 ACK를 조건으로 정했다. 정책 판단과 이번 쓰기의 전달 완료가 서로 다른 정보라는 점을 보여 준다.

```java
import java.util.List;

public final class ReplicaWriteGateLesson {
    record Replica(boolean connected, boolean initialSyncComplete,
                   long millisSinceAck) {
        Replica {
            if (millisSinceAck < 0) throw new IllegalArgumentException("negative age");
        }
    }

    static boolean mayAccept(List<Replica> replicas, int minimum,
                             long maximumAckAgeMillis) {
        if (minimum < 1 || maximumAckAgeMillis <= 0) {
            throw new IllegalArgumentException("this model requires an active gate");
        }
        long acceptable = replicas.stream()
                .filter(Replica::connected)
                .filter(Replica::initialSyncComplete)
                .filter(replica -> replica.millisSinceAck() <= maximumAckAgeMillis)
                .count();
        return acceptable >= minimum;
    }

    public static void main(String[] args) {
        Replica ready = new Replica(true, true, 200);
        Replica stale = new Replica(true, true, 5000);
        Replica loading = new Replica(true, false, 100);
        if (!mayAccept(List.of(ready, stale), 1, 3000)) {
            throw new AssertionError("one acceptable replica");
        }
        if (mayAccept(List.of(ready, stale), 2, 3000)) {
            throw new AssertionError("two acceptable replicas required");
        }
        if (mayAccept(List.of(stale, loading), 1, 3000)) {
            throw new AssertionError("no acceptable candidate");
        }
        boolean accepted = mayAccept(List.of(ready), 1, 3000);
        boolean thisWriteAlreadyReplicated = false;
        if (!accepted || thisWriteAlreadyReplicated) {
            throw new AssertionError("gate and per-write delivery must stay distinct");
        }
        System.out.println("accepted=" + accepted);
        System.out.println("this write already replicated=" + thisWriteAlreadyReplicated);
    }
}
```

마지막 두 변수는 의도적으로 다른 정보다. 수락 조건은 만족하지만 새 쓰기의 전달 여부는 아직 확인되지 않았다. 이 상태는 논리적으로 모순이 아니다. 이 구별을 이해하면 최소 replica 조건을 동기 커밋이나 롤백 기능으로 오해하지 않는다.

모델은 minimum이 1 이상인 활성 정책만 다룬다. Redis 제품에서 0이 어떤 설정 의미를 갖는지 구현한 것이 아니다. 설정값의 전체 범위와 교육 모델의 입력 범위를 구분해야 한다. 또한 millis 단위를 사용한 이유는 Java 계산의 편의를 위해서이며 Redis 설정의 단위를 그대로 옮겼다는 뜻이 아니다.

실제 운영에서 필요한 것은 이 함수의 true만이 아니다. 누가 조건을 충족하는지, 왜 나머지가 제외됐는지, 상태가 얼마나 오래 지속됐는지 관측해야 한다. 장애 중 쓰기가 막혔을 때 조건을 무조건 낮추기보다 끊긴 링크와 인증, 동기화 실패, 자원 부족을 구별하는 데 도움이 된다.


## 점검 계획 보충. replica 한 대를 내릴 때 쓰기가 막힐지 미리 계산하기

primary 하나와 replica 하나에서 최소 replica 수가 1이라고 하자. 유일한 replica를 점검하기 위해 종료하면 수락 조건을 만족할 수 없게 될 수 있다. primary가 살아 있고 메모리도 넉넉한데 쓰기가 거절되는 이유가 여기에 있다. 서비스 준비 문서가 노드 생존만 세면 계획된 점검에서도 예상치 못한 장애처럼 보일 수 있다.

replica가 두 대이고 최소 수가 1이라면 한 대를 내리는 동안 다른 한 대가 조건을 충족할 수 있다. 그러나 두 번째가 초기 동기화 중이거나 지연이 크면 단순 대수 계산과 결과가 달라진다. “두 대 있으니 하나 내려도 된다”보다 **현재 수락 조건을 충족하는 후보가 몇 대인지** 확인해야 한다.

점검 절차에는 변경 전 상태, 내릴 대상, 유지해야 할 조건, 예상 오류와 중단 기준, 복귀 후 확인을 적는다. replica를 올린 직후 소켓이 열렸다고 즉시 다음 replica를 내리지 않는다. 초기 동기화와 진행 상태, 서비스 요구에 맞는 준비 조건을 확인한다. 순차 점검에서 이 기다림이 다음 단계의 선행 조건이다.

| 점검 단계 | 확인할 것 | 성급하게 다음으로 가면 생기는 문제 |
|---|---|---|
| 시작 전 | 남을 replica의 실제 준비 상태 | 대수만 맞고 보호 조건은 깨짐 |
| 대상 중지 | 의도한 노드만 내려갔는지·쓰기 영향 | 다른 대상 중지나 예상 밖 오류 확대 |
| 대상 복귀 | 역할·상위 주소·동기화·진행 | 연결만 된 미준비 노드를 정상으로 오해 |
| 다음 노드 점검 | 남은 후보가 조건 충족하는지 | 연속 점검으로 준비된 복제본이 없어짐 |

위험을 받아들이고 제한을 일시 완화해야 하는 운영 상황이 있을 수 있다. 그런 결정은 기존값과 새 값, 허용 시간, 감시와 복원 조건을 갖춘 변경으로 다뤄야 한다. 매번 오류가 보일 때 자동으로 보호를 끄는 대응은 보호 기능을 사실상 무력화한다. 가용성과 데이터 보호 사이에서 무엇을 선택했는지 기록해야 한다.


## 오류 처리 보충. 명시적 거절과 시간 초과를 같은 재시도로 묶지 않기

`NOREPLICAS`처럼 정책상 쓰기가 거절된 응답과, 명령의 결과를 받지 못한 시간 초과는 다르다. 전자는 서버가 조건을 판단해 거절한 결과를 받은 것이다. 후자는 실행되지 않았는지, 실행됐는데 응답을 못 받았는지 불확실할 수 있다. 애플리케이션 예외 계층에서 둘을 모두 “RedisException” 한 가지로 기록하면 필요한 업무 처리가 흐려진다.

명시적 거절이라도 즉시 무제한 재시도가 좋은 것은 아니다. replica가 복구되기까지 몇 초 이상 걸린다면 같은 요청을 밀어 넣는 양만 늘릴 수 있다. 시간 예산, 재시도 횟수, 지수 백오프와 jitter, 기능별 실패 응답을 설계한다. 재시도는 문제를 없애는 기능이 아니라 같은 의존성에 다시 부하를 보내는 행위다.

시간 초과 뒤의 쓰기는 멱등성 계약과 연결한다. 증가나 작업 제출을 다시 실행할 수 있는지, 같은 업무 ID를 유지하는지, 처리 결과를 어디에서 조회할지 정한다. 보호 조건 오류와 결과 불확실을 구분하면 사용자에게 전달할 메시지도 달라질 수 있다. “안전하게 거절됐다”와 “결과 확인이 필요하다”는 다른 상태다.

라이브러리의 자동 재연결도 같은 주의가 필요하다. 연결이 다시 만들어졌다는 사실만으로 업무 요청을 다시 실행해도 된다는 뜻은 아니다. 하위 드라이버가 어떤 명령을 큐에 두거나 재전송하는지, 상위 코드도 다시 시도하는지 확인한다. 여러 계층의 재시도가 겹치면 요청 수가 예상보다 크게 늘 수 있다.


## 인증 보충. 세 종류의 연결을 화살표의 출발점으로 구별하기

복제 환경에는 애플리케이션이 Redis로 들어오는 연결, replica가 primary로 만드는 연결, Sentinel이나 관리 도구가 노드를 확인하는 연결이 있을 수 있다. 각 연결은 출발 주체와 목적, 필요한 권한이 다르다. 같은 비밀번호를 여러 곳에 넣었다고 각 설정의 역할이 같아지는 것은 아니다.

`masterauth`는 replica가 상위에 제시하는 비밀이라는 방향을 먼저 그린다. replica로 들어오는 애플리케이션의 인증을 정하는 값과 다르다. primary에서 앱 로그인은 잘되는데 복제가 끊긴다면 앱 계정만 시험해 보고 인증 전체가 정상이라고 결론 내리면 안 된다. 실제 복제 계정과 방향을 확인해야 한다.

인증 비밀을 교체할 때도 연결별 순서를 설계한다. 한쪽만 새 값으로 바꾸면 replica가 재연결할 때 실패할 수 있다. 기존 연결이 살아 있는 동안 문제가 숨었다가 연결 재생성 시 드러날 수 있으므로, 설정 파일 갱신만으로 검증을 끝내지 않는다. 승인된 방식으로 새 인증을 사용하는 재연결을 확인하고 이전 비밀을 폐기하는 절차가 필요하다.

권한을 광범위하게 열면 인증 오류가 사라질 수 있지만 왜 실패했는지는 남는다. 사용자 이름과 비밀의 불일치, 필요한 명령 권한 부족, 대상 주소 오류, TLS 조건을 나누어 조사한다. 복제 계정은 데이터를 전달받는 역할을 가질 수 있으므로 단순 조회 명령을 직접 허용하지 않았다는 이유로 낮은 민감도로 취급하지 않는다.

또한 인증 성공은 통신 암호화를 의미하지 않는다. 비밀번호를 확인한 상대와 암호화된 경로를 사용하는지, 인증서의 신원을 검증하는지는 별도다. TLS 편에서 다시 다루지만 지금은 인증과 암호화가 다른 질문이라는 점만 정확히 기억해도 된다.


## 주소 보충. 연결에 쓴 주소와 다른 사람에게 알려 주는 주소

NAT와 컨테이너가 등장하면 주소가 두 종류로 보일 수 있다. replica가 primary로 연결할 때 사용한 주소와, 다른 노드에게 “나에게 연결하려면 여기로 오세요”라고 알려 주는 주소다. 이미 만들어진 한 방향의 연결이 성공했다고 모든 위치에서 새 연결을 만들 수 있는 것은 아니다.

주소를 명함으로 비유하면 쉽다. 직원이 본사에 전화하는 데 성공했어도 명함에 잘못된 지점 주소를 적었다면 고객은 그 직원을 찾아오지 못한다. announce 설정은 명함에 적는 주소를 정하는 역할에 가깝다. 방화벽을 열거나 포트 전달 규칙을 만들거나 컨테이너의 bind를 자동 수정하는 기능은 아니다.

확인은 실제 접속 주체의 위치에서 해야 한다. Redis 노드끼리 접근할 수 있는 주소를 애플리케이션도 사용할 수 있는지, Sentinel이 같은 주소로 접근할 수 있는지 나누어 본다. 운영자 노트북에서 연결됐다는 사실이 서버 네트워크에서의 접근성 증거가 되지는 않는다. 네트워크 경로는 출발점에 따라 다르다.

TLS가 있다면 IP와 호스트 이름, 인증서 이름도 연결된다. 접속 가능한 숫자 IP로 바꿨더니 인증서 검증이 실패할 수 있다. 이때 검증을 끄는 방식으로 문제를 덮기보다 광고 주소와 인증서의 신원 계약을 맞춰야 한다. 접속 성공과 올바른 상대에 안전하게 접속하는 것은 다르다.

이 문제는 평상시보다 failover 때 드러나기 쉽다. 기존 연결은 잘 동작했지만 승격된 노드를 새로 발견한 클라이언트가 광고 주소로 연결하지 못하는 것이다. 그래서 장애 전환 시험에는 역할 변경뿐 아니라 새 연결 경로가 포함되어야 한다. 이전 연결을 유지한 읽기 시험만으로는 그 경로를 검증하지 못한다.


## 승격 준비 보충. 예비 서버는 역할 이름만 바뀌는 것이 아니다

replica가 primary가 되면 클라이언트 쓰기를 직접 받고 그 역할의 메모리 정책과 영속성 경로를 사용하게 된다. 평소 복제 적용과 조회만 수행할 때의 자원 그래프가 승격 후 부하를 전부 설명하지 않는다. 쓰기 비율, 디스크 동기화, 재연결, 백업 작업이 함께 달라질 수 있다.

특히 replica에서 독립적으로 적용하지 않던 메모리 한도가 승격 뒤 영향을 줄 수 있다. 작은 한도와 noeviction 정책이 남아 있으면 새 primary에서 쓰기 오류가 발생할 수 있다. 반대로 eviction 정책이 업무 상태에 맞지 않으면 중요한 키가 자원 압력으로 제거될 수 있다. 역할 전환은 설정의 의미를 다시 확인하는 사건이다.

아래 모델은 특정 팀이 정한 승격 준비 계약과 후보의 관측값을 비교한다. Sentinel의 실제 선출 알고리즘이나 자동 승격 명령을 구현하지 않는다. “이 후보는 선출될 수 있다”와 “우리 서비스가 필요한 조건을 갖췄다”를 구별하기 위한 Java 21 예제다.

```java
import java.util.ArrayList;
import java.util.List;

public final class PromotionReadinessLesson {
    record Contract(long requiredHeadroomBytes, long expectedMaxmemoryBytes,
                    String expectedEvictionPolicy, boolean aofRequired) {}
    record Candidate(long observedHeadroomBytes, long configuredMaxmemoryBytes,
                     String evictionPolicyAfterPromotion, boolean aofEnabled,
                     boolean advertisedAddressReachable) {}

    static List<String> evaluate(Contract contract, Candidate candidate) {
        List<String> gaps = new ArrayList<>();
        if (candidate.observedHeadroomBytes() < contract.requiredHeadroomBytes()) {
            gaps.add("insufficient measured headroom");
        }
        if (candidate.configuredMaxmemoryBytes() != contract.expectedMaxmemoryBytes()) {
            gaps.add("different maxmemory contract");
        }
        if (!contract.expectedEvictionPolicy().equals(candidate.evictionPolicyAfterPromotion())) {
            gaps.add("different eviction policy");
        }
        if (contract.aofRequired() && !candidate.aofEnabled()) {
            gaps.add("AOF required by this service contract");
        }
        if (!candidate.advertisedAddressReachable()) {
            gaps.add("advertised address not reachable from application network");
        }
        return List.copyOf(gaps);
    }

    public static void main(String[] args) {
        long mib = 1024L * 1024L;
        Contract contract = new Contract(512L * mib, 2048L * mib,
                "noeviction", true);
        Candidate ready = new Candidate(768L * mib, 2048L * mib,
                "noeviction", true, true);
        Candidate gaps = new Candidate(128L * mib, 1024L * mib,
                "allkeys-lru", false, false);
        if (!evaluate(contract, ready).isEmpty()) {
            throw new AssertionError("matching contract should pass");
        }
        List<String> found = evaluate(contract, gaps);
        if (found.size() != 5) throw new AssertionError("five contract gaps expected");
        System.out.println("ready candidate: passed");
        for (String gap : found) System.out.println(gap);
    }
}
```

AOF를 요구하는 것은 이 예제의 서비스 계약이다. 모든 Redis 용도에서 AOF가 필수라는 제품 규칙을 선언한 것이 아니다. requiredHeadroomBytes도 측정과 계획으로 정했다고 가정한 입력이며, 512 MiB가 보편적인 권장 여유라는 뜻은 아니다. 코드가 정확히 비교하더라도 계약의 입력이 적절한지는 별도로 검증해야 한다.

광고 주소 도달성은 boolean으로 주입했지만 실제 도구는 어느 위치에서 언제 어떤 방식으로 확인했는지 기록해야 한다. 후보가 하나의 시점에서 통과했다고 이후 상태가 영원히 유지되는 것은 아니다. 이 모델은 준비 차이를 드러내는 점검이지 자동 승격 승인이나 장애 안전성의 증명이 아니다.


## 메모리·만료 보충. 복제본이 원본과 다르게 보인다고 바로 손상은 아니다

논리 데이터의 상태와 물리 메모리 지표는 다른 층이다. 같은 키와 값을 따라와도 allocator의 상태, 연결 버퍼, 로딩 경로 때문에 RSS가 다를 수 있다. primary와 replica의 메모리 사용량이 바이트 단위로 같아야 한다는 검증 기준은 적절하지 않다. 무엇을 같은 것으로 비교할지 먼저 정한다.

만료에서도 논리적 부재와 실제 정리를 구분한다. 시간이 지나 읽기에서 없는 값으로 취급되더라도 메모리의 물리 제거 시점은 다른 경로와 연결될 수 있다. replica가 primary의 만료 효과를 따라가는 동작과 읽기에서 만료를 다루는 동작을 한 문장으로 축약하면 모순처럼 보일 수 있다. “GET은 없는데 메모리는 남아 있다”는 관측만으로 누수나 손상을 확정하지 않는다.

그렇다고 모든 차이를 정상으로 넘겨도 되는 것은 아니다. 같은 이력인지, 링크와 적용 상태가 어떤지, TTL과 시계가 어떤지, 버퍼가 계속 커지는지 확인한다. 지표 차이에 설명 가능한 원인이 있는지 조사하는 것과 차이가 있으니 바로 손상이라고 판단하는 것은 다르다. 증거에 맞춰 가설을 좁힌다.

복제본의 maxmemory 관련 동작도 OS 한도를 없애지 않는다. 복제 일관성을 유지하기 위해 독립적인 eviction을 하지 않는 경로가 있어도 물리 메모리와 컨테이너 limit은 남는다. 프로세스가 종료될 때까지 메모리를 무한히 받을 수 있다는 뜻으로 읽지 않는다. 역할별 메모리 예산과 승격 후 정책을 함께 점검한다.


## 장애 조사 보충. READONLY 오류가 오래 이어지면 무엇을 분리해서 볼까

Java 애플리케이션에서 READONLY 오류가 보이면 우선 쓰기 대상이 replica인지와 현재 토폴로지를 확인한다. failover 직후라면 이전 primary와 새 primary의 역할이 바뀌었을 수 있다. 클라이언트가 오래된 주소나 연결을 계속 사용하면 새 쓰기를 잘못된 역할에 보낼 수 있다. 오류를 없애려고 replica의 read-only를 끄면 라우팅 문제를 데이터 불일치 위험으로 바꾸게 된다.

시간을 네 구간으로 나누어 보자. 서버가 장애를 감지하고 새 primary를 정하는 시간, 클라이언트가 변경을 발견하는 시간, 오래된 연결을 교체하는 시간, 실제 업무 요청이 새 연결에서 성공하는 시간이다. “5분 뒤 정상화됐다”는 관측이 있다면 어느 구간이 5분을 차지했는지 확인해야 한다. 서버 승격 자체가 5분이었다고 바로 단정하지 않는다.

로그에는 오류가 난 대상 주소와 역할, 클라이언트 버전과 토폴로지 설정, 재연결과 발견 이벤트, 최초 성공 시각을 연결한다. 인증과 DNS, 광고 주소, 연결 풀 또는 드라이버의 재연결 동작도 후보가 될 수 있다. 특정 라이브러리 버전의 문제라고 결론 내리기 전에 해당 버전의 공식 변경 기록과 재현 조건을 확인한다.

이 절차는 실제 장애의 원인을 미리 확정하는 목록이 아니다. 서버 측 역할 전환과 클라이언트 측 발견을 분리하는 진단 틀이다. 증상이 비슷해도 원인은 다를 수 있으며, 개별 환경의 기록 없이 특정 설정 하나를 만능 해결책으로 제시하면 안 된다.


## 면접 질문과 상세 답변

<details><summary>1. replica-read-only를 켜면 인터넷에 공개해도 안전한가요?</summary>

아니다. 읽기 전용은 일반 데이터 쓰기 실수를 막는 기능이지 인증·명령 권한·네트워크 접근을 통제하는 전체 보안 정책이 아니다. 데이터 읽기 자체가 민감할 수 있고 관리 명령의 허용 여부는 별도 설정과 ACL에 달려 있다. 버전별 기본 보안 제한이 있더라도 read-only만 믿고 노출하면 안 된다. 네트워크 격리, ACL 최소 권한, TLS와 비밀 관리를 함께 적용한다.

</details>

<details><summary>2. min-replicas-to-write 1이면 모든 쓰기가 복제본 한 대에 저장된 뒤 성공하나요?</summary>

그렇지 않다. 이 설정은 최근 상태가 허용 범위 안인 replica가 충분한지 보고 새 쓰기의 수락 여부를 정한다. 그 쓰기 자체가 replica에 적용되었다는 ACK를 기다리는 동기 복제와 다르다. 최근 ACK 이후 새 쓰기를 성공 처리하고 복제 전달 전에 primary가 죽는 구간은 남는다. WAIT나 WAITAOF의 범위와도 구별해야 하며, 어느 방법도 자동으로 전체 시스템을 강한 합의 저장소로 바꾸지 않는다.

</details>

<details><summary>3. min-replicas-max-lag는 데이터가 몇 초 오래되었는지 직접 재나요?</summary>

복제본의 최근 확인 상태를 판단하는 시간 기준이지 모든 키의 업무상 갱신 나이를 계산하는 기능은 아니다. ACK 시각, 스트림 offset 차이, 애플리케이션 데이터의 신선도는 다른 지표다. 쓰기량이 달라지면 같은 바이트 차이도 의미가 달라진다. 따라서 설정값 하나를 “모든 읽기는 3초 이내 최신” 같은 보장으로 해석하면 안 된다.

</details>

<details><summary>4. replica-serve-stale-data no면 강한 읽기 일관성이 생기나요?</summary>

아니다. 주로 연결 단절·동기화 상황에서 오래된 데이터 제공을 제한하는 정책이다. 연결이 살아 있어도 비동기 적용 지연이 남을 수 있다. 변경 직후 읽기가 최신이어야 한다면 primary 읽기, 버전 검증, 명확한 라우팅 전략 등이 필요하다. replica 건강 점검도 PING만으로 판단하지 말고 역할·링크·동기화·지연 상태를 함께 봐야 한다.

</details>

<details><summary>5. replica의 maxmemory가 작아도 primary를 따라갈 수 있는 이유는 무엇인가요?</summary>

기본적으로 replica는 원본과 같은 논리 상태를 유지하기 위해 독립적인 maxmemory 축출을 하지 않는 방향으로 동작한다. 원본의 eviction 결과를 복제받는다. 하지만 물리 메모리는 무한하지 않으므로 OS OOM이나 컨테이너 한도에 걸릴 수 있다. 충분한 여유와 버퍼·로딩 비용을 확보해야 하고, 승격 뒤 적용될 한도와 정책도 검증해야 한다.

</details>

<details><summary>6. masterauth와 replica에 접속하는 클라이언트 비밀번호는 같은 설정인가요?</summary>

아니다. masterauth는 replica가 상위 primary에 연결할 때 제시하는 비밀이다. replica로 들어오는 클라이언트의 인증 정책은 그 replica의 ACL 또는 관련 서버 인증 설정으로 다룬다. ACL 지원 버전에서는 masteruser로 복제 사용자 이름을 지정할 수 있다. 인증 방향을 화살표로 그리면 실수를 줄일 수 있으며, 인증과 TLS 암호화도 서로 다른 층이다.

</details>

<details><summary>7. replica에 임시 키를 써도 어차피 나중에 지워지니 괜찮지 않나요?</summary>

원본과 같은 키를 건드리면 이후 복제 명령의 입력 상태가 달라져 불일치가 생길 수 있다. 로컬 쓰기가 원본으로 합쳐지는 것도 아니며, 사라질 시점이 업무적으로 안전하다고 보장되지 않는다. 승격될 수 있는 replica라면 더 위험하다. 임시 계산은 읽기 전용 명령이나 별도 저장소로 분리하고, read-only 오류를 없애려고 writable replica로 바꾸지 않는 것이 일반적으로 안전하다.

</details>

<details><summary>8. replica-announce-ip를 바꾸면 네트워크 연결 문제도 해결되나요?</summary>

광고하는 주소를 바로잡을 수는 있지만 bind, 방화벽, NAT 경로 자체를 만들지는 않는다. 연결에 사용된 주소와 발견 과정에서 다른 노드에게 알려 주는 주소는 다를 수 있다. Sentinel·클라이언트·관리망 각 위치에서 광고 주소로 실제 접근되는지 검증해야 한다. TLS라면 호스트 이름과 인증서 검증도 맞아야 한다. 복제 링크 성공만으로 failover 후 접근성을 증명하지 않는다.

</details>

<details><summary>9. replica에서 키가 읽히지 않는데 메모리는 남아 있을 수 있나요?</summary>

논리적으로 만료된 키를 읽기에서 없는 것으로 취급하는 것과 실제 메모리 정리 시점은 다를 수 있다. replica는 primary의 만료·축출 효과를 따라가므로 잠시 메모리에 남은 데이터와 읽기 결과가 다르게 보일 수 있다. TTL 경과, 복제 링크와 offset, 키 개수의 의미를 함께 확인해야 한다. 단순히 GET이 nil인데 메모리가 줄지 않았다고 즉시 누수나 손상으로 단정하지 않는다.

</details>

## 추가 면접 문답: 읽기·보호·승격의 계약을 나누기

<details><summary>10. 읽기 전용 메서드는 전부 replica에 보내면 되나요?</summary>

읽기 여부와 오래된 결과 허용 여부는 다르다. 확정 직후 상태 확인이나 권한 변경 확인은 읽기여도 최신 근거가 필요할 수 있다. 통계나 일부 캐시는 일정한 오래됨을 허용할 수 있다. 기능별 신선도 요구를 먼저 정하고 라우팅을 선택한다.

프레임워크의 read-only 표시가 Redis 읽기 경로를 어떤 방식으로 바꾸는지도 실제 구성에서 확인해야 한다. 이름이 비슷한 설정들을 동일한 계약으로 취급하지 않는다. fallback 때 primary가 받을 부하와 요청 시간 예산까지 함께 설계한다.

</details>

<details><summary>11. replica가 두 대인데 한 대 점검 중 쓰기가 막힐 수 있나요?</summary>

남은 한 대가 조건을 충족하지 못하면 가능하다. 초기 동기화 중이거나 연결과 최근 ACK 상태가 정책 밖일 수 있다. 단순 프로세스 대수와 쓰기 수락 조건을 충족하는 복제본 수는 다르다.

점검 전후에 역할과 동기화, 진행 상태를 확인하고 다음 노드를 내릴 통과 조건을 둔다. 오류를 없애려고 최소 수 조건을 습관적으로 끄지 말고, 정책의 목적과 남은 위험을 분명히 판단해야 한다.

</details>

<details><summary>12. 승격 성공을 확인했는데 왜 새 primary가 쓰기를 못 받나요?</summary>

역할 변경과 실제 서비스 준비가 다르기 때문이다. 승격 후 적용되는 메모리 한도와 정책, 디스크와 AOF 상태, 인증, 광고 주소와 클라이언트 연결이 조건을 만족하지 못할 수 있다. replica로 잘 따라왔다는 사실만으로 쓰기 역할의 모든 준비가 끝난 것은 아니다.

시험에는 실제 애플리케이션 위치에서 새 연결을 만들고 작은 업무 동작을 확인하는 단계가 필요하다. 프로세스 역할만 보는 검사와 사용자 요청이 안정적으로 성공하는 검사를 분리한다. 자원 피크와 업무 정합성도 목적에 맞게 확인한다.

</details>

<details><summary>13. READONLY 오류를 없애려고 replica-read-only를 끄면 안 되나요?</summary>

잘못된 쓰기 경로를 writable replica로 받아 주면 원본과 다른 상태를 만들 수 있다. 로컬 쓰기가 primary로 자동 병합되는 구조가 아니므로 오류만 사라지고 더 어려운 불일치가 남을 수 있다. 먼저 현재 역할과 실제 쓰기 대상, 토폴로지 발견과 연결 교체를 확인한다.

특정 실험이나 지원되는 별도 설계의 예외를 일반적인 운영 처방으로 확대하지 않는다. 서버 역할 전환과 클라이언트 반영의 시간선을 분리해 원인을 좁히는 것이 우선이다.

</details>

<details><summary>14. 최근 ACK가 1초 전이면 모든 데이터가 1초 이내 최신인가요?</summary>

ACK의 최근성은 특정 키의 업무 갱신 나이와 같은 지표가 아니다. 어떤 이력 위치까지 확인했는지와 그 뒤 생성된 스트림, 해당 키의 변경 시점과 읽기 경로가 필요하다. 최소 replica의 시간 조건을 모든 읽기의 최신성 상한으로 바꾸면 안 된다.

바이트 차이, 확인 시각, 업무 버전은 서로 다른 질문에 답한다. 요구하는 보장이 무엇인지 먼저 정하고 그에 맞는 관측과 라우팅 정책을 선택한다. 숫자 하나의 단위를 정확히 읽는 것이 출발점이다.

</details>

## 정리와 공식 자료

복제 운영의 핵심은 **연결 상태, 읽기 신선도, 쓰기 수락 조건, 디스크 내구성, 보안 권한을 각각 다른 질문으로 다루는 것**이다. 한 설정이 모든 보장을 제공한다고 생각할 때 사고가 생긴다. 다음 Sentinel 장에서는 이 복제 구조 위에 장애 감지와 승격을 어떻게 올리는지 살펴본다.

- [Redis replication](https://redis.io/docs/latest/operate/oss_and_stack/management/replication/): read-only, 최소 replica 조건, 만료, NAT, replica 메모리 정책.
- [Redis ACL](https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/): 사용자 인증과 복제 계정의 최소 명령 권한.
- [Redis 7.2 공식 redis.conf](https://raw.githubusercontent.com/redis/redis/7.2/redis.conf): masteruser/masterauth, stale-data 등 버전 고정 설명의 예시. 자신의 배포 버전 파일과 비교한다.
- [INFO](https://redis.io/docs/latest/commands/info/), [ROLE](https://redis.io/docs/latest/commands/role/), [WAIT](https://redis.io/docs/latest/commands/wait/): 상태 확인과 복제 확인 명령의 보장 범위.
