public class Walkthrough05 {
    static int subtract(int left, int right) { return left - right; }
    static int grouped(int a, int b, int c) { return (a + b) * c; }
    static int precedence(int a, int b, int c) { return a + b * c; }
    public static void main(String[] args) {
        System.out.println(subtract(10, 3));
        System.out.println(grouped(2, 4, 6));
        System.out.println(precedence(2, 4, 6));
    }
}
