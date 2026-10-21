from typing import Protocol


class ChatClient(Protocol):
    def chat_answer(self, question: str, context: str) -> str: ...


def chat_messages(question: str, context: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You answer questions about the user's personal notes. "
                "Use only facts from the NOTES section; some notes may be irrelevant, so ignore those. "
                "Answer directly in one to three complete sentences of plain text without markdown formatting, in the language of the question. "
                "Never mention the notes, the context or the note numbers in your answer. "
                "If the notes do not contain the answer, reply exactly: "
                "I don't know based on the provided notes."
            ),
        },
        {"role": "user", "content": f"NOTES:\n{context}\n\nQUESTION: {question}"},
    ]
