# Mnemo — Target Architecture

## Goal

Build a compact portfolio project demonstrating full-stack development, polyglot microservices, asynchronous messaging, and AI/RAG integration.

## Architecture

```text
                    React + TypeScript UI
                       |             |
                      REST          REST
                       v             v
              +----------------+  +----------------+
              | MS1: Knowledge |  | MS2: RAG       |
              | Java / Spring  |  | Python / FastAPI|
              +-------+--------+  +--------+-------+
                      |                    |
                      v                    v
                 PostgreSQL             ChromaDB
                      |                    ^
                      |   Note events      |
                      +----> RabbitMQ -----+

   MS1 --> Ollama (summaries, tags)    MS2 --> Ollama (embeddings, answers)
```

Detailed MS2 design: [architecture-plan-ms2-update.md](architecture-plan-ms2-update.md).

## 1. Frontend

- [x] React + TypeScript UI.
- [x] Note management UI: list, search note title/content/tags, create, edit, and delete notes through MS1.
- [x] Display summaries and tags already stored on a note.
- [x] Trigger AI enrichment from the UI for a saved note.
- [x] RAG chatbot UI with Notes/Chat navigation, source references, and in-session chat history (kept in `sessionStorage`).
- [x] Calls MS1 through REST; local development uses the Vite proxy, with direct CORS access configurable.
- [x] Calls MS2 through REST (`/api/v1/chat/query`) and supports manual index actions (`/api/v1/admin/index/reconcile`, `/api/v1/admin/index/rebuild`).

## 2. MS1 — Knowledge Service (core done; MS2 integration work pending)

- **Stack:** Java 25, Spring Boot 4, Spring Data JPA / Hibernate.
- **Database:** PostgreSQL; source of truth for notes and tags.
- **Responsibilities:**
  - [x] Note CRUD API (list, read, create, update, delete).
  - [x] Persisted tags and note-tag associations, including tags created by enrichment; standalone tag CRUD API is not implemented.
  - [x] Input validation and centralized exception handling.
  - [x] AI enrichment through Ollama: generate summaries and suggest tags; persist results.
  - [x] Add a persisted `source_hash` (title + content), recomputed whenever title or content changes.
  - [x] Index-metadata endpoint (`note_id`, `source_hash`) for MS2 reconciliation (`GET /api/v1/notes/index-metadata`).
  - [x] Publish versioned events when notes are created, updated, or deleted.
  - [ ] Structured application logging (basic SLF4J application logs are present).
  - [x] OpenAPI / Swagger API documentation.
  - [ ] Optional API pagination, server-side text search, and tag filtering (the UI currently searches its loaded notes locally).

## 3. MS2 — RAG Service

- **Status:** Implemented (indexing, RabbitMQ events, reconcile/rebuild, chat query); containerized in Compose; UI integration completed.
- **Stack:** Python, FastAPI, Ollama (`qwen3-embedding:0.6b` embeddings, `qwen3:4b` answers), Qwen3-Embedding tokenizer (`tokenizers`) for chunking.
- **Database:** ChromaDB for embeddings and vector-index data.
- **Responsibilities:**
  - [x] Consume note events and update the vector index.
  - [x] Fetch notes from MS1 through REST for initial indexing and full reindexing.
  - [x] Run retrieval and answer generation for the chatbot.
  - [x] Return answers with references to source notes.
  - [x] Structured application logging.
  - [x] OpenAPI documentation through FastAPI's built-in support.
  - [x] Process events idempotently: always fetch the current note from MS1 and compare `source_hash`, so duplicate or out-of-order events are harmless.
- [x] **Indexing scope:** Use note `title` and `content`; exclude summaries and tags initially.
- [x] **Indexing versioning:** Reindex when note `source_hash` changes or when indexing configuration changes (chunk size, overlap, splitter strategy, embedding model).
- [x] **RAG pipeline:** Embeddings, vector search, context construction, and LLM generation.
- [x] **API scope:** Keep chat endpoint user-facing; place index rebuild/reconcile under admin endpoints with a static API key from an environment variable.

## 4. Communication

- **UI ↔ MS1:** [x] REST note CRUD and UI-triggered enrichment. [ ] UI tag filtering.
- **UI ↔ MS2:** [x] REST for chat requests and manual admin index actions.
- **MS1 → MS2:** [x] RabbitMQ events (`NoteCreated`, `NoteUpdated`, `NoteDeleted`).
- **MS2 → MS1:** [x] REST for initial indexing and full reindexing.
- **MS2 → Ollama:** [x] REST for embeddings and answer generation.
- **Event contract:** Define a versioned payload with `event_id`, `event_type`, `occurred_at`, and `note_id`. The event is only a change trigger; MS2 fetches the current note state from MS1.
- The vector index is derived data; MS1 remains the source of truth.
- Index updates are eventually consistent with PostgreSQL.

## 5. Infrastructure and Quality

- [x] Docker Compose for local development with PostgreSQL, RabbitMQ, MS1, and MS2.
- [x] Separate Docker images for MS1 and MS2 (multi-stage Dockerfiles, built by Compose); UI containerization optional.
- [x] GitHub Actions CI for builds and tests (`.github/workflows/ci.yml`: MS1, MS2, and UI jobs on push to `main` and on PRs).
- [x] MS1 persistence integration tests, MS2 unit/API tests (pytest), and isolated cross-service integration tests (`tests/e2e`, also run in CI).
- [x] OpenAPI / Swagger documentation for API exploration.
- [ ] Structured logs for debugging and operations (MS2 supports JSON logs; MS1 has basic SLF4J logs only).
- [x] Retry and dead-letter handling for RabbitMQ consumers in MS2.
- [x] PostgreSQL persistent volume in Docker Compose; backup procedure is not set up.
- [ ] HTTPS and production secret management.
- [ ] Consider the Transactional Outbox Pattern later for reliable event publishing.

## Design Principles

- Clear domain boundaries and independent deployability.
- Each service owns its data; no direct cross-service database access.
- Keep the initial RAG implementation simple.
- Defer advanced RAG, Kubernetes, and additional infrastructure until needed.

## Phases of Implementation

1. [x] MS1 — Knowledge Service (core done)
2. [x] UI for note management
3. [x] MS1 prerequisites for MS2 (`source_hash`, index-metadata endpoint)
4. [x] MS2 — RAG Service (manual/scheduled reconcile + query first)
5. [x] MS1 ↔ MS2 integration via RabbitMQ incremental events
6. [x] UI for RAG chatbot
7. [x] CI setup (GitHub Actions builds and tests all three services)
8. [x] Cross-service integration tests (MS1 → RabbitMQ → MS2 → chat), run in CI
9. [ ] MS1 structured (JSON) logging
10. [ ] Optional: MS1 pagination, server-side search, and tag filtering, plus UI tag filtering
11. [ ] Optional: CD (publish Docker images), HTTPS and production secret management, Transactional Outbox, PostgreSQL backup procedure
