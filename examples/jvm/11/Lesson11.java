import java.lang.ref.WeakReference;
import java.util.HashMap;
import java.util.Map;

public class Lesson11 {
    static final Map<String, byte[]> cache = new HashMap<>();
    static class Node { Node next; }
    static WeakReference<Node> makeCycle() {
        Node a = new Node();
        Node b = new Node();
        a.next = b;
        b.next = a;
        return new WeakReference<>(a);
    }
    public static void main(String[] args) {
        WeakReference<Node> reference = makeCycle();
        cache.put("old-request", new byte[1024 * 1024]);
        System.out.println("cache entries=" + cache.size());
        System.gc();
        System.out.println("cycle observed alive=" + (reference.get() != null));
        cache.clear();
        System.out.println("cache entries=" + cache.size());
    }
}
