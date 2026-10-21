public class Deep09 {
    static class Config {
        static int value = load();
        static int load() {
            System.out.println("loading config");
            throw new IllegalStateException("configuration unavailable");
        }
    }
    public static void main(String[] args) {
        for (int i = 0; i < 2; i++) {
            try {
                System.out.println(Config.value);
            } catch (LinkageError e) {
                System.out.println(e.getClass().getSimpleName());
            }
        }
    }
}
