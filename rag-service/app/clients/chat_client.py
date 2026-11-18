import re
from typing import Protocol

from app.schemas import ChatHistoryMessage

_CLARIFICATION_QUESTION = re.compile(
    r"\b(?:what do you mean|what did you mean|can you clarify|explain that)\b",
    re.IGNORECASE,
)


class ChatClient(Protocol):
    def chat_answer(
        self,
        question: str,
        context: str,
        history: list[ChatHistoryMessage] | None = None,
    ) -> str: ...

    def complete(
        self, messages: list[dict[str, str]], *, choices: list[str] | None = None,
    ) -> str: ...


def chat_messages(
    question: str,
    context: str,
    history: list[ChatHistoryMessage] | None = None,
) -> list[dict[str, str]]:
    clarification_instruction = ""
    if _CLARIFICATION_QUESTION.search(question):
        previous_answer = next(
            (
                message.content
                for message in reversed(history or [])
                if message.role == "assistant"
            ),
            None,
        )
        if previous_answer:
            clarification_instruction = (
                "\n\nPREVIOUS ANSWER TO CLARIFY:\n"
                f"<previous_answer>{previous_answer}</previous_answer>\n"
                "Explain this in different, simpler words in exactly one short sentence. "
                "Do not repeat it or add unsupported details."
            )
    return [
        {
            "role": "system",
            "content": (
                "Use NOTES as the only source of factual claims and use conversation history only to resolve references. "
                "Reply with only the final answer in the language of the question, in one to three short natural sentences. "
                "For clarification follow-ups, restate the previous answer more simply instead of repeating it verbatim. "
                "For meaning questions, present a likely interpretation clearly as interpretation, not fact. "
                "For opinion questions, give a brief subjective reaction to the writing without claiming personal feelings. "
                "Consider every supplied note: when multiple notes are relevant, include each note's distinct "
                "contribution, even when they share a title. Do not rely only on the first note. Ignore notes "
                "that are unrelated to the question. "
                "Do not narrate reasoning, process, or instructions, and do not mention notes, context, or note numbers. "
                "If the notes do not contain the answer, reply exactly: "
                "I don't know based on the provided notes."
            ),
        },
        *[message.model_dump() for message in history or []],
        {
            "role": "user",
            "content": (
                f"NOTES:\n{context}\n\nQUESTION: {question}"
                f"{clarification_instruction}"
            ),
        },
    ]
