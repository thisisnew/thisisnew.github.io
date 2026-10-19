{"n":12,"title":"세대별 GC: 짧게 사는 객체를 싸게 정리하는 방법","desc":"세대 가설·Eden·Survivor·승격·Old→Young 참조·카드와 write barrier를 연결한다"}

## 1. 매번 창고 전체를 검사하면 비싸다

검수용 일회성 포장재는 금방 버려지고 장기 보관 장비는 오래 남는다고 생각해 봅시다. 모든 쓰레기 수거 때 장기 보관 구역까지 전부 뒤지면 비용이 큽니다. 생성된 지 얼마 안 된 객체가 많이 사라진다는 관찰을 활용해 어린 객체와 오래 살아남은 객체를 구분하는 것이 세대별 GC의 출발점입니다.

**약한 세대 가설**은 많은 객체가 어린 나이에 죽는다는 경험적 성향입니다. 언어의 보장이나 모든 프로그램의 법칙이 아닙니다. 대형 캐시를 채우는 시점에는 새 객체가 많이 살아남을 수 있고, 처리 중인 요청이 지연되면 평소 짧게 살던 DTO도 더 오래 유지됩니다.

## 2. Young·Eden·Survivor·Old

| 용어 | 일반적인 의미 | 주의점 |
|---|---|---|
| Young | 새 객체를 주로 다루는 세대 | JVM 전체 Heap과 동일하지 않음 |
| Eden | 일반적인 새 할당의 출발 영역 | 모든 수집기의 모든 객체에 적용되는 법칙 아님 |
| Survivor | Young 수집 뒤 살아남은 객체의 공간 | 정확한 배치·규칙은 수집기에 따라 다름 |
| Old | 오래 생존했거나 특정 조건으로 배치된 객체 | 살아 있다는 뜻이지 영구 생존 보장 아님 |
| Promotion | 객체가 Old 쪽으로 이동 | 특정 age 하나로만 결정되지 않을 수 있음 |

Serial·Parallel의 연속된 세대 공간 그림과 G1의 Region 기반 세대는 물리 배치가 다릅니다. G1도 Young·Old라는 논리적 세대를 가지지만 Eden·Survivor·Old Region이 여러 위치에 배정될 수 있습니다. 모든 JVM의 Heap을 반드시 Eden:S0:S1:Old의 고정 비율로 그리면 안 됩니다.

## 3. 살아남은 객체를 복사하는 이유

Young 안에서 대부분 사라진다면 죽은 객체를 하나씩 복잡하게 정리하기보다 살아 있는 소수만 다른 공간으로 옮기는 것이 유리할 수 있습니다. 수집 대상 공간을 비우고 새 할당에 재사용할 수 있기 때문입니다. 하지만 살아남는 양이 많으면 복사와 참조 갱신 비용도 늘어납니다.

age는 단순한 벽시계 나이가 아닙니다. Young 수집에서 살아남는 과정과 관련된 상태입니다. 공간 압박과 생존량 등 조건에 따라 일찍 Old로 승격할 수도 있습니다. `MaxTenuringThreshold`만 외워 모든 객체가 정확히 그 횟수 뒤 승격한다고 말하지 마세요. 수집기 정책과 실제 로그를 함께 읽습니다.

## 4. 가장 중요한 질문: Old가 Young을 참조하면?

Old 캐시 객체가 방금 만든 Young DTO를 가리킨다고 생각해 봅시다. Young만 검사하면서 Young 내부 참조만 따라가면 DTO를 놓칠 수 있습니다. 그렇다고 매 Young GC마다 Old 전체를 스캔하면 세대를 나눈 효과가 줄어듭니다.

그래서 JVM은 참조 변경 때 **write barrier**로 관련 정보를 기록하고 **카드 테이블·remembered set** 등의 구조를 활용합니다. 카드란 객체마다 정확한 정보를 모두 유지하기보다 메모리의 작은 구간을 단위로 표시하는 아이디어입니다. 수집기는 외부에서 Young으로 들어오는 참조가 있을 법한 구간을 좁혀 검사합니다.

이는 “Old가 Young을 참조할 수 없다”가 아니라 “그 참조를 놓치지 않게 추적하는 비용을 지불한다”는 뜻입니다. G1은 Region 간 참조도 중요하여 13편에서 remembered set을 더 살펴봅니다. 자료구조의 구체적 구성은 수집기·버전 구현에 의존합니다.

## 5. 생존 기간을 달리하는 Java 실습

