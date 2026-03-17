#!/usr/bin/env python3
"""Analyze exposure probe data and persist it into SQLite."""

import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from location_normalizer import GREATER_CHINA_COUNTRIES, normalize_country_name, normalize_location_fields

DATA_DIR = SCRIPT_DIR.parent / "data"
DB_PATH = DATA_DIR / "exposure.db"
RISKS_DB_PATH = DATA_DIR / "risks.db"


SERVICE_MAP = {
    22: "SSH",
    80: "HTTP",
    443: "HTTPS",
    8080: "HTTP-Alt",
    8443: "HTTPS-Alt",
    9200: "Elasticsearch",
    27017: "MongoDB",
}

SEVERITY_ORDER = {"Critical": 4, "High": 3, "Moderate": 2, "Medium": 2, "Low": 1}


def parse_datetime(value: str) -> Optional[str]:
    if not value:
        return None

    for fmt in ("%d/%m/%Y, %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue

    direct_date_match = re.match(r"(\d{4}-\d{2}-\d{2})", value.strip())
    if direct_date_match:
        return direct_date_match.group(1)

    return value


def extract_version_token(value: str) -> Optional[str]:
    if not value:
        return None

    match = re.search(r"v?\d+\.\d+\.\d+(?:[-.][A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)?", value.strip(), re.IGNORECASE)
    if not match:
        return None
    return match.group(0)


def normalize_version_string(value: str) -> Optional[str]:
    token = extract_version_token(value)
    if not token:
        return None

    normalized = token.strip().lower()
    if normalized.startswith("v"):
        normalized = normalized[1:]

    base_match = re.match(r"(\d+\.\d+\.\d+)", normalized)
    if not base_match:
        return None

    return base_match.group(1)


def parse_version(value: str) -> Optional[Dict[str, List]]:
    version = extract_version_token(value)
    if not version:
        return None

    normalized = version.strip().lower()
    if normalized.startswith("v"):
        normalized = normalized[1:]

    tokens = re.findall(r"[a-z]+|\d+", normalized)
    if not tokens:
        return None

    main: List[int] = []
    prerelease: List[Tuple[int, int | str]] = []
    seen_prerelease = False

    for token in tokens:
        if token.isdigit():
            if seen_prerelease:
                prerelease.append((0, int(token)))
            else:
                main.append(int(token))
        else:
            seen_prerelease = True
            rank = {"alpha": 0, "beta": 1, "rc": 2, "dev": 3}.get(token, 4)
            prerelease.append((1, rank))

    return {
        "raw": version,
        "main": main,
        "prerelease": prerelease,
    }


def compare_versions(left: Dict[str, List], right: Dict[str, List]) -> int:
    max_length = max(len(left["main"]), len(right["main"]))
    for index in range(max_length):
        left_value = left["main"][index] if index < len(left["main"]) else 0
        right_value = right["main"][index] if index < len(right["main"]) else 0
        if left_value != right_value:
            return -1 if left_value < right_value else 1

    left_pre = left["prerelease"]
    right_pre = right["prerelease"]
    if not left_pre and not right_pre:
        return 0
    if not left_pre:
        return 1
    if not right_pre:
        return -1

    max_pre_length = max(len(left_pre), len(right_pre))
    for index in range(max_pre_length):
        if index >= len(left_pre):
            return -1
        if index >= len(right_pre):
            return 1

        left_kind, left_value = left_pre[index]
        right_kind, right_value = right_pre[index]
        if left_kind != right_kind:
            return -1 if left_kind < right_kind else 1
        if left_value != right_value:
            return -1 if left_value < right_value else 1

    return 0


def version_satisfies_expression(version: str, expression: str) -> bool:
    normalized_version = normalize_version_string(version)
    parsed_version = parse_version(normalized_version or "")
    if not parsed_version or not expression:
        return False

    clauses = [clause.strip() for clause in re.split(r"\|\|", expression) if clause.strip()]
    if not clauses:
        clauses = [expression.strip()]

    for clause in clauses:
        matches = re.findall(r"(<=|>=|<|>|=)\s*(v?[A-Za-z0-9][A-Za-z0-9.\-]*)", clause)
        if not matches:
            bare_version = extract_version_token(clause)
            parsed_target = parse_version(bare_version or "")
            if parsed_target and compare_versions(parsed_version, parsed_target) == 0:
                return True
            continue

        satisfies_all = True
        for operator, target in matches:
            parsed_target = parse_version(target)
            if not parsed_target:
                satisfies_all = False
                break

            comparison = compare_versions(parsed_version, parsed_target)
            if operator == "<" and not comparison < 0:
                satisfies_all = False
                break
            if operator == "<=" and not comparison <= 0:
                satisfies_all = False
                break
            if operator == ">" and not comparison > 0:
                satisfies_all = False
                break
            if operator == ">=" and not comparison >= 0:
                satisfies_all = False
                break
            if operator == "=" and comparison != 0:
                satisfies_all = False
                break

        if satisfies_all:
            return True

    return False


def load_vulnerability_rules() -> List[Dict[str, str]]:
    if not RISKS_DB_PATH.exists():
        return []

    conn = sqlite3.connect(RISKS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    rows = cursor.execute(
        """
        SELECT vulnerability_id, vulnerability_title, severity, affected_versions, cve
        FROM vulnerabilities
        WHERE affected_versions IS NOT NULL AND trim(affected_versions) != ''
        """
    ).fetchall()
    conn.close()

    return [
        {
            "vulnerability_id": row["vulnerability_id"] or "",
            "title": row["vulnerability_title"] or "",
            "severity": row["severity"] or "Unknown",
            "affected_versions": row["affected_versions"] or "",
            "cve": row["cve"] or "",
        }
        for row in rows
    ]


def match_vulnerabilities_for_version(version: str, vulnerability_rules: List[Dict[str, str]]) -> List[Dict[str, str]]:
    matched = []
    for rule in vulnerability_rules:
        if version_satisfies_expression(version, rule["affected_versions"]):
            matched.append(rule)

    matched.sort(key=lambda item: (-SEVERITY_ORDER.get(item["severity"], 0), item["vulnerability_id"], item["title"]))
    return matched


def normalize_country(raw_country: str) -> Tuple[str, str]:
    raw_country = (raw_country or "").strip()
    if not raw_country:
        return "Unknown", "Unknown"

    country = normalize_country_name(raw_country)
    country_name = re.sub(r"^[^\w]+", "", country).strip() or country
    return country, country_name


def split_csv_values(value: str) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def service_name_for_port(port: int) -> str:
    return SERVICE_MAP.get(port, "OpenClaw")


def mask_ip_third_segment(ip: str) -> str:
    parts = ip.split(".")
    if len(parts) != 4:
        return ip
    if not all(part.isdigit() for part in parts):
        return ip
    parts[2] = "*"
    return ".".join(parts)


def load_probe_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        """
        SELECT ip_port, ip, port, first_seen_at, last_active_at, is_active, source,
               country_name, region, city, asn, org, server_version, updated_at
        FROM probe_instances
        ORDER BY ip_port
        """
    ).fetchall()


def analyze_exposure_data():
    vulnerability_rules = load_vulnerability_rules()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    probe_rows = load_probe_rows(conn)
    if not probe_rows:
        print("❌ probe_instances 为空，无法重建 exposure 统计")
        print("💡 先运行 refresh:exposure-probe 填充探测库")
        conn.close()
        return

    cursor.execute("DELETE FROM exposure_instances")
    cursor.execute("DELETE FROM exposure_country_stats")
    cursor.execute("DELETE FROM exposure_isp_stats")
    cursor.execute("DELETE FROM exposure_port_stats")
    cursor.execute("DELETE FROM exposure_province_stats")

    total = 0
    active_instances = 0
    status_counter = Counter()
    country_counter = Counter()
    isp_counter = Counter()
    port_counter = Counter()
    province_counter = Counter()
    last_scan_candidates: List[str] = []
    matched_vulnerability_ids = set()
    historical_vulnerable_instances = 0
    historical_vulnerable_active_instances = 0

    print("🔍 开始分析 exposure 数据: probe_instances")

    for probe_row in probe_rows:
        ip_port = (probe_row["ip_port"] or "").strip()
        if ":" not in ip_port:
            continue

        total += 1

        ip = (probe_row["ip"] or "").strip() or ip_port.rsplit(":", 1)[0]
        port = int(probe_row["port"] or 0)
        masked_ip = mask_ip_third_segment(ip)
        service = service_name_for_port(port)

        country, province, cn_city = normalize_location_fields(
            probe_row["country_name"] or "",
            probe_row["region"] or "",
            probe_row["city"] or "",
        )
        country, country_name = normalize_country(country)

        cve_list: List[str] = []
        apt_groups: List[str] = []
        domains: List[str] = []

        first_seen = parse_datetime(probe_row["first_seen_at"] or "")
        last_seen = parse_datetime(probe_row["last_active_at"] or "")
        scan_time = parse_datetime(probe_row["updated_at"] or "")
        if scan_time:
            last_scan_candidates.append(scan_time)

        credentials_leaked = "Unknown"
        authenticated = "Unknown"
        has_mcp = "Unknown"
        active = "Yes" if int(probe_row["is_active"] or 0) else "No"
        runtime_status = "Active" if int(probe_row["is_active"] or 0) else "Inactive"
        status = "Unknown"
        isp = (probe_row["org"] or "").strip()

        server_version = normalize_version_string(probe_row["server_version"] or "")
        historical_matches = match_vulnerabilities_for_version(server_version, vulnerability_rules) if server_version else []
        historical_vuln_count = len(historical_matches)
        historical_vuln_max_severity = historical_matches[0]["severity"] if historical_matches else None
        historical_payload = json.dumps(historical_matches[:10], ensure_ascii=False) if historical_matches else None
        is_china_instance = "Yes" if country_name in GREATER_CHINA_COUNTRIES else "No"

        if runtime_status == "Active":
            active_instances += 1
        if historical_vuln_count > 0:
            historical_vulnerable_instances += 1
            if runtime_status == "Active":
                historical_vulnerable_active_instances += 1
            matched_vulnerability_ids.update(item["vulnerability_id"] or item["title"] for item in historical_matches)

        cursor.execute(
            """
            INSERT OR REPLACE INTO exposure_instances (
                ip_port, ip, masked_ip, port, service, assistant_name, country, country_name,
                authenticated, active, status, asn, organization, isp, first_seen, last_seen,
                credentials_leaked, has_mcp, apt_groups, apt_group_count, cve_list, cve_count,
                scan_time, domains, runtime_status, server_version, is_china_instance, province, cn_city,
                historical_vuln_count, historical_vuln_max_severity, historical_vuln_matches
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ip_port,
                ip,
                masked_ip,
                port,
                service,
                "",
                country,
                country_name,
                authenticated,
                active,
                status,
                (probe_row["asn"] or "").strip(),
                (probe_row["org"] or "").strip(),
                isp,
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
                runtime_status,
                server_version,
                is_china_instance,
                province if is_china_instance == "Yes" else "",
                cn_city if is_china_instance == "Yes" else "",
                historical_vuln_count,
                historical_vuln_max_severity,
                historical_payload,
            ),
        )

        status_counter[status] += 1
        country_counter[country_name] += 1
        if isp:
            isp_counter[isp] += 1
        port_counter[port] += 1
        if is_china_instance == "Yes" and province:
            province_counter[province] += 1

        if total % 10000 == 0:
            print(f"✅ 已处理 {total} 条暴露记录...")

    total_instances = total
    last_scan_time = max(last_scan_candidates) if last_scan_candidates else None
    china_exposed_services = 0
    china_active_instances = 0
    for raw_row in conn.execute("SELECT country_name, runtime_status, is_china_instance FROM exposure_instances").fetchall():
        country_name, runtime_status, is_china_instance = raw_row
        if is_china_instance != "Yes" and (country_name or "") not in GREATER_CHINA_COUNTRIES:
            continue
        china_exposed_services += 1
        if runtime_status == "Active":
            china_active_instances += 1
    province_count = len(province_counter)
    city_count = sum(
        1
        for (city_name,) in conn.execute(
            """
            SELECT DISTINCT cn_city
            FROM exposure_instances
            WHERE is_china_instance = 'Yes'
              AND cn_city IS NOT NULL
              AND trim(cn_city) != ''
            """
        ).fetchall()
        if city_name
    )

    cursor.execute(
        """
        INSERT INTO exposure_summary (
            total_instances, active_instances, china_exposed_services, china_active_instances, province_count, city_count,
            clean_count, leaked_count, credentials_yes, credentials_no,
            credentials_unknown,
            country_count, historical_vulnerable_instances, historical_vulnerable_active_instances,
            historical_matched_vulnerability_count, last_scan_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            total_instances,
            active_instances,
            china_exposed_services,
            china_active_instances,
            province_count,
            city_count,
            status_counter["Clean"],
            status_counter["Leaked"],
            0,
            0,
            total_instances,
            len(country_counter),
            historical_vulnerable_instances,
            historical_vulnerable_active_instances,
            len(matched_vulnerability_ids),
            last_scan_time,
        ),
    )

    for country_name, count in country_counter.items():
        raw_country = country_name
        cursor.execute(
            """
            INSERT INTO exposure_country_stats (
                country, country_name, count, leaked_count
            ) VALUES (?, ?, ?, ?)
            """,
            (
                raw_country,
                country_name,
                count,
                0,
            ),
        )

    for isp, count in isp_counter.most_common(100):
        cursor.execute(
            "INSERT INTO exposure_isp_stats (isp, count) VALUES (?, ?)",
            (isp, count),
        )

    for port, count in port_counter.items():
        percentage = round(count * 100.0 / total_instances, 2) if total_instances else 0
        cursor.execute(
            "INSERT INTO exposure_port_stats (port, service, count, percentage) VALUES (?, ?, ?, ?)",
            (port, service_name_for_port(port), count, percentage),
        )

    for province, count in province_counter.most_common():
        cursor.execute(
            "INSERT INTO exposure_province_stats (province, count) VALUES (?, ?)",
            (province, count),
        )

    conn.commit()
    conn.close()

    print("🎉 Exposure 数据分析完成:")
    print(f"   总计: {total_instances} 条")
    print(f"   Active: {active_instances}")
    print(f"   历史漏洞关联实例: {historical_vulnerable_instances}")
    print(f"   历史漏洞关联活跃实例: {historical_vulnerable_active_instances}")
    print(f"   命中的历史漏洞条目: {len(matched_vulnerability_ids)}")


if __name__ == "__main__":
    analyze_exposure_data()
