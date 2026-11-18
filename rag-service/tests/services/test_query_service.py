import json

import httpx
import pytest

from app.rag.retrieval import Candidate, fuse
from app.services.query_service import _focus_candidates


def test_query_returns_sources_above_threshold(indexing, query, knowledge, ollama):
    knowledge.put(1, "Quokka", "Quokkas live on Rottnest Island.")
    indexing.sync_note(1)
    response = query.answer_query("Where?", top_k=4)
    assert response.answer == "fake answer"
    assert [s.note_id for s in response.sources] == [1]


def test_named_note_focus_keeps_semantic_matches_and_drops_weak_keyword_matches():
    named_note = Candidate(
        "1-0", "A tiny paper hat is on the houseplant.",
        {"note_id": "1", "note_title": "A very small mystery"},
        dense_score=0.25,
        keyword_score=1.0,
    )
    semantic_match = Candidate(
        "2-0", "The potted fern sits on the windowsill.",
        {"note_id": "2", "note_title": "A quiet corner"},
        dense_score=0.55,
    )
    weak_keyword_match = Candidate(
        "3-0", "A small notebook for birdwatching.",
        {"note_id": "3", "note_title": "Birdwatching, technically"},
        dense_score=0.25,
        keyword_score=0.25,
    )

    candidates = _focus_candidates(
        "What do my notes say about A very small mystery and potted plants?",
        [named_note, semantic_match, weak_keyword_match],
        min_dense_score=0.4,
    )

    assert [candidate.chunk_id for candidate in candidates] == ["1-0", "2-0"]
    assert [candidate.chunk_id for candidate in fuse(candidates, 0.4, 4)] == [
        "1-0",
        "2-0",
    ]


def test_follow_up_retrieval_uses_previous_user_question(
    indexing, query, knowledge, ollama
):
    from app.schemas import ChatHistoryMessage

    knowledge.put(1, "Bluebird", "A bluebird sings at dawn.")
    indexing.sync_note(1)

    response = query.answer_query(
        "What do you mean by that?",
        top_k=4,
        history=[
            ChatHistoryMessage(role="user", content="What do my notes say about Bluebird?"),
            ChatHistoryMessage(role="assistant", content="A bluebird sings at dawn."),
        ],
    )

    assert response.answer == "fake answer"
    assert [source.note_id for source in response.sources] == [1]
    assert "Bluebird" in ollama.last_query


def test_standalone_question_does_not_inherit_previous_topic(
    indexing, query, knowledge, ollama
):
    from app.schemas import ChatHistoryMessage

    knowledge.put(1, "Bluebird", "A bluebird sings at dawn.")
    indexing.sync_note(1)

    query.answer_query(
        "Where do quokkas live?",
        top_k=4,
        history=[
            ChatHistoryMessage(role="user", content="Tell me about Bluebird."),
            ChatHistoryMessage(role="assistant", content="A bluebird sings at dawn."),
        ],
    )

    assert ollama.last_query == "Where do quokkas live"


def test_model_selected_summary_uses_history_without_retrieval(query, ollama, store, monkeypatch):
    from app.schemas import ChatHistoryMessage

    monkeypatch.setattr(store, "collection", lambda: pytest.fail("Summary must not retrieve notes"))
    ollama.completion_results = iter(["conversation", "Conversation summary."])
    history = [
        ChatHistoryMessage(role="user" if index % 2 == 0 else "assistant", content=f"message {index}")
        for index in range(14)
    ]
    question = "What should I remember from everything we covered?"

    response = query.answer_query(question, top_k=4, history=history)

    assert response.answer == "Conversation summary."
    assert response.sources == []
    assert len(ollama.completions) == 2
    assert ollama.completions[0][-1]["content"] == question
    assert len(ollama.completions[0]) == 2
    summary_input = ollama.completions[1][-1]["content"]
    assert question in summary_input
    assert all(json.dumps(message.content) in summary_input for message in history)
    assert not ollama.last_query
    assert ollama.chat_calls == 0


def test_chat_summary_without_history_returns_clear_message(query, ollama):
    ollama.completion_results = iter(["conversation"])
    response = query.answer_query("Give me a summary of our conversation", top_k=4)

    assert response.answer == "There isn't any earlier chat to summarize yet."
    assert response.sources == []
    assert ollama.embed_calls == 0
    assert len(ollama.completions) == 1
    assert not ollama.last_query


@pytest.mark.parametrize(
    "question",
    [
        "Summarize the discussion in my bird note",
        "Summarize the conversation in my meeting note",
        "Do not summarize our chat; answer from my notes",
        "Find my note about a conversation",
    ],
)
def test_non_chat_summary_requests_use_retrieval(
    query, ollama, indexing, knowledge, question
):
    knowledge.put(1, "Bird", "A bird sings.")
    indexing.sync_note(1)

    query.answer_query(question, top_k=4)

    assert len(ollama.completions) == 1
    assert ollama.last_query
    assert ollama.embed_calls == 1


def test_invalid_intent_does_not_silently_fall_back_to_notes(query, ollama, store, monkeypatch):
    monkeypatch.setattr(store, "collection", lambda: pytest.fail("Invalid intent must fail explicitly"))
    ollama.completion_results = iter(["maybe"])

    with pytest.raises(httpx.DecodingError, match="invalid request intent"):
        query.answer_query("Recap our conversation", top_k=4)


def test_note_answer_only_receives_ten_recent_messages(
    indexing, query, knowledge, ollama
):
    from app.schemas import ChatHistoryMessage

    knowledge.put(1, "Quokka", "Quokkas live on Rottnest Island.")
    indexing.sync_note(1)
    history = [
        ChatHistoryMessage(
            role="user" if index % 2 == 0 else "assistant",
            content=f"message {index}",
        )
        for index in range(12)
    ]

    query.answer_query("Where do quokkas live?", top_k=4, history=history)

    assert ollama.last_chat_history == history[-10:]


def test_query_below_threshold_skips_llm(indexing, query, knowledge, ollama):
    knowledge.put(1, "Quokka", "Quokkas live on Rottnest Island.")
    indexing.sync_note(1)
    ollama.query_vector = [0.0, 1.0]  # orthogonal: score 0
    response = query.answer_query("Unrelated", top_k=4)
    assert response.sources == []
    assert "don't know" in response.answer
    assert ollama.chat_calls == 0


def test_separate_chat_provider_preserves_retrieval(indexing, settings, knowledge, ollama, store):
    from app.services.query_service import QueryService
    from app.schemas import ChatHistoryMessage

    class FakeChat:
        def complete(self, messages, *, choices=None):
            return "notes"

        def chat_answer(self, question, context, history=None):
            assert question == "Where do quokkas live?"
            assert "Rottnest Island" in context
            assert history[0].content == "Tell me about quokkas."
            return "On Rottnest Island."

    knowledge.put(1, "Quokka", "Quokkas live on Rottnest Island.")
    indexing.sync_note(1)
    query = QueryService(settings, ollama, store, FakeChat())
    result = query.answer_query(
        "Where do quokkas live?",
        top_k=4,
        history=[
            ChatHistoryMessage(role="user", content="Tell me about quokkas.")
        ],
    )
    assert result.answer == "On Rottnest Island."
    assert [s.note_id for s in result.sources] == [1]
    assert ollama.chat_calls == 0
