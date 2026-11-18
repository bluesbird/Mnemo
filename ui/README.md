# UI

React/TypeScript frontend for Mnemo note management and grounded chat.

## Role in the system

- Note editor and note list/search UI.
- Manual summary trigger for saved notes.
- Chat interface with source-note navigation.
- Same-origin proxy mode in production (`/api` and `/rag-api`).

## Main flows

- Notes: create, update, delete, summarize, search.
- Chat: ask grounded questions, summarize the conversation, inspect source notes, trigger index reconcile/rebuild.
- In-session chat history is stored in `sessionStorage`. Each request sends up
  to 500 prior non-error messages to the backend, which identifies the intent
  using the configured model rather than a list of trigger phrases.
  Note answers use only the latest 10 messages as conversational context;
  summaries process all submitted history without retrieving notes.
  Longer sessions show a notice that earlier messages are outside this window.

## Configuration

Defaults are proxy-based and require no browser API keys.

- `VITE_API_BASE_URL` (optional; direct Knowledge service base)
- `VITE_RAG_API_BASE_URL` (optional; direct RAG service base)

See `.env.example` for direct-call examples.

## Run and test

From `ui`:

```powershell
npm install
npm test
npm run dev
npm run build
```
