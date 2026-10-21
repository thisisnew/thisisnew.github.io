public class Deep07 {
    interface Mapper<T> { T map(T value); }
    static class Labels implements Mapper<String> {
        public String map(String value) { return "label:" + value; }
    }
    public static void main(String[] args) {
        Mapper<String> mapper = new Labels();
        System.out.println(mapper.map("42"));
    }
}
