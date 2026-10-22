import java.util.ArrayList;
import java.util.List;

public final class PromotionReadinessLesson {
    record Contract(long requiredHeadroomBytes, long expectedMaxmemoryBytes,
                    String expectedEvictionPolicy, boolean aofRequired) {}
    record Candidate(long observedHeadroomBytes, long configuredMaxmemoryBytes,
                     String evictionPolicyAfterPromotion, boolean aofEnabled,
                     boolean advertisedAddressReachable) {}

    static List<String> evaluate(Contract contract, Candidate candidate) {
        List<String> gaps = new ArrayList<>();
        if (candidate.observedHeadroomBytes() < contract.requiredHeadroomBytes()) {
            gaps.add("insufficient measured headroom");
        }
        if (candidate.configuredMaxmemoryBytes() != contract.expectedMaxmemoryBytes()) {
            gaps.add("different maxmemory contract");
        }
        if (!contract.expectedEvictionPolicy().equals(candidate.evictionPolicyAfterPromotion())) {
            gaps.add("different eviction policy");
        }
        if (contract.aofRequired() && !candidate.aofEnabled()) {
            gaps.add("AOF required by this service contract");
        }
        if (!candidate.advertisedAddressReachable()) {
            gaps.add("advertised address not reachable from application network");
        }
        return List.copyOf(gaps);
    }

    public static void main(String[] args) {
        long mib = 1024L * 1024L;
        Contract contract = new Contract(512L * mib, 2048L * mib,
                "noeviction", true);
        Candidate ready = new Candidate(768L * mib, 2048L * mib,
                "noeviction", true, true);
        Candidate gaps = new Candidate(128L * mib, 1024L * mib,
                "allkeys-lru", false, false);
        if (!evaluate(contract, ready).isEmpty()) {
            throw new AssertionError("matching contract should pass");
        }
        List<String> found = evaluate(contract, gaps);
        if (found.size() != 5) throw new AssertionError("five contract gaps expected");
        System.out.println("ready candidate: passed");
        for (String gap : found) System.out.println(gap);
    }
}