```java
// file: Lesson12.java
public class Lesson12 {
    static volatile Object sink;
    public static void main(String[] args) {
        byte[][] retained = new byte[128][];
        for (int i = 0; i < 20_000; i++) {
            byte[] data = new byte[16 * 1024];
            data[0] = (byte) i;
            sink = data;
            if (i % 100 == 0) retained[(i / 100) % retained.length] = data;
        }
        int aliveSlots = 0;
        for (byte[] value : retained) if (value != null) aliveSlots++;
        System.out.println("retained slots=" + aliveSlots);
        System.out.println("done");
    }
}
```

```sh
javac --release 21 -g Lesson12.java
java -Xms32m -Xmx32m -XX:+UseG1GC -Xlog:gc*,gc+age=trace:file=gc12.log:time,uptime,level,tags Lesson12
```

출력은 `retained slots=128`, `done`입니다. sink는 최근 배열이 외부에서 관찰될 수 있게 하는 장치이며, retained는 일부 배열을 더 오래 유지합니다. 할당 최적화가 단순히 전체 루프를 없애는 것을 피하려는 교육용 설계로, 서비스의 실제 객체 수명 분포를 재현한 벤치마크는 아닙니다.

약 312.5MiB의 배열 데이터가 누적 생성되지만 동시에 모두 유지되는 것은 아닙니다. 따라서 작은 Heap으로도 전체 누적 할당량보다 훨씬 적은 메모리에서 완료될 수 있습니다. 이 차이가 “누적 할당량”과 “동시 생존량”의 차이입니다. 실제 헤더·로그·GC 비용은 별도입니다.

## 6. 로그에서 무엇을 확인할까

Young 수집 전후의 Eden·Survivor·Old Region 변화, age 분포와 threshold 관련 로그를 봅니다. 정확한 횟수와 threshold는 환경에 따라 달라지므로 글의 예시 숫자를 고정 정답으로 삼지 않습니다. retained에 저장하는 빈도를 높여 생존량이 늘면 어떤 변화가 생기는지 비교하세요.

로컬 비교용으로 `-XX:+UseParallelGC`를 선택해 다른 로그 구조를 볼 수도 있습니다. G1 전용 Region 개념을 Parallel 출력에 강제로 대입하지 마세요. 선택한 수집기는 `-Xlog:gc` 시작 출력이나 VM 옵션으로 확인합니다. 작은 실습에서 나온 성능을 운영 서버 수 산정에 사용하지는 않습니다.

## 7. 장애 사례: DB 지연이 승격과 GC 비용을 늘린다

입고 API가 DB 응답을 기다리는 동안 요청 DTO·조회 결과·추적 컨텍스트가 유지된다고 가정합니다. DB가 느려져 동시에 진행 중인 요청이 늘면, 객체가 Young 수집을 여러 번 통과하며 Old까지 넘어갈 수 있습니다. 결과적으로 외부 시스템 지연이 Heap 압박과 GC 증가로 이어질 수 있습니다.

이를 단순히 “GC 튜닝 문제”로만 보면 원인을 놓칩니다. 요청 동시 실행 수, 대기 시간, 큐 길이, 승격량, GC 이후 Old 점유를 시간축에 놓고 비교합니다. 원래의 느린 DB·무제한 큐·과도한 동시성을 해결하면 객체 생존 기간도 줄 수 있습니다. 반대로 Young만 크게 늘리는 조치는 한 번의 정지 비용을 늘리거나 Old 여유를 줄일 수 있습니다.

## 더 깊이: 할당률·생존량·승격률을 따로 계산하기

세 숫자를 분리하면 튜닝 가설을 더 명확히 세울 수 있습니다. 할당률은 초당 새로 만든 바이트이고, 생존량은 수집 시점 이후 계속 남는 양이며, 승격률은 단위 시간에 Old로 옮겨가는 양입니다. 할당률이 높아도 대부분 금방 죽으면 Young 수집이 주요 비용일 수 있습니다. 생존율까지 높으면 복사와 Old 압박을 같이 고려해야 합니다.

단순화한 안정 상태에서 초당 요청 수가 1,000이고 평균 처리 시간이 0.1초라면 진행 중인 요청은 대략 100개입니다. 시간이 2초로 늘면 약 2,000개가 될 수 있습니다. 이는 조건을 단순화한 산술 예이며 실제 서비스의 보장값이 아닙니다. 요청당 유지 데이터가 같아도 대기 시간만으로 동시 생존 데이터가 크게 늘 수 있다는 설명입니다.

