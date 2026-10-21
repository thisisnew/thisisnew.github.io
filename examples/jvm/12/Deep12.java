public class Deep12 {
    static volatile int checksum;
    public static void main(String[] args) {
        int slots = args.length == 0 ? 8 : Integer.parseInt(args[0]);
        if (slots < 1 || slots > 1024) throw new IllegalArgumentException("1..1024");
        byte[][] pending = new byte[slots][];
        for (int i = 0; i < 20_000; i++) {
            byte[] state = new byte[16 * 1024];
            state[0] = (byte) i;
            pending[i % slots] = state;
            checksum += pending[i % slots][0];
        }
        System.out.println("retained slots=" + pending.length);
        System.out.println("last=" + pending[19_999 % slots][0]);
    }
}
