#!/usr/bin/env python3
"""Import fetched external skill datasets into skills.db."""

import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data" / "skills"
DB_PATH = SCRIPT_DIR.parent / "data" / "skills.db"
SKILLS_SH_FILE = DATA_DIR / "skills_sh_audits.json"
SKILLS_SH_RANKINGS_FILE = DATA_DIR / "skills_sh_rankings.json"
GENDIGITAL_FILES = [
    DATA_DIR / "gendigital_safe.json",
    DATA_DIR / "gendigital_suspicious.json",
    DATA_DIR / "gendigital_malicious.json",
]


def categorize_skill(skill_name: str, description: str = "") -> str:
    content = f"{skill_name} {description}".lower()
    if any(word in content for word in ["security", "auth", "crypto", "scan", "protect"]):
        return "Security"
    if any(word in content for word in ["network", "api", "http", "socket", "web", "client"]):
        return "Network"
    if any(word in content for word in ["file", "data", "parser", "analyzer", "process"]):
        return "Analysis"
    if any(word in content for word in ["dev", "build", "test", "deploy", "code", "git"]):
        return "Development"
    if any(word in content for word in ["system", "monitor", "admin", "ops"]):
        return "System"
    if any(word in content for word in ["ui", "frontend", "design", "interface"]):
        return "Frontend"
    if any(word in content for word in ["db", "database", "sql", "storage"]):
        return "Database"
    if any(word in content for word in ["ai", "model", "agent", "prompt"]):
        return "AI/ML"
    if any(word in content for word in ["email", "chat", "message", "notification"]):
        return "Communication"
    if any(word in content for word in ["automation", "workflow", "task", "schedule"]):
        return "Automation"
    return "Utility"


def normalize_date(value: str | None):
    if not value:
        return datetime.now(UTC).strftime("%Y-%m-%d")
    match = re.match(r"(\d{4}-\d{2}-\d{2})", value)
    return match.group(1) if match else value


def infer_skills_sh_classification(item: dict) -> str:
    levels = []

    agent_risk = (((item.get("agentTrustHub") or {}).get("result") or {}).get("overall_risk_level") or "").upper()
    snyk_risk = ((((item.get("snyk") or {}).get("result") or {}).get("overall_risk_level")) or "").upper()
    gemini_risk = (((((item.get("agentTrustHub") or {}).get("result") or {}).get("gemini_analysis")) or {}).get("verdict") or "").upper()
    socket_alerts = int((((item.get("socket") or {}).get("result") or {}).get("alertCount") or 0))
    av_infected = int((((((item.get("agentTrustHub") or {}).get("result") or {}).get("av_analysis")) or {}).get("summary") or {}).get("infected") or 0)

    for value in [agent_risk, snyk_risk, gemini_risk]:
        if value:
            levels.append(value)

    if av_infected > 0 or "MALICIOUS" in levels:
        return "malicious"

    if socket_alerts > 0 or any(level in {"MEDIUM", "HIGH", "CRITICAL"} for level in levels):
        return "suspicious"

    if levels and all(level in {"SAFE", "LOW"} for level in levels):
        return "safe"

    return "unknown"


