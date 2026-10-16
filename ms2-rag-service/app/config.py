from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MS2_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ms2-rag-service"
    app_env: str = "dev"

    ms1_base_url: str = "http://localhost:8080"
    ms1_timeout_seconds: float = 10.0

    admin_api_key: str | None = None

    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "qwen3-embedding:0.6b"
    chat_model: str = "qwen3:4b"
    chat_num_ctx: int = 4096
    chat_temperature: float = 0.1
    chat_think: bool = False
    query_instruction_prefix: str = (
        "Instruct: Given a question, retrieve notes that answer it\nQuery:"
    )

    chroma_path: str = "./data/chroma"
    chroma_collection_name: str = "notes"

    chunk_size_tokens: int = 400
    chunk_overlap_tokens: int = 50
    tokenizer_name: str = "Qwen/Qwen3-Embedding-0.6B"
    tokenizer_revision: str = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
    retrieval_top_k_default: int = 4
    retrieval_min_score: float = 0.4  # only for chunks without a keyword match

    log_format: str = "text"  # "text" or "json"

    rabbitmq_enabled: bool = True
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_username: str = "bluesbird"
    rabbitmq_password: str = "password"
    rabbitmq_heartbeat_seconds: int = 300
    events_exchange: str = "notes.events"
    events_queue: str = "ms2.note-events"
    events_dead_letter_exchange: str = "notes.events.dlx"
    events_dead_letter_queue: str = "ms2.note-events.dlq"
    events_max_attempts: int = 3
    events_retry_backoff_seconds: float = 2.0

    @property
    def indexing_version(self) -> str:
        return (
            f"v1|chunk={self.chunk_size_tokens}|overlap={self.chunk_overlap_tokens}"
            f"|embed={self.embedding_model}|tokenizer={self.tokenizer_name}@{self.tokenizer_revision}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
