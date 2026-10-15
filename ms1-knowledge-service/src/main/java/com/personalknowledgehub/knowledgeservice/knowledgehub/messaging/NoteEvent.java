package com.personalknowledgehub.knowledgeservice.knowledgehub.messaging;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.Instant;
import java.util.UUID;

public record NoteEvent(
        @JsonProperty("schema_version") int schemaVersion,
        @JsonProperty("event_id") UUID eventId,
        @JsonProperty("event_type") String eventType,
        @JsonProperty("occurred_at") Instant occurredAt,
        @JsonProperty("note_id") Long noteId
) {

    public static final int CURRENT_SCHEMA_VERSION = 1;

    public static NoteEvent of(NoteEventType type, Long noteId) {
        return new NoteEvent(
                CURRENT_SCHEMA_VERSION,
                UUID.randomUUID(),
                type.eventType(),
                Instant.now(),
                noteId
        );
    }
}
