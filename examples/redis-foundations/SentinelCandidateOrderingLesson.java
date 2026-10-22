import java.util.Comparator;
import java.util.List;

public final class SentinelCandidateOrderingLesson {
    record Candidate(String runId, int priority, long offset, boolean eligible) {
        Candidate {
            if (priority < 0 || offset < 0) throw new IllegalArgumentException("negative value");
        }
    }

    static Candidate select(List<Candidate> candidates) {
        Comparator<Candidate> order = Comparator.comparingInt(Candidate::priority)
                .thenComparing(Comparator.comparingLong(Candidate::offset).reversed())
                .thenComparing(Candidate::runId);
        return candidates.stream()
                .filter(Candidate::eligible)
                .filter(candidate -> candidate.priority() != 0)
                .min(order)
                .orElseThrow(() -> new IllegalStateException("no eligible promotion candidate"));
    }

    public static void main(String[] args) {
        Candidate preferred = new Candidate("r1", 50, 9000, true);
        Candidate newer = new Candidate("r2", 100, 10000, true);
        Candidate forbidden = new Candidate("r0", 0, 20000, true);
        Candidate unhealthy = new Candidate("r3", 1, 30000, false);
        if (!preferred.equals(select(List.of(newer, preferred, forbidden, unhealthy)))) {
            throw new AssertionError("policy priority must precede offset");
        }
        Candidate samePriorityNewer = new Candidate("r4", 50, 9500, true);
        if (!samePriorityNewer.equals(select(List.of(preferred, samePriorityNewer)))) {
            throw new AssertionError("offset should decide equal priority");
        }
        Candidate tieA = new Candidate("a", 50, 9500, true);
        Candidate tieB = new Candidate("b", 50, 9500, true);
        if (!tieA.equals(select(List.of(tieB, tieA)))) throw new AssertionError("stable tie");
        boolean rejected = false;
        try {
            select(List.of(forbidden, unhealthy));
        } catch (IllegalStateException expected) {
            rejected = true;
        }
        if (!rejected) throw new AssertionError("invalid candidates were promoted");
        System.out.println("priority, offset, tie and exclusion cases passed");
    }
}
