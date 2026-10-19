package study;
import static org.junit.jupiter.api.Assertions.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
class FrameTest {
    @Test void partialLengthHeaderDoesNotConsumeInput() {
        var in = ByteBuffer.wrap(new byte[]{0,0});
        assertTrue(TopicExamples.tryFrame(in).isEmpty());
        assertEquals(0, in.position());
    }
    @Test void partialBodyWaitsForMoreBytesWithoutLosingLength() {
        var in = ByteBuffer.allocate(10).putInt(10).put((byte)1).flip();
        assertTrue(TopicExamples.tryFrame(in).isEmpty());
        assertEquals(0, in.position());
    }
    @Test void concatenatedFramesUseUtf8ByteLengthNotCharacterCount() {
        byte[] korean = "입고".getBytes(StandardCharsets.UTF_8);
        var in = ByteBuffer.allocate(100).putInt(korean.length).put(korean)
                .putInt(1).put((byte)7).flip();
        assertArrayEquals(korean, TopicExamples.tryFrame(in).orElseThrow());
        assertArrayEquals(new byte[]{7}, TopicExamples.tryFrame(in).orElseThrow());
        assertFalse(in.hasRemaining());
    }
}
