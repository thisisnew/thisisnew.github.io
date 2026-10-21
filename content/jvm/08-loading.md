{"n":8,"title":"클래스 로딩: 이름이 같아도 다른 타입인 이유","desc":"Bootstrap·Platform·Application 로더, 위임, defining loader, 클래스 정체성과 로딩 오류를 이해한다"}

## 시작 전에: 이 편에서 쓰는 말

처음 읽는다면 아래 용어의 뜻만 확인한 뒤 본문으로 넘어가세요. 먼저 예제의 결과를 예상하고, 실행 과정을 따라간 다음, 면접 답변을 펼쳐 자신의 설명과 비교하면 좋습니다.

| 용어 | 이 글에서의 뜻 |
|---|---|
| 바이너리 이름 | JVM에서 클래스를 식별할 때 사용하는 이름 |
| 정의 로더 | 클래스를 실제로 정의한 로더 |
| 위임 | 다른 로더에게 클래스 탐색을 맡기는 동작 |
| 언로딩 | 조건을 충족한 클래스 정의를 런타임에서 제거하는 일 |

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

## 차근차근 이해하기: 클래스 로더는 이름을 타입으로 만드는 경계다

클래스 이름을 사람 이름에, 정의 로더를 발급 기관에 비유해 봅시다. 이름이 같다고 같은 사람이라고 판단할 수 없듯이, 바이너리 이름이 같은 클래스라도 정의 로더가 다르면 별개의 타입일 수 있습니다. 반대로 두 로더가 모두 부모에게 위임해서 부모가 정의한 하나의 클래스를 받았다면 서로 다른 요청 경로를 거쳐도 같은 타입을 얻을 수 있습니다.

기존 예제의 두 로더는 같은 바이트를 직접 정의해서 차이를 드러냅니다. 일반적인 부모 우선 위임 흐름과 일부러 조건을 달리한 실습입니다. 따라서 “로더 객체를 두 개 만들면 언제나 클래스도 두 개 생긴다”로 일반화하면 안 됩니다. **최종적으로 누가 정의했는지**가 중요합니다.

### 같은 바이트인데 다른 타입이 되는 실험의 순서

| 단계 | 로더 A | 로더 B | 결과 |
|---|---|---|---|
| 입력 | Token의 class 바이트 | 같은 class 바이트 | 파일 내용은 동일 |
| 정의 | A가 직접 정의 | B가 직접 정의 | 정의 로더가 다름 |
| Class 이름 비교 | 같은 바이너리 이름 | 같은 바이너리 이름 | 이름 비교 true |
| Class 객체 비교 | A가 정의한 타입 | B가 정의한 타입 | 타입 비교 false |
| 대입 가능성 검사 | A 타입 기준 | B 타입 기준 | 예제에서는 false |

타입이 분리되는 것은 플러그인 격리에 유용할 수 있지만, 플러그인과 호스트가 서로 객체를 주고받을 때는 경계가 됩니다. 공통 인터페이스를 각 플러그인이 따로 정의하면 같은 이름의 인터페이스도 서로 다른 타입이 되어 통신이 어긋날 수 있습니다. 공유 API는 적절한 공통 상위 로더에서 정의하고 각 구현체가 이를 사용하도록 설계하는 이유입니다.

### 찾을 수 없음과 사용할 수 없음을 구분하기

직접 이름을 주고 클래스를 찾는 API에서 찾기에 실패하면 ClassNotFoundException을 볼 수 있습니다. 반면 실행 중 필요한 클래스 정의를 사용할 수 없는 상황에서는 NoClassDefFoundError를 볼 수 있습니다. 파일이 정말 빠졌을 수도 있지만, 그 클래스의 초기화가 앞서 실패해 잘못된 상태가 된 경우도 조사해야 합니다.

그래서 마지막 오류 메시지만 검색하지 말고 프로세스 시작부터 **처음 발생한 실패**를 찾는 것이 중요합니다. 첫 오류가 초기화 중 설정 파일 읽기 실패였는데 나중의 NoClassDefFoundError만 보고 JAR을 추가하면 실제 원인은 남습니다. 클래스 경로·정의 로더·초기화 실패라는 세 질문을 분리해 보세요.

### 재배포 때 메모리가 늘어나는 경로를 추적하기

