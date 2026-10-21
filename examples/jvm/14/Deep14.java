public class Deep14 {
    interface Fee { int apply(int quantity); }
    static class Normal implements Fee {
        public int apply(int quantity) { return quantity + 1; }
    }
    static class Express implements Fee {
        public int apply(int quantity) { return quantity + 10; }
    }
    static volatile long sink;
    static long batch(Fee fee) {
        long sum = 0;
        for (int i = 0; i < 100; i++) sum += fee.apply(i);
        return sum;
    }
    public static void main(String[] args) {
        Fee normal = new Normal();
        for (int i = 0; i < 30_000; i++) sink = batch(normal);
        System.out.println(batch(normal));
        System.out.println(batch(new Express()));
    }
}
