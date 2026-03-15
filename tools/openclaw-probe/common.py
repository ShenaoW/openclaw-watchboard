from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
from typing import Any

from constants import TODAY


def log(message: str) -> None:
    print(f"[openclaw-probe] {message}")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return (reader.fieldnames or [], list(reader))


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def parse_existing_date(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return TODAY
    for fmt in ("%d/%m/%Y, %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return dt.datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    if len(text) >= 10:
        return text[:10]
    return TODAY


def country_code_from_name(country_name: str) -> str:
    mapping = {
        "china": "CN",
        "中国": "CN",
        "hong kong": "HK",
        "香港": "HK",
        "taiwan": "TW",
        "台湾": "TW",
        "macao": "MO",
        "macau": "MO",
        "澳门": "MO",
    }
    return mapping.get((country_name or "").strip().lower(), "")


def build_ip_port(row: dict[str, str]) -> str:
    ip = (row.get("ip") or "").strip()
    port = (row.get("port") or "").strip()
    if not ip:
        return ""
    return f"{ip}:{port}" if port else ip


def split_ip_port(ip_port: str) -> tuple[str, int]:
    if ":" not in ip_port:
        return ip_port, 0
    ip, port_text = ip_port.rsplit(":", 1)
    return ip, int(port_text) if port_text.isdigit() else 0
