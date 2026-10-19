package study;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.*;

/** Finite lab: unique topic, explicit offsets, bounded waits. Java 21. */
public final class Lab {
    public static String bootstrap() {
        return System.getenv().getOrDefault("KAFKA_BOOTSTRAP", "localhost:9092");
    }
    public static Properties producerProperties() {
        Properties p = new Properties();
        p.put("bootstrap.servers", bootstrap());
        p.put("key.serializer", StringSerializer.class.getName());
        p.put("value.serializer", StringSerializer.class.getName());
        p.put("acks", "all");
        p.put("enable.idempotence", true);
        p.put("linger.ms", 5);
        p.put("request.timeout.ms", 10000);
        p.put("delivery.timeout.ms", 30000);
        return p;
    }
    public static Properties consumerProperties(String group) {
        Properties p = new Properties();
        p.put("bootstrap.servers", bootstrap());
        p.put("group.id", group);
        p.put("key.deserializer", StringDeserializer.class.getName());
        p.put("value.deserializer", StringDeserializer.class.getName());
        p.put("enable.auto.commit", false);
        p.put("auto.offset.reset", "earliest");
        p.put("max.poll.records", 10);
        return p;
    }
    public static void main(String[] args) throws Exception {
        String topic = "study.java." + UUID.randomUUID();
        String group = topic + ".group";
        try (Admin admin = Admin.create(Map.of("bootstrap.servers", bootstrap()))) {
            admin.createTopics(List.of(new NewTopic(topic, 1, (short) 1)))
                 .all().get(30, TimeUnit.SECONDS);
            try {
                try (KafkaProducer<String, String> producer = new KafkaProducer<>(producerProperties())) {
                    List<java.util.concurrent.Future<RecordMetadata>> sends = new ArrayList<>();
                    for (int i = 0; i < 10; i++) {
                        sends.add(producer.send(new ProducerRecord<>(topic, "order-A", "evt-" + i)));
                    }
                    for (var send : sends) {
                        var m = send.get(30, TimeUnit.SECONDS);
                        System.out.printf("sent partition=%d offset=%d%n", m.partition(), m.offset());
                    }
                }
                Set<String> seen = new HashSet<>();
                try (KafkaConsumer<String, String> c = new KafkaConsumer<>(consumerProperties(group))) {
                    c.subscribe(List.of(topic));
                    long deadline = System.nanoTime() + Duration.ofSeconds(40).toNanos();
                    while (seen.size() < 10 && System.nanoTime() < deadline) {
                        ConsumerRecords<String, String> batch = c.poll(Duration.ofMillis(500));
                        Map<TopicPartition, OffsetAndMetadata> done = new HashMap<>();
                        for (var r : batch) {
                            // In-memory observation only: not durable business deduplication.
                            seen.add(r.value());
                            System.out.printf("read %s-%d@%d value=%s%n", r.topic(), r.partition(), r.offset(), r.value());
                            done.put(new TopicPartition(r.topic(), r.partition()), new OffsetAndMetadata(r.offset() + 1));
                        }
                        if (!done.isEmpty()) c.commitSync(done);
                        for (var tp : c.assignment()) {
                            System.out.printf("position=%d committed=%s%n", c.position(tp), c.committed(Set.of(tp)).get(tp));
                        }
                    }
                }
                if (seen.size() != 10) throw new IllegalStateException("Expected 10 unique events, got " + seen.size());
                System.out.println("PASS: ten events observed and explicit next offsets committed");
            } finally {
                admin.deleteTopics(List.of(topic)).all().get(30, TimeUnit.SECONDS);
            }
        }
    }
}
