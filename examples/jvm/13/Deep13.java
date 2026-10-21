public class Deep13 {
    static final byte[][] cache = new byte[512][];
    static volatile int sink;
    public static void main(String[] args) {
        for (int round = 0; round < 120; round++) {
            for (int i = 0; i < cache.length; i++) {
                byte[] value = new byte[8 * 1024];
                value[0] = (byte) round;
                cache[i] = value;
                sink = value[0];
            }
        }
        System.out.println("slots=" + cache.length);
        System.out.println("last=" + cache[511][0]);
    }
}
