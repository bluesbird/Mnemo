import json

import httpx

from app.clients.chat_client import (
    chat_messages,
    has_unsupported_numbers,
    numeric_revision_messages,
)
from app.core.config import Settings
from app.schemas import ChatHistoryMessage


class GroqClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.Client(
            base_url="https://api.groq.com/openai/v1/",
            headers={"Authorization": f"Bearer {settings.groq_api_key.get_secret_value()}"},
            timeout=60.0,
        )

    def chat_answer(
        self,
        question: str,
        context: str,
        history: list[ChatHistoryMessage] | None = None,
    ) -> str:
        if not context.strip():
            return "I don't know based on the provided notes."

        messages = chat_messages(question, context, history)
        answer = self.complete(messages)
        if not has_unsupported_numbers(answer, context):
            return answer

        answer = self.complete(numeric_revision_messages(messages, answer))
        if has_unsupported_numbers(answer, context):
            raise RuntimeError("Groq returned unsupported numeric claims.")
        return answer

    def complete(
        self, messages: list[dict[str, str]], *, choices: list[str] | None = None,
    ) -> str:
        if choices:
            messages = [
                *messages,
                {
                    "role": "system",
                    "content": 'Return a JSON object with an "answer" string, one of: '
                    + json.dumps(choices),
                },
            ]
        response = self._client.post(
            "chat/completions",
            json={
                "model": self._settings.groq_model,
                "messages": messages,
                "temperature": 0 if choices else self._settings.chat_temperature,
                "max_completion_tokens": 32 if choices else self._settings.chat_num_predict,
                "reasoning_effort": "none",
                "stream": False,
                **({"response_format": {"type": "json_object"}} if choices else {}),
            },
        )
        response.raise_for_status()
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise httpx.DecodingError("Groq returned invalid JSON.", request=response.request) from exc
        returned_choices = data.get("choices") if isinstance(data, dict) else None
        choice = returned_choices[0] if isinstance(returned_choices, list) and returned_choices else None
        if not isinstance(choice, dict) or choice.get("finish_reason") != "stop":
            raise httpx.DecodingError("Groq returned an incomplete answer.", request=response.request)
        message = choice.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise httpx.DecodingError("Groq returned an empty answer.", request=response.request)
        if choices:
            try:
                result = json.loads(content)
            except json.JSONDecodeError as exc:
                raise httpx.DecodingError("Groq returned invalid JSON.", request=response.request) from exc
            content = result.get("answer") if isinstance(result, dict) else None
            if not isinstance(content, str) or content not in choices:
                raise httpx.DecodingError("Groq returned an invalid choice.", request=response.request)
        return content.strip()
