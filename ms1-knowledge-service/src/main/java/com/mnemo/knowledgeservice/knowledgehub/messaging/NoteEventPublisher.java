package com.mnemo.knowledgeservice.knowledgehub.messaging;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class NoteEventPublisher {

    private static final Logger logger = LoggerFactory.getLogger(NoteEventPublisher.class);

    private final RabbitTemplate rabbitTemplate;
    private final String exchange;

    public NoteEventPublisher(
            RabbitTemplate rabbitTemplate,
            @Value("${app.events.exchange}") String exchange
    ) {
        this.rabbitTemplate = rabbitTemplate;
        this.exchange = exchange;
    }

    // A broker outage must not fail note writes; MS2 reconcile recovers missed events.
    public void publish(NoteEventType type, Long noteId) {
        NoteEvent event = NoteEvent.of(type, noteId);
        try {
            rabbitTemplate.convertAndSend(exchange, type.routingKey(), event);
            logger.info("Published {} for note {} (event {})", type.eventType(), noteId, event.eventId());
        } catch (AmqpException e) {
            logger.error("Failed to publish {} for note {}; run MS2 reconcile to recover",
                    type.eventType(), noteId, e);
        }
    }
}
