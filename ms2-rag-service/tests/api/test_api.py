import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.api.deps import get_indexing_service, get_query_service
from app.main import app


class BoomQuery:
    def answer_query(self, question, top_k):
        raise httpx.ConnectError("ollama down")


class BoomIndexing:
    def reconcile_index(self):
        raise RuntimeError("boom")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MS2_ADMIN_API_KEY", "test-key")
    monkeypatch.setenv("MS2_RABBITMQ_ENABLED", "false")
    get_settings.cache_clear()
    app.dependency_overrides[get_query_service] = lambda: BoomQuery()
    app.dependency_overrides[get_indexing_service] = lambda: BoomIndexing()
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_health(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_admin_requires_api_key(client):
    assert client.post("/api/v1/admin/index/reconcile").status_code == 401


def test_unhandled_error_returns_500_json(client):
    response = client.post("/api/v1/admin/index/reconcile", headers={"X-API-Key": "test-key"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error."}


def test_upstream_failure_returns_502(client):
    response = client.post("/api/v1/chat/query", json={"question": "hi"})
    assert response.status_code == 502


def test_empty_question_is_rejected(client):
    assert client.post("/api/v1/chat/query", json={"question": ""}).status_code == 422
