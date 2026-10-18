# Deployment Compose

This Compose project is separate from the local-development stack in the
repository root. It keeps PostgreSQL, RabbitMQ and both application services
off host-published ports. The UI is available only on `127.0.0.1:8081`, ready
for a host reverse proxy.

Create a private deployment environment file and set both passwords to strong,
unique values. Compose refuses to run while either value is empty:

```powershell
Copy-Item deploy\.env.example deploy\.env
```

Start or update the deployment from the repository root:

```powershell
docker compose --env-file deploy\.env -f deploy\compose.yaml up -d --build
```

The Compose project creates named volumes for PostgreSQL, RabbitMQ, ChromaDB and
the MS2 tokenizer cache. Normal stop/start and image updates preserve them. Do
not use `down --volumes` unless deleting all stored application/index data is
intended. Keep `deploy\.env` private and out of version control.

Inspect service status and logs with:

```powershell
docker compose --env-file deploy\.env -f deploy\compose.yaml ps
docker compose --env-file deploy\.env -f deploy\compose.yaml logs --tail 100
```
