import java.util.List;

public final class ReplicaWriteGateLesson {
    record Replica(boolean connected, boolean initialSyncComplete,
                   long millisSinceAck) {
        Replica {
            if (millisSinceAck < 0) throw new IllegalArgumentException("negative age");
        }
    }

    static boolean mayAccept(List<Replica> replicas, int minimum,
                             long maximumAckAgeMillis) {
        if (minimum < 1 || maximumAckAgeMillis <= 0) {
            throw new IllegalArgumentException("this model requires an active gate");
        }
        long acceptable = replicas.stream()
                .filter(Replica::connected)
                .filter(Replica::initialSyncComplete)
                .filter(replica -> replica.millisSinceAck() <= maximumAckAgeMillis)
                .count();
        return acceptable >= minimum;
    }

    public static void main(String[] args) {
        Replica ready = new Replica(true, true, 200);
        Replica stale = new Replica(true, true, 5000);
        Replica loading = new Replica(true, false, 100);
        if (!mayAccept(List.of(ready, stale), 1, 3000)) {
            throw new AssertionError("one acceptable replica");
        }
        if (mayAccept(List.of(ready, stale), 2, 3000)) {
            throw new AssertionError("two acceptable replicas required");
        }
        if (mayAccept(List.of(stale, loading), 1, 3000)) {
            throw new AssertionError("no acceptable candidate");
        }
        boolean accepted = mayAccept(List.of(ready), 1, 3000);
        boolean thisWriteAlreadyReplicated = false;
        if (!accepted || thisWriteAlreadyReplicated) {
            throw new AssertionError("gate and per-write delivery must stay distinct");
        }
        System.out.println("accepted=" + accepted);
        System.out.println("this write already replicated=" + thisWriteAlreadyReplicated);
    }
}
