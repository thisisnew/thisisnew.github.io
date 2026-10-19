public class Lesson12 {
    static volatile Object sink;
    public static void main(String[] args) {
        byte[][] retained = new byte[128][];
        for (int i = 0; i < 20_000; i++) {
            byte[] data = new byte[16 * 1024];
            data[0] = (byte) i;
            sink = data;
            if (i % 100 == 0) retained[(i / 100) % retained.length] = data;
        }
        int aliveSlots = 0;
        for (byte[] value : retained) if (value != null) aliveSlots++;
        System.out.println("retained slots=" + aliveSlots);
        System.out.println("done");
    }
}
