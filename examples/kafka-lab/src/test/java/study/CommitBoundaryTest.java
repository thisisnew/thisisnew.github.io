package study;
import static org.junit.jupiter.api.Assertions.*;
import java.util.*;
import org.junit.jupiter.api.Test;
class CommitBoundaryTest {
    @Test void doesNotSkipEarlierFailureWhenLaterRecordCompletes() {
        assertEquals(101, CommitBoundary.next(List.of(100L,101L,102L), Set.of(100L,102L)).orElseThrow());
    }
    @Test void offsetGapsDoNotMeanMissingBusinessRecords() {
        assertEquals(106, CommitBoundary.next(List.of(100L,102L,105L), Set.of(100L,102L,105L)).orElseThrow());
    }
    @Test void noCompletionMeansNoForwardProgress() {
        assertEquals(100, CommitBoundary.next(List.of(100L,101L), Set.of()).orElseThrow());
        assertTrue(CommitBoundary.next(List.of(), Set.of()).isEmpty());
    }
    @Test void rejectsWrongOrderRatherThanInventingSafeBoundary() {
        assertThrows(IllegalArgumentException.class, () -> CommitBoundary.next(List.of(2L,1L), Set.of(1L,2L)));
    }
}
