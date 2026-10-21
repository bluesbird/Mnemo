"""One isolated real-model sanity-check run; standard library only. No scoring."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTPUT = HERE / "responses.json"

# HTTP runs inside RAG service: no host ports, host dependencies, or development APIs.
HTTP = """
import json, sys, urllib.request, urllib.error
data = json.load(sys.stdin)
payload = data.get("payload")
request = urllib.request.Request(data["url"],
    data=None if payload is None else json.dumps(payload).encode(),
    headers=data.get("headers", {}), method=data["method"])
try:
    response = urllib.request.urlopen(request, timeout=150)
except urllib.error.HTTPError as error:
    response = error
body = response.read().decode()
try:
    body = json.loads(body)
except ValueError:
    pass
print(json.dumps({"http_status": response.code, "body": body}))
"""

INSPECT = """
import hashlib, json
from app.api.deps import get_index_store
from app.core.config import get_settings
from app.rag.chunker import NoteChunker
settings = get_settings()
chunker = NoteChunker(settings)
tokenizer = chunker._get_tokenizer()
page = get_index_store().collection().get(include=["documents", "metadatas"])
chunks = []
for doc, meta in zip(page["documents"], page["metadatas"]):
    chunks.append({"note_id": int(meta["note_id"]), "chunk_index": meta["chunk_index"],
                   "tokens": chunker._count_tokens(doc), "text": doc,
                   "source_hash": meta["source_hash"],
                   "indexing_version": meta["indexing_version"]})
settings_data = settings.model_dump()
for key in ("rabbitmq_password",):
    settings_data[key] = "[redacted]"
print(json.dumps({"settings": settings_data, "indexing_version": settings.indexing_version,
    "tokenizer_fallback": tokenizer is None,
    "tokenizer_sha256": hashlib.sha256(tokenizer.to_str().encode()).hexdigest()
                        if tokenizer else None,
    "chunks": sorted(chunks, key=lambda c: (c["note_id"], c["chunk_index"]))}))
