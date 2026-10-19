package study;
import javax.sql.DataSource;
import java.sql.*;

/** MySQL-specific duplicate-key classification; not a generic SQL dialect adapter.
 * The event marker and inventory update share ONE local DB transaction.
 * Kafka offsets are deliberately outside this JDBC transaction. */
public final class DedupJdbc {
    public static boolean apply(DataSource ds, String consumer, String eventId,
                                String sku, long inboundQuantity) throws SQLException {
        if (consumer == null || eventId == null || sku == null || inboundQuantity < 0)
            throw new IllegalArgumentException("Invalid inbound event");
        try (Connection c = ds.getConnection()) {
            c.setAutoCommit(false);
            try {
                try (PreparedStatement marker = c.prepareStatement(
                        "INSERT INTO processed_event(consumer_name,event_id) VALUES (?,?)")) {
                    marker.setString(1, consumer);
                    marker.setString(2, eventId);
                    try {
                        marker.executeUpdate();
                    } catch (SQLException duplicate) {
                        if (duplicate.getErrorCode() != 1062) throw duplicate;
                        c.rollback();
                        return false; // Marker already exists: no inventory change.
                    }
                }
                try (PreparedStatement update = c.prepareStatement(
                        "UPDATE stock SET qty = qty + ? WHERE sku = ?")) {
                    update.setLong(1, inboundQuantity);
                    update.setString(2, sku);
                    if (update.executeUpdate() != 1)
                        throw new SQLException("Stock row missing or unexpected update count");
                }
                c.commit();
                return true;
            } catch (SQLException | RuntimeException failure) {
                try { c.rollback(); } catch (SQLException rollback) { failure.addSuppressed(rollback); }
                throw failure;
            }
        }
    }
}
