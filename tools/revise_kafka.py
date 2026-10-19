"""Build self-contained additions from reviewed, topic-specific teaching notes.
Existing URLs, skin, and original explanations are retained.
"""
from pathlib import Path
import re, html, json
from special_notes import SPECIAL
from kafka_worked_cases import CASES
ROOT=Path(__file__).resolve().parents[1]
def esc(s):return html.escape(s,quote=True)
def p(s):return '<p>'+s+'</p>'
def code(s,lang='text'):return '<pre><code class="language-'+lang+'">'+esc(s.strip())+'</code></pre>'
def section(title,body,id=''):return f'<section'+(f' id="{id}"' if id else '')+'><h2>'+title+'</h2>'+body+'</section>'
def qa(q,a,follow):return '<details class="question"><summary>'+esc(q)+'</summary><div class="answer">'+p('<strong>답변:</strong> '+a)+p('<strong>꼬리 질문과 해설:</strong> '+follow)+'</div></details>'
# All examples of incidents below are constructed learning scenarios, not claims
# about a particular company's production incident.
TOPICS={}
def topic(n,flow,analogy,mechanism,decision,incident,lab,questions,source):
 TOPICS[n]=dict(flow=flow,analogy=analogy,mechanism=mechanism,decision=decision,incident=incident,lab=lab,questions=questions,source=source)
topic(1,
 '업무 트랜잭션 → 이벤트 직렬화 → 파티션 선택 → 리더 기록 → 복제 확인 → 소비 → 업무 저장 → 오프셋 커밋',
 '도서관의 책은 누군가 읽었다고 없어지지 않습니다. 책의 페이지가 offset, 독서 모임의 책갈피가 committed offset입니다. 다만 Kafka의 페이지는 계속 뒤에 추가되고 보존 정책으로 앞부분이 제거될 수 있습니다. 책갈피를 앞으로 옮기는 행위가 실제 독서 완료를 증명하지 않는다는 점까지 비유해야 정확합니다.',
 '레코드는 키와 값이 직렬화된 바이트로 이동합니다. 토픽은 논리 이름이고 저장·순서·복제의 실제 단위는 파티션입니다. 한 레코드는 한 파티션의 로그 위치를 얻으며, 다른 파티션의 같은 offset과는 관계가 없습니다. Producer의 성공은 Consumer의 DB 성공을 의미하지 않습니다. Consumer의 poll은 position을 전진시키지만 DB 작업 완료나 그룹 커밋과는 별개입니다.',
 '주문 단위 순서가 필요하면 orderId를 키로 삼되 파티션 수 변경 시 매핑이 달라질 수 있음을 설계에 반영합니다. 서로 다른 업무가 이벤트를 모두 받아야 하면 서로 다른 group.id를 사용합니다. 같은 업무를 수평 확장할 때 같은 그룹을 사용합니다. 이벤트에 eventId와 schemaVersion을 넣고, 중복 처리와 스키마 변경을 처음부터 실습하는 편이 안전합니다.',
 '입고 완료를 DB에 저장한 뒤 발행 직전에 프로세스가 종료되면 DB에는 완료인데 배송 서비스는 모릅니다. 반대로 발행 후 DB 롤백이면 실제로 없는 완료 사실이 전달됩니다. 두 작업을 단순히 같은 메서드에서 호출하는 것으로 원자성이 생기지 않습니다. Outbox는 업무 데이터와 발행할 의도를 같은 DB 트랜잭션에 저장하고, 전달 과정의 중복은 eventId로 방어하는 설계입니다.',
 'study.intro 토픽을 만든 뒤 서로 다른 두 그룹으로 콘솔 Consumer를 실행합니다. 세 건을 전송하고 양쪽에서 모두 보이는지 확인합니다. 같은 그룹의 두 번째 Consumer를 추가한 뒤 파티션 배정을 비교합니다. 종료·재시작 전후 CURRENT-OFFSET을 기록합니다. 예상은 독립 그룹은 각각 읽고, 같은 그룹은 파티션을 나눠 맡는다는 것입니다.',
 [('이벤트 발행이 성공했는데 주문 처리가 끝났다고 응답해도 되나요?','발행 성공이 보증하는 경계와 사용자에게 약속한 업무 완료 경계를 구분해야 합니다. 비동기 접수 완료라면 그 상태를 응답하고 후속 상태 조회를 제공할 수 있습니다.','후속 처리가 영구 실패하면 보상, 재처리, 사용자 상태 표시가 필요합니다.'),('로그가 남아 있는데 왜 재처리가 안 되나요?','새 Consumer가 유효한 기존 그룹 커밋에서 시작하거나 latest 초기 위치를 택했을 수 있습니다. 보존 여부와 시작 위치를 따로 조사합니다.','auto.offset.reset은 매 시작마다 모든 과거 이벤트를 읽는 스위치가 아닙니다.')],
 ['getting-started/introduction/','getting-started/quickstart/','apis/','design/design/'])
topic(2,
 '작은 레코드 축적 → 파티션별 배치 → 압축 → 네트워크 전송 → 순차 로그 추가 → 페이지 캐시 재사용',
 '택배 한 개마다 트럭을 보내면 출발 비용이 큽니다. 배치는 같은 방향의 택배를 묶어 운송 비용을 나눕니다. 하지만 트럭이 찰 때까지 영원히 기다리지는 않으므로 대기 상한이 필요합니다. Kafka도 파티션별 배치와 linger.ms를 사용하지만, 혼잡으로 생기는 전체 지연을 linger만으로 제한하지는 못합니다.',
 '로그 추가는 임의 위치를 갱신하는 것보다 순차 I/O에 유리합니다. OS 페이지 캐시는 최근 로그를 메모리에 유지하므로 뒤따라오는 Consumer가 매번 디스크를 읽지 않아도 됩니다. Producer·Broker·Consumer가 배치 형식을 공유하면 네트워크 왕복과 처리 비용을 여러 레코드에 분산할 수 있습니다. 압축은 중복 필드가 많은 배치에서 유리하지만 CPU 비용과 배치 크기, 데이터 특성에 따라 효과가 달라집니다.',
 '처리량만 높이고 지연을 무시하면 사용자 요청 경로가 느려집니다. p50뿐 아니라 p95·p99 지연, bytes/sec, CPU, 요청 크기, 오류율을 같은 조건에서 측정합니다. 공식문서의 과거 디스크 수치는 설계 동기의 예시이지 오늘의 서버 처리량 보증이 아닙니다. 복제본 수를 줄여 얻은 성능은 내구성 조건이 달라진 결과이므로 같은 실험으로 비교할 수 없습니다.',
 'Producer 전송 건수는 늘었는데 DB 반영이 더 느려졌다고 합시다. Kafka 병목이 개선되면서 DB 연결풀이 포화된 상황일 수 있습니다. Consumer concurrency를 더 올리면 잠금 경합과 재시도만 늘 수 있습니다. 구간별 대기 시간을 나누고 최종 업무 완료량으로 병목 이동을 검증해야 합니다.',
 '동일한 레코드 1만 건에 대해 linger.ms=0과 5, compression.type=none과 lz4를 교차 비교합니다. 전송 시작부터 모든 Future 완료까지 시간을 재고 bytes/sec와 오류 수를 함께 기록합니다. 한 번에 한 변수만 바꾸고 워밍업을 분리합니다. 로컬 결과를 운영 처리량 산정으로 곧바로 복사하지 않습니다.',
 [('디스크에 저장하는데 어떻게 빠른가요?','순차 로그 추가, 배치, 페이지 캐시, 효율적인 전송 경로를 함께 사용하기 때문입니다. 저장을 생략해서 빠른 것은 아닙니다.','콜드 데이터 재처리와 최신 데이터 소비는 캐시 적중률이 달라 같은 성능이 나오지 않을 수 있습니다.'),('acks=all이면 매 요청마다 fsync하나요?','복제 확인과 물리 디스크 flush는 서로 다른 축입니다. acks=all은 ISR 복제 조건과 관련됩니다.','모든 사본의 동시 전원 상실 같은 장애는 복제 배치와 저장장치 정책까지 따져야 합니다.')],
 ['design/design/','implementation/log/','implementation/network-layer/'])
topic(3,
 '소켓 수신 → 요청 큐 → 요청 처리 → 로그 append/fetch → 응답 큐 → 소켓 송신',
 '식당 접수 직원과 요리사는 하는 일이 다릅니다. 접수 직원만 늘려도 주방이 막혀 있으면 음식은 빨라지지 않습니다. Broker도 네트워크 수신, 요청 처리, 디스크·복제 대기를 분리해 관찰해야 합니다. 실제 내부 스레드와 큐는 버전·요청 유형별로 다르므로 비유를 스레드 개수 공식으로 사용하면 안 됩니다.',
 '파티션 로그는 하나의 무한 파일이 아니라 세그먼트 묶음입니다. offset index는 논리 offset에 가까운 파일 위치를 찾고, 그 지점부터 스캔하여 레코드를 찾도록 돕는 희소 인덱스입니다. time index는 시간 기반 탐색에 사용됩니다. 인덱스의 모든 엔트리가 모든 레코드와 일대일 대응하는 B+Tree라고 생각하면 틀립니다. 활성 세그먼트가 roll되어야 보존·정리 대상이 될 수 있으므로 세그먼트 설정은 삭제 지연과 파일 개수에도 영향을 줍니다.',
 'TLS 사용 시 Kafka의 일반적인 sendfile 경로를 그대로 사용할 수 없습니다. 그래서 zero-copy라는 말만 듣고 암호화한 클러스터의 CPU 사용량이 동일하리라 가정하면 안 됩니다. 브로커 힙을 늘리면 오히려 페이지 캐시에 쓸 메모리가 줄 수 있습니다. 먼저 request queue time, local processing time, remote/replication wait, response time을 나눠 병목을 찾습니다.',
 '장기 보관 토픽을 처음부터 읽는 작업이 시작되자 정상 실시간 Consumer도 느려졌다면 캐시 오염, 디스크 읽기 경쟁, 네트워크 경쟁을 함께 봅니다. 디스크 사용률만 낮다고 I/O가 정상인 것은 아닙니다. await와 처리량, 장치 제한을 확인하고 재처리 속도를 제한합니다.',
 '실습용 데이터 디렉터리에서만 kafka-dump-log.sh로 닫힌 세그먼트를 확인합니다. 첫 offset과 마지막 offset, 레코드 수, 파일 크기를 기록합니다. 압축 토픽에서는 offset 차이와 레코드 개수가 같지 않을 수 있습니다. 운영 로그 파일을 텍스트 에디터로 수정하거나 세그먼트 일부만 지우는 실습은 하지 않습니다.',
 [('offset으로 파일의 몇 바이트인지 바로 계산할 수 있나요?','가변 길이 레코드, 배치 압축, offset 공백 때문에 단순 곱셈으로 계산할 수 없습니다. 세그먼트와 인덱스로 범위를 좁힙니다.','offset 연속성과 파일 바이트 연속성은 같은 개념이 아닙니다.'),('네트워크 스레드를 늘리면 지연이 줄까요?','네트워크 수신이 실제 병목일 때 검토합니다. 요청 큐나 디스크·복제 대기가 원인이면 수신만 빨라져 대기가 늘 수 있습니다.','튜닝 전후 어떤 지연 구간이 줄어야 가설이 맞는지 미리 정해야 합니다.')],
 ['implementation/network-layer/','implementation/message-format/','implementation/log/','design/design/'])
topic(4,
 'send 호출 → 직렬화·메타데이터 → 버퍼 적재 → 배치 송신 → 응답 또는 재시도 → Future 완료',
 '등기우편 접수증을 받는 것과 수취인이 업무를 끝내는 것은 다릅니다. acks는 Kafka가 전송 성공을 언제 알릴지에 관한 규칙입니다. Producer 버퍼에 넣었다는 사실, 리더가 기록했다는 사실, 복제가 충족됐다는 사실, 최종 업무 완료를 순서대로 구별해야 합니다.',
 'acks=all은 복제 계수 숫자만큼 무조건 응답을 기다린다는 뜻이 아니라 현재 ISR의 복제 조건과 연결됩니다. min.insync.replicas는 이 모드에서 쓰기를 허용할 최소 ISR 수입니다. RF=3, minISR=2에서 ISR이 1로 줄면 정상적인 쓰기 성공을 기대하지 않습니다. 전송 도중 실패 응답이나 타임아웃이 나도 일부 데이터가 기록되었을 수 있어 결과 불명 상태를 처리해야 합니다. 멱등 Producer는 producer id·epoch·partition sequence로 전송 재시도의 중복을 다루며 업무 이벤트 두 번 생성까지 막지는 않습니다.',
 'delivery.timeout.ms는 linger와 요청·재시도에 쓸 전체 전달 시간을 고려하는 제한이고 max.block.ms는 send의 메타데이터·버퍼 대기 같은 호출 지연을 제한합니다. serializer 내부 실행 시간을 모두 포함한 전역 타임아웃으로 이해하면 안 됩니다. Kafka 4.3 Producer 설정에서 linger.ms 기본값은 5ms입니다. 예전 버전의 0ms를 모든 버전에 적용하지 않습니다. 동기 get을 매 건 호출하면 배치 이점을 약화시킬 수 있습니다.',
 '응답을 못 받은 앱이 새 eventId로 같은 입고 완료를 다시 보내면 Producer 멱등성이 켜져 있어도 별개의 레코드입니다. 같은 업무 요청에는 안정적인 eventId를 유지하고 Consumer에서 유일 제약으로 검증합니다. TimeoutException을 곧바로 미기록 판정으로 바꾸면 중복·역전 복구가 어려워집니다.',
 'study.producer에 key=A를 100번 보내고 각 Future의 partition과 offset을 출력합니다. 멱등성을 끄는 실험은 별도 설정 파일에서만 수행합니다. 브로커를 잠시 차단하고 Future가 언제 실패하는지 관찰하되, 실패했던 eventId가 실제 로그에 없는지는 다시 읽어 별도로 확인합니다.',
 [('acks=all과 minISR=2면 딱 두 대가 쓰면 응답하나요?','minISR은 쓰기 허용 최소 조건입니다. 현재 ISR 전체에 관한 복제 확인과 숫자 2를 혼동하면 안 됩니다.','ISR이 세 대일 때와 두 대일 때의 요청 대기 조건을 나눠 설명하세요.'),('enable.idempotence=true면 모든 중복이 없어지나요?','동일 Producer 세션의 프로토콜 재시도를 보호하는 범위와 업무 중복 발행은 다릅니다.','프로세스 재시작 후 같은 비즈니스 이벤트를 다시 생성하는 경우 Consumer 멱등성이 여전히 필요합니다.')],
 ['configuration/producer-configs/','design/design/'])
topic(5,
 '그룹 참여 → 파티션 할당 → fetch/poll → position 전진 → 업무 처리 → 다음 offset 커밋',
 '책을 100페이지까지 빌려 왔어도 100페이지까지 읽은 것은 아닙니다. position은 가져올 다음 위치이고 커밋은 복구 책갈피입니다. Spring의 acknowledgment는 책갈피 갱신 요청이지 특정 레코드를 서버 큐에서 삭제하는 행위가 아닙니다.',
 'poll이 100~109를 반환하면 position이 110으로 진행할 수 있습니다. 업무가 104까지 성공했다고 전체 position 110을 커밋하면 105~109를 놓칠 수 있습니다. 파티션별로 연속 성공한 경계의 다음 offset을 커밋해야 합니다. KafkaConsumer는 일반적으로 스레드 안전하지 않으므로 한 Consumer를 임의의 여러 스레드에서 동시에 호출하지 않습니다. wakeup 같은 문서화된 예외와 정상 API 호출을 구별해야 합니다.',
 'auto.offset.reset은 유효한 커밋이 없거나 범위를 벗어난 경우의 초기 위치 정책입니다. earliest로 설정했다고 매 재시작마다 처음부터 읽지 않습니다. classic 그룹과 group.protocol=consumer 그룹은 heartbeat·session timeout을 제어하는 설정 위치가 다릅니다. max.poll.interval.ms는 업무가 너무 오래 걸려 poll 호출이 지연되는 상황과 연결됩니다. max.poll.records를 낮추는 것만으로 외부 DB의 영구 정지를 해결할 수는 없습니다.',
 'MANUAL ack를 생략한 채 정상 반환하면 같은 프로세스에서 position은 계속 진행할 수 있습니다. 뒤 레코드의 ack로 앞 offset까지 커밋될 수도 있습니다. 스위치 OFF는 재전달 보장이 아닙니다. 처리 중단 요구라면 pause/resume, 오류 전파와 검증된 오류 처리기를 사용하고 Consumer position·committed offset·할당을 함께 기록합니다.',
 '파티션 하나에 10건을 넣고 auto commit을 끈 Java Consumer에서 poll 반환 직후 position과 committed를 출력합니다. 세 건 처리 후 강제 종료하고 재시작합니다. 커밋 전이면 재수신, 성공한 다음 offset을 커밋했다면 그 위치부터 시작하는 것을 비교합니다. 신규 그룹으로 반복해야 이전 실험 커밋에 영향을 덜 받습니다.',
 [('lag가 0이면 DB 작업도 전부 완료됐나요?','커밋 기준 lag가 0이어도 별도 비동기 큐나 너무 이른 커밋 때문에 업무가 남을 수 있습니다.','최종 DB 완료 시각과 eventId 기준 미완료 수를 별도 계측해야 합니다.'),('ack를 안 하면 다음 poll에서 반드시 다시 오나요?','그렇지 않습니다. 현재 position과 커밋은 다르며 프레임워크 오류 처리·seek 동작까지 확인해야 합니다.','나중 레코드의 누적 커밋이 앞 실패를 덮는 시간선을 그려 설명하세요.')],
 ['configuration/consumer-configs/','ops/consumer-rebalance-protocol/','design/design/'])
topic(6,
 '토픽 생성 → 파티션·복제 배치 → 로그 보존/정리 → 그룹별 진행 관리',
 '여러 창구로 일을 나누면 병렬로 처리할 수 있지만, 같은 고객이 어느 창구에 가는지가 바뀌면 이전 순서와 섞입니다. 파티션 증가는 창구를 늘리는 작업이고, 기존 레코드를 새 창구로 옮겨 정렬해 주는 작업이 아닙니다.',
 '보존 크기 retention.bytes는 토픽 전체 총합이 아니라 파티션 단위 제한입니다. retention.ms와 함께 설정하면 먼저 충족되는 삭제 조건을 고려합니다. 실제 삭제는 세그먼트 단위로 진행되므로 시간 만료 순간 개별 레코드가 즉시 사라지는 모델이 아닙니다. cleanup.policy=compact는 키별 최신 값을 남기는 백그라운드 정리이며, 실행 직전에는 중복 키의 과거 값도 보일 수 있습니다. tombstone은 null value의 삭제 표식이며 문자열 "null"과 다릅니다.',
 '키 기반 순서와 처리량 목표를 함께 만족하는 파티션 수를 부하 시험으로 고릅니다. RF 변경은 단순 토픽 속성 변경으로 끝나는 것이 아니라 파티션 복제본 재배치가 필요합니다. 일반 Consumer Group의 할당 단위는 파티션이고, Share Group은 다른 소비 모델입니다. group.id 이름을 같게 한다고 서로 다른 종류의 클라이언트가 무조건 호환되는 것도 아닙니다.',
 'retention.bytes를 전체 10GB라고 생각하고 파티션 20개에 적용하면 예상 총 저장량이 크게 어긋납니다. 반대로 보존 기간이 짧아 정지 중이던 그룹의 오프셋이 log start보다 뒤처지면 재처리할 원본이 사라질 수 있습니다. 복구 목표와 최대 중단 기간을 먼저 정하고 보존·아카이브 예산을 계산해야 합니다.',
 'study.compact라는 별도 토픽에 key=A,value=1, key=A,value=2, key=B,value=3을 전송합니다. 즉시 읽어 세 레코드가 보일 수 있음을 확인합니다. compaction 후에도 offset이 다시 0,1로 정리되지 않는다는 점을 관찰합니다. 짧은 세그먼트 설정은 실습 토픽에만 적용합니다.',
 [('compact 토픽을 읽으면 항상 키당 한 건만 오나요?','정리 전에는 여러 버전이 올 수 있으며 로그를 읽는 스트림 자체가 실시간 조회 테이블은 아닙니다.','Consumer가 최신 상태 테이블을 만들려면 키별 갱신과 tombstone 처리를 구현해야 합니다.'),('파티션을 늘리면 기존 메시지도 분산되나요?','기존 로그는 기존 파티션에 남고 새 발행의 매핑이 달라질 수 있습니다.','키별 순서가 중요하면 이전 파티션의 미처리분과 새 파티션 메시지의 동시 처리까지 고려합니다.')],
 ['configuration/topic-configs/','configuration/group-configs/','design/design/'])
