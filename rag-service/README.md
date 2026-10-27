# RAG Service

Python/FastAPI service that maintains the vector index and answers questions with grounded sources.

## Role in the system

- Builds and updates ChromaDB index entries from Knowledge service notes.
- Consumes note change events from RabbitMQ for incremental sync.
- Serves retrieval-augmented chat answers with source note references.
- Offers manual reconcile/rebuild operations for index recovery.

## Main API

- `GET /api/v1/health`
- `POST /api/v1/chat/query`
- `POST /api/v1/index/reconcile`
- `POST /api/v1/index/rebuild`

FastAPI docs: `/docs`

## Key configuration

All variables are `RAG_`-prefixed.

- `RAG_KNOWLEDGE_BASE_URL`
- `RAG_OLLAMA_BASE_URL`
- `RAG_CHAT_PROVIDER=ollama|groq`
- `RAG_GROQ_API_KEY` (required when `RAG_CHAT_PROVIDER=groq`)
- `RAG_EMBEDDING_MODEL` (default `qwen3-embedding:0.6b`)
- `RAG_CHAT_MODEL` (default `qwen3:4b`)
- `RAG_CHUNK_SIZE_TOKENS`, `RAG_CHUNK_OVERLAP_TOKENS`
- `RAG_RABBITMQ_ENABLED` + RabbitMQ host/queue settings
- `RAG_LOG_FORMAT=text|json`

## Run and test

From `rag-service`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```
