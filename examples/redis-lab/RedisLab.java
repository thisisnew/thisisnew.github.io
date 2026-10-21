import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Deliberately small RESP2 teaching client, NOT a production client. */
public class RedisLab {
    record ErrorReply(String message) {}
    static final class Resp implements AutoCloseable {
        final Socket socket = new Socket();
        final InputStream in;
        final OutputStream out;
        Resp(int port, String password) throws IOException {
            socket.connect(new InetSocketAddress("127.0.0.1", port), 2000);
            socket.setSoTimeout(3000);
            in = new BufferedInputStream(socket.getInputStream());
            out = new BufferedOutputStream(socket.getOutputStream());
            eq("OK", command("AUTH", password), "isolated server authentication");
        }
        void write(String... args) throws IOException {
            out.write(("*" + args.length + "\r\n").getBytes(StandardCharsets.US_ASCII));
            for (String arg : args) {
                byte[] data = arg.getBytes(StandardCharsets.UTF_8);
                out.write(("$" + data.length + "\r\n").getBytes(StandardCharsets.US_ASCII));
                out.write(data); out.write('\r'); out.write('\n');
            }
        }
        Object command(String... args) throws IOException { write(args); out.flush(); return read(); }
        String line() throws IOException {
            ByteArrayOutputStream b = new ByteArrayOutputStream();
            for (int c; (c = in.read()) != -1;) {
                if (c == '\r') { if (in.read() != '\n') throw new IOException("bad CRLF"); return b.toString(StandardCharsets.UTF_8); }
                b.write(c); if (b.size() > 65536) throw new IOException("oversized line");
            }
            throw new EOFException();
        }
        Object read() throws IOException {
            int type = in.read();
            return switch (type) {
                case '+' -> line();
                case '-' -> new ErrorReply(line());
                case ':' -> Long.parseLong(line());
                case '$' -> {
                    int n = Integer.parseInt(line());
                    if (n == -1) yield null;
                    if (n < 0 || n > 1_000_000) throw new IOException("bad bulk length");
                    byte[] bytes = in.readNBytes(n);
                    if (bytes.length != n || in.read() != '\r' || in.read() != '\n') throw new EOFException();
                    yield new String(bytes, StandardCharsets.UTF_8);
                }
                case '*' -> {
                    int n = Integer.parseInt(line());
                    if (n == -1) yield null;
                    if (n < 0 || n > 10000) throw new IOException("bad array length");
                    List<Object> values = new ArrayList<>();
                    for (int i = 0; i < n; i++) values.add(read());
                    yield values;
                }
                default -> throw new IOException("unsupported RESP type: " + type);
            };
        }
        public void close() throws IOException { socket.close(); }
    }
    static void eq(Object expected, Object actual, String label) {
        if (!Objects.equals(expected, actual)) throw new AssertionError(label + ": expected=" + expected + ", actual=" + actual);
    }
    static void check(boolean condition, String label) { if (!condition) throw new AssertionError(label); }
    static void pass(String name) { System.out.println("PASS " + name); }
    static final String STOCK = """
        local q = tonumber(ARGV[1])
        if not q or q < 1 or q > 1000000 or q ~= math.floor(q) then return redis.error_reply('BAD_QUANTITY') end
        local old = redis.call('GET', KEYS[2])
        if old then
          local sep = string.find(old, ':')
          if string.sub(old, 1, sep-1) ~= ARGV[1] then return redis.error_reply('TOKEN_REUSED_WITH_DIFFERENT_QUANTITY') end
          return tonumber(string.sub(old, sep+1))
        end
        local s = tonumber(redis.call('GET', KEYS[1]))
        if not s or s < 0 or s > 1000000 or s ~= math.floor(s) then return redis.error_reply('BAD_STOCK') end
        if s < q then return -1 end
        local remaining = s - q
        redis.call('MSET', KEYS[1], tostring(remaining), KEYS[2], ARGV[1] .. ':' .. tostring(remaining))
        redis.call('EXPIRE', KEYS[2], 60)
        return remaining
        """;
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("Use check-redis-lab.py, not an existing server");
        String k = "learning:{" + UUID.randomUUID() + "}:";
        try (Resp r = new Resp(Integer.parseInt(args[0]), args[1])) {
            eq("PONG", r.command("PING"), "ping");
            eq("OK", r.command("SET", k+"text", "한글 Redis"), "set");
            eq("한글 Redis", r.command("GET", k+"text"), "utf8 get");
            eq(-1L, r.command("TTL", k+"text"), "persistent TTL");
            eq(-2L, r.command("TTL", k+"missing"), "missing TTL");
            eq("OK", r.command("SET", k+"ttl", "temporary", "PX", "250"), "set px");
            long ttl = (Long) r.command("PTTL", k+"ttl");
            check(ttl >= 0 && ttl <= 250, "PTTL is bounded");
            long deadline = System.nanoTime() + 3_000_000_000L;
            while (r.command("GET", k+"ttl") != null && System.nanoTime() < deadline) Thread.sleep(20);
            eq(null, r.command("GET", k+"ttl"), "eventual expiration");
            eq(1L, r.command("INCR", k+"counter"), "incr missing");
            pass("get-set-utf8-ttl-incr");

            // Pipeline means sending before reading, not an atomic transaction.
            r.write("INCR", k+"counter"); r.write("INCR", k+"counter"); r.write("GET", k+"counter"); r.out.flush();
            eq(2L, r.read(), "pipeline 1"); eq(3L, r.read(), "pipeline 2"); eq("3", r.read(), "pipeline 3");
            pass("pipeline-ordered-replies");

            eq("OK", r.command("MULTI"), "multi");
            eq("QUEUED", r.command("SET", k+"tx", "not-a-number"), "queue set");
            eq("QUEUED", r.command("INCR", k+"tx"), "queue incr");
            eq("QUEUED", r.command("SET", k+"after", "still-executed"), "queue after");
            List<?> result = (List<?>) r.command("EXEC");
            eq("OK", result.get(0), "first transaction result");
            check(result.get(1) instanceof ErrorReply, "runtime error is inside EXEC reply");
            eq("OK", result.get(2), "last command still executes");
            eq("not-a-number", r.command("GET", k+"tx"), "no rollback");
            eq("still-executed", r.command("GET", k+"after"), "continued execution");
            pass("multi-exec-runtime-error-no-rollback");

            eq("OK", r.command("SET", k+"stock", "5"), "stock init");
            eq(3L, r.command("EVAL", STOCK, "2", k+"stock", k+"order-a", "2"), "reserve");
            eq(3L, r.command("EVAL", STOCK, "2", k+"stock", k+"order-a", "2"), "same business token retry");
            check(r.command("EVAL", STOCK, "2", k+"stock", k+"order-a", "1") instanceof ErrorReply, "reject conflicting retry");
            eq(-1L, r.command("EVAL", STOCK, "2", k+"stock", k+"order-b", "4"), "no oversell");
            check(r.command("EVAL", STOCK, "2", k+"stock", k+"order-c", "-1") instanceof ErrorReply, "invalid quantity");
            eq("3", r.command("GET", k+"stock"), "stock unchanged by rejected requests");
            pass("lua-stock-guard-idempotent-token");

            Object failure = r.command("EVAL", "redis.call('SET',KEYS[1],'written'); return redis.call('INCR',KEYS[1])", "1", k+"lua-error");
            check(failure instanceof ErrorReply, "lua runtime failure");
            eq("written", r.command("GET", k+"lua-error"), "Lua also has no automatic rollback");
            pass("lua-runtime-error-no-rollback");
        }
    }
}
