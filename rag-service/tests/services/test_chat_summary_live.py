import os
from unittest.mock import Mock

import pytest

from app.clients.ollama_client import OllamaClient
from app.core.config import Settings
from app.schemas import ChatHistoryMessage
from app.services.chat_summary import is_chat_summary_request
from app.services.query_service import QueryService

pytestmark = pytest.mark.skipif(
    os.environ.get("MNEMO_LIVE_CHAT_TESTS") != "1",
    reason="Opt-in real-model checks require local Ollama",
)


@pytest.fixture
def local_chat():
    client = OllamaClient(Settings(
        chat_provider="ollama", ollama_base_url="http://localhost:11434",
    ))
    yield client
    client._client.close()


@pytest.mark.parametrize("question, summary", [
    ("Summarize the chat", True),
    ("Recap our conversation", True),
    ("What should I remember from everything we've covered?", True),
    ("Pull together the main threads of our exchange", True),
    ("Summarize what we discussed", True),
    ("Give me a quick rundown of our conversation without adding new information.", True),
    ("What were the main points we talked about earlier?", True),
    ("Fass unser bisheriges Gespraech kurz zusammen.", True),
    ("Haz un resumen de nuestra conversaci\u00f3n.", True),
    ("Summarize the discussion in my bird note", False),
    ("What do my notes say about Secret codes?", False),
    ("Are these codes about postmen?", False),
    ("Summarize my note titled Conversation summary", False),
    ("Do not summarize our chat; find my shipment note", False),
    ("Where exactly is the bluebird?", False),
    ("Is he in the heart or on a telephone line?", False),
])
def test_local_model_recognizes_meaning_without_trigger_phrases(local_chat, question, summary):
    assert is_chat_summary_request(local_chat, question) is summary


def test_local_summary_includes_early_and_late_topics_without_retrieval(local_chat):
    history = [
        ChatHistoryMessage(role="user", content="What are the secret codes used for?"),
        ChatHistoryMessage(role="assistant", content="I described shipment and inventory statuses."),
        *[
            ChatHistoryMessage(
                role="user" if index % 2 == 0 else "assistant",
                content=(
                    "We also discussed the garden plan and chose to grow tomatoes. "
                    "The planting date was still undecided. " * 3
                ),
            )
            for index in range(10)
        ],
        ChatHistoryMessage(role="user", content="Where is the bluebird?"),
        ChatHistoryMessage(
            role="assistant",
            content="I described a bluebird in a heart in one text and on a telephone line in another.",
        ),
    ]
    store = Mock()
    query = QueryService(Settings(), local_chat, store)
    result = query.answer_query(
        "Pull together the main threads of our exchange, including the opening topic.",
        top_k=4, history=history,
    )
    store.collection.assert_not_called()
    assert result.sources == []
    assert any(word in result.answer.lower() for word in ("shipment", "inventory", "codes"))
    assert "bluebird" in result.answer.lower()
