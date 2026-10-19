public class Lesson03 {
    static final class Box {
        int quantity;
    }
    static final Box shared = new Box();
    static int inspect(Box box) {
        int adjustment = 2;
        return box.quantity + adjustment;
    }
    public static void main(String[] args) {
        Box localRef = shared;
        localRef.quantity = 40;
        System.out.println(inspect(localRef));
        System.out.println(shared == localRef);
    }
}
