def test_query_returns_sources_above_threshold(indexing, query, knowledge, ollama):
    knowledge.put(1, "Quokka", "Quokkas live on Rottnest Island.")
    indexing.sync_note(1)
    response = query.answer_query("Where?", top_k=4)
    assert response.answer == "fake answer"
    assert [s.note_id for s in response.sources] == [1]


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

    class FakeChat:
        def chat_answer(self, question, context):
            assert question == "Where do quokkas live?"
            assert "Rottnest Island" in context
            return "On Rottnest Island."

    knowledge.put(1, "Quokka", "Quokkas live on Rottnest Island.")
    indexing.sync_note(1)
    query = QueryService(settings, ollama, store, FakeChat())
    result = query.answer_query("Where do quokkas live?", top_k=4)
    assert result.answer == "On Rottnest Island."
    assert [s.note_id for s in result.sources] == [1]
    assert ollama.chat_calls == 0
