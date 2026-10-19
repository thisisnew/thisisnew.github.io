public class Lesson15 {
    static final class Counter {
        private int value;
        synchronized void increment() { value++; }
        synchronized int read() { return value; }
        void blockIncrement() {
            synchronized (this) { value++; }
        }
    }
    public static void main(String[] args) throws InterruptedException {
        Counter counter = new Counter();
        Runnable job = () -> {
            for (int i = 0; i < 10_000; i++) counter.increment();
        };
        Thread first = new Thread(job, "inspection-a");
        Thread second = new Thread(job, "inspection-b");
        first.start();
        second.start();
        first.join();
        second.join();
        System.out.println(counter.read());
    }
}
