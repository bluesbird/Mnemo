package com.mnemo.knowledgeservice;

import com.mnemo.knowledgeservice.knowledgehub.messaging.*;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageDeliveryMode;
import org.springframework.amqp.core.MessagePostProcessor;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.core.ReturnedMessage;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

import java.util.ArrayList;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class ConfirmedNoteSenderTests {
    @Test
    void acceptsAckRejectsNackAndReturnsAndUsesPersistentStableMessageIdentity() throws Exception {
        var rabbit = mock(RabbitTemplate.class);
        var sender = new ConfirmedNoteSender(rabbit, "notes.events");
        var event = NoteEvent.of(NoteEventType.CREATED, 1L);
        var pending = new NoteOutboxStore.Pending(event, "note.created", 0);
        var correlations = new ArrayList<String>();
        doAnswer(call -> {
            var processor = call.getArgument(3, MessagePostProcessor.class);
            var message = processor.postProcessMessage(new Message(new byte[0], new MessageProperties()));
            assertEquals(MessageDeliveryMode.PERSISTENT, message.getMessageProperties().getDeliveryMode());
            assertEquals(event.eventId().toString(), message.getMessageProperties().getMessageId());
            var correlation = call.getArgument(4, CorrelationData.class);
            correlations.add(correlation.getId());
            int attempt = correlations.size();
            if (attempt == 3) {
                correlation.setReturned(new ReturnedMessage(message, 312, "NO_ROUTE", "notes.events", "note.created"));
            }
            correlation.getFuture().complete(new CorrelationData.Confirm(attempt != 2, null));
            return null;
        }).when(rabbit).convertAndSend(eq("notes.events"), eq("note.created"), eq(event),
                any(MessagePostProcessor.class), any(CorrelationData.class));
        sender.send(pending);
        assertThrows(AmqpException.class, () -> sender.send(pending));
        assertThrows(AmqpException.class, () -> sender.send(pending));
        assertEquals(3, correlations.stream().distinct().count());
    }

    @Test
    void missingConfirmTimesOutAndConnectionFailuresPropagate() {
        var rabbit = mock(RabbitTemplate.class);
        var sender = new ConfirmedNoteSender(rabbit, "notes.events");
        var pending = new NoteOutboxStore.Pending(NoteEvent.of(NoteEventType.CREATED, 1L), "note.created", 0);
        assertThrows(AmqpException.class, () -> sender.send(pending));
        doThrow(new AmqpException("Disconnected")).when(rabbit).convertAndSend(anyString(), anyString(),
                any(Object.class), any(MessagePostProcessor.class), any(CorrelationData.class));
        assertThrows(AmqpException.class, () -> sender.send(pending));
    }
}
