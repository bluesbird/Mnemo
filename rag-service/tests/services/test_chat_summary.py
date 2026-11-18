import json
from unittest.mock import Mock

import httpx
import pytest

from app.clients.chat_client import ChatClient
from app.core.config import Settings
from app.schemas import ChatHistoryMessage
from app.services.chat_summary import NO_CHAT_HISTORY, is_chat_summary_request, summarize_chat


@pytest.mark.parametrize("intent, expected", [("conversation", True), ("notes", False)])
def test_routing_uses_model_decision_and_passes_current_request(intent, expected):
    client = Mock(spec=ChatClient)
    client.complete.return_value = intent
    question = "Draw together the main threads of our exchange"
    assert is_chat_summary_request(client, question) is expected
    assert client.complete.call_args.args[0][-1] == {"role": "user", "content": question}
    assert client.complete.call_args.kwargs == {"choices": ["notes", "conversation"]}


def test_empty_history_does_not_generate_an_invented_summary():
    client = Mock(spec=ChatClient)
    assert summarize_chat(client, Settings(), "Wrap this up", []) == NO_CHAT_HISTORY
    client.complete.assert_not_called()


def test_short_chat_needs_only_one_summary_call():
    client = Mock(spec=ChatClient)
    client.complete.return_value = "You discussed logistics and poetry."
    question = "Two bullet points in German, please"
    history = [ChatHistoryMessage(role="user", content="Talk about logistics.")]

    assert summarize_chat(client, Settings(), question, history) == client.complete.return_value
    client.complete.assert_called_once()
    prompt = client.complete.call_args.args[0][-1]["content"]
    assert question in prompt
    assert 'user: "Talk about logistics."' in prompt


def test_long_unicode_chat_is_consumed_once_in_order_with_bounded_requests():
    client = Mock(spec=ChatClient)
    # A fixed-size result never shrinks: it must not cause a recursive merge loop.
    client.complete.return_value = "Running recap: " + "x" * 200
    settings = Settings(chat_num_ctx=2200, chat_num_predict=256)
    question = "Include the opening topic and later corrections."
    history = [
        ChatHistoryMessage(
            role="user" if index % 2 == 0 else "assistant",
            content=f"Topic {index}: " + "\u00e9\u4e2d\U0001f426\n" * 90,
        )
        for index in range(14)
    ]

    assert summarize_chat(client, settings, question, history) == client.complete.return_value
    segments = []
    for index, call in enumerate(client.complete.call_args_list):
        messages = call.args[0]
        assert (
            sum(len(message["content"].encode("utf-8")) for message in messages)
            + 128 + settings.chat_num_predict
        ) <= settings.chat_num_ctx
        prompt = messages[-1]["content"]
        assert question in prompt
        if index:
            assert client.complete.return_value in prompt
        segments.append(prompt.split("Next transcript segment:\n", 1)[1])
    assert 1 < len(segments) < 100
    assert "".join(segments) == "\n".join(
        f"{message.role}: {json.dumps(message.content, ensure_ascii=False)}"
        for message in history
    )


def test_insufficient_context_fails_instead_of_dropping_history():
    client = Mock(spec=ChatClient)
    with pytest.raises(RuntimeError, match="context is too small"):
        summarize_chat(
            client, Settings(chat_num_ctx=128), "Recap this",
            [ChatHistoryMessage(role="user", content="Earlier topic")],
        )
    client.complete.assert_not_called()


def test_failed_summary_does_not_return_partial_success():
    client = Mock(spec=ChatClient)
    client.complete.side_effect = ["Partial recap", httpx.ReadTimeout("Provider timeout")]
    with pytest.raises(httpx.ReadTimeout):
        summarize_chat(
            client, Settings(chat_num_ctx=1500), "Recap this",
            [ChatHistoryMessage(role="user", content="x" * 2000)],
        )
