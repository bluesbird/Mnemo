from app.rag.retrieval import Candidate, fuse, keyword_score, keywords, normalize_query


def test_normalize_query_drops_trailing_punctuation():
    assert normalize_query("  What is a transformer? ") == "What is a transformer"


def test_keywords_skip_stopwords_and_plurals():
    assert keywords("What is a transformer?") == {"transformer"}
    assert keyword_score(keywords("transformer"), "Transformers are models") == 1.0


def test_keyword_match_beats_weak_dense_score_and_junk_is_dropped():
    relevant = Candidate("2", "transformer paper", {}, dense_score=0.32, keyword_score=1.0)
    junk = Candidate("69", "hello", {}, dense_score=0.35)
    result = fuse([junk, relevant], min_dense_score=0.4, top_k=4)
    assert [c.chunk_id for c in result] == ["2"]


def test_strong_dense_match_without_keyword_is_kept():
    paraphrase = Candidate("1", "text", {}, dense_score=0.6)
    assert fuse([paraphrase], min_dense_score=0.4, top_k=4) == [paraphrase]
