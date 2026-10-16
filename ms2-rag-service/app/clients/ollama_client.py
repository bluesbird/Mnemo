import logging

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


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

    def chat_answer(self, question: str, context: str) -> str:
        if context.strip() == "":
            return "I don't know based on the provided notes."

        system_prompt = (
            "You answer questions about the user's personal notes. "
            "Use only facts from the NOTES section; some notes may be irrelevant, so ignore those. "
            "Answer directly in one to three complete sentences of plain text without markdown formatting, in the language of the question. "
            "Never mention the notes, the context or the note numbers in your answer. "
            "If the notes do not contain the answer, reply exactly: "
            "I don't know based on the provided notes."
        )
        user_prompt = f"NOTES:\n{context}\n\nQUESTION: {question}"
        payload = {
            "model": self._settings.chat_model,
            "stream": False,
            "think": self._settings.chat_think,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": self._settings.chat_temperature,
                "num_ctx": self._settings.chat_num_ctx,
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
        return content.strip()
