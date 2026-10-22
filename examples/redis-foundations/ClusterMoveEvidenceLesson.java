public final class ClusterMoveEvidenceLesson {
    record Sample(String type, String value, long pttlMillis) {}

    static boolean samePayload(Sample before, Sample after) {
        return before.type().equals(after.type())
                && before.value().equals(after.value());
    }

    static boolean plausibleTtl(long before, long after,
                                long elapsedMillis, long toleranceMillis) {
        if (before <= 0 || after <= 0 || elapsedMillis < 0 || toleranceMillis < 0) {
            return false;
        }
        long expected = before - elapsedMillis;
        return expected > 0 && Math.abs(after - expected) <= toleranceMillis;
    }

    public static void main(String[] args) {
        Sample before = new Sample("string", "PACKED", 60000);
        Sample after = new Sample("string", "PACKED", 54900);
        if (!samePayload(before, after)) throw new AssertionError("payload");
        if (!plausibleTtl(before.pttlMillis(), after.pttlMillis(), 5000, 300)) {
            throw new AssertionError("elapsed time must be considered");
        }
        if (plausibleTtl(60000, -1, 5000, 300)) {
            throw new AssertionError("lost expiry must not pass");
        }
        if (plausibleTtl(60000, -2, 5000, 300)) {
            throw new AssertionError("missing key needs separate investigation");
        }
        if (samePayload(before, new Sample("string", "LOST", 54900))) {
            throw new AssertionError("value mismatch");
        }
        System.out.println("payload unchanged and sampled TTL matches elapsed time");
    }
}
