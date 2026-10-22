import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;

public final class BackupChecksumLesson {
    static String sha256(Path file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[64 * 1024];
        try (InputStream input = Files.newInputStream(file)) {
            int read;
            while ((read = input.read(buffer)) != -1) {
                digest.update(buffer, 0, read);
            }
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    static void verify(Path file, String expectedHex) throws Exception {
        if (!expectedHex.matches("[0-9a-f]{64}")) {
            throw new IllegalArgumentException("expected SHA-256 must be lowercase hex");
        }
        String actual = sha256(file);
        if (!actual.equals(expectedHex)) {
            throw new IllegalStateException("checksum mismatch");
        }
    }

    public static void main(String[] args) throws Exception {
        Path directory = Files.createTempDirectory("redis-checksum-lesson-");
        Path file = directory.resolve("teaching-data.txt");
        try {
            Files.writeString(file, "snapshot-generation-1", StandardCharsets.UTF_8);
            String expected = sha256(file);
            verify(file, expected);
            System.out.println("unchanged copy: passed");
            Files.writeString(file, "snapshot-generation-2", StandardCharsets.UTF_8);
            boolean detected = false;
            try {
                verify(file, expected);
            } catch (IllegalStateException mismatch) {
                detected = true;
            }
            if (!detected) throw new AssertionError("changed bytes were not detected");
            System.out.println("changed bytes: detected");
        } finally {
            Files.deleteIfExists(file);
            Files.deleteIfExists(directory);
        }
    }
}
