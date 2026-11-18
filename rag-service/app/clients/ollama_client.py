import json
import logging

import httpx

from app.clients.chat_client import chat_messages
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

        payload = {
            "model": self._settings.chat_model,
            "stream": False,
            "think": self._settings.chat_think,
            "format": CHAT_RESPONSE_FORMAT,
            "messages": chat_messages(question, context, history),
            "options": {
                "temperature": self._settings.chat_temperature,
                "num_ctx": self._settings.chat_num_ctx,
                "num_predict": self._settings.chat_num_predict,
            },
        }
        response = self._client.post(f"{self._base_url}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
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
