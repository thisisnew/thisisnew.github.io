import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
public class Deep11 {
    static final ThreadLocal<String> REQUEST = new ThreadLocal<>();
    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newSingleThreadExecutor();
        try {
            pool.submit(() -> REQUEST.set("request-A")).get();
            System.out.println(pool.submit(() -> REQUEST.get()).get());
            pool.submit(() -> {
                try {
                    REQUEST.set("request-B");
                } finally {
                    REQUEST.remove();
                }
            }).get();
            System.out.println(pool.submit(() -> REQUEST.get()).get());
        } finally {
            pool.shutdown();
        }
    }
}
