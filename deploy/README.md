# Deployment Compose

This Compose project is separate from the local-development stack in the
repository root. It keeps PostgreSQL, RabbitMQ and both application services
off host-published ports. Caddy listens on ports 80 and 443, obtains and renews
certificates for `mnemo-hub.duckdns.org`, and forwards HTTPS traffic to the UI's
nginx server. Nginx serves the frontend and proxies API requests to Knowledge service and RAG service.
The UI is also available on `127.0.0.1:8081` for local diagnostics.

Before starting the stack, point the domain's DNS A record to the VPS public IPv4
address and allow inbound TCP ports 80/443 through the host firewall and any
provider firewall. Caddy cannot issue certificates until the domain resolves
to that server and those ports are reachable.

## Resource limits

The shared collection allows at most 100 notes, including starter notes.
Creation at the limit returns HTTP 409; editing and deleting remain available.

Deployment Nginx limits each client IP to 30 chat requests/minute (burst 20)
and 10 summarization requests/minute (burst 5). It allows at most two concurrent
model-backed HTTP operations across all clients. Reconcile and rebuild are each
limited globally to one request/minute. Requests larger than 256 KiB are rejected;
Note titles are limited to 70 characters, note bodies to 5,000 and chat questions
to 500 in both local and deployed apps. Chat answers are limited to 256 tokens.
Knowledge service summarization allows 2,048 generated tokens in one call per button press.
Groq reasoning is disabled for both services. Empty or incomplete summaries
return an HTTP 502 error and leave the note's existing summary unchanged.
These deployment-only limits are disabled in the root local-development Compose
stack. Caddy replaces the forwarded client-IP header, and Nginx trusts it only
from Caddy's fixed address (`172.30.0.2`) on the private proxy network. Dynamic
addresses, including the UI's, are allocated from `172.30.0.128/25` so they cannot
claim Caddy's address. Existing deployments must recreate the proxy network
with `docker compose --env-file deploy/.env -f deploy/compose.yaml down` before
starting again; omit `--volumes` to preserve data.

## AI providers

Local development keeps Ollama for summarization, chat and embeddings; no Groq
key is needed. Deployment uses GroqCloud (`qwen/qwen3.8-27b`) for Knowledge service summarization
and RAG service answer generation. Knowledge service activates the `groq` Spring profile; RAG service sets
`RAG_CHAT_PROVIDER=groq`. Both read the same `GROQ_API_KEY` from `deploy/.env`
(mapped to `RAG_GROQ_API_KEY` for RAG service). Keys never belong in browser assets,
committed configuration or logs.

Groq receives the title/content of notes being summarized, and questions plus
retrieved note excerpts for RAG answers. Only use synthetic/non-sensitive data
in this public deployment. Requests are subject to your organization's shared
Groq quota: each summarization uses one request, each grounded RAG answer one.
Failures are reported explicitly, with no automatic fallback to local inference
or application-level retries. Check the account's Limits page for current quotas.

Embeddings remain on host Ollama (`qwen3-embedding:0.6b`) in both environments.
This preserves Chroma's embedding dimensions and indexing version; switching
generation providers needs no rebuild or data migration.

Ollama runs on the VPS host and is not managed by this Compose project. An
administrator must install Ollama using its official Linux installation
instructions before starting the application. RAG service connects through Docker's host
gateway, so a loopback-only Ollama listener is not sufficient.
Find the host's private Docker bridge address:

```sh
docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}'
```

On the current VPS this is `172.17.0.1`. Use `sudo systemctl edit ollama` to
configure the listener and bounded parallelism/queueing (replace the address
if the command above returns a different one):

```ini
[Service]
Environment="OLLAMA_HOST=172.17.0.1:11434"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_MAX_QUEUE=16"
```

Do not bind to a public address or publish/forward port 11434. Host firewall
rules must permit the application containers to reach this private listener
while keeping the port inaccessible from the internet. After saving the
override, restart Ollama and download the required embedding model:

```sh
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl restart ollama
export OLLAMA_HOST=http://172.17.0.1:11434
ollama pull qwen3-embedding:0.6b
curl --fail "$OLLAMA_HOST/api/tags"
```

The VPS no longer needs the Ollama chat model for application requests.

Create a private deployment environment file and set both passwords plus the
reset key to strong, unique values, and add your Groq API key as `GROQ_API_KEY`.
Preserve existing values when updating a deployment. Compose refuses to run
while any required value is empty:

