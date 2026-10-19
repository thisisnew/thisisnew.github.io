{"n":11,"title":"GC의 기본 원리: 도달 가능성과 메모리 회수","desc":"GC Root·참조 그래프·Mark·Sweep·Copy·Compact·STW를 누수 예제로 이해한다"}

## 1. GC는 내가 쓸 객체를 어떻게 아는가

창고에서 앞으로 주문될 상품을 완벽히 예측할 수는 없습니다. 대신 “현재 유효한 주문과 연결되어 있는가?”를 기준으로 분류할 수 있습니다. GC도 개발자가 앞으로 읽을 의도를 직접 예측하지 않습니다. 실행 상태에서 출발해 참조를 따라 도달할 수 있는지를 기준으로 객체를 조사합니다.

**도달 가능성(Reachability)**은 “살아 있는 출발점에서 참조를 따라 갈 수 있는가”라는 개념입니다. 따라서 업무적으로 쓸모없어도 static Map이 계속 붙잡는 객체는 남을 수 있습니다. Java에도 메모리 누수가 발생하는 가장 중요한 이유입니다. JVMS는 자동 메모리 관리가 존재함을 규정하지만 특정 GC 알고리즘을 강제하지 않습니다.

## 2. GC Root와 참조 그래프

GC의 출발점으로 자주 설명하는 것은 실행 중인 스레드에서 살아 있는 참조, JNI 참조, JVM 내부의 살아 있는 참조 등입니다. static 필드의 참조도 살아 있는 클래스·로더와 연결된 도달 경로에서 중요합니다. 정확한 루트 종류와 표시 방식은 JVM·진단 도구에 따라 다르므로 모든 static 필드 자체를 무조건 독립적인 영구 Root라고 외우지는 마세요.

객체 A가 B를, B가 C를 참조하면 A로부터 C까지 도달할 수 있습니다. A와 B가 서로 참조하더라도 외부의 살아 있는 경로가 전혀 없다면 둘 다 회수 후보가 될 수 있습니다. 단순 참조 카운팅과 달리 추적 기반 GC가 순환 참조를 처리할 수 있는 이유입니다.

**회수 후보**라는 표현도 중요합니다. 도달 불가능해지는 순간 그 메모리가 바로 반환된다고 보장하지 않습니다. 수집 시점과 참조 처리·정리 동작에 따라 실제 회수 시점은 달라집니다. 파일·소켓·DB 연결은 GC가 나중에 처리하길 기다리지 말고 명시적인 수명 관리와 try-with-resources 등으로 다룹니다.

## 3. 누수와 순환 참조를 보여 주는 예제

```java
// file: Lesson11.java
import java.lang.ref.WeakReference;
import java.util.HashMap;
import java.util.Map;

public class Lesson11 {
    static final Map<String, byte[]> cache = new HashMap<>();
    static class Node { Node next; }
    static WeakReference<Node> makeCycle() {
        Node a = new Node();
        Node b = new Node();
        a.next = b;
        b.next = a;
        return new WeakReference<>(a);
    }
    public static void main(String[] args) {
        WeakReference<Node> reference = makeCycle();
        cache.put("old-request", new byte[1024 * 1024]);
        System.out.println("cache entries=" + cache.size());
        System.gc();
        System.out.println("cycle observed alive=" + (reference.get() != null));
        cache.clear();
        System.out.println("cache entries=" + cache.size());
    }
}
```

`makeCycle`의 강한 지역 참조가 더 이상 유지되지 않고 반환된 것은 약한 참조뿐이므로 순환 객체는 강하게 도달 가능한 상태가 아닐 수 있습니다. 그러나 `System.gc()`는 즉시 회수 보장이 아닙니다. `cycle observed alive`의 true·false 어느 결과도 특정 JVM 실행에서 가능하므로 그 값을 고정 기대값으로 테스트하면 안 됩니다.

반면 cache 크기는 1에서 0으로 바뀝니다. clear는 Map이 배열을 붙잡는 참조를 제거합니다. 배열의 물리 메모리가 그 줄에서 즉시 회수되었다는 뜻은 아닙니다. 참조 해제와 회수 완료를 구분하는 실험입니다.

## 4. Mark·Sweep·Copy·Compact

| 개념 | 하는 일 | 장점과 비용 |
|---|---|---|
| Mark | 출발점에서 살아 있는 객체를 표시 | 참조 그래프 탐색 비용 |
| Sweep | 사용하지 않는 공간을 회수 | 이동 없이 회수할 수 있지만 단편화 고려 |
| Copy/Evacuation | 살아 있는 객체를 다른 공간으로 옮김 | 연속 공간 확보, 대상 공간과 참조 갱신 필요 |
| Compact | 살아 있는 객체를 모아 빈 공간을 정리 | 단편화 완화, 이동과 갱신 비용 |

