public class Lesson14 {
    interface Price { int apply(int value); }
    static final class PlusOne implements Price {
        public int apply(int value) { return value + 1; }
    }
    static final class PlusTwo implements Price {
        public int apply(int value) { return value + 2; }
    }
    static volatile long sink;
    static long run(Price price, int n) {
        long sum = 0;
        for (int i = 0; i < n; i++) sum += price.apply(i);
        return sum;
    }
    public static void main(String[] args) {
        for (int i = 0; i < 40; i++) sink = run(new PlusOne(), 100_000);
        System.out.println(run(new PlusOne(), 100));
        System.out.println(run(new PlusTwo(), 100));
    }
}
