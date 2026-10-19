import java.util.ArrayList;
import java.util.List;

public class Lesson16 {
    static volatile long sink;
    static final List<byte[]> retained = new ArrayList<>();
    public static void main(String[] args) throws InterruptedException {
        int seconds = args.length == 0 ? 2 : Integer.parseInt(args[0]);
        if (seconds < 1 || seconds > 600) throw new IllegalArgumentException("1..600");
        for (int i = 0; i < 8; i++) retained.add(new byte[256 * 1024]);
        System.out.println("pid=" + ProcessHandle.current().pid());
        System.out.flush();
        long until = System.nanoTime() + seconds * 1_000_000_000L;
        while (System.nanoTime() < until) {
            for (int i = 0; i < 100_000; i++) sink += i;
            Thread.sleep(20);
        }
        System.out.println("done");
    }
}
