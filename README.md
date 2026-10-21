# Mnemo

**Your personal knowledge hub.**

Self-hosted notes with a RAG chatbot. Local development uses Ollama; the public
demo uses Groq for text generation and host Ollama for embeddings.

**Live demo:** https://mnemo-hub.duckdns.org — anonymous, shared, disposable data.
Do not enter personal or confidential information.

Public deployment is complete for the demo scope, with HTTPS, private backend
ports, request limits and automatic deployment after CI passes on `main`.
See [deployment instructions](deploy/README.md) and the
[verification record](deploy/plan.md) for operating commands and limitations.

Monorepo with three independent project modules:

- `knowledge-service`: Java / Spring Boot knowledge API (current implementation)
- `rag-service`: Python / FastAPI RAG service (Chroma, Ollama embeddings, Ollama/Groq chat, RabbitMQ-driven indexing)
- `ui`: React + TypeScript frontend for note management and the RAG chat

## Structure

```text
mnemo/
├── knowledge-service/   # Note API, PostgreSQL migrations, Java tests
├── rag-service/         # Indexing, retrieval, grounded chat, Python tests
├── ui/                  # React frontend and colocated tests
├── deploy/              # Public hosting configuration and operations scripts
├── tests/               # Deployment checks and isolated cross-service tests
├── evaluation/          # Evaluation harness, corpus, and recorded results
├── pom.xml              # Maven aggregator for the Java service
├── compose.yaml         # Local development stack
└── README.md
```

## Documentation

- [Architecture and implementation status](architecture-plan.md): overall design, completed milestones, and remaining work.
- [RAG service design](architecture-plan-rag-service.md): indexing, retrieval, messaging, and API details.
- [Deployment guide](deploy/README.md): hosting, configuration, upgrades, and operations.
- [Deployment preparation and verification record](deploy/plan.md): rollout checklist and historical verification.
- [Evaluation plan](evaluation-plan.md) and [recorded results](evaluation/results.md): procedure, scores, and limitations.

The architecture documents combine implemented design with future plans; use their
completion markers and the code to distinguish current behavior from proposed work.

## Quick start (full backend)

