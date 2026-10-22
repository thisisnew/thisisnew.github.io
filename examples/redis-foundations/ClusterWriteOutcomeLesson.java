public final class ClusterWriteOutcomeLesson {
    enum Observation { ACKNOWLEDGED, EXPLICITLY_REJECTED, TIMEOUT }
    enum Decision { RECORD_ACK, INSPECT_REJECTION, RECONCILE_BY_REQUEST_ID }

    static Decision decide(Observation observation) {
        return switch (observation) {
            case ACKNOWLEDGED -> Decision.RECORD_ACK;
            case EXPLICITLY_REJECTED -> Decision.INSPECT_REJECTION;
            case TIMEOUT -> Decision.RECONCILE_BY_REQUEST_ID;
        };
    }

    public static void main(String[] args) {
        if (decide(Observation.TIMEOUT) != Decision.RECONCILE_BY_REQUEST_ID) {
            throw new AssertionError("timeout is an unknown execution outcome");
        }
        if (decide(Observation.ACKNOWLEDGED) != Decision.RECORD_ACK) {
            throw new AssertionError("record what the client observed");
        }
        if (decide(Observation.EXPLICITLY_REJECTED) != Decision.INSPECT_REJECTION) {
            throw new AssertionError("inspect the concrete server error");
        }
        System.out.println("timeout requires reconciliation, not blind DECR retry");
        System.out.println("an ACK is not a cross-failure durability proof");
    }
}
