import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.springframework.data.redis.core.StringRedisTemplate;

public final class GoodsHashCache {
    private final StringRedisTemplate redis;

    public GoodsHashCache(StringRedisTemplate redis) {
        this.redis = Objects.requireNonNull(redis);
    }

    public void put(long goodsId, String name, String center) {
        if (goodsId <= 0) throw new IllegalArgumentException("invalid ID");
        Map<String, String> fields = Map.of(
                "name", Objects.requireNonNull(name),
                "center", Objects.requireNonNull(center));
        redis.<String, String>opsForHash().putAll(key(goodsId), fields);
    }

    public List<String> namesAndCenters(long goodsId) {
        if (goodsId <= 0) throw new IllegalArgumentException("invalid ID");
        return redis.<String, String>opsForHash().multiGet(
                key(goodsId), List.of("name", "center"));
    }

    private String key(long goodsId) {
        return "goods:profile:v1:" + goodsId;
    }
}
