import logging
import threading
from dataclasses import dataclass

import chromadb
from chromadb.api.models.Collection import Collection

from app.chunker import NoteChunker
from app.config import Settings
from app.ms1_client import Ms1Client
from app.ollama_client import OllamaClient
from app.schemas import ChatQueryResponse, ChatSourceReference, IndexOperationResponse, NoteSyncResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IndexedNoteState:
    source_hash: str
    indexing_version: str


class RagService:
    def __init__(
        self,
        settings: Settings,
        ms1_client: Ms1Client,
        ollama_client: OllamaClient,
        chunker: NoteChunker,
    ) -> None:
        self._settings = settings
        self._ms1_client = ms1_client
        self._ollama_client = ollama_client
        self._chunker = chunker
        self._chroma_client = chromadb.PersistentClient(path=settings.chroma_path)
        # Serializes index writes between the event consumer thread and admin endpoints.
        self._index_lock = threading.Lock()

    def sync_note(self, note_id: int) -> NoteSyncResult:
        with self._index_lock:
            collection = self._get_or_create_collection()
            note = self._ms1_client.fetch_note(note_id)
            if note is None:
                self._delete_note_chunks(collection, note_id)
                logger.info("Note %s deleted in MS1; removed from index", note_id)
                return NoteSyncResult(note_id=note_id, action="deleted")

            current_state = self._read_note_state(collection, note_id)
            if (
                current_state is not None
                and current_state.source_hash == note.source_hash
                and current_state.indexing_version == self._settings.indexing_version
            ):
                logger.info("Note %s already up to date; skipping", note_id)
                return NoteSyncResult(note_id=note_id, action="skipped")

            self._index_note(collection, note.id, note.title, note.content, note.source_hash)
            return NoteSyncResult(note_id=note_id, action="indexed")

    def reconcile_index(self) -> IndexOperationResponse:
        with self._index_lock:
            return self._reconcile_index_locked()

    def rebuild_index(self) -> IndexOperationResponse:
        with self._index_lock:
            return self._rebuild_index_locked()

    def _reconcile_index_locked(self) -> IndexOperationResponse:
        collection = self._get_or_create_collection()
        metadata_items = self._ms1_client.fetch_index_metadata()
        index_state = self._read_index_state(collection)

        indexed_note_ids: list[int] = []
        deleted_note_ids: list[int] = []
        skipped_note_ids: list[int] = []

        ms1_note_ids = {item.note_id for item in metadata_items}

        for item in metadata_items:
            note_key = str(item.note_id)
            current_state = index_state.get(note_key)
            if (
                current_state is not None
                and current_state.source_hash == item.source_hash
                and current_state.indexing_version == self._settings.indexing_version
            ):
                skipped_note_ids.append(item.note_id)
                continue

            note = self._ms1_client.fetch_note(item.note_id)
            if note is None:
                self._delete_note_chunks(collection, item.note_id)
                deleted_note_ids.append(item.note_id)
                continue

            self._index_note(collection, note.id, note.title, note.content, note.source_hash)
            indexed_note_ids.append(item.note_id)

        for indexed_note_id in index_state:
            as_int = int(indexed_note_id)
            if as_int not in ms1_note_ids:
                self._delete_note_chunks(collection, as_int)
                deleted_note_ids.append(as_int)

        logger.info(
            "Reconcile complete: indexed=%s deleted=%s skipped=%s",
            len(indexed_note_ids),
            len(deleted_note_ids),
            len(skipped_note_ids),
        )
        return IndexOperationResponse(
            indexed_note_ids=sorted(set(indexed_note_ids)),
            deleted_note_ids=sorted(set(deleted_note_ids)),
            skipped_note_ids=sorted(set(skipped_note_ids)),
            total_ms1_notes=len(metadata_items),
        )

    def _rebuild_index_locked(self) -> IndexOperationResponse:
        metadata_items = self._ms1_client.fetch_index_metadata()
        self._reset_collection()
        collection = self._get_or_create_collection()

        indexed_note_ids: list[int] = []
        deleted_note_ids: list[int] = []
        skipped_note_ids: list[int] = []

        for item in metadata_items:
            note = self._ms1_client.fetch_note(item.note_id)
            if note is None:
                deleted_note_ids.append(item.note_id)
                continue
            self._index_note(collection, note.id, note.title, note.content, note.source_hash)
            indexed_note_ids.append(item.note_id)

        logger.info("Rebuild complete: indexed=%s", len(indexed_note_ids))
        return IndexOperationResponse(
            indexed_note_ids=sorted(set(indexed_note_ids)),
            deleted_note_ids=sorted(set(deleted_note_ids)),
            skipped_note_ids=skipped_note_ids,
            total_ms1_notes=len(metadata_items),
        )

    def answer_query(self, question: str, top_k: int) -> ChatQueryResponse:
        collection = self._get_or_create_collection()
        query_embedding = self._ollama_client.embed_query(question)

        query_result = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = (query_result.get("documents") or [[]])[0]
        metadatas = (query_result.get("metadatas") or [[]])[0]
        distances = (query_result.get("distances") or [[]])[0]

        context_parts: list[str] = []
        sources: list[ChatSourceReference] = []

        for index, document in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) else {}
            distance = distances[index] if index < len(distances) else 1.0

            note_id = int(metadata.get("note_id", 0))
            note_title = str(metadata.get("note_title", ""))
            chunk_index = int(metadata.get("chunk_index", index))
            source_hash = str(metadata.get("source_hash", ""))
            score = max(0.0, 1.0 - float(distance))
            excerpt = document[:300].strip()

            context_parts.append(f"[Note {note_id} | chunk {chunk_index}]\n{document}")
            sources.append(
                ChatSourceReference(
                    note_id=note_id,
                    note_title=note_title,
                    chunk_index=chunk_index,
                    source_hash=source_hash,
                    score=score,
                    excerpt=excerpt,
                )
            )

        context = "\n\n".join(context_parts)
        answer = self._ollama_client.chat_answer(question, context)
        return ChatQueryResponse(answer=answer, sources=sources)

    def _index_note(
        self,
        collection: Collection,
        note_id: int,
        title: str,
        content: str,
        source_hash: str,
    ) -> None:
        chunks = self._chunker.chunk_note(title, content)
        if not chunks:
            logger.info("Skipping empty note %s", note_id)
            self._delete_note_chunks(collection, note_id)
            return

        documents = [chunk.text for chunk in chunks]
        embeddings = self._ollama_client.embed_documents(documents)
        ids = [f"note-{note_id}-chunk-{chunk.index}" for chunk in chunks]
        metadatas = [
            {
                "note_id": str(note_id),
                "note_title": title,
                "chunk_index": int(chunk.index),
                "source_hash": source_hash,
                "indexing_version": self._settings.indexing_version,
            }
            for chunk in chunks
        ]

        self._delete_note_chunks(collection, note_id)
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info("Indexed note %s into %s chunks", note_id, len(chunks))

    def _delete_note_chunks(self, collection: Collection, note_id: int) -> None:
        collection.delete(where={"note_id": str(note_id)})

    def _read_note_state(self, collection: Collection, note_id: int) -> IndexedNoteState | None:
        page = collection.get(where={"note_id": str(note_id)}, limit=1, include=["metadatas"])
        metadatas = page.get("metadatas") or []
        if not metadatas:
            return None
        source_hash = metadatas[0].get("source_hash")
        indexing_version = metadatas[0].get("indexing_version")
        if isinstance(source_hash, str) and isinstance(indexing_version, str):
            return IndexedNoteState(source_hash=source_hash, indexing_version=indexing_version)
        return None

    def _read_index_state(self, collection: Collection) -> dict[str, IndexedNoteState]:
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

    def _reset_collection(self) -> None:
        try:
            self._chroma_client.delete_collection(name=self._settings.chroma_collection_name)
        except Exception:  # noqa: BLE001
            return

    def _get_or_create_collection(self) -> Collection:
        return self._chroma_client.get_or_create_collection(
            name=self._settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
