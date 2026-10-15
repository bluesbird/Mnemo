import logging
import re
from dataclasses import dataclass

from tokenizers import Tokenizer

from app.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str


class NoteChunker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._tokenizer: Tokenizer | None = None
        self._tokenizer_attempted = False

    def chunk_note(self, title: str, content: str) -> list[Chunk]:
        text = f"{title.strip()}\n\n{content.strip()}".strip()
        if text == "":
            return []
        if self._count_tokens(text) <= self._settings.chunk_size_tokens:
            return [Chunk(index=0, text=text)]

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs:
            return [Chunk(index=0, text=text)]

        chunks: list[Chunk] = []
        current = ""
        current_tokens = 0

        for paragraph in paragraphs:
            para_tokens = self._count_tokens(paragraph)
            if para_tokens > self._settings.chunk_size_tokens:
                for piece in self._split_large_paragraph(paragraph):
                    chunks.append(Chunk(index=len(chunks), text=piece))
                continue

            separator = "\n\n" if current else ""
            projected_text = f"{current}{separator}{paragraph}"
            projected_tokens = self._count_tokens(projected_text)
            if projected_tokens <= self._settings.chunk_size_tokens:
                current = projected_text
                current_tokens = projected_tokens
                continue

            chunks.append(Chunk(index=len(chunks), text=current))
            overlap = self._overlap_tail(current)
            current = f"{overlap}\n\n{paragraph}".strip() if overlap else paragraph
            current_tokens = self._count_tokens(current)
            if current_tokens > self._settings.chunk_size_tokens:
                for piece in self._split_large_paragraph(current):
                    chunks.append(Chunk(index=len(chunks), text=piece))
                current = ""
                current_tokens = 0

        if current:
            chunks.append(Chunk(index=len(chunks), text=current))
        return chunks

    def _split_large_paragraph(self, paragraph: str) -> list[str]:
        words = paragraph.split()
        if not words:
            return []
        chunks: list[str] = []
        step = max(1, self._settings.chunk_size_tokens - self._settings.chunk_overlap_tokens)
        start = 0
        while start < len(words):
            end = min(len(words), start + self._settings.chunk_size_tokens)
            chunk = " ".join(words[start:end]).strip()
            if chunk:
                chunks.append(chunk)
            if end == len(words):
                break
            start += step
        return chunks

    def _overlap_tail(self, text: str) -> str:
        if self._settings.chunk_overlap_tokens <= 0:
            return ""
        words = text.split()
        if not words:
            return ""
        return " ".join(words[-self._settings.chunk_overlap_tokens :])

    def _count_tokens(self, text: str) -> int:
        tokenizer = self._get_tokenizer()
        if tokenizer is None:
            return max(1, len(text.split()))
        return len(tokenizer.encode(text).ids)

    def _get_tokenizer(self) -> Tokenizer | None:
        if self._tokenizer_attempted:
            return self._tokenizer
        self._tokenizer_attempted = True
        try:
            self._tokenizer = Tokenizer.from_pretrained(
                self._settings.tokenizer_name,
                revision=self._settings.tokenizer_revision,
            )
            logger.info(
                "Loaded tokenizer %s@%s",
                self._settings.tokenizer_name,
                self._settings.tokenizer_revision,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Tokenizer load failed (%s). Falling back to word-based counting.",
                exc,
            )
            self._tokenizer = None
        return self._tokenizer
