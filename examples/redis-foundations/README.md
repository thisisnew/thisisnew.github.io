# Redis 기초 확장판 Java 예제

00~12편의 완전한 클래스를 본문에서 추출했다. Java 21 기준이다.

## 독립 실행 모델

Redis 서버가 필요하지 않다. 로컬 임시 출력 디렉터리를 사용한다.

```bash
javac --release 21 -encoding UTF-8 -d /tmp/redis-foundations \
  LocalKeyValueLesson.java IdempotentStockLesson.java \
  RedisConfigContract.java RedisMemoryBudget.java \
  RedisTextBytes.java RedisBucketAddress.java GoodsLookupPolicy.java RedisSnapshotLesson.java
java -cp /tmp/redis-foundations LocalKeyValueLesson
java -cp /tmp/redis-foundations IdempotentStockLesson
java -cp /tmp/redis-foundations RedisConfigContract
java -cp /tmp/redis-foundations RedisMemoryBudget
java -cp /tmp/redis-foundations RedisTextBytes
java -cp /tmp/redis-foundations RedisBucketAddress
java -cp /tmp/redis-foundations RedisSnapshotLesson
```

GoodsLookupPolicy는 API 입력 검증 클래스이며 main은 없다.

## Spring 예제

GoodsNameCache와 GoodsHashCache는 Spring Data Redis 3.2.0 의존성을 사용하는 프로젝트에 넣는 예제다. 연결 팩토리와 StringRedisTemplate 빈 구성은 실행 프로젝트의 책임이다. 이 두 클래스는 해당 API에 대한 컴파일을 확인했으며 이번 기록은 Redis 통합 실행을 주장하지 않는다. Hash 예제의 TTL 생략과 부분 필드 갱신 의미는 03편에서 설명한다.

## 범위

독립 모델의 synchronized는 단일 JVM 범위다. 분산 원자성이나 장애 후 복원을 검증하지 않는다. 메모리 예산의 입력은 가상 측정값이며 실제 서버 권장 용량이 아니다. 바이트 수 예제는 UTF-8 표현을 검사하며 Redis 객체 전체 메모리를 계산하지 않는다.

실제 실행 결과는 `learning/redis/expansion-code-checks.json`에 기록한다. 전편 두 배 확장은 `learning/redis/expansion-progress.json`의 complete 값으로 별도 관리한다.


## 05~07편 추가 독립 예제

- `AofDurabilityLesson`: 가정한 Redis 버퍼·OS 캐시·내구성 경계와 장애 모델별 생존 상태. 실제 AOF 구현이 아니다.
- `AofRewriteLesson`: 변경 이력을 현재 상태로 재표현해도 결과는 같지만 과거 이력은 달라질 수 있음을 검사한다.
- `BackupChecksumLesson`: 자신이 만든 임시 파일을 스트리밍 SHA-256으로 검사하고 바이트 변경을 감지한다. Redis 파일 형식 검사는 아니다.
- `RestoreBusinessLesson`: 개수·자체 업무 규칙·기준 데이터 일치를 다른 검사로 다룬다.
- `ReplicationWindowLesson`: 한 개의 호환 이력과 유한한 바이트 보관 창의 여섯 경계값을 검사한다. PSYNC 전체 구현이 아니다.
- `ReplicationBacklogPlan`: 가정한 스트림 생성률·단절 시간·여유로 용량 산술을 검사한다. 실제 Redis 설정을 변경하지 않는다.

모든 독립 예제에는 `main`이 있으며 앞의 javac 명령에 파일을 추가해 실행할 수 있다. 전체 클래스와 본문 코드의 일치, Java 21 컴파일 및 main 검사는 다음 스크립트로 재현한다. Spring API 검사를 위해 Spring Data Redis 3.2.0과 Spring Framework 6.1.1의 의존성 JAR 경로를 전달한다.

```bash
python scripts/check-redis-foundations.py \
  --java-home "$JAVA_HOME" \
  --spring-classpath '/path/to/spring-dependencies/*'
```

이 명령은 저장소 루트에서 실행한다. 검사 스크립트는 컴파일 출력을 임시 디렉터리에 만들고 정리하며, 실행 범위와 한계를 JSON으로 기록한다.


## 08편 추가 독립 예제

- `ReadFreshnessLesson`: 업무 최소 버전과 후보 준비 상태에 따른 읽기 경로 선택을 여섯 조건으로 확인한다. 실제 Redis 라우터가 아니다.
- `ReplicaWriteGateLesson`: 최근 ACK 기반의 교육용 수락 조건과 개별 쓰기의 전달 완료를 구분한다. Redis의 내부 검사 주기와 전체 설정 의미를 구현하지 않는다.
- `PromotionReadinessLesson`: 팀이 정한 메모리·정책·AOF·광고 주소 계약과 후보 상태의 차이를 확인한다. Sentinel 선출이나 자동 승격 도구가 아니다.


## 09~12편 Sentinel 예제

- `SentinelPlacementLesson`: 고정된 감시자 집합에서 단일 호스트 상실 뒤 남는 과반·후보 조건.
- `SentinelClientConfiguration`: Spring Data Redis 3.2.0의 Sentinel 연결 구성. 컴파일 검사이며 실제 Spring 재연결 시험은 아니다.
- `SentinelFailoverTimelineLesson`: 서버 역할·첫 사용자 쓰기·복제 여유 회복 시각 구분.
- `SentinelDiscoveryValidationLesson`: 발견 주소와 실제 역할 확인의 차이.
- `SentinelAuthorizationLesson`: 교육용 역할별 허용·거부 표. Redis ACL 명령 집합 전체를 구현하지 않는다.
- `SentinelCandidateOrderingLesson`: 이미 적격성을 계산한 후보의 priority·offset·식별자 비교.
- `SentinelApprovalLesson`: 고정된 알려진 감시자 집합의 정족수와 과반 승인 경계.
- `SentinelEpochLesson`: 구성 최신성과 업무 쓰기 집합의 독립성.
- `SentinelTiltClockLesson`: 시간 관측 이상과 안정 구간의 단순 보호 모델.

실제 로컬 Sentinel 시험은 저장소 루트에서 `python scripts/check-redis-sentinel.py --bin-dir /path/to/redis/src`로 실행한다. 이 시험은 자체 임시 경로와 빈 루프백 포트 다섯 개를 사용하며 정상 primary 종료 뒤 자동 승격·이전 primary 재편입·발견 전용 계정의 허용/거부만 확인한다. 네트워크 분할·전원 장애·Spring 재연결은 확인하지 않는다. 실제 범위와 결과는 `learning/redis/sentinel-checks.json`에 기록한다.


Spring 의존성의 버전을 맞추어 전체 클래스의 검사 경로를 만들려면 Maven 프로젝트도 사용할 수 있다.

```bash
mvn -B -f examples/redis-foundations/pom.xml dependency:build-classpath -Dmdep.outputFile=target/classpath.txt
python scripts/check-redis-foundations.py --java-home "$JAVA_HOME" --spring-classpath "$(cat examples/redis-foundations/target/classpath.txt)"
```

Maven 경로는 Spring Boot 3.2.0의 의존성 관리를 사용한다. Sentinel 서버 통합 시험과 Java 교육 모델 검사는 CI에서 별도 실행되며, 배포는 두 검사와 기존 브라우저 검사 통과를 요구한다. 전편의 두 배 확장이 완료됐다는 뜻은 아니며 `expansion-progress.json`의 complete 값을 확인한다.
