public final class ReadFreshnessLesson {
    enum Target { REPLICA, PRIMARY }
    record Request(boolean replicaAllowed, long minimumBusinessVersion) {
        Request {
            if (minimumBusinessVersion < 0) throw new IllegalArgumentException("version");
        }
    }
    record Replica(boolean connected, boolean initialSyncInProgress,
                   long observedBusinessVersion) {}

    static Target choose(Request request, Replica replica) {
        if (!request.replicaAllowed()) return Target.PRIMARY;
        if (!replica.connected() || replica.initialSyncInProgress()) return Target.PRIMARY;
        if (replica.observedBusinessVersion() < request.minimumBusinessVersion()) {
            return Target.PRIMARY;
        }
        return Target.REPLICA;
    }

    static void expect(Target expected, Target actual, String label) {
        if (actual != expected) throw new AssertionError(label);
    }

    public static void main(String[] args) {
        Request afterWrite = new Request(true, 42);
        expect(Target.PRIMARY, choose(afterWrite, new Replica(true, false, 41)),
                "older than the version returned by the write");
        expect(Target.REPLICA, choose(afterWrite, new Replica(true, false, 42)),
                "minimum version satisfied");
        expect(Target.PRIMARY, choose(afterWrite, new Replica(true, true, 100)),
                "initial synchronization is not a ready candidate");
        expect(Target.PRIMARY, choose(afterWrite, new Replica(false, false, 100)),
                "disconnected candidate excluded by this policy");
        expect(Target.PRIMARY, choose(new Request(false, 0),
                new Replica(true, false, 100)), "primary-only business flow");
        expect(Target.REPLICA, choose(new Request(true, 0),
                new Replica(true, false, 10)), "stale-tolerant example");
        System.out.println("6 read-routing policy cases passed");
    }
}