```sh
cp deploy/.env.example deploy/.env
${EDITOR:-vi} deploy/.env
```

The reset key stays server-side only. Never inject it through Nginx/Caddy or
the browser. To run the reset from a trusted shell on the host:

```sh
MNEMO_RESET_API_KEY="$(sed -n 's/^MNEMO_RESET_API_KEY=//p' deploy/.env)"
curl --fail-with-body -X POST http://127.0.0.1:8081/api/v1/admin/reset-database \
  -H "X-Mnemo-Reset-Key: $MNEMO_RESET_API_KEY"
```

The endpoint returns `202 Accepted` after committing the replacement notes and
an outbox event requesting a RAG service full rebuild. Broker outages do not block reset;
the event remains in PostgreSQL for automatic delivery. Rebuilding is asynchronous.

Start or update the deployment from the repository root:

```sh
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d --build --remove-orphans
```

The manual summary action is `POST /api/v1/notes/{id}/summarize`; saving notes
does not invoke AI and updating clears the previous summary. The old
`/ai-enrich` route is removed. Deploy Knowledge service and UI together. Flyway V2 drops the
old tag tables at Knowledge service startup without changing notes, summaries or the derived
index. Tag data cannot be recovered without a pre-update database backup.
Flyway V3 adds the transactional event outbox; existing migrations stay unchanged.

## Automatic deployment

### Service-name migration

The application directories and Compose services are now `knowledge-service`
and `rag-service`, without numbered prefixes.
Keep the existing Compose project name and `deploy/.env`. The update commands
use `--remove-orphans` so the old application containers do not keep consuming
events after the renamed containers start. Do not run `down --volumes`.

Settings now use `RAG_*`, `KNOWLEDGE_BASE_URL`, `UI_KNOWLEDGE_UPSTREAM`,
`UI_RAG_UPSTREAM`, and `VITE_RAG_API_BASE_URL`. Update custom environment
overrides to these names. Index operation responses use `total_knowledge_notes`.
The internal notes client is `KnowledgeClient`.

Before the first manual update of an existing host, run from the repository root:

```sh
python3 deploy/migrate-service-names.py
```

CD runs this automatically before updating containers. It finds the old RAG
container in the same Compose project and records its actual volume and queue
identities in private `deploy/.env` overrides (`RAG_DATA_VOLUME`,
`RAG_CACHE_VOLUME`, `RAG_EVENTS_QUEUE`, `RAG_EVENTS_DEAD_LETTER_QUEUE`). This
retains existing index data, cache, pending messages and dead letters without
copying or deleting them. Keep these overrides on subsequent deployments.
Legacy physical Docker/RabbitMQ names may remain; fresh installations use the
new names. The migration refuses conflicting overrides or unexpected mounts.
Do not remove old containers before running it.

Historical evaluation responses retain the service identities of their recorded run.

The repository rename does not migrate a running host until it is deployed.

### CI/CD

The GitHub Actions `CI` workflow deploys pushes to `main` only after all four
test jobs pass. Pull requests never deploy. Repository secrets required:
`VPS_HOST` (hostname/IP only), `VPS_USER`, `VPS_SSH_KEY` (a dedicated,
non-interactive SSH private key), and `VPS_KNOWN_HOSTS` (the verified OpenSSH
known-hosts entry for that host). Host verification is mandatory; do not use
an unverified key scanned during the workflow.

The SSH user must have write access to `/opt/mnemo/Mnemo` and Docker access.
The server's existing `deploy/.env` supplies application credentials, including
the Groq key; Actions neither prints nor replaces it. Deployments are serialized
and skip commits superseded on `main`. A dirty checkout or non-fast-forward
update fails rather than discarding server changes.

Images build before containers are updated. Normal updates preserve volumes,
but container recreation can briefly interrupt requests. The job checks the UI,
notes API and RAG service health locally and over public HTTPS without invoking AI.
There is no automatic rollback: a failed deployment/check is visible in Actions;
inspect container status/logs on the VPS before retrying. CI failures leave the
running deployment untouched. View deployment output in the workflow's
`Deploy to VPS` job.

The Compose project creates named volumes for PostgreSQL, RabbitMQ, ChromaDB,
the RAG service tokenizer cache, and Caddy's TLS certificates and state. Normal
stop/start and image updates preserve them. Do not use `down --volumes` unless
deleting all stored application/index data and TLS state is intended. Keep
`deploy/.env` private and out of version control.

