# Phase 18: Public Deployment

## Scope

Deploy Mnemo at `https://mnemo-hub.duckdns.org` on the VPS using Docker Compose.
Anonymous visitors can use all current functionality: note CRUD, enrichment,
chat, reconcile and rebuild. Data is shared, synthetic and disposable.
No login, users, read-only mode or deployment-specific backend mode.

## Plan

1. [x] **Public index operations:** move reconcile/rebuild from `/api/v1/admin/index/*`
   to `/api/v1/index/*`. Remove their obsolete admin-key checks and configuration;
   update callers and tests. No compatibility aliases.
2. [x] **Deployment configuration:** use a separate Compose file, persistent volumes,
   external database/broker credentials, and private backend ports. Keep local
   development working as before.
3. [x] **HTTPS and routing:** Caddy handles Let's Encrypt certificates; the existing
   UI Nginx serves frontend files and proxies the supported API routes.
4. [x] **Resource limits:** bound chat/enrichment traffic and concurrency, request
   sizes and Ollama resources. Reconcile and rebuild each allow one request per
   minute globally. Keep configuration small; no custom limiting service.
5. [x] **Starter data:** load ten fictional notes with varied topics and lengths on
   an empty database only. Normal deployment must not overwrite existing notes.
   One note is "Attention Is All You Need"; the rest are humorous fictional notes.
6. [x] **Authenticated reset:** add an admin endpoint that clears notes/tags,
   restores the same ten starter notes, and best-effort triggers an MS2 full
   rebuild event. If MS2/RabbitMQ is unavailable, data reset still succeeds.
7. **Deploy and verify:** confirm server permissions/firewall, deploy, then check
   HTTPS, all user actions, limits, private ports and persistence after restart.
   Document the commands needed to start, update and troubleshoot the deployment.

### Step 7 preflight

Preparation completed on the VPS:

- SSH, repository ownership and Docker access work. The checkout was
  fast-forwarded to `039ee6f`.
- DNS resolves to the VPS address.
- `deploy/.env` was generated on the VPS with random passwords/reset key and
  mode `0600`; no credentials were printed or added to Git.
- All three application images were built successfully. PostgreSQL, RabbitMQ,
  starter-data and Caddy images were downloaded.

Application startup remains blocked by host Ollama setup. No `ollama`
executable or running service was found, and `mnemo-agent` has no passwordless
sudo. An administrator must install the host service, bind it to the private
Docker bridge address (`172.17.0.1` on this VPS), apply the documented resource
limits and download `qwen3:4b` and `qwen3-embedding:0.6b`. See `deploy/README.md`.
Do not expose port 11434 publicly.

No application containers have been started. Container-to-Ollama connectivity,
firewall/public port access, HTTPS, real-model behavior, application limits and
restart persistence still need verification. Step 7 is not complete.

## Boundaries

- Add only necessary configuration, small helpers and focused regression tests.
- No custom deployment framework, general login system or unrelated refactoring.
- Public index operations do not need a key injected by the proxy.
- The reset endpoint must stay authenticated by a server-side secret and is not
  exposed as a public UI action.

## Done

The public HTTPS deployment works with real models, the above checks pass, and
the operating instructions are reproducible. Configuration alone is not completion.

## VPS Info
SSH access to my VPS:
- Host alias: `mnemo-vps`
- User: `mnemo-agent`
- OS: Ubuntu 24.04
- Project directory: `/opt/mnemo/Mnemo`
- Docker and Docker Compose are installed.

Connect using:
```bash
ssh mnemo-vps
```

The SSH key and configuration are already set up locally on my Windows machine. Do not ask for passwords, passphrases, or private keys.
