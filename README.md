# Personal Knowledge Hub

Monorepo with three independent project modules:

- `ms1-knowledge-service`: Java / Spring Boot knowledge API (current implementation)
- `ms2-rag-service`: Python / FastAPI RAG service (stub for now)
- `ui`: React + TypeScript frontend (stub for now)

## Structure

```text
personal-knowledge-hub/
├── ms1-knowledge-service/
├── ms2-rag-service/
├── ui/
├── compose.yaml
└── README.md
```

## Quick start (MS1 + Postgres)

1. Start PostgreSQL:
   - `docker compose up -d db`
2. Run MS1:
   - `cd ms1-knowledge-service`
   - `./mvnw spring-boot:run` (Linux/macOS)
   - `mvnw.cmd spring-boot:run` (Windows)

