import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.api.deps import get_indexing_service, get_query_service
from app.main import app


class FakeIndexing:
    def reconcile_index(self):
        return {
            "indexed_note_ids": [1],
            "deleted_note_ids": [],
            "skipped_note_ids": [],
            "total_ms1_notes": 1,
        }

    def rebuild_index(self):
        return {
            "indexed_note_ids": [1],
            "deleted_note_ids": [],
            "skipped_note_ids": [],
            "total_ms1_notes": 1,
        }


class BoomQuery:
    def answer_query(self, question, top_k):
        raise httpx.ConnectError("ollama down")


class BoomIndexing:
    def reconcile_index(self):
        raise RuntimeError("boom")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MS2_RABBITMQ_ENABLED", "false")
    get_settings.cache_clear()
    app.dependency_overrides[get_query_service] = lambda: BoomQuery()
    app.dependency_overrides[get_indexing_service] = lambda: BoomIndexing()
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_health(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_index_operations_are_public(client):
    app.dependency_overrides[get_indexing_service] = lambda: FakeIndexing()

    for operation in ("reconcile", "rebuild"):
        response = client.post(f"/api/v1/index/{operation}")
        assert response.status_code == 200
        assert response.json() == {
            "indexed_note_ids": [1],
            "deleted_note_ids": [],
            "skipped_note_ids": [],
            "total_ms1_notes": 1,
        }


def test_admin_index_paths_are_not_aliased(client):
    assert client.post("/api/v1/admin/index/reconcile").status_code == 404
    assert client.post("/api/v1/admin/index/rebuild").status_code == 404


def test_unhandled_error_returns_500_json(client):
    response = client.post("/api/v1/index/reconcile")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error."}


def test_upstream_failure_returns_502(client):
    response = client.post("/api/v1/chat/query", json={"question": "hi"})
    assert response.status_code == 502


def test_provider_quota_returns_explicit_unavailable_error(client):
    class QuotaQuery:
        def answer_query(self, question, top_k):
            request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("quota exceeded", request=request, response=response)

    app.dependency_overrides[get_query_service] = lambda: QuotaQuery()
    response = client.post("/api/v1/chat/query", json={"question": "hi"})
    assert response.status_code == 503
    assert response.json() == {"detail": "AI provider quota exceeded. Please try again later."}


def test_empty_question_is_rejected(client):
    assert client.post("/api/v1/chat/query", json={"question": ""}).status_code == 422


def test_question_length_boundary():
    from pydantic import ValidationError
    from app.schemas import ChatQueryRequest

    assert len(ChatQueryRequest(question="q" * 500).question) == 500
    with pytest.raises(ValidationError):
        ChatQueryRequest(question="q" * 501)
