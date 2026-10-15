import logging

import httpx

from app.config import Settings
from app.schemas import IndexMetadataItem, NoteForIndex

logger = logging.getLogger(__name__)


class Ms1Client:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ms1_base_url.rstrip("/")
        self._client = httpx.Client(timeout=settings.ms1_timeout_seconds)

    def fetch_index_metadata(self) -> list[IndexMetadataItem]:
        response = self._client.get(f"{self._base_url}/api/v1/notes/index-metadata")
        response.raise_for_status()
        data = response.json()
        metadata = [IndexMetadataItem.model_validate(item) for item in data]
        logger.info("Fetched %s note metadata records from MS1", len(metadata))
        return metadata

    def fetch_note(self, note_id: int) -> NoteForIndex | None:
        response = self._client.get(f"{self._base_url}/api/v1/notes/{note_id}")
        if response.status_code == 404:
            logger.info("Note %s no longer exists in MS1", note_id)
            return None
        response.raise_for_status()
        return NoteForIndex.model_validate(response.json())