topic(7,
 '현황 수집 → 영향 범위 한정 → 변경안 dry-run → 중단/실행 → 결과 대조 → 복구 검증',
 '책갈피를 뒤로 옮기면 다시 읽을 수 있지만 이미 보낸 택배까지 자동 취소되지는 않습니다. offset reset은 읽기 위치 변경이고 업무 DB·결제·알림의 되돌리기가 아닙니다. 따라서 재처리에는 같은 eventId가 다시 와도 안전한 업무 규칙이 필요합니다.',
 'consumer-groups의 CURRENT-OFFSET, LOG-END-OFFSET, LAG는 파티션별로 봅니다. 그룹이 구독하는 토픽 전체를 합산하면 특정 핫 파티션 문제가 숨습니다. 브로커 장애에서 데이터 리더 선출과 Consumer 그룹 리밸런스는 별개의 제어 흐름입니다. 리더가 바뀌어도 Consumer 프로세스가 반드시 그룹을 다시 구성하는 것은 아닙니다. 파티션 재배치는 원본을 새 브로커로 복제하는 동안 네트워크·디스크를 사용하므로 재시도 폭주와 겹치지 않게 조절합니다.',
 'reset은 대상 그룹을 정지시키고 전후 offset을 파일로 저장한 뒤 dry-run 결과를 검토하는 순서를 사용합니다. 활성 그룹에 대한 제한과 명령 옵션은 설치 버전의 --help로 확인합니다. timestamp reset은 정확한 업무 경계와 일치하지 않을 수 있어 eventId나 업무 시간 범위 대조가 필요합니다. 운영 명령을 블로그에서 복사할 때 토픽과 그룹의 실습 접두사를 먼저 확인합니다.',
 '잘못된 그룹 이름으로 --to-earliest를 실행하면 정상 업무가 전량 재실행될 수 있습니다. 오프셋 복구만 해서는 이미 발생한 외부 부작용을 되돌릴 수 없습니다. 그래서 변경 전 스냅샷, 대상 allowlist, Consumer 중단 확인, 최종 업무 대조를 하나의 작업 단위로 관리합니다.',
 'study.ops 그룹의 기존 오프셋을 describe로 저장합니다. Consumer를 정지하고 --reset-offsets --topic study.ops --to-earliest --dry-run으로 변경 예정 위치만 확인합니다. 명령 출력의 그룹·토픽·파티션이 예상과 같을 때 실습 환경에서만 --execute합니다. 재가동 후 중복 방지 결과를 확인합니다.',
 [('리더 이동과 리밸런스를 왜 구분하나요?','하나는 파티션 복제본 중 데이터 서비스를 담당할 서버를 바꾸고 다른 하나는 그룹 멤버의 파티션 담당을 바꾸기 때문입니다.','리더 장애가 모든 소비 지연의 원인이라고 단정하지 않고 두 제어면 로그를 따로 봅니다.'),('offset만 복원하면 사고가 복구되나요?','이미 실행한 DB 작업·외부 호출이 남기 때문에 그렇지 않습니다.','재처리 전후 eventId 집합과 업무 결과를 대조할 수 있어야 합니다.')],
 ['ops/basic-kafka-operations/','ops/monitoring/','ops/consumer-rebalance-protocol/'])
topic(8,
 '컨트롤러 메타데이터 합의 → 브로커 파티션 서비스 → 원격 로그 계층 → 트랜잭션 상태 전환',
 '회사 조직도와 택배 창고 물건 목록은 서로 다른 장부입니다. KRaft의 메타데이터 로그는 클러스터 구성을 다루고, 토픽 파티션 로그는 업무 이벤트를 담습니다. 컨트롤러가 세 대라고 모든 업무 레코드가 그 세 대에 복제되는 것은 아닙니다.',
 'KRaft quorum은 컨트롤러 다수의 합의로 메타데이터 변경을 관리합니다. 데이터 파티션의 리더·ISR 복제와 구별해야 합니다. Tiered Storage는 닫힌 로그 세그먼트 등을 원격 저장 계층으로 옮겨 로컬 디스크 부담을 낮추지만 실제 플러그인 구현, 원격 메타데이터, 복구 경로의 운영이 필요합니다. Kafka 트랜잭션은 여러 파티션 출력과 Consumer offset을 묶을 수 있으며 read_committed Consumer가 abort된 데이터를 업무 데이터로 읽지 않도록 돕습니다.',
 '컨트롤러 3개는 1개 장애를 견디는 다수 구성의 예시이며 전체 가용성은 브로커 복제와 네트워크 분리에도 의존합니다. 트랜잭션에 DB까지 자동 포함된다고 가정하지 않습니다. 원격 계층을 켰다고 로컬 로그와 복제본이 불필요해지지도 않습니다. 각각의 보장 범위를 따로 쓰고 결합했을 때의 복구 목표를 시험합니다.',
 '열린 트랜잭션이 오래 유지되면 read_committed Consumer의 가시 경계가 막혀 뒤의 정상 레코드 처리도 늦어질 수 있습니다. 단순히 컨슈머 수를 늘려도 이 경계가 앞으로 가지 않습니다. transaction timeout, 소유 Producer, LSO와 high watermark 차이를 조사해야 합니다.',
 '같은 입력에서 하나는 commitTransaction, 다른 하나는 abortTransaction으로 끝나는 출력을 만듭니다. read_uncommitted와 read_committed Consumer 결과를 비교합니다. 정상 종료와 프로세스 강제 종료도 비교해 트랜잭션 미완료가 어떤 지연을 만드는지 기록합니다.',
 [('KRaft 다수 합의와 ISR은 같은 건가요?','대상 로그와 제어 목적이 다릅니다. KRaft는 메타데이터 합의이고 ISR은 데이터 파티션 복제 집합과 관련됩니다.','메타데이터 quorum이 정상이어도 특정 토픽 복제본이 모두 장애일 수 있습니다.'),('Kafka 트랜잭션으로 HTTP 호출도 롤백되나요?','Kafka가 관리하는 레코드·오프셋 범위를 넘어선 외부 부작용은 자동 원복되지 않습니다.','외부 결제에는 별도 멱등 키와 보상·대조 절차가 필요합니다.')],
 ['ops/kraft/','ops/tiered-storage/','ops/transaction-protocol/','ops/eligible-leader-replicas/'])
topic(9,
 '생성 시각 → 브로커 기록 → fetch → 업무 완료 → 커밋 → 대시보드 집계',
 '고속도로 차량 수만 세면 각 차가 얼마나 늦는지 모릅니다. lag는 대기 레코드 위치 차이를 보여 주지만 이벤트의 나이와 업무 마감 위험을 그대로 표현하지 않습니다. 레코드 수, 가장 오래된 이벤트의 나이, 최종 업무 완료 지연을 함께 봐야 합니다.',
 '일반적인 커밋 기준 lag는 log end와 committed offset의 차이로 계산합니다. 클라이언트 fetch lag, read_committed에서의 가시 경계, 모니터링 도구가 사용하는 조회 API에 따라 값의 의미가 달라질 수 있습니다. 트랜잭션 제어 레코드와 compaction으로 offset 차이가 실제 업무 건수와 일치하지 않을 수 있습니다. UnderReplicatedPartitions는 복제 건강 신호이지만 OfflinePartitionsCount처럼 서비스를 못하는 상태와 심각도가 같다고 보면 안 됩니다.',
 'lag 합계만 알람하면 한 파티션 정체를 놓칠 수 있습니다. 파티션 최댓값, 증가 속도, 소비율, 업무 지연 SLO를 결합합니다. 장애가 짧게 지속되는 정상 배포와 장기 정체를 구분하려면 알람 지속 시간과 회복 판정이 필요합니다. 브로커 RequestQueueTime과 처리 지연, 디스크·네트워크 지표를 함께 봐야 Consumer 문제인지 구분할 수 있습니다.',
 'lag가 매초 1000씩 증가하고 생성률 5000/s, 처리율 4000/s라면 소비를 계속해도 뒤처집니다. backlog 60만 건을 처리율 7000/s로 끌어올려도 새 입력 5000/s를 빼면 순감소는 2000/s여서 약 300초가 필요합니다. 이 계산은 일정한 속도라는 가정이며 DB 병목과 파티션 편중이 있으면 어긋납니다.',
 '테스트 Consumer에 의도적인 100ms 처리를 넣고 입력률을 단계적으로 올립니다. group lag, event timestamp 기반 age, DB 성공 수를 10초마다 기록합니다. 커밋을 너무 일찍 하는 변형도 실습하여 lag만 정상일 때 업무 완료 지연이 어떻게 다른지 확인합니다.',
 [('lag가 크면 무조건 장애인가요?','야간 배치처럼 의도된 소비 지연도 있습니다. 업무 SLO와 복구 가능한 보존 시간을 함께 판단합니다.','같은 10만 건도 생성률·레코드 크기·최고령 이벤트 나이에 따라 위험이 다릅니다.'),('복제 지표가 나쁘면 Consumer 증설부터 하나요?','복제 지연과 업무 소비 병목은 구분해야 합니다. 브로커 I/O 부족이면 증설 Consumer가 부담을 더할 수도 있습니다.','ISR 감소 시각과 디스크 지연·네트워크 오류를 먼저 대조합니다.')],
 ['ops/monitoring/','configuration/consumer-configs/','design/design/'])
topic(10,
 '입력 바이트 산정 → 보존·복제 용량 → 브로커별 분산 → 장애 여유 → 부하 시험',
 '냉장고를 물건으로 100% 채우면 문 하나가 고장났을 때 다른 냉장고로 옮길 여유가 없습니다. 브로커 용량도 평상시 평균만으로 잡으면 장애 후 리더 집중과 복제 복구를 감당하기 어렵습니다. 여유율은 특정 숫자가 정답인 규칙이 아니라 장애 시나리오에서 나오는 요구입니다.',
 '대략적인 저장량은 초당 레코드 수 × 평균 저장 크기 × 보존 초 × 복제 계수로 시작합니다. 실제 압축률, 인덱스, 세그먼트 오버헤드, 내부 토픽, 분산 편차, 임시 복제량을 더해야 합니다. 예를 들어 1000건/s, 압축 후 평균 500B, 7일, RF=3이면 약 907.2GB의 복제본 총량입니다. GB와 GiB를 혼용하지 않고 단위를 명시합니다. tiered storage를 쓰면 로컬과 원격 보존을 분리 계산합니다.',
 '브로커 JVM 힙, OS 페이지 캐시, 직접 버퍼, 파일 매핑, 운영체제·에이전트 메모리를 모두 고려합니다. 힙만 서버 메모리 전체로 키우는 것은 캐시와 OS 여유를 없앱니다. Java 지원 여부와 권장 버전, Broker·Client·Connect의 최소 버전은 공식 Java Version 페이지에서 역할별로 확인합니다. 이 교재의 Java 21 예제와 기존 Java 17 브로커의 실행 환경을 혼동하지 않습니다.',
 '평균 디스크 사용률은 낮지만 클라우드 볼륨의 처리량 제한이나 IOPS burst 크레딧을 소진하면 지연이 급등할 수 있습니다. CPU만 보고 Kafka 문제를 배제하면 원인을 놓칩니다. 파일 디스크립터 한도 부족은 파티션·세그먼트 수 증가와 함께 나타날 수 있으므로 오류 로그와 열린 파일 수를 확인합니다.',
 '실제 압축률을 측정한 뒤 계산 시트에 일 입력량, RF, 보존 기간, 재처리 읽기량을 적습니다. 브로커 한 대가 빠진 경우 리더·트래픽 재분산과 복구 복제량을 별도 산정합니다. 캐시가 따뜻한 상태와 오래된 로그를 재생하는 상태의 부하 시험 결과를 비교합니다.',
 [('서버 메모리가 남으면 힙을 크게 하면 되나요?','Kafka는 페이지 캐시에도 크게 의존합니다. 힙 사용량·GC와 OS 캐시·직접 메모리를 함께 보고 결정합니다.','힙 확대 후 디스크 읽기와 p99가 늘면 캐시 감소 가설을 검증합니다.'),('RF=3이면 저장비용만 세 배인가요?','복제 네트워크와 follower 디스크 쓰기, 장애 복구 트래픽에도 영향이 있습니다.','리더 입력량만으로 네트워크와 디스크 용량을 계산하면 부족할 수 있습니다.')],
 ['ops/java-version/','ops/hardware-and-os/','ops/monitoring/'])
topic(11,
 '현재 버전·기능 확인 → 사전 호환 시험 → 한 대씩 바이너리 교체 → 안정성 관찰 → 기능 버전 최종화',
 '휴대전화 앱을 새로 설치하는 것과 파일 저장 형식을 새 버전으로 바꾸는 것은 다릅니다. Kafka도 실행 바이너리를 바꾸는 단계와 클러스터 기능·메타데이터를 최종화하는 단계를 분리합니다. 새 형식을 쓰기 시작하면 이전 프로그램이 그 데이터를 이해하지 못할 수 있으므로 롤백 가능 시점이 다릅니다.',
 '4.3 서버는 KRaft 모드만 지원합니다. 공식 가이드는 KRaft의 소프트웨어·메타데이터 버전이 최소 3.3.x인 조건을 제시하며 ZooKeeper 클러스터는 지원되는 경로로 KRaft 마이그레이션을 먼저 마쳐야 합니다. 브로커 롤링 교체 후 정상 상태를 검증하고 kafka-features로 release version을 최종화합니다. 4.3 메타데이터 변경을 넘는 다운그레이드는 지원되지 않는다는 제한을 먼저 읽어야 합니다. 무조건 바이너리만 되돌리면 복구된다고 가정하면 안 됩니다.',
 '패치 버전도 릴리스 노트를 읽습니다. 공식 4.3.1 안내에는 트랜잭션 복구·Streams 재시작·Admin 리더 API 관련 수정 등이 있으므로 단순 문자열 수정으로 취급하지 않습니다. 클라이언트·Spring 의존성은 서버와 반드시 동시에 바꿀 필요는 없지만, 사용하는 API·인증·그룹 프로토콜의 호환 시험이 필요합니다. inter.broker.protocol.version처럼 과거 ZooKeeper 시대 절차를 그대로 가져오지 않습니다.',
 '브로커 전체를 동시에 재시작해 quorum과 데이터 복제 가용성을 함께 잃었다면 롤링 업그레이드의 전제가 깨집니다. 다음 노드로 가기 전에 ISR 회복, 오프라인 파티션, Producer 오류율, Consumer 업무 지연을 확인해야 합니다. 중간에 실패하면 최종화를 서두르지 말고 현재 기능 버전과 혼합 실행 상태를 기록합니다.',
 '실습 클러스터에서 kafka-features.sh --bootstrap-server localhost:9092 describe 결과를 보관합니다. 클라이언트 Producer/Consumer와 보안 접속을 유지하며 노드 하나씩 교체합니다. 이 장의 학습은 조회부터 시작하며, upgrade --release-version 4.3은 되돌림 제한을 확인한 실습 클러스터에서만 실행합니다.',
 [('브로커 버전이 4.3이면 모든 기능도 4.3인가요?','실행 버전과 클러스터 기능 수준을 따로 확인해야 합니다. 최종화 전 혼합 상태가 존재할 수 있습니다.','최종화가 필요한 이유와 그 이후 되돌림 제한을 설명하세요.'),('ZooKeeper 2.x에서 4.3으로 바로 갈 수 있나요?','4.3은 ZooKeeper 모드를 지원하지 않으므로 해당 출발 버전에서 지원되는 중간 업그레이드·마이그레이션 경로가 필요합니다.','출발 소프트웨어·메타데이터 버전을 모른 채 단일 명령을 제시하면 안 됩니다.')],
 ['getting-started/upgrade/','getting-started/zk2kraft/','operations/kraft/','getting-started/compatibility/'])
topic(12,
 '업무 요구 정의 → 메시지 생산/소비 또는 파이프라인/계산/관리 선택 → API 보장 범위 확인',
 '연필·계산기·운송차·관리 열쇠는 모두 회사 도구지만 대체 관계가 아닙니다. Producer는 기록을 쓰고 Consumer는 읽습니다. Streams는 읽고 계산하는 애플리케이션 라이브러리이고 Connect는 외부 시스템과의 반복적인 이동을 운영하는 프레임워크입니다. Admin은 자원을 관리하는 도구입니다.',
 '4.3 API 문서는 Producer, Consumer, Share Consumer, Streams, Connect, Admin의 여섯 주요 API를 설명합니다. Share Consumer는 Share Group에서 레코드 처리를 협력하는 모델이며 기존 Consumer Group의 파티션 독점 할당 모델과 다릅니다. 기존 KafkaConsumer에서 group.id만 바꾸면 Share Consumer가 되는 것은 아닙니다. 각 API는 언어 독립 바이너리 프로토콜 위에 있으며 프로젝트가 직접 관리하는 Java 클라이언트와 외부 언어 구현의 지원 범위도 다릅니다.',
 '업무 DB 트랜잭션과 세밀하게 연결할 처리는 일반 Consumer와 애플리케이션 코드가 이해하기 쉽습니다. 표준 DB 적재와 CDC는 적합한 Connector가 있는지 먼저 검토하고, Kafka 토픽 사이 집계·조인은 Streams를 검토합니다. 일회성 토픽 조회를 위해 운영 Consumer 그룹을 만들 필요 없이 Admin API를 쓰는 편이 적합합니다. Share 사용은 정확한 릴리스의 지원·운영 조건을 별도로 검증합니다.',
 '데이터를 옮기기만 하는 일을 사용자 정의 Consumer로 모두 구현하면 offset·재시도·설정 변경·모니터링까지 직접 유지해야 합니다. 반대로 복잡한 업무 정합성을 SMT 한 줄로 숨기면 장애 지점을 설명하기 어렵습니다. 도구 선택은 코드 줄 수가 아니라 보장 범위와 운영 책임을 기준으로 판단합니다.',
 '같은 study.apis 토픽을 Producer로 쓰고 Consumer로 읽은 뒤 Admin으로 파티션·복제본을 조회합니다. 별도 Streams 앱으로 값을 대문자로 바꾼 출력 토픽을 만듭니다. 각 프로세스가 같은 브로커에 접속하더라도 역할과 group/application 식별자가 다른 이유를 설명해 봅니다.',
 [('Streams는 별도 Kafka 서버인가요?','Kafka Streams는 애플리케이션에 넣는 Java 라이브러리입니다. 앱 인스턴스를 운영해야 합니다.','브로커 복제 수를 늘리는 것과 Streams 처리 인스턴스를 늘리는 것은 별개입니다.'),('Connect를 쓰면 중복과 장애 대응이 없어지나요?','프레임워크가 반복 기능을 제공하지만 소스·싱크·Connector 구현별 전달 보장은 여전히 확인해야 합니다.','외부 시스템의 쓰기와 Kafka offset 커밋 경계를 그려 판단합니다.')],
 ['apis/','design/design/','kafka-connect/overview/','streams/introduction/'])
topic(13,
 '프로세스 역할 → 노드 식별 → 리스너 바인딩 → 광고 주소 → 메타데이터 quorum → 데이터 로그',
 '가게가 문을 여는 주소와 손님에게 안내하는 주소가 다를 수 있습니다. listeners는 서버가 실제 접속을 받는 위치이고 advertised.listeners는 클라이언트에게 알려 주는 주소입니다. 안내 지도에 손님이 못 가는 내부 주소를 적으면 처음 문의는 성공해도 실제 방문은 실패합니다.',
 'bootstrap.servers는 초기 메타데이터를 얻기 위한 출발점입니다. 클라이언트는 받은 리더 주소로 직접 연결하므로 한 개 로드밸런서 주소가 열려 있다는 사실만으로 모든 경로가 정상인 것은 아닙니다. node.id는 KRaft 노드를 구별하고 process.roles는 broker/controller 역할을 지정합니다. controller.listener.names와 listener.security.protocol.map은 컨트롤러 통신과 보안 프로토콜 연결을 명확히 해야 합니다. 정적 quorum과 동적 quorum 구성은 초기화·변경 절차가 다르므로 설정 몇 줄만 섞지 않습니다.',
 'combined 역할은 학습에 편리하지만 운영 분리 여부는 장애 격리·부하·배치 정책에 따라 판단합니다. log.dirs는 이벤트 로그를 저장하는 경로이고 metadata.log.dir은 메타데이터 로그 배치와 관련됩니다. 설정은 브로커 기본값, 토픽 override, 동적 변경 가능 여부를 같이 확인합니다. 모든 항목이 즉시 변경되는 동적 속성이라고 생각하면 안 됩니다.',
 '개발 PC에서는 정상인데 컨테이너에서만 연결이 끊기면 advertised.listeners가 localhost인지 확인합니다. 컨테이너의 localhost는 브로커 호스트가 아닙니다. DNS, 방화벽, TLS SAN까지 클라이언트가 받은 주소를 기준으로 검증해야 합니다.',
 'Admin으로 cluster node 목록과 host/port를 출력합니다. 각 주소를 실제 앱이 실행되는 네트워크에서 접속해 봅니다. 브로커 프로세스 내부에서 성공한 curl이나 포트 확인만으로 외부 앱의 접속 성공을 판정하지 않습니다. 설정 변경 전후 광고 주소 목록을 기록합니다.',
 [('bootstrap 주소 한 개로 모든 요청이 프록시되나요?','일반적으로 초기 발견 후 각 리더·코디네이터 주소에 직접 연결합니다.','광고된 모든 주소에 접근할 수 있는지 확인해야 합니다.'),('0.0.0.0을 광고 주소로 쓰면 되나요?','바인딩용 전체 인터페이스 주소와 실제 클라이언트가 접속할 주소를 구분해야 합니다.','클라이언트에서 해석·라우팅 가능한 DNS와 인증서 이름을 사용합니다.')],
 ['configuration/broker-configs/','operations/kraft/','security/listener-configuration/'])
