{"n":15,"title":"스레드·모니터·Safepoint: 대기와 정지를 구분하기","desc":"synchronized·monitorenter/exit·happens-before·락 경합·안전 지점과 Java 21 가상 스레드를 연결한다"}

## 1. 한 대의 창고 단말기를 여러 직원이 쓴다면

직원 A와 B가 수량 10을 동시에 읽고 각자 1을 더한 뒤 11을 기록하면 한 번의 증가가 사라집니다. 실행 순서를 조율해야 할 때 같은 자원에 들어가는 열쇠가 필요합니다. Java의 `synchronized`는 객체와 연결된 **모니터(Monitor)**를 이용하는 동기화 구문입니다.

모니터는 단순히 “객체에 붙은 boolean 잠금값”으로만 설명하기에는 부족합니다. 소유자, 재진입, 경합과 대기, wait/notify 규칙이 관련됩니다. 락을 갖지 못한 요청이 기다리는 것과 JVM 전체 작업을 위해 애플리케이션 실행을 멈추는 STW는 서로 다른 현상입니다.

## 2. 원자성과 가시성을 함께 보기

synchronized는 같은 모니터를 사용하는 임계 구역에 한 번에 한 스레드가 들어가도록 합니다. 같은 스레드가 이미 가진 모니터를 다시 획득할 수 있는 재진입도 지원합니다. 임계 구역 전체의 복합 동작을 묶는 데 사용할 수 있습니다.