이때 Young 크기를 키우는 처방은 원인의 일부만 건드립니다. DB 지연으로 오래 잡힌 객체는 더 큰 Young에서도 계속 생존할 수 있습니다. 처리 시간·허용 동시성·대기열 상한을 함께 다루어야 합니다. GC는 애플리케이션이 계속 참조하는 요청을 대신 취소하지 못합니다.

<details class="question"><summary>심화 Q. 누적 300MiB를 생성한 프로그램이 32MiB Heap에서 끝날 수 있는 이유는 무엇인가요?</summary><div class="answer"><p>누적 생성량과 동시에 필요한 생존량이 다르기 때문입니다. 앞의 객체가 도달 불가능해져 회수된 공간을 뒤의 객체가 재사용할 수 있습니다.</p><p>반대로 300MiB를 전부 리스트에 보관하면 같은 Heap에서 성공할 수 없습니다. 메모리 산정에서는 총 처리 건수뿐 아니라 동시에 유지되는 건수와 객체 수명을 보아야 합니다.</p></div></details>

## 8. 상세 면접 Q&A

<details class="question"><summary>Q1. 객체는 일정 시간이 지나면 Old로 가나요?</summary><div class="answer"><p>벽시계 시간만으로 판단하지 않습니다. Young 수집 생존과 age, 생존 공간, 수집기 정책 등의 조건이 관련됩니다. 오래 머물렀어도 수집을 거의 경험하지 않은 경우와 수집을 여러 번 통과한 경우를 구분해야 합니다.</p></div></details>
<details class="question"><summary>Q2. Young GC는 Young만 보면 되나요?</summary><div class="answer"><p>수집 대상이 Young이어도 외부에서 들어오는 참조는 확인해야 합니다. Old→Young 참조를 추적하는 barrier·카드·remembered set 등이 필요한 이유입니다. 대상 영역과 탐색의 출발 정보를 혼동하면 살아 있는 객체를 놓치게 됩니다.</p></div></details>
<details class="question"><summary>Q3. Old는 GC가 안 되는 영역인가요?</summary><div class="answer"><p>아닙니다. 수집 빈도와 방법이 다를 수 있을 뿐입니다. G1은 Mixed 수집에서 일부 Old Region을 포함하고 필요하면 Full GC도 수행할 수 있습니다. Old를 영구 보관 영역이나 Metaspace와 같은 것으로 설명하면 안 됩니다.</p></div></details>
<details class="question"><summary>Q4. Survivor를 무조건 크게 하면 좋은가요?</summary><div class="answer"><p>생존 객체를 더 오래 Young에 둘 수 있지만 다른 공간과 정지 비용에 영향을 줍니다. 생존량·할당률·정지 목표를 모르고 비율만 고정하면 적응형 정책을 방해할 수 있습니다. 기본 설정과 로그를 출발점으로 병목을 확인합니다.</p></div></details>
<details class="question"><summary>Q5. 모든 GC가 같은 세대 구조를 쓰나요?</summary><div class="answer"><p>아닙니다. 수집기와 JDK 버전에 따라 다릅니다. JDK 21의 ZGC는 세대형 모드를 선택하는 방식이 있고 G1·Parallel과 자료구조가 다릅니다. 특정 수집기의 Eden·Survivor 그림을 JVM의 필수 구조라고 제시하지 않습니다.</p></div></details>
<details class="question"><summary>Q6. 외부 API가 느린데 GC가 늘어나는 이유는 무엇인가요?</summary><div class="answer"><p>대기 중인 요청이 많아지면 객체가 더 오래 유지되고 동시 생존량이 늘 수 있습니다. 할당률이 같아도 생존 기간이 길어지면 메모리 압박이 커집니다. 객체 수명과 요청 대기를 연결해 조사해야 합니다.</p></div></details>

## 9. 공식 근거와 복습

- [JDK 21 GC Tuning Guide](https://docs.oracle.com/en/java/javase/21/gctuning/index.html): 세대별 GC의 추가 공식 자료.
- [G1 기본 개념과 Heap 구조](https://docs.oracle.com/en/java/javase/21/gctuning/garbage-first-g1-garbage-collector1.html): Region 기반 Young·Old와 참조 추적.
- [G1 튜닝](https://docs.oracle.com/en/java/javase/21/gctuning/garbage-first-garbage-collector-tuning.html): 적응형 정책을 전제로 읽기.
- [JEP 439: Generational ZGC](https://openjdk.org/jeps/439): JDK 21의 수집기별 차이.

첨부 12편에는 세대별 GC 본문이 없어 공식 GC 가이드로 보충했습니다. retained의 크기와 보관 빈도를 각각 바꾸고 “할당량은 같은데 생존량만 달라지는 실험”을 해 보세요.
