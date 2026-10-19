public class Lesson02 {
    static {
        System.out.println("init");
    }
    static int add(int a, int b) {
        return a + b;
    }
    public static void main(String[] args) {
        System.out.println("main");
        System.out.println(add(20, 22));
    }
}