이전 배포의 클래스 로더를 더 이상 사용하지 않는다고 생각해도, 장수명 스레드의 컨텍스트 로더나 등록된 콜백, static 컬렉션 등이 이전 로더 또는 그 클래스의 객체를 참조할 수 있습니다. 그러면 로더와 관련 클래스의 생존에 영향을 줍니다. 재배포 횟수만큼 메타데이터가 늘어나는 경우에는 “Metaspace가 작다”보다 “이전 배포에 도달하는 경로가 남는가”를 먼저 조사합니다.

다만 객체 하나가 사라졌다고 그 객체의 클래스가 즉시 언로드되는 것은 아닙니다. 클래스 언로딩은 로더의 도달 가능성 및 JVM·수집기의 처리 조건과 연결됩니다. 애플리케이션이 만든 객체 수명과 그 타입 정의의 수명은 별도로 봐야 합니다. 로더 통계와 Heap의 유지 경로를 함께 확인하면 양쪽을 연결할 수 있습니다.

<details class="question"><summary>확인 문제. 클래스 로더 누수라면 Heap dump는 볼 필요가 없나요?</summary><div class="answer"><p><strong>판단:</strong> 볼 가치가 있습니다. 클래스 메타데이터가 Native 쪽 Metaspace를 사용하더라도, 그 수명을 붙잡는 원인은 Heap 객체의 참조 경로일 수 있기 때문입니다.</p><p><strong>조사 예:</strong> 재배포 전후의 로더 수와 클래스 수를 비교하고, 이전 로더 또는 이전 배포의 객체를 붙잡는 장수명 스레드·컬렉션·콜백을 찾습니다. 사용하지 않는 로더라는 판단은 이름이 아니라 현재 배포와의 관계 및 참조 경로로 확인합니다.</p><p><strong>꼬리질문:</strong> Metaspace 한도를 늘리면 해결되나요? 임시 여유는 생길 수 있지만 재배포마다 유지 경로가 추가된다면 같은 문제가 늦게 반복될 뿐입니다. 등록 해제와 종료 처리 등 수명을 끊는 수정이 필요합니다.</p></div></details>

## 심화 실험실: 로더 두 개를 만들었는데 같은 클래스가 나오는 경우

### 문의한 창구와 발급한 기관은 다르다

이전 예제는 두 로더가 같은 바이트를 직접 정의했습니다. 이번에는 같은 부모를 둔 두 로더가 기본 위임 절차로 클래스를 요청합니다. 창구가 둘이어도 같은 본사에서 발급한 문서를 받으면 문서의 발급 주체는 같습니다. 이를 비교해야 defining loader의 의미가 분명해집니다.

```java
// file: Deep08.java
public class Deep08 {
    public static class Item { }
    public static void main(String[] args) throws Exception {
        ClassLoader parent = Deep08.class.getClassLoader();
        ClassLoader a = new ClassLoader(parent) { };
        ClassLoader b = new ClassLoader(parent) { };
        Class<?> x = a.loadClass("Deep08$Item");
        Class<?> y = b.loadClass("Deep08$Item");
        System.out.println("same=" + (x == y));
        System.out.println("definedByParent=" + (x.getClassLoader() == parent));
        System.out.println("requesterIsDefiner=" + (x.getClassLoader() == a));
    }
}
```

```sh
javac --release 21 Deep08.java
java Deep08
```

결과는 `same=true`, `definedByParent=true`, `requesterIsDefiner=false`입니다. a와 b를 만들었다는 사실은 두 클래스가 정의되었다는 뜻이 아닙니다. 이 예제에서 기본 loadClass는 부모에게 위임하고 부모가 찾은 클래스를 반환합니다. 반환된 Class 객체의 getClassLoader는 요청자 a가 아니라 실제 정의 로더를 나타냅니다.

### 두 실험을 함께 정리하기

| 로딩 방식 | 최종 정의 | 타입 비교 | 활용/위험 |
|---|---|---|---|
| 기존 Lesson08의 직접 defineClass | a와 b 각각 | 서로 다름 | 격리는 가능하지만 경계 객체 캐스팅 주의 |
| Deep08의 부모 위임 | 공통 부모 | 동일 | 공통 API 타입을 공유 가능 |

플러그인 시스템에서 `Plugin` 인터페이스까지 각 로더가 따로 정의하면 호스트가 알고 있는 Plugin과 플러그인이 구현한 Plugin이 달라질 수 있습니다. 이름이 같아도 호스트의 캐스팅은 실패합니다. 공통 API를 부모에서 공유하고 플러그인 내부 구현을 격리하는 설계는 이름 충돌만이 아니라 객체가 경계를 넘을 때의 타입 일관성을 위한 것입니다.

