import json
import logging

import httpx

from app.clients.chat_client import (
    chat_messages,
    has_unsupported_numbers,
    numeric_revision_messages,
)
from app.core.config import Settings
from app.schemas import ChatHistoryMessage

logger = logging.getLogger(__name__)

CHAT_RESPONSE_FORMAT = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._client = httpx.Client(timeout=60.0)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {"model": self._settings.embedding_model, "input": texts}
        response = self._client.post(f"{self._base_url}/api/embed", json=payload)
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise RuntimeError("Invalid embedding response from Ollama.")
        return embeddings

    def embed_query(self, question: str) -> list[float]:
        prompt = f"{self._settings.query_instruction_prefix}{question}"
        embeddings = self.embed_documents([prompt])
        return embeddings[0]

    def chat_answer(
        self,
        question: str,
        context: str,
        history: list[ChatHistoryMessage] | None = None,
    ) -> str:
        if context.strip() == "":
            return "I don't know based on the provided notes."

        messages = chat_messages(question, context, history)
        answer = self.complete(messages)
        if not has_unsupported_numbers(answer, context):
            return answer

        logger.warning("Ollama added unsupported numeric claims; requesting a correction")
        answer = self.complete(numeric_revision_messages(messages, answer))
        if has_unsupported_numbers(answer, context):
            raise RuntimeError("Ollama returned unsupported numeric claims.")
        return answer

    def complete(
        self, messages: list[dict[str, str]], *, choices: list[str] | None = None,
    ) -> str:
        response_format = CHAT_RESPONSE_FORMAT
        if choices:
            response_format = {
                **CHAT_RESPONSE_FORMAT,
                "properties": {"answer": {"type": "string", "enum": choices}},
            }
        payload = {
            "model": self._settings.chat_model,
            "stream": False,
            "think": self._settings.chat_think,
            "format": response_format,
            "messages": messages,
            "options": {
                "temperature": 0 if choices else self._settings.chat_temperature,
                "num_ctx": self._settings.chat_num_ctx,
                "num_predict": 32 if choices else self._settings.chat_num_predict,
            },
        }
        response: httpx.Response | None = None
        data: dict = {}
        for attempt in range(2):
            response = self._client.post(f"{self._base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get("done_reason") != "length":
                break
            if attempt == 0:
                logger.warning("Ollama reached its output limit; retrying once")
        if data.get("done_reason") == "length":
            assert response is not None
            raise httpx.DecodingError("Ollama returned an incomplete answer.", request=response.request)
        content = data.get("message", {}).get("content")
        if isinstance(content, str) and "</think>" in content:
            # Some Qwen3 builds ignore think=false and emit reasoning before a closing tag.
            content = content.rsplit("</think>", 1)[1]
        if not isinstance(content, str) or content.strip() == "":
            raise RuntimeError("Invalid chat response from Ollama.")
        try:
            structured = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Invalid structured chat response from Ollama.") from exc
        if not isinstance(structured, dict):
            raise RuntimeError("Invalid structured chat response from Ollama.")
        answer = structured.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("Invalid structured chat response from Ollama.")
        return answer.strip()
