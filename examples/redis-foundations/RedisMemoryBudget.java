public final class RedisMemoryBudget {
    private static final long MIB = 1024L * 1024L;

    record Budget(long limitBytes, long baselineBytes,
                  long extraPeakBytes, long reserveBytes) {
        Budget {
            if (limitBytes <= 0 || baselineBytes < 0
                    || extraPeakBytes < 0 || reserveBytes < 0) {
                throw new IllegalArgumentException("invalid byte count");
            }
        }

        long requiredBytes() {
            return Math.addExact(Math.addExact(baselineBytes, extraPeakBytes),
                    reserveBytes);
        }

        long remainingBytes() {
            return Math.subtractExact(limitBytes, requiredBytes());
        }

        boolean fitsObservedScenario() {
            return remainingBytes() >= 0;
        }
    }

    static long mib(long value) {
        return Math.multiplyExact(value, MIB);
    }

    public static void main(String[] args) {
        Budget normalSave = new Budget(mib(8192), mib(5200),
                mib(1800), mib(800));
        Budget slowSave = new Budget(mib(8192), mib(5200),
                mib(2600), mib(800));

        if (!normalSave.fitsObservedScenario()) {
            throw new AssertionError("first scenario should fit");
        }
        if (slowSave.fitsObservedScenario()) {
            throw new AssertionError("second scenario should exceed limit");
        }
        System.out.println("normal remaining MiB="
                + normalSave.remainingBytes() / MIB);
        System.out.println("slow remaining MiB="
                + slowSave.remainingBytes() / MIB);
    }
}
