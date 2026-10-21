package com.mnemo.knowledgeservice.knowledgehub.messaging;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.sql.Timestamp;
import java.util.Optional;
import java.util.UUID;

@Repository
@Transactional(propagation = Propagation.MANDATORY)
public class NoteOutboxStore {
    private final JdbcTemplate jdbc;

    public NoteOutboxStore(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public void enqueue(NoteEvent event, String routingKey) {
        jdbc.update("""
                INSERT INTO note_outbox
                    (event_id, schema_version, event_type, routing_key, occurred_at, note_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """, event.eventId(), event.schemaVersion(), event.eventType(), routingKey,
                Timestamp.from(event.occurredAt()), event.noteId());
    }

    public Optional<Pending> nextForUpdate() {
        return jdbc.query("""
                SELECT * FROM note_outbox WHERE available_at <= clock_timestamp()
                ORDER BY available_at, occurred_at, event_id
                FOR UPDATE SKIP LOCKED LIMIT 1
                """, (rs, row) -> new Pending(new NoteEvent(rs.getInt("schema_version"),
                        rs.getObject("event_id", UUID.class), rs.getString("event_type"),
                        rs.getTimestamp("occurred_at").toInstant(), rs.getObject("note_id", Long.class)),
                        rs.getString("routing_key"), rs.getInt("attempts")))
                .stream().findFirst();
    }

    public void delivered(Pending pending) {
        jdbc.update("DELETE FROM note_outbox WHERE event_id = ?", pending.event().eventId());
    }

    public void retry(Pending pending) {
        long seconds = Math.min(300, 1L << Math.min(9, pending.attempts() + 1));
        jdbc.update("""
                UPDATE note_outbox SET attempts = LEAST(attempts, 1000000) + 1,
                    available_at = clock_timestamp() + (? * interval '1 second')
                WHERE event_id = ?
                """, seconds, pending.event().eventId());
    }

    public record Pending(NoteEvent event, String routingKey, int attempts) {}
}
