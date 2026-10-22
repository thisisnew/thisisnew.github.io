import java.util.Set;

public final class SentinelEpochLesson {
    record Configuration(long epoch, String primary, Set<String> observedWrites) {
        Configuration {
            if (epoch < 0) throw new IllegalArgumentException("negative epoch");
            observedWrites = Set.copyOf(observedWrites);
        }
    }

    static Configuration newer(Configuration current, Configuration received) {
        return received.epoch() > current.epoch() ? received : current;
    }

    public static void main(String[] args) {
        Configuration oldSide = new Configuration(11, "old-primary", Set.of("W1", "W2"));
        Configuration newSide = new Configuration(12, "new-primary", Set.of("W1", "W3"));
        Configuration chosen = newer(oldSide, newSide);
        if (chosen.epoch() != 12) throw new AssertionError("newer configuration");
        if (chosen.observedWrites().contains("W2")) {
            throw new AssertionError("configuration selection invented a data merge");
        }
        if (!chosen.observedWrites().contains("W3")) throw new AssertionError("new side");
        if (!newSide.equals(newer(newSide, oldSide))) {
            throw new AssertionError("older configuration replaced newer one");
        }
        System.out.println("chosen epoch=" + chosen.epoch());
        System.out.println("chosen writes=" + chosen.observedWrites().stream().sorted().toList());
        System.out.println("old-only write W2 is not automatically merged");
    }
}
