# Personal Knowledge Hub — Target Architecture

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
```

## 1. Frontend
- React + TypeScript.
- One shared UI for note management and the RAG chatbot.
- Calls both microservices through REST.

## 2. MS1 — Knowledge Service (done for now)
- **Stack:** Java 25, Spring Boot 4, Spring Data JPA / Hibernate.
- **Database:** PostgreSQL; source of truth for notes and tags.
- **Responsibilities:**
  - Note and tag CRUD.
  - Input validation and centralized exception handling.
  - AI enrichment: generate summaries and suggest tags; persist results.
  - Publish events when notes are created, updated, or deleted.
  - Structured application logging.
  - OpenAPI / Swagger API documentation.
  - Optional: Pagination, basic text search, and tag filtering.

## 3. MS2 — RAG Service
- **Stack:** Python, FastAPI.
- **Database:** ChromaDB for embeddings and vector-index data.
- **Responsibilities:**
  - Consume note events and update the vector index.
  - Fetch notes from MS1 through REST for initial indexing and full reindexing.
  - Run retrieval and answer generation for the chatbot.
  - Return answers with references to source notes.
  - Structured application logging.
  - OpenAPI documentation through FastAPI's built-in support.
- **Indexing scope:** Use note `title` and `content`; exclude summaries and tags initially.
- **RAG pipeline:** Embeddings, vector search, context construction, and LLM generation.

## 4. Communication
- **UI ↔ MS1:** REST for notes, tags, filtering, and enrichment.
- **UI ↔ MS2:** REST for chat requests.
- **MS1 → MS2:** RabbitMQ events (`NoteCreated`, `NoteUpdated`, `NoteDeleted`).
- **MS2 → MS1:** REST for initial indexing and full reindexing.
- The vector index is derived data; MS1 remains the source of truth.
- Index updates are eventually consistent with PostgreSQL.

## 5. Infrastructure and Quality
- Docker Compose for local development and deployment.
- Separate Docker images for MS1 and MS2; optionally containerize the UI.
- GitHub Actions CI for builds and tests.
- Integration tests.
- OpenAPI / Swagger documentation for API exploration.
- Structured logs for debugging and operations.
- Persistent volumes and backups for stateful services.
- HTTPS and secrets supplied through environment variables in production.
- Consider the Transactional Outbox Pattern later for reliable event publishing.

## Design Principles
- Clear domain boundaries and independent deployability.
- Each service owns its data; no direct cross-service database access.
- Keep the initial RAG implementation simple.
- Defer advanced RAG, Kubernetes, and additional infrastructure until needed.

## Phases of Implementation
1. MS1 — Knowledge Service (done - for now)
2. UI for note management
3. MS2 — RAG Service
4. MS1 ↔ MS2 integration via RabbitMQ
5. UI for RAG chatbot
6. Integration tests and CI/CD setup
