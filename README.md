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
The first run builds the production MS1/MS2/UI images and downloads base images/dependencies.

The standalone test Compose stack uses real PostgreSQL, RabbitMQ and MS2's embedded
Chroma, and a local deterministic Ollama-compatible HTTP fake. It creates a note
through MS1, waits for event-driven chat retrieval with its source/hash, updates it
and checks the new content/hash replaces the old one, then deletes it and verifies
there are no stale chat sources. This direct-service lifecycle never calls
reconcile/rebuild. Consumer readiness,
event acknowledgements and an empty dead-letter queue are also checked.
The runner also verifies MS1's emitted JSON logs contain timestamp, severity, logger,
message and service name.
After the unchanged direct-service lifecycle, it checks the UI's static assets and
hash route, real note CRUD/chat/admin actions through nginx, and a separate echo
upstream for exact proxy paths, query strings, methods, bodies, error statuses and
admin-header isolation (including browser-supplied headers and path aliases).
It validates nginx configuration and rejects unsafe runtime substitutions. This same
CI job builds and smoke-tests the production UI container without model downloads.
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
Fast fake/polling/log-format checks: `python -m unittest discover -s tests\e2e -p test_harness.py`.
After a forcibly terminated local run, use the project name printed by Compose:
`docker compose -p <mnemo-e2e-ID> --env-file .\tests\e2e\e2e.env -f .\tests\e2e\compose.yaml down -v --remove-orphans --rmi local`.

## Run everything in Docker

Ollama must run on the host (reached via `host.docker.internal`), with the models
listed above already pulled. Docker Compose is the only other runtime prerequisite;
host Java, Node and Python are not needed.

From the repository root:

```powershell
docker compose up -d --build
```

Open **http://localhost:5173** once the services are ready. This builds and starts
PostgreSQL, RabbitMQ, MS1, MS2 and the UI. Stop host-run MS1/MS2 and the Vite dev
server first to free ports 8080/8000/5173. UI port 5173 is bound to loopback only.
The existing backend/infrastructure ports and persistent volumes are unchanged.

The UI image builds React/Vite assets with Node in a separate stage and serves them
with nginx; Node and development `.env` files are not in the runtime image.
The browser uses the same origin: `/api/...` goes unchanged to MS1 and
`/rag-api/...` goes to MS2 with `/rag-api` stripped. `#/chat` remains client-side.
No `VITE_*` build arguments or runtime browser configuration are needed.

Runtime container settings (override via a Compose override file, or `docker run -e`):

| Variable | Default in the UI image | Meaning |
| --- | --- | --- |
| `UI_MS1_UPSTREAM` | `http://ms1-knowledge-service:8080` | MS1 origin |
| `UI_MS2_UPSTREAM` | `http://ms2-rag-service:8000` | MS2 origin |
| `MS2_ADMIN_API_KEY` | empty | Server-side key for MS2 admin paths only |

Upstreams must be HTTP(S) hostname/IPv4 origins with an optional port, without
credentials, paths or trailing slashes. Keys accept letters, digits and
`. _ ~ + / = -`; other characters fail startup rather than being interpreted as
nginx syntax. Only these variables are substituted, preserving nginx variables.
Changing settings requires recreating the UI container, not rebuilding the assets.
An empty key sends no admin header. Compose supplies the same `MS2_ADMIN_API_KEY`
to UI and MS2 (local default `dev-admin-key`); override it in the root environment
or an untracked root `.env`, **never** a `VITE_*` variable.

**Local/trusted deployment only:** the key is held by nginx, not served as browser
configuration or bundled assets, and browser `X-API-Key` headers are discarded. nginx injects
its key only for `/rag-api/api/v1/admin/...` requests. However, this is **not user
authentication**: anyone who can reach the UI can invoke its admin proxy, including
rebuild/reconcile. The app still has unauthenticated note/chat APIs, local Compose
credentials and published backend ports. Do not expose this stack to the Internet
or untrusted users. A real public domain deployment needs access control, TLS,
restricted backend ports and production secret management separately.

## Application logs

Docker Compose enables Spring Boot's built-in ECS JSON console logging for MS1
(`LOGGING_STRUCTURED_FORMAT_CONSOLE=ecs`) and JSON logging for MS2 (`MS2_LOG_FORMAT=json`).
MS1 records include timestamp, severity, logger, message and `service.name`, taken
from `spring.application.name`. Existing SLF4J calls and log levels are unchanged;
the services do not use the same JSON schema and cross-service tracing is not added.
The MS1 startup banner is disabled in Compose so it does not mix with application logs.

Host-run MS1 keeps Spring Boot's default readable text output. To opt into JSON in
PowerShell, set `$env:LOGGING_STRUCTURED_FORMAT_CONSOLE = "ecs"` before starting MS1;
`Remove-Item Env:LOGGING_STRUCTURED_FORMAT_CONSOLE` restores the default for future starts.
Host-run MS2 similarly defaults to text unless `MS2_LOG_FORMAT=json` is set.
No additional dependencies or log-collection service are required.

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
