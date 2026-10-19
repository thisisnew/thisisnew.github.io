{"n":8,"title":"AWS 보안 서비스 지도: IAM·KMS·Secrets·WAF의 서로 다른 역할","desc":"인증·인가·암호화·비밀 관리·탐지·방어를 한 요청의 흐름으로 연결하기"}

## 1. 출입증, 열쇠, CCTV를 혼동하지 않기

출입증은 누구인지 확인하고 어느 방에 들어갈 수 있는지 결정합니다. 금고의 열쇠는 내용을 읽게 해 주고, CCTV는 일어난 일을 기록하며, 경비원은 의심스러운 행동을 탐지합니다. IAM·KMS·CloudTrail·GuardDuty도 목적이 다릅니다. 암호화했다고 권한이 올바른 것은 아니고, 공격을 탐지한다고 취약한 코드를 고치는 것도 아닙니다.

먼저 사용자 요청을 생각해 봅시다. 고객 로그인은 Cognito 같은 고객 신원 서비스가 맡을 수 있고, 앱이 AWS API를 호출하는 권한은 IAM role로 부여합니다. DB 비밀번호는 Secrets Manager에서 관리하고, 저장 데이터 암호화에는 KMS를 활용합니다. 웹 공격의 일부는 WAF로 걸러내며, 감사와 위협 탐지는 별도 서비스를 연결합니다.

## 2. IAM: 인증과 인가를 분리하기

인증은 호출자가 누구인지, 인가는 그 호출이 허용되는지 판단하는 과정입니다. IAM user는 장기 신원과 자격 증명을 가질 수 있고, role은 신뢰 정책에 따라 주체가 맡아 임시 자격 증명으로 행동하는 역할입니다. 애플리케이션에 access key를 하드코딩하는 대신 EC2 instance profile·ECS task role·Lambda execution role 등을 이용하면 자격 증명의 배포와 교체 부담을 줄일 수 있습니다.

정책은 Action·Resource·Condition·Effect 등으로 허용과 거부를 표현합니다. 기본은 암묵적 거부이고 필요한 허용이 있어야 합니다. 적용 가능한 명시적 Deny는 Allow보다 우선합니다. identity policy·resource policy·permissions boundary·session policy·SCP는 모두 같은 종류의 허용장이 아닙니다. boundary와 SCP는 권한의 최대 범위를 제한하며 자체로 앱에 권한을 주지 않습니다. cross-account와 resource policy의 주체 유형에 따라 평가가 달라지므로 복잡한 경우 단순 합집합 공식 하나로 결론 내리지 않습니다.

## 3. KMS: 데이터를 암호화하는 키의 수명주기

큰 데이터를 모두 KMS API에 직접 보내 암호화하는 방식만 있는 것은 아닙니다. envelope encryption에서는 데이터 키로 본문을 암호화하고, 그 데이터 키를 KMS key로 보호합니다. 저장할 것은 암호문과 암호화된 데이터 키이며 평문 키는 필요한 동안만 사용합니다. 복호화할 때 KMS 권한과 키 정책이 맞아야 데이터 키를 얻고 본문을 읽을 수 있습니다.

S3 읽기 권한이 있어도 SSE-KMS 객체의 키를 사용할 수 없으면 읽기가 실패할 수 있습니다. 반대로 키 권한이 있다고 버킷 접근 권한까지 생기는 것은 아닙니다. 키 교체는 새 암호화에 사용할 키 재료를 바꾸는 과정이며 기존 데이터 전체를 즉시 다시 암호화하는 것과 구분합니다. 키 삭제는 해당 키로 보호한 데이터를 되살릴 수 없게 만들 수 있으므로 데이터 보존과 복구 계획에 포함해야 합니다.

CloudHSM은 전용 HSM과 더 직접적인 암호화 장치 제어 요구에서 검토하는 선택지입니다. KMS와 동일한 운영 책임·통합 편의성을 제공하는 대체 이름이 아닙니다. ACM은 인증서 발급·관리·지원 서비스 연동, Secrets Manager는 DB 비밀번호·API 비밀 등 secret 저장과 교체라는 역할입니다.

## 4. Secrets Manager: 저장보다 교체가 어렵다

비밀번호를 안전한 곳에 넣어도 앱이 로그에 출력하거나 메모리에 무기한 캐시하면 문제가 남습니다. secret 교체는 새 값을 만들고 대상 시스템에 적용하고 검증하며 앱이 새 값을 쓰도록 만드는 과정입니다. DB 비밀번호만 바꾸고 연결 풀이나 캐시를 고려하지 않으면 배포 없이도 접속 장애가 생깁니다. 새 secret 조회 권한과 KMS 복호화 권한, 회전 작업의 네트워크 접근을 함께 확인합니다.

직원 로그인을 중앙화하는 IAM Identity Center, Microsoft 디렉터리 통합을 돕는 Directory Service, 앱 내부 권한 정책을 다루는 Verified Permissions도 IAM과 목적이 겹쳐 보이지만 책임 범위가 다릅니다. 고객의 “자기 주문만 조회” 권한은 AWS API role 하나로 저절로 구현되지 않습니다. 애플리케이션이 리소스 소유자를 검증해야 합니다.

## 5. 방어와 탐지 서비스 비교

