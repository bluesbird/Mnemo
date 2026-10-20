"""Real REST -> PostgreSQL -> RabbitMQ -> MS2/Chroma -> chat lifecycle."""

import base64
import json
import time
import urllib.error
import urllib.request

MS1 = "http://ms1:8080/api/v1/notes"
ADMIN_RESET = "http://ms1:8080/api/v1/admin/reset-database"
MS2 = "http://ms2:8000/api/v1"
BROKER = "http://rabbitmq:15672/api/queues/%2F/"
AUTH = "Basic " + base64.b64encode(b"e2e:e2e-only").decode()
RESET_KEY = "e2e-reset-key-that-is-long-enough-for-test"
NO_ANSWER = "I don't know based on the provided notes."


def request(url, method="GET", payload=None, expected=200, headers=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read().decode()
            assert response.status == expected, (url, response.status, body)
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        if exc.code == expected:
            return None
        raise AssertionError(f"{method} {url}: HTTP {exc.code}: {body}") from exc


def eventually(label, probe, timeout=60):
    deadline = time.monotonic() + timeout
    last = "not attempted"
    while True:
        try:
            result = probe()
            if result:
                print(f"PASS: {label}", flush=True)
                return result
            last = repr(result)
        except (AssertionError, urllib.error.URLError, TimeoutError, OSError) as exc:
            last = repr(exc)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(f"Timed out waiting for {label}; last observation: {last}")
        time.sleep(min(0.5, remaining))


def queue(name="ms2.note-events"):
    return request(BROKER + name, headers={"Authorization": AUTH})


def consumer_ready():
    state = queue()
    assert state.get("consumers", 0) == 1, state
    return True


def broker_drained():
    state, dead = queue(), queue("ms2.note-events.dlq")
    assert state.get("consumers") == 1, state
    assert state.get("messages") == 0, state
    assert dead.get("messages") == 0, dead
    return True


def chat():
    return request(MS2 + "/chat/query", "POST",
                   {"question": "What is the observatory access code?", "top_k": 4})


def assert_indexed(note, present, absent):
    response = chat()
    assert present in response["answer"], response
    assert absent not in response["answer"], response
    assert response["sources"], response
    for source in response["sources"]:
        assert source["note_id"] == note["id"], response
        assert source["source_hash"] == note["sourceHash"], response
        assert source["note_title"] == note["title"], response
        assert source["chunk_index"] == 0, response
        assert present in source["excerpt"] and absent not in source["excerpt"], response
    return True


def assert_removed():
    response = chat()
    assert response == {"answer": NO_ANSWER, "sources": []}, response
    return True


def main():
    eventually("MS1/PostgreSQL ready", lambda: request(MS1) == [], timeout=120)
    eventually("MS2 HTTP ready", lambda: request(MS2 + "/health")["status"] == "ok",
               timeout=120)
    # HTTP health alone does not prove queue/binding declaration. Do not race creation.
    eventually("RabbitMQ consumer and binding ready", consumer_ready)
    eventually("fresh empty index", assert_removed)

    original = {"title": "Observatory access", "content": "The observatory access code is amber-1729."}
    changed = {"title": "Observatory access revised",
               "content": "The observatory access code is violet-3141."}
    created = request(MS1, "POST", original, expected=201)
    note_url = MS1 + "/" + str(created["id"])
    persisted = request(note_url)
    # PostgreSQL rounds timestamp precision; compare the persisted indexing contract.
    for field in ("id", "title", "content", "sourceHash"):
        assert persisted[field] == created[field], persisted
    assert created["sourceHash"], created
    eventually("create event indexes note and chat cites source",
               lambda: assert_indexed(created, "amber-1729", "violet-3141"))
    eventually("create event acknowledged, no dead letters", broker_drained)

    updated = request(note_url, "PUT", changed)
    assert updated["id"] == created["id"], updated
    assert updated["sourceHash"] != created["sourceHash"], updated
    persisted = request(note_url)
    assert persisted["content"] == changed["content"], persisted
    assert persisted["sourceHash"] == updated["sourceHash"], persisted
    eventually("update replaces content and source hash without stale chunks",
               lambda: assert_indexed(updated, "violet-3141", "amber-1729"))
    eventually("update event acknowledged, no dead letters", broker_drained)

    request(note_url, "DELETE", expected=204)
    request(note_url, expected=404)
    assert request(MS1 + "/index-metadata") == []
    eventually("delete removes index and stale chat sources", assert_removed)
    eventually("delete event acknowledged, no dead letters", broker_drained)
    # Check again after the consumer has acknowledged deletion.
    assert_removed()

    print("PASS: full event-driven lifecycle (no reconcile/rebuild calls)", flush=True)
    from proxy_smoke import run
    run(request, eventually)

    request(ADMIN_RESET, "POST", expected=401)
    request(ADMIN_RESET, "POST", headers={"X-Mnemo-Reset-Key": "wrong"}, expected=401)
    reset = request(
        ADMIN_RESET,
        "POST",
        headers={"X-Mnemo-Reset-Key": RESET_KEY},
        expected=202,
    )
    assert reset == {
        "status": "reset",
        "restoredNoteCount": 10,
        "indexRebuild": "queued",
    }, reset

    def starter_data_restored():
        restored = request(MS1)
        assert len(restored) == 10, restored
        assert any(note["title"] == "Attention Is All You Need" for note in restored), restored
        return True

    eventually("authenticated reset restores the starter notes", starter_data_restored)
    eventually("reset rebuild event acknowledged without dead letters", broker_drained)

    # The host runner verifies index contents read-only; reconciliation here could mask a missed event.
    print("PASS: authenticated reset and rebuild trigger queued", flush=True)


if __name__ == "__main__":
    main()
