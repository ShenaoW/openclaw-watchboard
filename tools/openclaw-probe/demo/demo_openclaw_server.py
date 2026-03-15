#!/usr/bin/env python3
"""Small local server that mimics a minimal OpenClaw instance for demos."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ROOT_HTML = """<!doctype html>
<html>
  <head><title>OpenClaw Control UI</title></head>
  <body>
    <h1>OpenClaw Control UI</h1>
  </body>
</html>
"""

CONFIG_PAYLOAD = {
    "assistantName": "demo-assistant",
    "serverVersion": "2.1.0",
    "mode": "demo",
}


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "OpenClawDemo/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            self._send_text(200, ROOT_HTML, "text/html; charset=utf-8")
            return
        if self.path in {"/health", "/healthz", "/ready", "/readyz"}:
            self._send_text(200, "ok", "text/plain; charset=utf-8")
            return
        if self.path == "/avatar/main?meta=1":
            self._send_json(200, {"id": "main", "kind": "avatar"})
            return
        if self.path == "/__openclaw/control-ui-config.json":
            self._send_json(200, CONFIG_PAYLOAD)
            return

        self._send_text(404, "not found", "text/plain; charset=utf-8")

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send_text(self, status: int, body: str, content_type: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, status: int, payload: dict) -> None:
        self._send_text(status, json.dumps(payload), "application/json; charset=utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small local OpenClaw demo server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", type=int, default=28789, help="Bind port.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    print(f"demo openclaw server listening on {args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
