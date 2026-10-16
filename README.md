# Personal Knowledge Hub

Monorepo with three independent project modules:

- `ms1-knowledge-service`: Java / Spring Boot knowledge API (current implementation)
- `ms2-rag-service`: Python / FastAPI RAG service (Chroma + Ollama, RabbitMQ-driven indexing)
- `ui`: React + TypeScript frontend for note management and the RAG chat

## Structure

```text
personal-knowledge-hub/
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
