import hashlib

import pytest

from app.chunker import NoteChunker
from app.config import Settings
from app.rag_service import RagService
from app.schemas import IndexMetadataItem, NoteForIndex


class FakeMs1:
    def __init__(self) -> None:
        self.notes: dict[int, NoteForIndex] = {}

    def put(self, note_id: int, title: str, content: str) -> None:
        digest = hashlib.sha256(f"{title}{content}".encode()).hexdigest()
        self.notes[note_id] = NoteForIndex(id=note_id, title=title, content=content, sourceHash=digest)

    def fetch_note(self, note_id: int):
        return self.notes.get(note_id)

    def fetch_index_metadata(self):
        return [IndexMetadataItem(noteId=n.id, sourceHash=n.source_hash) for n in self.notes.values()]


class FakeOllama:
    def __init__(self) -> None:
        self.embed_calls = 0
        self.chat_calls = 0
        self.query_vector = [1.0, 0.0]

    def embed_documents(self, texts):
        self.embed_calls += 1
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, question):
        return self.query_vector

    def chat_answer(self, question, context):
        self.chat_calls += 1
        return "fake answer"


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        chroma_path=str(tmp_path / "chroma"),
        rabbitmq_enabled=False,
        admin_api_key="test-key",
        tokenizer_name="does-not-exist/offline",  # forces word-based fallback
    )


@pytest.fixture
def ms1() -> FakeMs1:
    return FakeMs1()


@pytest.fixture
def ollama() -> FakeOllama:
    return FakeOllama()


@pytest.fixture
def rag(settings, ms1, ollama) -> RagService:
    return RagService(settings, ms1, ollama, NoteChunker(settings))