topic(14,
 'Worker 시작 → 내부 토픽 읽기 → Connector 설정 수신 → Task 배정 → 변환·직렬화 → offset 관리',
 '운송 회사의 사무실이 Worker, 운송 계획이 Connector, 실제 노선 운행 단위가 Task입니다. 사무실을 늘려도 노선이 한 개뿐이면 모든 사무실이 동시에 운전하지는 않습니다. tasks.max는 요청 상한이며 실제 분할 수는 Connector 구현과 원본 시스템에 달려 있습니다.',
 '분산 Connect는 config.storage.topic, offset.storage.topic, status.storage.topic을 사용합니다. 설정·진행·상태라는 서로 다른 종류의 데이터를 보관하므로 일반 업무 토픽처럼 삭제해도 되는 임시 로그가 아닙니다. config 토픽은 단일 파티션 요구가 있고 내부 토픽의 compaction·복제 구성은 공식 설정을 따라야 합니다. Worker group.id와 내부 토픽 이름은 클러스터 격리에 함께 영향을 줍니다. 다른 환경의 Worker가 같은 내부 자원을 공유하면 의도치 않은 합류가 가능합니다.',
 'Converter는 Connect의 내부 데이터 표현과 Kafka 바이트를 오가고 SMT는 레코드를 변환합니다. 애플리케이션 JSON과 schemas.enable=true인 JsonConverter envelope를 혼동하지 않습니다. plugin.path는 코드 로딩 경로이며 모든 Worker에 동일 플러그인·의존성 배포가 필요합니다. Source EOS는 Worker 기능 설정과 Connector의 지원을 확인해야 하며 모든 외부 Source에서 자동 보장되는 속성이 아닙니다.',
 '특정 Worker로 Task가 이동할 때만 ClassNotFoundException이 나면 데이터 문제가 아니라 플러그인 불일치일 수 있습니다. RUNNING인 Worker 프로세스와 성공적으로 실행 중인 각 Task는 별개 상태입니다. 내부 토픽 권한 오류도 REST 접속 성공 뒤에 나타날 수 있습니다.',
 'Worker REST의 /connector-plugins와 /connectors/{name}/status를 조회합니다. tasks.max를 늘린 뒤 실제 Task 수가 늘었는지 확인합니다. source partition이 하나인 Connector를 무작정 늘려도 선형 확장이 되지 않는 이유를 관찰합니다. 설정 파일에서 비밀번호를 출력하지 않고 변수 참조로 주입합니다.',
 [('Worker 두 대면 같은 그룹에 자동 합류하나요?','bootstrap, group.id, 내부 토픽과 프로토콜·보안 설정 등이 일관되어야 합니다.','서로 다른 환경이 같은 group.id와 내부 토픽을 공유하면 격리가 깨질 수 있습니다.'),('Converter와 Serializer는 같은 역할인가요?','바이트 변환이라는 면은 비슷하지만 Connect Converter는 스키마를 포함한 Connect 내부 모델을 다룹니다.','schemas.enable 설정을 실제 Kafka payload와 함께 확인해야 합니다.')],
 ['configuration/kafka-connect-configs/','kafka-connect/user-guide/','kafka-connect/administration/'])
topic(15,
 'Topology 생성 → application.id 그룹 참여 → Task 배정 → 상태 복구 → 처리·커밋 → 종료',
 '계산 공책을 들고 출근하는 직원이 Streams 인스턴스입니다. application.id는 직원 이름보다 공동 작업 프로젝트 이름에 가깝습니다. 이 이름을 바꾸면 기존 프로젝트의 진행과 장부를 자동 승계하는 단순 재배포가 아니라 별도 앱처럼 동작할 수 있습니다.',
 'Streams는 topology의 sub-topology와 입력 파티션을 바탕으로 Task를 구성하고 Stream Thread에 배정합니다. num.stream.threads만 늘려도 Task보다 많은 병렬성이 생기지 않습니다. state.dir의 로컬 상태는 성능에 중요하지만 장애 복구에는 changelog·입력 토픽 보존과 올바른 설정이 필요합니다. num.standby.replicas는 대기 상태 사본으로 복구를 돕지만 별도 인스턴스·파티션 배치와 자원이 필요합니다.',
 'processing.guarantee=exactly_once_v2는 Kafka 입력 offset, 상태 changelog, Kafka 출력의 처리 경계를 묶는 데 사용합니다. 외부 HTTP 부작용은 포함되지 않습니다. Serde는 입력·출력뿐 아니라 repartition과 store 경계에서도 맞아야 합니다. 기본 Serde만 설정했다고 변경된 키·집계 타입까지 맞는 것이 아니므로 Consumed, Produced, Grouped, Materialized를 필요한 위치에 명시합니다.',
 '재배포 후 전체 이력이 다시 처리됐다면 application.id 변경, offset reset 정책, 내부 토픽 삭제를 의심합니다. Local state를 지웠다고 커밋까지 지워지는 것도 아니며 반대로 출력은 남았는데 진행만 초기화되면 중복 결과가 생길 수 있습니다. App reset은 토픽·그룹·로컬 상태의 서로 다른 범위를 함께 검토해야 합니다.',
 '같은 application.id로 앱을 정지·재시작하여 기존 진행을 이어가는지 봅니다. 실습용 새 application.id로 실행했을 때 초기 offset 정책에 따라 무엇을 읽는지 비교합니다. state.dir를 인스턴스별로 분리하고 restore 로그와 첫 출력까지 걸린 시간을 기록합니다.',
 [('state.dir만 백업하면 완전 복구되나요?','상태 파일과 입력·changelog·offset의 일관성이 필요합니다. 단일 디렉터리 복사만으로 보장을 가정하면 안 됩니다.','토폴로지와 store 포맷 호환성도 함께 검증합니다.'),('exactly_once_v2면 결제 API도 한 번만 호출되나요?','Kafka 트랜잭션에 외부 결제 호출은 자동 참여하지 않습니다.','재시도 가능한 외부 멱등 키와 별도 업무 대조가 필요합니다.')],
 ['configuration/kafka-streams-configs/','streams/architecture/','streams/developer-guide/config-streams/'])
topic(16,
 '관리 요청 구성 → 컨트롤러/코디네이터로 전달 → 개별 Future 확인 → 실제 상태 재조회 → 원격 복제 대조',
 '관리자에게 창고 증설을 신청했다는 접수증과 모든 창고가 새 지도를 반영했다는 사실은 다릅니다. Admin API 호출 반환, Future 완료, 클러스터 전체 관측 가능 시점을 나눠 봅니다. 여러 자원을 한 번에 변경해도 전체가 하나의 원자 트랜잭션처럼 성공하는 것은 아닙니다.',
 'Admin은 비동기 결과를 반환하며 all().get()은 하나의 실패로 전체 대기를 예외 종료시킬 수 있습니다. 운영 도구는 자원별 Future 결과를 기록해 부분 성공을 구분해야 합니다. 설정 변경에는 삭제된 alterConfigs 대신 incrementalAlterConfigs를 사용합니다. 민감 설정의 조회 결과는 숨겨질 수 있으므로 null을 곧바로 미설정으로 해석하지 않습니다. timeout 후에는 재시도 전에 대상 자원의 실제 상태를 조회합니다.',
 'MirrorMaker 2는 Connect 기반으로 소스 토픽을 대상 클러스터에 복제합니다. source와 target의 offset은 숫자가 같다고 같은 이벤트라는 뜻이 아닙니다. offset-sync와 checkpoint 등 변환 메타데이터를 통해 그룹 전환을 준비하며, 전환 시점·설정·진행 상태에 따라 중복·손실 위험을 따져야 합니다. 비동기 복제가 동일 클러스터 RF와 같은 내구성 보장을 주지는 않습니다.',
 '대상 토픽 생성은 성공했지만 응답이 유실된 경우 무조건 create를 반복하면 TopicExistsException이 납니다. 이를 무시할지 판단하려면 기존 토픽의 파티션 수·RF·설정이 의도한 것과 같은지 확인해야 합니다. DR 전환 시 source offset을 target에 그대로 넣으면 읽기 위치가 틀어질 수 있습니다.',
 'Admin으로 study.admin을 생성하고 describeTopics로 파티션·복제본을 검증합니다. 같은 생성 요청을 반복해 기존 상태와 요구 상태 비교를 구현합니다. MM2 실습은 별도 두 클러스터에서 eventId를 유지한 채 양쪽 로그와 checkpoint를 관찰합니다.',
 [('Admin timeout이면 변경이 적용 안 된 건가요?','요청이 적용된 뒤 응답만 늦거나 유실됐을 수 있습니다. 실제 상태를 재조회해야 합니다.','재시도 가능한 선언적 요구 상태와 자원별 결과 기록이 유용합니다.'),('원격 클러스터 offset 100을 그대로 사용해도 되나요?','서로 다른 로그의 offset 숫자는 이벤트 동일성을 보장하지 않습니다.','checkpoint·변환 진행과 eventId 대조로 전환 위치를 검증해야 합니다.')],
 ['configuration/admin-configs/','configuration/mirrormaker-configs/','operations/geo-replication-cross-cluster-data-mirroring/','apis/'])
topic(17,
 '활성 세그먼트 기록 → roll → 원격 업로드 → 메타데이터 관리 → 오래된 로컬 제거 → 필요 시 원격 fetch',
 '자주 보는 책은 책상에, 오래된 책은 외부 보관소에 둡니다. 외부 보관소에 옮겼다고 목록·운송·열쇠 관리가 없어지는 것은 아닙니다. Tiered Storage에는 실제 원격 저장 플러그인과 위치 메타데이터, 업로드·조회 권한, 실패 복구가 필요합니다.',
 '원격 보존과 로컬 보존은 서로 다른 기간·크기 정책입니다. 원격에 안전하게 업로드되지 않은 데이터를 로컬에서 무작정 지우는 방식으로 운영하지 않습니다. 리더 전환 후 새 리더도 원격 메타데이터를 올바르게 해석할 수 있어야 합니다. 최근 데이터는 로컬에서, 오래된 데이터는 원격 fetch에서 제공될 수 있어 지연과 비용이 달라집니다. object storage의 요청 수·대역폭·캐시 적중률이 총비용에 영향을 줍니다.',
 'RemoteStorageManager와 RemoteLogMetadataManager의 역할을 구분합니다. 전자는 원격 세그먼트 저장·조회·삭제 같은 데이터 경로, 후자는 원격 세그먼트 상태를 추적하는 메타데이터 경로와 관련됩니다. ConfigProvider는 설정 값을 외부 참조에서 가져오도록 돕는 인터페이스이며 그 자체가 비밀 암호화·권한 관리·자동 회전을 모두 제공하는 것은 아닙니다. 사용 환경의 provider 허용 설정과 외부 저장소 권한을 검증해야 합니다.',
 '새 비밀번호를 외부 저장소에 넣었는데 실행 중 연결이 계속 실패한다면 값 변경을 감지하고 연결을 갱신하는 lifecycle이 있는지 확인합니다. 단순 파일 변경과 클라이언트 재인증·커넥션 재생성은 별개입니다. 원격 조회가 느린 사고에서는 Consumer 증설이 object store throttling을 더 악화시킬 수 있습니다.',
 '플러그인이 준비된 별도 환경에서 업로드 완료, 로컬 삭제 후 원격 읽기, 브로커 리더 전환을 순서대로 시험합니다. 파일 기반 provider는 실습용 더미 값으로만 참조 해석을 확인합니다. provider 설정을 로그에 출력해 비밀 원문이 노출되지 않는지도 검사합니다.',
 [('원격 저장소를 쓰면 RF=1로 낮춰도 되나요?','원격 계층과 실시간 파티션 복제는 역할이 다릅니다. 업로드 전 데이터와 가용성을 따로 고려해야 합니다.','원격 저장소가 최근 미업로드 데이터의 실시간 복제본을 대신하지 않습니다.'),('ConfigProvider면 비밀번호가 자동으로 회전하나요?','값 조회와 실행 중 연결 교체는 다른 문제입니다. provider·컴포넌트 구현의 갱신 동작을 확인해야 합니다.','변경 전후 재인증·재시작 필요 여부를 실제로 시험합니다.')],
 ['operations/tiered-storage/','configuration/tiered-storage-configs/','configuration/configuration-providers/'])
topic(18,
 'TCP 바이트 스트림 → 길이 프레임 → 요청 헤더 → API별 본문 → 응답 correlation 매칭',
 '우편 봉투의 길이·문서 종류·접수번호를 먼저 알아야 내용을 해석할 수 있습니다. Kafka 프로토콜도 길이, API key/version, correlation id 등의 헤더를 바탕으로 본문 구조를 결정합니다. TCP 한 번 읽기가 Kafka 요청 한 개와 일치한다는 보장은 없습니다.',
 'TCP는 메시지 경계를 제공하지 않는 바이트 스트림이므로 부분 수신과 여러 프레임의 합쳐진 수신을 처리해야 합니다. 고정 길이 정수와 가변 길이 필드의 인코딩, big-endian 표현, nullable 필드의 의미를 API 스키마에 맞춰 읽어야 합니다. correlation id는 요청·응답 연결용이며 업무 eventId나 Producer 멱등 sequence와 다른 식별자입니다. API key는 작업 종류, API version은 그 작업의 메시지 형식 버전입니다.',
 'ApiVersions로 API별 지원 범위를 확인한 뒤 공통 버전을 선택합니다. 브로커 버전 문자열과 모든 요청 API version이 일대일 대응하는 것은 아닙니다. Flexible version은 compact 인코딩과 tagged fields를 도입하지만 모든 필드가 임의 JSON처럼 확장되는 것은 아닙니다. 인증 전후 사용할 수 있는 API와 TLS/SASL 연결 단계도 프로토콜 문제와 분리합니다.',
 '직접 만든 프로토콜 파서가 로컬에서는 성공하다 실제 네트워크에서 깨진다면 부분 프레임 처리 누락을 의심합니다. Kafka 클라이언트를 쓰는 앱에서 이런 파서를 새로 만들 필요는 거의 없습니다. 패킷 내용을 보기 전에 디버그 로그로 API 이름·버전·오류·상대 주소를 확인하는 편이 효율적입니다.',
 'Java ByteBuffer로 길이 프리픽스를 넣고 두 조각으로 나눠 읽는 작은 테스트를 만듭니다. 전체 프레임이 모이기 전에 본문을 읽으면 실패하는지 확인합니다. 실제 Kafka 요청을 수작업 송신하기보다 kafka-broker-api-versions.sh 출력과 클라이언트 로그를 대응시켜 봅니다.',
 [('correlation id가 같으면 같은 이벤트인가요?','네트워크 요청과 응답을 연결하는 값이지 비즈니스 이벤트 식별자가 아닙니다. 하나의 요청에 여러 레코드가 포함될 수 있습니다.','eventId·offset·producer sequence와 각각의 유일성 범위를 구분합니다.'),('TCP가 신뢰성이 있는데 왜 타임아웃 결과가 불명인가요?','서버가 처리한 뒤 응답 전에 연결이 끊길 수 있습니다. 전송 신뢰성과 업무 결과 확인은 다릅니다.','실패 시 실제 상태를 재조회하거나 멱등하게 재시도하는 이유입니다.')],
 ['design/protocol/','implementation/network-layer/','implementation/messages/'])
topic(19,
 'Metadata로 리더 발견 → Produce 배치 추가 → Fetch offset 요청 → 가시 경계까지 반환 → 위치 전진',
 '창고 안내 데스크에서 해당 물건 담당 창고를 찾고, 그 창고에 직접 입출고를 요청합니다. Metadata는 안내 지도이고 Produce/Fetch는 실제 운송 요청입니다. 지도는 오래될 수 있으므로 리더 변경 응답을 받으면 새 지도를 받아야 합니다.',
 'Produce는 토픽·파티션별 레코드 배치를 운반하고 acks·timeout 조건과 함께 처리됩니다. Fetch는 파티션별 시작 offset과 바이트 상한 등을 전달합니다. Consumer fetch와 follower 복제 fetch는 목적과 필드·권한이 다릅니다. read_committed의 반환은 last stable offset 영향을 받으며 high watermark만 보고 모든 데이터가 보인다고 단정할 수 없습니다. 제어 배치와 abort된 레코드 때문에 물리 로그 offset 증가가 사용자 레코드 개수와 맞지 않을 수 있습니다.',
 'max.partition.fetch.bytes, fetch.max.bytes, max.poll.records는 서로 다른 층입니다. 서버가 돌려주는 바이트, 파티션별 한도, 애플리케이션 poll에 건네는 레코드 수를 구분해야 합니다. 첫 큰 배치 반환 등 진행 보장 예외가 있어 바이트 설정을 정확한 JVM 메모리 최대치로 쓰면 안 됩니다. 리더 오류는 메타데이터 갱신과 재시도에 연결되지만 인증·직렬화 오류까지 같은 방식으로 반복하면 안 됩니다.',
 '레코드 크기를 늘린 후 Producer는 성공하는데 Consumer가 메모리 부족을 겪으면 압축 해제 후 크기·객체 생성·동시 fetch 수를 봅니다. 네트워크 압축 바이트만 보고 heap을 계산하면 부족할 수 있습니다. 특정 파티션만 막히면 파티션별 큰 배치와 리더 상태를 함께 확인합니다.',
 '작은 JSON과 반복 문자열로 큰 배치를 각각 전송합니다. Producer record-size·request-size와 Consumer fetch-size·poll 레코드 수를 기록합니다. max.poll.records를 낮춰도 네트워크에 미리 fetch한 전체 데이터가 그 숫자로 제한되는 것은 아닌지 비교합니다.',
 [('poll 한 번이면 Fetch 요청 한 번인가요?','클라이언트 내부 버퍼와 비동기 fetch가 있어 일대일 관계가 아닙니다.','메서드 호출 횟수로 네트워크 요청 수를 추정하지 않습니다.'),('high watermark 뒤에 안 읽히는 건 모두 장애인가요?','isolation.level과 열린 트랜잭션에 따른 LSO를 확인해야 합니다.','read_committed와 read_uncommitted를 비교할 때 업무 격리 의미도 함께 판단합니다.')],
 ['design/protocol/','configuration/consumer-configs/','implementation/message-format/','operations/transaction-protocol/'])
topic(20,
 '코디네이터 발견 → 그룹 참여/heartbeat → 할당 조정 → 데이터 소비 → offset 커밋 → 세대·epoch 검증',
 '당번표를 관리하는 반장과 실제 책을 보관하는 사서가 다릅니다. Group Coordinator는 멤버·할당·커밋을 다루고 파티션 리더는 레코드를 제공합니다. bootstrap 브로커, Coordinator, Controller, 데이터 리더가 항상 같은 서버는 아닙니다.',
 'classic 프로토콜의 JoinGroup·SyncGroup·Heartbeat 흐름과 새 consumer 프로토콜의 ConsumerGroupHeartbeat 흐름을 구별합니다. 새 프로토콜은 서버 쪽 할당과 점진적 조정으로 동작하며 classic의 클라이언트 설정을 그대로 적용할 수 없습니다. OffsetCommit은 그룹·토픽·파티션별 복구 위치를 기록하고 멤버 세대나 epoch와 같은 정보로 오래된 소유자의 부적절한 갱신을 제어합니다. 그럼에도 DB 작업은 이미 실행됐을 수 있어 fencing과 외부 멱등성을 함께 생각해야 합니다.',
 '정적 멤버십의 group.instance.id는 같은 그룹에서 인스턴스별로 유일해야 합니다. 이미지를 복제하면서 동일 값을 복사하면 fencing 오류가 날 수 있습니다. Cooperative assignor와 새 consumer 프로토콜은 같은 이름의 기능이 아니며 각 버전에서 지원되는 전환 경로를 확인합니다. 블루그린으로 인스턴스 수가 두 배가 되어도 처리 가능한 파티션 수가 두 배가 되는 것은 아닙니다.',
 '새 배포 후 FencedInstanceIdException이 반복되면 실제 인스턴스 ID 중복을 먼저 봅니다. CommitFailedException이 나타나면 처리 시간이 max.poll.interval을 넘었는지, 리밸런스 후 이전 할당에서 커밋을 시도했는지 시간순으로 대조합니다. 커밋 실패 뒤 DB 성공 여부를 확인하지 않고 전체 재처리하면 중복이 생깁니다.',
 'Consumer 세 개에 서로 다른 group.instance.id를 주고 파티션 배정을 기록합니다. 한 인스턴스를 정상 종료한 경우와 kill한 경우 재할당까지 시간을 비교합니다. classic과 consumer 프로토콜은 별도 그룹으로 실험하여 heartbeat 관련 설정 위치 차이를 확인합니다.',
 [('멤버가 여섯 개인데 파티션이 세 개면 모두 일하나요?','일반적인 해당 토픽 그룹 할당에서는 동시에 세 멤버까지만 파티션을 맡습니다. 다른 구독 토픽은 별도로 계산합니다.','증설 판단에 멤버 수뿐 아니라 전체 파티션·편중을 봐야 합니다.'),('static membership이면 리밸런스가 완전히 없어지나요?','안정적인 인스턴스 식별로 불필요한 이동을 줄이지만 멤버·구독·장애 변화에 따른 조정 자체를 없애지는 않습니다.','중복 ID fencing과 장애 감지 지연의 운영 조건도 확인합니다.')],
 ['design/protocol/','operations/consumer-rebalance-protocol/','configuration/consumer-configs/','design/design/'])
topic(21,
 '자원별 권한 확인 → 관리 요청 → 컨트롤러 처리 → 자원별 결과 → 전파 상태 재조회',
 '건물 한 동씩 공사 허가를 받는 작업을 묶어서 신청해도 모두 동시에 완공되는 것은 아닙니다. 관리 API의 여러 자원 요청도 부분 성공이 가능합니다. 신청 전체가 실패했다고 성공한 토픽을 다시 지우거나 새로 만들면 사고가 커집니다.',
 'CreateTopics, DescribeConfigs, IncrementalAlterConfigs, DescribeGroups는 목적과 대상 자원, 허용되는 버전이 다릅니다. NotController 같은 응답은 메타데이터·대상 갱신이 필요한 신호일 수 있지만 TopicAuthorizationException은 권한 설계 문제입니다. throttle_time_ms는 서버가 할당량을 적용한 지연이며 단순 네트워크 RTT와 구분합니다. validateOnly 지원 작업도 실제 적용과 같은 모든 경쟁 조건까지 없애지는 않습니다.',
 '읽기·변경 권한을 분리하고 원하는 상태를 선언적으로 비교합니다. 기존 토픽이 있다고 성공 취급하기 전에 파티션 수·복제·cleanup.policy를 검증합니다. incrementalAlterConfigs에서는 SET·DELETE 등 연산 의미를 확인하고 누락된 다른 설정이 삭제되는 전체 교체 방식과 구별합니다. 롤백은 원래 값과 override 존재 여부까지 보관해야 정확합니다.',
 '일부 토픽만 권한이 없어 배치 생성이 부분 실패했다고 가정합니다. 전체 Future의 예외 메시지만 남기면 어느 토픽이 만들어졌는지 모릅니다. 자원별 결과를 기록하고 실제 상태를 다시 읽어 재시도 대상을 정해야 합니다. 민감 설정이 마스킹된 조회 값을 그대로 덮어쓰는 복구도 피합니다.',
 'Admin 예제에서 존재하는 토픽, 새 토픽, 권한 없는 토픽을 함께 요청하는 통합 실험을 구성합니다. 결과를 자원별로 분해하고 describe로 확인합니다. 학습 계정에 권한이 없다면 권한 오류를 건너뛰었다고 표시하고 성공 검증으로 보고하지 않습니다.',
 [('관리 요청 여러 개가 한 번에 성공하거나 롤백되나요?','보통 자원별 결과가 존재하며 전체 원자성을 가정하면 안 됩니다.','부분 성공 뒤 요구 상태를 재조회해 수렴시키는 도구가 필요합니다.'),('validateOnly 성공이면 실제 적용도 반드시 성공하나요?','그 사이 상태·권한·자원이 달라질 수 있습니다. 검증과 실행은 별도 요청입니다.','실행 결과와 사후 상태 검증을 생략할 수 없습니다.')],
 ['design/protocol/','configuration/admin-configs/','security/authorization-and-acls/'])
