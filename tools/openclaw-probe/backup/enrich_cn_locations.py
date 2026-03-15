#!/usr/bin/env python3
"""Enrich China OpenClaw instances with province/city fields using IP2Location."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

try:
    import IP2Location  # type: ignore
except ImportError:  # pragma: no cover - runtime dependency
    IP2Location = None


CHINA_CODES = {"CN", "HK", "TW", "MO"}
SPECIAL_PROVINCES = {
    "HK": "香港",
    "TW": "台湾",
    "MO": "澳门",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter China/HK/TW/MO OpenClaw instances and enrich province/city using IP2Location."
    )
    parser.add_argument("--input", required=True, type=Path, help="Input deduped CSV path.")
    parser.add_argument("--output", required=True, type=Path, help="Output China-only CSV path.")
    parser.add_argument(
        "--database",
        required=True,
        type=Path,
        help="IP2Location BIN database path.",
    )
    return parser.parse_args()


def extract_ip(ip_port: str) -> str:
    text = (ip_port or "").strip()
    if not text:
        return ""
    if text.count(":") > 1:
        return ":".join(text.split(":")[:-1])
    return text.split(":", 1)[0]


def get_geo_info(ip: str, db: "IP2Location.IP2Location") -> tuple[str, str, str]:
    try:
        record = db.get_all(ip)
    except Exception:
        return "", "", ""

    if not record:
        return "", "", ""

    return (
        (record.country_short or "").strip(),
        (record.region or "").strip(),
        (record.city or "").strip(),
    )


def main() -> int:
    args = parse_args()

    if IP2Location is None:
        raise RuntimeError("Missing dependency: IP2Location")
    if not args.input.exists():
        raise FileNotFoundError(f"Input not found: {args.input}")
    if not args.database.exists():
        raise FileNotFoundError(f"IP2Location database not found: {args.database}")

    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            raise ValueError("Input CSV has no header.")

        rows = list(reader)

    db = IP2Location.IP2Location(str(args.database))
    output_fieldnames = list(fieldnames)
    for extra in ("physical_country", "region", "city"):
        if extra not in output_fieldnames:
            output_fieldnames.append(extra)

    china_rows: list[dict[str, str]] = []
    for row in rows:
        ip = extract_ip((row.get("ip_port") or "").strip())
        if not ip:
            continue

        country_code, region, city = get_geo_info(ip, db)
        if country_code not in CHINA_CODES:
            continue

        province = SPECIAL_PROVINCES.get(country_code, region or "未知")
        normalized_city = city or "未知"

        row["physical_country"] = country_code
        row["region"] = province
        row["city"] = normalized_city
        china_rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(china_rows)

    print(f"china rows: {len(china_rows)}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
