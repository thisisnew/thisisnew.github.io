public final class ClusterShardBudgetLesson {
    record Plan(int primaries, int replicasPerPrimary,
                long memoryPerNodeMiB, int reservePercent) {
        Plan {
            if (primaries < 1 || replicasPerPrimary < 0 || memoryPerNodeMiB < 1
                    || reservePercent < 0 || reservePercent >= 100) {
                throw new IllegalArgumentException("invalid plan");
            }
        }

        long processes() {
            return Math.multiplyExact((long) primaries, replicasPerPrimary + 1L);
        }

        long provisionedMiB() {
            return Math.multiplyExact(processes(), memoryPerNodeMiB);
        }

        long logicalBudgetMiB() {
            long perShard = Math.multiplyExact(memoryPerNodeMiB,
                    100L - reservePercent) / 100;
            return Math.multiplyExact((long) primaries, perShard);
        }
    }

    public static void main(String[] args) {
        Plan oneCopy = new Plan(3, 0, 1024, 25);
        Plan twoCopies = new Plan(3, 1, 1024, 25);
        if (twoCopies.processes() != 6) throw new AssertionError("processes");
        if (twoCopies.provisionedMiB() != 6144) throw new AssertionError("physical");
        if (twoCopies.logicalBudgetMiB() != 2304) throw new AssertionError("logical");
        if (oneCopy.logicalBudgetMiB() != twoCopies.logicalBudgetMiB()) {
            throw new AssertionError("replica must not increase unique-data budget");
        }
        if (new Plan(4, 1, 1024, 25).logicalBudgetMiB() != 3072) {
            throw new AssertionError("another shard changes the model budget");
        }
        System.out.println("processes=" + twoCopies.processes());
        System.out.println("provisionedMiB=" + twoCopies.provisionedMiB());
        System.out.println("logicalBudgetMiB=" + twoCopies.logicalBudgetMiB());
    }
}