topic(22,
 '클라이언트 버전 → ApiVersions 협상 → API별 공통 버전 선택 → 인코딩/오류 해석 → 기능 회귀 시험',
 '같은 한국어를 사용해도 계약서 양식의 개정 번호가 다를 수 있습니다. Kafka 제품 버전은 프로그램 묶음의 버전이고 API version은 요청 종류별 양식 번호입니다. 모든 API가 동시에 같은 번호로 올라가는 모델이 아닙니다.',
 '클라이언트는 서버가 지원하는 API별 최소·최대 버전과 자신의 범위에서 사용할 버전을 고릅니다. 최신 클라이언트가 오래된 브로커와 연결될 수 있어도 새 기능을 모두 사용할 수 있다는 보장은 아닙니다. Flexible version의 tagged fields는 알려지지 않은 태그를 건너뛸 수 있도록 하지만 필수 의미 변경까지 자동 호환시키지는 않습니다. 오류 코드는 retriable 여부만 보지 말고 동작의 멱등성과 이미 적용됐을 가능성까지 함께 판단합니다.',
 '브로커, Java 클라이언트, Spring Kafka, JDK, 인증, 그룹 프로토콜을 호환성 표로 관리합니다. Spring Boot의 BOM을 무시하고 kafka-clients만 강제로 교체하면 컴파일은 되어도 런타임 linkage 오류나 지원 범위 문제가 생길 수 있습니다. 최신 의존성을 쓰는 학습 앱과 기존 운영 앱의 업그레이드 결정을 분리합니다.',
 'NoSuchMethodError는 브로커가 요청을 거절한 프로토콜 오류와 다릅니다. 실행 classpath에 충돌하는 라이브러리가 있는지 dependency tree를 확인합니다. UnsupportedVersionException은 사용한 기능에 필요한 API 버전이 공통 범위에 없는지 확인합니다. 두 오류를 같은 재시도 정책으로 처리하면 복구되지 않습니다.',
 'kafka-broker-api-versions.sh로 각 노드 지원 API를 저장합니다. 최소 두 클라이언트 버전 조합에서 생산·소비·커밋·Admin·TLS 인증을 시험합니다. 단순 TCP 연결 성공은 스키마·트랜잭션·리밸런스 호환성 시험을 대신하지 않습니다.',
 [('브로커 4.3이면 모든 API version이 4인가요?','API별 번호는 제품 버전과 별도로 증가합니다.','ApiVersions 결과를 요청 종류별로 읽어야 합니다.'),('재시도 가능 오류는 무조건 계속 재시도하나요?','종료 시간, backoff, 결과 불명 상태, 업무 중복 가능성을 함께 설계해야 합니다.','인증·권한·직렬화 오류를 반복해도 해결되지 않으며 장애를 증폭할 수 있습니다.')],
 ['design/protocol/','getting-started/compatibility/','getting-started/upgrade/'])
topic(23,
 '소스 커밋 → 비동기 복제 → 원격 로그 기록 → checkpoint 갱신 → 전환 결정 → Consumer 재개·대조',
 '서울 창고 장부를 부산 창고에 복사하면 복사 중인 마지막 몇 페이지는 아직 없을 수 있습니다. 같은 창고 안의 사본 복제와 먼 창고로의 비동기 복제는 실패 모델이 다릅니다. DR은 복사 도구 설치로 끝나지 않고 마지막 안전 페이지를 어디로 정할지 결정하는 절차입니다.',
 '클러스터 간 복제는 네트워크 단절·대역폭·지연에 영향을 받습니다. RPO는 감수 가능한 데이터 손실 구간, RTO는 서비스 복구 시간 목표입니다. source offset과 target offset은 로그가 다르므로 변환 메타데이터와 실제 이벤트 대조가 필요합니다. 양방향 복제에서는 토픽 이름 정책과 루프 방지, 어느 클러스터가 어떤 업무 키의 쓰기 권한을 갖는지 명확히 해야 합니다.',
 '멀티테넌시는 토픽 이름만 나누는 문제가 아닙니다. ACL, client.id/사용자별 quota, 용량, 파티션 수, 보존 비용, 운영 권한을 함께 분리합니다. quota는 공정성과 보호 장치이지만 물리적인 완전 격리는 아닙니다. 이웃 팀의 대량 재처리가 캐시·디스크를 사용하면 내 앱도 영향을 받을 수 있습니다.',
 '주 센터가 복구되자 양쪽이 동시에 주문을 발행하면 동일 업무가 충돌할 수 있습니다. Consumer만 전환하고 Producer의 쓰기 주체를 통제하지 않은 사고입니다. failback은 failover의 반대 버튼 하나가 아니라 쓰기 중지, 복제 따라잡기, 진행 변환, 업무 대조를 다시 수행하는 작업입니다.',
 '두 클러스터에 동일 eventId를 유지하는 MM2 실험을 구성합니다. 복제를 잠시 정지해 의도적 lag를 만들고, 전환 시점에 누락·중복 eventId를 계산합니다. RPO를 offset 숫자만으로 쓰지 말고 마지막 복제된 이벤트 시간과 업무 영향으로 표현합니다.',
 [('RF=3이면 원격 재해 복구도 해결되나요?','동일 장애 영역에 세 사본이 있으면 지역 전체 장애에 취약합니다. 배치 위치와 원격 복구를 따로 설계합니다.','복제 수와 장애 도메인 분산은 다른 축입니다.'),('quota가 있으면 테넌트 간 간섭이 0인가요?','공유 자원을 사용하는 이상 모든 간섭을 없애지는 못합니다.','비용 큰 재처리·핫 파티션·용량 경고를 별도 정책으로 통제합니다.')],
 ['operations/datacenters/','operations/geo-replication-cross-cluster-data-mirroring/','operations/multi-tenancy/','design/design/'])
topic(24,
 'DNS·TCP 연결 → TLS 서버 인증 → 선택적 클라이언트 인증 → Kafka 인증/인가 → 메타데이터 주소 재연결',
 '잠긴 택배 상자는 내용을 숨기고 발송자 서명은 신원을 증명합니다. TLS 암호화, 인증서의 서버 신원 확인, mTLS의 클라이언트 인증은 연결되지만 같은 항목은 아닙니다. 신원을 확인했다고 특정 토픽 읽기 권한까지 생기는 것도 아닙니다.',
 'truststore는 믿을 인증 기관·인증서를, keystore는 자신의 인증서와 개인 키를 제공하는 용도로 구분합니다. 서버 인증서의 SAN은 클라이언트가 실제 접속하는 DNS 이름과 맞아야 합니다. bootstrap 접속이 성공해도 advertised.listeners에 나온 다른 브로커 이름이 인증서와 안 맞으면 후속 연결이 실패합니다. listener.security.protocol.map으로 이름과 SSL/SASL_SSL 등을 연결하고 controller·inter-broker 경로도 별도 검토합니다.',
 'hostname verification을 끄는 것을 정상 해결로 쓰지 않습니다. 연결 호스트, 인증서 SAN, trust chain, 만료 시각, 프로토콜·암호군을 확인하는 순서로 원인을 좁힙니다. mTLS에서는 클라이언트 인증서와 principal 매핑이 ACL 설계까지 이어집니다. 인증서 회전은 만료 전 중첩 신뢰 기간과 롤링 갱신·재접속 시험이 필요합니다.',
 '인증서 갱신 후 일부 인스턴스만 실패하면 각 인스턴스가 읽는 파일 버전·권한·경로, JVM의 신뢰 저장소, 오래된 커넥션을 비교합니다. 인증서 파일을 교체했다는 사실만으로 실행 중 객체가 새 내용을 읽었다고 보장할 수 없습니다.',
 '실습 CA와 서버 인증서를 만들 때 localhost와 실제 테스트 DNS를 SAN에 넣습니다. 올바른 CA, 틀린 CA, 틀린 hostname 세 경우를 비교합니다. openssl s_client의 TLS 성공 뒤에도 Kafka Admin 조회를 수행해 인증·인가까지 통과하는지 확인합니다.',
 [('TLS가 되면 ACL 없이 안전한가요?','암호화와 서버 신원 확인만으로 토픽별 권한이 자동 분리되지는 않습니다.','mTLS 또는 SASL로 얻은 principal에 적절한 인가를 적용해야 합니다.'),('bootstrap만 SSL로 열리면 되나요?','메타데이터가 알려 주는 각 브로커 연결도 DNS·포트·인증서가 정상이어야 합니다.','한 노드에서만 실패하면 광고 주소와 SAN을 노드별로 대조합니다.')],
 ['security/listener-configuration/','security/encryption-and-authentication-using-ssl/','security/security-overview/'])
topic(25,
 '보안 프로토콜 선택 → TLS → SASL 메커니즘 협상 → 자격 검증 → principal 생성 → ACL 판단',
 '출입증 검사와 잠긴 통로는 다릅니다. SASL은 신원 확인 절차이고 SSL은 통신 보호와 서버 인증에 사용됩니다. SASL_PLAINTEXT라는 이름의 인증이 성공해도 전송 내용이 TLS로 암호화되는 것은 아닙니다.',
 'SASL_SSL은 TLS 위에서 SASL 인증을 수행합니다. SCRAM은 비밀번호 기반 검증 메커니즘이며 클라이언트와 서버에 동일한 메커니즘 지원·사용자 자격 설정이 필요합니다. PLAIN은 전송 계층 보호 없이 사용하면 자격 정보 노출 위험이 있어 TLS와 결합합니다. OAUTHBEARER는 토큰의 issuer·audience·만료·서명 검증과 외부 엔드포인트 접근 제약까지 확인합니다. 토큰을 문자열로 받았다고 검증 없이 신뢰하면 안 됩니다.',
 'JAAS 설정을 소스·Git·에러 로그에 넣지 않습니다. ${ENV} 참조를 사용해도 환경 변수나 설정 덤프를 로그에 출력하면 노출될 수 있습니다. 사용자 교체 시 새 자격 배포와 ACL 적용, 구 자격 폐기를 단계적으로 진행합니다. Broker 인증 실패와 Consumer의 토픽 권한 실패는 예외 종류와 서버 로그에서 구분합니다.',
 '운영 비밀번호를 회전한 직후 재배포한 앱만 실패하면 실행 환경의 secret 주입과 메커니즘을 확인합니다. 성공한 기존 연결이 남아 있어 전체가 정상처럼 보일 수 있으므로 새 연결 인증을 강제로 시험하는 검증이 필요합니다. 반복 인증 실패는 backoff 없이 재시도하면 서버 부담을 키웁니다.',
 '더미 사용자로 SASL_SSL 클라이언트 설정을 만들고 올바른 비밀번호, 틀린 비밀번호, 권한 없는 토픽 세 경우를 비교합니다. 잘못된 비밀번호는 인증, 올바른 비밀번호와 잘못된 ACL은 인가 실패라는 것을 로그로 구분합니다. 실제 비밀 값을 명령 인자로 노출하지 않습니다.',
 [('SCRAM이면 TLS가 필요 없나요?','SASL 인증과 업무 데이터 암호화는 다릅니다. SCRAM을 쓴다는 사실만으로 모든 전송 데이터가 암호화되지 않습니다.','사용할 security.protocol과 위협 모델을 함께 정합니다.'),('SASL 인증 성공인데 TopicAuthorizationException이 왜 나나요?','신원 확인 후 해당 principal의 자원 권한이 없을 수 있습니다.','인증 사용자·principal 매핑·토픽·그룹 ACL을 대조해야 합니다.')],
 ['security/authentication-using-sasl/','security/security-overview/','security/authorization-and-acls/'])
topic(26,
 '클라이언트 인증 → principal 매핑 → resource·operation·host 매칭 → allow/deny 판단 → 요청 실행',
 '출입증으로 누구인지 확인해도 모든 창고 문을 열 수 있는 것은 아닙니다. ACL은 누가 어떤 자원에서 어떤 행동을 할 수 있는지 정하는 규칙입니다. Topic READ와 Group READ는 다른 문을 여는 권한이어서 한쪽만 있으면 그룹 소비가 실패할 수 있습니다.',
 'KRaft의 StandardAuthorizer는 메타데이터 기반 인가를 수행합니다. ACL은 principal, operation, resource type/name/pattern, host 등을 조합합니다. Literal과 prefixed 패턴은 매칭 범위가 다르고, 이름에 별표를 넣는 방식과 패턴 타입을 혼동하면 권한 범위가 달라집니다. deny와 allow의 우선순위, super.users, allow.everyone.if.no.acl.found 같은 예외는 전체 인가 모델을 바꾸므로 문서의 정확한 규칙을 확인해야 합니다.',
 'Consumer에는 업무 토픽 읽기뿐 아니라 그룹 권한이 필요합니다. Producer에는 쓰기와 사용하는 멱등·트랜잭션 기능에 필요한 권한을 검토합니다. Streams는 입력·출력·내부 토픽·application 그룹 권한이 연결됩니다. CLI의 --consumer/--producer 편의 옵션이 어떤 ACL을 생성하는지 --list 결과로 확인하고 wildcard를 정상 해결로 삼지 않습니다.',
 '스테이징에서는 되는데 운영에서는 안 되면 토픽 이름 prefix, principal 매핑, group.id 차이를 확인합니다. 권한 오류를 재시도 가능 네트워크 오류처럼 처리하면 진행 없이 요청만 반복합니다. 임시 광범위 권한을 준 뒤 회수하지 않으면 별도 보안 사고가 남습니다.',
 '실습 사용자 User:study-reader에 study.acl 토픽과 study.acl 그룹의 읽기를 부여합니다. 다른 그룹·다른 토픽으로 각각 접근해 어느 권한에서 거절되는지 확인합니다. 변경 전후 --list를 보관하고 실습 종료 후 정확히 추가한 규칙만 제거합니다.',
 [('Topic READ만 있으면 그룹 소비가 되나요?','그룹 조정과 offset 관리에 대한 그룹 권한도 확인해야 합니다.','오류가 토픽인지 그룹인지 구분하고 해당 resource ACL을 조회합니다.'),('prefix ACL이면 모든 이름에 부분 문자열 매칭되나요?','prefixed는 자원 이름의 접두사 조건입니다. 임의 정규식이나 부분 포함 검색과 다릅니다.','환경·팀 prefix 설계를 먼저 정해 우발적인 권한 공유를 막습니다.')],
 ['security/authorization-and-acls/','security/listener-configuration/'])
topic(27,
 'Source 원본 읽기 → SourceRecord → SMT → Converter → Kafka → Converter → SMT → SinkRecord → 외부 저장',
 '통관 서류를 내부 공통 양식으로 바꾸고 필요한 항목을 수정한 뒤 운송하는 과정입니다. Converter는 공통 양식과 전송 바이트 사이, SMT는 레코드 내용 변환, Connector는 외부 시스템과의 연결을 담당합니다. 셋을 구분하면 데이터가 어느 지점에서 달라졌는지 추적할 수 있습니다.',
 'Source의 진행은 외부 원본 파티션과 source offset으로 표현됩니다. Sink는 Kafka 토픽·파티션 offset을 소비하고 외부 저장 성공과 커밋을 조정합니다. Sink put이 반환했다고 실제 비동기 외부 저장이 완료됐다고 보장할 수 없으므로 Connector 구현은 flush/preCommit 경계를 지켜야 합니다. Worker 수를 늘려도 원본이 분할 불가하거나 task 수가 작으면 병렬성이 늘지 않습니다.',
 'SMT는 레코드 단위의 가벼운 변환에 적합합니다. 외부 서비스 조인이나 대규모 상태 집계를 SMT에 숨기면 장애·성능 특성이 불투명해집니다. CDC 도입은 스냅샷과 변경 로그 전환, 삭제 이벤트, 스키마 변경, 원본 로그 보존, 재시작 offset을 함께 시험합니다. 특정 DB Connector의 보장은 Apache Kafka 코어 문서만으로 확정할 수 없으므로 해당 구현 문서를 추가로 확인해야 합니다.',
 '스냅샷이 끝나기 전에 DB 변경 로그가 정리되면 재개 지점을 잃을 수 있습니다. Connect가 RUNNING이어도 원본의 로그 보존 시간이 충분한지 별도로 감시해야 합니다. Sink 중복 적재는 안정적인 키 기반 upsert·고유 제약으로 방어할 수 있지만 append-only 대상이라면 별도 중복 정책이 필요합니다.',
 'FileStream Connector처럼 학습 목적의 플러그인으로 세 줄을 읽고 재시작합니다. 동일 파일·source offset 보존 조건에서 어디부터 읽는지 기록합니다. Converter의 schemas.enable을 바꿨을 때 실제 payload envelope와 Sink가 기대하는 구조를 비교합니다.',
 [('tasks.max=10이면 Task가 반드시 10개 생기나요?','최대 요청값이며 실제 Task 구성은 Connector와 외부 분할에 달려 있습니다.','상태 API에서 실제 Task 수와 각 처리율을 확인해야 합니다.'),('CDC를 켜면 원본 로그를 짧게 보관해도 되나요?','Connector가 정지하거나 스냅샷이 오래 걸릴 수 있어 복구 가능한 기간을 고려해야 합니다.','원본 로그·Kafka 보존·Sink 복구 시간의 전체 경계를 계산합니다.')],
 ['kafka-connect/user-guide/','kafka-connect/overview/','kafka-connect/connector-development-guide/'])
topic(28,
 'Connector.start → taskConfigs → Task.start → poll/put 반복 → flush·offset 경계 → stop',
 '노선 설계자가 여러 운전사에게 겹치지 않는 구간을 배정해야 중복 운행과 누락을 줄일 수 있습니다. Connector는 Task 설정을 만들고 Task는 실제 데이터를 이동시킵니다. Task를 복제할 때 원본 범위를 겹치게 주면 처리량이 아니라 중복량이 늘어납니다.',
 'SourceTask.poll은 SourceRecord 목록을 반환하며 각 레코드에는 복구 가능한 source partition·offset을 넣습니다. 시스템 시각만 진행값으로 쓰면 같은 시각 여러 행이나 지연 도착을 놓칠 수 있습니다. SinkTask.put은 레코드 묶음을 받고 flush 또는 preCommit에서 안전하게 커밋할 offset을 결정합니다. 외부 저장을 별도 큐에 넣고 즉시 완료로 취급하면 재시작 시 유실될 수 있습니다.',
 '재시도 가능 예외와 영구 데이터 오류를 분리합니다. RetriableException을 무한 방출하면 잘못된 데이터가 전체 Task를 막을 수 있습니다. 외부 API timeout은 적용 여부 불명이므로 idempotency key를 유지합니다. stop은 블로킹 poll·외부 요청을 깨우고 제한 시간 안에 종료하도록 설계합니다. Connector 플러그인은 모든 Worker에 동일 버전으로 배포합니다.',
 'Sink가 100건 중 50건만 외부 저장한 뒤 실패하면 묶음 전체가 다시 전달될 수 있습니다. 외부 저장의 원자성 또는 레코드별 멱등성이 없으면 앞 50건이 중복됩니다. 단순히 마지막 레코드 offset을 반환하는 preCommit은 앞 실패분을 건너뛰게 만들 수 있습니다.',
 '가짜 외부 저장소가 3번째 쓰기에서 실패하도록 만듭니다. Task 재시도 후 eventId별 저장 횟수와 성공 결과를 대조합니다. Source는 같은 timestamp의 서로 다른 id 두 개와 지연 도착 행을 넣어 source offset 설계가 누락 없이 재개되는지 확인합니다.',
 [('Source offset을 마지막 timestamp로만 저장하면 안전한가요?','동일 timestamp와 늦게 도착한 데이터 때문에 충분하지 않을 수 있습니다. 원본의 안정적 순서·복구 키를 설계해야 합니다.','timestamp와 유일 id 복합 경계도 원본 조회 의미와 함께 검증합니다.'),('Sink put 반환 후 언제 커밋해도 되나요?','외부 저장이 안전하게 완료된 경계를 flush/preCommit에 반영해야 합니다.','비동기 큐에 넣었다는 사실을 영속 저장 완료로 취급하면 안 됩니다.')],
 ['kafka-connect/connector-development-guide/','kafka-connect/user-guide/'])
