public class Lesson06 {
    static final class Box {
        private final int value;
        Box(int value) { this.value = value; }
        int read() { return value; }
    }
    static int first(int[] values) {
        return values[0];
    }
    public static void main(String[] args) {
        Box box = new Box(7);
        int[] values = {box.read(), 9};
        System.out.println(first(values));
        try {
            first(new int[0]);
        } catch (ArrayIndexOutOfBoundsException e) {
            System.out.println("empty");
        }
    }
}
