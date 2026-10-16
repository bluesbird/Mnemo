def test_sync_indexes_then_skips_unchanged(indexing, ms1, ollama):
    ms1.put(1, "Quokka", "Quokkas live on Rottnest Island.")
    assert indexing.sync_note(1).action == "indexed"
    calls = ollama.embed_calls
    assert indexing.sync_note(1).action == "skipped"
    assert ollama.embed_calls == calls


def test_sync_reindexes_changed_note(indexing, ms1):
    ms1.put(1, "Quokka", "v1")
    indexing.sync_note(1)
    ms1.put(1, "Quokka", "v2")
    assert indexing.sync_note(1).action == "indexed"


def test_sync_deletes_when_note_is_gone(indexing, query, ms1):
    ms1.put(1, "Quokka", "text")
    indexing.sync_note(1)
    del ms1.notes[1]
    assert indexing.sync_note(1).action == "deleted"
    assert query.answer_query("anything", top_k=4).sources == []


def test_reconcile_indexes_skips_and_removes_orphans(indexing, ms1):
    ms1.put(1, "A", "alpha")
    ms1.put(2, "B", "beta")
    indexing.sync_note(1)
    indexing.sync_note(2)
    ms1.put(3, "C", "gamma")
    del ms1.notes[2]
    result = indexing.reconcile_index()
    assert result.indexed_note_ids == [3]
    assert result.skipped_note_ids == [1]
    assert result.deleted_note_ids == [2]


def test_rebuild_reindexes_everything(indexing, ms1):
    ms1.put(1, "A", "alpha")
    indexing.sync_note(1)
    assert indexing.rebuild_index().indexed_note_ids == [1]
