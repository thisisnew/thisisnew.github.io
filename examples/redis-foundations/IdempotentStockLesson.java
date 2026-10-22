import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

public final class IdempotentStockLesson {
    record Result(boolean accepted, int remaining) {}
    record Processed(int quantity, Result result) {}

    static final class Stock {
        private int remaining;
        private final Map<String, Processed> processed = new HashMap<>();

        Stock(int initial) {
            if (initial < 0) throw new IllegalArgumentException("negative stock");
            this.remaining = initial;
        }

        synchronized Result reserve(String requestId, int quantity) {
            Objects.requireNonNull(requestId);
            if (requestId.isBlank() || quantity <= 0) {
                throw new IllegalArgumentException("invalid request");
            }
            Processed prior = processed.get(requestId);
            if (prior != null) {
                if (prior.quantity() != quantity) {
                    throw new IllegalArgumentException("request ID reused with new quantity");
                }
                return prior.result();
            }
            boolean accepted = remaining >= quantity;
            if (accepted) remaining -= quantity;
            Result result = new Result(accepted, remaining);
            processed.put(requestId, new Processed(quantity, result));
            return result;
        }
    }

    public static void main(String[] args) {
        Stock stock = new Stock(10);
        Result first = stock.reserve("receiving-001", 3);
        Result retry = stock.reserve("receiving-001", 3);
        Result second = stock.reserve("receiving-002", 2);
        if (!first.equals(retry)) throw new AssertionError("retry changed result");
        if (first.remaining() != 7) throw new AssertionError("first request");
        if (second.remaining() != 5) throw new AssertionError("duplicate subtraction");
        System.out.println("first=" + first);
        System.out.println("retry=" + retry);
        System.out.println("second=" + second);
    }
}
