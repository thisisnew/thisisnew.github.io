# Redis 기초 확장판 Java 예제

00~03편의 완전한 클래스를 본문에서 추출했다. Java 21 기준이다.

## 독립 실행 모델

Redis 서버가 필요하지 않다. 로컬 임시 출력 디렉터리를 사용한다.

```bash
javac --release 21 -encoding UTF-8 -d /tmp/redis-foundations \
  LocalKeyValueLesson.java IdempotentStockLesson.java \
  RedisConfigContract.java RedisMemoryBudget.java \
  RedisTextBytes.java RedisBucketAddress.java GoodsLookupPolicy.java
java -cp /tmp/redis-foundations LocalKeyValueLesson
java -cp /tmp/redis-foundations IdempotentStockLesson
java -cp /tmp/redis-foundations RedisConfigContract
java -cp /tmp/redis-foundations RedisMemoryBudget
java -cp /tmp/redis-foundations RedisTextBytes
java -cp /tmp/redis-foundations RedisBucketAddress
```

GoodsLookupPolicy는 API 입력 검증 클래스이며 main은 없다.

## Spring 예제

GoodsNameCache와 GoodsHashCache는 Spring Data Redis 3.2.0 의존성을 사용하는 프로젝트에 넣는 예제다. 연결 팩토리와 StringRedisTemplate 빈 구성은 실행 프로젝트의 책임이다. 이 두 클래스는 해당 API에 대한 컴파일을 확인했으며 이번 기록은 Redis 통합 실행을 주장하지 않는다. Hash 예제의 TTL 생략과 부분 필드 갱신 의미는 03편에서 설명한다.

## 범위

독립 모델의 synchronized는 단일 JVM 범위다. 분산 원자성이나 장애 후 복원을 검증하지 않는다. 메모리 예산의 입력은 가상 측정값이며 실제 서버 권장 용량이 아니다. 바이트 수 예제는 UTF-8 표현을 검사하며 Redis 객체 전체 메모리를 계산하지 않는다.

실제 실행 결과는 `learning/redis/expansion-code-checks.json`에 기록한다. 전편 두 배 확장은 `learning/redis/expansion-progress.json`의 complete 값으로 별도 관리한다.
