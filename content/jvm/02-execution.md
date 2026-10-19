{"n":2,"title":"Java 코드가 실행되는 과정: 소스에서 CPU까지","desc":"javac·class·로딩·링킹·초기화·인터프리터·JIT를 실행 예제로 연결한다"}

## 1. 실행을 두 번의 번역으로 나누기

레시피를 공통 조리 지시서로 바꾸는 작업과, 실제 주방에서 그 지시를 수행하는 작업을 구분해 봅시다. `javac`는 Java 소스를 JVM의 class 형식으로 컴파일합니다. HotSpot은 실행 중 바이트코드를 해석하거나 자주 실행되는 부분을 해당 CPU의 기계 코드로 컴파일합니다. 앞의 컴파일과 뒤의 JIT 컴파일은 입력과 출력이 다릅니다.

Java 코드가 “바이트코드로 바뀌고 그 뒤 기계어가 된다”는 문장은 큰 흐름으로 유용합니다. 하지만 모든 메서드가 반드시 JIT를 거치는 직선 파이프라인은 아닙니다. 적게 실행되는 메서드는 해석 실행으로 끝날 수 있고, 최적화된 메서드도 가정이 깨지면 해석 실행 등으로 돌아갈 수 있습니다.

## 2. 각 단계의 입력과 출력

| 단계 | 입력 | 결과 또는 역할 |
|---|---|---|
| 소스 컴파일 | .java와 필요한 타입 정보 | .class, 메서드의 바이트코드와 메타데이터 |
| JVM 시작 | 클래스 이름, classpath, 옵션 | 실행 프로세스와 초기 실행 환경 |
| 로딩 | 클래스의 이진 표현 | JVM이 관리하는 클래스 생성 |
| 링킹 | 로드된 클래스 | 검증, 준비, 심벌 참조 해석 |
| 초기화 | static 초기화 코드 | 클래스 초기화 규칙에 따른 실행 |
| 해석 실행 | JVM 명령과 실행 상태 | 명령의 의미를 수행 |
| JIT | 실행 프로파일과 메서드·루프 | CPU별 최적화 기계 코드 |

