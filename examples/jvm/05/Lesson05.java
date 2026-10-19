public class Lesson05 {
    static int add(int a, int b) {
        int result = a + b;
        return result;
    }
    static int adjust(int quantity) {
        if (quantity > 0) return quantity + 1;
        return 0;
    }
    public static void main(String[] args) {
        System.out.println(add(20, 22));
        System.out.println(adjust(0));
        System.out.println(adjust(3));
    }
}
