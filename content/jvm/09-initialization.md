{"n":9,"title":"링킹과 초기화: static이 실행되는 정확한 시점","desc":"Verification·Preparation·Resolution·Initialization, 상수 인라이닝과 초기화 실패를 실험한다"}

## 1. 건물 검사와 실제 입주는 다르다

건물을 받았다고 곧바로 입주하는 것은 아닙니다. 구조가 맞는지 확인하고, 기본 설비를 마련하고, 외부 연결을 준비한 뒤 입주 작업을 합니다. 클래스도 로딩 뒤 검증·준비·해석이라는 링킹 작업과 초기화 작업을 구분합니다. 준비 과정에서 Java의 static 블록을 전부 실행하는 것이 아닙니다.

이 비유가 모든 작업의 고정 시점을 뜻하지는 않습니다. JVM은 제약을 만족하는 범위에서 심벌 해석을 늦출 수 있습니다. 초기화 전에 검증·준비는 필요하지만, 해당 클래스가 참조하는 모든 메서드·필드 해석을 전부 끝내야만 초기화할 수 있는 것은 아닙니다. [근거: JVMS §5.4](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html#jvms-5.4)

## 2. 네 단계의 역할을 비교하기

| 단계 | 핵심 질문 | 수행하지 않는 것으로 구분할 것 |
|---|---|---|
| Verification | 형식과 타입 사용이 유효한가? | 업무 로직의 정답 검증 |
| Preparation | static 저장 공간과 기본값이 준비되었나? | 임의의 Java 초기화식 실행 |
| Resolution | 심벌이 가리키는 실제 타입·필드·메서드는 무엇인가? | 모든 호출의 최종 수신 객체를 영구 고정 |
| Initialization | 클래스 초기화 코드를 규칙대로 실행했나? | 인스턴스마다 생성자 실행 |

해석과 가상 메서드 선택도 구분해야 합니다. 심벌 메서드 참조를 해석했다고 수신 객체에 따른 모든 디스패치가 없어지는 것은 아닙니다. 이름·descriptor·접근성·상속 규칙 등이 링크 시의 연결에 영향을 줍니다.

## 3. static의 순서를 보여 주는 예제

```java
// file: Lesson09.java
public class Lesson09 {
    static class Config {
        static final int CONSTANT = 7;
        static final Integer BOXED = 8;
        static int first = readSecond();
        static int second = 42;
        static int readSecond() { return second; }
        static { System.out.println("Config init"); }
    }
    public static void main(String[] args) throws Exception {
        System.out.println(Config.CONSTANT);
        Class.forName("Lesson09$Config", false, Lesson09.class.getClassLoader());
        System.out.println("loaded without init request");
        System.out.println(Config.first);
        System.out.println(Config.second);
        System.out.println(Config.BOXED);
    }
}
```

```sh
javac --release 21 -g Lesson09.java
java Lesson09
javap -c -v -p 'Lesson09$Config'
javap -c -p Lesson09
```

논리적 출력은 7, `loaded without init request`, `Config init`, 0, 42, 8 순서입니다. `Class.forName(..., false, ...)`는 초기화를 요청하지 않습니다. 처음 `Config.first`를 읽을 때 초기화가 진행됩니다. first의 계산 중에는 second의 명시적 대입이 아직 실행되지 않아 기본값 0을 읽습니다.

이것은 초기화 순서의 효과입니다. static int가 항상 0으로 유지된다는 뜻이 아닙니다. 각 초기화식과 static 블록은 언어 규칙의 순서에 따라 실행되고, 그 뒤 second는 42가 됩니다. 자기 초기화 과정에서 다른 필드를 읽는 복잡한 코드는 기본값 노출과 순환 의존을 만들기 쉽습니다.

## 4. static final이면 모두 컴파일 상수인가

아닙니다. Java의 상수 변수는 기본형 또는 String이고 상수 표현식으로 초기화된 final 변수 등 언어의 조건을 만족해야 합니다. `static final int CONSTANT = 7`은 해당하지만 `static final Integer BOXED = 8`은 아닙니다. `static final int X = loadFromDb()`도 해당하지 않습니다.

컴파일 타임 상수의 사용은 호출자 코드에 값이 들어갈 수 있어 그 사용만으로 선언 클래스를 초기화하지 않습니다. 반대로 일반 static 필드의 읽기는 초기화 트리거가 됩니다. 필드를 실제로 선언한 타입과 소스에서 접근에 사용한 이름도 구분해야 합니다. 상위 클래스가 선언한 필드를 하위 이름으로 접근했다고 하위까지 반드시 초기화되는 것은 아닙니다. [근거: JLS §12.4.1](https://docs.oracle.com/javase/specs/jls/se21/html/jls-12.html#jls-12.4.1)

## 5. ConstantValue와 초기화의 세부 경계

준비에서 static 필드는 기본값을 갖습니다. JVM 사양의 초기화 절차는 ConstantValue가 있는 static final 필드의 설정도 별도로 규정합니다. 따라서 “모든 final 상수는 Preparation에서 Java 소스 값으로 대입된다”는 식으로 단순화하지 않는 것이 좋습니다. 상수 인라이닝 때문에 호출자에서 필드 읽기 자체가 없어질 수도 있습니다.

클래스 초기화 메서드 `<clinit>`은 컴파일러가 필요한 static 초기화 동작을 모은 특수 메서드입니다. 모든 클래스에 의미 있는 `<clinit>`이 반드시 생기는 것은 아닙니다. 생성자 `<init>`는 객체 초기화와 연결되며 클래스 초기화와 다른 수명을 갖습니다.

## 6. 초기화는 동시 실행과 실패 상태가 있다

여러 스레드가 같은 클래스를 처음 사용해도 JVM은 클래스 초기화 절차를 동기화합니다. 한 스레드가 수행하는 동안 다른 스레드는 완료를 기다릴 수 있습니다. 이 때문에 static 초기화 안의 느린 네트워크 접근이 여러 요청을 동시에 막을 수 있습니다. 다른 클래스 초기화와 상호 대기하면 교착 위험도 생깁니다.

초기화 코드가 실패하면 클래스는 오류 상태가 될 수 있습니다. 첫 사용에서는 원인에 따라 `ExceptionInInitializerError` 등이 보이고, 나중에는 `NoClassDefFoundError: Could not initialize class` 형태가 나타날 수 있습니다. 실패 후 요청마다 static 블록을 처음부터 재시도하는 모델이 아닙니다. 정상적으로 복구하려면 초기화 설계를 바꾸고 적절한 배포·재시작 등의 수명 관리가 필요합니다.

## 7. 장애 사례: 라이브러리 상수만 바꿨는데 값이 옛날 그대로

공통 라이브러리의 `public static final int MAX_BATCH = 100`을 200으로 바꾸고 라이브러리 JAR만 교체했다고 가정합니다. 호출자에 100이 컴파일되어 있으면 호출자 재컴파일 없이 200을 읽지 않을 수 있습니다. 이것은 JVM 캐시가 갱신되지 않은 문제와 다릅니다.

javap로 호출자의 getstatic 여부와 값 적재 명령을 확인합니다. 운영 중 변경 가능한 정책값을 컴파일 타임 상수로 배포하는 것이 적절한지도 검토합니다. 설정 서버나 DB 조회를 쓰라는 무조건적 결론이 아니라, 변경 수명과 바이너리 호환성을 설계에 반영해야 한다는 뜻입니다.

## 더 깊이: 상속·인터페이스·상수 배포의 경계

클래스 초기화에는 상위 클래스의 초기화 순서도 관련됩니다. 자식 객체를 만들기 전에 필요한 부모 초기화가 수행됩니다. 하지만 인터페이스의 초기화 규칙을 클래스 상속과 기계적으로 같다고 보면 안 됩니다. default 메서드를 선언한 특정 상위 인터페이스 등 규칙에 따른 경우와 단순한 인터페이스 참조를 구분해야 합니다. JLS §12.4와 JVMS §5.5가 세부 조건을 정의합니다.

클래스 리터럴 `Config.class`를 얻는 행위나 Config 배열을 만드는 행위도 Config 인스턴스를 new하는 것과 같은 초기화 트리거라고 단정하지 않습니다. 반사 API의 메서드 역시 initialize 인자와 실제 사용 방식을 따져야 합니다. 이름에 Class가 보인다고 초기화가 모두 완료되는 것은 아닙니다.

공개 상수를 배포할 때는 소비자 재컴파일이 중요한 변경 절차가 될 수 있습니다. 예를 들어 예전 호출자에 100이 박혀 있는데 새 서버는 정책 200을 기대하면, 같은 라이브러리 이름을 사용해도 노드 간 동작이 달라질 수 있습니다. 상수는 편리하지만 값 변경의 배포 수명을 숨기지 않습니다.

<details class="question"><summary>심화 Q. Class 객체를 얻었으면 그 클래스의 static 블록이 완료됐다고 볼 수 있나요?</summary><div class="answer"><p>볼 수 없습니다. 클래스 리터럴이나 초기화를 요청하지 않는 로딩으로 Class 객체를 얻을 수 있습니다. '타입을 나타내는 객체가 있다'와 '초기화가 끝났다'는 다른 상태입니다.</p><p>동적 등록 시스템에서는 타입 정보를 수집하는 단계와 실제 인스턴스 생성·초기화 단계를 구분하면 기동 비용과 실패 위치를 더 명확히 관리할 수 있습니다.</p></div></details>

## 8. 상세 면접 Q&A

<details class="question"><summary>Q1. 클래스 로딩과 초기화는 같은가요?</summary><div class="answer"><p>아닙니다. 로딩은 이진 표현으로 클래스를 만들고, 초기화는 규정된 static 초기화 동작을 수행합니다. 초기화하지 않는 Class.forName 호출로 차이를 관찰할 수 있습니다. 클래스가 존재하는 것과 초기화가 완료된 것은 다릅니다.</p></div></details>
<details class="question"><summary>Q2. Resolution은 초기화 전에 모두 끝나나요?</summary><div class="answer"><p>그럴 필요는 없습니다. JVM은 해석을 지연할 수 있습니다. 검증·준비와 해석의 시점을 나누어 설명해야 합니다. 초기화 성공 후 드물게 사용한 경로에서 링크 오류가 드러나는 이유와도 연결됩니다.</p></div></details>
<details class="question"><summary>Q3. static final Integer와 int의 차이는 무엇인가요?</summary><div class="answer"><p>final Integer는 참조를 바꿀 수 없다는 뜻이지 언어의 상수 변수가 된다는 뜻은 아닙니다. 상수 변수의 타입과 초기화식 조건을 만족해야 컴파일 타임 상수 규칙을 적용할 수 있습니다. 그 차이가 초기화 트리거와 호출자 바이트코드에 영향을 줍니다.</p></div></details>
<details class="question"><summary>Q4. 왜 first가 42가 아니라 0인가요?</summary><div class="answer"><p>first 초기화식이 readSecond를 호출하는 시점에는 second=42라는 명시적 초기화가 아직 실행되지 않았습니다. 기본값을 읽어 first가 0이 됩니다. 나중에 second가 42로 바뀌어도 이미 계산된 first가 자동 갱신되지는 않습니다.</p></div></details>
<details class="question"><summary>Q5. 초기화 실패 뒤 재호출하면 자동 재시도하나요?</summary><div class="answer"><p>일반적으로 해당 클래스는 오류 상태로 남아 후속 사용도 실패합니다. 첫 원인 예외를 조사해야 하며 후속 NoClassDefFoundError만 보고 JAR 누락으로 단정하지 않습니다. 재시도 가능한 외부 연결은 static 초기화에 묶는 것이 적절한지 검토합니다.</p></div></details>
<details class="question"><summary>Q6. JVM의 클래스 초기화 동기화가 Bean의 스레드 안전성을 보장하나요?</summary><div class="answer"><p>클래스 초기화 완료와 관련된 보장은 이후 임의의 가변 상태 갱신을 모두 안전하게 만들지 않습니다. 요청마다 바꾸는 필드는 별도의 동시성 설계가 필요합니다. static 초기화의 안전성과 프로그램 전체의 thread safety는 다릅니다.</p></div></details>

## 9. 공식 문서와 복습

- [JVMS §5.4 링킹](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html#jvms-5.4).
- [JVMS §5.5 초기화 절차](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html#jvms-5.5).
- [JLS §12.4 초기화](https://docs.oracle.com/javase/specs/jls/se21/html/jls-12.html#jls-12.4).
- [JVMS §4.7.2 ConstantValue](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html#jvms-4.7.2).

CONSTANT를 `Integer.parseInt("7")`의 결과로 바꾸고 출력 순서를 예상한 뒤 실행하세요. final 여부만으로 상수를 판정할 수 없는 이유를 확인할 수 있습니다.
