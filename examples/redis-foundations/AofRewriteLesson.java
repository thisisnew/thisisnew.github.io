import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class AofRewriteLesson {
    record Put(String key, String value) {}

    static Map<String, String> replay(List<Put> log) {
        Map<String, String> state = new HashMap<>();
        for (Put put : log) state.put(put.key(), put.value());
        return state;
    }

    static List<Put> rewriteState(Map<String, String> state) {
        return state.entrySet().stream()
                .sorted(Map.Entry.comparingByKey())
                .map(entry -> new Put(entry.getKey(), entry.getValue()))
                .toList();
    }

    public static void main(String[] args) {
        List<Put> history = new ArrayList<>();
        for (int i = 1; i <= 100; i++) {
            history.add(new Put("counter", Integer.toString(i)));
        }
        history.add(new Put("status", "waiting"));
        history.add(new Put("status", "completed"));
        Map<String, String> before = replay(history);
        List<Put> rewritten = rewriteState(before);
        Map<String, String> after = replay(rewritten);
        if (!before.equals(after)) throw new AssertionError("state changed");
        if (rewritten.size() != 2) throw new AssertionError("one record per live key");
        if (history.size() != 102) throw new AssertionError("original history lost");
        System.out.println("records " + history.size() + " -> " + rewritten.size());
        System.out.println("same state=" + before.equals(after));
    }
}
