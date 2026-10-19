public class Lesson04 {
    int base = 10;
    int add(int quantity) {
        int result = base + quantity;
        return result;
    }
    static int call(Lesson04 target) {
        return target.add(32);
    }
    public static void main(String[] args) {
        Lesson04 service = new Lesson04();
        System.out.println(call(service));
    }
}
