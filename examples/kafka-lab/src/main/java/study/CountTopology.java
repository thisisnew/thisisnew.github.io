package study;
import org.apache.kafka.streams.*;
import org.apache.kafka.streams.kstream.*;
import org.apache.kafka.common.serialization.Serdes;

public final class CountTopology {
    public static Topology build() {
        StreamsBuilder b = new StreamsBuilder();
        b.stream("study.streams.input", Consumed.with(Serdes.String(), Serdes.String()))
         .filter((key, value) -> key != null && value != null)
         .groupByKey(Grouped.with(Serdes.String(), Serdes.String()))
         .count(Materialized.as("event-counts"))
         .toStream()
         .to("study.streams.output", Produced.with(Serdes.String(), Serdes.Long()));
        return b.build();
    }
    public static void main(String[] args) {
        java.util.Properties p = new java.util.Properties();
        p.put(StreamsConfig.APPLICATION_ID_CONFIG, "study-count-v1");
        p.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, Lab.bootstrap());
        p.put(StreamsConfig.STATE_DIR_CONFIG, System.getProperty("java.io.tmpdir") + "/study-count-" + ProcessHandle.current().pid());
        // Single broker LAB only. Not a production durability recommendation.
        p.put(StreamsConfig.REPLICATION_FACTOR_CONFIG, 1);
        p.put(StreamsConfig.STATESTORE_CACHE_MAX_BYTES_CONFIG, 0);
        Topology t = build();
        System.out.println(t.describe());
        KafkaStreams streams = new KafkaStreams(t, p);
        streams.setStateListener((next, old) -> System.out.println(old + " -> " + next));
        Runtime.getRuntime().addShutdownHook(new Thread(() -> streams.close(java.time.Duration.ofSeconds(15))));
        streams.start();
    }
}
