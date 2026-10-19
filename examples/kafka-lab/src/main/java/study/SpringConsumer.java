package study;
import java.util.Map;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.context.annotation.*;
import org.springframework.kafka.annotation.*;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.listener.ContainerProperties;
import org.springframework.kafka.listener.CommonContainerStoppingErrorHandler;
import org.springframework.kafka.support.Acknowledgment;

/** Plain Spring configuration; Boot is intentionally not needed for this lab. */
@Configuration
@EnableKafka
public class SpringConsumer {
    @Bean
    ConcurrentKafkaListenerContainerFactory<String, String> kafkaListenerContainerFactory() {
        var f = new ConcurrentKafkaListenerContainerFactory<String, String>();
        Map<String, Object> props = new java.util.HashMap<>();
        Lab.consumerProperties("study.spring").forEach((k, v) -> props.put(k.toString(), v));
        f.setConsumerFactory(new DefaultKafkaConsumerFactory<>(props));
        f.getContainerProperties().setAckMode(ContainerProperties.AckMode.MANUAL_IMMEDIATE);
        // Educational fail-stop: do not silently recover/discard after retries.
        f.setCommonErrorHandler(new CommonContainerStoppingErrorHandler());
        return f;
    }
    @KafkaListener(topics = "study.spring.input", groupId = "study.spring")
    public void listen(ConsumerRecord<String, String> record, Acknowledgment ack) {
        if (record.value() == null) throw new IllegalArgumentException("Null payload in this lab");
        System.out.printf("processed %s-%d@%d value=%s%n", record.topic(), record.partition(), record.offset(), record.value());
        // Replace with a durable transactional service before using for real work.
        ack.acknowledge();
    }
    public static void main(String[] args) {
        var ctx = new AnnotationConfigApplicationContext(SpringConsumer.class);
        ctx.registerShutdownHook();
    }
}
