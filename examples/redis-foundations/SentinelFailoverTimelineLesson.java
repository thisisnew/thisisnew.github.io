public final class SentinelFailoverTimelineLesson {
    record Timeline(long impactStart, long detected, long authorized,
                    long promoted, long discovered, long firstWrite,
                    long redundancyRestored) {
        Timeline {
            long[] times = {impactStart, detected, authorized, promoted,
                    discovered, firstWrite, redundancyRestored};
            for (int i = 0; i < times.length; i++) {
                if (times[i] < 0 || (i > 0 && times[i] < times[i - 1])) {
                    throw new IllegalArgumentException("non-monotonic teaching timeline");
                }
            }
        }
        long serverRoleRecoveryMillis() { return promoted - impactStart; }
        long userWriteRecoveryMillis() { return firstWrite - impactStart; }
        long discoveryAndReconnectMillis() { return firstWrite - promoted; }
        long redundancyGapAfterServiceMillis() { return redundancyRestored - firstWrite; }
    }

    public static void main(String[] args) {
        Timeline t = new Timeline(0, 5000, 7000, 9000, 12000, 14000, 30000);
        if (t.serverRoleRecoveryMillis() != 9000) throw new AssertionError("server");
        if (t.userWriteRecoveryMillis() != 14000) throw new AssertionError("user");
        if (t.discoveryAndReconnectMillis() != 5000) throw new AssertionError("client");
        if (t.redundancyGapAfterServiceMillis() != 16000) throw new AssertionError("replicas");
        boolean rejected = false;
        try {
            new Timeline(0, 5000, 4000, 9000, 12000, 14000, 30000);
        } catch (IllegalArgumentException expected) {
            rejected = true;
        }
        if (!rejected) throw new AssertionError("contradictory sequence accepted");
        System.out.println("server role recovery ms=" + t.serverRoleRecoveryMillis());
        System.out.println("first user write ms=" + t.userWriteRecoveryMillis());
        System.out.println("replica redundancy ms=" + t.redundancyRestored());
    }
}