Prerequisites: Docker, Java 25, Python 3.12+, [Ollama](https://ollama.com).

1. Pull the models (once):
   - `ollama pull qwen3-embedding:0.6b`
   - `ollama pull qwen3:4b`
2. Start infrastructure (PostgreSQL + RabbitMQ; management UI at `http://localhost:15672`):
   - `docker compose up -d db rabbitmq`
3. Run Knowledge service (`http://localhost:8080`):
   - `cd knowledge-service`
   - `.\mvnw.cmd spring-boot:run` (Windows) / `./mvnw spring-boot:run`
4. Run RAG service (`http://localhost:8000`, API docs at `/docs`):
   - `cd rag-service`
   - `python -m venv .venv`
   - `.\.venv\Scripts\python.exe -m pip install ".[dev]"`
   - `.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000`
5. Build the initial index (afterwards RabbitMQ events keep it current):
   - `POST http://localhost:8000/api/v1/index/reconcile`
6. Ask a question: `POST http://localhost:8000/api/v1/chat/query` with `{"question": "..."}`.

Example requests: `rag-service/requests.http`.

Notes contain a title, content and an optional AI summary; there are no tags.
The shared collection is limited to 100 notes, including starter notes; delete
a note to make room when the limit is reached.
Use **Summarize note** on a saved note to generate a summary with one model call
(`POST /api/v1/notes/{id}/summarize`). Saving never invokes AI. Updating a note
clears its summary; a failed summarization preserves the previous summary.
Knowledge service's provider-neutral `app.summary.enabled` setting defaults to `true`.
Set `APP_SUMMARY_ENABLED=false` to disable summarization with either Ollama or
Groq; this replaces the old `ai.ollama.enabled` / `AI_OLLAMA_ENABLED` setting.

RAG service options (env vars, prefix `RAG_`): `RABBITMQ_ENABLED=false` runs without the broker, `LOG_FORMAT=json` enables JSON logs, `RETRIEVAL_MIN_SCORE` sets the relevance cut-off.

The root Compose stack seeds the ten starter notes on an empty database. You can
also trigger an authenticated reset that replaces notes with starter data
and durably queues an index-rebuild event for RAG service:

```powershell
$resetKey = $env:MNEMO_RESET_API_KEY
if (-not $resetKey) { $resetKey = "local-dev-reset-key-only-do-not-use-in-production" }
Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/v1/admin/reset-database `
  -Headers @{ "X-Mnemo-Reset-Key" = $resetKey }
```

The endpoint returns `202 Accepted` when reset and its outbox event have committed.
Rebuilding is asynchronous: broker outages and Knowledge service restarts retain pending events
for automatic delivery when RabbitMQ and the RAG service queue recover.

Note create/update/delete use the same transactional outbox in PostgreSQL.
The dispatcher sends persistent messages and removes pending rows only after a
positive broker confirmation without an unroutable-message return. Failed sends
retry indefinitely with delays capped at five minutes. Delivery is at-least-once;
RAG service fetches current note state, so duplicate/out-of-order events converge.
This does not guarantee successful indexing: consumer failures can reach RAG service's
dead-letter queue. Manual reconcile/rebuild remain available for those failures
or lost index data. The VPS also runs reconciliation nightly at 04:00
Europe/Berlin as a safety net. See [outbox operations](deploy/README.md#outbox-and-index-recovery)
and [nightly reconciliation](deploy/README.md#nightly-index-reconciliation).

## Tests

- Knowledge service: `cd knowledge-service; .\mvnw.cmd test`
- RAG service: `cd rag-service; .\.venv\Scripts\python.exe -m pytest`

From the repository root:

- Deployment configuration, seeding and service-name migration: `python -m pytest tests/test_deploy_seed.py tests/test_deploy_network.py tests/test_service_name_migration.py -q`
  (requires pytest and Docker Compose; does not start containers).
- Evaluation harness: `python -m unittest discover -s evaluation -p test_run.py`
  (standard library only; no model calls).

Both run in the existing E2E CI job before the isolated stack starts.

### Real-model RAG sanity check

The separate [evaluation results](evaluation/results.md) contain a fixed synthetic
10-note corpus, ten questions with an answer key, the first real-model responses
and provisional assistant-reviewed scores. This is not a deterministic CI test.
See that page for the small standard-library runner, isolation and reproduction
instructions; it never loads or clears the development notes/index.

## Knowledge service database migrations

Knowledge service applies versioned PostgreSQL migrations from
`knowledge-service/src/main/resources/db/migration` at startup. New databases
apply V1 followed by `V2__remove_note_tags.sql`; V2 removes the old tag tables
while preserving notes and summaries. Existing V1 databases apply V2 at startup.
Tag data is intentionally discarded; the old `/ai-enrich` endpoint is replaced
by `/summarize` with no compatibility alias. Deploy Knowledge service and UI together.
Hibernate uses `ddl-auto=validate` and
does not create or update tables. Keep future schema changes in new versioned
migrations; do not edit a migration after it has been applied.

Existing databases created by older Knowledge service versions have no Flyway history. Do not
enable baseline-on-migrate for normal operation: it is off by default. To adopt a
known legacy database, stop Knowledge service and all other writers, take and verify a database
backup, and run the read-only compatibility check against the intended database
and schema:

```powershell
$backup = Join-Path $env:USERPROFILE 'mnemo-before-flyway.dump'
pg_dump --format=custom --host=localhost --port=5332 --username=bluesbird `
  --dbname=mnemo --file="$backup"
if ($LASTEXITCODE -ne 0) { throw 'Database backup failed' }
pg_restore --list "$backup"
if ($LASTEXITCODE -ne 0) { throw 'Database backup verification failed' }

psql -h localhost -p 5332 -U bluesbird -d mnemo -v ON_ERROR_STOP=1 `
  -f .\knowledge-service\docs\legacy-schema-preflight.sql
```

The dump is outside the repository and `pg_restore --list` verifies it can be read.
The preflight rejects a different table set, column shape, source-hash default, or
primary/unique/foreign-key definitions. Review the result and confirm the database
is the expected Knowledge service legacy schema before proceeding. If it fails, do not baseline;
investigate the schema/data drift and resolve it from the verified backup first.

For the one-time adoption, start Knowledge service once with
`SPRING_FLYWAY_BASELINE_ON_MIGRATE=true` (for a host-run PowerShell start, set
`$env:SPRING_FLYWAY_BASELINE_ON_MIGRATE = "true"` before
`.\mvnw.cmd spring-boot:run`). The configured baseline is version `1`: Flyway
records that the existing schema already represents V1 and does not execute V1
against the populated tables. Hibernate then validates the schema during startup.
If startup validation fails, stop and restore/investigate; do not switch back to
schema auto-update. After a successful start, stop Knowledge service, remove the environment
variable (`Remove-Item Env:SPRING_FLYWAY_BASELINE_ON_MIGRATE`), and start it
normally. Normal startups keep baseline-on-migrate disabled and apply only newer
migrations.

### Cross-service integration (phase 8)

From the repository root, with Python 3.12+ and Docker Compose v2 available:

```powershell
python .\tests\e2e\run.py
```

On Linux/macOS: `python tests/e2e/run.py`. No host Java, service Python dependencies,
Ollama installation, model downloads, or running development services are needed.
The first run builds the production Knowledge service/RAG service/UI images and downloads base images/dependencies.

The standalone test Compose stack uses real PostgreSQL, RabbitMQ and RAG service's embedded
Chroma, and a local deterministic Ollama-compatible HTTP fake. It creates a note
through Knowledge service, waits for event-driven chat retrieval with its source/hash, updates it
and checks the new content/hash replaces the old one, then deletes it and verifies
there are no stale chat sources. This direct-service lifecycle never calls
reconcile/rebuild. Consumer readiness,
event acknowledgements and an empty dead-letter queue are also checked.
It then stops RabbitMQ, commits creates/updates/deletes and a separate reset,
restarts Knowledge service with pending work, and restores the broker. Read-only index checks
verify automatic convergence to Knowledge service and drained outbox/queues without calling
reconcile/rebuild during recovery.
The runner also verifies Knowledge service's emitted JSON logs contain timestamp, severity, logger,
message and service name.
After the unchanged direct-service lifecycle, it checks the UI's static assets and
hash route, real note CRUD/chat/index actions through nginx, and a separate echo
upstream for exact proxy paths, query strings, methods, bodies, error statuses and
API-key header isolation (including browser-supplied headers and path aliases).
It validates nginx configuration and rejects unsafe runtime substitutions. This same
CI job builds and smoke-tests the production UI container without model downloads.
Polling is deadline-bounded and reports the last failed observation.

Each run has a unique Compose project, private network and disposable data volumes,
no published host ports, no development `.env` files, and no development data mounts.
The tokenizer uses RAG service's existing offline word-count fallback. The fake returns fixed
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

Local containers use Compose project-scoped names. Use `docker compose exec db`
and `docker compose exec rabbitmq` rather than hard-coded container names.
Existing data volumes are unchanged. Running multiple stacks on one host still
requires distinct published ports.

Ollama must run on the host (reached via `host.docker.internal`), with the models
listed above already pulled. Docker Compose is the only other runtime prerequisite;
host Java, Node and Python are not needed.

From the repository root:

```powershell
python deploy/migrate-service-names.py --compose compose.yaml --env-file .env
docker compose up -d --build --remove-orphans
```

The migration requires host Python only when upgrading an existing numbered
service deployment; fresh installations can skip it. It preserves existing
index volumes and RabbitMQ queues through local `.env` overrides. See
[service-name migration](deploy/README.md#service-name-migration) for details.

Open **http://localhost:5173** once the services are ready. This builds and starts
PostgreSQL, RabbitMQ, Knowledge service, RAG service and the UI. Stop host-run Knowledge service/RAG service and the Vite dev
server first to free ports 8080/8000/5173. UI port 5173 is bound to loopback only.
The existing backend/infrastructure ports and persistent volumes are unchanged.

The UI image builds React/Vite assets with Node in a separate stage and serves them
with nginx; Node and development `.env` files are not in the runtime image.
The browser uses the same origin: `/api/...` goes unchanged to Knowledge service and
`/rag-api/...` goes to RAG service with `/rag-api` stripped. `#/chat` remains client-side.
No `VITE_*` build arguments or runtime browser configuration are needed.

Runtime container settings (override via a Compose override file, or `docker run -e`):

| Variable | Default in the UI image | Meaning |
| --- | --- | --- |
| `UI_KNOWLEDGE_UPSTREAM` | `http://knowledge-service:8080` | Knowledge service origin |
| `UI_RAG_UPSTREAM` | `http://rag-service:8000` | RAG service origin |

Upstreams must be HTTP(S) hostname/IPv4 origins with an optional port, without
credentials, paths or trailing slashes. Only these variables are substituted,
preserving nginx variables.
Changing settings requires recreating the UI container, not rebuilding the assets.

The UI proxy discards browser-supplied `X-API-Key` headers. Index reconcile/rebuild
are public operations. The root Compose stack is for local development: it uses
local credentials and publishes backend/infrastructure ports. For public hosting,
use the separate [deployment stack](deploy/README.md), not the root Compose file.
The public demo intentionally keeps note/chat/index APIs anonymous; only database
reset requires a server-side secret.

## Application logs

Docker Compose enables Spring Boot's built-in ECS JSON console logging for Knowledge service
(`LOGGING_STRUCTURED_FORMAT_CONSOLE=ecs`) and JSON logging for RAG service (`RAG_LOG_FORMAT=json`).
Knowledge service records include timestamp, severity, logger, message and `service.name`, taken
from `spring.application.name`. Existing SLF4J calls and log levels are unchanged;
the services do not use the same JSON schema and cross-service tracing is not added.
The Knowledge service startup banner is disabled in Compose so it does not mix with application logs.

Host-run Knowledge service keeps Spring Boot's default readable text output. To opt into JSON in
PowerShell, set `$env:LOGGING_STRUCTURED_FORMAT_CONSOLE = "ecs"` before starting Knowledge service;
`Remove-Item Env:LOGGING_STRUCTURED_FORMAT_CONSOLE` restores the default for future starts.
Host-run RAG service similarly defaults to text unless `RAG_LOG_FORMAT=json` is set.
No additional dependencies or log-collection service are required.

## UI quick start

1. Install UI dependencies:
   - `cd ui`
   - `npm install`
2. Run the UI dev server:
   - `npm run dev`
3. Open:
   - `http://localhost:5173`

The UI defaults to `/api` and uses Vite proxy to reach Knowledge service at `http://localhost:8080`. Chat requests go to `/rag-api`, which the proxy forwards to RAG service at `http://localhost:8000`. Index reconcile/rebuild are available at `/api/v1/index/reconcile` and `/api/v1/index/rebuild` without an API key.

Chat tab: the empty state offers three example questions (the two most recently updated notes plus one random note, re-rolled on "Clear chat"). The conversation is kept in `sessionStorage` and survives a page reload. Tests: `npm test`.

Optional direct browser-to-Knowledge service mode (uses CORS):

1. In `ui`, create `.env` from `.env.example`.
2. Set `VITE_API_BASE_URL=http://localhost:8080/api`.
3. Restart `npm run dev`.
