public class Lesson09 {
    static class Config {
        static final int CONSTANT = 7;
        static final Integer BOXED = 8;
        static int first = readSecond();
        static int second = 42;
        static int readSecond() { return second; }
        static { System.out.println("Config init"); }
    }
    public static void main(String[] args) throws Exception {
        System.out.println(Config.CONSTANT);
        Class.forName("Lesson09$Config", false, Lesson09.class.getClassLoader());
        System.out.println("loaded without init request");
        System.out.println(Config.first);
        System.out.println(Config.second);
        System.out.println(Config.BOXED);
    }
}
