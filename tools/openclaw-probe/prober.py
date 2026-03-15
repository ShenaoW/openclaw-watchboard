from __future__ import annotations

import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


def fetch_url(url: str, timeout: int) -> tuple[str, str | None]:
    request = urllib.request.Request(url, headers={"User-Agent": "openclaw-probe/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return str(response.status), body
    except urllib.error.HTTPError as error:
        try:
            body = error.read().decode("utf-8", errors="replace")
        except Exception:
            body = None
        return str(error.code), body
    except urllib.error.URLError as error:
        reason = str(error.reason).lower()
        if "timed out" in reason or "timeout" in reason:
            return "timeout", None
        if "refused" in reason:
            return "refused", None
        return "err", None
    except Exception:
        return "err", None


def probe_instance(ip_port: str, timeout: int) -> dict[str, Any]:
    result = {
        "ip_port": ip_port,
        "statuses": {
            "health": "",
            "__openclaw_control-ui-config.json": "",
        },
        "config_payload": None,
        "server_version": "",
        "is_active": False,
        "is_openclaw": False,
    }

    endpoints = [
        ("health", "/health"),
        ("__openclaw_control-ui-config.json", "/__openclaw/control-ui-config.json"),
    ]

    for key, path in endpoints:
        status, body = fetch_url(f"http://{ip_port}{path}", timeout)
        result["statuses"][key] = status
        if key == "health" and status == "200":
            result["is_active"] = True

        if key == "__openclaw_control-ui-config.json" and status == "200" and body:
            try:
                payload = json.loads(body)
                result["config_payload"] = payload
                server_version = str(payload.get("serverVersion") or "").strip()
                if server_version:
                    result["server_version"] = server_version
                result["is_openclaw"] = True
            except Exception:
                result["config_payload"] = body

    return result


def probe_many(ip_ports: list[str], concurrency: int, timeout: int) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    if not ip_ports:
        return results

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        future_map = {executor.submit(probe_instance, ip_port, timeout): ip_port for ip_port in ip_ports}
        for future in as_completed(future_map):
            ip_port = future_map[future]
            results[ip_port] = future.result()
    return results
