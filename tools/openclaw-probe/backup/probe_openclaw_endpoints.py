#!/usr/bin/env python3
"""Probe likely OpenClaw HTTP and WebSocket endpoints on a target host.

This is a lightweight ingress probe. It does not authenticate and it does not
attempt destructive actions. The goal is to answer:

- which endpoints appear present
- which endpoints are publicly reachable
- which endpoints look auth-gated
- whether a reverse proxy is failing before the app

Examples:
  python3 scripts/probe_openclaw_endpoints.py 8.216.33.248 18789
  python3 scripts/probe_openclaw_endpoints.py gateway.example.com 443 --tls
  python3 scripts/probe_openclaw_endpoints.py 1.2.3.4 18789 --json
"""

from __future__ import annotations

import argparse
import base64
import http.client
import json
import os
import socket
import ssl
import sys
import textwrap
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlencode


DEFAULT_TIMEOUT = 5.0


@dataclass
class ProbeSpec:
    name: str
    kind: str
    method: str
    path: str
    body: bytes | None = None
    headers: dict[str, str] | None = None
    note: str | None = None


@dataclass
class ProbeResult:
    name: str
    kind: str
    method: str
    path: str
    status: int | None
    category: str
    reachable: bool
    summary: str
    content_type: str | None
    location: str | None
    body_preview: str | None
    error: str | None
    note: str | None


