# Mnemo

**Your personal knowledge hub.**

Self-hosted personal notes with a local RAG chatbot.

Monorepo with three independent project modules:

- `ms1-knowledge-service`: Java / Spring Boot knowledge API (current implementation)
- `ms2-rag-service`: Python / FastAPI RAG service (Chroma + Ollama, RabbitMQ-driven indexing)
- `ui`: React + TypeScript frontend for note management and the RAG chat

## Structure

```text
mnemo/
├── ms1-knowledge-service/
├── ms2-rag-service/
├── ui/
├── compose.yaml
└── README.md
```

## Quick start (full backend)

Prerequisites: Docker, Java 25, Python 3.12+, [Ollama](https://ollama.com).

1. Pull the models (once):
   - `ollama pull qwen3-embedding:0.6b`
   - `ollama pull qwen3:4b`
2. Start infrastructure (PostgreSQL + RabbitMQ; management UI at `http://localhost:15672`):
   - `docker compose up -d db rabbitmq`
3. Run MS1 (`http://localhost:8080`):
   - `cd ms1-knowledge-service`
   - `.\mvnw.cmd spring-boot:run` (Windows) / `./mvnw spring-boot:run`
4. Run MS2 (`http://localhost:8000`, API docs at `/docs`):
   - `cd ms2-rag-service`
   - `python -m venv .venv`
   - `.\.venv\Scripts\python.exe -m pip install ".[dev]"`
   - `$env:MS2_ADMIN_API_KEY = "dev-admin-key"`
   - `.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000`
5. Build the initial index (afterwards RabbitMQ events keep it current):
   - `POST http://localhost:8000/api/v1/admin/index/reconcile` with header `X-API-Key: dev-admin-key`
6. Ask a question: `POST http://localhost:8000/api/v1/chat/query` with `{"question": "..."}`.

Example requests: `ms2-rag-service/requests.http`.

MS2 options (env vars, prefix `MS2_`): `RABBITMQ_ENABLED=false` runs without the broker, `LOG_FORMAT=json` enables JSON logs, `RETRIEVAL_MIN_SCORE` sets the relevance cut-off.

## Tests

- MS1: `cd ms1-knowledge-service; .\mvnw.cmd test`
- MS2: `cd ms2-rag-service; .\.venv\Scripts\python.exe -m pytest`

### Cross-service integration (phase 8)

From the repository root, with Python 3.12+ and Docker Compose v2 available:

```powershell
python .\tests\e2e\run.py
```

On Linux/macOS: `python tests/e2e/run.py`. No host Java, service Python dependencies,
Ollama installation, model downloads, or running development services are needed.
The first run builds the production MS1/MS2 images and downloads base images/dependencies.

The standalone test Compose stack uses real PostgreSQL, RabbitMQ and MS2's embedded
Chroma, and a local deterministic Ollama-compatible HTTP fake. It creates a note
through MS1, waits for event-driven chat retrieval with its source/hash, updates it
and checks the new content/hash replaces the old one, then deletes it and verifies
there are no stale chat sources. It never calls reconcile/rebuild. Consumer readiness,
event acknowledgements and an empty dead-letter queue are also checked.
Polling is deadline-bounded and reports the last failed observation.

Each run has a unique Compose project, private network and disposable data volumes,
no published host ports, no development `.env` files, and no development data mounts.
The tokenizer uses MS2's existing offline word-count fallback. The fake returns fixed
embeddings and echoes only retrieved context: this tests integration, not model quality,
semantic ranking or the real tokenizer. No production code is substituted.

The runner always attempts teardown (including volumes) and writes service logs,
scenario output, container status and queue diagnostics to ignored `tests\e2e\artifacts`.
Project-built images are removed; shared base images/build cache are retained. CI runs it
as an independent job and uploads those diagnostics, with a final cleanup step.
Fast fake/polling checks: `python -m unittest discover -s tests\e2e -p test_harness.py`.
After a forcibly terminated local run, use the project name printed by Compose:
`docker compose -p <mnemo-e2e-ID> --env-file .\tests\e2e\e2e.env -f .\tests\e2e\compose.yaml down -v --remove-orphans --rmi local`.

## Run everything in Docker

Ollama must run on the host (reached via `host.docker.internal`).

`docker compose up -d --build` builds and starts PostgreSQL, RabbitMQ, MS1 and MS2 (admin key `MS2_ADMIN_API_KEY`, default `dev-admin-key`). Stop host-run MS1/MS2 first to free ports 8080/8000.

## UI quick start

1. Install UI dependencies:
   - `cd ui`
   - `npm install`
2. Run the UI dev server:
   - `npm run dev`
3. Open:
   - `http://localhost:5173`

The UI defaults to `/api` and uses Vite proxy to reach MS1 at `http://localhost:8080`. Chat requests go to `/rag-api`, which the proxy forwards to MS2 at `http://localhost:8000` and adds the admin key (`MS2_ADMIN_API_KEY`, default `dev-admin-key`) for the Index actions.

Chat tab: the empty state offers three example questions (the two most recently updated notes plus one random note, re-rolled on "Clear chat"). The conversation is kept in `sessionStorage` and survives a page reload. Tests: `npm test`.

Optional direct browser-to-MS1 mode (uses CORS):

1. In `ui`, create `.env` from `.env.example`.
2. Set `VITE_API_BASE_URL=http://localhost:8080/api`.
3. Restart `npm run dev`.
