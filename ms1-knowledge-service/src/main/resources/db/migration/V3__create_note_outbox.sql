CREATE TABLE note_outbox (
    event_id UUID PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    routing_key VARCHAR(64) NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    note_id BIGINT,
    attempts INTEGER NOT NULL DEFAULT 0,
    available_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_note_outbox_due ON note_outbox (available_at, occurred_at, event_id);
