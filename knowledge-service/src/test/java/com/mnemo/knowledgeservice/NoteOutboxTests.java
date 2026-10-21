package com.mnemo.knowledgeservice;

import com.mnemo.knowledgeservice.knowledgehub.application.DatabaseResetService;
import com.mnemo.knowledgeservice.knowledgehub.application.NoteService;
import com.mnemo.knowledgeservice.knowledgehub.messaging.*;
import com.mnemo.knowledgeservice.knowledgehub.persistence.NoteRepository;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.AmqpException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.IllegalTransactionStateException;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@SpringBootTest(properties = "app.events.outbox.enabled=false")
class NoteOutboxTests {
    @Autowired NoteService notes;
    @Autowired NoteRepository repository;
    @Autowired DatabaseResetService reset;
    @Autowired NoteEventPublisher publisher;
    @Autowired NoteOutboxStore store;
    @Autowired JdbcTemplate jdbc;
    @Autowired PlatformTransactionManager manager;

    @BeforeEach
    @AfterEach
    void cleanup() {
        jdbc.update("DELETE FROM note_outbox");
        repository.deleteAllInBatch();
    }

    @Test
    void commitsLifecycleAndResetEventsWithNotes() {
        var note = notes.addNote("Title", "Content");
        notes.updateNote(note.getId(), "Updated", "Changed");
        notes.deleteNote(note.getId());
        assertEquals(0, repository.count());
        assertEquals(List.of("NoteCreated", "NoteDeleted", "NoteUpdated"),
                jdbc.queryForList("SELECT event_type FROM note_outbox ORDER BY event_type", String.class));
        assertEquals(10, reset.reset());
        assertEquals(4, pendingCount());
        assertEquals(1, jdbc.queryForObject(
                "SELECT count(*) FROM note_outbox WHERE event_type='IndexRebuildRequested' AND note_id IS NULL",
                Integer.class));
    }

    @Test
    void rollsBackNoteAndEventTogetherForCreateUpdateDeleteAndReset() {
        var transaction = new TransactionTemplate(manager);
        transaction.executeWithoutResult(status -> {
            notes.addNote("Rolled back", "Content");
            status.setRollbackOnly();
        });
        assertEquals(0, repository.count());
        assertEquals(0, pendingCount());
        var note = notes.addNote("Original", "Content");
        transaction.executeWithoutResult(status -> {
            notes.updateNote(note.getId(), "Changed", "Changed");
            notes.deleteNote(note.getId());
            reset.reset();
            status.setRollbackOnly();
        });
        assertEquals("Original", notes.getNoteById(note.getId()).getTitle());
        assertEquals(1, repository.count());
        assertEquals(1, pendingCount());
        assertThrows(IllegalTransactionStateException.class,
                () -> publisher.publish(NoteEventType.CREATED, note.getId()));
    }

    @Test
    void enqueueFailureRollsBackTheNoteWrite() {
        jdbc.execute("ALTER TABLE note_outbox ADD CONSTRAINT reject_test_event CHECK (event_type <> 'NoteCreated')");
        try {
            assertThrows(org.springframework.dao.DataIntegrityViolationException.class,
                    () -> notes.addNote("Must roll back", "Content"));
            assertEquals(0, repository.count());
            assertEquals(0, pendingCount());
        } finally {
            jdbc.execute("ALTER TABLE note_outbox DROP CONSTRAINT reject_test_event");
        }
    }

    @Test
    void failedDeliveryBacksOffThenRetriesTheSameEventAndDeletesOnlyOnSuccess() throws Exception {
        notes.addNote("Title", "Content");
        var sender = mock(ConfirmedNoteSender.class);
        var dispatcher = new NoteOutboxDispatcher(store, sender, manager);
        doThrow(new AmqpException("Broker unavailable")).doNothing().when(sender).send(any());
        dispatcher.dispatch();
        assertEquals(1, pendingCount());
        assertEquals(1, jdbc.queryForObject("SELECT attempts FROM note_outbox", Integer.class));
        assertTrue(jdbc.queryForObject(
                "SELECT available_at > clock_timestamp() FROM note_outbox", Boolean.class));
        dispatcher.dispatch();
        verify(sender, times(1)).send(any());
        jdbc.update("UPDATE note_outbox SET available_at=clock_timestamp()");
        dispatcher.dispatch();
        var attempts = org.mockito.ArgumentCaptor.forClass(NoteOutboxStore.Pending.class);
        verify(sender, times(2)).send(attempts.capture());
        assertEquals(attempts.getAllValues().getFirst().event(), attempts.getValue().event());
        assertEquals(0, pendingCount());
    }

    @Test
    void rollbackAfterBrokerAcceptanceLeavesEventEligibleForRedelivery() {
        notes.addNote("Title", "Content");
        var transaction = new TransactionTemplate(manager);
        var event = transaction.execute(status -> {
            var pending = store.nextForUpdate().orElseThrow();
            store.delivered(pending);
            status.setRollbackOnly();
            return pending.event();
        });
        assertEquals(1, pendingCount());
        transaction.executeWithoutResult(status -> {
            assertEquals(event, store.nextForUpdate().orElseThrow().event());
        });
    }

    @Test
    void concurrentWorkersSkipLockedEventsAndUncommittedEventsAreInvisible() throws Exception {
        var transaction = new TransactionTemplate(manager);
        var locked = new CountDownLatch(1);
        var release = new CountDownLatch(1);
        notes.addNote("Title", "Content");
        try (var executor = Executors.newSingleThreadExecutor()) {
            var worker = executor.submit(() -> transaction.executeWithoutResult(status -> {
                assertTrue(store.nextForUpdate().isPresent());
                publisher.publish(NoteEventType.INDEX_REBUILD_REQUESTED, null);
                locked.countDown();
                try {
                    assertTrue(release.await(10, TimeUnit.SECONDS));
                } catch (InterruptedException ex) {
                    Thread.currentThread().interrupt();
                    throw new IllegalStateException(ex);
                }
            }));
            try {
                assertTrue(locked.await(10, TimeUnit.SECONDS));
                transaction.executeWithoutResult(status -> assertTrue(store.nextForUpdate().isEmpty()));
            } finally {
                release.countDown();
            }
            worker.get(10, TimeUnit.SECONDS);
        }
        assertEquals(2, pendingCount());
    }

    private int pendingCount() {
        return jdbc.queryForObject("SELECT count(*) FROM note_outbox", Integer.class);
    }
}
