# Mnemo

**A self-hosted knowledge hub for notes, on-demand AI summaries, and RAG-based grounded answers.**

Mnemo is a polyglot microservice app: the Knowledge service manages source
data, the RAG service builds a derived vector index, and the UI provides note
management and source-backed chat.

**Open the live demo**: https://mnemo-hub.duckdns.org

## System architecture

![Mnemo production deployment architecture](docs/assets/mnemo_architecture_diagram.png)

Mnemo is deployed on a self-hosted VPS with a same-origin web gateway. Caddy
handles HTTPS termination, while Nginx serves the UI and proxies API requests
to the Knowledge and RAG services over the private network.

The Knowledge Service is the source of truth for notes and summaries in PostgreSQL.
The RAG Service handles retrieval and answer generation: it builds a derived ChromaDB
index from note title/content chunks, retrieves relevant context, and returns
answers with source-note references.

Data flows both synchronously and asynchronously. User actions (CRUD, summarization,
chat, and manual reconciliation or rebuild) use HTTP through the UI proxy. 
The Knowledge Service also publishes note-change and index-rebuild events to 
RabbitMQ, allowing the RAG Service to keep the index synchronized incrementally 
or rebuild it when requested.

In this deployment, Ollama generates embeddings, while Groq handles text generation 
for summaries and RAG answers.

## What this project demonstrates

- **Full-stack, polyglot development:** React/TypeScript, Java/Spring Boot, and
  Python/FastAPI working as separate services.
- **Reliable asynchronous integration:** database-backed transactional outbox,
  at-least-once RabbitMQ delivery, idempotent consumers, dead-letter handling,
  and reconciliation for recovery.
- **Grounded RAG:** versioned note indexing, semantic retrieval, and answers
  linked to their source notes.
- **Production-minded delivery:** containerized services, automated CI/CD, and
  a live HTTPS deployment with private backend services and bounded requests.

## Key design decisions

- **One source of truth:** PostgreSQL owns notes and summaries; ChromaDB is
  derived, rebuildable index data. RAG detects stale content using note hashes
  and indexing-configuration versions.
- **Events trigger current-state reads:** RabbitMQ messages identify changed
  notes; RAG fetches their latest state from Knowledge service. Duplicate and
  out-of-order events therefore converge safely.
- **Durability without a separate platform:** note changes and outbox events
  commit together. Failed delivery retries, while reconciliation provides a
  recovery path for index drift.
- **Separate embeddings and generation:** embeddings stay on Ollama while
  answer-generation providers can change without reindexing.

## Technology stack

| Area | Technologies |
| --- | --- |
| Frontend | React, TypeScript, Vite |
| Knowledge API | Java 25, Spring Boot 4, Spring Data JPA, Flyway |
| RAG API | Python 3.12+, FastAPI, ChromaDB, tokenizers |
| Data and messaging | PostgreSQL, RabbitMQ |
| AI | Ollama embeddings and local models; Groq generation in the public demo |
| Delivery | Docker Compose, Nginx, Caddy, GitHub Actions |

## See it in action

<p align="center">
  <img src="docs/assets/notes_wide.png" width="100%" alt="Mnemo notes view with a selected note and its AI summary">
</p>
<p align="center">
  <img src="docs/assets/chat_2_wide.png" width="100%" alt="Mnemo chat showing grounded answers and linked source notes">
</p>

## Production scope

- Public demo APIs are intentionally anonymous and shared.
- Database reset is the only authenticated operation.
- Notes + summaries are primary data; the vector index is derived and rebuildable.
- The demo is optimized for clarity and reliability, not multi-user tenancy.

## Service documentation

- [Knowledge service](knowledge-service/README.md)
- [RAG service](rag-service/README.md)
- [UI](ui/README.md)
- [Deployment and operations](deploy/README.md)

## Run locally

Prerequisites: Docker Compose and [Ollama](https://ollama.com). Pull the local
models, then start the full application from the repository root:

```sh
ollama pull qwen3-embedding:0.6b
ollama pull qwen3:4b
docker compose up -d --build
```

Open **http://localhost:5173**. Compose starts the UI, both APIs, PostgreSQL,
RabbitMQ, and starter data; Ollama runs on the host. See the
[deployment guide](deploy/README.md) for public hosting and operations.

## Testing

The CI workflow builds and tests the services and runs isolated cross-service
integration checks without downloading real AI models. Run the end-to-end
integration scenario locally with Docker Compose and Python 3.12+:

```sh
python tests/e2e/run.py
```

See the [evaluation snapshot](evaluation/README.md) and
[RAG sanity-check results](evaluation/results.md) for reproducibility details
and limitations.
