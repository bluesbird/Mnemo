package com.mnemo.knowledgeservice.knowledgehub.messaging;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Component
public class NoteEventPublisher {

    private static final Logger logger = LoggerFactory.getLogger(NoteEventPublisher.class);

    private final NoteOutboxStore outbox;

    public NoteEventPublisher(NoteOutboxStore outbox) {
        this.outbox = outbox;
    }

    @Transactional(propagation = Propagation.MANDATORY)
    public void publish(NoteEventType type, Long noteId) {
        NoteEvent event = NoteEvent.of(type, noteId);
        outbox.enqueue(event, type.routingKey());
        logger.info("Queued {} for note {} (event {})", type.eventType(), noteId, event.eventId());
    }
}
