import java.util.List;

public final class SentinelDiscoveryValidationLesson {
    enum Role { PRIMARY, REPLICA, UNKNOWN }
    record Endpoint(String host, int port) {}
    record CheckedCandidate(Endpoint endpoint, boolean reachable, Role reportedRole) {}

    static Endpoint firstVerifiedPrimary(List<CheckedCandidate> candidates) {
        return candidates.stream()
                .filter(CheckedCandidate::reachable)
                .filter(candidate -> candidate.reportedRole() == Role.PRIMARY)
                .map(CheckedCandidate::endpoint)
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("no verified primary"));
    }

    public static void main(String[] args) {
        Endpoint oldAddress = new Endpoint("127.0.0.1", 16390);
        Endpoint newAddress = new Endpoint("127.0.0.1", 16391);
        List<CheckedCandidate> observed = List.of(
                new CheckedCandidate(oldAddress, true, Role.REPLICA),
                new CheckedCandidate(newAddress, true, Role.PRIMARY));
        if (!newAddress.equals(firstVerifiedPrimary(observed))) {
            throw new AssertionError("stale discovered address was trusted");
        }
        boolean rejected = false;
        try {
            firstVerifiedPrimary(List.of(
                    new CheckedCandidate(oldAddress, false, Role.PRIMARY),
                    new CheckedCandidate(newAddress, true, Role.UNKNOWN)));
        } catch (IllegalStateException expected) {
            rejected = true;
        }
        if (!rejected) throw new AssertionError("unverified role accepted");
        System.out.println("verified primary=" + firstVerifiedPrimary(observed));
        System.out.println("unreachable and unknown candidates rejected");
    }
}
