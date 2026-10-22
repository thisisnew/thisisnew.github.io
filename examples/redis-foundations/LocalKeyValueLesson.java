import java.util.HashMap;
import java.util.Map;

public final class LocalKeyValueLesson {
    public static void main(String[] args) {
        Map<String, String> names = new HashMap<>();
        names.put("goods:123:name", "배추");
        names.put("goods:124:name", "당근");
        names.put("goods:123:name", "알배기배추");

        if (names.size() != 2) throw new AssertionError("same key should replace");
        if (!"알배기배추".equals(names.get("goods:123:name"))) {
            throw new AssertionError("wrong value");
        }
        if (names.get("goods:999:name") != null) {
            throw new AssertionError("missing key should return null");
        }
        System.out.println(names.get("goods:123:name"));
    }
}
