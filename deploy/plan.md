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
2. **Deployment configuration:** use a separate Compose file, persistent volumes,
   external database/broker credentials, and private backend ports. Keep local
   development working as before.
3. **HTTPS and routing:** Caddy handles Let's Encrypt certificates; the existing
   UI Nginx serves frontend files and proxies the supported API routes.
4. **Resource limits:** bound chat/enrichment traffic and concurrency, request
   sizes and Ollama resources. Reconcile and rebuild each allow one request per
   minute globally. Keep configuration small; no custom limiting service.
5. **Starter data:** load ten fictional notes with varied topics and lengths on
   an empty database only. Normal deployment must not overwrite existing notes.
6. **Deploy and verify:** confirm server permissions/firewall, deploy, then check
   HTTPS, all user actions, limits, private ports and persistence after restart.
   Document the commands needed to start, update and troubleshoot the deployment.

## Boundaries

- Add only necessary configuration, small helpers and focused regression tests.
- No custom deployment framework, new authentication system or unrelated refactoring.
- Public index operations do not need a key injected by the proxy.
- **Later, separate phase:** add an authenticated **reset database** endpoint that
  clears application data, restores the ten starter notes and rebuilds the index.
  Do not implement reset or its authentication in phase 18.

## Done

The public HTTPS deployment works with real models, the above checks pass, and
the operating instructions are reproducible. Configuration alone is not completion.
