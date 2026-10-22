import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class AofDurabilityLesson {
    record Change(String key, String value) {}

    static final class Model {
        private final List<Change> redisBuffer = new ArrayList<>();
        private final List<Change> osCache = new ArrayList<>();
        private final List<Change> durableFile = new ArrayList<>();

        void append(String key, String value) {
            redisBuffer.add(new Change(key, value));
        }

        void writeToOs() {
            osCache.addAll(redisBuffer);
            redisBuffer.clear();
        }

        void syncToDurableBoundary() {
            durableFile.addAll(osCache);
            osCache.clear();
        }

        Map<String, String> recoverAfterProcessLoss() {
            // Model assumption: OS remains alive and preserves its accepted writes.
            List<Change> surviving = new ArrayList<>(durableFile);
            surviving.addAll(osCache);
            return replay(surviving);
        }

        Map<String, String> recoverAfterHostVolatileLoss() {
            // Model assumption: all volatile memory disappears, durable storage remains.
            return replay(durableFile);
        }
    }

    static Map<String, String> replay(List<Change> changes) {
        Map<String, String> result = new HashMap<>();
        for (Change change : changes) result.put(change.key(), change.value());
        return Map.copyOf(result);
    }

    public static void main(String[] args) {
        Model model = new Model();
        model.append("goods:123:name", "배추");
        model.writeToOs();
        model.syncToDurableBoundary();
        model.append("goods:123:name", "알배기배추");
        model.writeToOs();
        model.append("goods:124:name", "당근");

        Map<String, String> process = model.recoverAfterProcessLoss();
        Map<String, String> host = model.recoverAfterHostVolatileLoss();
        if (!"알배기배추".equals(process.get("goods:123:name"))) {
            throw new AssertionError("OS-accepted write should survive in this model");
        }
        if (!"배추".equals(host.get("goods:123:name"))) {
            throw new AssertionError("only synced write survives volatile host loss");
        }
        if (process.containsKey("goods:124:name") || host.containsKey("goods:124:name")) {
            throw new AssertionError("Redis-only buffer should not survive");
        }
        System.out.println("process loss: " + process);
        System.out.println("host volatile loss: " + host);
    }
}
