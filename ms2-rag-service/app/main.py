import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.deps import get_indexing_service
from app.api.routes import router
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.messaging.consumer import NoteEventConsumer

configure_logging(get_settings().log_format)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    consumer: NoteEventConsumer | None = None
    if settings.rabbitmq_enabled:
        consumer = NoteEventConsumer(settings, get_indexing_service().sync_note)
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
app.include_router(router)


@app.exception_handler(httpx.HTTPError)
def upstream_error_handler(_: Request, exc: httpx.HTTPError) -> JSONResponse:
    logger.error("Upstream call failed: %s", exc)
    return JSONResponse(status_code=502, content={"detail": "An upstream dependency (MS1 or Ollama) failed or is unavailable."})


@app.exception_handler(Exception)
def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})
