"""Wire-level checks against nginx, plus a real-backend UI lifecycle."""

import json
import re
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.request


def fetch(url, method="GET", body=None, headers=None):
    req = urllib.request.Request(url, method=method, data=body, headers=headers or {})
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return response.status, response.headers, response.read()


def check_static():
    status, headers, body = fetch("http://ui/")
    assert status == 200 and "text/html" in headers["Content-Type"], (status, body)
    assert b'<div id="root">' in body, body
    assets = re.findall(rb'(?:src|href)="(/assets/[^"]+)"', body)
    assert assets, body
    for asset in assets:
        status, _, data = fetch("http://ui" + asset.decode())
        assert status == 200 and data, (asset, status)
        assert b"MS2_ADMIN_API_KEY" not in data, asset
    # Hash routes remain browser-side; nginx only sees "/".
    assert fetch("http://ui/#/chat")[0] == 200
    for path in ("/.env", "/docker/default.conf.template", "/missing.js"):
        assert fetch("http://ui" + path)[0] == 404, path
    print("PASS: static HTML/assets, hash route and no exposed runtime config", flush=True)
    return True


def check_proxy():
    cases = [
        ("/api", "/api", []),
        ("/api/v1/notes?q=a%20b&page=1", "/api/v1/notes?q=a%20b&page=1", []),
        ("/api/v1/notes/1/summarize", "/api/v1/notes/1/summarize", []),
        ("/rag-api", "/", []),
        ("/rag-api/api/v1/chat/query", "/api/v1/chat/query", []),
        ("/rag-api/api/v1/index/reconcile?dry=1",
         "/api/v1/index/reconcile?dry=1", []),
        ("/rag-api/api/v1/index/rebuild", "/api/v1/index/rebuild", []),
        ("/rag-api/api/v1/chat/query?next=/api/v1/index/rebuild",
         "/api/v1/chat/query?next=/api/v1/index/rebuild", []),
        ("/rag-api/api/v1/admin/../chat/query", "/api/v1/chat/query", []),
        ("/rag-api/api/v1/%61dmin/index/rebuild", "/api/v1/admin/index/rebuild", []),
    ]
    for path, forwarded, keys in cases:
        supplies = (None,) if (
            path.startswith("/rag-api/api/v1/index/")
        ) else (None, "browser-supplied")
        for supplied in supplies:
            headers = {"Content-Type": "application/json"}
            if supplied:
                headers["X-API-Key"] = supplied
            status, _, body = fetch("http://ui-probe" + path, "POST",
                                    b'{"text":"exact body + unicode \\u00e9"}', headers)
            data = json.loads(body)
            assert status == 200, (path, status, body)
            assert data == {
                "path": forwarded, "method": "POST",
                "body": '{"text":"exact body + unicode \\u00e9"}', "admin_key": keys,
            }, (path, data)
    for method in ("GET", "PUT", "PATCH", "DELETE", "OPTIONS"):
        status, _, body = fetch("http://ui-probe/api/v1/notes?status=422",
                                method, b"unchanged")
        data = json.loads(body)
        assert status == 422 and data["method"] == method and data["body"] == "unchanged", data
    for status in (201, 404, 503):
        result, _, body = fetch(f"http://ui-probe/rag-api/api/v1/chat/query?status={status}")
        assert result == status and json.loads(body)["admin_key"] == [], (result, body)
    assert fetch("http://ui-probe/rag-api/api/v1/chat/query?status=204", "DELETE")[0] == 204
    print("PASS: proxy paths, query strings, methods, bodies, statuses and API-key header isolation",
          flush=True)


def check_rate_limits():
    chat = "http://ui-probe/rag-api/api/v1/chat/query"
    payload = b'{"question":"test"}'

    oversized = fetch(
        chat,
        "POST",
        b"x" * (256 * 1024 + 1),
        {"Content-Type": "application/json"},
    )[0]
    assert oversized == 413, oversized

    with ThreadPoolExecutor(max_workers=3) as pool:
        concurrent = list(pool.map(
            lambda _: fetch(chat + "?hold=1", "POST", payload,
                            {"Content-Type": "application/json"})[0],
            range(3),
        ))
    assert concurrent.count(200) == 2 and concurrent.count(429) == 1, concurrent

    chat_statuses = [
        fetch(chat, "POST", payload, {"Content-Type": "application/json"})[0]
        for _ in range(30)
    ]
    assert 200 in chat_statuses and 429 in chat_statuses, chat_statuses

    summarize = "http://ui-probe/api/v1/notes/1/summarize"
    summarize_statuses = [
        fetch(summarize, "POST", b"", {})[0]
        for _ in range(12)
    ]
    assert 200 in summarize_statuses and 429 in summarize_statuses, summarize_statuses

    for operation in ("reconcile", "rebuild"):
        status = fetch(
            f"http://ui-probe/rag-api/api/v1/index/{operation}",
            "POST",
            b"",
            {},
        )[0]
        assert status == 429, (operation, status)
    print("PASS: per-IP rates, global model concurrency/index rates and request-size cap",
          flush=True)


def check_real_backends(request, eventually):
    notes = "http://ui/api/v1/notes"
    rag = "http://ui/rag-api/api/v1"
    assert request(notes) == []
    assert request(rag + "/health")["status"] == "ok"
    # Public index actions work directly and through nginx without credentials.
    request("http://ms2:8000/api/v1/admin/index/reconcile", "POST", expected=404)
    note = request(notes, "POST", {"title": "UI proxy", "content": "Proxy access is indigo-2718."},
                   expected=201)
    note_url = notes + "/" + str(note["id"])
    try:
        assert note["summary"] is None and "tags" not in note, note
        request(note_url + "/ai-enrich", "POST", expected=404)
        summarized = request(note_url + "/summarize", "POST")
        assert summarized["summary"] == "This note records access details.", summarized
        assert summarized["sourceHash"] == note["sourceHash"], summarized
        assert request(note_url)["summary"] == summarized["summary"]
        updated = request(note_url, "PUT",
                          {"title": "UI proxy revised", "content": "Proxy access is indigo-3141."})
        assert updated["summary"] is None, updated
        assert request(note_url)["sourceHash"] == updated["sourceHash"]

        def indexed():
            result = request(rag + "/chat/query", "POST", {"question": "What is proxy access?"})
            assert "indigo-3141" in result["answer"] and result["sources"], result
            assert result["sources"][0]["source_hash"] == updated["sourceHash"], result
            return True

        eventually("UI proxy CRUD and event-driven chat", indexed)
    finally:
        request(note_url, "DELETE", expected=204)
    request(note_url, expected=404)
    request(rag + "/chat/query", "POST", {"question": ""}, expected=422)
    # Run manual index actions only after the event-driven lifecycle has passed.
    for action in ("reconcile", "rebuild"):
        result = request(rag + "/index/" + action, "POST")
        assert isinstance(result, dict), result
    print("PASS: real MS1/MS2 via UI and public index actions", flush=True)


def run(request, eventually):
    eventually("UI static readiness", check_static)
    eventually("UI probe readiness", lambda: fetch("http://ui-probe/api")[0] == 200)
    check_proxy()
    check_rate_limits()
    check_real_backends(request, eventually)
