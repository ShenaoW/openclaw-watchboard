#!/usr/bin/env python3
"""Build FOFA incremental targets and watchboard-compatible rows."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


WATCHBOARD_HEADER = [
    "ip_port",
    "assistant_name",
    "country",
    "auth_required",
    "is_active",
    "has_leaked_creds",
    "asn",
    "asn_name",
    "org",
    "first_seen",
    "last_seen",
    "asi_has_breach",
    "asi_has_threat_actor",
    "asi_threat_actors",
    "asi_cves",
    "asi_enriched_at",
    "asi_domains",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert FOFA raw CSV into incremental targets relative to current deduped watchboard data."
    )
    parser.add_argument("--fofa", required=True, type=Path, help="FOFA raw CSV path.")
    parser.add_argument("--deduped", required=True, type=Path, help="Current watchboard deduped CSV.")
    parser.add_argument("--out-dir", required=True, type=Path, help="Output directory.")
    return parser.parse_args()


def load_existing_keys(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            return set()
        first_column = fieldnames[0]
        return {(row.get(first_column) or "").strip() for row in reader if (row.get(first_column) or "").strip()}


def build_ip_port(row: dict[str, str]) -> str:
    ip = (row.get("ip") or "").strip()
    port = (row.get("port") or "").strip()
    if not ip:
        return ""
    if not port:
        return ip
    return f"{ip}:{port}"


def to_watchboard_row(row: dict[str, str], ip_port: str) -> dict[str, str]:
    country_name = (row.get("country_name") or "").strip()
    region = (row.get("region") or "").strip()
    city = (row.get("city") or "").strip()
    org = (row.get("org") or "").strip()
    asn = (row.get("asn") or "").strip()
    domain = (row.get("domain") or "").strip()
    host = (row.get("host") or "").strip()

    location_parts: list[str] = []
    for part in (country_name, region, city):
        cleaned = part.strip()
        if cleaned and cleaned not in location_parts:
            location_parts.append(cleaned)
    country = " / ".join(location_parts)

    domains: list[str] = []
    for value in (domain, host):
        cleaned = value.strip()
        if cleaned and cleaned not in domains:
            domains.append(cleaned)

    return {
        "ip_port": ip_port,
        "assistant_name": "",
        "country": country,
        "auth_required": "",
        "is_active": "",
        "has_leaked_creds": "",
        "asn": asn,
        "asn_name": org,
        "org": org,
        "first_seen": "",
        "last_seen": "",
        "asi_has_breach": "",
        "asi_has_threat_actor": "",
        "asi_threat_actors": "",
        "asi_cves": "",
        "asi_enriched_at": "",
        "asi_domains": ",".join(domains),
    }


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    if not args.fofa.exists():
        raise FileNotFoundError(f"FOFA CSV not found: {args.fofa}")
    if not args.deduped.exists():
        raise FileNotFoundError(f"Deduped CSV not found: {args.deduped}")

    existing_keys = load_existing_keys(args.deduped)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    raw_rows: list[dict[str, str]] = []
    ip_only_rows: list[dict[str, str]] = []
    watchboard_rows: list[dict[str, str]] = []

    with args.fofa.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        raw_header = reader.fieldnames or []
        if not raw_header:
            raise ValueError("FOFA CSV has no header.")

        seen_new_keys: set[str] = set()
        for row in reader:
            ip_port = build_ip_port(row)
            if not ip_port or ip_port in existing_keys or ip_port in seen_new_keys:
                continue
            seen_new_keys.add(ip_port)
            raw_rows.append(row)
            ip_only_rows.append({"ip_port": ip_port})
            watchboard_rows.append(to_watchboard_row(row, ip_port))

    write_csv(args.out_dir / "fofa_new_full_rows.csv", raw_header, raw_rows)
    write_csv(args.out_dir / "fofa_new_ip_port.csv", ["ip_port"], ip_only_rows)
    write_csv(args.out_dir / "fofa_new_watchboard_rows.csv", WATCHBOARD_HEADER, watchboard_rows)

    print(f"existing keys: {len(existing_keys)}")
    print(f"new targets: {len(ip_only_rows)}")
    print(f"output dir: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
