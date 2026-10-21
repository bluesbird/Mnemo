from deploy.seed import STARTER_NOTES, seed_notes


def test_seed_populates_only_an_empty_database():
    notes = []

    def get_json(_url):
        return list(notes)

    def post_json(_url, method, payload):
        assert method == "POST"
        notes.append(payload)

    assert seed_notes("http://ms1", get_json, post_json) is True
    assert notes == STARTER_NOTES


def test_seed_leaves_existing_notes_untouched():
    existing = [{"id": 1, "title": "Existing", "content": "Keep this note."}]
    posts = []

    def get_json(_url):
        return existing

    def post_json(*args, **kwargs):
        posts.append((args, kwargs))

    assert seed_notes("http://ms1", get_json, post_json) is False
    assert posts == []
