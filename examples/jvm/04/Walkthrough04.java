public class Walkthrough04 {
    long base = 10;
    long add(long quantity) {
        long result = base + quantity;
        return result;
    }
    public static void main(String[] args) {
        System.out.println(new Walkthrough04().add(32L));
    }
}
