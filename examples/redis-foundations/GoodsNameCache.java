import java.time.Duration;
import java.util.Objects;
import org.springframework.data.redis.core.StringRedisTemplate;

public final class GoodsNameCache {
    private final StringRedisTemplate redis;
    private final Duration ttl;

    public GoodsNameCache(StringRedisTemplate redis, Duration ttl) {
        this.redis = Objects.requireNonNull(redis);
        this.ttl = Objects.requireNonNull(ttl);
        if (ttl.isNegative() || ttl.isZero() || ttl.toMillis() == 0) {
            throw new IllegalArgumentException("TTL must be at least one millisecond");
        }
    }

    public void put(long goodsId, String name) {
        if (goodsId <= 0) throw new IllegalArgumentException("invalid goodsId");
        redis.opsForValue().set(key(goodsId), Objects.requireNonNull(name), ttl);
    }

    public String get(long goodsId) {
        if (goodsId <= 0) throw new IllegalArgumentException("invalid goodsId");
        return redis.opsForValue().get(key(goodsId));
    }

    private String key(long goodsId) {
        return "goods:name:v1:" + goodsId;
    }
}
