from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from common import parse_existing_date, read_csv_rows, split_ip_port
from constants import TODAY


def open_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_probe_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS probe_instances (
            ip_port TEXT PRIMARY KEY,
            ip TEXT NOT NULL,
            port INTEGER NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_active_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL,
            country_name TEXT,
            region TEXT,
            city TEXT,
            asn TEXT,
            org TEXT,
            server_version TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS probe_daily_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL,
            ip_port TEXT NOT NULL,
            is_active INTEGER NOT NULL,
            server_version TEXT,
            UNIQUE(snapshot_date, ip_port)
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_probe_instances_active ON probe_instances(is_active)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_probe_snapshots_date ON probe_daily_snapshots(snapshot_date)")
    conn.commit()


def bootstrap_instances(
    conn: sqlite3.Connection,
    deduped_csv: Path,
    alive_csv: Path,
    configs_json: Path,
    cn_csv: Path,
) -> int:
    cursor = conn.cursor()
    _, deduped_rows = read_csv_rows(deduped_csv)
    if not deduped_rows:
        return 0

    _, alive_rows = read_csv_rows(alive_csv)
    alive_map = {(row.get("ip_port") or "").strip(): row for row in alive_rows if (row.get("ip_port") or "").strip()}
    config_map: dict[str, Any] = {}
    if configs_json.exists():
        config_map = json.loads(configs_json.read_text(encoding="utf-8"))
    _, cn_rows = read_csv_rows(cn_csv)
    cn_map = {(row.get("ip_port") or "").strip(): row for row in cn_rows if (row.get("ip_port") or "").strip()}

    inserted = 0
    for row in deduped_rows:
        ip_port = (row.get("ip_port") or "").strip()
        if not ip_port:
            continue
        if cursor.execute("SELECT 1 FROM probe_instances WHERE ip_port = ?", (ip_port,)).fetchone():
            continue

        ip, port = split_ip_port(ip_port)
        alive_row = alive_map.get(ip_port, {})
        config_payload = config_map.get(ip_port, {})
        cn_row = cn_map.get(ip_port, {})
        server_version = ""
        if isinstance(config_payload, dict):
            server_version = str(config_payload.get("serverVersion") or "").strip()

        is_active = 1 if (alive_row.get("health") or "").strip() == "200" else 0
        last_active_at = parse_existing_date(row.get("last_seen", "") or row.get("first_seen", "")) if is_active else ""
        first_seen_at = parse_existing_date(row.get("first_seen", ""))

        cursor.execute(
            """
            INSERT INTO probe_instances (
                ip_port, ip, port, first_seen_at, last_active_at, is_active, source,
                country_name, region, city, asn, org, server_version, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                ip_port,
                ip,
                port,
                first_seen_at,
                last_active_at or None,
                is_active,
                "legacy",
                (row.get("country") or "").strip(),
                (cn_row.get("region") or "").strip(),
                (cn_row.get("city") or "").strip(),
                (row.get("asn") or "").strip(),
                (row.get("org") or "").strip(),
                server_version or None,
            ),
        )
        inserted += 1

    conn.commit()
    return inserted


def load_probe_instances(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM probe_instances ORDER BY ip_port").fetchall()


def insert_new_instances(
    conn: sqlite3.Connection,
    fofa_rows: list[dict[str, str]],
    daily_probe_results: dict[str, dict[str, Any]],
) -> int:
    cursor = conn.cursor()
    existing_keys = {row["ip_port"] for row in load_probe_instances(conn)}
    inserted = 0

    for row in fofa_rows:
        ip_port = f"{(row.get('ip') or '').strip()}:{(row.get('port') or '').strip()}".rstrip(":")
        if not ip_port or ip_port in existing_keys:
            continue

        probe_result = daily_probe_results.get(ip_port)
        if not probe_result or not probe_result["is_openclaw"] or not probe_result["is_active"]:
            continue

        ip, port = split_ip_port(ip_port)
        cursor.execute(
            """
            INSERT INTO probe_instances (
                ip_port, ip, port, first_seen_at, last_active_at, is_active, source,
                country_name, region, city, asn, org, server_version, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                ip_port,
                ip,
                port,
                TODAY,
                TODAY,
                1,
                "fofa",
                (row.get("country_name") or "").strip(),
                (row.get("region") or "").strip(),
                (row.get("city") or "").strip(),
                (row.get("asn") or "").strip(),
                (row.get("org") or "").strip(),
                probe_result["server_version"] or None,
            ),
        )
        inserted += 1

    conn.commit()
    return inserted


def update_runtime_state(conn: sqlite3.Connection, daily_probe_results: dict[str, dict[str, Any]]) -> None:
    cursor = conn.cursor()
    for ip_port, probe_result in daily_probe_results.items():
        server_version = probe_result["server_version"] or None
        if probe_result["is_active"]:
            cursor.execute(
                """
                UPDATE probe_instances
                SET is_active = 1,
                    last_active_at = ?,
                    server_version = COALESCE(?, server_version),
                    updated_at = CURRENT_TIMESTAMP
                WHERE ip_port = ?
                """,
                (TODAY, server_version, ip_port),
            )
        else:
            cursor.execute(
                """
                UPDATE probe_instances
                SET is_active = 0,
                    server_version = COALESCE(?, server_version),
                    updated_at = CURRENT_TIMESTAMP
                WHERE ip_port = ?
                """,
                (server_version, ip_port),
            )
    conn.commit()


def upsert_daily_snapshots(conn: sqlite3.Connection) -> int:
    rows = load_probe_instances(conn)
    cursor = conn.cursor()
    for row in rows:
        cursor.execute(
            """
            INSERT INTO probe_daily_snapshots (snapshot_date, ip_port, is_active, server_version)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(snapshot_date, ip_port) DO UPDATE SET
                is_active = excluded.is_active,
                server_version = excluded.server_version
            """,
            (TODAY, row["ip_port"], int(row["is_active"]), row["server_version"]),
        )
    conn.commit()
    return len(rows)
