import json

import httpx

from app.clients.chat_client import ChatClient
from app.core.config import Settings
from app.schemas import ChatHistoryMessage

NO_CHAT_HISTORY = "There isn't any earlier chat to summarize yet."

_ROUTING_INSTRUCTION = (
    "Choose the source needed to answer the CURRENT request, in any language.\n"
    "notes: information from saved notes or documents. Use this for topic questions, "
    "factual follow-ups, and summaries of a note/document.\n"
    "conversation: a recap of the messages exchanged between the user and assistant "
    "in this chat session, not a summary of a document.\n"
    "Choose notes unless the request is about reviewing the conversation itself. "
    "Return only the source label.\n"
    "Example: 'Give me the key points from my meeting document' -> notes.\n"
    "Example: 'What were the key points of our exchange?' -> conversation."
)

_SUMMARY_INSTRUCTION = (
    "Summarize conversations for the user. Return a finished user-facing summary, "
    "never a plan, explanation, or description of the summarization process. Use the "
    "current request's language and format; default to one short paragraph. Merge the "
    "previous summary with the additional transcript in chronological order, preserving "
    "earlier important topics and decisions. Attribute claims to their speakers; "
    "assistant statements are not automatically verified facts. Use only the supplied "
    "information. Return only the summary."
)


def is_chat_summary_request(client: ChatClient, question: str) -> bool:
    messages = [
        {"role": "system", "content": _ROUTING_INSTRUCTION},
        {"role": "user", "content": question},
    ]
    intent = client.complete(messages, choices=["notes", "conversation"]).strip()
    if intent not in {"conversation", "notes"}:
        raise httpx.DecodingError("The chat provider returned an invalid request intent.")
    return intent == "conversation"


def summarize_chat(
    client: ChatClient,
    settings: Settings,
    question: str,
    history: list[ChatHistoryMessage],
) -> str:
    if not history:
        return NO_CHAT_HISTORY

    transcript = "\n".join(
        f"{message.role}: {json.dumps(message.content, ensure_ascii=False)}"
        for message in history
    )
    summary = ""
    while transcript:
        transcript_header = (
            f"User's request: {json.dumps(question, ensure_ascii=False)}\n\n"
            f"Previous summary: {json.dumps(summary, ensure_ascii=False)}\n\n"
            "Additional conversation transcript:\n"
        )
        completion_instruction = "\n\nWrite the complete summary for the user."
        messages = [
            {"role": "system", "content": _SUMMARY_INSTRUCTION},
            {
                "role": "user",
                "content": transcript_header + completion_instruction,
            },
        ]
        # UTF-8 bytes conservatively bound input tokens for the Qwen byte-level
        # tokenizers. Reserve context for generation and message framing too.
        available = (
            settings.chat_num_ctx - settings.chat_num_predict - 128
            - sum(len(message["content"].encode("utf-8")) for message in messages)
        )
        if available < 4:
            raise RuntimeError(
                "Chat summary context is too small. Increase RAG_CHAT_NUM_CTX "
                "or reduce RAG_CHAT_NUM_PREDICT."
            )
        segment = transcript.encode("utf-8")[:available].decode("utf-8", errors="ignore")
        # Advance only by decoded characters; retain any split Unicode character.
        transcript = transcript[len(segment):]
        messages[-1]["content"] = transcript_header + segment + completion_instruction
        summary = client.complete(messages)
    return summary
