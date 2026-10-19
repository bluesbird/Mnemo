# Deployment Compose

This Compose project is separate from the local-development stack in the
repository root. It keeps PostgreSQL, RabbitMQ and both application services
off host-published ports. Caddy listens on ports 80 and 443, obtains and renews
certificates for `mnemo-hub.duckdns.org`, and forwards HTTPS traffic to the UI's
nginx server. Nginx serves the frontend and proxies API requests to MS1 and MS2.
The UI is also available on `127.0.0.1:8081` for local diagnostics.

Before starting the stack, point the domain's DNS A record to the VPS public IPv4
address and allow inbound TCP ports 80/443 through the host firewall and any
provider firewall. Caddy cannot issue certificates until the domain resolves
to that server and those ports are reachable.

## Resource limits

Deployment Nginx limits each client IP to 30 chat requests/minute (burst 20)
and 10 enrichment requests/minute (burst 5). It allows at most two concurrent
model-backed HTTP operations across all clients. Reconcile and rebuild are each
limited globally to one request/minute. Requests larger than 256 KiB are rejected;
Note titles are limited to 70 characters, note bodies to 5,000 and chat questions
to 500 in both local and deployed apps. Chat answers are limited to 256 tokens.
MS1 enrichment allows 2,048 generated tokens per call (summary and tags are
separate calls). Groq reasoning is disabled for both services. Empty or
incomplete enrichment responses return an HTTP 502 error and leave the note's
existing summary and tags unchanged.
These deployment-only limits are disabled in the root local-development Compose
stack. Caddy replaces the forwarded client-IP header, and Nginx trusts it only
from Caddy's fixed address (`172.30.0.2`) on the private proxy network. Dynamic
addresses, including the UI's, are allocated from `172.30.0.128/25` so they cannot
claim Caddy's address. Existing deployments must recreate the proxy network
with `docker compose --env-file deploy/.env -f deploy/compose.yaml down` before
starting again; omit `--volumes` to preserve data.

## AI providers

Local development keeps Ollama for enrichment, chat and embeddings; no Groq
key is needed. Deployment uses GroqCloud (`qwen/qwen3.8-27b`) for MS1 enrichment
and MS2 RAG answer generation. MS1 activates the `groq` Spring profile; MS2 sets
`MS2_CHAT_PROVIDER=groq`. Both read the same `GROQ_API_KEY` from `deploy/.env`
(mapped to `MS2_GROQ_API_KEY` for MS2). Keys never belong in browser assets,
committed configuration or logs.

Groq receives the title/content of notes being enriched, and questions plus
retrieved note excerpts for RAG answers. Only use synthetic/non-sensitive data
in this public deployment. Requests are subject to your organization's shared
Groq quota: each enrichment uses two requests, each grounded RAG answer one.
Failures are reported explicitly, with no automatic fallback to local inference
or application-level retries. Check the account's Limits page for current quotas.

Embeddings remain on host Ollama (`qwen3-embedding:0.6b`) in both environments.
This preserves Chroma's embedding dimensions and indexing version; switching
generation providers needs no rebuild or data migration.

Ollama runs on the VPS host and is not managed by this Compose project. An
administrator must install Ollama using its official Linux installation
instructions before starting the application. MS2 connects through Docker's host
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

The endpoint returns `202 Accepted` after replacing notes/tags and requesting an
MS2 full rebuild event. Event publication is best effort: if RabbitMQ/MS2 is
currently unavailable, the reset still succeeds and an operator should run index
rebuild/reconcile once dependencies are healthy.

Start or update the deployment from the repository root:

```sh
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d --build
```

## Automatic deployment

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
notes API and MS2 health locally and over public HTTPS without invoking AI.
There is no automatic rollback: a failed deployment/check is visible in Actions;
inspect container status/logs on the VPS before retrying. CI failures leave the
running deployment untouched. View deployment output in the workflow's
`Deploy to VPS` job.

The Compose project creates named volumes for PostgreSQL, RabbitMQ, ChromaDB,
the MS2 tokenizer cache, and Caddy's TLS certificates and state. Normal
stop/start and image updates preserve them. Do not use `down --volumes` unless
deleting all stored application/index data and TLS state is intended. Keep
`deploy/.env` private and out of version control.

On first startup, the `starter-data` job reads the same canonical note catalog
used by reset and creates the ten fictional notes only if MS1's note list is
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