"""


def command(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, text=True, encoding="utf-8",
                          errors="replace", timeout=kwargs.pop("timeout", 180), **kwargs)


def save(result):
    # Persist after each note and question, even if a later request fails.
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    if OUTPUT.exists():
        raise SystemExit("responses.json already exists; preserve the first run, do not overwrite it.")
    fixture_bytes = (HERE / "fixture.json").read_bytes()
    fixture = json.loads(fixture_bytes)
    project = "mnemo-eval-" + uuid.uuid4().hex[:12]
    scratch = HERE / ".run"
    scratch.mkdir(exist_ok=True)
    override = scratch / "override.json"
    # Reuse the E2E topology, never its fake Ollama. Selected services only.
    override.write_text(json.dumps({"services": {
        "rabbitmq": {"command": ["sh", "-c",
            "printf '%s' mnemo-evaluation-only-cookie > /var/lib/rabbitmq/.erlang.cookie; "
            "chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie; "
            "chmod 600 /var/lib/rabbitmq/.erlang.cookie; "
            "exec docker-entrypoint.sh rabbitmq-server"]},
        "knowledge-service": {"environment": {
            "SPRING_AI_OLLAMA_BASE_URL": "http://host.docker.internal:11434"},
            "extra_hosts": ["host.docker.internal:host-gateway"]},
        "rag-service": {"environment": {
            "RAG_OLLAMA_BASE_URL": "http://host.docker.internal:11434",
            "RAG_RABBITMQ_ENABLED": "false", "HF_HUB_OFFLINE": "0"},
            "extra_hosts": ["host.docker.internal:host-gateway"]}
    }}), encoding="utf-8")
    compose = ["docker", "compose", "--project-name", project, "--env-file",
               str(ROOT / "tests" / "e2e" / "e2e.env"), "--file",
               str(ROOT / "tests" / "e2e" / "compose.yaml"), "--file", str(override)]
    # Prevent caller Compose settings from selecting a development project.
    for key in list(os.environ):
        if key.startswith("COMPOSE_"):
            del os.environ[key]
    result = {
        "started_at": datetime.now(timezone.utc).isoformat(), "status": "running",
        "project": project, "commit": command(["git", "rev-parse", "HEAD"],
                                           capture_output=True).stdout.strip(),
        "dirty_state": command(["git", "status", "--short", "--untracked-files=all"],
                               capture_output=True).stdout.splitlines(),
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "notes": [], "questions": [], "errors": [],
        "ingestion": "Explicit reconcile; event consumer disabled to avoid concurrent ingestion.",
    }
    save(result)
    container = None

    def request(url, payload=None, headers=None):
        data = {"url": url, "method": "GET" if payload is None else "POST",
                "payload": payload, "headers": {"Content-Type": "application/json", **(headers or {})}}
        response = command(["docker", "exec", "-i", container, "python", "-c", HTTP],
                           input=json.dumps(data), capture_output=True)
        return json.loads(response.stdout)

    def success(response):
        if not 200 <= response["http_status"] < 300:
            raise RuntimeError(json.dumps(response))
        return response["body"]

    def ollama(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request("http://localhost:11434" + path, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=150) as response:
            return json.load(response)

    try:
        result["ollama_version"] = ollama("/api/version")
        result["models_before"] = ollama("/api/tags")
        available = {m["name"] for m in result["models_before"]["models"]}
        for model in ("qwen3-embedding:0.6b", "qwen3:4b"):
            if model not in available:
                raise RuntimeError(f"Required local model missing: {model}; no automatic downloads.")
        result["model_details"] = {
            model: ollama("/api/show", {"model": model})
            for model in ("qwen3-embedding:0.6b", "qwen3:4b")
        }
        save(result)
        with (scratch / "startup.log").open("w", encoding="utf-8") as log:
            command(compose + ["up", "-d", "--wait", "db", "rabbitmq"],
                    stdout=log, stderr=subprocess.STDOUT, timeout=180)
            command(compose + ["up", "-d", "--build", "--no-deps", "knowledge-service", "rag-service"],
                    stdout=log, stderr=subprocess.STDOUT, timeout=900)
        container = command(compose + ["ps", "-q", "rag-service"], capture_output=True).stdout.strip()
        last = None
        for _ in range(90):
            try:
                assert success(request("http://knowledge-service:8080/api/v1/notes")) == []
                assert success(request("http://localhost:8000/api/v1/health"))["status"] == "ok"
                break
            except (subprocess.SubprocessError, AssertionError, ValueError, RuntimeError) as exc:
                last = str(exc)
                time.sleep(2)
        else:
            raise RuntimeError(f"Isolated services not ready: {last}")
        result["containers"] = [json.loads(line) for line in command(
            compose + ["ps", "--format", "json"], capture_output=True).stdout.splitlines()]
        for note in fixture["notes"]:
            created = success(request("http://knowledge-service:8080/api/v1/notes",
                                      {"title": note["title"], "content": note["content"]}))
            result["notes"].append({"key": note["key"], "note_id": created["id"],
                                    "source_hash": created["sourceHash"]})
            save(result)
        result["reconcile"] = request("http://localhost:8000/api/v1/index/reconcile", {})
        success(result["reconcile"])
        result["index"] = json.loads(command(
            ["docker", "exec", container, "python", "-c", INSPECT],
            capture_output=True).stdout)
        for note, mapping in zip(fixture["notes"], result["notes"]):
            mapping["chunk_count"] = sum(c["note_id"] == mapping["note_id"]
                                         for c in result["index"]["chunks"])
            assert mapping["chunk_count"] > 0, mapping
            if note["length"] == "long":
                assert mapping["chunk_count"] > 1, mapping
        assert result["reconcile"]["body"]["total_knowledge_notes"] == 10
        save(result)
        # One warmup, not a scored question and not drawn from the answer key.
        result["warmup"] = ollama("/api/chat", {
            "model": "qwen3:4b", "stream": False, "think": False,
            "messages": [{"role": "user", "content": "Reply with Ready."}],
            "options": {"temperature": 0.1, "num_ctx": 4096}})
        save(result)
        key_by_id = {n["note_id"]: n["key"] for n in result["notes"]}
        for question in fixture["questions"]:
            entry = {"id": question["id"], "question": question["question"],
                     "started_at": datetime.now(timezone.utc).isoformat()}
            result["questions"].append(entry)
            save(result)
            start = time.monotonic()
            try:
                entry["response"] = request("http://localhost:8000/api/v1/chat/query",
                                           {"question": question["question"], "top_k": 4})
                body = success(entry["response"])
                entry["source_keys"] = [key_by_id[s["note_id"]] for s in body["sources"]]
                if not isinstance(body["answer"], str) or not body["answer"].strip():
                    raise RuntimeError("Empty or invalid answer")
            except (subprocess.SubprocessError, OSError, ValueError, KeyError, RuntimeError) as exc:
                entry["error"] = str(exc)
            entry["elapsed_seconds"] = round(time.monotonic() - start, 3)
            save(result)
            print(question["id"], entry.get("error", "saved"), flush=True)
        result["models_after"] = ollama("/api/tags")
        result["status"] = "completed_with_errors" if any(
            q.get("error") for q in result["questions"]) else "completed"
    except (subprocess.SubprocessError, OSError, AssertionError, ValueError, KeyError, RuntimeError) as exc:
        result["status"] = "blocked"
        result["errors"].append(str(exc))
        print(f"Blocked: {exc}", file=sys.stderr)
    finally:
        try:
            logs = command(compose + ["logs", "--no-color"], capture_output=True, timeout=30)
            (scratch / "services.log").write_text(logs.stdout + logs.stderr, encoding="utf-8")
        except (subprocess.SubprocessError, OSError) as exc:
            result["errors"].append(f"Log collection: {exc}")
        try:
            command(compose + ["down", "--volumes", "--remove-orphans", "--rmi", "local",
                               "--timeout", "10"], timeout=120)
            remaining = command(["docker", "ps", "-aq", "--filter",
                                 f"label=com.docker.compose.project={project}"],
                                capture_output=True).stdout.strip()
            volumes = command(["docker", "volume", "ls", "-q", "--filter",
                               f"label=com.docker.compose.project={project}"],
                              capture_output=True).stdout.strip()
            result["cleanup"] = {"containers_remaining": remaining, "volumes_remaining": volumes}
            assert not remaining and not volumes, result["cleanup"]
        except (subprocess.SubprocessError, OSError, AssertionError) as exc:
            result["errors"].append(f"Cleanup: {exc}")
        override.unlink(missing_ok=True)
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        save(result)
    return 0 if result["status"] == "completed" and not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
