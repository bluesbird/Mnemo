import json

import httpx
import pytest

from app.core.config import Settings
from app.clients.ollama_client import OllamaClient
from app.clients.chat_client import chat_messages
from app.schemas import ChatHistoryMessage


def _client_returning(content: str) -> OllamaClient:
    client = OllamaClient(Settings())
    client._client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"message": {"content": content}})
        )
    )
    return client


def test_chat_prompt_requires_a_concise_final_answer():
    system_prompt = chat_messages(
        "What does this mean?", "A plant has a paper hat."
    )[0]["content"]

    assert "Do not narrate reasoning" in system_prompt
    assert "one to three short natural sentences" in system_prompt
    assert "present a likely interpretation clearly as interpretation, not fact" in system_prompt
    assert "brief subjective reaction to the writing" in system_prompt
    assert "restate the previous answer more simply" in system_prompt


def test_chat_prompt_synthesizes_all_relevant_notes():
    system_prompt = chat_messages(
        "Tell me something about bluebirds.",
        "Note 1: Bluebird\nA song about hidden longing.\n\n"
        "Note 2: Bluebird\nA poem about a bluebird on a telephone line.\n\n"
        "Note 3: Birdwatching\nA notebook for birdwatching.",
    )[0]["content"]

    assert "when multiple notes are relevant, include each note's distinct contribution" in system_prompt
    assert "even when they share a title" in system_prompt
    assert "Do not rely only on the first note." in system_prompt
    assert "Ignore notes that are unrelated to the question." in system_prompt


def test_clarification_prompt_requests_a_short_explanation():
    current_message = chat_messages(
        "What do you mean by that?",
        "Relevant note excerpt.",
        [
            ChatHistoryMessage(role="assistant", content="The note suggests hidden longing."),
        ],
    )[-1]["content"]

    assert "<previous_answer>The note suggests hidden longing.</previous_answer>" in current_message
    assert "different, simpler words in exactly one short sentence" in current_message
    assert "Do not repeat it or add unsupported details." in current_message


def test_clarification_prompt_is_not_added_without_previous_answer():
    current_message = chat_messages(
        "What do you mean by that?",
        "Relevant note excerpt.",
        [ChatHistoryMessage(role="user", content="Earlier question")],
    )[-1]["content"]

    assert "<previous_answer>" not in current_message


def test_chat_answer_strips_leaked_reasoning():
    client = _client_returning(
        'Let me think...\nmore reasoning\n</think>\n\n{"answer":"A transformer is X."}'
    )
    assert client.chat_answer("q", "ctx") == "A transformer is X."


def test_chat_answer_parses_structured_answer():
    assert _client_returning('{"answer":"Plain answer."}').chat_answer("q", "ctx") == "Plain answer."


def test_completion_sends_supplied_messages_and_parses_answer():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"message": {"content": '{"answer":"We discussed bluebirds and a song."}'}},
        )

    messages = [
        {"role": "system", "content": "Summarize the transcript."},
        {"role": "user", "content": "We discussed bluebirds and a song."},
    ]
    client = OllamaClient(Settings())
    client._client = httpx.Client(transport=httpx.MockTransport(respond))

    assert client.complete(messages) == "We discussed bluebirds and a song."
    payload = json.loads(requests[0].content)
    assert payload["messages"] == messages


def test_incomplete_completion_is_not_a_successful_summary():
    client = OllamaClient(Settings())
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json={
            "done_reason": "length", "message": {"content": '{"answer":"Incomplete"}'},
        }),
    ))
    with pytest.raises(httpx.DecodingError, match="incomplete answer"):
        client.complete([{"role": "user", "content": "Summarize the chat"}])


def test_routing_constrains_choices_without_changing_later_answers():
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": '{"answer":"notes"}'}})

    client = OllamaClient(Settings())
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(respond))
    messages = [{"role": "user", "content": "Where is the bird?"}]
    assert client.complete(messages, choices=["notes", "conversation"]) == "notes"
    client.chat_answer("question", "retrieved text")

    assert requests[0]["format"]["properties"]["answer"]["enum"] == ["notes", "conversation"]
    assert requests[0]["options"]["temperature"] == 0
    assert requests[0]["options"]["num_predict"] == 32
    assert "enum" not in requests[1]["format"]["properties"]["answer"]
    assert requests[1]["options"]["num_predict"] == 256


@pytest.mark.parametrize("invalid_content", [
    "not json",
    "{}",
    '{"answer":""}',
    "[]",
])
def test_chat_answer_rejects_invalid_structured_output(invalid_content):
    with pytest.raises(RuntimeError, match="Invalid structured chat response"):
        _client_returning(invalid_content).chat_answer("q", "ctx")


def test_chat_answer_bounds_generation_tokens():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200, json={"message": {"content": '{"answer":"Answer."}'}}
        )

    client = OllamaClient(Settings(chat_num_predict=256))
    client._client = httpx.Client(transport=httpx.MockTransport(respond))

    client.chat_answer("question", "context")

    payload = json.loads(requests[0].content)
    assert payload["options"]["num_predict"] == 256
    assert payload["format"] == {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    }
