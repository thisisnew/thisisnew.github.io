public class Walkthrough10 {
    static final class Box {
        int quantity;
        Box(int quantity) { this.quantity = quantity; }
    }
    public static void main(String[] args) {
        Box a = new Box(0);
        a.quantity = 10;
        Box b = a;
        b.quantity = 42;
        b = new Box(0);
        System.out.println(a.quantity);
        System.out.println(b.quantity);
        System.out.println(a == b);
    }
}
