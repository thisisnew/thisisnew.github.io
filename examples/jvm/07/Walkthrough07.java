public class Walkthrough07 {
    static long sum(String label, int[] values) {
        long total = 0;
        for (int value : values) total += value;
        return total;
    }
    public static void main(String[] args) {
        System.out.println(sum("inbound", new int[]{1, 2}));
    }
}
