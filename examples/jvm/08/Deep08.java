public class Deep08 {
    public static class Item { }
    public static void main(String[] args) throws Exception {
        ClassLoader parent = Deep08.class.getClassLoader();
        ClassLoader a = new ClassLoader(parent) { };
        ClassLoader b = new ClassLoader(parent) { };
        Class<?> x = a.loadClass("Deep08$Item");
        Class<?> y = b.loadClass("Deep08$Item");
        System.out.println("same=" + (x == y));
        System.out.println("definedByParent=" + (x.getClassLoader() == parent));
        System.out.println("requesterIsDefiner=" + (x.getClassLoader() == a));
    }
}
