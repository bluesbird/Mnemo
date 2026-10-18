from deploy.seed import STARTER_NOTES, seed_notes


def test_seed_populates_only_an_empty_database():
    notes = []
    created = []

    def get_json(_url):
        return list(notes)

    def post_json(_url, method, payload):
        assert method == "POST"
        notes.append(payload)
        created.append(payload)

    assert seed_notes("http://ms1", get_json, post_json) is True
    assert len(created) == 10
    assert len(notes) == 10
    assert any(note["title"] == "Attention Is All You Need" for note in notes)
    word_counts = [len(note["content"].split()) for note in notes]
    assert len({len(note["content"]) for note in notes}) > 1
    assert min(word_counts) <= 20
    assert max(word_counts) >= 80
    assert 520 <= sum(word_counts) <= 600


def test_seed_leaves_existing_notes_untouched():
    existing = [{"id": 1, "title": "Existing", "content": "Keep this note."}]
    posts = []

    def get_json(_url):
        return existing

    def post_json(*args, **kwargs):
        posts.append((args, kwargs))

    assert seed_notes("http://ms1", get_json, post_json) is False
    assert posts == []
