# RAG Service

Python/FastAPI service that maintains the vector index and answers questions with grounded sources.

## Role in the system

- Builds and updates ChromaDB index entries from Knowledge service notes.
- Consumes note change events from RabbitMQ for incremental sync.
- Serves retrieval-augmented chat answers with source note references.
- Summarizes submitted conversation history separately from note retrieval.
- Offers manual reconcile/rebuild operations for index recovery.

## Main API

- `GET /api/v1/health`
- `POST /api/v1/chat/query`
- `POST /api/v1/index/reconcile`
- `POST /api/v1/index/rebuild`

FastAPI docs: `/docs`

## Conversation summaries

`POST /api/v1/chat/query` accepts up to 500 prior user/assistant messages
(2,000 characters per message), excluding the current question. The configured
chat model classifies the current request from its meaning; no
frontend or backend trigger-phrase list is used. This costs one additional
short model call per question.

Note questions retain the existing retrieval path and latest 10-message
context. Conversation summaries use all submitted history and return no note
sources. Short conversations need one summary call; longer ones update a
running recap in chronological order, with no recursive merge. Each step also
receives the actual request so language and requested focus are retained.
Summaries recap what was said, not independently verified note facts.

Summary input uses a conservative UTF-8 byte budget derived from
`RAG_CHAT_NUM_CTX`, reserving room for instructions, the previous recap and
`RAG_CHAT_NUM_PREDICT`. This works with the default byte-level Qwen tokenizers.
Very long conversations require more calls and are slower; a context that
cannot fit the prompt or a provider failure returns an error, not a partial
summary. Neither summaries nor routing decisions are stored on the server.

## Key configuration

All variables are `RAG_`-prefixed.

- `RAG_KNOWLEDGE_BASE_URL`
- `RAG_OLLAMA_BASE_URL`
- `RAG_CHAT_PROVIDER=ollama|groq`
- `RAG_GROQ_API_KEY` (required when `RAG_CHAT_PROVIDER=groq`)
- `RAG_EMBEDDING_MODEL` (default `qwen3-embedding:0.6b`)
- `RAG_CHAT_MODEL` (default `qwen3:4b`)
- `RAG_CHAT_NUM_CTX` (default `4096`), `RAG_CHAT_NUM_PREDICT` (default `256`)
- `RAG_CHUNK_SIZE_TOKENS`, `RAG_CHUNK_OVERLAP_TOKENS`
- `RAG_RABBITMQ_ENABLED` + RabbitMQ host/queue settings
- `RAG_LOG_FORMAT=text|json`

## Run and test

From `rag-service`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Optional real-model checks for paraphrases and multi-topic summaries (local
Ollama with `qwen3:4b` must be running):

```powershell
$env:MNEMO_LIVE_CHAT_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest tests\services\test_chat_summary_live.py -q
```
