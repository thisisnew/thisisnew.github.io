import java.util.List;
import java.util.Set;

public final class SentinelPlacementLesson {
    record Host(String name, int sentinels, int promotionCandidates) {
        Host {
            if (sentinels < 0 || promotionCandidates < 0) {
                throw new IllegalArgumentException("negative process count");
            }
        }
    }
    record Remaining(int sentinels, int requiredMajority, int candidates) {
        boolean prerequisitesRemain() {
            return sentinels >= requiredMajority && candidates > 0;
        }
    }

    static Remaining afterLoss(List<Host> hosts, Set<String> failedHosts) {
        int known = hosts.stream().mapToInt(Host::sentinels).sum();
        if (known == 0) throw new IllegalArgumentException("no known Sentinels");
        int liveSentinels = hosts.stream().filter(h -> !failedHosts.contains(h.name()))
                .mapToInt(Host::sentinels).sum();
        int liveCandidates = hosts.stream().filter(h -> !failedHosts.contains(h.name()))
                .mapToInt(Host::promotionCandidates).sum();
        return new Remaining(liveSentinels, known / 2 + 1, liveCandidates);
    }

    public static void main(String[] args) {
        List<Host> spread = List.of(new Host("A", 1, 0),
                new Host("B", 1, 1), new Host("C", 1, 1));
        for (String lost : List.of("A", "B", "C")) {
            Remaining remaining = afterLoss(spread, Set.of(lost));
            if (!remaining.prerequisitesRemain()) throw new AssertionError(lost);
            System.out.println("lost " + lost + ": " + remaining);
        }
        List<Host> concentrated = List.of(new Host("A", 3, 0),
                new Host("B", 0, 1), new Host("C", 0, 1));
        if (afterLoss(concentrated, Set.of("A")).prerequisitesRemain()) {
            throw new AssertionError("one host must not count as three domains");
        }
        if (afterLoss(spread, Set.of("B", "C")).prerequisitesRemain()) {
            throw new AssertionError("no majority and no promotion candidates");
        }
        System.out.println("correlated loss cases detected");
    }
}
