import logging
import threading

from app.clients.ms1_client import Ms1Client
from app.clients.ollama_client import OllamaClient
from app.core.config import Settings
from app.rag.chunker import NoteChunker
from app.schemas import IndexOperationResponse, NoteSyncResult
from app.services.index_store import IndexStore

logger = logging.getLogger(__name__)


class IndexingService:
    def __init__(
        self,
        settings: Settings,
        ms1_client: Ms1Client,
        ollama_client: OllamaClient,
        chunker: NoteChunker,
        store: IndexStore,
    ) -> None:
        self._settings = settings
        self._ms1_client = ms1_client
        self._ollama_client = ollama_client
        self._chunker = chunker
        self._store = store
        # Serializes index writes between the event consumer thread and API operations.
        self._index_lock = threading.Lock()

    def sync_note(self, note_id: int) -> NoteSyncResult:
        with self._index_lock:
            note = self._ms1_client.fetch_note(note_id)
            if note is None:
                self._store.delete_note(note_id)
                logger.info("Note %s deleted in MS1; removed from index", note_id)
                return NoteSyncResult(note_id=note_id, action="deleted")

            current_state = self._store.read_note_state(note_id)
            if current_state is not None and current_state.is_current(
                note.source_hash, self._settings.indexing_version
            ):
                logger.info("Note %s already up to date; skipping", note_id)
                return NoteSyncResult(note_id=note_id, action="skipped")

            self._index_note(note.id, note.title, note.content, note.source_hash)
            return NoteSyncResult(note_id=note_id, action="indexed")

    def reconcile_index(self) -> IndexOperationResponse:
        with self._index_lock:
            return self._reconcile_index_locked()

    def rebuild_index(self) -> IndexOperationResponse:
        with self._index_lock:
            return self._rebuild_index_locked()

    def _reconcile_index_locked(self) -> IndexOperationResponse:
        metadata_items = self._ms1_client.fetch_index_metadata()
        index_state = self._store.read_index_state()

        indexed_note_ids: list[int] = []
        deleted_note_ids: list[int] = []
        skipped_note_ids: list[int] = []

        ms1_note_ids = {item.note_id for item in metadata_items}

        for item in metadata_items:
            current_state = index_state.get(str(item.note_id))
            if current_state is not None and current_state.is_current(
                item.source_hash, self._settings.indexing_version
            ):
                skipped_note_ids.append(item.note_id)
                continue

            note = self._ms1_client.fetch_note(item.note_id)
            if note is None:
                self._store.delete_note(item.note_id)
                deleted_note_ids.append(item.note_id)
                continue

            self._index_note(note.id, note.title, note.content, note.source_hash)
            indexed_note_ids.append(item.note_id)

        for indexed_note_id in index_state:
            as_int = int(indexed_note_id)
            if as_int not in ms1_note_ids:
                self._store.delete_note(as_int)
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
        self._store.reset()

        indexed_note_ids: list[int] = []
        deleted_note_ids: list[int] = []

        for item in metadata_items:
            note = self._ms1_client.fetch_note(item.note_id)
            if note is None:
                deleted_note_ids.append(item.note_id)
                continue
            self._index_note(note.id, note.title, note.content, note.source_hash)
            indexed_note_ids.append(item.note_id)

        logger.info("Rebuild complete: indexed=%s", len(indexed_note_ids))
        return IndexOperationResponse(
            indexed_note_ids=sorted(set(indexed_note_ids)),
            deleted_note_ids=sorted(set(deleted_note_ids)),
            skipped_note_ids=[],
            total_ms1_notes=len(metadata_items),
        )

    def _index_note(self, note_id: int, title: str, content: str, source_hash: str) -> None:
        chunks = self._chunker.chunk_note(title, content)
        if not chunks:
            logger.info("Skipping empty note %s", note_id)
            self._store.delete_note(note_id)
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

        self._store.replace_note_chunks(note_id, ids, documents, embeddings, metadatas)
        logger.info("Indexed note %s into %s chunks", note_id, len(chunks))
