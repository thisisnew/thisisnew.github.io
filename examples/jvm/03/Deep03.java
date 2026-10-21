import java.lang.management.ManagementFactory;
import java.lang.management.BufferPoolMXBean;
import java.nio.ByteBuffer;
public class Deep03 {
    public static void main(String[] args) {
        ByteBuffer buffer = ByteBuffer.allocateDirect(4 * 1024 * 1024);
        buffer.putInt(0, 42);
        for (BufferPoolMXBean pool : ManagementFactory.getPlatformMXBeans(BufferPoolMXBean.class)) {
            if (pool.getName().equals("direct")) {
                System.out.println("capacity=" + pool.getTotalCapacity());
                System.out.println("used=" + pool.getMemoryUsed());
            }
        }
        System.out.println("value=" + buffer.getInt(0));
    }
}
