public final class ClusterRetryBudgetLesson {
    enum Failure { TRYAGAIN_BEFORE_EXECUTION, CROSSSLOT, TIMEOUT }
    enum Action { DELAYED_RETRY, STOP, RECONCILE }

    static Action decide(Failure failure, int attemptsMade, int maximumAttempts,
                         long elapsedMillis, long deadlineMillis,
                         long nextDelayMillis, long minimumAttemptMillis) {
        if (attemptsMade < 1 || maximumAttempts < 1 || elapsedMillis < 0
                || deadlineMillis < 1 || nextDelayMillis < 0 || minimumAttemptMillis < 1) {
            throw new IllegalArgumentException("invalid retry budget");
        }
        if (failure == Failure.TIMEOUT) return Action.RECONCILE;
        if (failure == Failure.CROSSSLOT) return Action.STOP;
        long remaining = deadlineMillis - elapsedMillis;
        return attemptsMade < maximumAttempts && remaining > nextDelayMillis
                && remaining - nextDelayMillis >= minimumAttemptMillis
                ? Action.DELAYED_RETRY : Action.STOP;
    }

    public static void main(String[] args) {
        if (decide(Failure.TRYAGAIN_BEFORE_EXECUTION, 1, 3, 40, 200, 20, 30)
                != Action.DELAYED_RETRY) throw new AssertionError("budget available");
        if (decide(Failure.TRYAGAIN_BEFORE_EXECUTION, 3, 3, 40, 200, 20, 30)
                != Action.STOP) throw new AssertionError("attempt limit");
        if (decide(Failure.TRYAGAIN_BEFORE_EXECUTION, 1, 3, 170, 200, 20, 30)
                != Action.STOP) throw new AssertionError("deadline limit");
        if (decide(Failure.CROSSSLOT, 1, 3, 1, 200, 20, 30)
                != Action.STOP) throw new AssertionError("schema error");
        if (decide(Failure.TIMEOUT, 1, 3, 1, 200, 20, 30)
                != Action.RECONCILE) throw new AssertionError("unknown outcome");
        System.out.println("attempt, deadline, schema and unknown-outcome gates passed");
    }
}