### TCCL이 등장하는 이유

공통 라이브러리는 상위 로더에서 정의되었지만 실제 구현체는 애플리케이션 로더 아래에 있을 수 있습니다. 부모는 일반적으로 자식의 클래스 경로를 자동 탐색하지 않습니다. Thread Context ClassLoader는 일부 라이브러리나 서비스 탐색 API가 현재 실행 문맥의 로더를 사용하도록 전달하는 수단입니다. 모든 클래스 로딩이 자동으로 TCCL을 쓰는 것은 아니므로 호출하는 API의 규약을 확인해야 합니다.

장수명 스레드에 이전 배포의 TCCL을 남기면 이전 로더를 붙잡는 경로가 될 수 있습니다. 임시로 바꾼 컨텍스트 로더는 작업 후 복원하고, 플러그인 해제 시 스레드·콜백·레지스트리 등록도 정리해야 합니다. URLClassLoader.close는 파일 자원을 닫는 동작이지 이미 살아 있는 타입과 객체를 강제로 언로드하는 명령이 아닙니다.

### 장애 조사에서 남길 정보

“com.example.Item을 com.example.Item으로 바꿀 수 없다”는 메시지를 만나면 양쪽 Class 객체의 이름만 비교하지 말고 로더 정보와 코드 출처를 함께 기록합니다. 모듈 정보도 접근 문제에 도움이 됩니다. 정상적인 경우에도 부트스트랩 로더는 null로 표현될 수 있으므로 로그 출력 코드는 null을 처리해야 합니다. JAR 중복 제거는 원인이 중복 정의라는 증거를 확보한 뒤 수행합니다.

<details class="question"><summary>심화 면접. 부모 우선 위임을 쓰면 모든 의존성 충돌이 해결되나요?</summary><div class="answer"><p><strong>답변:</strong> 아닙니다. 공유되는 타입의 일관성에는 도움이 되지만 부모에 있는 다른 버전이 선택되어 필요한 메서드가 없을 수도 있습니다. 같은 타입을 공유하는 문제와 요구하는 API 버전이 맞는 문제는 다릅니다.</p><p><strong>설계:</strong> 경계를 넘는 API는 공유하고 내부 구현 의존성은 필요한 범위에서 격리합니다. 어떤 클래스가 어떤 로더에서 정의되는지 명시적으로 확인하겠습니다.</p><p><strong>검증:</strong> 두 로더의 존재만으로 격리를 판단하지 않고 실제 Class 동일성, 정의 로더, 메서드 호환성과 플러그인 해제 후 참조 정리까지 보겠습니다.</p></div></details>

