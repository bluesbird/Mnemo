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