이것은 기본 아이디어의 구분입니다. 현대 수집기는 여러 아이디어를 결합하고 일부 작업을 병렬·동시 수행합니다. “Java GC는 전부 Mark-Sweep 한 종류”라고 외우지 마세요. 복사 수집은 살아남은 객체가 적을 때 효율적일 수 있지만 생존량이 많으면 이동 비용이 커집니다.

## 5. STW·Parallel·Concurrent는 서로 다른 축

**STW(Stop-The-World)**는 특정 JVM 작업을 위해 애플리케이션 스레드 실행을 일시 중단하는 상황을 가리킵니다. **Parallel**은 여러 GC 작업 스레드가 함께 처리하는 것입니다. **Concurrent**는 애플리케이션이 실행되는 동안 GC의 일부 작업도 진행하는 것입니다.

여러 GC 스레드가 병렬로 일해도 그동안 애플리케이션이 멈춰 있을 수 있습니다. 동시 GC도 짧은 정지 단계가 있을 수 있습니다. 따라서 “Concurrent GC를 쓰면 STW가 0”은 틀립니다. 정지 목표와 처리량, CPU·메모리 여유 사이에는 비용 교환이 있습니다.

객체 그래프가 계속 바뀌는데 동시에 추적하려면 추가 장치가 필요합니다. write barrier 같은 기법으로 참조 변경을 기록해 수집기가 중요한 객체를 놓치지 않게 합니다. 이 barrier는 동시성에서 말하는 모든 memory barrier와 동일한 목적·형태인 것은 아닙니다. 12~13편에서 세대 간 참조와 SATB로 이어집니다.

## 6. 실습 로그와 읽는 기준

```sh
javac --release 21 -g Lesson11.java
java -Xms32m -Xmx32m -Xlog:gc*,safepoint:file=gc11.log:time,uptime,level,tags Lesson11
```

명령은 작은 로컬 Heap으로 실험하기 위한 것이며 운영 권장값이 아닙니다. 로그에서 수집기 종류, GC 원인, 전후 Heap, 정지 시간을 구분하세요. System.gc 요청이 보일 수 있지만 명시적 GC를 억제하는 옵션과 수집기 정책에 따라 동작이 달라집니다.

Heap이 줄었다는 사실만으로 누수가 없다고 결론 내릴 수 없습니다. 비슷한 부하의 여러 시점에서 GC 이후 남는 live set이 계속 커지는지 보아야 합니다. 반대로 사용량이 증가하다 한 번에 떨어지는 톱니 모양은 정상 할당·수집일 수 있습니다. 부하와 유지 정책을 함께 봅니다.

## 7. 장애 사례: 완료한 요청을 캐시가 모두 기억한다

입고 검수 결과를 요청 ID로 static Map에 저장하고 삭제하지 않는다고 가정합니다. 요청 프레임은 끝났어도 Map에서 응답 DTO·이미지 메타데이터 등으로 이어지는 참조가 남습니다. GC를 더 자주 실행해도 도달 가능한 객체는 필요할 수 있다고 취급되어 회수되지 않습니다.

Heap dump에서 큰 클래스 개수만 보는 것보다 “누가 붙잡는가?”를 조사합니다. dominator와 retained size, GC Root까지의 경로가 유용합니다. 해결은 크기·시간·업무 상태에 따른 보관 수명과 제거 정책을 정하는 것입니다. `System.gc()` 호출을 루프에 추가하는 것은 참조 유지 문제를 해결하지 못합니다.

## 더 깊이: 강한·약한 참조와 외부 자원 수명

일반적인 객체 필드와 지역변수가 갖는 참조는 강한 참조의 기본 사례입니다. WeakReference는 이와 다른 회수 규칙을 관찰하도록 제공합니다. SoftReference는 메모리 상황에 따라 유지 정책이 달라질 수 있으며, PhantomReference와 ReferenceQueue는 객체 도달 가능성 변화 후의 후처리와 관련됩니다. 어떤 참조든 강한 경로가 별도로 남아 있으면 약한 참조 하나를 만들었다고 회수 가능해지는 것은 아닙니다.

특히 SoftReference를 '메모리가 부족해지면 알아서 정리되는 완벽한 캐시'라고 생각하면 크기·히트율·지연 예측이 어려워집니다. 업무 캐시는 최대 크기·만료·무효화 정책을 명시하는 것이 보통 더 다루기 쉽습니다. GC 정책과 비즈니스 보관 정책은 서로 다른 책임입니다.

