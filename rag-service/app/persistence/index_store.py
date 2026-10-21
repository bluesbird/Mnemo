import logging
from dataclasses import dataclass

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IndexedNoteState:
    source_hash: str
    indexing_version: str

    def is_current(self, source_hash: str, indexing_version: str) -> bool:
        return self.source_hash == source_hash and self.indexing_version == indexing_version


class IndexStore:
    """ChromaDB access for the derived note-chunk index."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._chroma_client = chromadb.PersistentClient(path=settings.chroma_path)

    def collection(self) -> Collection:
        return self._chroma_client.get_or_create_collection(
            name=self._settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        try:
            self._chroma_client.delete_collection(name=self._settings.chroma_collection_name)
        except Exception:  # noqa: BLE001
            return

    def delete_note(self, note_id: int) -> None:
        self.collection().delete(where={"note_id": str(note_id)})

    def replace_note_chunks(
        self,
        note_id: int,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        self.delete_note(note_id)
        self.collection().upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def read_note_state(self, note_id: int) -> IndexedNoteState | None:
        page = self.collection().get(where={"note_id": str(note_id)}, limit=1, include=["metadatas"])
        metadatas = page.get("metadatas") or []
        if not metadatas:
            return None
        source_hash = metadatas[0].get("source_hash")
        indexing_version = metadatas[0].get("indexing_version")
        if isinstance(source_hash, str) and isinstance(indexing_version, str):
            return IndexedNoteState(source_hash=source_hash, indexing_version=indexing_version)
        return None

    def read_index_state(self) -> dict[str, IndexedNoteState]:
        collection = self.collection()
        state: dict[str, IndexedNoteState] = {}
        offset = 0
        batch_size = 500

        while True:
            page = collection.get(limit=batch_size, offset=offset, include=["metadatas"])
            metadatas = page.get("metadatas") or []
            if not metadatas:
                break

            for metadata in metadatas:
                note_id = metadata.get("note_id")
                source_hash = metadata.get("source_hash")
                indexing_version = metadata.get("indexing_version")
                if isinstance(note_id, str) and isinstance(source_hash, str) and isinstance(indexing_version, str):
                    state[note_id] = IndexedNoteState(source_hash=source_hash, indexing_version=indexing_version)

            if len(metadatas) < batch_size:
                break
            offset += len(metadatas)

        return state
