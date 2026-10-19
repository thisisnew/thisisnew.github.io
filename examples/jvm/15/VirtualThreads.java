import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.ArrayList;
import java.util.List;

public class VirtualThreads {
    public static void main(String[] args) throws Exception {
        List<Future<Integer>> tasks = new ArrayList<>();
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 100; i++) {
                tasks.add(executor.submit(() -> {
                    Thread.sleep(10);
                    return 1;
                }));
            }
            int total = 0;
            for (Future<Integer> task : tasks) total += task.get();
            System.out.println("completed=" + total);
        }
    }
}
