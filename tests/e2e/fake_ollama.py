"""Ollama HTTP contract fake, not a model/relevance evaluation."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def respond(path, payload):
    if path == "/api/embed":
        texts = payload["input"]
        if isinstance(texts, str):
            texts = [texts]
        if not texts or not all(isinstance(text, str) and text for text in texts):
            raise ValueError("Expected nonempty embedding input")
        # Same unit vector for all text: retrieval is deterministic with our single note.
        return {"embeddings": [[1.0, 0.0, 0.0] for _ in texts]}
    if path == "/api/chat":
        if payload["stream"] is not False:
            raise ValueError("Only non-streaming chat is supported")
        message = payload["messages"][-1]["content"]
        if message.startswith("Create a short summary of this note.\n"):
            return {
                "model": payload["model"],
                "message": {"role": "assistant", "content": "This note records access details."},
                "done": True,
                "done_reason": "stop",
                # Spring AI only exposes finish_reason when usage counts are present.
                "prompt_eval_count": 10,
                "eval_count": 6,
            }
        context = message.split("NOTES:\n", 1)[1].rsplit("\n\nQUESTION:", 1)[0]
        if not context.strip():
            raise ValueError("Missing context")
        # Echo only retrieved context, never the question or canned lifecycle answers.
        # A stale chunk therefore cannot be hidden behind an abstaining model answer.
        return {"message": {"role": "assistant", "content": context}, "done": True}
    raise ValueError(f"Unsupported Ollama endpoint: {path}")


class Handler(BaseHTTPRequestHandler):
    def read_body(self):
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            chunks = []
            while True:
                size = int(self.rfile.readline().split(b";", 1)[0], 16)
                if size == 0:
                    while self.rfile.readline() not in (b"\r\n", b""):
                        pass
                    return b"".join(chunks)
                chunks.append(self.rfile.read(size))
                if self.rfile.read(2) != b"\r\n":
                    raise ValueError("Invalid chunk terminator")
        return self.rfile.read(int(self.headers["Content-Length"]))

    def do_POST(self):
        try:
            payload = json.loads(self.read_body())
            data = respond(self.path, payload)
            status = 200
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            self.log_error("Invalid fake Ollama request: %s", exc)
            data, status = {"error": str(exc)}, 400
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 11434), Handler).serve_forever()
