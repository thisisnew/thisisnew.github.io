public class Lesson10 {
    static final class Box {
        int quantity;
        Box(int quantity) { this.quantity = quantity; }
    }
    static void change(Box box) {
        box.quantity = 42;
        box = new Box(99);
    }
    static int temporary(int value) {
        Box box = new Box(value);
        return box.quantity + 1;
    }
    public static void main(String[] args) {
        Box first = new Box(1);
        Box second = first;
        change(second);
        System.out.println(first.quantity);
        System.out.println(first == second);
        System.out.println(temporary(41));
    }
}