def import_skills_sh(cursor):
    if not SKILLS_SH_FILE.exists():
        print("ℹ️ 未找到 skills.sh 数据文件，跳过")
        return 0

    payload = json.loads(SKILLS_SH_FILE.read_text(encoding="utf-8"))
    skills = payload.get("skills", [])
    ranking_map = {}
    if SKILLS_SH_RANKINGS_FILE.exists():
        ranking_payload = json.loads(SKILLS_SH_RANKINGS_FILE.read_text(encoding="utf-8"))
        for ranking in ranking_payload.get("skills", []):
            key = f"{ranking.get('source', '')}::{ranking.get('skillId', '')}"
            ranking_map[key] = ranking
    count = 0

    cursor.execute("DELETE FROM skills WHERE source = 'skills.sh'")

    for item in skills:
        agent_trust_hub = item.get("agentTrustHub") or {}
        snyk_data = item.get("snyk") or {}
        socket_data = item.get("socket") or {}
        skill_id = f"skills.sh-{item.get('source', 'unknown').replace('/', '-')}-{item.get('skillId', item.get('name', 'unknown'))}"
        name = item.get("displayName") or item.get("name") or item.get("skillId") or "unknown"
        description = item.get("summary") or ""
        version = ""
        maintainer = (item.get("source") or "").split("/")[0] if item.get("source") else "Unknown"
        repository = f"https://skills.sh/{item.get('source', '').strip()}/{item.get('skillId', '').strip()}".rstrip("/")
        classification = infer_skills_sh_classification(item)
        ranking = ranking_map.get(f"{item.get('source', '')}::{item.get('skillId', '')}", {})
        last_updated = normalize_date(
            agent_trust_hub.get("analyzedAt")
            or snyk_data.get("analyzedAt")
            or socket_data.get("analyzedAt")
        )

        cursor.execute(
            """
            INSERT OR REPLACE INTO skills
            (id, name, version, description, category, maintainer, source, classification,
             security_score, downloads, rating, verified, last_updated, permissions,
             repository, file_structure, dependencies, skill_content, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                skill_id,
                name,
                version,
                description,
                categorize_skill(name, description),
                maintainer,
                "skills.sh",
                classification,
                0,
                int(ranking.get("installs") or 0),
                0.0,
                False,
                last_updated,
                json.dumps([]),
                repository if repository != "https://skills.sh" else "",
                json.dumps([]),
                json.dumps([]),
                "",
                datetime.now(UTC).strftime("%Y-%m-%d"),
            ),
        )
        count += 1

    print(f"✅ 已导入 skills.sh: {count} 条")
    return count


def import_gendigital(cursor):
    total_count = 0
    cursor.execute("DELETE FROM skills WHERE source = 'gendigital'")

    for file_path in GENDIGITAL_FILES:
        if not file_path.exists():
            continue

        payload = json.loads(file_path.read_text(encoding="utf-8"))
        skills = payload.get("skills", [])
        classification = payload.get("classification", "safe")

        for item in skills:
            name = item.get("displayName") or item.get("skillName") or item.get("skillSlug") or "unknown"
            description = item.get("description") or item.get("summary") or ""
            skill_slug = item.get("skillSlug") or item.get("skillName") or name
            author = item.get("authorHandle") or "Unknown"
            skill_id = f"gendigital-{author}-{skill_slug}"

            cursor.execute(
                """
                INSERT OR REPLACE INTO skills
                (id, name, version, description, category, maintainer, source, classification,
                 security_score, downloads, rating, verified, last_updated, permissions,
                 repository, file_structure, dependencies, skill_content, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    skill_id,
                    name,
                    item.get("version") or "",
                    description,
                    categorize_skill(name, description),
                    author,
                    "gendigital",
                    classification if classification in {"safe", "suspicious", "malicious"} else "unknown",
                    0,
                    0,
                    0.0,
                    item.get("status") == "verified",
                    normalize_date(item.get("createdAt")),
                    json.dumps([]),
                    item.get("url") or "",
                    json.dumps([]),
                    json.dumps([]),
                    item.get("summary") or "",
                    datetime.now(UTC).strftime("%Y-%m-%d"),
                ),
            )
            total_count += 1

    print(f"✅ 已导入 GenDigital: {total_count} 条")
    return total_count


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    skills_sh_count = import_skills_sh(cursor)
    gendigital_count = import_gendigital(cursor)

    conn.commit()
    conn.close()

    print("🎉 外部 Skills 数据导入完成")
    print(f"   skills.sh: {skills_sh_count}")
    print(f"   gendigital: {gendigital_count}")


if __name__ == "__main__":
    main()