topic(29,
 'REST 상태 조회 → 실패 Task 식별 → 원인 분류 → 데이터·설정 수정 → 제한 재시작 → 처리 결과 대조',
 '병원 건물의 전등이 켜져 있어도 모든 진료실이 정상 진료 중인 것은 아닙니다. Worker 프로세스의 실행과 Connector RUNNING, 개별 Task 상태, 실제 데이터가 도착하는 상태를 나눠 봅니다.',
 'Connect REST는 설정과 상태·재시작을 관리합니다. Connector 상태만 보고 Task 실패를 놓치지 않도록 /connectors/{name}/status의 task별 상태와 trace를 확인합니다. errors.tolerance=all은 지원되는 변환·변환기 등 오류 처리 범위에서 레코드를 건너뛸 수 있게 하지만 모든 Connector put 예외를 자동 복구하지 않습니다. Sink DLQ는 실패 데이터 보관 경로이지 최종 업무 처리 성공의 증거가 아닙니다.',
 'DLQ에는 원본 데이터·개인정보와 오류 문맥이 들어갈 수 있어 ACL·보존·재처리 도구를 설계합니다. 오류 허용을 켰으면 성공 처리량과 건너뛴 수·DLQ 수를 따로 봅니다. plugin upgrade는 모든 Worker 배포·Task 이동·직렬화 호환성을 시험하고 REST 인터페이스는 외부 공개 관리 API로 방치하지 않습니다.',
 '알람을 끄려고 errors.tolerance=all을 켜면 빨간 불은 줄어도 업무 누락이 늘 수 있습니다. DLQ에 쌓인 데이터를 누가 언제 어떤 버전으로 재처리할지 소유자를 정해야 합니다. 원인을 고치지 않고 restart만 반복하면 원본 로그 보존이 끝나 복구 범위를 잃을 수도 있습니다.',
 '일부 잘못된 JSON을 포함한 실습 입력을 넣습니다. Converter/SMT 단계 실패와 외부 Sink 장애를 각각 만들어 같은 옵션이 모든 단계에 적용되지 않는 것을 확인합니다. DLQ의 eventId를 정상 처리 결과와 대조하고 수정 후 재처리해 중복 여부를 검사합니다.',
 [('Connector RUNNING이면 데이터도 정상인가요?','Task 실패, 입력 없음, 외부 시스템 대기, 처리 정체를 별도로 확인해야 합니다.','최근 성공 시각·입출력 건수·DLQ·Task 상태를 함께 관찰합니다.'),('DLQ로 보내면 데이터 유실이 해결됐나요?','데이터 보관과 업무 반영 완료는 다릅니다. 재처리·대조가 필요합니다.','DLQ 보존 만료와 접근 권한까지 운영 책임으로 정해야 합니다.')],
 ['kafka-connect/administration/','kafka-connect/user-guide/','configuration/kafka-connect-configs/'])
topic(30,
 '입력 파티션 → sub-topology Task → processor node → state store/changelog → 출력 토픽',
 'KStream은 매번 일어난 입출고 내역이고 KTable은 상품별 현재 재고 장부입니다. 같은 상품이 두 번 등장하면 내역에는 두 사건, 장부에는 갱신된 현재 값이라는 서로 다른 의미가 됩니다. 이름만 바꿔 같은 데이터를 대체해 읽을 수 있는 것이 아닙니다.',
 'KStream 레코드는 독립 사건으로 해석하고 KTable 레코드는 같은 키 상태의 upsert로 해석합니다. KTable의 null value는 삭제 의미를 갖습니다. 상태가 필요한 집계·조인은 로컬 state store와 changelog를 사용하고 장애 시 복원합니다. Task는 sub-topology와 입력 파티션 분할을 바탕으로 만들어지며 한 Task 안의 연산을 Stream Thread가 수행합니다. 앱 인스턴스는 Task들을 분산 실행하는 프로세스입니다.',
 '키가 바뀐 뒤 집계·조인이 필요하면 repartition이 생길 수 있습니다. 내부 토픽은 구현 잡음이 아니라 데이터 재분배와 복구 경로입니다. topology.describe()로 실제 노드·sub-topology·입출력 토픽을 먼저 읽습니다. 읽기 전용 조회를 붙일 때 state store가 전체 클러스터 데이터를 한 인스턴스에 모은다고 가정하지 않습니다.',
 '재고 이벤트를 KTable로 바로 읽고 모든 변경 수를 세려고 하면 갱신 의미·캐시 동작 때문에 의도와 다른 결과를 얻을 수 있습니다. 이벤트 내역에서 발생 횟수를 세는 것과 현재 상태를 합산하는 것을 구분해야 합니다. 중복 이벤트를 입력하면 count도 늘 수 있으므로 eventId 기준의 의미를 설계합니다.',
 '동일 키 A에 값 10, 20, null을 전송합니다. KStream 출력, KTable 조회, table.toStream 출력을 비교합니다. 캐시 설정과 커밋 간격 때문에 관측 가능한 중간 업데이트가 달라질 수 있음을 기록하고, 모든 중간 이벤트가 필요한 업무에는 이벤트 스트림 의미를 유지합니다.',
 [('KTable은 데이터베이스 테이블과 완전히 같은가요?','키별 갱신 상태라는 의미는 비슷하지만 Kafka 로그와 분산 local store를 바탕으로 갱신됩니다. 임의의 SQL DB 기능을 자동 제공하지 않습니다.','조회 일관성·키 위치·복구 상태를 별도 설계해야 합니다.'),('인스턴스를 늘리면 모든 집계가 빨라지나요?','Task 수와 키 편중이 상한을 만듭니다. 한 키의 직렬 집계는 한 담당 Task에 집중될 수 있습니다.','파티션·Task·Thread·Instance를 구분해 병목을 진단합니다.')],
 ['streams/core-concepts/','streams/architecture/','streams/developer-guide/dsl-api/'])
topic(31,
 '설정·Serde 준비 → StreamsBuilder → Topology 확인 → KafkaStreams 생성 → start → 상태 관찰 → close',
 '요리책이 Topology라면 KafkaStreams는 실제 조리대를 가동하는 장치입니다. 요리책을 작성했다고 음식이 나오지는 않으며 start가 필요합니다. 종료할 때는 불을 끄고 진행을 마무리하는 close가 필요합니다.',
 'Topology는 데이터가 통과할 노드와 연결을 정의하고 실행 중인 KafkaStreams는 소비자·생산자·상태 저장소·스레드를 관리합니다. application.id는 그룹과 내부 토픽 이름의 기반이므로 안정적으로 유지합니다. default Serde에 기대기보다 입력 Consumed, 출력 Produced, 집계 Materialized에 실제 타입을 명시하면 런타임 직렬화 오류를 줄일 수 있습니다. 상태 전환은 CREATED, RUNNING, REBALANCING, ERROR 같은 관측 지점으로 관리합니다.',
 'start 호출 뒤 바로 준비 완료라고 응답하면 state restoration 중인 인스턴스에 조회가 들어올 수 있습니다. readiness는 앱 상태와 필요한 store 조회 가능 조건을 반영합니다. uncaught exception handler는 원인을 기록하고 교체·종료 정책을 정하되 동일 영구 오류를 끝없이 재생하지 않습니다. Spring에서 관리할 때와 직접 main으로 lifecycle을 관리할 때 중복 start/close를 하지 않도록 소유자를 하나로 정합니다.',
 '같은 state.dir를 두 인스턴스가 공유하면 파일 잠금 충돌이 날 수 있습니다. application.id는 같게 하여 일을 나누되 각 인스턴스의 로컬 상태 경로는 충돌하지 않게 둡니다. 배포 스크립트가 application.id에 빌드 번호를 붙이면 매번 새 앱이 만들어져 재처리·내부 토픽 증가가 생길 수 있습니다.',
 '아래 학습 Streams 코드를 실행하고 topology.describe를 보관합니다. 같은 application.id와 다른 state.dir로 두 프로세스를 실행해 Task가 나뉘는지 확인합니다. graceful close와 강제 종료를 비교하며 복구 시간·중복 출력·state restore 로그를 기록합니다.',
 [('start가 반환하면 모든 store가 즉시 준비됐나요?','할당과 상태 복원이 진행될 수 있어 준비 상태를 따로 확인합니다.','조회 API의 readiness와 데이터 신선도를 함께 정의해야 합니다.'),('배포 버전마다 application.id를 바꿔도 되나요?','새 논리 앱과 내부 자원을 만들 수 있어 단순 배포 식별자로 쓰면 위험합니다.','같은 업무를 이어갈 안정 ID와 인스턴스·빌드 식별자를 분리합니다.')],
 ['streams/developer-guide/write-streams-app/','streams/developer-guide/config-streams/','streams/developer-guide/running-app/'])
topic(32,
 '입력 이벤트 → filter/map → 키 결정 → 필요 시 repartition → window/aggregate/join → 결과 갱신',
 '학교의 하루 출석을 세려면 학생 이름, 날짜, 늦게 도착한 학생 처리 규칙이 필요합니다. 집계도 키·시간 구간·늦은 이벤트 수용 범위를 정하지 않으면 정답이 모호합니다. 실행 코드 한 줄보다 결과 의미를 먼저 정의해야 합니다.',
 'mapValues는 키를 유지하지만 selectKey나 map으로 키를 바꾸면 후속 집계·조인에서 repartition이 필요할 수 있습니다. groupByKey().count()는 이벤트 수 집계이고 같은 eventId가 다시 입력되면 기본적으로 다시 셉니다. 윈도우는 event time과 grace를 기준으로 늦은 이벤트를 처리하며 단순 벽시계 타이머와 다릅니다. stream-table join과 stream-stream join은 트리거·상태·시간 조건이 달라 같은 join이라는 이름으로 묶어 이해하면 안 됩니다.',
 '코파티셔닝은 같은 논리 키가 대응되는 파티션에 위치하도록 파티션 수와 파티셔닝 방식이 맞아야 함을 뜻합니다. 조인 키가 null이거나 값이 tombstone인 경우 연산별 의미가 다릅니다. Suppress와 캐시·커밋 설정은 중간 업데이트가 외부에서 언제 보이는지에 영향을 주며 최종 결과 요구와 지연·메모리 요구를 함께 검토합니다.',
 '입고량 집계가 실제보다 두 배라면 원본 업무 중복 발행과 Consumer 재처리 입력을 구분합니다. EOS를 켠다고 동일 eventId 두 레코드를 논리적으로 한 건으로 합쳐 주지는 않습니다. dedup store를 사용하면 키 범위·보존 기간·메모리·장기 재처리 시 의미까지 설계해야 합니다.',
 'A 키에 1,2,3을 넣고 count 결과를 확인합니다. 같은 eventId를 다시 넣어 count가 늘어나는지 봅니다. event timestamp를 과거·미래로 조절하고 grace 안팎의 레코드를 넣어 실제 결과를 예상 표와 비교합니다. TestDriver와 실제 브로커 시험을 분리합니다.',
 [('mapValues와 map은 왜 구별하나요?','키 보존 여부가 뒤의 분산 집계·조인에서 재분배 필요성에 영향을 줍니다.','topology.describe로 repartition 토픽이 생기는 지점을 확인합니다.'),('윈도우가 끝나면 그 시각에 반드시 결과가 나오나요?','Streams의 stream time은 입력에 의해 진행되며 grace·suppress 설정도 관여합니다.','입력이 멈춘 경우와 늦은 입력이 있는 경우를 따로 시험해야 합니다.')],
 ['streams/developer-guide/dsl-api/','streams/core-concepts/','streams/developer-guide/dsl-topology-naming/'])
topic(33,
 '바이트 역직렬화 → Processor.init → process → store 읽기/쓰기 → forward → punctuate → close',
 'DSL이 조립식 가구라면 Processor API는 필요한 모양으로 직접 제작하는 공구입니다. 자유도가 높아진 만큼 상태·시간·전달·종료 책임도 직접 관리해야 합니다. 스레드 밖에서 임의로 store를 바꾸는 만능 탈출구는 아닙니다.',
 '새 Processor API의 org.apache.kafka.streams.processor.api 타입과 과거 API 패키지를 섞지 않습니다. Processor는 init에서 context와 store를 얻고 process에서 레코드별 계산과 전달을 수행합니다. record key/value/header/timestamp를 바꿀 때 공유 객체의 가변성을 조심합니다. Punctuation의 stream time은 이벤트 처리에 의해 전진하고 wall clock time은 실행 시각 기반 best effort이며 GC·처리 정지 중 정확한 cron처럼 실행을 보장하지 않습니다.',
 'Serde는 serializer와 deserializer의 쌍입니다. null 값, 문자 인코딩, 스키마 버전, 잘못된 바이트를 명시적으로 다룹니다. 입력은 String인데 집계값이 Long인 경우 store와 output Serde를 별도로 지정해야 합니다. 버전 바이트가 있는 포맷이라면 모르는 버전을 조용히 빈 객체로 바꾸지 말고 명확히 실패·격리하도록 설계합니다.',
 '모든 데이터를 한 static Map에 보관하면 Task 이동·재시작 시 상태가 사라지고 인스턴스별 결과가 갈라집니다. 복구할 상태는 Task에 연결된 store에 두고 changelog·보존 정책을 검증합니다. Processor에서 외부 API를 매 레코드 동기 호출하면 poll 진행과 복구 비용을 크게 악화시킬 수 있습니다.',
 'ProcessorSupplier가 매번 새 Processor를 만드는지 확인하는 테스트를 작성합니다. 같은 객체를 여러 Task에 재사용하지 않습니다. stream-time punctuation은 새 timestamp 입력으로 진행시키고 wall-clock punctuation은 TestDriver의 시계 전진으로 검증합니다.',
 [('punctuate를 매분 정확히 실행되는 스케줄러로 써도 되나요?','정확한 외부 스케줄 보장이 아니라 Streams 실행·시간 모델 안의 콜백입니다.','입력 중단·GC·재시작에서 어떤 호출이 생기는지 시험해야 합니다.'),('serde 오류는 데이터를 무시하면 되나요?','업무 누락을 만들 수 있어 실패·격리·관측 정책을 정해야 합니다.','원본 바이트·스키마 버전·eventId를 안전하게 추적할 수 있어야 복구 가능합니다.')],
 ['streams/developer-guide/processor-api/','streams/developer-guide/datatypes/','streams/developer-guide/testing/'])
topic(34,
 '결정적 입력 테스트 → 시간·상태 검증 → 실제 브로커 시험 → store 위치 조회 → 서비스 응답·메모리 관찰',
 '비행 시뮬레이터는 조종 논리를 반복 연습하기 좋지만 실제 공항의 무전·날씨·혼잡을 모두 검증하지는 못합니다. TopologyTestDriver는 계산·상태·시간 의미를 빠르게 검증하고 실제 Kafka 시험은 네트워크·트랜잭션·복구·리밸런스를 검증합니다.',
 'TestDriver는 실제 브로커 없이 입력·출력 토픽과 store를 다루는 동기 테스트 도구입니다. 실제 분산 할당·복제·ACL·브로커 EOS를 입증하는 도구로 보고하지 않습니다. Interactive Queries는 로컬 store를 조회하며 키가 다른 인스턴스에 있으면 metadata를 이용한 별도 라우팅/RPC 계층을 애플리케이션이 제공해야 합니다. 조회 순간 store가 복구·이동 중일 수 있어 재시도·준비 상태·오래된 값 허용 정책을 정합니다.',
 '메모리는 heap만 보지 않습니다. RocksDB native memory, block cache, memtable, page cache, state cache, 직접 버퍼, 스레드별 비용을 모두 합칩니다. store와 파티션 수가 많으면 동일한 per-store 설정도 총량이 커집니다. 복원 시간은 대략 복구할 바이트/실효 복원 속도로 추정하되 디스크 쓰기·압축·다른 트래픽 경쟁까지 시험해야 합니다.',
 'JVM heap은 여유인데 컨테이너 OOMKilled가 나면 native memory와 page cache를 포함한 cgroup 사용량을 확인합니다. heap dump만으로 전체 소비를 설명할 수 없습니다. 조회 실패를 404로 바꾸면 아직 복원 중인 키를 존재하지 않는 데이터로 잘못 응답할 수 있습니다.',
 'TopologyTestDriver에 정상·중복·null·늦은 이벤트를 넣고 출력과 store를 검증합니다. 실제 브로커에서는 인스턴스 종료·재배정 중 조회 요청을 보내고 404, 재시도 가능 오류, 정상 응답을 구분합니다. 메모리는 컨테이너 제한 안에서 부하를 단계적으로 올립니다.',
 [('TestDriver가 통과하면 EOS도 검증됐나요?','계산 의미의 단위 시험과 브로커의 트랜잭션·장애 동작은 다른 검증입니다.','실제 브로커에서 kill·재시작·read_committed 결과를 별도 시험해야 합니다.'),('Interactive Queries가 자동으로 다른 서버를 호출하나요?','메타데이터는 라우팅에 도움을 주지만 RPC 계층을 자동 구현해 주지는 않습니다.','인증·timeout·재시도·리밸런스 중 위치 변화를 앱에서 설계합니다.')],
 ['streams/developer-guide/testing/','streams/developer-guide/interactive-queries/','streams/developer-guide/memory-mgmt/'])
topic(35,
 '배포 준비 → 호환 Topology·ACL 확인 → 점진적 인스턴스 교체 → Task 이동·상태 복원 → 업무 결과 대조',
 '교대 근무에서 직원만 바꾸는 것이 아니라 진행 장부를 옮기고 따라잡는 시간이 필요합니다. Streams 리밸런스는 단순 연결 재시도가 아니라 Task와 상태의 소유권 이동을 동반할 수 있습니다. standby는 장부 사본을 미리 준비해 두는 전략입니다.',
 'standby Task는 changelog를 따라 상태를 유지하므로 장애 후 복원량을 줄일 수 있지만 메모리·디스크·네트워크 비용을 사용합니다. 인스턴스·Task·thread 구성과 rack-aware 배치 조건에 따라 실제 보호 범위가 달라집니다. Streams의 새 rebalance protocol은 일반 Consumer의 group.protocol 전환과 혼동하지 말고 4.3의 Streams 전용 설정·전환 제한을 확인합니다. 상태 포맷·store 이름·repartition 토픽 이름은 Topology 변경 호환성의 일부입니다.',
 'Streams 계정에는 입력 READ, 출력 WRITE, application 그룹 및 내부 changelog/repartition 토픽 관련 권한을 검토합니다. auto-create를 막는 운영 환경에서는 내부 자원을 사전 준비하는 절차가 필요할 수 있습니다. EOS는 Kafka 출력과 상태·offset 경계에 관한 보장이고 외부 API를 한 번만 실행하게 만드는 기능이 아닙니다. 배포 성공은 프로세스 기동뿐 아니라 restore 완료·lag 회복·최종 집계 대조로 판정합니다.',
 '노드 교체를 너무 빠르게 연속 진행하면 이전 Task가 복원되기 전에 또 이동하여 처리 중단이 길어질 수 있습니다. 대시보드에서 REST 프로세스가 살아 있는지만 보면 이를 놓칩니다. restore bytes/rate, Task 상태, 입력 age, 출력 집계·eventId 대조를 함께 사용합니다.',
 '두 인스턴스에서 상태 있는 집계를 실행하고 standby 0과 1을 각각 시험합니다. 한 인스턴스 강제 종료 뒤 첫 정상 처리까지 걸린 시간과 복구 바이트를 비교합니다. 같은 application.id에 호환·비호환 Topology 변경을 별도 실습 환경에서 검증하고 운영 reset 명령과 섞지 않습니다.',
 [('standby가 있으면 장애 전환은 항상 즉시인가요?','감지·재할당·남은 changelog 적용·초기화 시간이 있어 무중단을 보장하지 않습니다.','실제 RTO는 상태 크기·배치·경쟁 부하 조건에서 측정해야 합니다.'),('배포에서 store 이름을 바꾸는 것도 위험한가요?','내부 토픽·상태와 연결되어 재사용·복원·호환성에 영향을 줄 수 있습니다.','topology.describe 비교와 버전별 업그레이드 가이드를 검토해야 합니다.')],
 ['streams/developer-guide/running-app/','streams/developer-guide/security/','streams/developer-guide/streams-rebalance-protocol/','streams/upgrade-guide/'])