또한 같은 모니터의 unlock은 이후 lock과 happens-before 관계를 만듭니다. 단순히 동시에 못 들어가게 하는 것뿐 아니라 쓰기 결과가 올바르게 보이는 동기화 규칙과 연결됩니다. 서로 다른 모니터로 각각 보호하면 같은 변수여도 이 상호 배제가 성립하지 않습니다. `volatile int count`도 `count++` 전체를 원자적으로 만들지는 않습니다. [근거: JLS §17.4.5](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html#jls-17.4.5)

## 3. 정확히 2만 번 증가하는 코드

```java
// file: Lesson15.java
public class Lesson15 {
    static final class Counter {
        private int value;
        synchronized void increment() { value++; }
        synchronized int read() { return value; }
        void blockIncrement() {
            synchronized (this) { value++; }
        }
    }
    public static void main(String[] args) throws InterruptedException {
        Counter counter = new Counter();
        Runnable job = () -> {
            for (int i = 0; i < 10_000; i++) counter.increment();
        };
        Thread first = new Thread(job, "inspection-a");
        Thread second = new Thread(job, "inspection-b");
        first.start();
        second.start();
        first.join();
        second.join();
        System.out.println(counter.read());
    }
}
```

```sh
javac --release 21 -g Lesson15.java
java Lesson15
javap -c -v -p 'Lesson15$Counter'
java -Xlog:safepoint=info Lesson15
```

출력은 20000입니다. 같은 Counter의 모니터로 증가를 보호합니다. 두 join은 스레드 완료를 기다립니다. 동기화를 제거한 변형은 종종 더 작은 값이 나올 수 있지만, 짧은 실험에서 우연히 20000이 나왔다고 스레드 안전성을 증명한 것은 아닙니다.

## 4. synchronized 메서드와 블록의 바이트코드

동기화된 메서드는 method_info의 `ACC_SYNCHRONIZED` 플래그로 표시될 수 있습니다. 명령 목록에 monitorenter가 없다고 락이 없다는 뜻이 아닙니다. 인스턴스 동기화 메서드는 수신 객체, static 동기화 메서드는 해당 Class 객체와 연결된 모니터를 사용합니다.

동기화 블록은 보통 `monitorenter`·`monitorexit`와 예외 처리 경로로 표현됩니다. 정상 종료와 예외 종료 모두 모니터를 놓아야 하기 때문입니다. blockIncrement를 javap로 보고 예외 표까지 확인하세요. 서로 다른 객체 두 개에 synchronized를 걸면 하나의 전역 락이 되는 것이 아닙니다. [근거: JVMS §3.14](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-3.html#jvms-3.14)

## 5. BLOCKED·WAITING·RUNNABLE과 wait/sleep

BLOCKED는 Java 모니터 진입 대기와 연결됩니다. WAITING·TIMED_WAITING에는 join, park, wait, sleep 등의 상황이 포함될 수 있습니다. RUNNABLE도 실제 CPU를 계속 쓰고 있다는 뜻만은 아닙니다. 네이티브 I/O 상태가 그렇게 보이는 경우도 있어 OS CPU 표본과 스택을 함께 봅니다.

`Object.wait()`는 해당 객체 모니터를 가진 상태에서 호출하며 대기 중 그 모니터를 놓습니다. `Thread.sleep()`은 현재 가지고 있는 모니터를 자동으로 놓지 않습니다. notify는 조건 충족을 영구 보장하거나 곧바로 CPU 실행권을 넘기는 마법이 아닙니다. wait는 조건 확인을 반복하는 패턴과 함께 사용해야 합니다.

락을 오래 잡고 DB·네트워크를 기다리면 같은 락을 쓰는 다른 요청도 막힐 수 있습니다. 스레드 수를 늘리면 대기자만 늘어 Heap과 Native 비용까지 악화될 수 있습니다. 임계 구역을 줄이되 보호해야 할 불변식이 깨지지 않도록 설계해야 합니다.

## 6. Safepoint는 무엇을 안전하게 만드는가

HotSpot은 GC의 특정 단계나 VM 작업을 수행할 때 스레드 상태를 안전하게 관찰·처리할 수 있어야 합니다. **Safepoint**는 이런 작업을 위한 안전한 실행 상태와 협조 메커니즘에 관련됩니다. Java 소스의 세미콜론마다 무조건 존재하는 지점이나 OS가 스레드를 임의로 선점하는 모든 순간과 같지 않습니다.

정지 로그를 읽을 때는 안전 상태에 도달하기까지의 시간과 실제 정지 상태에서 작업한 시간을 구분합니다. 애플리케이션이 느려진 전체 시간을 GC 작업 시간으로만 해석하면 safepoint 진입 지연이나 CPU 부족을 놓칠 수 있습니다. 또한 모든 safepoint가 GC 때문은 아닙니다. 반대로 특정 스레드만 협조하는 handshake와 전역 safepoint도 구분할 필요가 있습니다.

컴파일된 코드의 oop map 등 정보는 안전한 상태에서 어느 값이 객체 참조인지 판단하는 데 도움을 줍니다. 이는 07편의 class 파일 StackMapTable과 같은 자료구조라고 단정하면 안 됩니다. 하나는 JIT 실행과 런타임 관측의 구현 정보이고 다른 하나는 바이트코드 검증용 타입 정보입니다.

## 7. Java 21 가상 스레드는 무엇이 다른가

플랫폼 스레드는 OS 스레드와 연결되어 실행됩니다. 가상 스레드는 JVM이 스케줄링하며 캐리어 플랫폼 스레드 위에 올라가 실행합니다. 많은 블로킹 I/O 동시 작업을 효율적으로 다루려는 기능이지 CPU 코어 수를 늘리거나 DB 커넥션 한도를 없애는 기능이 아닙니다.

다음 예제는 **JDK 21 이상**에서 컴파일합니다. 완료 순서는 보장하지 않고 합계만 확인합니다.

```java
// file: VirtualThreads.java
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.ArrayList;
import java.util.List;

public class VirtualThreads {
    public static void main(String[] args) throws Exception {
        List<Future<Integer>> tasks = new ArrayList<>();
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 100; i++) {
                tasks.add(executor.submit(() -> {
                    Thread.sleep(10);
                    return 1;
                }));
            }
            int total = 0;
            for (Future<Integer> task : tasks) total += task.get();
            System.out.println("completed=" + total);
        }
    }
}
```

JDK 21에서는 synchronized 구역 안에서 블로킹할 때 캐리어에 pinning되는 조건 등이 중요합니다. 이 설명을 모든 최신 JDK의 영구 특성으로 외우지 마세요. JDK 24의 JEP 491은 synchronized 관련 pinning을 개선했습니다. 이 연재는 21을 기준으로 하므로 긴 I/O를 락 안에서 수행하는 경로와 JFR의 pinning 관측을 확인합니다. 가상 스레드를 사용해도 공유 상태의 동기화와 외부 자원의 동시성 제한은 필요합니다.

## 8. 장애 사례: CPU는 낮은데 요청이 밀림

검수 서비스가 synchronized 블록 안에서 외부 API를 2초 기다린다고 가정합니다. 같은 모니터가 필요한 요청들은 실행할 CPU가 남아도 대기할 수 있습니다. 이를 GC 정지로 오인해 Heap을 늘리면 락 병목은 그대로입니다.

시간 간격을 둔 thread dump에서 같은 모니터 소유자와 대기자들이 반복되는지 확인하고, JFR의 락 대기와 외부 호출 시간을 연결합니다. 전역 safepoint 로그에 같은 기간 정지가 있었는지도 비교합니다. CPU 부족·락 경합·외부 대기·GC는 관측 자료를 나누어야 구분할 수 있습니다.

## 더 깊이: 락 경합·교착·Safepoint 지연의 차이

락 경합은 한 자원을 여러 스레드가 필요로 하는 상황입니다. 소유자가 빠르게 완료하면 정상적으로 진행할 수 있습니다. 교착은 A가 가진 락을 B가 기다리고 B가 가진 락을 A가 기다리는 식으로 서로 필요한 자원을 놓지 못해 진행이 막히는 상황입니다. 단순히 BLOCKED가 많이 보인다고 모두 교착은 아닙니다.

락 순서를 일관되게 정하고 임계 구역의 외부 I/O를 줄이며, 타임아웃 가능한 락·자원 API의 필요성을 검토할 수 있습니다. 다만 timeout을 걸었다고 중간에 변경한 업무 상태가 자동 롤백되는 것은 아닙니다. 동시성 제어와 트랜잭션 보상·정합성도 구분해야 합니다.

Safepoint 도달 지연은 다른 질문입니다. JVM이 필요한 안전 상태를 기다리느라 시간이 걸리는지, 실제 VM 작업이 오래 걸리는지를 봅니다. CPU 제한과 스레드 스케줄링도 영향을 줄 수 있으므로 정지 로그의 총시간을 특정 GC 단계 하나로 치환하지 않습니다.

<details class="question"><summary>심화 Q. JVM 안에서 synchronized를 걸면 여러 서버의 재고 갱신도 보호되나요?</summary><div class="answer"><p>같은 JVM 안에서 같은 모니터를 사용하는 스레드끼리의 규칙입니다. 서버가 세 대라면 각 프로세스의 객체와 모니터는 별개이므로 전역 업무 동기화가 되지 않습니다.</p><p>DB 조건부 갱신·트랜잭션·유일 제약 등 공유 자원의 정합성 설계가 필요합니다. JVM 모니터의 범위를 네트워크 전체로 확대해서 설명하면 안 됩니다.</p></div></details>

## 9. 상세 면접 Q&A

<details class="question"><summary>Q1. synchronized는 원자성만 제공하나요?</summary><div class="answer"><p>같은 모니터의 상호 배제와 unlock→이후 lock의 happens-before를 함께 봐야 합니다. 올바른 공유 규칙 없이 다른 락으로 읽으면 같은 보호를 얻지 못합니다. volatile과 복합 연산 원자성의 차이도 구분합니다.</p></div></details>
<details class="question"><summary>Q2. javap에 monitorenter가 없으면 동기화되지 않은 메서드인가요?</summary><div class="answer"><p>동기화 메서드는 ACC_SYNCHRONIZED 플래그로 표시될 수 있습니다. 블록의 명령과 메서드 플래그를 함께 확인해야 합니다. static과 인스턴스 메서드가 사용하는 모니터도 다릅니다.</p></div></details>
<details class="question"><summary>Q3. sleep은 락을 놓나요?</summary><div class="answer"><p>sleep은 보유한 모니터를 자동으로 놓지 않습니다. wait는 해당 모니터의 소유 규칙을 만족해야 하고 대기 중 그 모니터를 놓습니다. 긴 sleep이나 I/O를 임계 구역 안에 두면 다른 스레드가 계속 막힐 수 있습니다.</p></div></details>
<details class="question"><summary>Q4. Safepoint는 GC와 같은 말인가요?</summary><div class="answer"><p>GC는 안전 상태를 필요로 하는 중요한 작업 중 하나이지만 전부는 아닙니다. 전역 협조·관측 메커니즘과 수행할 작업을 구분해야 합니다. 도달 시간과 작업 시간, 다른 VM 작업도 로그에서 따로 확인합니다.</p></div></details>
<details class="question"><summary>Q5. 가상 스레드를 늘리면 CPU 계산도 무한히 빨라지나요?</summary><div class="answer"><p>아닙니다. 실제 계산 병렬성은 CPU와 캐리어 실행 자원에 제한됩니다. 가상 스레드는 주로 많은 블로킹 작업을 저렴하게 표현하는 데 유리합니다. DB 풀·API 한도·메모리 등 외부 제약은 따로 제한해야 합니다.</p></div></details>
<details class="question"><summary>Q6. Java 21의 pinning 설명을 JDK 24에도 그대로 적용하나요?</summary><div class="answer"><p>그대로 적용하면 안 됩니다. JEP 491은 synchronized 관련 pinning을 개선했습니다. 사용하는 JDK의 기능·버전과 실제 스택·JFR 이벤트를 기준으로 진단해야 합니다. 모든 지연을 pinning 한 단어로 설명하지 않습니다.</p></div></details>

## 10. 공식 근거와 복습

- [JLS §17 동기화·메모리 모델](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html).
- [JVMS §2.11.10 동기화](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-2.html#jvms-2.11.10).
- [JEP 312: Thread-Local Handshakes](https://openjdk.org/jeps/312).
- [JEP 444: Java 21 가상 스레드](https://openjdk.org/jeps/444).
- [JEP 491: JDK 24의 변경](https://openjdk.org/jeps/491).

counter를 두 개 만들어 각 스레드가 다른 인스턴스를 증가시키게 바꿔 보세요. 그다음 static synchronized를 쓴 경우와 비교해 “어떤 객체가 락인가?”를 설명하세요.
