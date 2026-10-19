public class Lesson07 {
    static final int LIMIT = 42;
    static final String LABEL = "inbound";
    static String label(int count) {
        return LABEL + ":" + count;
    }
    public static void main(String[] args) {
        System.out.println(label(LIMIT));
        System.out.println("inbound" == LABEL);
    }
}
