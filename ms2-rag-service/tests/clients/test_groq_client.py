import json

import httpx
import pytest
from pydantic import ValidationError

from app.clients.groq_client import GroqClient
from app.clients.ollama_client import OllamaClient
from app.core.config import Settings


def settings():
    return Settings(chat_provider="groq", groq_api_key="test-key-not-a-real-secret")


def mock_client(handler):
    client = GroqClient(settings())
    client._client.close()
    client._client = httpx.Client(
        base_url="https://api.groq.com/openai/v1/",
        headers={"Authorization": "Bearer test-key-not-a-real-secret"},
        transport=httpx.MockTransport(handler),
    )
    return client


def test_groq_request_and_answer():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={
            "choices": [{"finish_reason": "stop", "message": {"content": " Answer. "}}],
        })

    client = mock_client(handler)
    assert client.chat_answer("question", "retrieved text") == "Answer."
    assert str(requests[0].url) == "https://api.groq.com/openai/v1/chat/completions"
    assert requests[0].headers["Authorization"] == "Bearer test-key-not-a-real-secret"
    payload = json.loads(requests[0].content)
    assert payload["model"] == "qwen/qwen3.8-27b"
    assert payload["max_completion_tokens"] == 256
    assert payload["reasoning_effort"] == "none"
    assert payload["messages"][1]["content"] == "NOTES:\nretrieved text\n\nQUESTION: question"
    assert "options" not in payload
    assert "think" not in payload


@pytest.mark.parametrize("choices", [
    [],
    [{"finish_reason": "length", "message": {"content": "Partial answer"}}],
    [{"finish_reason": "stop", "message": {"content": ""}}],
    [{"finish_reason": "stop", "message": {"content": None}}],
    [{"finish_reason": "stop", "message": {"content": " "}}],
    [{"finish_reason": "stop"}],
])
def test_empty_or_incomplete_answers_are_errors(choices):
    client = mock_client(lambda _: httpx.Response(200, json={"choices": choices}))
    with pytest.raises(httpx.DecodingError):
        client.chat_answer("question", "context")


@pytest.mark.parametrize("status", [401, 429, 500])
def test_provider_errors_are_not_hidden_or_retried(status):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status, json={"error": {"message": "provider error"}})

    client = mock_client(handler)
    with pytest.raises(httpx.HTTPStatusError):
        client.chat_answer("question", "context")
    assert len(requests) == 1


def test_no_context_does_not_call_groq():
    def fail(_):
        pytest.fail("No request expected")

    assert "don't know" in mock_client(fail).chat_answer("question", "")


def test_invalid_json_is_an_upstream_error():
    client = mock_client(lambda _: httpx.Response(200, text="not json"))
    with pytest.raises(httpx.DecodingError):
        client.chat_answer("question", "context")


def test_local_defaults_and_secret_validation():
    assert Settings().chat_provider == "ollama"
    with pytest.raises(ValidationError, match="MS2_GROQ_API_KEY is required"):
        Settings(chat_provider="groq")
    with pytest.raises(ValidationError):
        Settings(chat_provider="unknown")
    assert "test-key-not-a-real-secret" not in repr(settings())


def test_embeddings_remain_on_ollama_with_groq_selected():
    assert settings().indexing_version == Settings().indexing_version
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"embeddings": [[1.0, 0.0]]})

    client = OllamaClient(settings())
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    assert client.embed_query("question") == [1.0, 0.0]
    assert requests[0].url.path == "/api/embed"
    assert json.loads(requests[0].content)["model"] == "qwen3-embedding:0.6b"
    assert "Authorization" not in requests[0].headers
