import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

STARTER_NOTES_PATH = Path(
    os.environ.get(
        "STARTER_NOTES_FILE",
        Path(__file__).resolve().parent.parent
        / "knowledge-service"
        / "src"
        / "main"
        / "resources"
        / "starter-notes.json",
    )
)
STARTER_NOTES = json.loads(STARTER_NOTES_PATH.read_text(encoding="utf-8"))


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
            f"Knowledge service {method} {url} failed with HTTP {exc.code}: {detail}"
        ) from exc


def wait_for_knowledge(base_url):
    deadline = time.monotonic() + 120
    while True:
        try:
            return request_json(f"{base_url}/api/v1/notes")
        except (URLError, TimeoutError):
            if time.monotonic() >= deadline:
                raise RuntimeError("Timed out waiting for Knowledge service to accept requests.")
            time.sleep(2)


def seed_notes(base_url, get_json=request_json, post_json=request_json):
    notes_url = f"{base_url.rstrip('/')}/api/v1/notes"
    existing_notes = get_json(notes_url)
    if not isinstance(existing_notes, list):
        raise RuntimeError("Knowledge service returned an invalid note list during starter-data check.")
    if existing_notes:
        print(f"Starter data skipped: database already contains {len(existing_notes)} notes.")
        return False

    for note in STARTER_NOTES:
        post_json(notes_url, method="POST", payload=note)
    print(f"Loaded {len(STARTER_NOTES)} starter notes into the empty database.")
    return True


def main():
    base_url = os.environ.get("KNOWLEDGE_BASE_URL", "http://knowledge-service:8080")
    wait_for_knowledge(base_url)
    seed_notes(base_url)


if __name__ == "__main__":
    main()
