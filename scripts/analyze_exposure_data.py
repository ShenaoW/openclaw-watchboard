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
DEFAULT_CSV_FILE = DATA_DIR / "explosure" / "openclaw_instances_deduped.csv"
LEGACY_CSV_FILE = DATA_DIR / "explosure" / "openclaw_instances_merged.csv"
ALIVE_CSV_FILE = DATA_DIR / "explosure" / "endpoint_alive.csv"
CONFIG_JSON_FILE = DATA_DIR / "explosure" / "endpoint_alive_configs.json"
CN_CSV_FILE = DATA_DIR / "explosure" / "openclaw_instances_cn.csv"
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

HIGH_RISK_PORTS = {21, 23, 1433, 3306, 3389, 5432, 6379, 9200, 27017}
MEDIUM_RISK_PORTS = {22, 25, 80, 443, 8080, 8443, 18789, 18888}
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


def get_first_present(row: Dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def resolve_csv_path() -> Path:
    if DEFAULT_CSV_FILE.exists():
        return DEFAULT_CSV_FILE
    return LEGACY_CSV_FILE


def mask_ip_third_segment(ip: str) -> str:
    parts = ip.split(".")
    if len(parts) != 4:
        return ip
    if not all(part.isdigit() for part in parts):
        return ip
    parts[2] = "*"
    return ".".join(parts)


def load_runtime_probe_map() -> Dict[str, Dict[str, str]]:
    if not ALIVE_CSV_FILE.exists():
        return {}

    runtime_map: Dict[str, Dict[str, str]] = {}
    with ALIVE_CSV_FILE.open("r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            ip_port = (row.get("ip_port") or "").strip()
            if not ip_port:
                continue

            is_active = (row.get("health") or "").strip() == "200"

            runtime_map[ip_port] = {
                "runtime_status": "Active" if is_active else "Inactive",
                "health": (row.get("health") or "").strip(),
            }

    return runtime_map


def load_server_versions() -> Dict[str, str]:
    if not CONFIG_JSON_FILE.exists():
        return {}

    with CONFIG_JSON_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    version_map: Dict[str, str] = {}
    if not isinstance(data, dict):
        return version_map

    for ip_port, payload in data.items():
        if not isinstance(payload, dict):
            continue
        server_version = payload.get("serverVersion")
        if isinstance(server_version, str) and server_version.strip():
            version_map[ip_port] = server_version.strip()

    return version_map


def load_china_instance_map() -> Dict[str, Dict[str, str]]:
    if not CN_CSV_FILE.exists():
        return {}

    cn_map: Dict[str, Dict[str, str]] = {}
    with CN_CSV_FILE.open("r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            ip_port = (row.get("ip_port") or "").strip()
            if not ip_port:
                continue
            cn_map[ip_port] = {
                "is_china_instance": "Yes",
                "province": (row.get("region") or "").strip(),
                "cn_city": (row.get("city") or "").strip(),
            }

    return cn_map


def normalize_row(row: Dict[str, str]) -> Dict[str, str]:
    status_value = get_first_present(row, "status", "has_leaked_creds")
    normalized_status = "Leaked" if status_value.lower() == "leaked" else "Clean" if status_value.lower() == "clean" else status_value

    return {
        "ip_port": get_first_present(row, "ip_port"),
        "assistant_name": get_first_present(row, "assistant_name"),
        "country": get_first_present(row, "country"),
        "authenticated": get_first_present(row, "authenticated", "auth_required"),
        "active": get_first_present(row, "active", "is_active"),
        "status": normalized_status or "Unknown",
        "asn": get_first_present(row, "asn"),
        "organization": get_first_present(row, "organization", "org"),
        "isp": get_first_present(row, "isp", "asn_name"),
        "first_seen": get_first_present(row, "first_seen"),
        "last_seen": get_first_present(row, "last_seen"),
        "credentials_leaked": get_first_present(row, "credentials_leaked", "has_leaked_creds"),
        "has_mcp": get_first_present(row, "has_mcp"),
        "apt_groups": get_first_present(row, "apt_groups", "asi_threat_actors"),
        "cve_list": get_first_present(row, "cve_list", "asi_cves"),
        "scan_time": get_first_present(row, "scan_time", "asi_enriched_at"),
        "domains": get_first_present(row, "domains", "asi_domains"),
    }


def compute_risk_level(row: Dict[str, str], port: int, cve_count: int, apt_count: int) -> Tuple[str, int]:
    status = (row.get("status") or "").strip()
    credentials_leaked = normalize_flag(row.get("credentials_leaked", ""), {"Yes", "True", "Leaked"}, {"No", "False", "", "Clean"}, "Unknown")

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
    csv_file = resolve_csv_path()
    runtime_probe_map = load_runtime_probe_map()
    version_map = load_server_versions()
    china_instance_map = load_china_instance_map()
    vulnerability_rules = load_vulnerability_rules()

    if not csv_file.exists():
        print(f"❌ 暴露数据文件不存在: {csv_file}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM exposure_instances")
    cursor.execute("DELETE FROM exposure_summary")
    cursor.execute("DELETE FROM exposure_country_stats")
    cursor.execute("DELETE FROM exposure_isp_stats")
    cursor.execute("DELETE FROM exposure_port_stats")
    cursor.execute("DELETE FROM exposure_province_stats")

    total = 0
    active_instances = 0
    risk_counter = Counter()
    status_counter = Counter()
    credentials_counter = Counter()
    country_counter = Counter()
    country_risk_counter = defaultdict(Counter)
    country_leaked_counter = Counter()
    isp_counter = Counter()
    port_counter = Counter()
    province_counter = Counter()
    province_city_counter = defaultdict(Counter)
    last_scan_candidates: List[str] = []
    matched_vulnerability_ids = set()
    historical_vulnerable_instances = 0
    historical_vulnerable_active_instances = 0

    print(f"🔍 开始分析 exposure 数据: {csv_file}")

    with csv_file.open("r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for raw_row in reader:
            row = normalize_row(raw_row)
            ip_port = (row.get("ip_port") or "").strip()
            if ":" not in ip_port:
                continue

            total += 1

            ip, port_str = ip_port.rsplit(":", 1)
            masked_ip = mask_ip_third_segment(ip)
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
            runtime_status = runtime_probe_map.get(ip_port, {}).get("runtime_status", "Unknown")
            server_version = normalize_version_string(version_map.get(ip_port, "") or "")
            normalized_server_version = server_version
            historical_matches = match_vulnerabilities_for_version(normalized_server_version, vulnerability_rules) if normalized_server_version else []
            historical_vuln_count = len(historical_matches)
            historical_vuln_max_severity = historical_matches[0]["severity"] if historical_matches else None
            historical_payload = json.dumps(historical_matches[:10], ensure_ascii=False) if historical_matches else None
            china_instance = china_instance_map.get(ip_port, {})
            is_china_instance = china_instance.get("is_china_instance", "No")
            province = china_instance.get("province", "")
            cn_city = china_instance.get("cn_city", "")
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
                    historical_vuln_count, historical_vuln_max_severity, historical_vuln_matches,
                    risk_level, risk_score, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    ip_port,
                    ip,
                    masked_ip,
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
                    runtime_status,
                    server_version,
                    is_china_instance,
                    province,
                    cn_city,
                    historical_vuln_count,
                    historical_vuln_max_severity,
                    historical_payload,
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
            if is_china_instance == "Yes" and province:
                province_counter[province] += 1
                province_city_counter[province][cn_city or province] += 1

            if total % 10000 == 0:
                print(f"✅ 已处理 {total} 条暴露记录...")

    total_instances = total
    last_scan_time = max(last_scan_candidates) if last_scan_candidates else None

    cursor.execute(
        """
        INSERT INTO exposure_summary (
            total_instances, active_instances, clean_count, leaked_count, credentials_yes, credentials_no,
            credentials_unknown, critical_count, high_count, medium_count, low_count,
            country_count, historical_vulnerable_instances, historical_vulnerable_active_instances,
            historical_matched_vulnerability_count, last_scan_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            total_instances,
            active_instances,
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

    for province, count in province_counter.most_common():
        top_city = province_city_counter[province].most_common(1)[0][0] if province_city_counter[province] else province
        cursor.execute(
            "INSERT INTO exposure_province_stats (province, city, count) VALUES (?, ?, ?)",
            (province, top_city, count),
        )

    conn.commit()
    conn.close()

    print("🎉 Exposure 数据分析完成:")
    print(f"   总计: {total_instances} 条")
    print(f"   Active: {active_instances}")
    print(f"   历史漏洞关联实例: {historical_vulnerable_instances}")
    print(f"   历史漏洞关联活跃实例: {historical_vulnerable_active_instances}")
    print(f"   命中的历史漏洞条目: {len(matched_vulnerability_ids)}")
    print(f"   Critical: {risk_counter['Critical']}")
    print(f"   High: {risk_counter['High']}")
    print(f"   Medium: {risk_counter['Medium']}")
    print(f"   Low: {risk_counter['Low']}")


if __name__ == "__main__":
    analyze_exposure_data()
