package study;
import java.util.*;

/** One partition, one delivered batch in log order. A teaching calculation,
 * not a rebalance-aware concurrent commit manager. */
public final class CommitBoundary {
    public static OptionalLong next(List<Long> delivered, Set<Long> successful) {
        if (delivered.isEmpty()) return OptionalLong.empty();
        long previous = -1;
        for (long offset : delivered) {
            if (offset < 0 || offset <= previous)
                throw new IllegalArgumentException("Offsets must be strictly increasing");
            previous = offset;
        }
        for (long offset : delivered) {
            if (!successful.contains(offset)) return OptionalLong.of(offset);
        }
        return OptionalLong.of(Math.addExact(delivered.getLast(), 1));
    }
}
