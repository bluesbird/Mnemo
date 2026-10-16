from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_indexing_service, get_query_service
from app.api.security import require_admin_api_key
from app.core.config import Settings, get_settings
from app.schemas import ChatQueryRequest, ChatQueryResponse, HealthResponse, IndexOperationResponse
from app.services.indexing_service import IndexingService
from app.services.query_service import QueryService

router = APIRouter(prefix="/api/v1")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings: Settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name, env=settings.app_env)


@router.post(
    "/admin/index/reconcile",
    response_model=IndexOperationResponse,
    dependencies=[Depends(require_admin_api_key)],
)
def reconcile_index(
    indexing: Annotated[IndexingService, Depends(get_indexing_service)],
) -> IndexOperationResponse:
    return indexing.reconcile_index()


@router.post(
    "/admin/index/rebuild",
    response_model=IndexOperationResponse,
    dependencies=[Depends(require_admin_api_key)],
)
def rebuild_index(
    indexing: Annotated[IndexingService, Depends(get_indexing_service)],
) -> IndexOperationResponse:
    return indexing.rebuild_index()


@router.post("/chat/query", response_model=ChatQueryResponse)
def chat_query(
    request: ChatQueryRequest,
    query: Annotated[QueryService, Depends(get_query_service)],
) -> ChatQueryResponse:
    top_k = request.top_k or get_settings().retrieval_top_k_default
    return query.answer_query(request.question, top_k=top_k)
