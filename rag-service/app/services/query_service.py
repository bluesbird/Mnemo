import logging

from app.clients.ollama_client import OllamaClient
from app.clients.chat_client import ChatClient
from app.core.config import Settings
from app.rag.retrieval import Candidate, fuse, keyword_score, keywords, normalize_query
from app.schemas import ChatQueryResponse, ChatSourceReference
from app.persistence.index_store import IndexStore

logger = logging.getLogger(__name__)

NO_ANSWER = "I don't know based on the provided notes."


class QueryService:
    def __init__(
        self, settings: Settings, ollama_client: OllamaClient, store: IndexStore,
        chat_client: ChatClient | None = None,
    ) -> None:
        self._settings = settings
        self._ollama_client = ollama_client
        self._chat_client = chat_client if chat_client is not None else ollama_client
        self._store = store

    def answer_query(self, question: str, top_k: int) -> ChatQueryResponse:
        collection = self._store.collection()
        query = normalize_query(question) or question.strip()
        query_embedding = self._ollama_client.embed_query(query)

        dense = collection.query(
            query_embeddings=[query_embedding],
            n_results=max(top_k * 3, 12),
            include=["documents", "metadatas", "distances"],
        )
        candidates: dict[str, Candidate] = {}
        ids = (dense.get("ids") or [[]])[0]
        documents = (dense.get("documents") or [[]])[0]
        metadatas = (dense.get("metadatas") or [[]])[0]
        distances = (dense.get("distances") or [[]])[0]
        for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            candidates[chunk_id] = Candidate(
                chunk_id, document, metadata or {}, dense_score=max(0.0, 1.0 - float(distance))
            )

        # Keyword pass over all chunks: short or generic questions embed poorly.
        query_keywords = keywords(query)
        if query_keywords:
            stored = collection.get(include=["documents", "metadatas"])
            for chunk_id, document, metadata in zip(
                stored.get("ids") or [], stored.get("documents") or [], stored.get("metadatas") or []
            ):
                title = (metadata or {}).get("note_title", "")
                score = keyword_score(query_keywords, f"{title} {document}")
                if score > 0:
                    candidate = candidates.setdefault(chunk_id, Candidate(chunk_id, document, metadata or {}))
                    candidate.keyword_score = score

        selected = fuse(candidates.values(), self._settings.retrieval_min_score, top_k)
        if not selected:
            logger.info("No relevant chunks for the question; skipping LLM call")
            return ChatQueryResponse(answer=NO_ANSWER, sources=[])

        context_parts: list[str] = []
        sources: list[ChatSourceReference] = []
        for position, candidate in enumerate(selected, start=1):
            metadata = candidate.metadata
            note_title = str(metadata.get("note_title", ""))
            context_parts.append(f"Note {position}: {note_title}\n{candidate.document}")
            sources.append(
                ChatSourceReference(
                    note_id=int(metadata.get("note_id", 0)),
                    note_title=note_title,
                    chunk_index=int(metadata.get("chunk_index", 0)),
                    source_hash=str(metadata.get("source_hash", "")),
                    score=candidate.dense_score,
                    excerpt=candidate.document[:300].strip(),
                )
            )

        answer = self._chat_client.chat_answer(question, "\n\n".join(context_parts))
        if answer.lower().startswith("i don't know"):
            return ChatQueryResponse(answer=answer, sources=[])
        return ChatQueryResponse(answer=answer, sources=sources)
