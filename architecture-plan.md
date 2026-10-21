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

   MS1 --> Ollama/Groq (manual summaries)
   MS2 --> Ollama (embeddings) + Ollama/Groq (answers)
```

Detailed MS2 design: [architecture-plan-ms2-update.md](architecture-plan-ms2-update.md).

Local development uses Ollama for all model calls. The
[public demo](https://mnemo-hub.duckdns.org) uses Groq for text generation and
host Ollama for embeddings. Deployment and verification:
[deploy/README.md](deploy/README.md), [deploy/plan.md](deploy/plan.md).

## 1. Frontend

- [x] React + TypeScript UI.
- [x] Note management UI: list, search note title/content, create, edit, and delete notes through MS1.
- [x] Display the optional AI summary, hidden while editing and cleared on update.
- [x] Manually summarize a saved note from the UI; saving never invokes AI.
- [x] RAG chatbot UI with Notes/Chat navigation, source references, and in-session chat history (kept in `sessionStorage`).
- [x] Calls MS1 through REST; local development uses the Vite proxy, with direct CORS access configurable.
- [x] Calls MS2 through REST (`/api/v1/chat/query`) and supports public index actions (`/api/v1/index/reconcile`, `/api/v1/index/rebuild`).
- [x] Multi-stage UI image: Node builds static assets; nginx serves them and proxies same-origin `/api` to MS1 and `/rag-api` to MS2 (prefix stripped). Hash routing and the Vite development workflow are unchanged.
- [x] Validated runtime upstream origins; the UI proxy discards browser-supplied API-key headers.

## 2. MS1 — Knowledge Service

- **Stack:** Java 25, Spring Boot 4, Spring Data JPA / Hibernate.
- **Database:** PostgreSQL; source of truth for notes and optional summaries.
- **Layering:** controllers validate HTTP request DTOs and map notes to response
  DTOs. Application services accept plain inputs and return domain notes or
  application-level index metadata without
  depending on API DTOs. Business rules, transactions and event enqueueing stay
  in the application layer; JPA entities/repositories remain inside MS1.
- **Responsibilities:**
  - [x] Note CRUD API (list, read, create, update, delete).
  - [x] Input validation and centralized exception handling.
  - [x] Manual summarization through Ollama locally or Groq in deployment: one model call via `POST /api/v1/notes/{id}/summarize`. Failed or incomplete responses return explicit errors without replacing the existing summary. Tags have been removed from the domain, API and database through Flyway V2.
  - [x] Add a persisted `source_hash` (title + content), recomputed whenever title or content changes.
  - [x] Index-metadata endpoint (`note_id`, `source_hash`) for MS2 reconciliation (`GET /api/v1/notes/index-metadata`).
  - [x] Publish versioned events when notes are created, updated, or deleted.
  - [x] Structured application logging (Spring Boot ECS JSON output in Compose; readable text for host-run development).
  - [x] OpenAPI / Swagger API documentation.
  - The UI searches the loaded notes locally. With a 100-note collection limit,
    backend pagination and server-side search are not planned.

## 3. MS2 — RAG Service

- **Status:** Implemented (indexing, RabbitMQ events, reconcile/rebuild, chat query); containerized in Compose; UI integration completed.
- **Stack:** Python, FastAPI, Ollama (`qwen3-embedding:0.6b` embeddings, local `qwen3:4b` answers), Groq for deployed answers, Qwen3-Embedding tokenizer (`tokenizers`) for chunking.
- **Database:** ChromaDB for embeddings and vector-index data.
- **Responsibilities:**
  - [x] Consume note events and update the vector index.
  - [x] Fetch notes from MS1 through REST for initial indexing and full reindexing.
  - [x] Run retrieval and answer generation for the chatbot.
  - [x] Return answers with references to source notes.
  - [x] Structured application logging.
  - [x] OpenAPI documentation through FastAPI's built-in support.
  - [x] Process events idempotently: always fetch the current note from MS1 and compare `source_hash`, so duplicate or out-of-order events are harmless.
- [x] **Indexing scope:** Use note `title` and `content`; exclude generated summaries.
- [x] **Indexing versioning:** Reindex when note `source_hash` changes or when indexing configuration changes (chunk size, overlap, splitter strategy, embedding model).
- [x] **RAG pipeline:** Embeddings, vector search, context construction, and LLM generation.
- [x] **API scope:** Chat and index rebuild/reconcile are public user-facing endpoints.

## 4. Communication

- **UI ↔ MS1:** [x] REST note CRUD and UI-triggered summarization.
- **UI ↔ MS2:** [x] REST for chat requests and manual index actions.
- **MS1 → MS2:** [x] RabbitMQ events (`NoteCreated`, `NoteUpdated`, `NoteDeleted`).
- **MS2 → MS1:** [x] REST for initial indexing and full reindexing.
- **MS2 → Ollama/Groq:** [x] REST for Ollama embeddings and provider-selected answer generation.
- **Event contract:** Define a versioned payload with `event_id`, `event_type`, `occurred_at`, and `note_id`. The event is only a change trigger; MS2 fetches the current note state from MS1.
- The vector index is derived data; MS1 remains the source of truth.
- Index updates are eventually consistent with PostgreSQL.

## 5. Infrastructure and Quality

- [x] Docker Compose for local development with PostgreSQL, RabbitMQ, MS1, MS2 and UI (`http://localhost:5173`, UI bound to loopback).
- [x] Separate multi-stage Docker images for MS1, MS2 and UI, built by Compose.
- [x] GitHub Actions CI for builds and tests (`.github/workflows/ci.yml`: MS1, MS2, and UI jobs on push to `main` and on PRs).
- [x] MS1 persistence integration tests, MS2 unit/API tests (pytest), and isolated cross-service integration tests (`tests/e2e`, also run in CI).
- [x] UI container build and nginx smoke checks in that isolated E2E stack: static assets, real service proxy lifecycle, wire-level path/method/body/status/header checks and unsafe runtime configuration rejection; no real model downloads.
- [x] OpenAPI / Swagger documentation for API exploration.
- [x] Structured logs for debugging and operations (MS1 ECS JSON and MS2 JSON enabled in Compose; no centralized collection or cross-service tracing).
- [x] Retry and dead-letter handling for RabbitMQ consumers in MS2.
- [x] PostgreSQL persistent volume in Docker Compose; backup procedure is not set up.
- [x] Public HTTPS deployment with Caddy, server-side secrets, private backend ports and request limits; anonymous shared-demo APIs, authenticated operator-only reset.
- [x] GitHub Actions CD: deploy pushes to `main` after all four CI jobs pass, with SSH host verification and local/public health checks.
- [x] Transactional outbox for reliable event publishing; broker-outage/restart recovery verified in the isolated E2E stack.

