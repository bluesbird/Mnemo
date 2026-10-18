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
chat questions are limited to 4,000 characters and generated answers to 256 tokens.
These deployment-only limits are disabled in the root local-development Compose
stack. Caddy replaces the forwarded client-IP header, and Nginx trusts it only
from Caddy's fixed address on the private proxy network.

Ollama runs on the VPS host and is not managed by this Compose project. Configure
its service with bounded parallelism and queueing; for systemd, for example:

```ini
[Service]
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_MAX_QUEUE=16"
```

Apply the environment to the Ollama service and restart it. The deployment uses two models: the chat model (shared by MS1 and MS2) and MS2's
embedding model. If keeping both loaded exceeds the VPS memory budget, lower the
loaded-model limit and expect extra model reload latency. MS1 and MS2 chat calls
also cap context at 4,096 tokens.

Create a private deployment environment file and set both passwords to strong,
unique values. Compose refuses to run while either value is empty:

```sh
cp deploy/.env.example deploy/.env
${EDITOR:-vi} deploy/.env
```

Start or update the deployment from the repository root:

```sh
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d --build
```

The Compose project creates named volumes for PostgreSQL, RabbitMQ, ChromaDB,
the MS2 tokenizer cache, and Caddy's TLS certificates and state. Normal
stop/start and image updates preserve them. Do not use `down --volumes` unless
deleting all stored application/index data and TLS state is intended. Keep
`deploy/.env` private and out of version control.

Inspect service status and logs with:

```sh
docker compose --env-file deploy/.env -f deploy/compose.yaml ps
docker compose --env-file deploy/.env -f deploy/compose.yaml logs --tail 100
```
