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
chat questions are limited to 4,000 characters and chat answers to 256 tokens.
MS1 enrichment allows 2,048 generated tokens per call (summary and tags are
separate calls), including Qwen3's reasoning. This is a ceiling, not a target;
CPU-only inference can still be slow. Empty or incomplete enrichment responses
return an HTTP 502 error and leave the note's existing summary and tags unchanged.
These deployment-only limits are disabled in the root local-development Compose
stack. Caddy replaces the forwarded client-IP header, and Nginx trusts it only
from Caddy's fixed address (`172.30.0.2`) on the private proxy network. Dynamic
addresses, including the UI's, are allocated from `172.30.0.128/25` so they cannot
claim Caddy's address. Existing deployments must recreate the proxy network
with `docker compose --env-file deploy/.env -f deploy/compose.yaml down` before
starting again; omit `--volumes` to preserve data.

Ollama runs on the VPS host and is not managed by this Compose project. An
administrator must install Ollama using its official Linux installation
instructions before starting the application. Both backends connect through
Docker's host gateway, so a loopback-only Ollama listener is not sufficient.
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
override, restart Ollama and download both required models:

```sh
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl restart ollama
export OLLAMA_HOST=http://172.17.0.1:11434
ollama pull qwen3:4b
ollama pull qwen3-embedding:0.6b
curl --fail "$OLLAMA_HOST/api/tags"
```

The deployment uses the chat model for both MS1 and MS2, plus MS2's embedding
model. If keeping both loaded exceeds the VPS memory budget, lower the
loaded-model limit and expect extra model reload latency. MS1 and MS2 chat calls
also cap context at 4,096 tokens.

Create a private deployment environment file and set both passwords plus the
reset key to strong, unique values. Compose refuses to run while any value is
empty:

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
