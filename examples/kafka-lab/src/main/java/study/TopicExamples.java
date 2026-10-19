package study;

import java.net.URI;
import java.net.http.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.*;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.*;
import org.apache.kafka.common.acl.*;
import org.apache.kafka.common.config.*;
import org.apache.kafka.common.config.provider.FileConfigProvider;
import org.apache.kafka.common.serialization.*;
import org.apache.kafka.streams.*;
import org.apache.kafka.streams.kstream.*;
import org.apache.kafka.streams.processor.api.*;

/** Topic-specific teaching fragments. Methods are NOT automatically executed.
 * Admin mutations need dedicated lab resources; security uses dummy inputs.
 * Marker comments are used to insert the compiled fragments into each lesson. */
public final class TopicExamples {
// LESSON 01 BEGIN
    static ProducerRecord<String, String> event(String orderId, String eventId) {
        // Stable business identity and routing key have different roles.
        var r = new ProducerRecord<String, String>("study.intro", orderId, eventId);
        r.headers().add("schemaVersion", "1".getBytes(StandardCharsets.UTF_8));
        return r;
    }
// LESSON 01 END
// LESSON 02 BEGIN
    static Properties batching() {
        var p = Lab.producerProperties();
        p.put("linger.ms", 5);         // Small intentional batching delay, not total latency.
        p.put("batch.size", 32768);    // Bytes per partition batch, not record count.
        p.put("compression.type", "lz4");
        return p;
    }
// LESSON 02 END
// LESSON 03 BEGIN
    static void logDirectories(Admin admin, int brokerId) throws Exception {
        var dirs = admin.describeLogDirs(List.of(brokerId)).allDescriptions().get();
        dirs.forEach((id, byPath) -> byPath.forEach((path, description) -> {
            System.out.println("broker=" + id + " path=" + path + " error=" + description.error());
            description.replicaInfos().forEach((tp, info) ->
                System.out.println(tp + " bytes=" + info.size() + " offsetLag=" + info.offsetLag()));
        }));
    }
// LESSON 03 END
// LESSON 04 BEGIN
    static Properties durableProducer() {
        var p = Lab.producerProperties();
        p.put("acks", "all");
        p.put("enable.idempotence", true);
        p.put("max.in.flight.requests.per.connection", 5);
        p.put("delivery.timeout.ms", 30000);
        // Topic RF/minISR and failure domains must be configured separately.
        return p;
    }
// LESSON 04 END
// LESSON 05 BEGIN
    static void positions(KafkaConsumer<String, String> c) {
        // Call on the consumer thread after assignment, not from a worker pool.
        var committed = c.committed(c.assignment());
        for (var tp : c.assignment()) {
            System.out.println(tp + " position=" + c.position(tp)
                    + " committed=" + committed.get(tp));
        }
    }
// LESSON 05 END
// LESSON 06 BEGIN
    static NewTopic replicatedTopic() {
        // Requires at least 3 brokers. Not runnable on the RF=1 introductory lab.
        return new NewTopic("study.replicated", 3, (short)3).configs(Map.of(
                "min.insync.replicas", "2", "cleanup.policy", "delete",
                "retention.ms", "604800000", "retention.bytes", "1073741824"));
        // retention.bytes is per partition; replicas multiply physical storage.
    }
// LESSON 06 END
// LESSON 07 BEGIN
    static void snapshotOffsets(Admin admin, String group) throws Exception {
        // Read-only snapshot before planning any reset. This does not reset data.
        var offsets = admin.listConsumerGroupOffsets(group)
                           .partitionsToOffsetAndMetadata().get();
        offsets.forEach((tp, next) -> System.out.println(group + " " + tp + " next=" + next));
    }
// LESSON 07 END
// LESSON 08 BEGIN
    static Properties transactionalProducer(String stableUniqueId) {
        var p = Lab.producerProperties();
        p.put("transactional.id", stableUniqueId);
        // Different live instances must not accidentally share this identity.
        // initTransactions/begin/commit/abort and fatal-error handling are still required.
        return p;
    }
// LESSON 08 END
// LESSON 09 BEGIN
    static void consumerMetrics(KafkaConsumer<String, String> c) {
        c.metrics().forEach((name, metric) -> {
            if (name.name().contains("lag") || name.name().contains("rate"))
                System.out.println(name.group() + "/" + name.name()
                        + " " + name.tags() + "=" + metric.metricValue());
        });
        // Client fetch metrics and group committed lag are different observations.
    }
// LESSON 09 END
// LESSON 10 BEGIN
    static double replicatedGigabytes(double perSecond, double storedBytes,
                                      double days, int replicas) {
        if (perSecond < 0 || storedBytes < 0 || days < 0 || replicas < 1)
            throw new IllegalArgumentException("Invalid capacity input");
        return perSecond * storedBytes * days * 86400 * replicas / 1_000_000_000d;
        // 1000/s * 500B * 7 days * RF3 = 907.2 GB; overhead and headroom extra.
    }
// LESSON 10 END
// LESSON 11 BEGIN
    static void supportedFeatures(Admin admin) throws Exception {
        var features = admin.describeFeatures().featureMetadata().get();
        System.out.println("supported=" + features.supportedFeatures());
        System.out.println("finalized=" + features.finalizedFeatures());
        // Inspect first. This code never finalizes or downgrades feature versions.
    }
// LESSON 11 END
// LESSON 12 BEGIN
    static void apiRoles(Admin admin) throws Exception {
        // Admin inspects resources; it is not a business-record consumer.
        System.out.println("cluster=" + admin.describeCluster().clusterId().get());
        System.out.println("topics=" + admin.listTopics().names().get());
        // ProducerRecord -> Producer; poll -> Consumer; Topology -> Streams.
        // Share Consumer and Connect are separate APIs/lifecycles.
    }
// LESSON 12 END
// LESSON 13 BEGIN
    static void advertisedAddresses(Admin admin) throws Exception {
        for (var node : admin.describeCluster().nodes().get()) {
            System.out.println(node.id() + " " + node.host() + ":" + node.port());
        }
        // Test each returned address from the APP network, including TLS SANs.
        // Bootstrap is discovery; it is not a permanent routing proxy.
    }
// LESSON 13 END
// LESSON 14 BEGIN
    static Map<String, String> distributedConnectWorker() {
        return Map.of("group.id", "study-connect", "bootstrap.servers", Lab.bootstrap(),
                "config.storage.topic", "study-connect-config",
                "offset.storage.topic", "study-connect-offset",
                "status.storage.topic", "study-connect-status");
        // Worker properties, NOT an application KafkaConsumer configuration.
        // Converters, replication, compaction, plugins and security are additional.
    }
// LESSON 14 END
// LESSON 15 BEGIN
    static Properties streamsConfiguration() {
        Properties p = new Properties();
        p.put("application.id", "study-stateful-v1");
        p.put("bootstrap.servers", Lab.bootstrap());
        p.put("processing.guarantee", "exactly_once_v2");
        p.put("num.stream.threads", 2);
        // EOS broker internal-topic replication requirements need a suitable cluster.
        // External DB/HTTP side effects are not automatically in this transaction.
        return p;
    }
// LESSON 15 END
// LESSON 16 BEGIN
    static void describeTopicsIndividually(Admin admin, List<String> topics) {
        admin.describeTopics(topics).topicNameValues().forEach((name, future) -> {
            future.whenComplete((description, failure) -> {
                if (failure != null) System.err.println(name + " failed: " + failure.getClass().getSimpleName());
                else System.out.println(name + " partitions=" + description.partitions().size());
            });
        });
        // Keep Admin open until futures finish. A single failure is not a global rollback.
    }
// LESSON 16 END
// LESSON 17 BEGIN
    static void inspectFileProviderKeys(String path) throws Exception {
        try (var provider = new FileConfigProvider()) {
            provider.configure(Map.of());
            var result = provider.get(path, Set.of("username"));
            System.out.println("available keys=" + result.data().keySet());
            // Do not print secret values. File changes do not prove live reauthentication.
        }
    }
// LESSON 17 END
// LESSON 18 BEGIN
    static Optional<byte[]> tryFrame(ByteBuffer input) {
        input.order(ByteOrder.BIG_ENDIAN);
        if (input.remaining() < Integer.BYTES) return Optional.empty();
        input.mark();
        int length = input.getInt();
        if (length < 0 || length > 1024 * 1024)
            throw new IllegalArgumentException("Invalid lab frame length");
        if (input.remaining() < length) { input.reset(); return Optional.empty(); }
        byte[] body = new byte[length]; input.get(body);
        return Optional.of(body); // Length framing only: not a complete Kafka decoder.
    }
// LESSON 18 END
// LESSON 19 BEGIN
    static Properties fetchLimits(String group) {
        var p = Lab.consumerProperties(group);
        p.put("max.poll.records", 100);
        p.put("max.partition.fetch.bytes", 1_048_576);
        p.put("fetch.max.bytes", 5_242_880);
        p.put("isolation.level", "read_committed");
        // Record count, fetch bytes and decompressed object memory are different limits.
        return p;
    }
// LESSON 19 END
// LESSON 20 BEGIN
    static Properties consumerProtocol(String group, String protocol) {
        var p = Lab.consumerProperties(group);
        p.put("group.protocol", protocol); // "classic" or "consumer", not "streams".
        if (protocol.equals("classic")) p.put("heartbeat.interval.ms", 3000);
        // consumer protocol uses broker-side heartbeat/session controls.
        // Rolling protocol migration also has assignor/metadata restrictions.
        return p;
    }
// LESSON 20 END
// LESSON 21 BEGIN
    static void setLabRetention(Admin admin) throws Exception {
        var resource = new ConfigResource(ConfigResource.Type.TOPIC, "study.admin");
        var change = new AlterConfigOp(new ConfigEntry("retention.ms", "86400000"),
                                       AlterConfigOp.OpType.SET);
        admin.incrementalAlterConfigs(Map.of(resource, List.of(change))).all().get();
        System.out.println(admin.describeConfigs(List.of(resource)).all().get());
        // Save original override/source first; DELETE and SET are different operations.
    }
// LESSON 21 END
// LESSON 22 BEGIN
    static void protocolProbe(Admin admin) throws Exception {
        System.out.println(admin.describeCluster().clusterId().get());
        System.out.println(admin.describeFeatures().featureMetadata().get().supportedFeatures());
        // This is not the full ApiVersions matrix. Use kafka-broker-api-versions.sh too.
        // Probe the actual transaction/group/security features separately.
    }
// LESSON 22 END
// LESSON 23 BEGIN
    static void compareClusterIdentity(Admin source, Admin target) throws Exception {
        var a = source.describeCluster().clusterId().get();
        var b = target.describeCluster().clusterId().get();
        if (Objects.equals(a, b)) throw new IllegalArgumentException("Expected separate DR clusters");
        System.out.println("source=" + a + " target=" + b);
        // Different clusters have different offset coordinate systems.
        // This check does not translate offsets; MM2 checkpoints must be validated separately.
    }
// LESSON 23 END
// LESSON 24 BEGIN
    static Properties tlsClient(String truststore) {
        var p = Lab.producerProperties();
        p.put("security.protocol", "SSL");
        p.put("ssl.truststore.location", truststore);
        p.put("ssl.endpoint.identification.algorithm", "https");
        // Inject password privately if required. mTLS additionally needs client key/cert.
        // Keep hostname verification enabled and match advertised names to SANs.
        return p;
    }
// LESSON 24 END
// LESSON 25 BEGIN
    static Properties saslClient(String jaasFromSecretStore) {
        var p = Lab.producerProperties();
        p.put("security.protocol", "SASL_SSL");
        p.put("sasl.mechanism", "SCRAM-SHA-512");
        p.put("sasl.jaas.config", jaasFromSecretStore);
        // Add the correct trust configuration; never log this Properties object.
        // Successful authentication still does not grant Topic/Group permissions.
        return p;
    }
// LESSON 25 END
// LESSON 26 BEGIN
    static void inspectAcls(Admin admin) throws Exception {
        var rules = admin.describeAcls(AclBindingFilter.ANY).values().get();
        for (var rule : rules) {
            System.out.println(rule.pattern().resourceType() + " " + rule.pattern().name()
                + " " + rule.pattern().patternType() + " " + rule.entry().principal()
                + " " + rule.entry().operation() + " " + rule.entry().permissionType());
        }
        // Read-only; requires appropriate authorization. Do not fix by granting "*".
    }
// LESSON 26 END
// LESSON 27 BEGIN
    static HttpResponse<String> connectorStatus(String name) throws Exception {
        if (!name.matches("[A-Za-z0-9_-]+")) throw new IllegalArgumentException("Invalid lab connector name");
        var request = HttpRequest.newBuilder(URI.create("http://localhost:8083/connectors/" + name + "/status"))
                .timeout(Duration.ofSeconds(10)).GET().build();
        return HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build()
                .send(request, HttpResponse.BodyHandlers.ofString());
        // Check HTTP status AND connector/tasks[].state. Do not blindly print trace secrets.
    }
// LESSON 27 END
// LESSON 28 BEGIN
    static org.apache.kafka.connect.source.SourceRecord sourceRecord(long lastReadId, String value) {
        return new org.apache.kafka.connect.source.SourceRecord(
            Map.of("table", "study_source"), Map.of("id", lastReadId),
            "study.connect", org.apache.kafka.connect.data.Schema.STRING_SCHEMA, "row-" + lastReadId,
            org.apache.kafka.connect.data.Schema.STRING_SCHEMA, value);
        // Source partition/offset describes the EXTERNAL cursor, not Kafka log offset.
        // Real source queries must handle commit order, restart and late data safely.
    }
// LESSON 28 END
// LESSON 29 BEGIN
    static void requireConnectStatus200(HttpResponse<String> status) {
        if (status.statusCode() != 200)
            throw new IllegalStateException("Connect REST status=" + status.statusCode());
        // Parse JSON next. HTTP 200 can still contain FAILED tasks.
        // RUNNING without recent output is not proof of business progress.
        // DLQ is a recovery queue; count it separately from successful sink writes.
    }
// LESSON 29 END
// LESSON 30 BEGIN
    static Topology tableView() {
        var b = new StreamsBuilder();
        b.table("study.state", Consumed.with(Serdes.String(), Serdes.String()))
         .toStream().to("study.state.updates", Produced.with(Serdes.String(), Serdes.String()));
        // Same key is an upsert; null value means deletion. Caching may coalesce updates.
        return b.build();
    }
// LESSON 30 END
// LESSON 31 BEGIN
    static void lifecycle(KafkaStreams streams) {
        streams.setStateListener((next, old) -> System.out.println(old + " -> " + next));
        Runtime.getRuntime().addShutdownHook(new Thread(() -> streams.close(Duration.ofSeconds(15))));
        streams.start();
        // Do not equate start() returning with restored state stores being query-ready.
    }
// LESSON 31 END
// LESSON 32 BEGIN
    static Topology windowedCount() {
        var b = new StreamsBuilder();
        b.stream("study.window.input", Consumed.with(Serdes.String(), Serdes.String()))
         .filter((k,v) -> k != null && v != null)
         .groupByKey(Grouped.with(Serdes.String(), Serdes.String()))
         .windowedBy(TimeWindows.ofSizeAndGrace(Duration.ofMinutes(1), Duration.ofSeconds(10)))
         .count().toStream()
         .to("study.window.output", Produced.with(
             WindowedSerdes.timeWindowedSerdeFrom(String.class, 60_000), Serdes.Long()));
        return b.build(); // Stream time advances from data, not a wall-clock cron.
    }
// LESSON 32 END
// LESSON 33 BEGIN
    static Topology processorExample() {
        var b = new StreamsBuilder();
        b.stream("study.processor.input", Consumed.with(Serdes.String(), Serdes.String()))
         .process(() -> new ContextualProcessor<String,String,String,String>() {
             @Override public void process(org.apache.kafka.streams.processor.api.Record<String,String> r) {
                 if (r.value() != null) context().forward(r.withValue(r.value().toUpperCase(Locale.ROOT)));
             }
         }).to("study.processor.output", Produced.with(Serdes.String(), Serdes.String()));
        return b.build(); // Supplier creates an independent processor per task.
    }
// LESSON 33 END
// LESSON 34 BEGIN
    static Long localCount(KafkaStreams streams, String key) {
        var store = streams.store(StoreQueryParameters.fromNameAndType("event-counts",
                org.apache.kafka.streams.state.QueryableStoreTypes.<String,Long>timestampedKeyValueStore()));
        var v = store.get(key);
        return v == null ? null : v.value();
        // Local store only. Remote key routing/RPC and restore readiness are separate.
    }
// LESSON 34 END
// LESSON 35 BEGIN
    static Properties newStreamsProtocol() {
        Properties p = new Properties();
        p.put("application.id", "study-streams-protocol-v1");
        p.put("bootstrap.servers", Lab.bootstrap());
        p.put("group.protocol", "streams");
        // Requires supported broker/client + streams.version feature.
        // 4.3 restrictions: no online migration/static membership/pattern subscription.
        return p;
    }
// LESSON 35 END
}