## Design Principles

- Clear domain boundaries and independent deployability.
- Each service owns its data; no direct cross-service database access.
- Keep the initial RAG implementation simple.
- Keep the existing PostgreSQL/RabbitMQ/Compose stack; no Kubernetes, CDC platform,
  centralized logging service or additional deployment services are planned.

## Phases of Implementation

1. [x] MS1 — Knowledge Service (core done)
2. [x] UI for note management
3. [x] MS1 prerequisites for MS2 (`source_hash`, index-metadata endpoint)
4. [x] MS2 — RAG Service (manual/scheduled reconcile + query first)
5. [x] MS1 ↔ MS2 integration via RabbitMQ incremental events
6. [x] UI for RAG chatbot
7. [x] CI setup (GitHub Actions builds and tests all three services)
8. [x] Cross-service integration tests (MS1 → RabbitMQ → MS2 → chat), run in CI
9. [x] MS1 structured (JSON) logging
10. [x] UI containerization and same-origin nginx proxy in Compose, validated in isolated CI E2E
11. [x] Versioned MS1 database migrations (Flyway), replacing Hibernate `ddl-auto=update` with a safe migration path for existing data

### Remaining priorities

Phase numbers are retained for reference; use the order below for the remaining work.

- **Phase 16 — RAG evaluation:** [x] Small real-model sanity check completed: 10 fixed notes and 10 questions, with documented scoring and limitations in [evaluation/results.md](evaluation/results.md). Scores are assistant-reviewed, not independently human-validated. Scope and procedure: [evaluation-plan.md](evaluation-plan.md).
- **Phase 18 — Public deployment:** [x] Public demo deployed and verified for the agreed scope: HTTPS, server-side secrets, restricted backend exposure, request limits, index recovery and reset authentication. Note/chat/index actions intentionally remain anonymous; no account management. Automatic deployment after CI is working. Verification details and intentionally omitted destructive/reset/restart checks: [deploy/plan.md](deploy/plan.md).
- **Phases 12/13 — Transactional outbox and recovery verification:** [x] Implemented and verified locally in the isolated E2E stack: committed CRUD/reset events survive broker outages and MS1 restarts, then update the index without manual reconciliation. Public deployment of this change is pending.
- **Phase 15 — Release polish:** [ ] Keep startup instructions and model prerequisites accurate throughout development; finalize screenshots, architecture/limitations documentation, and a clean-start walkthrough after evaluation and any intended deployment safeguards are finished. Public hosting is not required for a repository-only release.

