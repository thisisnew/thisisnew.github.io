public class Deep04 {
    static int compute() {
        int quantity = 10;
        try {
            return quantity;
        } finally {
            quantity = 20;
            System.out.println("finally=" + quantity);
        }
    }
    static int[] reference() {
        int[] quantity = {10};
        try {
            return quantity;
        } finally {
            quantity[0] = 20;
        }
    }
    public static void main(String[] args) {
        System.out.println("result=" + compute());
        System.out.println("element=" + reference()[0]);
    }
}
