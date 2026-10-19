public class Lesson13 {
    static volatile byte[] sink;
    public static void main(String[] args) {
        byte[][] retained = new byte[8][];
        for (int i = 0; i < 240; i++) {
            byte[] data = new byte[700 * 1024];
            data[0] = (byte) i;
            retained[i % retained.length] = data;
            sink = data;
        }
        System.out.println("retained=" + retained.length);
        System.out.println("last=" + sink[0]);
    }
}
