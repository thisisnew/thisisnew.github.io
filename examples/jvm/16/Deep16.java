import java.util.ArrayList;
import java.util.List;
public class Deep16 {
    static final Object lock = new Object();
    static final List<byte[]> retained = new ArrayList<>();
    static volatile long sink;
    public static void main(String[] args) throws Exception {
        String mode = args.length == 0 ? "memory" : args[0];
        System.out.println("pid=" + ProcessHandle.current().pid());
        System.out.println("mode=" + mode);
        switch (mode) {
            case "cpu" -> {
                long until = System.nanoTime() + 15_000_000_000L;
                long value = 1;
                while (System.nanoTime() < until) value = value * 1664525 + 1013904223;
                sink = value;
            }
            case "lock" -> {
                Thread waiter;
                synchronized (lock) {
                    waiter = new Thread(() -> {
                        synchronized (lock) { System.out.println("acquired"); }
                    }, "lock-waiter");
                    waiter.start();
                    Thread.sleep(15_000);
                }
                waiter.join();
            }
            case "memory" -> {
                for (int i = 0; i < 16; i++) retained.add(new byte[1024 * 1024]);
                Thread.sleep(15_000);
                System.out.println("retained=" + retained.size());
            }
            default -> throw new IllegalArgumentException("cpu | lock | memory");
        }
        System.out.println("done");
    }
}
