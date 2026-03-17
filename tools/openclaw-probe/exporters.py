from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from common import country_code_from_name, normalize_location_fields, read_csv_rows, write_csv_rows
from constants import ALIVE_FIELDS, CN_FIELDS, DEDUPED_FIELDS, FOFA_FIELDS, TODAY
from repository import load_probe_instances


def export_deduped_csv(conn: sqlite3.Connection, deduped_csv: Path) -> int:
    existing_header, existing_rows = read_csv_rows(deduped_csv)
    header = existing_header or list(DEDUPED_FIELDS)
    row_map = {(row.get("ip_port") or "").strip(): row for row in existing_rows if (row.get("ip_port") or "").strip()}

    for item in load_probe_instances(conn):
        row = row_map.get(item["ip_port"], {field: "" for field in header})
        country_name, _, _ = normalize_location_fields(item["country_name"] or "", item["region"] or "", item["city"] or "")
        row["ip_port"] = item["ip_port"]
        row["country"] = country_name or row.get("country") or ""
        row["is_active"] = "True" if item["is_active"] else "False"
        row["asn"] = item["asn"] or row.get("asn", "")
        row["asn_name"] = row.get("asn_name") or item["org"] or ""
        row["org"] = item["org"] or row.get("org", "")
        row["first_seen"] = item["first_seen_at"] or row.get("first_seen", "")
        row["last_seen"] = item["last_active_at"] or row.get("last_seen", "")
        row["asi_enriched_at"] = TODAY
        row_map[item["ip_port"]] = row

    merged_rows = [row_map[key] for key in sorted(row_map)]
    write_csv_rows(deduped_csv, header, merged_rows)
    return len(merged_rows)


def export_alive_files(
    conn: sqlite3.Connection,
    daily_probe_results: dict[str, dict[str, Any]],
    alive_csv: Path,
    configs_json: Path,
) -> tuple[int, int]:
    alive_rows: list[dict[str, Any]] = []
    config_map: dict[str, Any] = {}

    for item in load_probe_instances(conn):
        probe_result = daily_probe_results.get(item["ip_port"])
        if probe_result:
            statuses = probe_result["statuses"]
            if probe_result["config_payload"] is not None:
                config_map[item["ip_port"]] = probe_result["config_payload"]
        else:
            statuses = {
                "health": "200" if item["is_active"] else "",
                "__openclaw_control-ui-config.json": "200" if item["server_version"] else "",
            }
            if item["server_version"]:
                config_map[item["ip_port"]] = {"serverVersion": item["server_version"]}

        alive_rows.append(
            {
                "ip_port": item["ip_port"],
                "any_200": "true" if (probe_result["is_active"] if probe_result else item["is_active"]) else "false",
                "config_ok": "true" if statuses["__openclaw_control-ui-config.json"] == "200" else "false",
                "root": "",
                "health": statuses["health"],
                "healthz": "",
                "ready": "",
                "readyz": "",
                "avatar_main_meta_1": "",
                "__openclaw_control-ui-config.json": statuses["__openclaw_control-ui-config.json"],
            }
        )

    write_csv_rows(alive_csv, ALIVE_FIELDS, alive_rows)
    configs_json.parent.mkdir(parents=True, exist_ok=True)
    configs_json.write_text(json.dumps(config_map, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(alive_rows), len(config_map)


def export_cn_csv(conn: sqlite3.Connection, cn_csv: Path) -> int:
    rows: list[dict[str, Any]] = []
    for item in load_probe_instances(conn):
        country_name, region, city = normalize_location_fields(item["country_name"] or "", item["region"] or "", item["city"] or "")
        code = country_code_from_name(country_name)
        if code not in {"CN", "HK", "TW", "MO"}:
            continue

        rows.append(
            {
                "ip_port": item["ip_port"],
                "assistant_name": "",
                "country": country_name or "",
                "auth_required": "",
                "is_active": "True" if item["is_active"] else "False",
                "has_leaked_creds": "",
                "asn": item["asn"] or "",
                "asn_name": item["org"] or "",
                "org": item["org"] or "",
                "first_seen": item["first_seen_at"] or "",
                "last_seen": item["last_active_at"] or "",
                "asi_has_breach": "",
                "asi_has_threat_actor": "",
                "asi_threat_actors": "",
                "asi_cves": "",
                "asi_enriched_at": TODAY,
                "asi_domains": "",
                "physical_country": code,
                "region": region or "",
                "city": city or "",
            }
        )

    write_csv_rows(cn_csv, CN_FIELDS, rows)
    return len(rows)


def save_run_artifacts(run_dir: Path, fofa_rows: list[dict[str, str]], new_keys: list[str]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    write_csv_rows(run_dir / "fofa_openclaw_raw.csv", FOFA_FIELDS, fofa_rows)
    new_key_set = set(new_keys)
    new_raw_rows = [row for row in fofa_rows if f"{(row.get('ip') or '').strip()}:{(row.get('port') or '').strip()}".rstrip(":") in new_key_set]
    write_csv_rows(run_dir / "fofa_new_full_rows.csv", FOFA_FIELDS, new_raw_rows)
    write_csv_rows(run_dir / "fofa_new_ip_port.csv", ["ip_port"], [{"ip_port": key} for key in new_keys])