# Detailed counterexamples used for the transfer exercises. Each entry contains
# a falsifiable claim and the specific evidence needed to test it.
COUNTER={
1:('같은 토픽을 읽는 모든 서비스는 서로 일을 나눈다','서로 다른 그룹은 각각 읽습니다. 배송 그룹의 처리와 알림 그룹의 처리를 eventId별로 비교하면 독립 소비를 확인할 수 있습니다. 같은 그룹인지 다른 그룹인지 설명 없이 Consumer 개수로 병렬성을 계산하면 안 됩니다.'),
2:('압축을 켜면 지연이 반드시 줄어든다','CPU가 포화라면 압축 비용이 더 크게 나타날 수 있습니다. 네트워크 전송 바이트 감소와 CPU·p99 증가를 함께 기록해야 성능 개선 여부를 판단할 수 있습니다. 메시지마다 이미 압축된 데이터라면 배치 압축 효과도 작을 수 있습니다.'),
3:('힙을 늘리면 읽기 캐시도 늘어난다','OS 페이지 캐시와 JVM 힙은 다릅니다. 총 메모리가 같은 상태에서 힙만 늘리면 페이지 캐시가 줄어 디스크 읽기가 증가할 수 있습니다. GC와 cache hit를 구별해 봅니다.'),
4:('Future 실패는 메시지가 로그에 없다는 뜻이다','서버 적용 후 응답 유실이면 이미 기록되었을 수 있습니다. 실패 eventId를 다시 조회하고 안정적인 ID로 재시도하는 실험이 이 주장을 반박합니다.'),
5:('MANUAL에서 ack를 생략하면 현재 레코드에 멈춘다','정상 반환으로 poll position은 진행할 수 있으며 후속 ack가 앞 위치까지 포함해 커밋할 수 있습니다. position, committed, listener 호출 기록을 함께 남기면 차이가 보입니다.'),
6:('retention.ms가 지나면 그 레코드가 즉시 지워진다','세그먼트 roll과 정리 주기에 따라 삭제가 늦어질 수 있습니다. 설정 시각과 실제 log start 이동 시각을 비교합니다. 아직 활성 세그먼트라면 개별 레코드 시각만으로 삭제 시점을 예측하지 않습니다.'),
7:('dry-run이면 적용 결과도 완전히 검증된다','dry-run은 실행 예정 위치를 보여 주는 단계입니다. 실제 Consumer 재개, 외부 DB 중복, 생성되는 부작용을 검증하지 않습니다. 별도 업무 대조가 필요합니다.'),
8:('컨트롤러가 세 대면 모든 데이터가 세 사본이다','metadata quorum 구성과 토픽 RF는 독립입니다. Admin으로 실제 파티션 replicas를 조회해 RF=1 토픽이 존재할 수도 있음을 확인합니다.'),
9:('lag 합계가 줄면 모든 파티션이 회복 중이다','나머지 파티션이 빠르게 처리되면서 한 핫 파티션만 계속 뒤처질 수 있습니다. 합계와 max, partition별 증가율을 같이 비교해야 합니다.'),
10:('평균 부하가 30%면 한 대 장애에도 항상 안전하다','리더·키 분포와 네트워크·스토리지 한도가 균등하다는 보장이 없습니다. 장애 후 가장 바쁜 노드와 복구 트래픽을 포함해 시험해야 합니다.'),
11:('패치 버전은 장애 의미가 없어 생략해도 된다','4.3.1처럼 특정 복구·재시작 결함을 수정하는 패치가 있습니다. 사용하는 기능과 릴리스 노트를 매칭하고 회귀 시험을 해야 합니다.'),
12:('KafkaConsumer에 옵션 하나를 주면 Share 모델이 된다','별도 API·그룹 모델을 사용합니다. 동일한 이름의 poll/ack 개념이 있어도 레코드 잠금·재전달 의미가 다릅니다.'),
13:('bootstrap 접속 성공은 전체 Kafka 접속 성공이다','메타데이터가 반환한 리더·코디네이터 주소가 클라이언트 네트워크에서 막혀 있을 수 있습니다. 노드별 주소·TLS·권한을 검사해야 합니다.'),
14:('tasks.max와 Worker 개수 중 큰 값만큼 병렬 처리한다','Connector가 생성한 실제 Task 수와 외부 분할 가능성이 상한입니다. status의 task 목록과 각 Task 처리량으로 확인합니다.'),
15:('application.id는 단순 로그 라벨이다','그룹·내부 토픽·상태 복구 식별에 연결됩니다. 바꾸면 새로운 처리 이력이 생길 수 있어 배포 빌드 번호를 붙이면 위험합니다.'),
16:('Admin 전체 Future 하나만 성공이면 상태 조회는 필요 없다','Controller 처리와 각 노드의 상태 전파가 순간적으로 다를 수 있고, 요구 설정이 의도와 다를 수도 있습니다. 자원별 실제 describe 결과로 사후 검증합니다.'),
17:('원격 보존을 늘리면 로컬 사용량도 같은 비율로 증가한다','원격과 로컬 보존 정책은 따로 관리합니다. 업로드 진행·로컬 제거 상태를 함께 봐야 합니다. 단, 원격 업로드 장애 시 로컬 로그가 예상보다 오래 남는 상황도 검증합니다.'),
18:('TCP read 한 번에 Kafka 프레임 하나가 온다','분할 수신·합쳐진 수신이 가능합니다. 길이 필드만 받았을 때와 본문이 일부만 왔을 때 파서가 대기하는지 단위 시험으로 반박합니다.'),
19:('max.poll.records는 네트워크 fetch 전체 메모리 한도다','애플리케이션에 반환하는 레코드 수와 미리 fetch한 배치 바이트는 다릅니다. 압축 해제·역직렬화 메모리도 포함해 관찰합니다.'),
20:('Consumer가 죽으면 컨트롤러가 직접 파티션을 배정한다','그룹 조정은 Group Coordinator 역할입니다. 데이터 리더와 메타데이터 컨트롤러가 처리하는 장애와 구분해야 적절한 로그를 찾을 수 있습니다.'),
21:('권한 없는 토픽 하나가 있으면 전체 CreateTopics가 롤백된다','자원별 결과를 확인해야 합니다. 만들어진 토픽과 실패 토픽이 공존할 수 있어 요구 상태 재조회가 필요합니다.'),
22:('최신 client면 오래된 broker에서도 모든 기능을 쓴다','API별 공통 버전과 브로커 기능 지원이 필요합니다. 연결·생산 성공과 트랜잭션·새 그룹 기능의 지원을 구분해 시험해야 합니다.'),
23:('DR은 Consumer bootstrap만 바꾸면 끝난다','쓰기 주체 통제, 복제 진행, offset 변환, target ACL·스키마·외부 시스템 준비가 필요합니다. failback도 별도 검증합니다.'),
24:('hostname 검증을 끄면 인증서 문제가 해결된다','원인인 이름 불일치를 숨기는 것입니다. 실제 DNS·SAN을 일치시키고 신뢰 체인을 검증해야 서버 신원을 확인할 수 있습니다.'),
25:('비밀번호가 맞으면 모든 Kafka 작업이 허용된다','인증 뒤에도 principal의 Topic·Group·Cluster·TransactionalId 권한 판단이 남습니다. 인증 성공 로그와 인가 실패 응답이 함께 나타날 수 있습니다.'),
26:('ACL에 prefix를 쓰면 정규식처럼 어느 위치든 매칭된다','자원 이름 시작 부분을 기준으로 합니다. 환경 prefix를 잘못 정하면 의도치 않은 자원을 포함하거나 정상 자원을 제외할 수 있습니다.'),
27:('SMT로 상태 있는 모든 업무 규칙을 구현해도 된다','레코드 단위 변환과 분산 상태·외부 호출을 포함한 업무 처리의 운영 책임이 다릅니다. 복구와 테스트가 어려워지면 별도 처리 애플리케이션이 적합할 수 있습니다.'),
28:('put에서 비동기 작업을 접수하면 flush도 완료다','외부 시스템이 영속 저장을 확인한 경계가 필요합니다. 프로세스를 종료하고 재시작해 미완료·중복이 생기는지 시험합니다.'),
29:('errors.tolerance=all이면 모든 Task 오류가 DLQ로 간다','지원되는 변환·처리 단계와 Connector별 예외를 구분해야 합니다. 외부 Sink 영구 장애까지 전부 건너뛴다고 가정하면 안 됩니다.'),
30:('KTable은 같은 키의 모든 중간 이벤트를 보관한다','KTable은 갱신 상태 의미이고 캐시·커밋에 따라 downstream 중간 업데이트가 합쳐질 수 있습니다. 이벤트 이력이 필요하면 KStream과 원본 로그를 유지합니다.'),
31:('Topology를 build하면 앱이 Kafka 소비를 시작한다','실제 KafkaStreams lifecycle의 start가 필요합니다. 단위 시험에서 Topology가 만들어진 것과 실행 환경에서 그룹에 참여한 것을 구분합니다.'),
32:('exactly once면 동일 eventId를 두 번 넣어도 count가 같다','Kafka 트랜잭션 중복 보호와 업무 레벨 dedup은 다릅니다. 서로 다른 입력 레코드 두 개는 기본 count에 두 번 반영됩니다.'),
33:('wall-clock punctuation은 정확한 cron이다','Streams 처리 정지·GC·스케줄링 영향을 받는 best effort입니다. 외부 마감 업무에는 별도의 영속 스케줄·멱등 설계가 필요합니다.'),
34:('heap만 여유면 컨테이너 OOM은 안 난다','RocksDB native memory·직접 버퍼·페이지 캐시 등도 컨테이너 사용량에 영향을 줍니다. JVM 지표와 cgroup 총 사용량을 함께 봅니다.'),
35:('standby가 있으면 리밸런스 복구 시간이 0이다','감지·배정·남은 상태 적용·초기화가 필요합니다. 실제 부하에서 standby 유무별 RTO를 측정해 비교해야 합니다.')}
FOUNDATIONS=[
('로그·상태·진행 위치를 서로 다른 장부로 구분하기', '''입고 이벤트 한 건을 추적할 때 장부를 세 개로 나눠 생각해 봅시다. 첫째는 Kafka에 실제로 들어 있는 레코드 로그, 둘째는 Consumer 그룹이 어디부터 다시 시작할지 저장한 진행 위치, 셋째는 MySQL의 실제 입고 결과입니다. 세 장부가 같은 시스템에 저장된다고 가정하면 거의 모든 정합성 설명이 틀어집니다. Kafka가 레코드를 오래 보관해도 Consumer가 앞서 커밋했다면 업무 누락이 생길 수 있고, DB가 성공해도 커밋이 실패하면 재처리가 생길 수 있습니다.
일반 Kafka Consumer에서 offset 104까지 성공했다면 다음 복구 위치는 105입니다. offset은 파티션마다 독립이므로 P0의 105와 P1의 105는 서로 다른 위치입니다. 로그 정리와 트랜잭션 제어 레코드 등의 영향 때문에 offset 차이를 곧바로 업무 건수로 바꾸면 안 됩니다. 키가 같은 레코드도 서로 다른 offset을 얻을 수 있습니다. eventId는 업무 이벤트의 정체성, offset은 특정 로그의 위치라는 차이를 기억하세요.
처리 순서를 시간선에 놓으면 문제가 단순해집니다. t1에서 poll이 100~109를 반환하고, t2에서 DB에 100~104를 반영하고, t3에서 프로세스가 죽었다고 해봅시다. 커밋이 100에 남아 있으면 재시작 후 앞 다섯 건이 다시 올 수 있습니다. 커밋을 110으로 미리 옮겼다면 뒤 다섯 건을 건너뛸 수 있습니다. 안전한 진전은 파티션별 연속 성공 경계를 기록하는 것입니다. 단순히 완료된 레코드 중 가장 큰 offset을 커밋하는 것은 병렬 처리에서 안전하지 않습니다.
Kafka 트랜잭션으로 Kafka 입력 offset과 Kafka 출력을 묶을 수 있어도 별도 DB의 성공이 자동으로 포함되는 것은 아닙니다. 업무 결과에 고유 eventId를 기록하고 같은 트랜잭션에서 재고 변경과 함께 확정하는 방식이 필요할 수 있습니다. 이 원리는 Producer·Connect·Streams·DR에서도 반복됩니다. 단, 각 도구의 진행 위치 저장 방식과 트랜잭션 범위는 다르므로 같은 단어를 그대로 옮겨 붙이면 안 됩니다.'''),
('재시도를 세 가지 결과로 나누면 중복이 이해된다', '''네트워크 요청 결과를 성공·실패 두 가지로만 나누면 어려운 장애가 설명되지 않습니다. 결과는 성공 확인, 미적용이 확인된 실패, 적용 여부를 알 수 없는 결과로 나눠 봅니다. 서버가 레코드를 저장한 뒤 응답이 끊겼다면 클라이언트는 타임아웃을 보지만 서버에는 기록이 남을 수 있습니다. 그래서 타임아웃을 무조건 미기록으로 해석한 재시도는 중복을 만듭니다.
재시도하려면 무엇이 같은 요청인지 먼저 정해야 합니다. 클라이언트 라이브러리가 같은 전송을 재시도하는 것과, 사용자가 버튼을 다시 눌러 새 이벤트를 만드는 것은 다릅니다. Producer idempotence는 프로토콜의 Producer 식별·epoch·sequence를 사용해 전송 재시도 문제를 다룹니다. 새 프로세스가 새 eventId로 같은 주문 완료를 발행하는 문제까지 자동 해결하지 않습니다. 업무 멱등 키를 안정적으로 유지해야 하는 이유입니다.
Consumer 쪽에서는 eventId를 저장한 뒤 이미 처리됐는지 확인하고 업무 작업을 수행하는 경계가 중요합니다. 단순 SELECT 후 INSERT는 동시 실행 경쟁에 약합니다. DB의 UNIQUE 제약을 최종 방어선으로 쓰고, 중복 감지 기록과 업무 갱신을 같은 DB 트랜잭션에 넣습니다. 중복 표식만 먼저 별도 트랜잭션으로 커밋하면 업무 실패 뒤 재수신을 잘못 건너뛸 수 있습니다. 반대로 업무만 먼저 커밋하면 표식 기록 전 장애에서 중복을 막지 못합니다.
재시도 간격에는 backoff와 jitter를 사용해 여러 인스턴스가 동시에 외부 DB를 두드리지 않게 합니다. 최대 횟수만 정하는 것으로는 충분하지 않습니다. 총 경과 시간, 업무 마감, 보존 기간, 영구 오류의 격리와 소유자까지 정해야 합니다. DLQ는 처리 실패를 보관하는 경로이며 성공으로 바꾸는 마법이 아닙니다. DLQ 건수와 재처리 결과를 정상 처리 결과와 별도로 대조합니다.'''),
('복제·가시성·물리 저장의 보장은 같은 말이 아니다', '''Replica는 파티션의 사본입니다. replication factor가 3이면 보통 세 브로커에 해당 파티션 사본을 둡니다. Leader가 쓰기와 일반 읽기 요청을 담당하고 follower는 로그를 복제합니다. ISR은 현재 동기 상태로 간주되는 복제본 집합이며 RF 숫자와 항상 같지는 않습니다. 장애·지연으로 ISR에서 빠진 사본이 존재할 수 있습니다.
acks=all은 현재 ISR과 연관된 복제 확인이고 min.insync.replicas는 그 모드에서 쓰기를 허용하는 최소 ISR 수입니다. RF=3, minISR=2에서 한 사본이 이탈해 ISR=2가 되면 설정 조건 안에서 쓰기를 계속할 수 있습니다. ISR=1이 되면 쓰기 가용성을 제한하여 내구성 조건을 지키는 선택입니다. minISR=2가 언제나 정확히 두 대 응답만 기다린다는 뜻은 아닙니다. 요청 도중 ISR이 바뀌거나 응답이 유실되면 실패 응답과 실제 로그 상태를 별도로 살펴야 합니다.
복제 확인과 fsync는 다른 층입니다. Kafka는 파일시스템 로그와 OS 페이지 캐시를 활용하며 매 레코드마다 모든 디스크를 물리적으로 flush한다는 의미로 acks를 설명하면 안 됩니다. 모든 복제본이 같은 전원·스토리지 장애 도메인에 있으면 복제 수만으로 충분한 내결함성을 얻지 못합니다. 랙·가용영역 배치와 장애 모델을 함께 써야 합니다.
Consumer가 볼 수 있는 위치도 로그 끝과 구별합니다. High watermark는 복제에 따른 커밋 경계와 관련되고, read_committed에서는 미완료 트랜잭션의 영향을 받는 last stable offset이 중요합니다. 아직 완료되지 않은 트랜잭션 때문에 뒤 데이터의 가시성이 지연될 수 있습니다. 모니터링 도구가 어느 경계를 조회하는지에 따라 lag 해석도 달라집니다. ELR을 사용하는 4.3 구성에서는 ISR 밖이라도 안전하게 리더 후보가 되는 경우를 공식 ELR 문서와 함께 확인해야 하므로 과거의 ISR 설명을 무조건적인 전체 규칙으로 외우지 않습니다.'''),
('DB 정합성: Outbox와 소비 멱등성은 서로 다른 실패를 다룬다', '''DB 저장과 Kafka 발행을 차례로 호출하는 코드를 생각해 봅시다. DB가 먼저 성공하면 발행 전 장애에서 이벤트가 빠집니다. Kafka를 먼저 성공시키면 뒤 DB 롤백에서 실제로 없는 사실이 발행될 수 있습니다. @Transactional이 붙었다는 사실만으로 두 자원이 하나의 분산 트랜잭션이 되는 것은 아닙니다. 어떤 트랜잭션 매니저가 어느 자원을 관리하는지 확인해야 합니다.
Outbox는 업무 행과 발행할 이벤트 행을 같은 DB 트랜잭션에서 저장합니다. 별도 발행기가 미발행 행을 읽어 Kafka에 보내고 전송 완료를 표시합니다. 이때 Kafka 성공 뒤 DB의 완료 표시 전에 발행기가 죽으면 같은 Outbox가 다시 전송될 수 있습니다. 따라서 Outbox는 발행 의도 누락을 줄이는 설계이지 모든 중복을 없애는 장치가 아닙니다. Consumer의 eventId 기반 멱등성과 함께 사용합니다.
발행기를 여러 개 운영하면 같은 Outbox 행을 누가 맡는지 잠금·상태·lease 같은 소유권 전략이 필요합니다. offset이나 auto increment id가 항상 DB 커밋 순서를 대변한다고 가정하면 늦게 커밋된 행을 건너뛸 수 있으므로 조회 경계와 재스캔 정책을 검토합니다. DB 락을 잡은 채 외부 Kafka 응답을 오래 기다리면 잠금과 커넥션풀 정체를 키울 수 있습니다. 처리량과 정합성 모두를 보며 설계해야 합니다.
소비 멱등성에는 eventId만이 아니라 업무 규칙도 있습니다. 서로 다른 eventId로 같은 주문 완료가 두 번 만들어진다면 이벤트 중복 키만으로 막을 수 없습니다. 주문 상태 전이, 업무 명령 id, 버전 비교 같은 도메인 조건을 함께 사용합니다. 재고를 무조건 더하는 연산과 특정 버전의 상태로 갱신하는 연산은 중복에 대한 성질이 다릅니다. 어떤 중복을 막는지 문장으로 먼저 정의한 뒤 코드를 작성하세요.'''),
('배치·병렬성·역압력을 분리해서 계산하기', '''배치란 여러 작업을 묶어 고정 비용을 나누는 것이고 병렬성은 여러 작업을 동시에 진행하는 것입니다. JDBC batch를 쓰는 Consumer가 하나일 수도 있고, 여러 Consumer가 건별 SQL을 보낼 수도 있습니다. Producer의 네트워크 배치, Consumer poll의 레코드 묶음, Spring batch listener, DB bulk insert는 서로 다른 네 단계입니다. 하나를 켰다고 나머지도 자동으로 묶이지 않습니다.
일반 Consumer Group에서 한 토픽 파티션은 같은 시점에 한 멤버가 담당하므로 파티션 3개에 멤버 10개를 붙여도 그 토픽을 10개가 동시에 분할 소비하지 않습니다. 여러 토픽을 구독하면 전체 배정 가능 파티션을 봐야 합니다. 한 파티션의 특정 키에 일이 집중되면 전체 평균 CPU가 낮아도 그 키의 진행이 막힐 수 있습니다. 처리 순서를 유지해야 하는 단위와 확장 단위를 함께 정합니다.
DB bulk로 처리할 때는 배치 전체 롤백이 가능한지, 일부 성공을 반환하는지, 실패 레코드를 어떻게 찾는지 검증합니다. 100개 중 50개 성공 후 실패했는데 전체를 재시도하면 앞 50개가 중복될 수 있습니다. 외부 시스템이 원자적 batch를 제공하지 않으면 멱등 키와 안전한 연속 성공 경계를 관리해야 합니다. 가장 큰 offset 한 개만 커밋해서는 안 되는 이유가 여기에도 있습니다.
역압력은 처리 가능한 속도에 맞춰 유입·소비를 조절하는 전략입니다. 큐가 무제한이면 순간적인 처리량은 좋아 보여도 메모리와 업무 지연이 계속 증가합니다. pause/resume, 제한된 작업 큐, DB 커넥션 수, 외부 API rate limit을 함께 설계합니다. pause 중에도 그룹 생존·poll 요구 조건을 지켜야 하며 Consumer 객체를 여러 작업 스레드에서 임의 호출하면 안 됩니다. 속도가 빨라졌는지 최종 업무 완료율과 가장 오래된 대기 이벤트의 나이로 판단합니다.'''),
('시간·보존·재처리 가능 기간을 함께 보기', '''레코드의 event timestamp, Broker 도착 시각, Consumer 처리 시각, DB 반영 시각은 서로 다를 수 있습니다. 이벤트 시간 기반 통계를 처리 시각으로 계산하면 장애 후 재처리한 과거 이벤트가 오늘 실적으로 잡힐 수 있습니다. 반대로 잘못된 미래 timestamp는 윈도우 진행이나 유효성 검사에 영향을 줄 수 있습니다. 시간의 출처·단위·타임존을 스키마와 함께 정합니다.
retention은 Consumer가 읽었는지와 무관한 로그 보관 정책입니다. 그룹이 오래 멈추면 커밋 위치가 이미 정리된 구간을 가리킬 수 있습니다. 이때 auto.offset.reset의 선택에 따라 뒤에서 재개하거나 오류를 노출할 수 있지만 사라진 이벤트를 되살려 주지는 않습니다. 업무 복구 목표가 14일인데 로그는 7일만 보관한다면 별도 아카이브·원본 재추출 전략이 필요합니다.
compaction은 시간순 사건 이력을 전부 보존하는 것과 다릅니다. 키별 최신 상태를 재구성하는 데 유용하지만 중간 변경 내역이 정리될 수 있습니다. null value tombstone은 삭제를 뜻하고, 삭제 표식을 뒤늦게 읽는 복구 Consumer가 놓치지 않도록 관련 보존·복구 기간을 함께 검토합니다. 키가 없는 이벤트에 compaction을 무심코 적용하는 것도 올바른 상태 모델이 아닙니다.
재처리 전에 출력 부작용을 확인합니다. 통계 테이블을 새로 만드는 작업과 실제 고객에게 알림을 다시 보내는 작업은 위험이 다릅니다. 별도 그룹·출력 토픽·shadow 테이블로 먼저 재생하고 eventId 집합과 결과 합계를 비교하는 방법이 유용합니다. 검증된 결과를 서비스에 반영하는 단계와 원본을 읽는 단계를 분리하면 재처리 오류가 실제 업무를 다시 오염시키는 위험을 줄일 수 있습니다.'''),
('장애 조사에서 계층별 증거를 모으는 방법', '''장애를 "Kafka가 느리다"로 시작하면 원인이 너무 넓습니다. 먼저 최초 이상 시각, 영향을 받은 토픽·파티션·그룹·인스턴스, 사용자 증상을 적습니다. 그다음 앱의 입력·처리·DB·커밋 구간 시간을 나눕니다. Producer Future 대기와 DB 커넥션 대기를 같은 한 개의 응답 시간으로만 남기면 어느 쪽이 막혔는지 알기 어렵습니다.
네트워크 계층에서는 bootstrap뿐 아니라 메타데이터가 알려 준 모든 주소에 대한 DNS·포트·TLS를 확인합니다. 인증 계층에서는 메커니즘과 principal을, 인가 계층에서는 Topic·Group·TransactionalId 등 자원을 구분합니다. 데이터 계층에서는 직렬화·스키마와 키·offset·timestamp를 봅니다. 처리 계층에서는 외부 API·DB 잠금·커넥션풀·스레드 큐를 봅니다. 서로 다른 계층의 오류를 무조건 같은 재시도 분기로 보내지 않습니다.
모니터링에는 Kafka lag와 최종 업무 지연을 같이 둡니다. 생성률이 5000/s이고 처리율이 4000/s면 backlog는 초당 약 1000 증가합니다. 처리율을 7000/s로 높이면 순감소는 2000/s입니다. 60만 backlog를 없애는 데 약 300초라는 계산은 입력률·처리율이 일정하고 파티션 편중이 없다는 가정입니다. 가정과 실제를 비교하면 증설이 효과를 냈는지 빨리 판단할 수 있습니다.
복구 종료 기준도 미리 정합니다. 프로세스 재시작 성공은 첫 단계입니다. 할당 안정, ISR 회복, lag/age 감소, 오류율 회복, DB eventId·합계 대조까지 끝나야 업무 복구로 판단할 수 있습니다. 재처리를 했다면 중복 알림·재고 이중 증가가 없는지 별도로 확인합니다. 로그에 비밀번호·토큰·원본 개인정보를 남기지 않으면서도 eventId·파티션·offset·traceId를 연결할 수 있도록 설계하세요.'''),
('실험에서 주장할 수 있는 범위를 정하기', '''실습이 통과했다고 운영 안전성이 모두 입증되는 것은 아닙니다. 단일 브로커에서 Producer·Consumer가 동작한 것은 기본 연결과 코드 경로를 확인한 것입니다. RF=3의 내구성·브로커 장애·네트워크 분리·가용영역 장애를 검증한 것이 아닙니다. TopologyTestDriver는 계산 의미를 빠르게 검증하지만 실제 분산 리밸런스나 ACL·EOS 장애 복구를 대신하지 않습니다.
실험 전에 가설과 관측값을 씁니다. 예를 들어 "ack 생략만으로 position이 멈추지 않는다"는 가설이라면 listener 호출 offset, position, committed를 같은 시간축에 기록합니다. 재시작 뒤 재수신 여부만 보면 프레임워크의 오류 처리·커밋 타이밍에 따른 다른 원인이 섞일 수 있습니다. 실험 변수 하나를 바꾸고 다른 조건을 유지해야 인과를 설명하기 쉽습니다.
성능 실험은 레코드 수뿐 아니라 평균·최대 바이트, 키 분포, 압축률, RF/minISR/acks, 브로커 수, Consumer 수, DB 처리 조건을 적습니다. 평균 latency가 줄어도 p99가 나빠질 수 있으며, Kafka 전송량이 늘어도 최종 DB 처리율이 그대로면 전체 업무는 빨라지지 않았습니다. 비용·오류율·복구 시간을 같이 기록해야 운영 선택이 됩니다.
마지막으로 결과를 세 칸으로 나눠 보고합니다. "실행해 관측한 사실", "공식문서가 정의한 동작", "아직 시험하지 않은 가정"입니다. 예제 코드가 보인다는 이유로 실제 실행까지 완료했다고 쓰지 않습니다. 실패 실험은 정확한 환경과 복구·정리 절차를 포함해 다시 수행할 수 있게 보관합니다. 이 구분은 면접에서도 자신의 경험과 이론을 정직하고 설득력 있게 설명하는 데 도움이 됩니다.''')]
GROUPS={
'app':('Java/Spring에서 처리 경계를 실제 코드로 확인하기', '''아래 Lab은 토픽 이름을 매번 다르게 생성해 이전 실행의 커밋·데이터가 결과에 섞이는 것을 줄입니다. Producer는 10개 Future를 모은 뒤 결과를 확인하므로 각 send 직후 동기 대기로 배치를 끊지 않습니다. 전송 Future가 성공한 레코드의 파티션·offset을 출력하고 Consumer에서 같은 값을 관측합니다. bootstrap은 환경 변수로 바꿀 수 있지만 인증 설정은 별도 주입이 필요합니다.
Consumer는 auto commit을 끄고 poll한 레코드를 순서대로 관찰한 뒤 파티션별 다음 offset을 명시해 commitSync합니다. 이 예제는 stdout 출력을 업무로 취급하는 학습 코드이며 DB 트랜잭션을 구현한 것은 아닙니다. 실제 업무에서는 service 메서드의 DB 커밋이 성공한 뒤 오프셋 진전을 허용해야 합니다. DB가 성공하고 커밋 전에 죽는 경우는 여전히 재실행되므로 업무 멱등성이 필요합니다.
SpringConsumer는 MANUAL_IMMEDIATE를 사용하며 listener 스레드에서 ack를 호출합니다. 이 조건에서 즉시 커밋 시도가 이루어지며, ack 성공과 별도 DB 성공을 분산 원자 작업으로 묶지는 않습니다. 오류를 삼키고 정상 반환하지 않고 예외를 노출합니다. 학습 예제의 CommonContainerStoppingErrorHandler는 컨테이너를 정지시켜 원인 조사 뒤 재시작하도록 합니다. 운영에서는 재시도·DLT·중복·순서 정책을 업무별로 선택해야 합니다.
중복 방지 저장소를 붙인다면 listener에서 별도 스레드 큐에 접수만 하고 ack하지 마세요. 실제 영속 업무 완료 시점을 기다리거나, 원본 Kafka offset과 독립적으로 신뢰할 수 있는 영속 작업 큐에 안전하게 이관한 경계를 정의해야 합니다. HashSet·ConcurrentHashMap은 프로세스 재시작에서 사라지므로 이 교재의 관찰 코드와 운영 멱등 저장소를 혼동하면 안 됩니다.'''),
'infra':('서버·운영 설정을 앱에서 검증하는 작은 폐회로', '''브로커 설정을 바꿨다면 프로세스가 시작했다는 로그만 보지 말고 아래 Lab을 별도 테스트 토픽에서 실행합니다. Admin 생성·조회, Producer 쓰기, Consumer 읽기·커밋이 하나의 폐회로를 이룹니다. advertised.listeners가 틀리면 Admin의 초기 접속은 되어도 이후 특정 노드 요청에서 실패할 수 있습니다. 로그의 상대 노드 주소를 실제 앱 네트워크에서 확인합니다.
이 예제는 파티션 하나, RF=1로 만들어 한 대짜리 학습 브로커에서 재현 가능합니다. 따라서 이 결과로 ISR 장애 내구성, 브로커 한 대 상실, 컨트롤러 다수 상실을 검증했다고 말하면 안 됩니다. 복제 실험에는 최소 필요한 브로커와 RF·minISR를 별도로 구성하고 어느 노드를 언제 중단했는지 기록해야 합니다. Broker·Controller의 역할이 함께 있는지 분리되어 있는지도 적습니다.
설정은 기본값과 override를 구분합니다. 예를 들어 브로커의 log.retention.ms와 토픽 retention.ms는 같은 이름의 설정 파일 항목이 아닙니다. describeConfigs에서 ConfigEntry의 source·isDefault·isSensitive와 override를 확인하면 변경이 실제 어느 층에 적용됐는지 판단하기 쉽습니다. 조회에서 숨겨진 비밀 값은 null일 수 있으므로 그대로 원복 데이터로 저장하지 않습니다.
부하 실험에는 복구 구간을 포함합니다. 정상 상태 처리량을 측정한 뒤 한 노드 재시작, 리더 이동, 재처리와 동시 부하에서 p99·오류율·ISR·업무 지연이 어떻게 바뀌는지 비교합니다. 서버 수 산정은 평균 한 번의 결과를 곱하는 문제가 아닙니다. 최악으로 바쁜 파티션·노드와 복구 복제량을 감당할 수 있는지 시험해야 합니다.'''),
'protocol':('Java 클라이언트 로그와 와이어 프로토콜을 대응시키기', '''프로토콜 학습의 목적은 직접 TCP 클라이언트를 새로 만드는 것이 아니라 Java API 한 번 호출 뒤 어떤 서버·요청·응답·재시도가 이어지는지 설명하는 것입니다. 아래 Lab에서 createTopics, send, poll, commitSync를 분리해 실행하고 로그 시각을 기록하면 Metadata·Produce·Fetch·OffsetCommit 등의 흐름에 대응시킬 수 있습니다. 메서드 호출과 네트워크 요청이 항상 일대일은 아닙니다.
모든 레코드의 eventId, topic, partition, offset을 기록하되 correlation id와 혼동하지 않습니다. 한 Produce 요청은 여러 파티션의 여러 배치를 포함할 수 있고, 한 poll은 내부 버퍼에서 여러 레코드를 반환할 수 있습니다. API version은 요청별 스키마 번호이므로 제품 버전 4.3과 같은 숫자를 대입해 파싱하면 안 됩니다. 필요한 정확한 필드·오류는 공식 Protocol 문서의 해당 API version 행에서 확인합니다.
응답 오류를 네 묶음으로 분류해 보세요. 메타데이터가 바뀐 경우에는 새 리더·코디네이터를 찾을 수 있습니다. 일시 자원 부족은 backoff 후 재시도가 가능할 수 있습니다. 인증·인가·직렬화 오류는 설정·데이터 수정이 필요합니다. Timeout은 적용 여부 불명 상태를 포함할 수 있습니다. 라이브러리의 retriable 분류와 업무에서 안전하게 재실행할 수 있는지는 서로 다른 질문입니다.
실습 로그를 과하게 켜면 인증 정보나 원본 payload가 노출되거나 로그 I/O가 성능에 영향을 줄 수 있습니다. 실습용 더미 데이터에서 필요한 logger만 제한적으로 사용하고 요청 이름·버전·노드·오류·소요 시간으로 범위를 좁힙니다. 패킷 캡처가 암호화된 내용을 못 읽는 것은 TLS의 정상 동작이며 이를 보기 위해 운영 TLS를 끄는 방식으로 조사하지 않습니다.'''),
'connect':('Connect에서 데이터와 진행 위치를 함께 복구하기', '''Connect 실습은 Worker를 띄운 뒤 세 가지를 따로 확인합니다. REST로 Connector·Task 상태를 읽고, Kafka에서 실제 eventId를 읽고, 외부 원본·대상 시스템의 행을 대조합니다. Worker가 RUNNING인 것과 전체 데이터가 도착했다는 것은 다른 주장입니다. 학습에 쓰는 FileStream은 Connect 흐름을 관찰하는 예시이며 운영 CDC 성능·내구성 보증으로 확장하지 않습니다.
SourceTask가 원본 100번 행까지 읽고 Kafka 전송 전에 죽는 경우와, Kafka 성공 뒤 source offset 저장 전에 죽는 경우를 구분합니다. 전자는 다시 읽을 수 있어야 하고 후자는 중복 전송이 생길 수 있습니다. exactly-once source 지원은 Worker·Connector·외부 원본의 조건을 함께 확인합니다. SinkTask는 외부 시스템에서 완료되지 않은 레코드의 Kafka offset을 안전한 진행으로 보고하지 않아야 합니다.
외부 Sink에서 batch 100건 중 50건만 저장하고 timeout이 났다면 어떤 50건인지 아는지, 대상이 원자 batch를 제공하는지, eventId 기준 upsert가 가능한지 조사합니다. flush와 preCommit을 연결하지 않고 비동기 put 접수만 성공으로 보고하면 재시작에서 유실될 수 있습니다. 예외를 무조건 RetriableException으로 바꿔도 영구 오류는 사라지지 않으며 원본 보존 기간만 소모할 수 있습니다.
아래 Java Consumer는 Kafka 쪽 실제 레코드를 대조하는 관찰 도구로 사용할 수 있습니다. 별도 그룹에서 읽어야 실제 Sink 그룹의 offset에 영향을 주지 않습니다. 아래 Spring 예제는 Connector 코드가 아니라 같은 토픽을 읽는 애플리케이션 예시입니다. 프레임워크가 다르면 ack/flush의 의미도 다르므로 메서드 이름이 비슷하다는 이유로 같은 복구 경계라고 단정하지 않습니다.'''),
'streams':('Streams의 결과 의미·상태·분산 복구를 단계적으로 검증하기', '''아래 CountTopology는 키별 이벤트 개수를 세는 상태 있는 최소 예제입니다. null key와 null value는 이 예제의 정책으로 제외합니다. 모든 Streams 연산이 null을 이렇게 처리한다는 일반 규칙이 아닙니다. 입력 String/String, 출력 String/Long을 명시해 역직렬화 약속을 분리했고, store 이름을 event-counts로 고정하여 테스트에서 상태를 조회할 수 있게 했습니다.
키 A의 evt-1을 두 번 넣으면 count는 1 다음 2입니다. 이는 서로 다른 입력 레코드 두 개를 본 것이므로 EOS를 켰다고 자동으로 한 번만 세지는 않습니다. 업무 이벤트 중복 제거가 필요하면 eventId를 일정 기간 기억하는 store와 보존 정책을 설계합니다. 여러 파티션에 같은 eventId가 들어올 수 있다면 dedup 키와 repartition 위치도 함께 검토해야 합니다.
TopologyTestDriver 시험은 입력·출력·store 계산을 검증합니다. 실제 브로커의 transaction marker, offset 커밋, 리밸런스, ACL을 확인하는 시험은 별도입니다. 실습용 main은 RF=1 설정을 명시해 단일 브로커에서 실행하기 쉽도록 했지만 운영 내구성 추천이 아닙니다. 다중 인스턴스 시험에서는 application.id는 공유하고 state.dir는 충돌하지 않게 분리합니다.
출력 LongSerializer는 바이너리 8바이트 표현이므로 StringDeserializer 콘솔에서 "2"라고 보이지 않을 수 있습니다. 테스트는 LongDeserializer를 사용해 결과를 비교합니다. 출력이 이상하다고 Producer가 잘못 보냈다고 단정하지 말고 serializer·deserializer 쌍을 확인하세요. 입력·repartition·store·출력마다 자료형이 달라질 수 있으므로 각 경계의 Serde를 명시적으로 추적하면 오류를 줄일 수 있습니다.'''),
'security':('보안 장애를 Java/Spring 접속 경로에서 재현하기', '''보안 설정은 클라이언트가 실행되는 네트워크·파일 경로를 기준으로 확인합니다. truststore가 존재한다는 사실, 파일을 읽을 권한이 있다는 사실, 신뢰 체인이 올바르다는 사실은 각각 검증해야 합니다. 인증서 SAN에는 metadata가 반환한 실제 접속 DNS가 포함되어야 합니다. localhost 인증서로 컨테이너 DNS에 접속하는 실험은 이름 검증에서 실패하는 것이 정상입니다.
Java Properties에 security.protocol, sasl.mechanism, ssl.truststore.location 등 필요한 속성을 넣을 수 있습니다. Spring Boot에서는 spring.kafka.properties 아래로 전달할 수 있지만 이름·타입·별도 producer/consumer override를 확인해야 합니다. 이 교재의 평문 localhost 예제는 기능 학습용 기본값이며 보안 클러스터에는 그 상태로 접속하지 않습니다. 실제 비밀은 환경·외부 비밀 저장소에서 주입하고 설정 전체를 로그로 덤프하지 않습니다.
실패를 DNS/포트, TLS handshake, SASL authentication, Kafka authorization, 데이터 역직렬화로 구분해 봅니다. AuthenticationException과 TopicAuthorizationException을 같은 비밀번호 오류로 처리하면 권한 문제를 놓칩니다. 그룹 소비는 Topic READ와 Group 권한을 함께 검토해야 하고, 트랜잭션·Streams·Connect는 내부 자원 권한이 추가로 필요할 수 있습니다.
회전 실험은 기존 연결 유지 상태와 새 연결을 구분해야 합니다. 구 자격으로 연결된 앱이 정상이라고 새 인증서·비밀번호도 정상인 것은 아닙니다. 새 인스턴스의 접속 성공을 확인하고 단계적으로 기존 연결을 교체한 뒤 구 자격을 폐기합니다. TLS hostname verification을 끄거나 wildcard ACL을 임시로 준 경우를 정상 운영 해결책으로 남겨 두지 않습니다.''')}
def group(n):
 if n in [14,27,28,29]:return 'connect'
 if n in [15,30,31,32,33,34,35]:return 'streams'
 if n in [24,25,26]:return 'security'
 if n in [18,19,20,21,22]:return 'protocol'
 if n in [3,6,7,8,9,10,11,13,16,17,23]:return 'infra'
 return 'app'
