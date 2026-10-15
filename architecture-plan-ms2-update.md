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

## Chunking and Indexing

- Chunk size: approximately 400 tokens.
- Overlap: approximately 50 tokens.
- Respect paragraph boundaries where practical.
- Avoid unnecessary chunking of short notes.
- Store chunk text, embedding, `note_id`, `chunk_index`, `source_hash`, and indexing configuration metadata in ChromaDB.
- Use stable chunk IDs, e.g. `note-{note_id}-chunk-{chunk_index}`.
- Calculate `source_hash` in MS1 from title and content; expose it through an index-metadata endpoint.
- Reindex a note when its hash or indexing configuration changes.
- Remove obsolete chunks when notes are updated or deleted.

## API

- `POST /api/v1/index/reconcile` — compare MS1 notes and ChromaDB; index missing or changed notes and remove deleted notes.
- `POST /api/v1/index/rebuild` — rebuild the entire vector index.
- `POST /api/v1/chat/query` — retrieve relevant chunks, generate an answer, and return source references.
- `GET /api/v1/health` — health check.

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
- Reconcile provides a recovery mechanism for missed events and stale index entries.
- Rebuild recreates the index from scratch.
- Keep MS1 as the source of truth; ChromaDB contains derived data.

## Implementation Phases

1. [ ] Set up Python project, FastAPI, and configuration.
2. [ ] Integrate Ollama embeddings and ChromaDB.
3. [ ] Implement chunking and indexing for a small set of notes.
4. [ ] Implement semantic retrieval and RAG answers with source references.
5. [ ] Implement index reconciliation and full rebuild.
6. [ ] Integrate RabbitMQ events from MS1.
7. [ ] Add error handling, structured logging, and tests.
8. [ ] Containerize MS2 and integrate it into Docker Compose.
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