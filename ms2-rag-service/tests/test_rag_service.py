def test_sync_indexes_then_skips_unchanged(rag, ms1, ollama):
    ms1.put(1, "Quokka", "Quokkas live on Rottnest Island.")
    assert rag.sync_note(1).action == "indexed"
    calls = ollama.embed_calls
    assert rag.sync_note(1).action == "skipped"
    assert ollama.embed_calls == calls


def test_sync_reindexes_changed_note(rag, ms1):
    ms1.put(1, "Quokka", "v1")
    rag.sync_note(1)
    ms1.put(1, "Quokka", "v2")
    assert rag.sync_note(1).action == "indexed"


def test_sync_deletes_when_note_is_gone(rag, ms1):
    ms1.put(1, "Quokka", "text")
    rag.sync_note(1)
    del ms1.notes[1]
    assert rag.sync_note(1).action == "deleted"
    assert rag.answer_query("anything", top_k=4).sources == []


def test_reconcile_indexes_skips_and_removes_orphans(rag, ms1):
    ms1.put(1, "A", "alpha")
    ms1.put(2, "B", "beta")
    rag.sync_note(1)
    rag.sync_note(2)
    ms1.put(3, "C", "gamma")
    del ms1.notes[2]
    result = rag.reconcile_index()
    assert result.indexed_note_ids == [3]
    assert result.skipped_note_ids == [1]
    assert result.deleted_note_ids == [2]


def test_rebuild_reindexes_everything(rag, ms1):
    ms1.put(1, "A", "alpha")
    rag.sync_note(1)
    assert rag.rebuild_index().indexed_note_ids == [1]


def test_query_returns_sources_above_threshold(rag, ms1, ollama):
    ms1.put(1, "Quokka", "Quokkas live on Rottnest Island.")
    rag.sync_note(1)
    response = rag.answer_query("Where?", top_k=4)
    assert response.answer == "fake answer"
    assert [s.note_id for s in response.sources] == [1]


def test_query_below_threshold_skips_llm(rag, ms1, ollama):
    ms1.put(1, "Quokka", "Quokkas live on Rottnest Island.")
    rag.sync_note(1)
    ollama.query_vector = [0.0, 1.0]  # orthogonal: score 0
    response = rag.answer_query("Unrelated", top_k=4)
    assert response.sources == []
    assert "don't know" in response.answer
    assert ollama.chat_calls == 0
