package study;

import static org.junit.jupiter.api.Assertions.assertTrue;
import java.util.List;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.junit.jupiter.api.Test;

class ProducerConfigurationTest {
    @Test void deliveryBudgetIncludesLingerAndRequestWithResolvedDefaults() {
        for (var properties : List.of(Lab.producerProperties(), TopicExamples.durableProducer())) {
            var config = new ProducerConfig(properties);
            long required = config.getLong(ProducerConfig.LINGER_MS_CONFIG)
                    + config.getInt(ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG);
            assertTrue(config.getInt(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG) >= required,
                    "KafkaProducer requires delivery.timeout.ms >= linger.ms + request.timeout.ms");
        }
    }
}
