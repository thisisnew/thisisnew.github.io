import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class RestoreBusinessLesson {
    enum Status { WAITING, COMPLETED }
    record Receiving(long id, Status status, int confirmedQuantity, Instant completedAt) {}

    static List<String> validate(List<Receiving> rows) {
        List<String> errors = new ArrayList<>();
        Map<Long, Receiving> unique = new HashMap<>();
        for (Receiving row : rows) {
            if (unique.putIfAbsent(row.id(), row) != null) {
                errors.add("duplicate receiving ID " + row.id());
            }
            if (row.confirmedQuantity() < 0) errors.add("negative quantity " + row.id());
            if (row.status() == Status.COMPLETED && row.completedAt() == null) {
                errors.add("completion time missing " + row.id());
            }
        }
        return List.copyOf(errors);
    }

    static List<String> compare(List<Receiving> expected, List<Receiving> restored) {
        Map<Long, Receiving> actual = new HashMap<>();
        for (Receiving row : restored) actual.put(row.id(), row);
        List<String> differences = new ArrayList<>();
        for (Receiving row : expected) {
            if (!row.equals(actual.get(row.id()))) differences.add("different ID " + row.id());
        }
        return List.copyOf(differences);
    }

    public static void main(String[] args) {
        Instant done = Instant.parse("2026-10-22T03:00:00Z");
        List<Receiving> expected = List.of(
                new Receiving(1, Status.COMPLETED, 10, done),
                new Receiving(2, Status.WAITING, 0, null));
        List<Receiving> restored = List.of(
                new Receiving(1, Status.COMPLETED, 7, done),
                new Receiving(2, Status.WAITING, 0, null));
        if (expected.size() != restored.size()) throw new AssertionError("count differs");
        if (!validate(restored).isEmpty()) throw new AssertionError("local rules fail");
        if (compare(expected, restored).size() != 1) {
            throw new AssertionError("content difference must be found");
        }
        List<Receiving> invalid = List.of(new Receiving(3, Status.COMPLETED, -1, null));
        if (validate(invalid).size() != 2) throw new AssertionError("two rule violations");
        System.out.println("same count, different content: detected");
        System.out.println("invalid completion and quantity: detected");
    }
}
