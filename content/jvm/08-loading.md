{"n":8,"title":"클래스 로딩: 이름이 같아도 다른 타입인 이유","desc":"Bootstrap·Platform·Application 로더, 위임, defining loader, 클래스 정체성과 로딩 오류를 이해한다"}

## 1. 클래스 이름만으로는 부족하다

두 회사에 모두 “김검수”라는 직원이 있어도 사번 체계와 소속이 다르면 다른 사람입니다. JVM의 클래스도 이름만 같다고 같은 타입이 아닙니다. 런타임 클래스의 정체성에는 **이진 이름과 정의한 클래스 로더(defining loader)**가 함께 들어갑니다.

따라서 `com.example.Order`라는 같은 class 바이트를 서로 다른 로더가 별도로 정의하면 다른 타입이 될 수 있습니다. 한쪽 객체를 다른 쪽 Order로 캐스팅하면 이름이 같은데도 `ClassCastException`이 발생할 수 있습니다. 플러그인·애플리케이션 서버·개발용 재시작 로더에서 중요한 원리입니다. [근거: JVMS §5.3](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html#jvms-5.3)

## 2. JDK 21의 기본 로더를 이해하기

| 로더 | 대표 책임 | 주의할 점 |
|---|---|---|
| Bootstrap | 핵심 클래스 로딩 | Java 객체로 그대로 표현되지 않아 API에서 null로 보일 수 있음 |
| Platform | 플랫폼 클래스의 일부 | Java 8의 Extension 로더 그림을 그대로 쓰지 않기 |
| Application/System | 애플리케이션 classpath 등 | 모든 로딩이 무조건 이 로더에서 끝나는 것은 아님 |
| 사용자 정의 | 플러그인·격리·동적 클래스 등 | 위임·중복 정의·수명 관리 필요 |

“부모”는 Java 클래스 상속 관계가 아니라 로딩 요청을 위임하는 관계입니다. 일반적인 ClassLoader의 기본 loadClass 동작은 이미 로드했는지 확인하고 부모에게 위임한 뒤 자신의 findClass를 시도하는 식입니다. 다만 모든 사용자 로더가 사양상 무조건 동일한 부모 우선 알고리즘을 사용해야 하는 것은 아닙니다. 로딩 제약과 보안·접근 규칙을 만족해야 합니다.

## 3. 기본 로더를 출력하는 실습

```java
// file: Lesson08.java
import java.nio.file.Files;
import java.nio.file.Path;

public class Lesson08 {
    public static class Token { }
    static final class IsolatedLoader extends ClassLoader {
        Class<?> define(byte[] bytes) {
            return defineClass("Lesson08$Token", bytes, 0, bytes.length);
        }
    }
    public static void main(String[] args) throws Exception {
        System.out.println("String loader=" + String.class.getClassLoader());
        System.out.println("app loader=" + Lesson08.class.getClassLoader());
        byte[] bytes = Files.readAllBytes(Path.of("Lesson08$Token.class"));
        Class<?> first = new IsolatedLoader().define(bytes);
        Class<?> second = new IsolatedLoader().define(bytes);
        System.out.println("same name=" + first.getName().equals(second.getName()));
        System.out.println("same type=" + (first == second));
        System.out.println("assignable=" + first.isAssignableFrom(second));
    }
}
```

```sh
javac --release 21 -g Lesson08.java
java -Xlog:class+load=info Lesson08
```

이 예제는 컴파일 결과가 있는 현재 디렉터리에서 실행해야 합니다. String 로더는 보통 `null`, 앱 로더는 구현체 정보가 출력됩니다. 뒤의 논리적 결과는 `same name=true`, `same type=false`, `assignable=false`입니다. 두 로더가 같은 이름과 바이트를 각각 정의했기 때문입니다.

이것은 loadClass의 위임을 관찰하는 예제가 아니라 **서로 다른 defining loader가 직접 정의한 타입**을 보여 주는 예제입니다. defineClass를 직접 호출한 교육용 실험이며 운영 플러그인 로더 구현으로 그대로 사용하지 않습니다.

## 4. initiating loader와 defining loader

로딩을 요청한 로더가 항상 클래스를 직접 정의하는 것은 아닙니다. A 로더가 부모 B에 위임하여 B가 클래스를 정의했다면, A는 로딩을 시작한 initiating loader가 될 수 있고 B가 defining loader입니다. 타입 정체성에서 중요한 것은 정의한 로더입니다.

그래서 두 사용자 로더가 부모로 위임하여 같은 라이브러리를 받으면 같은 타입을 공유할 수 있습니다. 반대로 각 로더 안에 라이브러리를 중복 정의하면 경계를 넘는 API 객체에서 문제가 생길 수 있습니다. 플러그인 인터페이스를 공통 부모가 정의하고 구현체만 격리하는 패턴은 이 원리를 활용합니다.

배열 클래스는 일반 class 파일을 읽어 그대로 정의하는 것과 다릅니다. JVM이 배열 클래스를 만들며 참조 배열의 정체성은 구성 요소 타입과 로더에 연결됩니다. 기본형 자체는 별도의 로딩으로 만드는 일반 클래스가 아닙니다. [근거: JVMS §5.3.3](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html#jvms-5.3.3)

## 5. 로딩·링킹·초기화는 다른 사건

로딩은 바이트 표현으로부터 클래스를 만드는 과정입니다. `Class.forName(name, false, loader)`는 초기화를 요청하지 않고 클래스를 얻는 데 사용할 수 있습니다. 반면 일반적인 `Class.forName(name)`은 초기화를 유발할 수 있습니다. “클래스가 메모리에 보이면 static 블록도 반드시 끝났다”는 설명은 잘못입니다.

클래스 로딩은 classpath만의 문제가 아닐 수 있습니다. 모듈 경계, 접근 권한, 서비스 로딩, 컨텍스트 클래스 로더 등도 고려합니다. 특히 라이브러리가 어떤 로더로 클래스를 찾는지 모르면, 파일이 JAR 안에 존재하는데도 찾지 못하는 상황이 이해되지 않습니다.

## 6. 실패 이름에서 조사 방향 찾기

| 오류 | 대표 조사 방향 |
|---|---|
| ClassNotFoundException | 명시적 로딩 요청 이름·classpath·사용 로더 |
| NoClassDefFoundError | 실행 의존성 누락, 이전 초기화 실패 등 원인 체인 |
| ClassCastException | 실제 타입과 defining loader, 중복 라이브러리 |
| LinkageError 계열 | 중복 정의·바이너리 불일치·로딩 제약 |

예외 이름 하나만으로 원인을 단정하지는 마세요. 특히 NoClassDefFoundError는 파일 누락만 뜻하지 않습니다. 먼저 난 ExceptionInInitializerError 때문에 클래스가 오류 상태가 되었을 수도 있습니다. 최초 실패 로그와 cause를 찾아야 합니다.

## 7. 장애 사례: 재배포할수록 Metaspace가 증가

플러그인을 새 로더로 반복 로드하는데 예전 로더가 static 컬렉션이나 살아 있는 스레드에 계속 참조된다고 가정합니다. 이전 클래스와 로더의 수명이 끝나지 않아 클래스 메타데이터가 계속 남을 수 있습니다. 이 경우 Metaspace 크기만 늘리는 것은 증가 원인을 제거하지 못합니다.

클래스 수와 로더 수가 재배포마다 어떻게 변하는지 보고, 이전 로더를 붙잡는 스레드·ThreadLocal·콜백·전역 레지스트리를 확인합니다. 클래스 언로딩은 로더 도달 가능성과 JVM의 수집 조건에 연결되며 특정 API를 호출했다고 즉시 발생하는 것으로 보장되지 않습니다. 로더의 수명도 자원의 수명으로 설계해야 합니다.

## 더 깊이: 로딩 제약과 접근 권한

클래스 로더를 격리하면 같은 이름을 따로 정의할 수 있지만, 메서드 시그니처를 통해 타입이 교차할 때 타입 일관성이 필요합니다. JVM의 loading constraints는 로더가 다르다는 이유로 서로 모순되는 타입 관계를 아무렇게나 연결하지 못하게 합니다. 모든 로더의 동일 이름이 항상 같은 타입이라는 뜻도, 항상 완전히 독립적이라는 뜻도 아닙니다.

패키지 이름만 같다고 같은 런타임 패키지 권한을 자동 공유하지도 않습니다. 정의한 로더와 모듈·접근 규칙까지 관련됩니다. 플러그인에 호스트의 내부 패키지와 같은 문자열 이름을 붙였다고 package-private 멤버를 자유롭게 호출할 수 있다고 생각하면 안 됩니다.

이 때문에 공통 API는 호스트와 플러그인이 같은 정의를 공유하고, 구현체와 전용 라이브러리는 격리하는 경계가 필요합니다. 'child-first로 바꾸면 모든 충돌 해결' 같은 규칙은 없습니다. 어떤 타입을 경계 너머로 전달할지, 어느 로더가 정의할지부터 설계해야 합니다.

<details class="question"><summary>심화 Q. 클래스를 초기화하지 않고 로드하면 아무 부수 효과도 없나요?</summary><div class="answer"><p>그 클래스의 static 초기화를 요청하지 않는 것과 전체 로딩 과정이 무부수 효과라는 것은 다릅니다. 사용자 로더 자체의 코드가 파일·네트워크를 읽거나 다른 작업을 수행할 수 있습니다.</p><p>또한 타입 메타데이터와 의존 관계를 준비하는 JVM 작업도 있습니다. initialize=false는 '모든 작업을 하지 않는다'는 플래그가 아니라 초기화 요청 여부의 제어입니다.</p></div></details>

## 8. 상세 면접 Q&A

<details class="question"><summary>Q1. 같은 이름의 클래스끼리 왜 캐스팅이 실패하나요?</summary><div class="answer"><p>정체성에 defining loader가 포함되기 때문입니다. 이름과 바이트가 같아도 서로 다른 로더가 정의하면 다른 타입일 수 있습니다. getClass().getClassLoader()와 클래스 출처를 함께 확인하면 중복 로딩을 조사할 수 있습니다.</p></div></details>
<details class="question"><summary>Q2. Bootstrap 로더가 null이면 클래스가 로드되지 않았다는 뜻인가요?</summary><div class="answer"><p>아닙니다. Class.getClassLoader()가 Bootstrap을 null로 표현할 수 있는 API 규칙입니다. String.class가 존재하며 사용 가능한 사실과 모순되지 않습니다. null을 실패 표시로 해석하면 안 됩니다.</p></div></details>
<details class="question"><summary>Q3. 부모 우선 위임은 JVM의 절대 규칙인가요?</summary><div class="answer"><p>기본 ClassLoader 구현의 중요한 전략이지만 모든 사용자 로더의 유일한 구현 방식은 아닙니다. 컨테이너나 플러그인은 다른 정책을 쓸 수 있습니다. 다만 타입 안정성을 위한 로딩 제약과 접근 규칙을 지켜야 하므로 임의의 중복 정의가 안전하다는 뜻도 아닙니다.</p></div></details>
<details class="question"><summary>Q4. 로딩을 요청한 로더가 타입의 정체성을 결정하나요?</summary><div class="answer"><p>정체성은 defining loader를 봅니다. 요청한 로더가 부모에게 위임하면 정의한 로더는 부모일 수 있습니다. initiating loader와 defining loader를 구분하면 여러 플러그인이 공통 API 타입을 공유하는 구조를 설명할 수 있습니다.</p></div></details>
<details class="question"><summary>Q5. class 파일이 있는데 NoClassDefFoundError가 날 수 있나요?</summary><div class="answer"><p>가능합니다. 현재 로더가 그 위치를 찾지 못하거나 의존 클래스가 없거나, 이전 초기화 실패로 클래스가 오류 상태일 수 있습니다. 최상위 메시지만 보지 말고 최초 예외와 원인 체인, 로더·classpath를 확인해야 합니다.</p></div></details>
<details class="question"><summary>Q6. 클래스 로더 누수는 Heap 문제인가요, Native 문제인가요?</summary><div class="answer"><p>남아 있는 로더와 그 참조 관계는 Heap에서 조사할 수 있고, 그 로더가 유지하는 클래스 메타데이터는 Metaspace 사용 증가로 나타날 수 있습니다. 하나의 참조 유지 문제가 여러 영역에 영향을 주므로 Heap과 Native 지표를 함께 연결해야 합니다.</p></div></details>

## 9. 공식 근거와 복습

- [JVMS §5.3 생성과 로딩](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html#jvms-5.3).
- [ClassLoader API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ClassLoader.html).
- [Class API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Class.html).
- [JLS §12.2 로딩](https://docs.oracle.com/javase/specs/jls/se21/html/jls-12.html#jls-12.2).

두 IsolatedLoader가 직접 define하지 않고 부모에 Token 로딩을 위임하도록 바꾸면 같은 타입을 얻는지 비교하세요. 직접 정의와 위임의 차이를 말로 설명하는 것이 핵심입니다.
