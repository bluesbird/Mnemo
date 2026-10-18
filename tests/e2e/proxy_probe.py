"""HTTP echo upstream used only to observe the production UI proxy on the wire."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import time
from urllib.parse import parse_qs, urlsplit


class Handler(BaseHTTPRequestHandler):
    def respond(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode()
        query = parse_qs(urlsplit(self.path).query)
        if query.get("hold") == ["1"]:
            time.sleep(1)
        status = int(query.get("status", ["200"])[0])
        data = json.dumps({
            "path": self.path,
            "method": self.command,
            "body": body,
            "admin_key": self.headers.get_all("X-API-Key", []),
        }).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = respond


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
