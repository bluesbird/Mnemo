"""Real broker outage/restart recovery; never repairs the index during assertions."""

import json
import subprocess
import time


def run(command, env):
    def compose(*args):
        return subprocess.run(command + list(args), env=env, check=True,
                              capture_output=True, text=True, errors="replace", timeout=45).stdout.strip()

    def sql(query):
        return compose("exec", "-T", "db", "psql", "-U", "e2e", "-d", "mnemo_e2e", "-At", "-c", query)

    def api(code):
        script = """
import json, urllib.request
from app.core.config import get_settings
from app.persistence.index_store import IndexStore
base = 'http://knowledge-service:8080/api/v1'
def request(path, method='GET', payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(base + path, data=data, method=method, headers={
        'Content-Type': 'application/json',
        'X-Mnemo-Reset-Key': 'e2e-reset-key-that-is-long-enough-for-test',
    })
    with urllib.request.urlopen(req, timeout=5) as response:
        body = response.read()
        return json.loads(body) if body else None
""" + code
        return compose("exec", "-T", "rag-service", "python", "-c", script)

    def eventually(label, probe, timeout=180):
        deadline = time.monotonic() + timeout
        last = "not attempted"
        while time.monotonic() < deadline:
            try:
                probe()
                print("PASS: " + label, flush=True)
                return
            except (AssertionError, subprocess.CalledProcessError) as exc:
                last = str(exc)
                if isinstance(exc, subprocess.CalledProcessError):
                    last += ": " + (exc.stderr or "")[-1500:]
            time.sleep(1)
        raise AssertionError(label + "; last observation: " + last)

    def pending_empty():
        assert sql("SELECT count(*) FROM note_outbox") == "0"

    def index_matches():
        api("""
notes = request('/notes')
expected = {str(note['id']): note['sourceHash'] for note in notes}
settings = get_settings()
metadata = IndexStore(settings).collection().get(include=['metadatas'])['metadatas']
assert {item['note_id'] for item in metadata} == set(expected)
assert all(item['source_hash'] == expected[item['note_id']]
           and item['indexing_version'] == settings.indexing_version for item in metadata)
""")

    def broker_drained():
        api("""
import base64
auth = 'Basic ' + base64.b64encode(b'e2e:e2e-only').decode()
for name in ('rag.note-events', 'rag.note-events.dlq'):
    req = urllib.request.Request('http://rabbitmq:15672/api/queues/%2F/' + name,
                                 headers={'Authorization': auth})
    with urllib.request.urlopen(req, timeout=5) as response:
        queue = json.load(response)
    assert queue['messages'] == 0, queue
    if name == 'rag.note-events':
        assert queue['consumers'] == 1, queue
""")

    def recovered(label):
        eventually(label + ": outbox drained", pending_empty)
        eventually(label + ": index matches Knowledge service (no reconcile/rebuild)", index_matches)
        eventually(label + ": consumer acknowledged, no dead letters", broker_drained)

    def ready():
        api("assert isinstance(request('/notes'), list)")

    recovered("initial reset event")
    fixtures = json.loads(api("""
first = request('/notes', 'POST', {'title': 'Recovery update', 'content': 'Old content'})
second = request('/notes', 'POST', {'title': 'Recovery delete', 'content': 'To be removed'})
print(json.dumps([first['id'], second['id']]))
"""))
    recovered("outage fixtures")
    compose("stop", "rabbitmq")
    api(f"""
request('/notes/{fixtures[0]}', 'PUT', {{'title': 'Recovery updated', 'content': 'New committed content'}})
request('/notes/{fixtures[1]}', 'DELETE')
request('/notes', 'POST', {{'title': 'Recovery create', 'content': 'Created while broker down'}})
""")
    pending = sql("SELECT event_id FROM note_outbox ORDER BY event_id")
    assert len(pending.splitlines()) == 3, pending
    assert sql("SELECT string_agg(event_type, ',' ORDER BY event_type) FROM note_outbox") == (
        "NoteCreated,NoteDeleted,NoteUpdated")
    compose("restart", "knowledge-service")
    eventually("Knowledge service restarts while broker unavailable", ready)
    assert sql("SELECT event_id FROM note_outbox ORDER BY event_id") == pending
    compose("start", "rabbitmq")
    recovered("create/update/delete after broker outage and Knowledge service restart")

    # Check a reset with an older event still pending; reset must not clear the outbox.
    compose("stop", "rabbitmq")
    api("request('/notes', 'POST', {'title': 'Pending before reset', 'content': 'Disposable'})")
    pending = sql("SELECT event_id FROM note_outbox")
    api("""
reset = request('/admin/reset-database', 'POST')
assert reset == {'status': 'reset', 'restoredNoteCount': 10, 'indexRebuild': 'queued'}, reset
assert len(request('/notes')) == 10
""")
    assert sql("SELECT count(*) FROM note_outbox") == "2"
    assert pending in sql("SELECT event_id FROM note_outbox")
    assert sql("SELECT count(*) FROM note_outbox WHERE note_id IS NULL "
               "AND event_type='IndexRebuildRequested'") == "1"
    compose("restart", "knowledge-service")
    eventually("reset survives Knowledge service restart with broker down", ready)
    assert sql("SELECT count(*) FROM note_outbox") == "2"
    compose("start", "rabbitmq")
    recovered("reset after broker outage and Knowledge service restart")
    print("PASS: durable outbox recovery, including reset and retained earlier events", flush=True)
