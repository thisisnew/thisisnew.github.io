public class Deep05 {
    static long tooLate(int boxes, int perBox) {
        return (long) (boxes * perBox);
    }
    static long early(int boxes, int perBox) {
        return (long) boxes * perBox;
    }
    public static void main(String[] args) {
        System.out.println(tooLate(50_000, 50_000));
        System.out.println(early(50_000, 50_000));
        try {
            System.out.println(Math.multiplyExact(50_000, 50_000));
        } catch (ArithmeticException e) {
            System.out.println("overflow detected");
        }
    }
}
