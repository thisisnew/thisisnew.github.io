import java.time.Duration;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

public final class RedisSnapshotLesson {
    record Snapshot(Instant capturedAt, Map<String, String> values) {
        Snapshot {
            values = Map.copyOf(values);
        }
    }

    static Snapshot capture(Instant at, Map<String, String> live) {
        return new Snapshot(at, live);
    }

    static Map<String, String> restore(Snapshot snapshot) {
        return new HashMap<>(snapshot.values());
    }

    public static void main(String[] args) {
        Map<String, String> live = new HashMap<>();
        live.put("lab:balance", "100");
        Instant captured = Instant.parse("2026-10-22T03:00:00Z");
        Snapshot snapshot = capture(captured, live);

        live.put("lab:balance", "90");
        live.put("lab:after", "yes");
        Instant failure = captured.plusSeconds(30);
        Map<String, String> restored = restore(snapshot);

        if (!"90".equals(live.get("lab:balance"))) {
            throw new AssertionError("live state must change");
        }
        if (!"100".equals(restored.get("lab:balance"))) {
            throw new AssertionError("snapshot boundary was lost");
        }
        if (restored.containsKey("lab:after")) {
            throw new AssertionError("post-snapshot write must be absent");
        }
        System.out.println("live=" + live.get("lab:balance"));
        System.out.println("restored=" + restored.get("lab:balance"));
        System.out.println("point age seconds="
                + Duration.between(snapshot.capturedAt(), failure).toSeconds());
    }
}
