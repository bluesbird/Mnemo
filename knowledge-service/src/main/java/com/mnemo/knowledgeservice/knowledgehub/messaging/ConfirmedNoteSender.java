package com.mnemo.knowledgeservice.knowledgehub.messaging;

import org.springframework.amqp.AmqpException;
import org.springframework.amqp.core.MessageDeliveryMode;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.UUID;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

@Component
public class ConfirmedNoteSender {
    private final RabbitTemplate rabbit;
    private final String exchange;

    public ConfirmedNoteSender(RabbitTemplate rabbit, @Value("${app.events.exchange}") String exchange) {
        this.rabbit = rabbit;
        this.exchange = exchange;
    }

    public void send(NoteOutboxStore.Pending pending) throws InterruptedException {
        // Late confirms from earlier attempts must not collide with this attempt's correlation.
        var correlation = new CorrelationData(UUID.randomUUID().toString());
        rabbit.convertAndSend(exchange, pending.routingKey(), pending.event(), message -> {
            message.getMessageProperties().setMessageId(pending.event().eventId().toString());
            message.getMessageProperties().setDeliveryMode(MessageDeliveryMode.PERSISTENT);
            return message;
        }, correlation);
        try {
            var confirm = correlation.getFuture().get(5, TimeUnit.SECONDS);
            // Spring records mandatory returns before completing the confirm future.
            if (!confirm.ack() || correlation.getReturned() != null) {
                throw new AmqpException("Broker rejected or returned outbox event");
            }
        } catch (ExecutionException | TimeoutException ex) {
            throw new AmqpException("Outbox publisher confirmation failed", ex);
        }
    }
}
