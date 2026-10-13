# Personal Knowledge Hub

Monorepo with three independent project modules:

- `ms1-knowledge-service`: Java / Spring Boot knowledge API (current implementation)
- `ms2-rag-service`: Python / FastAPI RAG service (stub for now)
- `ui`: React + TypeScript frontend for note management

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

## UI quick start

1. Install UI dependencies:
   - `cd ui`
   - `npm install`
2. Run the UI dev server:
   - `npm run dev`
3. Open:
   - `http://localhost:5173`

The UI defaults to `/api` and uses Vite proxy to reach MS1 at `http://localhost:8080`.

Optional direct browser-to-MS1 mode (uses CORS):

1. In `ui`, create `.env` from `.env.example`.
2. Set `VITE_API_BASE_URL=http://localhost:8080/api`.
3. Restart `npm run dev`.
