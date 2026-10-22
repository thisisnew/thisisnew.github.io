import java.util.Objects;

public final class ReplicationWindowLesson {
    record Window(String historyId, long firstRetainedByte, long lastProducedByte) {
        Window {
            Objects.requireNonNull(historyId);
            if (historyId.isBlank() || firstRetainedByte < 1
                    || lastProducedByte < firstRetainedByte) {
                throw new IllegalArgumentException("invalid retained window");
            }
        }
    }

    record Request(String historyId, long lastProcessedByte) {}

    static boolean canContinue(Window window, Request request) {
        return window.historyId().equals(request.historyId())
                && request.lastProcessedByte() >= window.firstRetainedByte() - 1
                && request.lastProcessedByte() <= window.lastProducedByte();
    }

    static void expect(boolean expected, boolean actual, String label) {
        if (expected != actual) throw new AssertionError(label);
    }

    public static void main(String[] args) {
        Window window = new Window("history-A", 1001, 2000);
        expect(true, canContinue(window, new Request("history-A", 1000)),
                "next required byte 1001 is retained");
        expect(true, canContinue(window, new Request("history-A", 1500)),
                "middle of retained range");
        expect(true, canContinue(window, new Request("history-A", 2000)),
                "already at current end");
        expect(false, canContinue(window, new Request("history-A", 999)),
                "next required byte 1000 was discarded");
        expect(false, canContinue(window, new Request("history-B", 1500)),
                "same offset does not establish compatible history");
        expect(false, canContinue(window, new Request("history-A", 2001)),
                "request claims a position beyond this history");
        System.out.println("6 retained-window boundary cases passed");
    }
}
