#!/usr/bin/env python3

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from location_normalizer import normalize_location_fields


DATA_DIR = ROOT_DIR / "data"
EXPOSURE_DB = DATA_DIR / "exposure.db"
DEDUPED_CSV = DATA_DIR / "explosure" / "openclaw_instances_deduped.csv"
CN_CSV = DATA_DIR / "explosure" / "openclaw_instances_cn.csv"
FOFA_CACHE_CSV = DATA_DIR / "explosure" / "fofa_cache" / "openclaw_latest.csv"


def normalize_csv(path: Path, field_triplets: list[tuple[str, str, str]]) -> int:
    if not path.exists():
        return 0

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    updated = 0
    for row in rows:
        changed = False
        for country_field, region_field, city_field in field_triplets:
            if country_field not in row:
                continue
            country, region, city = normalize_location_fields(
                row.get(country_field, ""),
                row.get(region_field, ""),
                row.get(city_field, ""),
            )
            new_values = {
                country_field: country,
                region_field: region,
                city_field: city,
            }
            for key, value in new_values.items():
                if key in row and (row.get(key) or "").strip() != value:
                    row[key] = value
                    changed = True
        if changed:
            updated += 1

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return updated


def normalize_probe_instances(conn: sqlite3.Connection) -> int:
    rows = conn.execute("SELECT ip_port, country_name, region, city FROM probe_instances").fetchall()
    updated = 0
    for ip_port, country_name, region, city in rows:
        new_country, new_region, new_city = normalize_location_fields(country_name or "", region or "", city or "")
        if (country_name or "") == new_country and (region or "") == new_region and (city or "") == new_city:
            continue
        conn.execute(
            """
            UPDATE probe_instances
            SET country_name = ?, region = ?, city = ?, updated_at = CURRENT_TIMESTAMP
            WHERE ip_port = ?
            """,
            (new_country, new_region, new_city, ip_port),
        )
        updated += 1
    conn.commit()
    return updated


def normalize_exposure_instances(conn: sqlite3.Connection) -> int:
    rows = conn.execute("SELECT id, country, country_name, province, cn_city FROM exposure_instances").fetchall()
    updated = 0
    for row_id, country, country_name, province, cn_city in rows:
        base_country = country_name or country or ""
        new_country, new_region, new_city = normalize_location_fields(base_country, province or "", cn_city or "")
        if (
            (country or "") == new_country
            and (country_name or "") == new_country
            and (province or "") == new_region
            and (cn_city or "") == new_city
        ):
            continue
        conn.execute(
            """
            UPDATE exposure_instances
            SET country = ?, country_name = ?, province = ?, cn_city = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_country, new_country, new_region, new_city, row_id),
        )
        updated += 1
    conn.commit()
    return updated


def main() -> int:
    csv_updates = {
        str(DEDUPED_CSV): normalize_csv(DEDUPED_CSV, [("country", "region", "city")]),
        str(CN_CSV): normalize_csv(CN_CSV, [("country", "region", "city")]),
        str(FOFA_CACHE_CSV): normalize_csv(FOFA_CACHE_CSV, [("country_name", "region", "city")]),
    }

    probe_updates = 0
    exposure_updates = 0
    if EXPOSURE_DB.exists():
        conn = sqlite3.connect(EXPOSURE_DB)
        try:
            probe_updates = normalize_probe_instances(conn)
            exposure_updates = normalize_exposure_instances(conn)
        finally:
            conn.close()

    print("Normalized exposure location data:")
    for path, count in csv_updates.items():
        print(f"  CSV {path}: {count} row(s) updated")
    print(f"  DB probe_instances: {probe_updates} row(s) updated")
    print(f"  DB exposure_instances: {exposure_updates} row(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
