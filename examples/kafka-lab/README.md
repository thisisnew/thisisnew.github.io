# Kafka 4.3 학습 코드

Java 21, Maven 3.9+, Kafka 4.3.1. Spring 예제는 Spring Kafka 4.1.1과
Kafka clients 4.3.1을 명시한 학습 조합이다. 운영 Spring Boot BOM을 강제 변경하라는
권장 구성이 아니다. Kafka 프로토콜과 Spring API의 버전을 구분한다.

```bash
mvn test
# 별도 터미널에서 로컬 학습 브로커
# RF=1 학습 환경이며 복제 장애를 검증하지 않는다.
docker run --rm --name kafka-study -p 9092:9092 apache/kafka:4.3.1
# 고유 study.java.* 토픽 1개를 만들어 10건 검증 후 삭제한다.
mvn exec:java -Dexec.mainClass=study.Lab
```

Streams는 입력/출력 토픽을 먼저 만든 후 실행한다. 출력 값은 LongSerializer의
바이너리이므로 String 콘솔 출력으로 숫자를 검증하지 않는다.

```bash
mvn exec:java -Dexec.mainClass=study.CountTopology
mvn exec:java -Dexec.mainClass=study.SpringConsumer
```

SpringConsumer의 입력 토픽은 `study.spring.input`이다. 예제는 출력 후 ack만 하며
DB 멱등성·업무 처리를 구현한 프로덕션 코드가 아니다. 처리 예외는 컨테이너를 멈춘다.
전체 실패를 조용히 skip하는 기본 복구 정책과 구분하기 위한 학습용 선택이다.
`Lab`의 HashSet은 관찰용이며 재시작 후 보존되는 중복 방지 저장소가 아니다.
실제 장애·TLS·SASL·ACL·다중 브로커·MM2·원격 저장 플러그인 실험은 별도 환경이 필요하다.
