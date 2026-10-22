public final class ClusterProtectionRecoveryLesson {
    record Observation(boolean expectedPrimary, boolean slotViewsConverged,
                       boolean applicationProbePassed, boolean replicaProtected) {}

    static boolean serviceRestored(Observation e) {
        return e.expectedPrimary() && e.slotViewsConverged()
                && e.applicationProbePassed();
    }

    static boolean nextMaintenanceAllowed(Observation e) {
        return serviceRestored(e) && e.replicaProtected();
    }

    public static void main(String[] args) {
        Observation roleOnly = new Observation(true, false, false, false);
        Observation serving = new Observation(true, true, true, false);
        Observation protectedAgain = new Observation(true, true, true, true);
        if (serviceRestored(roleOnly)) throw new AssertionError("role alone");
        if (!serviceRestored(serving)) throw new AssertionError("service probe");
        if (nextMaintenanceAllowed(serving)) {
            throw new AssertionError("serving is not replica protection");
        }
        if (!nextMaintenanceAllowed(protectedAgain)) {
            throw new AssertionError("all evidence present");
        }
        System.out.println("service restored before the next maintenance is allowed");
    }
}
