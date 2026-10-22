import java.util.ArrayList;
import java.util.List;

public final class RedisConfigContract {
    record Expected(long maxmemoryBytes, String evictionPolicy) {
        Expected {
            if (maxmemoryBytes <= 0) {
                throw new IllegalArgumentException("expected limit must be positive");
            }
            if (evictionPolicy == null || evictionPolicy.isBlank()) {
                throw new IllegalArgumentException("policy is required");
            }
        }
    }

    record Observed(String endpoint, long maxmemoryBytes,
                    String evictionPolicy, String serverVersion) {}

    static List<String> compare(Expected expected, Observed observed) {
        List<String> differences = new ArrayList<>();
        if (expected.maxmemoryBytes() != observed.maxmemoryBytes()) {
            differences.add("maxmemory expected=" + expected.maxmemoryBytes()
                    + " observed=" + observed.maxmemoryBytes());
        }
        if (!expected.evictionPolicy().equals(observed.evictionPolicy())) {
            differences.add("policy expected=" + expected.evictionPolicy()
                    + " observed=" + observed.evictionPolicy());
        }
        return List.copyOf(differences);
    }

    public static void main(String[] args) {
        long mib = 1024L * 1024L;
        Expected contract = new Expected(128L * mib, "noeviction");
        Observed before = new Observed("127.0.0.1:16379",
                128L * mib, "noeviction", "example");
        Observed changed = new Observed("127.0.0.1:16379",
                96L * mib, "noeviction", "example");

        if (!compare(contract, before).isEmpty()) {
            throw new AssertionError("matching snapshot was rejected");
        }
        List<String> differences = compare(contract, changed);
        if (differences.size() != 1) {
            throw new AssertionError("one memory difference was expected");
        }
        System.out.println(differences.get(0));
    }
}
