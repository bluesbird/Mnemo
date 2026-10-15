import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI

from app.chunker import NoteChunker
from app.config import Settings, get_settings
from app.ms1_client import Ms1Client
from app.ollama_client import OllamaClient
from app.rag_service import RagService
from app.schemas import ChatQueryRequest, ChatQueryResponse, HealthResponse, IndexOperationResponse
from app.security import require_admin_api_key

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

app = FastAPI(
    title="MS2 RAG Service",
    version="0.1.0",
    description="RAG service for indexing MS1 notes and answering questions with references.",
)


@lru_cache
def get_rag_service() -> RagService:
    settings = get_settings()
    return RagService(
        settings=settings,
        ms1_client=Ms1Client(settings),
        ollama_client=OllamaClient(settings),
        chunker=NoteChunker(settings),
    )


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings: Settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name, env=settings.app_env)


@app.post(
    "/api/v1/admin/index/reconcile",
    response_model=IndexOperationResponse,
    dependencies=[Depends(require_admin_api_key)],
)
def reconcile_index(
    rag_service: Annotated[RagService, Depends(get_rag_service)],
) -> IndexOperationResponse:
    return rag_service.reconcile_index()


@app.post(
    "/api/v1/admin/index/rebuild",
    response_model=IndexOperationResponse,
    dependencies=[Depends(require_admin_api_key)],
)
def rebuild_index(
    rag_service: Annotated[RagService, Depends(get_rag_service)],
) -> IndexOperationResponse:
    return rag_service.rebuild_index()


@app.post("/api/v1/chat/query", response_model=ChatQueryResponse)
def chat_query(
    request: ChatQueryRequest,
    rag_service: Annotated[RagService, Depends(get_rag_service)],
) -> ChatQueryResponse:
    settings = get_settings()
    top_k = request.top_k or settings.retrieval_top_k_default
    return rag_service.answer_query(request.question, top_k=top_k)
