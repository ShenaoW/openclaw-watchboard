#!/usr/bin/env python3
"""Export domestic exposure instances with matched vulnerabilities to Excel."""

import json
import os
import sqlite3
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "data", "exposure.db")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")


def parse_matches(raw_value):
    if not raw_value:
        return []
    try:
        value = json.loads(raw_value)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def build_matches_text(matches):
    parts = []
    for item in matches:
        vulnerability_id = (item.get("vulnerability_id") or "").strip()
        title = (item.get("title") or "").strip()
        severity = (item.get("severity") or "").strip()
        affected_versions = (item.get("affected_versions") or "").strip()
        cve = (item.get("cve") or "").strip()
        detail = " | ".join(
            part
            for part in [vulnerability_id, title, severity, affected_versions, cve]
            if part
        )
        if detail:
            parts.append(detail)
    return "\n".join(parts)


def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT
            id,
            ip,
            port,
            service,
            assistant_name,
            country_name,
            organization,
            isp,
            runtime_status,
            server_version,
            historical_vuln_count,
            historical_vuln_max_severity,
            historical_vuln_matches,
            province,
            cn_city,
            authenticated,
            active,
            status,
            credentials_leaked,
            has_mcp,
            asn,
            first_seen,
            last_seen,
            domains
        FROM exposure_instances
        WHERE is_china_instance = 'Yes'
          AND historical_vuln_count > 0
        ORDER BY
            CASE historical_vuln_max_severity
                WHEN 'Critical' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Moderate' THEN 3
                WHEN 'Medium' THEN 4
                WHEN 'Low' THEN 5
                ELSE 6
            END,
            historical_vuln_count DESC,
            province ASC,
            cn_city ASC,
            ip ASC
        """
    ).fetchall()
    conn.close()

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "境内漏洞关联暴露实例"

    headers = [
        "记录ID",
        "原始IP",
        "端口",
        "服务",
        "助手名称",
        "国家/地区",
        "省份",
        "城市",
        "组织",
        "运营商",
        "ASN",
        "运行状态",
        "服务版本",
        "关联漏洞数量",
        "最高漏洞级别",
        "漏洞匹配详情",
        "认证状态",
        "活跃标记",
        "状态",
        "凭据泄露",
        "MCP",
        "域名",
        "首次发现",
        "最后发现",
    ]
    worksheet.append(headers)

    for cell in worksheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row in rows:
        matches = parse_matches(row["historical_vuln_matches"])
        worksheet.append(
            [
                row["id"],
                row["ip"],
                row["port"],
                row["service"],
                row["assistant_name"] or "",
                row["country_name"] or "",
                row["province"] or "",
                row["cn_city"] or "",
                row["organization"] or "",
                row["isp"] or "",
                row["asn"] or "",
                row["runtime_status"] or "",
                row["server_version"] or "",
                row["historical_vuln_count"] or 0,
                row["historical_vuln_max_severity"] or "",
                build_matches_text(matches),
                row["authenticated"] or "",
                row["active"] or "",
                row["status"] or "",
                row["credentials_leaked"] or "",
                row["has_mcp"] or "",
                row["domains"] or "",
                row["first_seen"] or "",
                row["last_seen"] or "",
            ]
        )

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    wrap_alignment = Alignment(vertical="top", wrap_text=True)
    for row in worksheet.iter_rows(min_row=2):
      for cell in row:
        cell.alignment = wrap_alignment

    column_widths = {
        "A": 12,
        "B": 16,
        "C": 10,
        "D": 12,
        "E": 18,
        "F": 14,
        "G": 14,
        "H": 14,
        "I": 24,
        "J": 28,
        "K": 14,
        "L": 12,
        "M": 14,
        "N": 12,
        "O": 14,
        "P": 88,
        "Q": 12,
        "R": 12,
        "S": 12,
        "T": 12,
        "U": 10,
        "V": 24,
        "W": 14,
        "X": 14,
    }
    for column, width in column_widths.items():
        worksheet.column_dimensions[column].width = width

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = os.path.join(
        EXPORT_DIR,
        f"openclaw_domestic_vulnerable_exposures_{timestamp}.xlsx",
    )
    workbook.save(export_path)

    print(f"exported_rows={len(rows)}")
    print(export_path)


if __name__ == "__main__":
    main()
