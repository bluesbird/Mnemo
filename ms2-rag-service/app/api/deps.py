from functools import lru_cache

from app.clients.ms1_client import Ms1Client
from app.clients.ollama_client import OllamaClient
from app.core.config import get_settings
from app.rag.chunker import NoteChunker
from app.services.index_store import IndexStore
from app.services.indexing_service import IndexingService
from app.services.query_service import QueryService


@lru_cache
def get_index_store() -> IndexStore:
    return IndexStore(get_settings())


@lru_cache
def get_ollama_client() -> OllamaClient:
    return OllamaClient(get_settings())


@lru_cache
def get_indexing_service() -> IndexingService:
    settings = get_settings()
    return IndexingService(
        settings=settings,
        ms1_client=Ms1Client(settings),
        ollama_client=get_ollama_client(),
        chunker=NoteChunker(settings),
        store=get_index_store(),
    )


@lru_cache
def get_query_service() -> QueryService:
    return QueryService(get_settings(), get_ollama_client(), get_index_store())
