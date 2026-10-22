import java.util.ArrayList;
import java.util.List;

public final class ClusterMaintenanceGateLesson {
    record Evidence(boolean backupRecoveryChecked, boolean expectedParent,
                    boolean replicaLinkUp, boolean initialSyncFinished,
                    boolean independentFailureDomain, boolean applicationHealthy) {}

    static List<String> blockers(Evidence e) {
        List<String> result = new ArrayList<>();
        if (!e.backupRecoveryChecked()) result.add("recovery evidence missing");
        if (!e.expectedParent()) result.add("unexpected replica parent");
        if (!e.replicaLinkUp()) result.add("replication link down");
        if (!e.initialSyncFinished()) result.add("initial sync in progress");
        if (!e.independentFailureDomain()) result.add("shared failure domain");
        if (!e.applicationHealthy()) result.add("application already unhealthy");
        return List.copyOf(result);
    }

    public static void main(String[] args) {
        Evidence ready = new Evidence(true, true, true, true, true, true);
        if (!blockers(ready).isEmpty()) throw new AssertionError("ready");
        Evidence syncing = new Evidence(true, true, true, false, true, true);
        if (!blockers(syncing).equals(List.of("initial sync in progress"))) {
            throw new AssertionError("a connected replica may still be syncing");
        }
        Evidence risky = new Evidence(true, true, false, false, false, true);
        if (blockers(risky).size() != 3) throw new AssertionError("independent reasons");
        System.out.println("ready blockers=" + blockers(ready));
        System.out.println("syncing blockers=" + blockers(syncing));
    }
}
