package com.mnemo.knowledgeservice.knowledgehub.messaging;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpException;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;

@Component
@EnableScheduling
@ConditionalOnProperty(name = "app.events.outbox.enabled", havingValue = "true", matchIfMissing = true)
public class NoteOutboxDispatcher {
    private static final Logger logger = LoggerFactory.getLogger(NoteOutboxDispatcher.class);
    private final NoteOutboxStore store;
    private final ConfirmedNoteSender sender;
    private final TransactionTemplate transaction;

    public NoteOutboxDispatcher(NoteOutboxStore store, ConfirmedNoteSender sender,
                               PlatformTransactionManager manager) {
        this.store = store;
        this.sender = sender;
        this.transaction = new TransactionTemplate(manager);
        transaction.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
    }

    @Scheduled(fixedDelayString = "${app.events.outbox.poll-delay-ms:1000}")
    public void dispatch() {
        for (int i = 0; i < 20 && !Thread.currentThread().isInterrupted(); i++) {
            if (!Boolean.TRUE.equals(transaction.execute(status -> deliverNext()))) {
                break;
            }
        }
    }

    private boolean deliverNext() {
        var next = store.nextForUpdate();
        if (next.isEmpty()) {
            return false;
        }
        var pending = next.get();
        try {
            sender.send(pending);
        } catch (AmqpException ex) {
            store.retry(pending);
            logger.warn("Outbox event {} retained for retry (attempt {}, {})",
                    pending.event().eventId(), pending.attempts() + 1, ex.getClass().getSimpleName());
            return false;
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            logger.warn("Outbox delivery interrupted; event {} remains pending", pending.event().eventId());
            return false;
        }
        store.delivered(pending);
        logger.info("Delivered {} for note {} (event {})",
                pending.event().eventType(), pending.event().noteId(), pending.event().eventId());
        return true;
    }
}
