import java.util.List;
public class Deep06 {
    static String first(List<String> names) {
        return names.get(0);
    }
    public static void main(String[] args) {
        System.out.println(first(List.of("inbound")));
    }
}
