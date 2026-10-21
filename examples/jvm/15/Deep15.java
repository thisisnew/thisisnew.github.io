import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
public class Deep15 {
    public static void main(String[] args) throws Exception {
        AtomicInteger stock = new AtomicInteger(1);
        CountDownLatch checked = new CountDownLatch(2);
        Runnable buy = () -> {
            boolean available = stock.get() > 0;
            checked.countDown();
            try { checked.await(); }
            catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
            if (available) stock.decrementAndGet();
        };
        Thread a = new Thread(buy);
        Thread b = new Thread(buy);
        a.start(); b.start(); a.join(); b.join();
        System.out.println("broken=" + stock.get());
        stock.set(1);
        System.out.println("first=" + takeOne(stock));
        System.out.println("second=" + takeOne(stock));
        System.out.println("fixed=" + stock.get());
    }
    static boolean takeOne(AtomicInteger stock) {
        for (;;) {
            int current = stock.get();
            if (current <= 0) return false;
            if (stock.compareAndSet(current, current - 1)) return true;
        }
    }
}
