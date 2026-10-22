import java.nio.charset.StandardCharsets;
import java.util.List;

public final class RedisTextBytes {
    public static void main(String[] args) {
        for (String value : List.of("A", "서울", "😀", "name=서울")) {
            int utf16Units = value.length();
            int codePoints = value.codePointCount(0, value.length());
            int utf8Bytes = value.getBytes(StandardCharsets.UTF_8).length;
            System.out.printf("%s | units=%d | points=%d | bytes=%d%n",
                    value, utf16Units, codePoints, utf8Bytes);
        }
        if ("서울".getBytes(StandardCharsets.UTF_8).length != 6) {
            throw new AssertionError("unexpected UTF-8 size");
        }
        if ("😀".length() != 2) {
            throw new AssertionError("unexpected UTF-16 length");
        }
    }
}
