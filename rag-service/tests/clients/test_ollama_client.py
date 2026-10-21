import json

import httpx

from app.core.config import Settings
from app.clients.ollama_client import OllamaClient


def _client_returning(content: str) -> OllamaClient:
    client = OllamaClient(Settings())
    client._client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"message": {"content": content}})
        )
    )
    return client


def test_chat_answer_strips_leaked_reasoning():
    client = _client_returning("Let me think...\nmore reasoning\n</think>\n\nA transformer is X.")
    assert client.chat_answer("q", "ctx") == "A transformer is X."


def test_chat_answer_keeps_plain_answers():
    assert _client_returning("Plain answer.").chat_answer("q", "ctx") == "Plain answer."


def test_chat_answer_bounds_generation_tokens():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"message": {"content": "Answer."}})

    client = OllamaClient(Settings(chat_num_predict=256))
    client._client = httpx.Client(transport=httpx.MockTransport(respond))

    client.chat_answer("question", "context")

    assert json.loads(requests[0].content)["options"]["num_predict"] == 256
