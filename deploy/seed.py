import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

STARTER_NOTES = (
    {
        "title": "Attention Is All You Need",
        "content": (
            "The 2017 paper Attention Is All You Need introduced the Transformer, "
            "an architecture that uses self-attention rather than recurrent layers "
            "to process sequences. Self-attention lets each token compare itself "
            "with other tokens, while positional information preserves sequence "
            "order. Multiple attention heads can learn different relationships in "
            "parallel. The encoder-decoder model achieved strong translation "
            "results and trained efficiently because sequence positions could be "
            "processed in parallel. Its ideas later became central to large "
            "language models, a reminder that a clear new perspective can reshape "
            "what a whole field is able to build."
        ),
    },
    {
        "title": "The dishwasher peace treaty",
        "content": (
            "We had both been loading the dishwasher with the quiet intensity of "
            "people who believe there is one correct geometry. We finally agreed "
            "that bowls go on the top rack and that neither of us is allowed to "
            "say \"I told you so\" until the cycle ends. The plates came out clean. "
            "Diplomacy remains a work in progress."
        ),
    },
    {
        "title": "A very small mystery",
        "content": (
            "The houseplant has a tiny paper hat. No one admits to making it. "
            "The plant seems pleased."
        ),
    },
    {
        "title": "Birdwatching, technically",
        "content": (
            "I bought a small notebook for birdwatching and went to the park with "
            "the confidence of someone who had read half an article. The first "
            "bird I saw was a pigeon. I wrote \"pigeon, very sure of itself.\" "
            "After that, I noticed a blackbird, two sparrows arguing over a crumb, "
            "and a duck that looked as if it had somewhere important to be. I "
            "still cannot identify every bird, but I can now spend an hour outside "
            "without checking my phone. The notebook has become less of a field "
            "guide and more of a record of tiny neighborhood personalities."
        ),
    },
    {
        "title": "The museum audio guide",
        "content": (
            "I rented the museum audio guide and accidentally selected the "
            "children's tour. A cheerful voice explained the ancient vase as "
            "\"a very old cup that had a big day.\" Honestly, that was enough "
            "context for me. I saw more exhibits than usual and learned that "
            "history is easier to remember when someone lets it be a little funny."
        ),
    },
    {
        "title": "Pancakes for one, plus the optimistic extra",
        "content": (
            "One egg, some flour, milk, and the confidence to make four pancakes "
            "instead of two."
        ),
    },
    {
        "title": "The umbrella's big day",
        "content": (
            "The forecast promised sun, so I left my umbrella at home. Naturally, "
            "it rained. I ducked into a bakery, where the person ahead of me was "
            "also waiting out the weather and offered to share the newspaper. We "
            "ended up comparing favorite soup recipes while the storm passed. "
            "By the time I stepped outside, the rain had stopped and I had a new "
            "recipe for lentil soup. The umbrella missed its outing, but the day "
            "managed to be useful anyway."
        ),
    },
    {
        "title": "Minutes from the household meeting",
        "content": (
            "Agenda: decide where the new lamp should go. Attendees: me, one cat. "
            "The cat sat in the box the lamp came in and declined to comment. "
            "After a long silence, I put the lamp by the chair. The cat approved "
            "by falling asleep under it. Motion carried."
        ),
    },
    {
        "title": "A shortcut with a scenic detour",
        "content": (
            "I tried a new shortcut home and got turned around near the community "
            "garden. A volunteer was watering the tomatoes and pointed me in the "
            "right direction, then insisted I take a handful of cherry tomatoes "
            "for the walk. I arrived ten minutes later than usual, with a small "
            "bag of tomatoes and a much better opinion of getting lost. The route "
            "was not shorter, exactly, but it did come with directions and a snack."
        ),
    },
    {
        "title": "The spare key",
        "content": (
            "Found the spare key in the place I put it so I would not lose it. "
            "Future me has finally come through."
        ),
    },
)


def request_json(url, method="GET", payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {} if body is None else {"Content-Type": "application/json"}
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            if response.status == 204:
                return None
            return json.loads(response.read())
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"MS1 {method} {url} failed with HTTP {exc.code}: {detail}"
        ) from exc


def wait_for_ms1(base_url):
    deadline = time.monotonic() + 120
    while True:
        try:
            return request_json(f"{base_url}/api/v1/notes")
        except (URLError, TimeoutError):
            if time.monotonic() >= deadline:
                raise RuntimeError("Timed out waiting for MS1 to accept requests.")
            time.sleep(2)


def seed_notes(base_url, get_json=request_json, post_json=request_json):
    notes_url = f"{base_url.rstrip('/')}/api/v1/notes"
    existing_notes = get_json(notes_url)
    if not isinstance(existing_notes, list):
        raise RuntimeError("MS1 returned an invalid note list during starter-data check.")
    if existing_notes:
        print(f"Starter data skipped: database already contains {len(existing_notes)} notes.")
        return False

    for note in STARTER_NOTES:
        post_json(notes_url, method="POST", payload=note)
    print(f"Loaded {len(STARTER_NOTES)} starter notes into the empty database.")
    return True


def main():
    base_url = os.environ.get("MS1_BASE_URL", "http://ms1-knowledge-service:8080")
    wait_for_ms1(base_url)
    seed_notes(base_url)


if __name__ == "__main__":
    main()
