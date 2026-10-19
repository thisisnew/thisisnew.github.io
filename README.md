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
