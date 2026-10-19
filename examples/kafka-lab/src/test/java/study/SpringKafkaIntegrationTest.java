package study;
import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.common.TopicPartition;
import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.kafka.core.KafkaTemplate;

/** Opt-in only: requires an isolated single-broker test cluster. */
class SpringKafkaIntegrationTest {
    @Test void springPublishesConsumesAndAcknowledgesOnRealKafka() throws Exception {
        assumeTrue(Boolean.getBoolean("kafka.it"), "Enable only against a dedicated lab broker");
        String topic = "study.spring.input";
        try (Admin admin = Admin.create(Map.of("bootstrap.servers", Lab.bootstrap()))) {
            // Fail if topic already exists: never delete someone else's lab data.
            admin.createTopics(List.of(new NewTopic(topic, 1, (short)1)))
                 .all().get(30, TimeUnit.SECONDS);
            try {
                try (var ctx = new AnnotationConfigApplicationContext(SpringConsumer.class, SpringPublisher.class)) {
                    @SuppressWarnings("unchecked")
                    KafkaTemplate<String, String> template = ctx.getBean(KafkaTemplate.class);
                    SpringPublisher.publish(template, "spring-event-1", "A").get(30, TimeUnit.SECONDS);
                    SpringPublisher.publish(template, "spring-event-2", "A").get(30, TimeUnit.SECONDS);
                    long deadline = System.nanoTime() + Duration.ofSeconds(40).toNanos();
                    long committed = -1;
                    while (System.nanoTime() < deadline && committed < 2) {
                        try {
                            var offsets = admin.listConsumerGroupOffsets("study.spring")
                                    .partitionsToOffsetAndMetadata().get(10, TimeUnit.SECONDS);
                            var offset = offsets.get(new TopicPartition(topic, 0));
                            if (offset != null) committed = offset.offset();
                        } catch (java.util.concurrent.ExecutionException pending) {
                            if (!(pending.getCause() instanceof org.apache.kafka.common.errors.GroupIdNotFoundException))
                                throw pending;
                        }
                        if (committed < 2) Thread.sleep(100);
                    }
                    assertEquals(2, committed, "Listener must acknowledge both events");
                }
            } finally {
                admin.deleteTopics(List.of(topic)).all().get(30, TimeUnit.SECONDS);
            }
        }
    }
}
