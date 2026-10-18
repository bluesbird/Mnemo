import json
from types import SimpleNamespace
from unittest.mock import Mock

from app.core.config import Settings
from app.messaging.consumer import NoteEventConsumer


def note_event(note_id: int) -> bytes:
    return json.dumps({
        "schema_version": 1,
        "event_id": "d791fcee-26ce-4a88-a1c1-1548f9a0dc44",
        "event_type": "NoteUpdated",
        "occurred_at": "2026-01-01T12:00:00Z",
        "note_id": note_id,
    }).encode()


def rebuild_event(note_id=None) -> bytes:
    return json.dumps({
        "schema_version": 1,
        "event_id": "0c8a0dfb-14aa-44fa-aab3-8269a8dc92b0",
        "event_type": "IndexRebuildRequested",
        "occurred_at": "2026-01-01T12:00:00Z",
        "note_id": note_id,
    }).encode()


def test_note_event_invokes_note_handler_and_acknowledges():
    note_handler = Mock()
    rebuild_handler = Mock()
    consumer = NoteEventConsumer(Settings(), note_handler, rebuild_handler)
    channel = Mock()

    consumer._on_message(channel, SimpleNamespace(delivery_tag=7), None, note_event(42))

    note_handler.assert_called_once_with(42)
    rebuild_handler.assert_not_called()
    channel.basic_ack.assert_called_once_with(delivery_tag=7)
    channel.basic_reject.assert_not_called()


def test_rebuild_event_invokes_rebuild_handler_and_acknowledges():
    note_handler = Mock()
    rebuild_handler = Mock()
    consumer = NoteEventConsumer(Settings(), note_handler, rebuild_handler)
    channel = Mock()

    consumer._on_message(channel, SimpleNamespace(delivery_tag=8), None, rebuild_event())

    note_handler.assert_not_called()
    rebuild_handler.assert_called_once_with()
    channel.basic_ack.assert_called_once_with(delivery_tag=8)
    channel.basic_reject.assert_not_called()


def test_invalid_rebuild_event_with_note_id_is_dead_lettered():
    note_handler = Mock()
    rebuild_handler = Mock()
    consumer = NoteEventConsumer(Settings(), note_handler, rebuild_handler)
    channel = Mock()

    consumer._on_message(channel, SimpleNamespace(delivery_tag=9), None, rebuild_event(5))

    note_handler.assert_not_called()
    rebuild_handler.assert_not_called()
    channel.basic_reject.assert_called_once_with(delivery_tag=9, requeue=False)
