import json

import httpx

from app.clients.chat_client import chat_messages
from app.core.config import Settings


class GroqClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.Client(
            base_url="https://api.groq.com/openai/v1/",
            headers={"Authorization": f"Bearer {settings.groq_api_key.get_secret_value()}"},
            timeout=60.0,
        )

    def chat_answer(self, question: str, context: str) -> str:
        if not context.strip():
            return "I don't know based on the provided notes."

        response = self._client.post(
            "chat/completions",
            json={
                "model": self._settings.groq_model,
                "messages": chat_messages(question, context),
                "temperature": self._settings.chat_temperature,
                "max_completion_tokens": self._settings.chat_num_predict,
                "reasoning_effort": "none",
                "stream": False,
            },
        )
        response.raise_for_status()
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise httpx.DecodingError("Groq returned invalid JSON.", request=response.request) from exc
        choices = data.get("choices") if isinstance(data, dict) else None
        choice = choices[0] if isinstance(choices, list) and choices else None
        if not isinstance(choice, dict) or choice.get("finish_reason") != "stop":
            raise httpx.DecodingError("Groq returned an incomplete answer.", request=response.request)
        message = choice.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise httpx.DecodingError("Groq returned an empty answer.", request=response.request)
        return content.strip()