COMMON_QA=[
('처리 성공과 커밋 성공 사이에 죽으면 어떤 일이 생기나요?', 'DB 성공 후 offset 커밋 전에 죽으면 같은 레코드를 다시 받을 수 있습니다. 소비 멱등성이 필요한 구간입니다. 커밋부터 한 뒤 DB가 실패하면 반대로 누락 위험을 만듭니다. 두 순서를 시간선으로 그려 어느 결과가 영속 저장됐는지 구분합니다.', '한 DB 트랜잭션 안에서 eventId 처리 표식과 업무 변경을 함께 확정하는지, 커밋 실패 후 재수신에도 결과가 유지되는지 시험하세요.'),
('한 파티션에서 병렬 처리한 가장 큰 offset을 커밋해도 되나요?', '완료된 최대 offset과 연속 완료 경계는 다릅니다. 100이 실패하고 101이 성공했는데 102를 커밋하면 재시작에서 100을 건너뛸 수 있습니다. 파티션별 빈틈 없는 성공 경계가 필요합니다.', '멀티스레드 큐의 완료 추적, 리밸런스 시 in-flight 처리, 중복 실행 방어를 함께 설계해야 합니다.'),
('새 그룹에 earliest를 주면 얼마나 오래된 데이터까지 읽나요?', '현재 보존되어 있는 가장 이른 유효 위치부터입니다. 이미 retention이나 compaction으로 제거된 사건을 되살리지 않습니다. 기존 그룹에 유효한 커밋이 있다면 auto.offset.reset이 매번 그 커밋을 무시하지도 않습니다.', '원본 재추출·아카이브가 필요한 재해 복구 기간과 Kafka 보존 기간을 비교해 보세요.'),
('같은 키면 모든 환경에서 영구적으로 같은 파티션인가요?', '같은 파티셔닝 조건과 파티션 수에서 매핑됩니다. 파티션 수·파티셔너·직렬화된 키 바이트를 바꾸면 새 레코드의 위치가 달라질 수 있습니다. 서로 다른 언어 클라이언트의 기본 파티셔너도 확인해야 합니다.', '기존 파티션의 미처리 이벤트와 새 파티션 이벤트가 동시에 처리될 때 업무 순서가 어떻게 되는지 검증하세요.'),
('한 번의 send나 poll이 한 번의 네트워크 왕복인가요?', '클라이언트는 버퍼·배치·메타데이터 조회·재시도를 수행합니다. send는 비동기 전송 결과를 반환할 수 있고 poll은 내부에 이미 가져온 데이터를 돌려줄 수 있습니다. 메서드 호출 수로 요청 수를 단순 계산하면 안 됩니다.', '프로듀서 request rate·batch size와 Consumer fetch 지표를 함께 계측하여 실제 왕복을 확인하세요.'),
('Timeout이 나면 무조건 같은 일을 다시 실행하면 되나요?', '서버 적용 후 응답만 유실됐을 가능성이 있습니다. 일시 장애 재시도와 업무 부작용의 안전한 재실행은 별개입니다. 안정적인 eventId·멱등 키·사후 조회를 사용해 결과 불명 상태를 처리해야 합니다.', '알림·결제·재고 증가처럼 되돌리기 어려운 외부 부작용에 어떤 대조·보상 경로가 있는지 답해 보세요.'),
('Kafka가 복제하면 별도 장애 복구 설계가 필요 없나요?', '복제본 수와 장애 도메인, 쓰기 확인 조건, 보존 정책, 클라이언트 진행 위치를 함께 봐야 합니다. 같은 지역 전체가 장애 나거나 애플리케이션이 잘못 커밋한 문제는 복제만으로 해결되지 않습니다.', '데이터 손실 허용 범위 RPO와 서비스 재개 시간 RTO를 정하고 실제 장애 실험으로 측정해야 합니다.'),
('오류를 catch하고 로그만 남기면 안전한가요?', '프레임워크가 정상 완료로 해석하여 뒤 offset으로 진행할 수 있습니다. 오류를 삼키는 행위가 처리 정책을 바꿀 수 있으므로 재시도·정지·격리 중 어떤 경로인지 명시해야 합니다.', '격리를 성공으로 셀지, 업무 미완료로 셀지 정하고 DLQ 수와 최종 업무 성공 수를 따로 계측하세요.'),
('성능을 높이려면 concurrency부터 올리면 되나요?', '파티션 수·키 편중·외부 DB 풀·잠금·API 제한이 상한을 만들 수 있습니다. 병목이 DB라면 Consumer 증설이 더 많은 대기와 재시도를 만들 수 있습니다.', '증설 전후 최종 업무 완료율과 p99·오류율이 어떻게 변해야 가설이 맞는지 먼저 정하세요.'),
('정확히 한 번 처리는 어떤 경계를 말해야 하나요?', 'Kafka 내부의 입력 offset·출력·상태를 묶는 보장과 외부 DB·HTTP 부작용은 구분해야 합니다. 동일한 업무 이벤트를 별도 레코드로 두 번 생성하는 것은 프로토콜 재시도 중복과도 다릅니다.', '면접에서는 도구 이름만 말하지 말고 원자적으로 묶이는 자원과 남은 실패 구간을 함께 설명하세요.'),
('가상 장애 시나리오와 실제 운영 경험을 어떻게 구별해 답하나요?', '실제로 측정한 값·환경·내가 실행한 조치와 공식문서를 통해 이해한 설계를 구분합니다. 이 교재의 장애 예시는 재현을 위한 가상 사례이며 특정 기업의 실사례로 주장하지 않습니다.', '직접 실험했다면 버전, 입력 데이터, 실패 주입 지점, 관측값, 복구 결과를 남기면 근거 있는 경험으로 설명할 수 있습니다.'),
('공식 기본값과 예제 설정이 다르면 무엇을 믿어야 하나요?', '기본값은 해당 버전·컴포넌트 공식 설정표에서 확인하고 예제는 학습 의도로 명시한 override로 읽습니다. 브로커 4.3과 오래된 Java 클라이언트·Spring 기본값이 같다고 가정하면 안 됩니다.', '운영 적용 전 실제 dependency tree, effective config, 토픽 override를 확인하고 지원 조합에서 회귀 시험하세요.')]

