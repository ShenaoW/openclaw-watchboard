#!/usr/bin/env python3
"""Import annotated vulnerability CSV into risks.db."""

import csv
import os
import sqlite3


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ANNOTATED_CSV_PATH = os.path.abspath(os.path.join(BASE_DIR, "data", "vuls", "openclaw_vuls_annotated.csv"))
RISKS_DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "data", "risks.db"))


def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def empty_to_none(value):
    if value is None:
      return None
    cleaned = str(value).strip()
    return cleaned or None


def main():
    conn = sqlite3.connect(RISKS_DB_PATH)
    cursor = conn.cursor()

    with open(ANNOTATED_CSV_PATH, "r", encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    cursor.execute("DELETE FROM vulnerabilities")
    cursor.execute("DELETE FROM vulnerability_summary")

    for row in rows:
        cursor.execute(
            '''
            INSERT INTO vulnerabilities (
                source_index,
                vulnerability_title,
                stage,
                reason,
                vulnerability_id,
                severity,
                affected_versions,
                cve,
                cwe,
                vulnerability_link,
                vulnerability_nature_id,
                vulnerability_nature_label,
                top10_primary_id,
                top10_primary_label,
                top10_match_ids,
                top10_match_labels,
                top10_match_count,
                top10_rank,
                mapping_confidence,
                analysis_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                to_int(row.get("No.")),
                row.get("Vulnerability Title", ""),
                row.get("Stage", ""),
                row.get("Reason", ""),
                empty_to_none(row.get("Vulnerability ID", "")),
                row.get("Severity", ""),
                row.get("Affected Versions", ""),
                row.get("CVE", ""),
                row.get("CWE", ""),
                row.get("Vulnerability Link", ""),
                row.get("vulnerability_nature_id", ""),
                row.get("vulnerability_nature_label", ""),
                row.get("top10_primary_id", ""),
                row.get("top10_primary_label", ""),
                row.get("top10_match_ids", ""),
                row.get("top10_match_labels", ""),
                to_int(row.get("top10_match_count")),
                to_int(row.get("top10_rank"), None),
                to_float(row.get("mapping_confidence")),
                row.get("analysis_reason", ""),
            ),
        )

    total_count = len(rows)
    llm_specific_count = sum(1 for row in rows if row.get("vulnerability_nature_id") == "llm_system_specific")
    general_software_count = sum(1 for row in rows if row.get("vulnerability_nature_id") == "general_software_vulnerability")
    mapped_top10_count = sum(1 for row in rows if row.get("top10_primary_id"))

    cursor.execute(
        '''
        INSERT INTO vulnerability_summary (
            total_count,
            llm_specific_count,
            general_software_count,
            mapped_top10_count
        ) VALUES (?, ?, ?, ?)
        ''',
        (total_count, llm_specific_count, general_software_count, mapped_top10_count),
    )

    conn.commit()
    conn.close()

    print(f"✅ 已导入 vulnerabilities 到数据库: {RISKS_DB_PATH}")
    print(f"📊 总计: {total_count}")
    print(f"📊 大模型系统特有漏洞: {llm_specific_count}")
    print(f"📊 软件系统通用漏洞: {general_software_count}")
    print(f"📊 已映射 OpenClaw Top 10: {mapped_top10_count}")


if __name__ == "__main__":
    main()
