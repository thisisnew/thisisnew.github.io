public final class SentinelApprovalLesson {
    record Result(int majority, int requiredApprovals,
                  boolean enoughDownReports, boolean mayProceed) {}

    static Result evaluate(int known, int quorum, int downReports, int approvals) {
        if (known < 1 || quorum < 1 || quorum > known
                || downReports < 0 || downReports > known
                || approvals < 0 || approvals > known) {
            throw new IllegalArgumentException("invalid fixed-membership input");
        }
        int majority = known / 2 + 1;
        int required = Math.max(majority, quorum);
        boolean down = downReports >= quorum;
        return new Result(majority, required, down, down && approvals >= required);
    }

    static void expect(boolean down, boolean proceed, int known, int quorum,
                       int reports, int approvals) {
        Result result = evaluate(known, quorum, reports, approvals);
        if (result.enoughDownReports() != down || result.mayProceed() != proceed) {
            throw new AssertionError(result);
        }
    }

    public static void main(String[] args) {
        expect(true, false, 5, 2, 2, 2);
        expect(true, true, 5, 2, 2, 3);
        expect(true, false, 5, 4, 4, 3);
        expect(false, false, 5, 4, 3, 5);
        expect(true, true, 3, 2, 2, 2);
        expect(true, false, 2, 1, 1, 1);
        for (int known : new int[]{3, 5, 7}) {
            Result r = evaluate(known, 2, 2, known / 2);
            if (r.mayProceed()) throw new AssertionError("minority authorized");
        }
        System.out.println("quorum and approval boundary cases passed");
    }
}
