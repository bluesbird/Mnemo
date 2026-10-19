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
7. [x] **Deploy and verify:** confirm server permissions and effective public port
   exposure, deploy, then check HTTPS, user actions, limits and index recovery.
   A destructive live reset and full-stack restart are optional for this demo.
   Document the commands needed to start, update and troubleshoot the deployment.

### Step 7 status

The application is deployed at `https://mnemo-hub.duckdns.org`.
The earlier host Ollama/startup blocker is resolved. Production uses Groq for
text generation and host Ollama for embeddings; local development remains
Ollama-only.

Completed:

- SSH, repository ownership and Docker access work.
- DNS, public HTTPS and application/API routing work.
- Server-side deployment credentials were configured without committing them.
- Note create/update/delete and real-model enrichment/chat work.
- Note lifecycle events and matching MS2 index updates were verified.
- Input-length validation was checked through the public APIs.
- Existing data survived application container recreation during updates.
- Start, update, reset and troubleshooting commands are in `deploy/README.md`.
- GitHub Actions automatically deploys pushes to `main` after CI passes.
  The first automatic deployment passed local and public HTTPS checks.

### Live verification (2026-10-20)

- External TCP probes of the published IPv4 address reached SSH (22), HTTP (80)
  and HTTPS (443). PostgreSQL (5432), RabbitMQ (4369, 5671/5672,
  15671/15672, 15691/15692, 25672), backends (8000, 8080), UI diagnostic port
  (8081), Ollama (11434) and Caddy admin (2019) were closed or filtered.
  Host listeners and Docker port bindings agree: UI is loopback-only and
  Ollama listens on the private Docker bridge. Direct UFW rule inspection
  requires administrator privileges and was not performed; this verifies
  observed exposure, not the complete firewall ruleset or external IPv6 access.
- Missing and incorrect reset keys both returned HTTP 401. No authenticated
  reset was executed and no source notes were deleted.
- Controlled bursts using invalid requests returned HTTP 429 for chat and
  enrichment. No valid AI requests or Groq inference calls were needed.
- Two incomplete chat request bodies occupied the shared model-backed request
  slots; a third request returned HTTP 429. Connections were then closed.
- A request exceeding 256 KiB returned HTTP 413.
- Reconcile returned HTTP 200 and skipped all 13 current notes, confirming
  their index state was already current. Rebuild returned HTTP 200 and indexed
  all 13 notes. Immediate follow-up GETs to each operation returned HTTP 429,
  verifying their global request limits without executing a second operation.
- Source notes were identical before and after index verification. Final public
  UI, notes API and MS2 health checks all returned HTTP 200.

Step 7 is complete for the agreed demo scope. Full-stack restart persistence
and a successful authenticated live reset were intentionally not exercised;
application recreation has preserved data and automated reset tests exist.
Do not expose Ollama port 11434 publicly or use `down --volumes` for restart
verification.

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
