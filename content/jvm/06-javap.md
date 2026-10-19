{"n":6,"title":"javap로 바이트코드 읽기: 객체·배열·호출·예외 실습","desc":"javac -g와 javap -c -v -p로 실제 class 파일을 읽고, new·dup·invoke·배열 명령을 해석한다"}

## 1. javap는 역컴파일러와 무엇이 다른가

완성된 기계의 부품 목록과 조립 지시를 보는 것이 javap에 가깝습니다. 사람이 썼던 Java 문장을 완전히 복원하는 도구는 아닙니다. `javap -c`는 메서드의 JVM 명령을, `-v`는 상수 풀과 Code 속성 등 자세한 정보를, `-p`는 private 멤버까지 보여 줍니다. `-l`은 줄 번호·지역변수 표를 요청합니다.

`javac -g`는 디버그 정보를 생성합니다. 변수명과 줄 번호를 더 잘 연결할 수 있지만 실행의 논리적 결과가 달라지는 것은 아닙니다. 주석이나 개발자의 원래 의도까지 class 파일에 보존하는 옵션은 아닙니다. [근거: javap](https://docs.oracle.com/en/java/javase/21/docs/specs/man/javap.html)

## 2. 한 파일에서 여러 종류를 관찰하기

```java
// file: Lesson06.java
public class Lesson06 {
    static final class Box {
        private final int value;
        Box(int value) { this.value = value; }
        int read() { return value; }
    }
    static int first(int[] values) {
        return values[0];
    }
    public static void main(String[] args) {
        Box box = new Box(7);
        int[] values = {box.read(), 9};
        System.out.println(first(values));
        try {
            first(new int[0]);
        } catch (ArrayIndexOutOfBoundsException e) {
            System.out.println("empty");
        }
    }
}
```

```sh
javac --release 21 -g Lesson06.java
java Lesson06
javap -c -v -p Lesson06
javap -c -v -p 'Lesson06$Box'
```

출력은 `7`, `empty`입니다. 중첩 클래스가 별도 class 파일로 생성된 점을 확인하세요. 셸에서 `$`를 변수 확장으로 오해하지 않도록 작은따옴표를 붙였습니다. 외부 클래스만 열고 Box 생성자 코드가 없다고 판단하면 잘못된 파일을 보고 있는 것입니다.

## 3. new·dup·invokespecial을 함께 읽기

`new Box(7)`에서는 보통 `new`, `dup`, 숫자 상수 적재, `invokespecial ... <init>`가 보입니다. `new`는 객체를 위한 공간을 할당하고 아직 생성자 초기화가 끝나지 않은 참조를 만듭니다. `dup`는 그 참조를 복제합니다. 생성자 호출에 참조 하나가 소비되어도 생성된 객체를 이어서 저장할 참조가 필요하기 때문입니다.

생성자의 이름은 class 파일에서 `<init>`입니다. 생성자 호출은 일반적인 가상 메서드 디스패치와 다르게 다루므로 invokespecial을 사용합니다. “new 명령 하나가 객체 할당과 Java 생성자 본문 실행 전체를 끝낸다”라고 외우지 마세요. 검증 규칙은 초기화되지 않은 참조의 사용도 제한합니다.

## 4. 호출 명령을 목적별로 구분하기

| 명령 | 대표 상황 | 읽을 때 확인할 것 |
|---|---|---|
| invokestatic | static 메서드 | 수신 객체 없이 인자 전달 |
| invokevirtual | 일반 클래스 인스턴스 메서드 | 실제 수신 객체와 디스패치 |
| invokeinterface | 인터페이스를 통한 호출 | 인터페이스 메서드 참조 |
| invokespecial | 생성자, super 호출 등 특별 취급 | 생성·상위 호출의 의미 |
| invokedynamic | 런타임에 연결되는 호출 지점 | 부트스트랩 메서드·호출 지점 |

Java 소스의 모든 메서드 호출이 invokevirtual은 아닙니다. Java 21의 문자열 연결에는 invokedynamic이 보일 수 있습니다. 람다도 관련 메커니즘을 사용하지만 “invokedynamic은 람다 전용”이라고 할 수 없습니다. class 파일의 `BootstrapMethods` 속성을 함께 보아야 연결 방식을 추적할 수 있습니다.

이 표는 명령의 일반적 용도를 이해하기 위한 것입니다. 정확한 대상 선택과 접근 규칙은 각 명령과 JVMS 해석·메서드 선택 절을 확인해야 합니다. JIT는 해당 의미를 유지하면서 호출을 인라이닝할 수도 있습니다.

## 5. 배열 초기화를 명령으로 따라가기

`int[] values = {box.read(), 9}`는 배열을 만들고 각 원소를 채우는 동작입니다. `newarray int`는 기본형 int 배열을 만들고, `iastore`는 인덱스 위치에 int를 저장합니다. 배열 참조·인덱스·값이 필요하므로 단순히 값 하나만 스택에 있으면 되는 명령이 아닙니다.

`first`에는 보통 `aload_0`, `iconst_0`, `iaload`, `ireturn`이 있습니다. 배열 참조를 올리고 인덱스 0을 올린 뒤 원소를 읽습니다. 참조가 null이면 `NullPointerException`, 길이가 0이면 범위 오류가 발생합니다. 참조 배열은 `anewarray`, `aaload`, `aastore` 등 다른 명령을 사용합니다. 배열 자체도 객체이며 `length`는 별도 `arraylength` 명령으로 읽습니다.

## 6. 예외 표와 줄 번호를 읽는 순서

메서드의 `Exception table`은 보호되는 바이트코드 범위, 처리할 예외 타입, 이동할 핸들러 위치를 보여 줍니다. 범위의 끝은 포함하지 않는 규칙입니다. 예제에서 빈 배열 접근이 난 명령 위치가 어느 보호 범위에 속하는지 확인하세요.

`LineNumberTable`은 바이트코드 위치를 소스 줄과 연결합니다. 소스 한 줄에 여러 명령이 대응할 수 있고, 최적화·컴파일 방식에 따라 단순 일대일 관계가 아닙니다. StackMapTable은 검증용 타입 상태이고, 예외 표는 제어 흐름의 핸들러 정보이며, 둘은 서로 다른 역할입니다.

## 7. 장애 사례: 내가 보는 코드와 배포된 코드가 다르다

개발자 화면에서는 메서드가 있는데 서버는 `NoSuchMethodError`를 낸다고 가정합니다. 소스만 다시 읽으면 빌드 결과에 다른 버전의 라이브러리가 들어갔다는 사실을 놓칠 수 있습니다. 실제 배포된 JAR의 대상 class를 javap로 확인하고 메서드 descriptor를 비교하세요.

다른 classpath의 같은 이름 클래스를 보고 있지 않은지도 확인합니다. 필요하면 `javap -classpath`에 배포 JAR 경로를 명시하고 로드 로그로 실제 출처를 확인합니다. javap는 조사용 도구이지 실행 중인 JVM의 모든 JIT 기계 코드를 보여 주는 도구는 아닙니다. 바이트코드가 같아도 실행 프로파일에 따라 JIT 결과가 달라질 수 있습니다.

## 더 깊이: switch와 finally도 명령 목록으로 읽기

정수 switch에는 tableswitch나 lookupswitch가 나타날 수 있습니다. 전자는 인덱스 범위에 대응하는 점프 표, 후자는 키와 대상의 대응 목록을 생각하면 이해하기 쉽습니다. 키의 분포와 컴파일러 선택 등에 따라 결과가 다르며 소스에 switch가 있다는 사실만으로 항상 같은 명령이라고 단정하지 않습니다. 문자열 switch는 추가 비교 과정이 생길 수 있습니다.

finally는 JVM의 'finally 명령 하나'로 전부 실행되는 기능이 아닙니다. javac는 정상 경로와 예외 경로에 필요한 정리 동작과 예외 처리 표를 구성합니다. try-with-resources에서는 닫는 중 예외가 발생했을 때 원래 예외와 suppressed 예외를 다루는 코드도 생길 수 있습니다. 명령이 길어졌다고 자동으로 나쁜 코드가 된다는 뜻은 아닙니다.

javap로 읽을 때는 첫째 메서드 descriptor, 둘째 정상 경로의 입력과 결과, 셋째 분기 대상, 넷째 예외 표, 다섯째 상수 풀 순서로 좁혀 보세요. 처음부터 verbose 출력의 모든 #번호를 외우려 하면 실제 제어 흐름을 놓치기 쉽습니다.

<details class="question"><summary>심화 Q. 소스 한 줄에서 예외가 났다면 명령도 한 개만 조사하면 되나요?</summary><div class="answer"><p>한 줄에 객체 생성·메서드 호출·배열 접근 등이 함께 있을 수 있습니다. LineNumberTable은 명령과 소스의 대략적 연결을 제공하므로 같은 줄에 여러 실패 지점이 있을 수 있습니다.</p><p>긴 표현식을 나누어 재현하거나 예외 메시지·호출 스택·바이트코드 범위를 함께 확인해야 합니다. 줄 번호 하나를 실제 CPU 명령 하나로 해석하지 않습니다.</p></div></details>

## 8. 상세 면접 Q&A

<details class="question"><summary>Q1. -c와 -v의 차이는 무엇인가요?</summary><div class="answer"><p>-c는 메서드 바이트코드를 해석해 보여 줍니다. -v는 상수 풀, 클래스 버전, 속성 등 더 자세한 출력을 제공합니다. 먼저 -c로 흐름을 잡고 #번호나 descriptor의 의미가 필요할 때 -v로 넓히면 읽기 쉽습니다.</p></div></details>
<details class="question"><summary>Q2. new 뒤에 왜 dup가 나오나요?</summary><div class="answer"><p>생성자 호출에 사용할 참조와 호출 뒤 사용할 참조를 확보하는 전형적인 패턴입니다. 생성자 호출은 반환 타입이 void이므로 생성자가 객체 참조를 결과로 돌려주는 것으로 이해하면 안 됩니다. new가 만든 참조를 유지하는 흐름을 스택으로 추적해야 합니다.</p></div></details>
<details class="question"><summary>Q3. 배열 접근은 단순 메모리 읽기인가요?</summary><div class="answer"><p>Java 의미에서는 null·범위·타입 규칙을 만족해야 합니다. JVM은 최적화로 검사가 불필요하다고 증명하면 제거할 수 있지만 결과와 예외 의미는 지켜야 합니다. JIT가 검사 명령을 줄였다고 언어 규칙이 사라지는 것은 아닙니다.</p></div></details>
<details class="question"><summary>Q4. javap로 원래 변수명을 항상 알 수 있나요?</summary><div class="answer"><p>지역변수 디버그 정보가 존재해야 더 많은 이름을 볼 수 있습니다. 인덱스만 남아 있는 class에서 원래 이름·주석·소스 표현을 완전히 복구하는 것은 보장되지 않습니다. -g를 사용한 학습용 결과와 배포 결과를 구분합니다.</p></div></details>
<details class="question"><summary>Q5. invokevirtual이 보이면 실제 CPU도 매번 가상 호출하나요?</summary><div class="answer"><p>명령은 가상 호출의 의미를 표현하지만 JIT는 실제 타입 프로파일을 활용해 호출을 인라이닝하거나 직접적인 경로로 최적화할 수 있습니다. 의미와 최적화 구현이 다릅니다. 타입이 달라져 가정이 깨지면 다른 경로나 역최적화가 필요할 수 있습니다.</p></div></details>
<details class="question"><summary>Q6. NoSuchMethodError를 javap로 어떻게 조사하나요?</summary><div class="answer"><p>호출하는 쪽의 상수 풀에 기록된 메서드 이름·descriptor와, 실행 시 로드되는 대상 클래스의 메서드 목록을 비교합니다. 컴파일 때 기대한 버전과 실행 때의 버전이 다르면 불일치가 드러날 수 있습니다. 실제 로드 경로를 함께 확인해야 다른 파일을 검사하는 실수를 피할 수 있습니다.</p></div></details>

## 9. 공식 문서와 추가 실습

- [javap 도구 명세](https://docs.oracle.com/en/java/javase/21/docs/specs/man/javap.html).
- [JVMS §3.7~3.9 호출·인스턴스·배열](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-3.html#jvms-3.7).
- [JVMS §6 명령 정의](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-6.html).
- [JVMS §4.7.3 Code](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html#jvms-4.7.3).

`int[]`를 `String[]`으로 바꾸어 명령을 비교하고, box를 인터페이스 타입 변수로 받아 호출하면 어떤 명령을 사용하는지 실험하세요. 명령 전체를 암기하는 대신 입력·출력·예외 조건을 찾아 읽는 연습입니다.
