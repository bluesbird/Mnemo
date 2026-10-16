import re
from dataclasses import dataclass

_STOPWORDS = frozenset(
    """a an the is are was were be been am do does did what whats which who whom whose when where why how
    of in on at to for from with by about as into and or but not no it its this that these those there
    i you he she we they me my your our their can could should would will shall may might tell explain
    describe define please give show
    der die das ein eine einen ist sind war was wie wer wo wann warum und oder nicht mit von zu im
    """.split()
)
_WORD = re.compile(r"\w+", re.UNICODE)
_RRF_K = 60


def normalize_query(question: str) -> str:
    """Trim whitespace and trailing punctuation that only adds noise to the embedding."""
    return question.strip().rstrip("?!.:;, ").strip()


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def tokens(text: str) -> set[str]:
    return {_stem(w) for w in _WORD.findall(text.lower())}


def keywords(question: str) -> set[str]:
    return {_stem(w) for w in _WORD.findall(question.lower()) if w not in _STOPWORDS}


def keyword_score(query_keywords: set[str], text: str) -> float:
    """Fraction of the question's keywords that appear in the text."""
    if not query_keywords:
        return 0.0
    return len(query_keywords & tokens(text)) / len(query_keywords)


@dataclass
class Candidate:
    chunk_id: str
    document: str
    metadata: dict
    dense_score: float = 0.0
    keyword_score: float = 0.0


def fuse(candidates: list[Candidate], min_dense_score: float, top_k: int) -> list[Candidate]:
    """Merge dense and keyword rankings (reciprocal rank fusion).

    A chunk is kept if it contains a question keyword or is similar enough on its own.
    """
    kept = [c for c in candidates if c.keyword_score > 0 or c.dense_score >= min_dense_score]
    by_dense = sorted(kept, key=lambda c: c.dense_score, reverse=True)
    by_keyword = sorted((c for c in kept if c.keyword_score > 0), key=lambda c: c.keyword_score, reverse=True)

    fused: dict[str, float] = {}
    for ranking in (by_dense, by_keyword):
        for rank, candidate in enumerate(ranking):
            fused[candidate.chunk_id] = fused.get(candidate.chunk_id, 0.0) + 1.0 / (_RRF_K + rank + 1)

    return sorted(kept, key=lambda c: fused[c.chunk_id], reverse=True)[:top_k]
