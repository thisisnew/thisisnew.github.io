public class Lesson01 {
    public static void main(String[] args) {
        System.out.println("java=" + System.getProperty("java.version"));
        System.out.println("vm=" + System.getProperty("java.vm.name"));
        System.out.println("os=" + System.getProperty("os.name"));
        System.out.println("arch=" + System.getProperty("os.arch"));
        System.out.println("sum=" + (20 + 22));
    }
}
