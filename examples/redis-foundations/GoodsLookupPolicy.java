import java.util.List;

public final class GoodsLookupPolicy {
    private static final int MAX_IDS_PER_REQUEST = 100;

    public static List<Long> validate(List<Long> goodsIds) {
        if (goodsIds == null || goodsIds.isEmpty()) {
            throw new IllegalArgumentException("at least one goods ID is required");
        }
        if (goodsIds.size() > MAX_IDS_PER_REQUEST) {
            throw new IllegalArgumentException("too many goods IDs");
        }
        for (Long id : goodsIds) {
            if (id == null || id <= 0) {
                throw new IllegalArgumentException("invalid goods ID");
            }
        }
        return List.copyOf(goodsIds);
    }
}
