public final class ReplicationBacklogPlan {
    private static final long MIB = 1024L * 1024L;

    static long plannedBytes(long bytesPerSecond, long gapSeconds,
                             int reservePercent) {
        if (bytesPerSecond <= 0 || gapSeconds <= 0 || reservePercent < 0) {
            throw new IllegalArgumentException("invalid planning input");
        }
        long base = Math.multiplyExact(bytesPerSecond, gapSeconds);
        long scaled = Math.multiplyExact(base, Math.addExact(100L, reservePercent));
        long quotient = scaled / 100;
        return scaled % 100 == 0 ? quotient : Math.addExact(quotient, 1);
    }

    public static void main(String[] args) {
        long steady = plannedBytes(2L * MIB, 30, 50);
        long burst = plannedBytes(6L * MIB, 30, 50);
        if (steady != 90L * MIB) throw new AssertionError("90 MiB expected");
        if (burst != 270L * MIB) throw new AssertionError("270 MiB expected");
        if (plannedBytes(1, 1, 1) != 2) throw new AssertionError("round up");
        System.out.println("2 MiB/s scenario: " + steady / MIB + " MiB");
        System.out.println("6 MiB/s scenario: " + burst / MIB + " MiB");
    }
}
