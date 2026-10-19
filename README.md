# thisisnew engineering blog

Static GitHub Pages blog with the original PIXEL QUEST skin.
Kafka lessons remain at `posts/kafka-study-01.html` through `kafka-study-35.html`.

The 2026-10-19 revision uses Apache Kafka 4.3 documentation and pins runnable
Kafka examples to 4.3.1 / Java 21. Each lesson contains topic-specific flow,
analogy, internals, operational decisions, constructed failure scenarios,
experiments, executable Java/Spring source, and expandable interview answers.
Common standalone background is explicitly labelled and separately audited.

- `learning/verification.html`: verification scope and results
- `learning/source-manifest.json`: 83 retrieved official pages and SHA-256 hashes
- `learning/lesson-audit.json`: per-lesson source and content metadata
- `learning/site-checks.json`: static links, anchors, sections and Q&A checks
- `learning/browser-checks.json`: desktop/mobile and answer controls
- `examples/kafka-lab`: pinned Maven project, tests and isolated real-broker lab

```bash
python tools/verify_site.py
cd examples/kafka-lab
mvn test
# Separate isolated broker, not a production cluster:
# docker run --rm --name kafka-study -p 9092:9092 apache/kafka:4.3.1
mvn exec:java -Dexec.mainClass=study.Lab
mvn test -Dkafka.it=true
```

The opt-in Spring integration test creates `study.spring.input` and deliberately
fails if it already exists. It deletes only the topic it successfully creates.
The JDBC sample compiles but MySQL transaction/concurrency testing is separate.
Single-broker smoke tests do not prove RF=3 durability, KRaft quorum failure,
TLS/SASL/ACL, tiered storage plugins or MM2 disaster recovery.

`tools/revise_kafka.py` assembles the labelled additions from authored notes,
source files and common modules. Re-running it replaces its own blocks, rather
than duplicating them. Existing authored sections are preserved; common generic
filler is removed. Source manifest and verification records are separate records
of retrieval/testing, not inferred from text length.

GitHub Actions checks static content, compiles examples, tests topology and offset
boundaries, runs Kafka 4.3.1 + Spring integration, then deploys static pages only.

## JVM 학습 연재

- 학습 안내: https://thisisnew.github.io/posts/jvm-study-00.html
- 01~16편: Java SE 21 사양과 HotSpot JDK 21 구현을 구분한 한국어 해설
- 원고: `content/jvm/*.md` (첫 문단은 JSON 메타데이터)
- 실습: `examples/jvm/01` ~ `16`, 외부 의존성 없는 Java 예제
- `npm ci && npm run build:jvm`: HTML·실습 코드·메인 목록 재생성
- `python3 scripts/check-jvm.py`: 페이지·목차·내부 링크·문답 검사
- `JAVA_HOME=/path/to/jdk-21 python3 scripts/check-jvm-java.py`: 실제 Java 21 출력과 바이트코드 검사
- 브라우저 검증: Playwright가 설치된 환경에서 `node scripts/check-jvm-browser.cjs`; 필요하면 `CHROME_PATH`로 실행 파일 지정. 자체 로컬 서버에서 모바일 390px·데스크톱 1440px, 문답 펼침·접기·키보드 조작·검색·가로 넘침을 검사합니다.
- 검증 결과: `learning/jvm-*-checks.json`. GC 타이밍처럼 결정적이지 않은 결과는 고정값으로 검증하지 않습니다.

기존 픽셀 스킨 파일은 공통으로 참조하며 JVM 전용 보조 스타일은 `assets/jvm-study.css`에 있습니다. GitHub Pages에는 생성된 HTML을 배포하므로 방문자의 브라우저에서 Markdown 변환 도구가 필요하지 않습니다.
