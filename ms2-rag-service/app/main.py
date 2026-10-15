import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.chunker import NoteChunker
from app.config import Settings, get_settings
from app.events import NoteEventConsumer
from app.logging_config import configure_logging
from app.ms1_client import Ms1Client
from app.ollama_client import OllamaClient
from app.rag_service import RagService
from app.schemas import ChatQueryRequest, ChatQueryResponse, HealthResponse, IndexOperationResponse
from app.security import require_admin_api_key

configure_logging(get_settings().log_format)
logger = logging.getLogger(__name__)


@lru_cache
def get_rag_service() -> RagService:
    settings = get_settings()
    return RagService(
        settings=settings,
        ms1_client=Ms1Client(settings),
        ollama_client=OllamaClient(settings),
        chunker=NoteChunker(settings),
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    consumer: NoteEventConsumer | None = None
    if settings.rabbitmq_enabled:
        consumer = NoteEventConsumer(settings, get_rag_service().sync_note)
        consumer.start()
    yield
    if consumer is not None:
        consumer.stop()


app = FastAPI(
    title="MS2 RAG Service",
    version="0.1.0",
    description="RAG service for indexing MS1 notes and answering questions with references.",
    lifespan=lifespan,
)


@app.exception_handler(httpx.HTTPError)
def upstream_error_handler(_: Request, exc: httpx.HTTPError) -> JSONResponse:
    logger.error("Upstream call failed: %s", exc)
    return JSONResponse(status_code=502, content={"detail": "An upstream dependency (MS1 or Ollama) failed or is unavailable."})


@app.exception_handler(Exception)
def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


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