추가 근거: [ClassLoader.loadClass 기본 위임](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ClassLoader.html#loadClass(java.lang.String,boolean)), [ServiceLoader](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/ServiceLoader.html).

## 8. 상세 면접 Q&A

<details class="question"><summary>Q1. 같은 이름의 클래스끼리 왜 캐스팅이 실패하나요?</summary><div class="answer"><p>정체성에 defining loader가 포함되기 때문입니다. 이름과 바이트가 같아도 서로 다른 로더가 정의하면 다른 타입일 수 있습니다. getClass().getClassLoader()와 클래스 출처를 함께 확인하면 중복 로딩을 조사할 수 있습니다.</p><p><strong>구체적으로:</strong> 플러그인 A와 B가 같은 패키지의 DTO를 각각 정의하면 클래스 이름 출력은 같아도 JVM 타입은 다릅니다. 객체를 전달하는 경계에서 ClassCastException 등이 드러날 수 있습니다.</p><p><strong>꼬리질문까지:</strong> 공통 API를 어떤 로더가 정의하도록 할지 설계해야 하며 이름 문자열만 비교해서 호환성을 판단하지 않습니다.</p></div></details>
<details class="question"><summary>Q2. Bootstrap 로더가 null이면 클래스가 로드되지 않았다는 뜻인가요?</summary><div class="answer"><p>아닙니다. Class.getClassLoader()가 Bootstrap을 null로 표현할 수 있는 API 규칙입니다. String.class가 존재하며 사용 가능한 사실과 모순되지 않습니다. null을 실패 표시로 해석하면 안 됩니다.</p><p><strong>구체적으로:</strong> 핵심 클래스의 getClassLoader 결과가 null인 것은 API의 표현 방식입니다. String이 실제로 존재하고 동작하는 것과 모순되지 않습니다.</p><p><strong>꼬리질문까지:</strong> null을 로딩 실패로 처리하는 진단 코드를 만들지 말고 Bootstrap 정의 여부를 구분해 출력하세요.</p></div></details>
<details class="question"><summary>Q3. 부모 우선 위임은 JVM의 절대 규칙인가요?</summary><div class="answer"><p>기본 ClassLoader 구현의 중요한 전략이지만 모든 사용자 로더의 유일한 구현 방식은 아닙니다. 컨테이너나 플러그인은 다른 정책을 쓸 수 있습니다. 다만 타입 안정성을 위한 로딩 제약과 접근 규칙을 지켜야 하므로 임의의 중복 정의가 안전하다는 뜻도 아닙니다.</p><p><strong>구체적으로:</strong> 일반적인 ClassLoader 구현의 위임 관행과 JVM의 타입 안전성 규칙은 다른 층위입니다. 특정 시스템은 격리 목적 등으로 다른 탐색 순서를 구현할 수 있습니다.</p><p><strong>꼬리질문까지:</strong> 위임을 바꾸면 중복 타입과 접근 경계 문제가 생길 수 있으므로 공유 API의 정의 위치를 검토해야 합니다.</p></div></details>
<details class="question"><summary>Q4. 로딩을 요청한 로더가 타입의 정체성을 결정하나요?</summary><div class="answer"><p>정체성은 defining loader를 봅니다. 요청한 로더가 부모에게 위임하면 정의한 로더는 부모일 수 있습니다. initiating loader와 defining loader를 구분하면 여러 플러그인이 공통 API 타입을 공유하는 구조를 설명할 수 있습니다.</p><p><strong>구체적으로:</strong> 자식 로더가 부모에게 요청을 전달하고 부모가 정의한 클래스를 받으면 자식은 요청 경로에 참여했어도 정의 로더는 부모입니다.</p><p><strong>꼬리질문까지:</strong> 이름과 로더를 진단 로그에 남길 때 initiating과 defining 중 무엇을 의미하는지 명확히 하세요.</p></div></details>
<details class="question"><summary>Q5. class 파일이 있는데 NoClassDefFoundError가 날 수 있나요?</summary><div class="answer"><p>가능합니다. 현재 로더가 그 위치를 찾지 못하거나 의존 클래스가 없거나, 이전 초기화 실패로 클래스가 오류 상태일 수 있습니다. 최상위 메시지만 보지 말고 최초 예외와 원인 체인, 로더·classpath를 확인해야 합니다.</p><p><strong>구체적으로:</strong> 첫 사용에서 static 초기화가 실패했을 수 있습니다. 이후 오류만 보면 파일이 사라진 것처럼 오해하지만 최초 예외는 설정·외부 자원 문제일 수 있습니다.</p><p><strong>꼬리질문까지:</strong> 시간순으로 첫 실패를 찾아야 하며 JAR 추가와 클래스 경로 변경을 무작정 반복하지 않습니다.</p></div></details>
<details class="question"><summary>Q6. 클래스 로더 누수는 Heap 문제인가요, Native 문제인가요?</summary><div class="answer"><p>남아 있는 로더와 그 참조 관계는 Heap에서 조사할 수 있고, 그 로더가 유지하는 클래스 메타데이터는 Metaspace 사용 증가로 나타날 수 있습니다. 하나의 참조 유지 문제가 여러 영역에 영향을 주므로 Heap과 Native 지표를 함께 연결해야 합니다.</p><p><strong>구체적으로:</strong> Heap의 장수명 객체가 이전 로더를 붙잡으면 Native 메타데이터가 함께 유지될 수 있습니다. 문제가 보이는 영역과 원인을 가진 참조의 위치가 다를 수 있습니다.</p><p><strong>꼬리질문까지:</strong> 재배포마다 로더 수가 늘어나는지 보고 이전 배포로 향하는 참조를 제거하는 것이 핵심입니다.</p></div></details>

## 9. 공식 근거와 복습

- [JVMS §5.3 생성과 로딩](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html#jvms-5.3).
- [ClassLoader API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ClassLoader.html).
- [Class API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Class.html).
- [JLS §12.2 로딩](https://docs.oracle.com/javase/specs/jls/se21/html/jls-12.html#jls-12.2).

두 IsolatedLoader가 직접 define하지 않고 부모에 Token 로딩을 위임하도록 바꾸면 같은 타입을 얻는지 비교하세요. 직접 정의와 위임의 차이를 말로 설명하는 것이 핵심입니다.