### Transactional outbox

- Flyway V3 adds `note_outbox`; V1/V2 are unchanged. Stored events include their
  stable event ID, routing key, attempt count and next-attempt timestamp.
  Nullable `note_id` has no foreign key, so deletion and reset events survive
  removal of notes. Reset does not delete pending events.
- Note create/update/delete and reset atomically commit their data and outbox
  events. Enqueue failure rolls back the mutation. Request handling never sends
  to RabbitMQ. The 100-note creation lock participates in this transaction;
  summarization still has no event or open transaction during the AI call.
- A one-second scheduler processes at most 20 due events per tick, each in its
  own transaction using `FOR UPDATE SKIP LOCKED`. It sends persistent messages
  with correlated confirms and mandatory returns. Only an ACK without a return
  deletes the row. Failures retain the event and retry indefinitely with
  exponential delays capped at five minutes and a bounded attempt counter.
- The row lock is held through the five-second confirmation wait. A crash
  releases it; acceptance before database commit can cause duplicate delivery.
  Transport correlations are unique per attempt; payload event IDs stay stable.
  This briefly occupies one database connection but avoids claim tokens/leases.
- MS2's existing durable queue, acknowledgements, retries/DLQ and current-state
  hashing handle duplicate/out-of-order events. Delivery is at-least-once, not
  exactly-once; publisher confirmation does not prove successful indexing.
  A VPS cron job reconciles nightly at 04:00 Europe/Berlin to repair drift or
  lost index entries. Manual reconcile/rebuild remains available for immediate
  repair; consumer/DLQ failures still need investigation.
- Focused tests cover transaction rollback, enqueue failure, confirms/returns/
  timeout, retries and row locking. The existing E2E runner also checks CRUD and
  reset during real broker outages, MS1 restarts, retained earlier reset events,
  drained queues and matching index metadata without repair calls.
- No new dependency, infrastructure service, API, UI or event archive.
  Pending-count/oldest-event queries and log/DLQ inspection are documented in
  [deploy/README.md](deploy/README.md#outbox-and-index-recovery).

### Optional / deferred work

- **Phase 14 — Backup and restore:** [ ] Defer while data is disposable; revisit before relying on Mnemo for real notes. Document and verify PostgreSQL restoration, then rebuild the derived Chroma index from MS1.
- **Optional release automation:** [ ] Publish versioned container images to GHCR through CI; not required for phase 15 or a complete portfolio release.
