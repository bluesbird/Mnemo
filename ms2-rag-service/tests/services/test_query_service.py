def test_query_returns_sources_above_threshold(indexing, query, ms1, ollama):
    ms1.put(1, "Quokka", "Quokkas live on Rottnest Island.")
    indexing.sync_note(1)
    response = query.answer_query("Where?", top_k=4)
    assert response.answer == "fake answer"
    assert [s.note_id for s in response.sources] == [1]


def test_query_below_threshold_skips_llm(indexing, query, ms1, ollama):
    ms1.put(1, "Quokka", "Quokkas live on Rottnest Island.")
    indexing.sync_note(1)
    ollama.query_vector = [0.0, 1.0]  # orthogonal: score 0
    response = query.answer_query("Unrelated", top_k=4)
    assert response.sources == []
    assert "don't know" in response.answer
    assert ollama.chat_calls == 0
