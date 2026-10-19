package study;
import static org.junit.jupiter.api.Assertions.*;
import java.util.*;
import org.apache.kafka.streams.*;
import org.apache.kafka.common.serialization.*;
import org.junit.jupiter.api.Test;

class CountTopologyTest {
    @Test void countsEventsAndShowsThatDuplicateBusinessIdsAreStillTwoInputs() {
        Properties p = new Properties();
        p.put(StreamsConfig.APPLICATION_ID_CONFIG, "count-test");
        p.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "unused:9092");
        p.put(StreamsConfig.STATESTORE_CACHE_MAX_BYTES_CONFIG, 0);
        p.put(StreamsConfig.STATE_DIR_CONFIG, "target/test-state");
        p.put("processing.exception.handler.global.enabled", true);
        try (TopologyTestDriver d = new TopologyTestDriver(CountTopology.build(), p)) {
            var in = d.createInputTopic("study.streams.input", new StringSerializer(), new StringSerializer());
            var out = d.createOutputTopic("study.streams.output", new StringDeserializer(), new LongDeserializer());
            in.pipeInput("A", "evt-1");
            in.pipeInput("A", "evt-1");
            in.pipeInput("B", "evt-2");
            in.pipeInput(null, "ignored");
            in.pipeInput("C", (String) null);
            assertEquals(List.of(1L, 2L, 1L), out.readValuesToList());
            assertEquals(2L, d.<String, Long>getTimestampedKeyValueStore("event-counts").get("A").value());
            assertNull(d.<String, Long>getTimestampedKeyValueStore("event-counts").get("C"));
        }
    }
}
