import java.util.ArrayList;
import java.util.List;
public class Deep10 {
    static class Item {
        int quantity;
        Item(int quantity) { this.quantity = quantity; }
    }
    public static void main(String[] args) {
        final List<Item> original = new ArrayList<>();
        original.add(new Item(10));
        List<Item> copy = new ArrayList<>(original);
        copy.get(0).quantity = 20;
        copy.clear();
        System.out.println("original size=" + original.size());
        System.out.println("quantity=" + original.get(0).quantity);
        List<Item> fixed = List.copyOf(original);
        fixed.get(0).quantity = 30;
        System.out.println("fixed quantity=" + original.get(0).quantity);
    }
}
