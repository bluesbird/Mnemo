from app.rag.chunker import NoteChunker
from app.core.config import Settings


def make_chunker(size: int = 20, overlap: int = 5) -> NoteChunker:
    return NoteChunker(
        Settings(chunk_size_tokens=size, chunk_overlap_tokens=overlap, tokenizer_name="does-not-exist/offline")
    )


def test_empty_note_has_no_chunks():
    assert make_chunker().chunk_note("  ", "  ") == []


def test_short_note_is_single_chunk():
    chunks = make_chunker().chunk_note("Title", "short body")
    assert len(chunks) == 1
    assert chunks[0].text.startswith("Title")


def test_long_note_is_split_with_sequential_indexes():
    body = "\n\n".join(" ".join(f"w{p}_{i}" for i in range(15)) for p in range(6))
    chunks = make_chunker().chunk_note("Title", body)
    assert len(chunks) > 1
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_single_huge_paragraph_is_split():
    chunks = make_chunker().chunk_note("T", " ".join(f"w{i}" for i in range(100)))
    assert len(chunks) > 1