해석 실행도 결국 CPU가 수행합니다. CPU가 바이트코드 형식을 직접 이해한다는 뜻이 아니라, CPU 위에서 동작하는 인터프리터 코드가 바이트코드의 의미를 구현합니다. JIT는 자주 쓰이는 경로의 반복 해석 비용을 줄일 수 있습니다. [공식 근거: HotSpot 개요](https://docs.oracle.com/en/java/javase/21/vm/java-virtual-machine-technology-overview.html)

## 3. main을 부르기 전에도 일이 일어난다

`java Lesson02`는 파일을 더블클릭해 소스 전체를 한 줄씩 읽는 것과 다릅니다. 런처와 JVM은 초기 클래스가 무엇인지 정하고 실행에 필요한 클래스를 로드·링크·초기화합니다. 일반적인 진입점 `public static void main(String[] args)`를 호출하기 전에 초기 클래스의 초기화가 수행됩니다.

프로그램의 모든 클래스가 이때 한꺼번에 초기화되는 것은 아닙니다. 나중에 특정 기능이 처음 사용될 때 로딩이나 초기화가 발생할 수 있습니다. 그렇기 때문에 “애플리케이션 기동 성공”과 “모든 기능의 클래스 의존성 검증 완료”는 같은 뜻이 아닙니다. 사용하지 않던 API를 처음 호출할 때 의존성 오류가 드러나는 이유입니다. [공식 근거: JVMS §5.2, §5.5](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html#jvms-5.2)

## 4. 직접 실행하는 작은 프로그램

```java
// file: Lesson02.java
public class Lesson02 {
    static {
        System.out.println("init");
    }
    static int add(int a, int b) {
        return a + b;
    }
    public static void main(String[] args) {
        System.out.println("main");
        System.out.println(add(20, 22));
    }
}
```

```sh
javac --release 21 -g Lesson02.java
java Lesson02
javap -c -p Lesson02
java -Xlog:class+load=info,class+init=info Lesson02
```

일반 실행의 논리적 출력은 `init`, `main`, `42` 순서입니다. 로그 옵션을 켜면 JVM이 사용하는 표준 클래스 로그가 함께 많이 나옵니다. class 로드 로그가 나온 사실과 그 클래스의 static 블록이 실행된 사실을 혼동하지 마세요. 두 종류 로그를 나누어 관찰합니다.

`javap`의 `add` 메서드에는 보통 `iload_0`, `iload_1`, `iadd`, `ireturn`이 보입니다. 지역변수 슬롯의 두 값을 피연산자 스택으로 올려 계산하고 반환하는 과정입니다. `javac`가 결과 전체를 OS 실행 파일로 만든 것이 아니라 메서드별 JVM 명령으로 만든 사실을 확인할 수 있습니다.

## 5. 링킹과 초기화를 미리 구분하기

**검증(Verification)**은 class 파일과 바이트코드의 규칙을 확인합니다. 예를 들어 정수가 필요한 연산에 잘못된 타입의 값이 올라가도록 만들어진 바이트코드는 정상적인 실행 코드로 받아들일 수 없습니다. 단, 검증이 SQL의 업무 정합성까지 확인하지는 않습니다.

**준비(Preparation)**는 static 필드 등을 위한 저장 공간과 기본 상태를 준비합니다. Java 코드에 쓴 임의의 계산식 전체를 이 단계에서 실행하지 않습니다. **해석(Resolution)**은 클래스·필드·메서드를 가리키는 심벌 참조를 구체적인 런타임 요소로 연결합니다. 해석은 지연될 수 있어 모든 해석이 초기화 전에 완결되는 것은 아닙니다.

**초기화(Initialization)**는 `<clinit>` 등 규칙에 따라 static 초기화 코드를 실행합니다. 생성자 `<init>`와 다른 작업입니다. 이 네 개념은 09편에서 상수 변수와 실패 사례로 더 깊이 살펴봅니다.

## 6. 인터프리터·JIT·CPU의 관계

HotSpot은 실행하며 호출 빈도와 분기, 실제로 들어오는 타입 같은 정보를 수집할 수 있습니다. 이 정보는 “이 호출에는 보통 이 구현체가 온다”와 같은 최적화의 재료입니다. JIT는 호출을 인라이닝하거나 중복 검사를 제거하는 등의 작업을 할 수 있습니다. 반면 컴파일 자체도 CPU와 메모리를 사용합니다.

따라서 처음 호출이 늦다는 사실만으로 GC를 원인이라고 할 수 없습니다. 클래스 준비, static 초기화, JIT 워밍업 외에도 커넥션 생성, DNS, 캐시 적재가 섞여 있습니다. 실행 경로별 시간을 측정하고 클래스 로그·JFR·외부 호출 시간을 함께 보아야 합니다. 코드가 자주 쓰이는 정도에 따라 최적화 결과가 달라질 수 있다는 설명이지, “정확히 몇 회 호출되면 항상 C2가 실행된다”는 보장은 아닙니다.

## 7. 장애 사례: 기동은 성공했는데 첫 요청만 실패

입고 시스템에서 평소 쓰지 않던 엑셀 내보내기 기능을 처음 누르자 `NoClassDefFoundError`가 났다고 가정합니다. main과 서버 기동에 필요한 클래스는 존재해도, 해당 요청 경로에서 처음 필요한 라이브러리가 빠졌을 수 있습니다. 또는 이전 클래스 초기화 실패가 원인일 수 있습니다.

전체 예외 체인에서 첫 실패를 확인하고, 실제 패키징 결과와 런타임 classpath를 비교합니다. 기능별 smoke test가 기동 확인과 다른 이유도 여기에 있습니다. JIT 옵션을 변경하는 것은 누락된 클래스를 복구하지 못합니다. 실패 단계를 찾으면 조사 범위를 훨씬 빨리 좁힐 수 있습니다.

## 더 깊이: 실패가 발생한 단계로 원인을 좁히기

컴파일 시 'cannot find symbol'이 나면 javac가 소스의 이름·타입을 찾지 못한 상황입니다. 반면 실행 중 ClassNotFoundException은 특정 로더의 클래스 탐색과 연결되고, NoSuchMethodError는 이미 컴파일된 코드가 기대한 메서드와 런타임 클래스가 맞지 않을 때 나타날 수 있습니다. 마지막으로 NullPointerException은 연결이 끝난 코드가 실제 실행값 null을 잘못 사용한 상황일 수 있습니다.

| 실패 예 | 먼저 볼 증거 | 조사가 빗나가는 예 |
|---|---|---|
| javac의 심벌 오류 | 컴파일 classpath와 소스 타입 | 서버 Heap부터 확대 |
| UnsupportedClassVersionError | class major와 실행 JVM | DB 풀 설정 변경 |
| NoSuchMethodError | 호출·대상의 descriptor와 JAR 버전 | 메서드 호출 횟수만 측정 |
| ExceptionInInitializerError | 최초 static 초기화 예외 | 후속 로그만 보고 재시도 반복 |
| 업무 메서드의 NPE | 입력과 실제 실행 경로 | JIT 전체 비활성화 |

JVM의 시작 절차가 익숙해지면 스택 트레이스도 '가장 눈에 띄는 이름'이 아니라 '어느 단계가 어떤 입력에서 실패했는가'로 읽을 수 있습니다. 이것이 실행 구조를 공부하는 실무상의 이점입니다.

<details class="question"><summary>심화 Q. 컴파일 성공과 통합 테스트 성공이 왜 다른 보장인가요?</summary><div class="answer"><p>컴파일은 소스와 컴파일 시점 타입 정보에 근거합니다. 실제 실행 이미지의 라이브러리, 환경 변수, 외부 서비스, 클래스 초기화의 부수 효과까지 모두 실행해 검증하지 않습니다. 따라서 배포 산출물을 대상으로 대표 기능을 호출하는 검사가 별도로 필요합니다.</p><p>예를 들어 main은 정상 동작하지만 특정 보고서 기능에서만 누락 JAR을 처음 사용할 수 있습니다. 경로별 실행 검증은 기동 성공과 다른 증거를 제공합니다.</p></div></details>

## 8. 상세 면접 Q&A

<details class="question"><summary>Q1. javac와 JIT 컴파일러는 무엇이 다른가요?</summary><div class="answer"><p>javac는 Java 소스를 class 파일로 만듭니다. JIT는 실행 중 JVM 코드와 프로파일을 활용해 CPU별 기계 코드를 생성합니다. javac는 실행 전 타입과 문법을 확인하고, JIT는 실제 실행 정보를 활용할 수 있다는 차이가 있습니다.</p><p>둘 다 컴파일러이지만 목적과 시점이 다릅니다. 바이트코드는 기계 코드와 같지 않으며 javac 성공이 모든 런타임 의존성의 성공을 보장하지 않습니다.</p></div></details>
<details class="question"><summary>Q2. 인터프리터를 사용하면 CPU는 무엇을 실행하나요?</summary><div class="answer"><p>CPU는 인터프리터 구현의 기계 코드를 실행합니다. 그 코드가 바이트코드 명령을 읽고 필요한 동작을 수행합니다. 바이트코드가 CPU에 직접 입력되는 것으로 설명하면 추상 실행 기계와 실제 하드웨어를 혼동하게 됩니다.</p></div></details>
<details class="question"><summary>Q3. static 블록은 main보다 먼저 실행되나요?</summary><div class="answer"><p>일반적인 클래스 main 진입에서는 초기 클래스 초기화가 main 호출 전에 수행되므로 예제의 init이 먼저 출력됩니다. 그렇다고 모든 클래스의 static 블록이 기동 시 실행되는 것은 아닙니다. 각 클래스의 초기화 트리거를 따로 봐야 합니다.</p></div></details>
<details class="question"><summary>Q4. 링킹은 반드시 시작 시 한 번에 끝나나요?</summary><div class="answer"><p>검증·준비와 심벌 해석의 시점을 구분해야 합니다. JVM은 명세의 제약을 지키면서 심벌 참조를 지연 해석할 수 있습니다. 클래스가 초기화되었다는 사실만으로 모든 참조가 이미 해석되었다고 결론 내릴 수 없습니다.</p></div></details>
<details class="question"><summary>Q5. 모든 메서드를 처음부터 JIT하면 더 빠르지 않나요?</summary><div class="answer"><p>컴파일 자체의 비용과 생성 코드의 메모리 비용이 있습니다. 실행하지 않는 기능까지 컴파일하면 기동 시간이 늘 수 있고, 실행 프로파일 없이 최적화하면 활용 가능한 정보도 적습니다. HotSpot은 빈번한 경로에 비용을 집중하는 적응형 전략을 사용합니다.</p></div></details>
<details class="question"><summary>Q6. 배포 직후 느린 현상을 어떻게 검증하나요?</summary><div class="answer"><p>응답 지연을 클래스 로딩, 컴파일, GC, DB·네트워크 대기로 나누어 관측합니다. JFR와 JVM 로그를 요청 시간대에 맞추고 충분히 예열된 상태와 비교합니다. 단순히 몇 번 호출한 평균만 비교하면 외부 캐시와 커넥션 상태가 결과를 오염시킬 수 있습니다.</p></div></details>

## 9. 공식 문서와 복습 실험

- [JVMS 21 §5.2 시작](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html#jvms-5.2).
- [JVMS 21 §5.4 링킹](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html#jvms-5.4).
- [HotSpot 기술 개요](https://docs.oracle.com/en/java/javase/21/vm/java-virtual-machine-technology-overview.html).
- [javap 명세](https://docs.oracle.com/en/java/javase/21/docs/specs/man/javap.html).

`add`를 인스턴스 메서드로 바꾼 뒤 생성자와 호출 명령이 어떻게 바뀌는지 관찰하세요. `this`가 인자로 전달되는 방식은 04편, 호출 명령의 차이는 06편으로 연결됩니다.