| 서비스 | 대표 질문 | 대신하지 않는 것 |
|---|---|---|
| WAF | 웹 요청에서 규칙에 맞는 공격·남용을 거를까 | 업무 권한 검사·코드 수정 |
| Shield | DDoS 대응을 어떻게 할까 | SQL 인젝션 수정·로그인 권한 |
| Network Firewall | VPC 트래픽을 어떤 규칙으로 검사할까 | 모든 애플리케이션 인가 |
| GuardDuty | 위협으로 의심되는 활동이 있나 | 모든 리소스의 패치 |
| Inspector | 지원 워크로드의 취약점은 무엇인가 | 모든 비즈니스 로직 보안 검사 |
| Macie | S3의 민감 정보 노출 위험은 무엇인가 | 모든 저장소의 자동 보안 완성 |
| Security Hub CSPM | 보안 상태와 결과를 어떻게 모을까 | 조사·대응 책임 자체 |
| Detective | 관련 활동을 어떻게 조사할까 | 자동으로 모든 원인 제거 |
| Security Lake | 보안 데이터를 어떻게 통합 저장할까 | 별도 분석 없이 모든 탐지 |

WAF 규칙은 정상 요청을 차단할 수 있으므로 관찰·카운트 모드와 샘플링으로 영향을 확인하고 적용합니다. CAPTCHA도 자동화 남용 대응 도구이지 사용자의 실제 업무 권한을 증명하는 절차가 아닙니다. Firewall Manager는 여러 계정의 방어 정책을 중앙 관리하는 목적입니다.

## 6. 증거·공유·컴플라이언스

Artifact는 AWS 규정 준수 문서 접근, Audit Manager는 감사 증거 수집과 평가 지원, Resource Access Manager는 지원 리소스의 안전한 공유와 관련됩니다. Audit Manager는 현재 공식 목록에서 신규 고객을 받지 않는 유지보수 단계로 안내됩니다. 기존 소개의 역할과 새 고객의 도입 가능성을 구분합니다. [유지보수 목록](https://docs.aws.amazon.com/general/latest/gr/maintenance_services.html) AWS가 인증을 보유했다는 이유만으로 고객의 애플리케이션이 자동으로 모든 규정을 준수하는 것은 아닙니다. 데이터 분류·보존·접근 검토·증거 수집은 자신의 워크로드 조건으로 확인해야 합니다. 공용·계정 간 공유는 IAM Access Analyzer 등으로 의도한 범위인지 점검합니다.

## 7. 가상 장애: 버킷 권한은 있는데 파일이 안 읽힌다

운영 앱에 S3 GetObject를 허용했는데 AccessDenied가 발생했습니다. 객체는 고객 관리형 KMS key로 암호화되어 있었고 앱 role은 해당 키를 사용할 수 없었습니다. 확인 순서는 호출 주체, 버킷·객체 ARN, 정책의 Deny와 조건, endpoint policy, KMS key policy와 필요한 권한입니다. 문제를 빨리 해결하려고 `Action: *`, `Resource: *`를 붙이면 원인을 숨기고 피해 범위를 키울 수 있습니다.

종이 실습으로 “고객→앱→S3→KMS” 경로마다 어떤 신원이 어떤 권한을 쓰는지 적어 보세요. 고객 로그인 토큰과 앱의 AWS 임시 자격 증명을 같은 것으로 적었다면 인증 경계부터 다시 정리해야 합니다.

## 8. 상세 면접 Q&A

<details><summary>Q. IAM role이 있으면 비밀번호가 전혀 필요 없나요?</summary><p>AWS API 접근에서 장기 access key를 줄이는 데 유용하지만 모든 외부 시스템이 IAM 인증을 지원하는 것은 아닙니다. DB나 외부 SaaS가 별도 secret을 요구할 수 있습니다. role로 Secrets Manager에 접근해 secret을 가져오는 것처럼 두 기능을 결합하기도 합니다.</p></details>
<details><summary>Q. KMS와 Secrets Manager의 차이는 무엇인가요?</summary><p>KMS는 암호화 키 관리와 암호 연산·서비스 통합을 제공하고, Secrets Manager는 애플리케이션이 사용할 비밀 값과 회전 수명주기를 관리합니다. Secrets Manager가 저장 데이터를 보호하는 데 KMS를 사용할 수 있습니다. 열쇠 관리와 비밀번호 보관·교체는 연결되지만 같은 책임은 아닙니다.</p></details>
<details><summary>Q. WAF를 설치하면 SQL 인젝션을 해결한 건가요?</summary><p>일부 공격 패턴을 줄이는 방어 계층을 추가한 것입니다. 파라미터 바인딩·입력 처리·DB 최소 권한 등 코드와 데이터 접근 설계는 여전히 필요합니다. 우회 가능한 패턴이나 업무 로직 취약점을 WAF 하나에 맡기지 않습니다.</p></details>
<details><summary>Q. 암호화된 백업이면 랜섬웨어에도 안전한가요?</summary><p>읽기 보호와 삭제·변조 방지는 다릅니다. 공격자가 백업 삭제나 키 삭제 권한을 얻으면 암호화만으로 복구를 보장할 수 없습니다. 별도 계정·제한된 권한·보존 잠금·복구 테스트를 조합해 공격과 실수의 범위를 줄입니다.</p></details>

## 공식 문서

- [IAM 정책 평가](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)
- [KMS 개념과 envelope encryption](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)
- [Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
- [AWS 보안 원칙](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
