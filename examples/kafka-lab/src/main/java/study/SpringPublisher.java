package study;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import org.springframework.context.annotation.*;
import org.springframework.kafka.core.*;
import org.springframework.kafka.support.SendResult;

@Configuration
public class SpringPublisher {
    @Bean
    DefaultKafkaProducerFactory<String, String> producerFactory() {
        Map<String, Object> props = new HashMap<>();
        Lab.producerProperties().forEach((k, v) -> props.put(k.toString(), v));
        return new DefaultKafkaProducerFactory<>(props);
    }
    @Bean
    KafkaTemplate<String, String> kafkaTemplate(DefaultKafkaProducerFactory<String, String> factory) {
        return new KafkaTemplate<>(factory);
    }
    public static CompletableFuture<SendResult<String, String>> publish(
            KafkaTemplate<String, String> template, String eventId, String orderId) {
        if (eventId == null || eventId.isBlank() || orderId == null || orderId.isBlank())
            throw new IllegalArgumentException("Stable eventId and orderId required");
        // Plain demo payload: real projects use a versioned event schema.
        // Returning the future preserves the caller's ability to observe failure.
        return template.send("study.spring.input", orderId, eventId);
    }
}
