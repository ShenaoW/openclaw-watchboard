#!/usr/bin/env python3
"""Analyze exposure CSV data and persist it into SQLite."""

import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CSV_FILE = DATA_DIR / "explosure" / "openclaw_instances_merged.csv"
DB_PATH = DATA_DIR / "exposure.db"


SERVICE_MAP = {
    22: "SSH",
    80: "HTTP",
    443: "HTTPS",
    8080: "HTTP-Alt",
    8443: "HTTPS-Alt",
    9200: "Elasticsearch",
    27017: "MongoDB",
}

HIGH_RISK_PORTS = {21, 23, 1433, 3306, 3389, 5432, 6379, 9200, 27017}
MEDIUM_RISK_PORTS = {22, 25, 80, 443, 8080, 8443, 18789, 18888}


def parse_datetime(value: str) -> Optional[str]:
    if not value:
        return None

    for fmt in ("%d/%m/%Y, %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).isoformat()
        except ValueError:
            continue

    return value


def normalize_country(raw_country: str) -> Tuple[str, str]:
    country = (raw_country or "").strip()
    if not country:
        return "Unknown", "Unknown"

    country_name = re.sub(r"^[^\w]+", "", country).strip() or country
    return country, country_name


def split_csv_values(value: str) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_flag(value: str, yes_values: set[str], no_values: set[str], default: str = "Unknown") -> str:
    cleaned = (value or "").strip()
    if cleaned in yes_values:
        return "Yes"
    if cleaned in no_values:
        return "No"
    return default


def service_name_for_port(port: int) -> str:
    return SERVICE_MAP.get(port, "OpenClaw")


def compute_risk_level(row: Dict[str, str], port: int, cve_count: int, apt_count: int) -> Tuple[str, int]:
    status = (row.get("status") or "").strip()
    credentials_leaked = normalize_flag(row.get("credentials_leaked", ""), {"Yes", "True"}, {"No", "False", ""}, "Unknown")

    if status == "Leaked":
        return "Critical", 95

    if credentials_leaked == "Yes":
        return "High", 80

    if port in HIGH_RISK_PORTS or cve_count >= 10 or apt_count >= 8:
        return "High", 70

    if port in MEDIUM_RISK_PORTS or cve_count > 0 or apt_count > 0:
        return "Medium", 55

    return "Low", 30


def analyze_exposure_data():
    if not CSV_FILE.exists():
        print(f"❌ 暴露数据文件不存在: {CSV_FILE}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM exposure_instances")
    cursor.execute("DELETE FROM exposure_summary")
    cursor.execute("DELETE FROM exposure_country_stats")
    cursor.execute("DELETE FROM exposure_isp_stats")
    cursor.execute("DELETE FROM exposure_port_stats")

    total = 0
    risk_counter = Counter()
    status_counter = Counter()
    credentials_counter = Counter()
    country_counter = Counter()
    country_risk_counter = defaultdict(Counter)
    country_leaked_counter = Counter()
    isp_counter = Counter()
    port_counter = Counter()
    last_scan_candidates: List[str] = []

    print("🔍 开始分析 exposure 数据...")

    with CSV_FILE.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            ip_port = (row.get("ip_port") or "").strip()
            if ":" not in ip_port:
                continue

            total += 1

            ip, port_str = ip_port.rsplit(":", 1)
            port = int(port_str) if port_str.isdigit() else 0
            service = service_name_for_port(port)

            country, country_name = normalize_country(row.get("country", ""))
            cve_list = split_csv_values(row.get("cve_list", ""))
            apt_groups = split_csv_values(row.get("apt_groups", ""))
            domains = split_csv_values(row.get("domains", ""))

            first_seen = parse_datetime(row.get("first_seen", ""))
            last_seen = parse_datetime(row.get("last_seen", ""))
            scan_time = parse_datetime(row.get("scan_time", ""))

            if scan_time:
                last_scan_candidates.append(scan_time)

            credentials_leaked = normalize_flag(
                row.get("credentials_leaked", ""),
                {"Yes", "True"},
                {"No", "False"},
                "Unknown",
            )
            authenticated = normalize_flag(
                row.get("authenticated", ""),
                {"Yes", "True"},
                {"No", "False"},
                "Unknown",
            )
            has_mcp = normalize_flag(
                row.get("has_mcp", ""),
                {"Yes", "True"},
                {"No", "False"},
                "Unknown",
            )
            active = normalize_flag(
                row.get("active", ""),
                {"True", "Yes"},
                {"False", "No"},
                "Unknown",
            )

            risk_level, risk_score = compute_risk_level(row, port, len(cve_list), len(apt_groups))

            cursor.execute(
                """
                INSERT OR REPLACE INTO exposure_instances (
                    ip_port, ip, port, service, assistant_name, country, country_name,
                    authenticated, active, status, asn, organization, isp, first_seen, last_seen,
                    credentials_leaked, has_mcp, apt_groups, apt_group_count, cve_list, cve_count,
                    scan_time, domains, risk_level, risk_score, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    ip_port,
                    ip,
                    port,
                    service,
                    (row.get("assistant_name") or "").strip(),
                    country,
                    country_name,
                    authenticated,
                    active,
                    (row.get("status") or "Unknown").strip(),
                    (row.get("asn") or "").strip(),
                    (row.get("organization") or "").strip(),
                    (row.get("isp") or "").strip(),
                    first_seen,
                    last_seen,
                    credentials_leaked,
                    has_mcp,
                    json.dumps(apt_groups, ensure_ascii=False),
                    len(apt_groups),
                    json.dumps(cve_list),
                    len(cve_list),
                    scan_time,
                    json.dumps(domains, ensure_ascii=False),
                    risk_level,
                    risk_score,
                ),
            )

            risk_counter[risk_level] += 1
            status_counter[(row.get("status") or "Unknown").strip()] += 1
            credentials_counter[credentials_leaked] += 1
            country_counter[country_name] += 1
            country_risk_counter[country_name][risk_level] += 1
            if (row.get("status") or "").strip() == "Leaked":
                country_leaked_counter[country_name] += 1
            if row.get("isp"):
                isp_counter[row["isp"].strip()] += 1
            port_counter[port] += 1

            if total % 10000 == 0:
                print(f"✅ 已处理 {total} 条暴露记录...")

    total_instances = total
    last_scan_time = max(last_scan_candidates) if last_scan_candidates else None

    cursor.execute(
        """
        INSERT INTO exposure_summary (
            total_instances, clean_count, leaked_count, credentials_yes, credentials_no,
            credentials_unknown, critical_count, high_count, medium_count, low_count,
            country_count, last_scan_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            total_instances,
            status_counter["Clean"],
            status_counter["Leaked"],
            credentials_counter["Yes"],
            credentials_counter["No"],
            credentials_counter["Unknown"],
            risk_counter["Critical"],
            risk_counter["High"],
            risk_counter["Medium"],
            risk_counter["Low"],
            len(country_counter),
            last_scan_time,
        ),
    )

    for country_name, count in country_counter.items():
        raw_country = country_name
        cursor.execute(
            """
            INSERT INTO exposure_country_stats (
                country, country_name, count, leaked_count, critical_count, high_count, medium_count, low_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                raw_country,
                country_name,
                count,
                country_leaked_counter[country_name],
                country_risk_counter[country_name]["Critical"],
                country_risk_counter[country_name]["High"],
                country_risk_counter[country_name]["Medium"],
                country_risk_counter[country_name]["Low"],
            ),
        )

    for isp, count in isp_counter.most_common(100):
        cursor.execute(
            "INSERT INTO exposure_isp_stats (isp, count) VALUES (?, ?)",
            (isp, count),
        )

    for port, count in port_counter.items():
        percentage = round(count * 100.0 / total_instances, 2) if total_instances else 0
        risk = "high" if port in HIGH_RISK_PORTS else "medium" if port in MEDIUM_RISK_PORTS else "low"
        cursor.execute(
            "INSERT INTO exposure_port_stats (port, service, count, percentage, risk) VALUES (?, ?, ?, ?, ?)",
            (port, service_name_for_port(port), count, percentage, risk),
        )

    conn.commit()
    conn.close()

    print("🎉 Exposure 数据分析完成:")
    print(f"   总计: {total_instances} 条")
    print(f"   Critical: {risk_counter['Critical']}")
    print(f"   High: {risk_counter['High']}")
    print(f"   Medium: {risk_counter['Medium']}")
    print(f"   Low: {risk_counter['Low']}")


if __name__ == "__main__":
    analyze_exposure_data()