def paragraphs(text):return ''.join(p(x) for x in text.split('\n') if x.strip())

def build_addition(n):
 t=TOPICS[n];g=group(n); tag=f'{n:02}';topicname=f'study.lesson.{tag}'
 urls=[('Apache Kafka 4.3 · '+u, 'https://kafka.apache.org/43/'+u.replace('ops/','operations/')) for u in t['source']]
 # Extra foundational pages support the explicitly labelled standalone recap.
 for u in ['design/design/','configuration/producer-configs/','configuration/consumer-configs/','configuration/topic-configs/','operations/eligible-leader-replicas/']:
  url='https://kafka.apache.org/43/'+u
  if url not in [v for _,v in urls]:urls.append(('공통 원리 · '+u,url))
 urls += [('Spring Kafka: 수신 컨테이너·커밋','https://docs.spring.io/spring-kafka/reference/kafka/receiving-messages/message-listener-container.html'),('Spring Kafka: 오류 처리','https://docs.spring.io/spring-kafka/reference/kafka/annotation-error-handling.html')]
 intro=section('개정판 학습 지도: 이번 편의 요청을 끝까지 추적하기',
 p('<strong>기준:</strong> Apache Kafka 4.3 문서 · 예제 Kafka 4.3.1 · Java 21 · 개정 2026-10-19. Kafka 서버·Java 클라이언트·Spring API 버전을 구분합니다. 실습 범위와 실제 실행 검증 결과는 <a href="/learning/verification.html">검증 기록</a>에서 확인할 수 있습니다.')+
 p('<strong>전체 흐름:</strong> '+esc(t['flow']))+
 p('<strong>비유로 먼저 이해하기:</strong> '+t['analogy'])+
 p('처음 읽는다면 흐름의 화살표마다 입력, 실행 주체, 저장되는 결과, 다음 단계가 알 수 있는 사실을 구분해 보세요. 용어가 낯설면 아래 독립 학습용 공통 원리에서 로그·위치·복제·재시도를 먼저 확인한 뒤 돌아오면 됩니다. 기존 본문 뒤에도 코드와 실습, 심화 Q&A가 이어집니다.'),'revision-map')
 deep=section('개정 심화: 내부 원리와 설계 판단', '<h3>실제로 저장되고 이동하는 것은 무엇인가?</h3>'+p(t['mechanism'])+'<h3>설정을 선택할 때 따져야 할 경계</h3>'+p(t['decision'])+'<h3>가상 장애 사례: 증상에서 실패 구간으로</h3>'+p(t['incident'])+
 '<h3>이 주장을 반례로 검증해 보세요</h3>'+p('<strong>검증할 주장:</strong> “'+COUNTER[n][0]+'”')+p('<strong>반박과 확인할 증거:</strong> '+COUNTER[n][1]),'revision-internals')
 c=CASES[n]
 deep += section('단계별 해설: '+esc(c['title']),
  '<h3>상황과 비유</h3>'+p(esc(c['setup']))+
  '<h3>시간순으로 내부 동작 따라가기</h3>'+p(esc(c['trace']))+
  '<h3>직접 확인할 실습과 판단 기준</h3>'+p(esc(c['check']))+
  qa(c['question'],esc(c['answer']),'위 상황에서 성공했다고 판단한 시점을 하나 고르고, 그 직전에 프로세스가 종료되면 어떤 상태가 남는지 설명해 보세요. 답변은 실제 기록·업무 결과·재시작 위치를 구분해야 합니다.'),
  'revision-worked-case')
 shell=f'''# Kafka 4.3.1 배포 디렉터리에서 실행. 평문 localhost 학습 환경.
# 브로커는 별도 터미널: docker run --rm --name kafka-study -p 9092:9092 apache/kafka:4.3.1
bin/kafka-topics.sh --bootstrap-server localhost:9092 --create \\
  --topic {topicname} --partitions 3 --replication-factor 1
bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic {topicname}
bin/kafka-console-producer.sh --bootstrap-server localhost:9092 \\
  --topic {topicname} --property parse.key=true --property key.separator=:
# 위 터미널에서 아래 세 줄을 입력한 뒤 Ctrl-C
# A:evt-1
# A:evt-2
# B:evt-3
# 다른 터미널
bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 \\
  --topic {topicname} --group {topicname}.g1 --from-beginning \\
  --property print.key=true --property print.partition=true --property print.offset=true
# 소비 중인 상태에서 별도 터미널로 그룹 현황 확인
bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \\
  --describe --group {topicname}.g1'''
 lab=section('재현 실습: 입력·예상 결과·관측·복구까지',
 p('<strong>이번 편의 고유 실험:</strong> '+t['lab'])+
 p('먼저 아래 공통 입력으로 학습 토픽의 상태를 확인한 뒤 고유 실험을 수행합니다. 세 줄은 서로 다른 세 레코드이며 같은 A 키의 순서는 해당 파티션 안에서 봅니다. B가 어느 파티션인지 미리 가정하지 말고 출력에서 확인합니다. RF=1인 이 준비 환경으로 복제 내구성을 검증하지 않습니다.')+code(shell,'bash')+
 '<table><thead><tr><th>실험</th><th>예상</th><th>관측·판정</th></tr></thead><tbody>'+
 '<tr><td>같은 키 A 두 건</td><td>동일 파티션에서 입력 순서를 관찰</td><td>partition·offset·eventId를 함께 기록</td></tr>'+
 '<tr><td>새 그룹 g2</td><td>보존된 같은 레코드를 독립 소비</td><td>g1·g2의 committed를 따로 비교</td></tr>'+
 '<tr><td>같은 그룹 멤버 추가</td><td>파티션 배정이 재조정될 수 있음</td><td>할당과 처리 중단 시간 기록</td></tr>'+
 '<tr><td>커밋 전 강제 종료</td><td>재시작 시 재수신 가능</td><td>업무 반영·커밋·중복을 각각 대조</td></tr>'+
 '<tr><td>고유 실험 종료</td><td>주장의 참·거짓을 관측으로 판단</td><td>실행하지 않은 항목은 미검증으로 표시</td></tr></tbody></table>'+
 p('정리할 때는 Consumer를 모두 종료하고 자신이 생성한 study.lesson.'+tag+' 토픽·그룹·로컬 상태만 삭제합니다. 다른 실험이 공유하는 리소스가 없는지 조회한 뒤 실행하세요. reset·토픽 삭제·브로커 중단은 운영 클러스터에서 수행하는 명령이 아닙니다.'),'revision-lab')
 snippets=(ROOT/'examples/kafka-lab/src/main/java/study/TopicExamples.java').read_text()
 fragment=re.search(r'// LESSON '+tag+r' BEGIN\n(.*?)// LESSON '+tag+r' END',snippets,re.S).group(1)
 lab += section('이번 편 전용 Java 실험 코드: 핵심 API를 직접 대응하기',p('다음은 TopicExamples.java의 실제 컴파일 대상에서 가져온 이번 편 전용 메서드입니다. 파일 상단의 import와 클래스 문맥은 실행 프로젝트를 참고하세요. 선언만으로 네트워크 요청이나 설정 변경이 실행되는 것은 아니며, Admin 변경 메서드는 전용 실습 자원에서만 호출합니다. 공통 생산·소비 예제와 별도로 이 메서드가 이번 편의 어느 단계에 해당하는지 연결해 보세요.')+code(fragment,'java')+p('코드 읽기 순서: 인자로 받는 객체가 어떤 네트워크·그룹·자원을 소유하는지 먼저 확인합니다. 이어서 반환값이 접수 사실인지, 서버 확인인지, 실제 업무 결과인지 분류합니다. 실패가 난다면 다음 줄로 진행하면 안 되는 지점과 재시도 전에 조회할 상태를 표시하세요. 컴파일 검증과 특정 외부 환경에서의 실행 검증은 서로 다르며, 실행하지 않은 보안·Connector·원격 저장 시험은 미검증 범위에 남깁니다.'),'revision-topic-code')
 labpath=ROOT/'examples/kafka-lab/src/main/java/study'
 runtime=section('실습 환경을 고정하고 첫 실행 준비하기',p('Java 21 JDK에는 java와 javac가 모두 필요하고 Maven 3.9 이상을 사용합니다. java -version과 mvn -version에서 같은 JDK를 가리키는지 확인하세요. 아래 pom.xml은 학습 프로젝트의 실제 빌드 파일입니다. Spring Boot 앱의 pom에 그대로 덮어쓰는 설정이 아니며 서버 버전과 Spring·Java 의존성의 호환성 검증은 별개입니다.')+code('git clone https://github.com/thisisnew/thisisnew.github.io.git\ncd thisisnew.github.io/examples/kafka-lab\njava -version\nmvn -version\nmvn test','bash')+code((ROOT/'examples/kafka-lab/pom.xml').read_text(),'xml')+p('mvn test는 브로커 없이 TopologyTestDriver와 커밋 경계 테스트를 실행하고 Java/Spring 소스를 컴파일합니다. 실제 Kafka 생산·소비·커밋은 브로커를 별도로 시작한 뒤 study.Lab을 실행해야 합니다. DB 코드는 컴파일만 포함하며 schema.sql을 적용한 전용 MySQL 환경의 정합성·동시성 시험을 자동 완료한 것으로 해석하지 않습니다. 의존성 다운로드 실패는 코드 컴파일 오류와 구별하고 Maven이 실제 받은 라이브러리 버전은 dependency:tree로 확인할 수 있습니다.'),'revision-runtime')
 javacode=(labpath/'CountTopology.java').read_text() if g=='streams' else (labpath/'Lab.java').read_text()
 mainclass='study.CountTopology' if g=='streams' else 'study.Lab'
 java=section('Java 21과 Spring 코드로 연결하기',paragraphs(GROUPS[g][1])+
 p('전체 프로젝트: <a href="https://github.com/thisisnew/thisisnew.github.io/tree/main/examples/kafka-lab">examples/kafka-lab</a>. 아래 코드는 해당 소스 파일에서 직접 삽입하므로 실행 프로젝트와 본문이 따로 바뀌지 않도록 구성했습니다. 컴파일 대상 예제와 설명용 코드 조각의 검증 범위를 구분합니다.')+
 code('cd examples/kafka-lab\nmvn test\nmvn exec:java -Dexec.mainClass='+mainclass,'bash')+
 '<h3>'+esc(GROUPS[g][0])+'</h3>'+code(javacode,'java')+
 '<h3>Spring에서 같은 처리 경계를 연결하기</h3>'+p('다음은 Boot 자동 설정에 의존하지 않는 명시적 Spring 예제입니다. 기존 Boot 앱에서는 BOM을 유지하고 필요한 설정만 적용해야 합니다. Kafka 4.3 브로커 설명을 읽었다는 이유로 운영 앱의 의존성을 무조건 강제 교체하지 마세요. 보안 클러스터에는 인증·암호화 속성을 추가해야 합니다.')+
 code((labpath/'SpringConsumer.java').read_text(),'java')+
 p('코드 읽기 과제: 메서드 호출이 성공한 사실과 영속 저장이 성공한 사실이 어디에서 갈라지는지 표시하세요. listen의 stdout을 실제 DB 서비스로 바꾼다면 DB 예외를 삼키지 말고, DB 트랜잭션이 반환된 뒤 ack 경계를 정합니다. 별도 비동기 큐에 넣고 즉시 ack하는 변경은 다른 전달 모델이므로 그대로 안전하다고 판단하지 않습니다.'),'revision-code')
 if n in SPECIAL:
  title,body=SPECIAL[n]
  java += section(title,paragraphs(body),'revision-special')
 if g=='streams':
  java += section('실행 가능한 계산 검증: TestDriver 테스트 전체',p('이 테스트는 정상·중복·null 입력과 store 결과를 검증합니다. 실제 브로커 장애나 분산 EOS를 검증하는 시험은 아닙니다.')+code((ROOT/'examples/kafka-lab/src/test/java/study/CountTopologyTest.java').read_text(),'java'),'revision-test')
 java += section('코드로 계산하는 안전한 커밋 경계와 offset 공백',p('다음 계산기는 한 파티션에서 실제 전달된 순서 목록을 사용합니다. offset이 100,102,105라면 101·103·104가 없다는 이유만으로 실패라고 판단하지 않습니다. 로그 정리·제어 레코드 등으로 offset 공백이 가능하기 때문입니다. 반대로 실제 전달된 102가 실패했는데 105가 성공했다면 106으로 뛰어넘으면 안 됩니다. 이 계산은 한 배치의 의미를 보여 주는 예제이며 리밸런스·이전 in-flight batch·동시 작업을 관리하는 운영 commit manager가 아닙니다.')+code((labpath/'CommitBoundary.java').read_text(),'java')+code((ROOT/'examples/kafka-lab/src/test/java/study/CommitBoundaryTest.java').read_text(),'java')+p('실험에서 100과 102가 먼저 성공하고 101이 실패한 경우를 설명하세요. 가장 큰 성공 offset은 102이지만 안전하게 건너뛸 수 있는 경계는 101입니다. 반면 실제 전달 목록 자체가 100,102,105이고 모두 성공했다면 다음 경계는 106입니다. 숫자의 연속성과 실제 전달된 업무의 연속 성공을 구분해야 합니다. 파티션마다 독립적으로 계산하고, 재할당 후 이전 소유자의 완료 통지를 그대로 적용하지 않도록 소유권 경계를 별도로 관리합니다.'),'revision-boundary')
 java += section('실무 연결: 발행 결과 관찰과 DB 멱등 경계',p('같은 이벤트를 다시 받았을 때 재고가 두 번 증가하지 않도록 DB 유일 키와 업무 변경을 같은 로컬 트랜잭션에 넣는 예제입니다. 이 코드는 MySQL 전용 오류 1062를 중복 키로 분류하며 다른 SQL 오류까지 중복이라고 삼키지 않습니다. Kafka offset은 이 DB 트랜잭션에 참여하지 않습니다. DB commit 후 listener에서 ack하며, commit 직후 프로세스가 죽으면 재수신에서 marker가 중복 증가를 막는 구조입니다. DB commit 결과가 네트워크 장애로 불명인 경우에도 실패를 노출하고 안정적인 eventId로 재시도해야 합니다.')+code((labpath/'SpringPublisher.java').read_text(),'java')+p('Producer Future를 반환하면 호출자가 실패를 관찰할 수 있습니다. callback에서 로그만 남기고 업무 성공으로 바꾸는 예제와 구분하세요. 실무 Outbox 발행기에서는 전송 확인 뒤 완료 상태를 기록하되 그 사이 장애로 재발행될 수 있음을 전제로 합니다. payload에 같은 eventId를 유지하는 책임은 애플리케이션에 있습니다.')+code((ROOT/'examples/kafka-lab/schema.sql').read_text(),'sql')+code((labpath/'DedupJdbc.java').read_text(),'java')+p('사고 실험은 세 단계로 나눕니다. 첫 호출로 SKU-A가 0에서 10으로 바뀌고 marker가 생기는지 확인합니다. 같은 consumer_name과 eventId로 다시 호출하면 false가 반환되고 재고가 10에 남아야 합니다. 다른 eventId에 재고 행이 없는 sku를 넣으면 UPDATE 실패로 marker도 롤백되어야 합니다. 이 예제의 DB 동작은 별도 MySQL 통합 시험 대상이며 컴파일 성공만으로 DB 동시성과 장애 복구를 검증했다고 보고하지 않습니다.')+p('운영 적용에는 연결풀 상태 복구, 서비스의 트랜잭션 매니저, DB 격리 수준, 재시도, 이벤트 검증, 삭제·보존 정책, consumer_name의 안정성을 추가로 검토합니다. Spring의 관리 트랜잭션 안에서 이 메서드가 임의로 별도 connection을 만들도록 섞어 쓰지 말고, 같은 트랜잭션 경계로 맞춰 이식해야 합니다. 서로 다른 eventId로 같은 업무가 두 번 발행되는 문제에는 업무 키·상태 전이 조건도 필요합니다.'),'revision-jdbc')
 # Explicit shared material: not counted as topic-specific coverage in the audit.
 recap=section('독립 학습용 공통 원리: 이 편만 읽어도 필요한 배경', p('다음 여덟 절은 각 포스팅을 독립적으로 읽을 수 있도록 공유하는 배경 교재입니다. 여러 편을 순서대로 읽는다면 이미 이해한 절은 건너뛰고 이번 편 고유 실험과 Q&A에 집중하세요. 공유 배경의 분량을 주제별 신규 설명 분량으로 집계하지 않습니다.')+''.join('<h3>'+title+'</h3>'+paragraphs(body) for title,body in FOUNDATIONS),'revision-foundations')
 interview=section('심화 면접 Q&A: 답변·경계·꼬리 질문',p('답을 접고 먼저 소리 내어 설명해 보세요. “항상”, “무조건”이라는 말을 썼다면 그 주장이 깨지는 반례를 같이 말해 봅니다. 첫 질문들은 이번 편 고유 쟁점이고 이어지는 질문들은 분산 처리의 공통 실패 경계를 확인합니다.')+
 ''.join(qa(q,a,f) for q,a,f in t['questions'])+
 qa('“'+COUNTER[n][0]+'”라는 주장에 동의하나요?',COUNTER[n][1], '이번 편 실습에서 이 주장을 가르는 관측값을 하나 선택하고, 정상·실패에서 각각 어떤 값이 나올지 예측하세요.')+
 ''.join(qa(q,a,f) for q,a,f in COMMON_QA),'revision-interview')
 sources=section('개정판 출처와 검증 범위',p('Kafka 동작의 근거는 아래 4.3 공식문서입니다. Spring의 listener·ack·오류 처리 설명은 Spring 공식문서에 별도 근거를 둡니다. 비유·물류 예제·장애 시나리오·설계 선택은 학습을 위한 해설이며 공식문서의 직접 인용이나 특정 회사의 실제 사고 기록이 아닙니다.')+
 '<ul>'+''.join('<li><a href="'+esc(u)+'">'+esc(label)+'</a></li>' for label,u in urls)+'</ul>'+
 p('정확한 API 필드와 기본값은 사용 중인 패치 버전의 문서를 대조하세요. 공식 문서가 정의한 보장, 코드 컴파일·단위 시험, 실제 브로커 통합 시험, 아직 수행하지 않은 장애 시험은 <a href="/learning/verification.html">검증 기록</a>에서 구분합니다.'),'revision-sources')
 return intro,deep+lab+runtime+java+recap+interview+sources

# Original authored content stays versioned in git. Remove repeated generic
# filler sentences rather than inflate the lesson with boilerplate.
FILLER=[
'정확한 이해를 위해서는 이 기능의 입력값, 처리 단계, 처리 결과와 실패 시 복구 위치를 구분해야 합니다. Kafka는 네트워크로 연결된 여러 프로세스가 협력하므로 성공 응답과 최종 비즈니스 작업 완료는 다른 사건일 수 있습니다. 메시지의 키·파티션·오프셋을 로그에 함께 남기면 문제를 더 쉽게 추적할 수 있습니다.',
'검증할 때는 동일한 이벤트 ID로 여러 번 실행했을 때의 결과와 한 프로세스가 강제 종료됐을 때의 복구 결과도 확인해 보세요. 코드가 한 번 실행됐다는 사실과 데이터가 정확히 한 번 반영됐다는 사실은 구별해야 합니다.'
]
def render():
 rows=[]
 for n in range(1,36):
  path=ROOT/f'posts/kafka-study-{n:02}.html';text=path.read_text()
  # Allow deterministic regeneration without stacking additions.
  text=re.sub(r'<!-- REVISION-INTRO -->.*?<!-- /REVISION-INTRO -->','',text,flags=re.S)
  text=re.sub(r'<!-- REVISION-BODY -->.*?<!-- /REVISION-BODY -->','',text,flags=re.S)
  for x in FILLER:text=text.replace('<p>'+x+'</p>','')
  text=text.replace('같다고','같다고')
  text=text.replace('官方','공식').replace('다섯 가지 주요 API','여섯 가지 주요 API')
  text=text.replace('apache/kafka:4.3.0','apache/kafka:4.3.1')
  text=text.replace('committed(tp)', 'committed(Set.of(tp)).get(tp)')
  text=text.replace('config/kraft/server.properties','config/server.properties')
  text=text.replace('UnderReplicatedPartitions', 'UnderReplicatedPartitions')
  # Legacy references used outdated short URLs. Use the fetched 4.3 routes.
  text=text.replace('https://kafka.apache.org/43/ops/','https://kafka.apache.org/43/operations/')
  intro,tail=build_addition(n)
  text=re.sub(r'(</h1>)',lambda m:m.group()+ '<!-- REVISION-INTRO -->'+intro+'<!-- /REVISION-INTRO -->',text,count=1)
  text=text.replace('</main>','<!-- REVISION-BODY -->'+tail+'<!-- /REVISION-BODY --></main>')
  if '/assets/study-tools.js' not in text:text=text.replace('</body>','<script src="/assets/study-tools.js" defer></script></body>')
  if '/assets/study-reading.css' not in text:text=text.replace('</head>','<link rel="stylesheet" href="/assets/study-reading.css"></head>')
  path.write_text(text)
  rows.append(dict(lesson=n,bytes=len(text.encode()),topic_chars=sum(len(str(v)) for v in TOPICS[n].values()),worked_case_chars=sum(len(v) for v in CASES[n].values()),source_urls=['https://kafka.apache.org/43/'+u.replace('ops/','operations/') for u in TOPICS[n]['source']]))
 (ROOT/'learning/lesson-audit.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 print(json.dumps({'lessons':len(rows),'min_bytes':min(r['bytes'] for r in rows),'max_bytes':max(r['bytes'] for r in rows)},ensure_ascii=False))
if __name__=='__main__':render()
