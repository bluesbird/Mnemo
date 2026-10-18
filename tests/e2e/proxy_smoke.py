"""Wire-level checks against nginx, plus a real-backend UI lifecycle."""

import json
import re
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
        ("/api/v1/notes?q=a%20b&tag=x", "/api/v1/notes?q=a%20b&tag=x", []),
        ("/api/v1/index/rebuild", "/api/v1/index/rebuild", []),
        ("/rag-api", "/", []),
        ("/rag-api/api/v1/chat/query", "/api/v1/chat/query", []),
        ("/rag-api/api/v1/index/reconcile?dry=1",
         "/api/v1/index/reconcile?dry=1", []),
        ("/rag-api/api/v1/index/rebuild", "/api/v1/index/rebuild", []),
        ("/rag-api/api/v1/admin", "/api/v1/admin", []),
        ("/rag-api/api/v1/administrator/test", "/api/v1/administrator/test", []),
        ("/rag-api/api/v1/chat/query?next=/api/v1/index/rebuild",
         "/api/v1/chat/query?next=/api/v1/index/rebuild", []),
        ("/rag-api/api/v1/admin/../chat/query", "/api/v1/chat/query", []),
        ("/rag-api/api/v1/%61dmin/index/rebuild", "/api/v1/admin/index/rebuild", []),
        ("/rag-api/api/v1/chat/../admin/index/rebuild", "/api/v1/admin/index/rebuild", []),
        ("/rag-api/api/v1/Admin/index/rebuild", "/api/v1/Admin/index/rebuild", []),
    ]
    for path, forwarded, keys in cases:
        for supplied in (None, "browser-supplied"):
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
    for status in (201, 400, 401, 403, 404, 500, 503):
        result, _, body = fetch(f"http://ui-probe/rag-api/api/v1/chat/query?status={status}")
        assert result == status and json.loads(body)["admin_key"] == [], (result, body)
    assert fetch("http://ui-probe/rag-api/api/v1/chat/query?status=204", "DELETE")[0] == 204
    print("PASS: proxy paths, query strings, methods, bodies, statuses and API-key header isolation",
          flush=True)


def check_real_backends(request, eventually):
    notes = "http://ui/api/v1/notes"
    rag = "http://ui/rag-api/api/v1"
    assert request(notes) == []
    assert request(rag + "/health")["status"] == "ok"
    # Public index actions work directly and through nginx without credentials.
    request("http://ms2:8000/api/v1/admin/index/reconcile", "POST", expected=404)
    request("http://ms2:8000/api/v1/index/reconcile", "POST")
    note = request(notes, "POST", {"title": "UI proxy", "content": "Proxy access is indigo-2718."},
                   expected=201)
    note_url = notes + "/" + str(note["id"])
    try:
        updated = request(note_url, "PUT",
                          {"title": "UI proxy revised", "content": "Proxy access is indigo-3141."})
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
    check_real_backends(request, eventually)
