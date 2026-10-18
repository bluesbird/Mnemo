from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    env: str


class IndexMetadataItem(BaseModel):
    note_id: int = Field(alias="noteId")
    source_hash: str = Field(alias="sourceHash")


class NoteForIndex(BaseModel):
    id: int
    title: str
    content: str
    source_hash: str = Field(alias="sourceHash")


class NoteEvent(BaseModel):
    schema_version: int = 1
    event_id: str
    event_type: str
    occurred_at: str
    note_id: int | None = None


class NoteSyncResult(BaseModel):
    note_id: int
    action: str


class IndexOperationResponse(BaseModel):
    indexed_note_ids: list[int]
    deleted_note_ids: list[int]
    skipped_note_ids: list[int]
    total_ms1_notes: int


class ChatQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class ChatSourceReference(BaseModel):
    note_id: int
    note_title: str
    chunk_index: int
    source_hash: str
    score: float
    excerpt: str


class ChatQueryResponse(BaseModel):
    answer: str
    sources: list[ChatSourceReference]
