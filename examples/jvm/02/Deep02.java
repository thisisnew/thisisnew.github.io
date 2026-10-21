public class Deep02 {
    static class LabelPrinter {
        static { System.out.println("printer initialized"); }
        static String print(int id) { return "label=" + id; }
    }
    public static void main(String[] args) throws Exception {
        System.out.println("main entered");
        Class.forName("Deep02$LabelPrinter", false, Deep02.class.getClassLoader());
        System.out.println("type found");
        System.out.println(LabelPrinter.print(42));
        System.out.println(LabelPrinter.print(43));
    }
}
