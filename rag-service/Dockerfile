FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    RAG_CHROMA_PATH=/app/data/chroma

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install . \
    && useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data /app/.cache \
    && chown -R appuser /app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
    CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/api/v1/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