def build_default_probes() -> list[ProbeSpec]:
    json_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    return [
        ProbeSpec("health", "http", "GET", "/health", note="Core liveness probe"),
        ProbeSpec("healthz", "http", "GET", "/healthz", note="Core liveness probe alias"),
        ProbeSpec("ready", "http", "GET", "/ready", note="Core readiness probe"),
        ProbeSpec("readyz", "http", "GET", "/readyz", note="Core readiness probe alias"),
        ProbeSpec(
            "control-ui-config",
            "http",
            "GET",
            "/__openclaw/control-ui-config.json",
            note="Public Control UI bootstrap config when Control UI is enabled",
        ),
        ProbeSpec(
            "control-ui-root",
            "http",
            "GET",
            "/",
            note="Default Control UI mount when no basePath is configured",
        ),
        ProbeSpec(
            "control-ui-ui-path",
            "http",
            "GET",
            "/ui",
            note="Usually 404 when UI is root-mounted",
        ),
        ProbeSpec(
            "avatar-meta-main",
            "http",
            "GET",
            "/avatar/main?meta=1",
            note="Public Control UI avatar metadata if agent 'main' exists",
        ),
        ProbeSpec(
            "tools-invoke",
            "http",
            "POST",
            "/tools/invoke",
            body=b"{}",
            headers=json_headers,
            note="Should be gateway-auth protected",
        ),
        ProbeSpec(
            "openai-chat-completions",
            "http",
            "POST",
            "/v1/chat/completions",
            body=json.dumps(
                {"model": "openclaw", "messages": [{"role": "user", "content": "ping"}]}
            ).encode("utf-8"),
            headers=json_headers,
            note="Optional endpoint; disabled by default and auth-protected when enabled",
        ),
        ProbeSpec(
            "openresponses",
            "http",
            "POST",
            "/v1/responses",
            body=json.dumps({"model": "openclaw", "input": "ping"}).encode("utf-8"),
            headers=json_headers,
            note="Optional endpoint; disabled by default and auth-protected when enabled",
        ),
        ProbeSpec(
            "hooks-default-wake",
            "http",
            "POST",
            "/hooks/wake",
            body=json.dumps({"text": "ping"}).encode("utf-8"),
            headers=json_headers,
            note="Requires separate hooks token when hooks.enabled=true",
        ),
        ProbeSpec(
            "mattermost-command-default",
            "http",
            "GET",
            "/api/channels/mattermost/command",
            note="Mattermost command callback path",
        ),
        ProbeSpec(
            "canvas-a2ui",
            "http",
            "GET",
            "/__openclaw__/a2ui",
            note="Canvas A2UI path; usually auth-protected off-loopback",
        ),
        ProbeSpec(
            "canvas-http",
            "http",
            "GET",
            "/__openclaw__/canvas",
            note="Canvas host path; usually auth-protected off-loopback",
        ),
        ProbeSpec(
            "canvas-ws-http-path",
            "http",
            "GET",
            "/__openclaw__/ws",
            note="Canvas WebSocket path over plain HTTP request",
        ),
        ProbeSpec(
            "gateway-ws-root",
            "ws",
            "GET",
            "/",
            note="OpenClaw control-plane WebSocket commonly upgrades on /",
        ),
        ProbeSpec(
            "canvas-ws",
            "ws",
            "GET",
            "/__openclaw__/ws",
            note="Canvas WebSocket path",
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe likely OpenClaw endpoints on a target host and port."
    )
    parser.add_argument("host", help="Target host or IP")
    parser.add_argument("port", type=int, help="Target TCP port")
    parser.add_argument(
        "--tls",
        action="store_true",
        help="Use HTTPS/WSS instead of HTTP/WS",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Per-request timeout in seconds. Default: {DEFAULT_TIMEOUT}",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a text table",
    )
    parser.add_argument(
        "--extra-path",
        action="append",
        default=[],
        help="Extra GET path to probe. Can be passed multiple times.",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification for HTTPS/WSS probes.",
    )
    return parser.parse_args()


def make_tls_context(insecure: bool) -> ssl.SSLContext:
    if insecure:
        return ssl._create_unverified_context()
    return ssl.create_default_context()


def request_http(
    host: str,
    port: int,
    tls: bool,
    timeout: float,
    insecure: bool,
    spec: ProbeSpec,
) -> ProbeResult:
    headers = {"User-Agent": "openclaw-endpoint-probe/1.0", "Accept": "*/*"}
    if spec.headers:
        headers.update(spec.headers)
    body = spec.body
    if body is not None and "Content-Length" not in headers:
        headers["Content-Length"] = str(len(body))

    conn: http.client.HTTPConnection | http.client.HTTPSConnection
    try:
        if tls:
            conn = http.client.HTTPSConnection(
                host,
                port,
                timeout=timeout,
                context=make_tls_context(insecure),
            )
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request(spec.method, spec.path, body=body, headers=headers)
        resp = conn.getresponse()
        raw = resp.read(1024)
        content_type = resp.getheader("Content-Type")
        location = resp.getheader("Location")
        body_preview = raw.decode("utf-8", errors="replace").strip() or None
        summary = summarize_http_response(spec, resp.status, content_type, location, body_preview)
        category = categorize_http_response(spec, resp.status, body_preview)
        return ProbeResult(
            name=spec.name,
            kind=spec.kind,
            method=spec.method,
            path=spec.path,
            status=resp.status,
            category=category,
            reachable=True,
            summary=summary,
            content_type=content_type,
            location=location,
            body_preview=body_preview,
            error=None,
            note=spec.note,
        )
    except Exception as exc:  # pragma: no cover - network failure path
        return ProbeResult(
            name=spec.name,
            kind=spec.kind,
            method=spec.method,
            path=spec.path,
            status=None,
            category="network_error",
            reachable=False,
            summary=f"Network error: {exc}",
            content_type=None,
            location=None,
            body_preview=None,
            error=str(exc),
            note=spec.note,
        )
    finally:
        try:
            conn.close()  # type: ignore[misc]
        except Exception:
            pass


def request_ws(
    host: str,
    port: int,
    tls: bool,
    timeout: float,
    insecure: bool,
    spec: ProbeSpec,
) -> ProbeResult:
    sock: socket.socket | ssl.SSLSocket | None = None
    try:
        raw_sock = socket.create_connection((host, port), timeout=timeout)
        raw_sock.settimeout(timeout)
        if tls:
            context = make_tls_context(insecure)
            sock = context.wrap_socket(raw_sock, server_hostname=host)
        else:
            sock = raw_sock

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        origin_scheme = "https" if tls else "http"
        host_header = f"{host}:{port}"
        request = (
            f"GET {spec.path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Origin: {origin_scheme}://{host_header}\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "User-Agent: openclaw-endpoint-probe/1.0\r\n"
            "\r\n"
        )
        sock.sendall(request.encode("ascii"))

        response = recv_headers(sock)
        status, headers = parse_http_response_head(response)
        summary = summarize_ws_response(spec, status, headers)
        category = categorize_ws_response(spec, status)
        return ProbeResult(
            name=spec.name,
            kind=spec.kind,
            method="GET",
            path=spec.path,
            status=status,
            category=category,
            reachable=True,
            summary=summary,
            content_type=headers.get("content-type"),
            location=headers.get("location"),
            body_preview=None,
            error=None,
            note=spec.note,
        )
    except Exception as exc:  # pragma: no cover - network failure path
        return ProbeResult(
            name=spec.name,
            kind=spec.kind,
            method="GET",
            path=spec.path,
            status=None,
            category="network_error",
            reachable=False,
            summary=f"Network error: {exc}",
            content_type=None,
            location=None,
            body_preview=None,
            error=str(exc),
            note=spec.note,
        )
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass


def recv_headers(sock: socket.socket | ssl.SSLSocket) -> bytes:
    chunks = []
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        chunks.append(chunk)
        data = b"".join(chunks)
        if len(data) > 65536:
            break
    return data


def parse_http_response_head(data: bytes) -> tuple[int | None, dict[str, str]]:
    text = data.decode("iso-8859-1", errors="replace")
    head = text.split("\r\n\r\n", 1)[0]
    lines = head.split("\r\n")
    if not lines:
        return None, {}
    status = None
    parts = lines[0].split(" ", 2)
    if len(parts) >= 2 and parts[1].isdigit():
        status = int(parts[1])
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    return status, headers


def categorize_http_response(spec: ProbeSpec, status: int, body_preview: str | None) -> str:
    if 200 <= status < 300:
        if looks_like_control_ui_html(body_preview) and spec.path != "/":
            return "spa_fallback_public"
        if spec.name == "control-ui-config":
            return "public_config"
        return "public"
    if status == 101:
        return "websocket_open"
    if status in (301, 302, 307, 308):
        return "redirect"
    if status in (401, 403):
        return "auth_gated"
    if status == 404:
        return "absent_or_disabled"
    if status == 405:
        return "exists_method_gated"
    if status == 400:
        lowered = (body_preview or "").lower()
        if "unauthorized" in lowered or "auth" in lowered:
            return "auth_gated"
        return "exists_invalid_request_or_proxy"
    if status == 408:
        return "timeout_guard"
    if status == 413:
        return "body_limit_guard"
    if status == 429:
        return "rate_limited"
    if status == 502:
        return "proxy_bad_gateway"
    if status == 503:
        return "server_unavailable"
    if status >= 500:
        return "server_error"
    return "other"


def categorize_ws_response(spec: ProbeSpec, status: int | None) -> str:
    if status == 101:
        return "websocket_open"
    if status in (401, 403):
        return "auth_gated"
    if status == 404:
        return "absent_or_disabled"
    if status == 429:
        return "rate_limited"
    if status == 502:
        return "proxy_bad_gateway"
    if status is None:
        return "invalid_response"
    if status >= 500:
        return "server_error"
    return "other"


def summarize_http_response(
    spec: ProbeSpec,
    status: int,
    content_type: str | None,
    location: str | None,
    body_preview: str | None,
) -> str:
    bits = [f"HTTP {status}"]
    if content_type:
        bits.append(content_type)
    if location:
        bits.append(f"Location={location}")
    if spec.name == "control-ui-config" and body_preview:
        try:
            data = json.loads(body_preview)
            assistant = data.get("assistantName")
            version = data.get("serverVersion")
            if assistant:
                bits.append(f"assistant={assistant}")
            if version:
                bits.append(f"serverVersion={version}")
        except Exception:
            pass
    elif looks_like_control_ui_html(body_preview):
        bits.append("looks like Control UI HTML")
    return "; ".join(bits)


def summarize_ws_response(spec: ProbeSpec, status: int | None, headers: dict[str, str]) -> str:
    if status is None:
        return "Invalid HTTP response to WebSocket upgrade"
    upgrade = headers.get("upgrade")
    connection = headers.get("connection")
    extra = []
    if upgrade:
        extra.append(f"Upgrade={upgrade}")
    if connection:
        extra.append(f"Connection={connection}")
    tail = f"; {'; '.join(extra)}" if extra else ""
    return f"WS upgrade response HTTP {status}{tail}"


def add_extra_probes(probes: list[ProbeSpec], extra_paths: list[str]) -> None:
    for idx, raw in enumerate(extra_paths, start=1):
        path = raw if raw.startswith("/") else f"/{raw}"
        probes.append(
            ProbeSpec(
                name=f"extra-{idx}",
                kind="http",
                method="GET",
                path=path,
                note="User-supplied extra path",
            )
        )


def looks_like_control_ui_html(body_preview: str | None) -> bool:
    if not body_preview:
        return False
    lowered = body_preview.lower()
    return "<!doctype html" in lowered and "openclaw control" in lowered


def print_text_report(host: str, port: int, tls: bool, results: list[ProbeResult]) -> None:
    scheme = "https/wss" if tls else "http/ws"
    print(f"Target: {host}:{port} ({scheme})")
    print()
    print(f"{'NAME':24} {'METHOD':6} {'STATUS':6} {'CATEGORY':28} PATH")
    print("-" * 96)
    for result in results:
        status = "-" if result.status is None else str(result.status)
        print(
            f"{result.name[:24]:24} {result.method:6} {status:6} "
            f"{result.category[:28]:28} {result.path}"
        )
    print()
    for result in results:
        print(f"[{result.name}]")
        print(f"  path: {result.path}")
        print(f"  category: {result.category}")
        print(f"  summary: {result.summary}")
        if result.note:
            print(f"  note: {result.note}")
        if result.body_preview:
            preview = textwrap.shorten(result.body_preview.replace("\n", " "), width=180)
            print(f"  body: {preview}")
        if result.error:
            print(f"  error: {result.error}")
        print()


def main() -> int:
    args = parse_args()
    probes = build_default_probes()
    add_extra_probes(probes, args.extra_path)

    results: list[ProbeResult] = []
    for spec in probes:
        if spec.kind == "ws":
            result = request_ws(args.host, args.port, args.tls, args.timeout, args.insecure, spec)
        else:
            result = request_http(
                args.host, args.port, args.tls, args.timeout, args.insecure, spec
            )
        results.append(result)

    if args.json:
        payload = {
            "target": {
                "host": args.host,
                "port": args.port,
                "tls": args.tls,
                "timeout": args.timeout,
            },
            "results": [asdict(item) for item in results],
        }
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print_text_report(args.host, args.port, args.tls, results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