finalize나 나중의 자동 정리를 파일·소켓·락 해제의 주된 보장으로 사용하지 않습니다. 도달 불가능과 정리 실행 사이에 지연이 있고 프로세스 종료 시 실행을 보장하지 못할 수 있기 때문입니다. try-with-resources는 코드 블록 수명에 맞춘 명시적 close를 표현합니다. GC는 Java Heap 회수의 문제이고 외부 자원 사용 기한은 별도로 설계합니다.

<details class="question"><summary>심화 Q. WeakReference를 Map 값으로 쓰면 누수가 모두 해결되나요?</summary><div class="answer"><p>어떤 참조 경로를 약하게 만들었는지가 중요합니다. 키나 다른 컬렉션·리스너가 강하게 붙잡거나 값에서 다시 다른 경로로 연결될 수 있습니다. 약한 참조는 업무 데이터의 필요한 수명까지 보장하지도 않습니다.</p><p>먼저 참조 그래프와 보관 계약을 정의한 뒤 자료구조를 선택합니다. 회수 가능성을 높이는 것과 정확한 캐시 무효화·업무 정합성은 다른 요구사항입니다.</p></div></details>

## 8. 상세 면접 Q&A

<details class="question"><summary>Q1. 순환 참조가 있으면 Java GC가 회수하지 못하나요?</summary><div class="answer"><p>추적 기반 GC는 루트에서의 도달 가능성을 봅니다. 서로만 참조하고 외부에서 도달할 수 없다면 순환 구조도 회수 후보가 될 수 있습니다. 단순 참조 카운팅의 한계를 모든 Java GC에 대입하면 안 됩니다.</p></div></details>
<details class="question"><summary>Q2. System.gc() 뒤에 WeakReference가 남으면 JVM 버그인가요?</summary><div class="answer"><p>아닙니다. System.gc는 즉시 회수 완료의 계약이 아닙니다. 살아 있는 강한 참조, 최적화된 변수 생존 범위, VM 옵션과 수집 시점도 영향을 줍니다. 테스트는 강제 GC의 타이밍을 논리적 정답으로 삼지 않아야 합니다.</p></div></details>
<details class="question"><summary>Q3. 객체를 null로 바꾸면 바로 메모리가 반환되나요?</summary><div class="answer"><p>해당 참조 하나를 제거하는 것입니다. 다른 강한 경로가 있으면 객체는 남습니다. 모든 경로가 없어져도 실제 수집은 나중일 수 있습니다. 파일 같은 외부 자원은 null 대입과 GC에 맡기지 않고 명시적으로 닫아야 합니다.</p></div></details>
<details class="question"><summary>Q4. STW와 Parallel GC는 반대말인가요?</summary><div class="answer"><p>아닙니다. 정지 여부와 작업자 수라는 다른 축입니다. 애플리케이션을 정지한 채 여러 GC 스레드가 병렬 처리할 수 있습니다. Concurrent도 모든 단계에서 애플리케이션이 계속 실행된다는 뜻은 아닙니다.</p></div></details>
<details class="question"><summary>Q5. GC가 있는데 왜 메모리 누수가 생기나요?</summary><div class="answer"><p>업무적으로 필요 없는 객체라도 살아 있는 참조 경로가 있으면 도달 가능합니다. 전역 Map, 리스너, 큐, ThreadLocal 등이 대표적인 유지 경로입니다. GC는 개발자의 보관 의도를 모르므로 객체 수명 설계는 여전히 필요합니다.</p></div></details>
<details class="question"><summary>Q6. GC 횟수가 많으면 무조건 누수인가요?</summary><div class="answer"><p>아닙니다. 짧게 사는 객체를 많이 생성해도 수집 횟수가 많습니다. 할당률, GC 이후 점유량, 정지 시간, GC CPU 비중을 구분해야 합니다. 누수 여부와 GC 성능 문제는 겹칠 수 있지만 동일하지 않습니다.</p></div></details>

## 9. 공식 근거와 복습

- [JVMS §2.5.3 Heap과 자동 관리](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-2.html#jvms-2.5.3).
- [JDK 21 GC Tuning Guide](https://docs.oracle.com/en/java/javase/21/gctuning/index.html).
- [WeakReference API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ref/WeakReference.html).
- [System.gc 계약](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/System.html#gc()).

첨부 11편은 GC의 상세 알고리즘을 제공하지 않아 공식 GC 가이드로 보충했습니다. 다음 편에서는 모든 객체를 매번 검사하지 않도록 수명을 활용하는 세대별 수집을 배웁니다.