On first startup, the `starter-data` job reads the same canonical note catalog
used by reset and creates the ten fictional notes only if Knowledge service's note list is
empty. Existing notes are left untouched. The UI waits for this one-shot job to
complete before accepting public requests;
inspect its result with:

```sh
docker compose --env-file deploy/.env -f deploy/compose.yaml logs starter-data
```

Inspect service status and logs with:

```sh
docker compose --env-file deploy/.env -f deploy/compose.yaml ps
docker compose --env-file deploy/.env -f deploy/compose.yaml logs --tail 100
```

## Outbox and index recovery

Note create/update/delete and reset atomically commit pending events in PostgreSQL.
The dispatcher polls every second, holds one pending row lock while sending, and
deletes only after a positive RabbitMQ confirmation with no mandatory return.
Persistent messages and unique per-attempt correlations preserve at-least-once
delivery; duplicates can occur after broker acceptance and before database commit.
RAG service handles them by fetching the current note state. Failed sends retry indefinitely,
with exponential delays from two seconds up to five minutes. No extra service is needed.

Inspect pending work without changing it:

```sh
docker compose --env-file deploy/.env -f deploy/compose.yaml exec -T db \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT count(*) AS pending, min(occurred_at) AS oldest_event, max(attempts) AS max_attempts FROM note_outbox;"'
docker compose --env-file deploy/.env -f deploy/compose.yaml logs --tail 100 knowledge-service rag-service
docker compose --env-file deploy/.env -f deploy/compose.yaml exec -T rabbitmq \
  rabbitmqctl list_queues name messages_ready messages_unacknowledged consumers
```

Pending rows survive Knowledge service/broker restarts and reset never clears them. Check broker
connectivity and the RAG service queue/bindings if rows keep retrying. Do not delete pending
rows to clear an error. Once delivery succeeds, an empty outbox means broker
acceptance, not finished indexing. Check `rag.note-events.dlq` and RAG service logs for
consumer failures; after fixing the cause, use the UI's reconcile/rebuild to repair
the derived index. The outbox does not replace PostgreSQL/RabbitMQ volume backups,
recover a lost index automatically, or provide exactly-once delivery.

## Nightly index reconciliation

The VPS has a `mnemo-agent` user cron job at **04:00 in the server's timezone**
(`Europe/Berlin`, including daylight-saving changes). It calls the existing
reconcile endpoint through the loopback UI proxy, not the rebuild endpoint.
Unchanged notes are skipped; missing/changed notes and stale index entries are
repaired without regenerating the entire index.

The source script is `deploy/reconcile-index.sh`. The installed copy and log
are outside the deployment checkout so normal Git updates do not remove them:

```sh
crontab -l
cat ~/.local/bin/mnemo-reconcile
tail -n 50 ~/.local/state/mnemo/reconcile.log
```

Automatic deployment refreshes the installed script from the tested checkout
after local application health checks pass. The replacement is atomic, so cron
cannot read a partially copied script. The existing schedule, log and lock are
preserved; cron installation is still a one-time host setup.

The script uses `flock` to prevent overlapping runs and a ten-minute HTTP timeout.
Failures are logged with a nonzero exit status; persistent errors still need
operator attention. To run it manually:

```sh
~/.local/bin/mnemo-reconcile >> ~/.local/state/mnemo/reconcile.log 2>&1
```

To install on another host or update the script after a manual deployment, run as the deployment
user from the repository root (requires `curl`, `flock`, and an active cron daemon):

```sh
install -d -m 700 ~/.local/bin ~/.local/state/mnemo
sh -n deploy/reconcile-index.sh
install -m 700 deploy/reconcile-index.sh ~/.local/bin/.mnemo-reconcile.new
mv -f ~/.local/bin/.mnemo-reconcile.new ~/.local/bin/mnemo-reconcile
(crontab -l 2>/dev/null | grep -v '# mnemo-nightly-reconcile$'; \
  printf '0 4 * * * %s/.local/bin/mnemo-reconcile >> %s/.local/state/mnemo/reconcile.log 2>&1 # mnemo-nightly-reconcile\n' "$HOME" "$HOME") | crontab -
```

Reconciliation is a safety net for the derived index, not a replacement for the
outbox, DLQ investigation, or backups. Its log is a small append-only daily log.
