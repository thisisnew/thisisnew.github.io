public final class RedisBucketAddress {
    private static final long BUCKET_SIZE = 100;

    record Address(String key, String field) {}

    static Address forId(long id) {
        if (id <= 0) throw new IllegalArgumentException("ID must be positive");
        long bucket = id / BUCKET_SIZE;
        long field = id % BUCKET_SIZE;
        return new Address("goods:bucket:v1:" + bucket, Long.toString(field));
    }

    public static void main(String[] args) {
        Address a = forId(1234);
        Address b = forId(1299);
        Address c = forId(1300);
        if (!a.key().equals(b.key())) throw new AssertionError("same bucket");
        if (a.field().equals(b.field())) throw new AssertionError("distinct fields");
        if (a.key().equals(c.key())) throw new AssertionError("next bucket");
        if (!a.field().equals("34")) throw new AssertionError("wrong field");
        System.out.println(a);
        System.out.println(c);
    }
}
