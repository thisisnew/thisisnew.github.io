public final class SentinelTiltClockLesson {
    static final class ClockModel {
        private long lastTick;
        private long abnormalAt;
        private boolean tilted;

        ClockModel(long initialTimeMillis) { lastTick = initialTimeMillis; }

        void tick(long nowMillis) {
            long delta = nowMillis - lastTick;
            if (delta < 0 || delta > 2000) {
                tilted = true;
                abnormalAt = nowMillis;
            } else if (tilted && nowMillis - abnormalAt >= 30000) {
                tilted = false;
            }
            lastTick = nowMillis;
        }

        boolean tilted() { return tilted; }
    }

    public static void main(String[] args) {
        ClockModel clock = new ClockModel(0);
        clock.tick(100);
        if (clock.tilted()) throw new AssertionError("ordinary interval");
        clock.tick(2301);
        if (!clock.tilted()) throw new AssertionError("long pause not detected");
        for (int i = 1; i < 300; i++) clock.tick(2301L + i * 100L);
        if (!clock.tilted()) throw new AssertionError("stable period not completed");
        clock.tick(32301);
        if (clock.tilted()) throw new AssertionError("stable period completed");
        clock.tick(32201);
        if (!clock.tilted()) throw new AssertionError("backward clock not detected");
        System.out.println("long pause, stable recovery and backward time checked");
    }
}
