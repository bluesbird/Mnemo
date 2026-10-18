import hashlib

import pytest

from app.core.config import Settings
from app.rag.chunker import NoteChunker
from app.schemas import IndexMetadataItem, NoteForIndex
from app.services.index_store import IndexStore
from app.services.indexing_service import IndexingService
from app.services.query_service import QueryService


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
        tokenizer_name="does-not-exist/offline",  # forces word-based fallback
    )


@pytest.fixture
def ms1() -> FakeMs1:
    return FakeMs1()


@pytest.fixture
def ollama() -> FakeOllama:
    return FakeOllama()


@pytest.fixture
def store(settings) -> IndexStore:
    return IndexStore(settings)


@pytest.fixture
def indexing(settings, ms1, ollama, store) -> IndexingService:
    return IndexingService(settings, ms1, ollama, NoteChunker(settings), store)


@pytest.fixture
def query(settings, ollama, store) -> QueryService:
    return QueryService(settings, ollama, store)