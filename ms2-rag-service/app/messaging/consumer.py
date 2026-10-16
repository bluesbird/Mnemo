import logging
import threading
from collections.abc import Callable

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas import NoteEvent

logger = logging.getLogger(__name__)

SUPPORTED_EVENT_TYPES = {"NoteCreated", "NoteUpdated", "NoteDeleted"}
ROUTING_KEY_PATTERN = "note.*"
MAX_RECONNECT_DELAY_SECONDS = 30.0


class NoteEventConsumer:
    """Consumes note events on a single thread, so events are processed serially.

    Events are change triggers only: the handler fetches the current note state, which
    makes duplicate and out-of-order deliveries harmless.
    """

    def __init__(self, settings: Settings, handler: Callable[[int], object]) -> None:
        self._settings = settings
        self._handler = handler
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._connection: pika.BlockingConnection | None = None
        self._channel: BlockingChannel | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="note-event-consumer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        connection, channel = self._connection, self._channel
        if connection is not None and channel is not None and connection.is_open:
            try:
                connection.add_callback_threadsafe(channel.stop_consuming)
            except Exception:  # noqa: BLE001
                logger.debug("Consumer connection already closed during shutdown")
        if self._thread is not None:
            self._thread.join(timeout=10)

    def _run(self) -> None:
        delay = 1.0
        while not self._stop.is_set():
            try:
                self._consume()
                delay = 1.0
            except Exception as exc:  # noqa: BLE001
                logger.warning("RabbitMQ consumer disconnected (%s); retrying in %.0fs", exc, delay)
            if self._stop.wait(delay):
                break
            delay = min(delay * 2, MAX_RECONNECT_DELAY_SECONDS)

    def _consume(self) -> None:
        connection = pika.BlockingConnection(self._connection_parameters())
        try:
            channel = connection.channel()
            self._declare_topology(channel)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=self._settings.events_queue, on_message_callback=self._on_message)
            self._connection, self._channel = connection, channel
            if self._stop.is_set():
                return
            logger.info(
                "Consuming note events from queue '%s' (exchange '%s')",
                self._settings.events_queue,
                self._settings.events_exchange,
            )
            channel.start_consuming()
        finally:
            self._connection, self._channel = None, None
            if connection.is_open:
                connection.close()

    def _connection_parameters(self) -> pika.ConnectionParameters:
        settings = self._settings
        return pika.ConnectionParameters(
            host=settings.rabbitmq_host,
            port=settings.rabbitmq_port,
            credentials=pika.PlainCredentials(settings.rabbitmq_username, settings.rabbitmq_password),
            heartbeat=settings.rabbitmq_heartbeat_seconds,
        )

    def _declare_topology(self, channel: BlockingChannel) -> None:
        settings = self._settings
        channel.exchange_declare(exchange=settings.events_exchange, exchange_type="topic", durable=True)
        channel.exchange_declare(
            exchange=settings.events_dead_letter_exchange, exchange_type="fanout", durable=True
        )
        channel.queue_declare(queue=settings.events_dead_letter_queue, durable=True)
        channel.queue_bind(
            queue=settings.events_dead_letter_queue, exchange=settings.events_dead_letter_exchange
        )
        channel.queue_declare(
            queue=settings.events_queue,
            durable=True,
            arguments={"x-dead-letter-exchange": settings.events_dead_letter_exchange},
        )
        channel.queue_bind(
            queue=settings.events_queue,
            exchange=settings.events_exchange,
            routing_key=ROUTING_KEY_PATTERN,
        )

    def _on_message(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes,
    ) -> None:
        event = self._parse_event(body)
        if event is None:
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        max_attempts = max(1, self._settings.events_max_attempts)
        for attempt in range(1, max_attempts + 1):
            try:
                self._handler(event.note_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Handling %s for note %s failed (attempt %s/%s): %s",
                    event.event_type,
                    event.note_id,
                    attempt,
                    max_attempts,
                    exc,
                )
                if attempt < max_attempts:
                    self._stop.wait(self._settings.events_retry_backoff_seconds * 2 ** (attempt - 1))
                continue
            logger.info(
                "Processed %s for note %s (event %s)", event.event_type, event.note_id, event.event_id
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        logger.error(
            "Giving up on %s for note %s (event %s); dead-lettering",
            event.event_type,
            event.note_id,
            event.event_id,
        )
        channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

    @staticmethod
    def _parse_event(body: bytes) -> NoteEvent | None:
        try:
            event = NoteEvent.model_validate_json(body)
        except ValidationError as exc:
            logger.error("Invalid note event payload; dead-lettering: %s", exc)
            return None
        if event.event_type not in SUPPORTED_EVENT_TYPES:
            logger.error("Unsupported event type '%s'; dead-lettering", event.event_type)
            return None
        return event
