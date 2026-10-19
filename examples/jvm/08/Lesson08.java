import java.nio.file.Files;
import java.nio.file.Path;

public class Lesson08 {
    public static class Token { }
    static final class IsolatedLoader extends ClassLoader {
        Class<?> define(byte[] bytes) {
            return defineClass("Lesson08$Token", bytes, 0, bytes.length);
        }
    }
    public static void main(String[] args) throws Exception {
        System.out.println("String loader=" + String.class.getClassLoader());
        System.out.println("app loader=" + Lesson08.class.getClassLoader());
        byte[] bytes = Files.readAllBytes(Path.of("Lesson08$Token.class"));
        Class<?> first = new IsolatedLoader().define(bytes);
        Class<?> second = new IsolatedLoader().define(bytes);
        System.out.println("same name=" + first.getName().equals(second.getName()));
        System.out.println("same type=" + (first == second));
        System.out.println("assignable=" + first.isAssignableFrom(second));
    }
}
