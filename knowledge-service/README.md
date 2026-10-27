# Knowledge Service

Java/Spring Boot service that owns Mnemo notes and optional summaries.

## Role in the system

- Source of truth for note data in PostgreSQL.
- Exposes note CRUD and on-demand summarization APIs.
- Publishes note change events through a transactional outbox to RabbitMQ.

## Main API

- `GET /api/v1/notes`
- `GET /api/v1/notes/{id}`
- `POST /api/v1/notes`
- `PUT /api/v1/notes/{id}`
- `DELETE /api/v1/notes/{id}`
- `POST /api/v1/notes/{id}/summarize`
- `GET /api/v1/notes/index-metadata`
- `POST /api/v1/admin/reset-database` (requires `X-Mnemo-Reset-Key`)
- `GET /health`

OpenAPI UI: `/swagger-ui.html`

## Key configuration

- `SPRING_DATASOURCE_URL`, `spring.datasource.username`, `spring.datasource.password`
- `SPRING_RABBITMQ_HOST` (+ optional port/credentials)
- `MNEMO_RESET_API_KEY` (enables authenticated reset endpoint)
- `APP_SUMMARY_ENABLED` (`true` by default)
- `APP_CORS_ALLOWED_ORIGINS`
- `SPRING_PROFILES_ACTIVE=groq` + `GROQ_API_KEY` for deployed summarization

Flyway migrations live under `src/main/resources/db/migration`.

## Run and test

From `knowledge-service`:

```powershell
mvnw.cmd test
mvnw.cmd spring-boot:run
```
