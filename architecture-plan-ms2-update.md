# MS2 — RAG Service

## Goal

Build a Python-based RAG service that indexes notes from MS1 and answers questions using semantic search with references to source notes.

## Stack

- **Python** — application language
- **FastAPI** — REST API and automatic OpenAPI/Swagger documentation
- **ChromaDB** — vector store for chunk texts, embeddings, and metadata
- **Ollama** — local embedding model and chat LLM
- **RabbitMQ** — asynchronous note-change events from MS1
- **Docker** — containerization

No LangChain, separate chunk database, or sparse retrieval in V1.

## Model Stack (V1)

- **Embedding model:** `qwen3-embedding:0.6b` via Ollama (multilingual, long context, small enough for local CPU/GPU).
- **RAG LLM:** `qwen3:1.7b` via Ollama.
- **Tokenizer:** `Qwen/Qwen3-Embedding-0.6B` from Hugging Face, used only to count tokens for chunking (use the lightweight `tokenizers` package, not full `transformers`). Only the tokenizer files are downloaded; the model weights come from Ollama.
- Pin the tokenizer to a specific Hugging Face revision and cache the files locally (also in the Docker image) so chunking is reproducible and works offline. Include the tokenizer revision in `indexing_version`.
- Token counts are an approximation for the quantized Ollama model; keep headroom below the embedding context limit.
- Model names, `num_ctx`, and generation settings are configuration (environment variables), not hard-coded.
- Embedding model name and dimension are part of `indexing_version`; switching models requires a full rebuild because vectors from different models are not comparable.
- Qwen3-Embedding is instruction-aware: embed queries with a task instruction prefix and documents without one; keep this consistent between indexing and querying.
- Set `num_ctx` explicitly for the chat model (Ollama's default is small and silently truncates context) and size it for the retrieved chunks plus question plus answer.
- Disable Qwen3 "thinking" mode for answer generation (e.g. `think: false`) to reduce latency and avoid reasoning text leaking into answers.
- The 1.7B model is weak at faithfulness: use a strict prompt ("answer only from the context; say you don't know otherwise"), low temperature, and a small top-k (e.g. 3-5 chunks).
- Upgrade path if quality is insufficient: a larger chat model such as `qwen3:4b` or `qwen3:8b`, changed through configuration only.

## Responsibilities

- Consume `NoteCreated`, `NoteUpdated`, and `NoteDeleted` events from MS1.
- Fetch current notes from MS1 through REST.
- Split note titles and content into chunks.
- Generate embeddings through Ollama and store chunks in ChromaDB.
- Detect missing, changed, and deleted notes.
- Perform semantic vector search for user questions.
- Construct context and generate answers through Ollama.
- Return answers with references to source notes.
- Provide structured logging and API documentation.

## Contracts and Versioning

- Define and version the MS1 → MS2 event contract from the start.
- Event payload should include at minimum: `event_id`, `event_type`, `occurred_at`, and `note_id`. Events are change triggers only; MS2 always fetches the current note state from MS1.
- No version or timestamp freshness field is needed: because MS2 compares the fetched note's `source_hash` with the indexed one, duplicate and out-of-order events converge to the same result.
- Define explicit MS1 endpoints used by MS2 for note fetch and index metadata reconciliation.
- **Required MS1 changes (prerequisite for MS2 sync, tracked in `architecture-plan.md`):**
  - Add a persisted `source_hash` (from title and content), recomputed whenever title or content changes.
  - Add an index-metadata endpoint returning `note_id` and `source_hash` for all notes.
  - Add a note-fetch endpoint usable by MS2 (existing `GET` note endpoints may suffice).
  - Publish versioned events through RabbitMQ.
- Keep event schema versioned to allow backward-compatible evolution.

## Chunking and Indexing

- Chunk size: approximately 400 tokens (counted with the Qwen3-Embedding tokenizer).
- Overlap: approximately 50 tokens.
- Respect paragraph boundaries where practical.
- Avoid unnecessary chunking of short notes.
- Store chunk text, embedding, `note_id`, `chunk_index`, `source_hash`, and indexing configuration metadata in ChromaDB.
- Use stable chunk IDs, e.g. `note-{note_id}-chunk-{chunk_index}`.
- Calculate `source_hash` in MS1 from title and content; expose it through an index-metadata endpoint.
- Track an `indexing_version` derived from chunking/splitting/embedding settings (e.g., chunk size, overlap, splitter strategy, embedding model).
- Reindex a note when either `source_hash` or `indexing_version` changes.
- Remove obsolete chunks when notes are updated or deleted.

## API

- `POST /api/v1/admin/index/reconcile` — compare MS1 notes and ChromaDB; index missing or changed notes and remove deleted notes.
- `POST /api/v1/admin/index/rebuild` — rebuild the entire vector index.
- `POST /api/v1/chat/query` — retrieve relevant chunks, generate an answer, and return source references.
- `GET /api/v1/health` — health check.
- Admin endpoints are protected in V1 by a static API key sent in an `X-API-Key` header and read from an environment variable (never committed). Chat and health endpoints stay open.

These are proposed endpoint names, not yet implemented.

## RAG Pipeline

1. Receive a question.
2. Generate a query embedding through Ollama.
3. Retrieve the most relevant chunks from ChromaDB.
4. Construct a context from the retrieved chunks.
5. Send the question and context to the chat LLM through Ollama.
6. Return the answer with references to the original notes.

## Synchronization

- RabbitMQ events trigger normal incremental updates.
- Fetch the current note from MS1 when processing an event.
- Make event processing idempotent.
- Use retry with bounded attempts and a dead-letter queue for poison messages.
- Treat events as at-least-once and potentially out-of-order; this is safe because each event triggers a fetch of the current note and a `source_hash` comparison. A deleted note (404 from MS1) removes its chunks. Process events for the same note serially (e.g. a single consumer).
- Reconcile provides a recovery mechanism for missed events and stale index entries.
- Rebuild recreates the index from scratch.
- Keep MS1 as the source of truth; ChromaDB contains derived data.

## Implementation Phases

0. [x] MS1 prerequisites: `source_hash` and index-metadata endpoint (implemented as `GET /api/v1/notes/index-metadata`; event publishing follows in step 6).
1. [x] Set up Python project, FastAPI, and configuration.
2. [x] Integrate Ollama embeddings and ChromaDB.
3. [x] Implement chunking and indexing for a small set of notes.
4. [x] Implement admin reconcile/rebuild and note-fetch contracts for manual/scheduled sync.
5. [x] Implement semantic retrieval and RAG answers with source references.
6. [x] Integrate RabbitMQ events from MS1 for incremental updates.
   - Exchange `notes.events` (topic), routing keys `note.created|updated|deleted`; MS2 queue `ms2.note-events` with DLX `notes.events.dlx` and DLQ `ms2.note-events.dlq`.
   - MS2 disable switch: `MS2_RABBITMQ_ENABLED=false`. Local broker: `docker compose up -d rabbitmq`.
7. [x] Add error handling, structured logging, and tests.
   - Upstream (MS1/Ollama) failures return 502, unhandled errors 500 as JSON; `MS2_LOG_FORMAT=json` for structured logs.
   - `MS2_RETRIEVAL_MIN_SCORE` (default 0.45): chunks below it are dropped; with none left the LLM is skipped and the answer is "I don't know".
   - Tokenizer revision pinned to a commit hash (changing it triggers a reindex via `indexing_version`).
   - pytest suite in `ms2-rag-service/tests` (chunker, sync/reconcile/rebuild, threshold, API errors).
8. [x] Containerize MS2 and integrate it into Docker Compose.
   - Non-root image with healthcheck; `docker compose up -d --build ms2-rag-service`. Chroma data and the HF tokenizer cache live in named volumes.
   - Ollama is expected on the host (`host.docker.internal:11434`); admin key via `MS2_ADMIN_API_KEY` (default `dev-admin-key`, local only).
9. [ ] Connect the frontend chatbot to MS2.

## Deferred

- Hybrid search / BM25
- LangChain
- Separate SQL database for chunks or index status
- Reranking and advanced RAG techniques
- Transactional Outbox Pattern
- Kubernetes

## Design Principles

- Keep the first implementation simple.
- Separate indexing, retrieval, and answer generation.
- Use ChromaDB for chunk texts, embeddings, and metadata.
- Keep MS1 as the source of truth.
- Add complexity only when concrete requirements justify it.