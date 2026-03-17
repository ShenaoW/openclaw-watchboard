#!/usr/bin/env python3
"""Import fetched external skill datasets into skills.db."""

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


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
KOI_MALICIOUS_FILE = DATA_DIR / "koi_malicious_skills.txt"
CLAWSEC_CONFIRMED_DIR = DATA_DIR / "malicious_confirmed"


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


def normalize_date(value: Optional[str]) -> str:
    if not value:
        return ""
    match = re.match(r"(\d{4}-\d{2}-\d{2})", value)
    return match.group(1) if match else value


def normalize_timestamp_millis(value) -> str:
    if not value:
        return ""
    try:
        return datetime.fromtimestamp(int(value) / 1000, timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return ""


def make_skills_sh_id(source: str, skill_id: str, fallback_name: str) -> str:
    return f"skills.sh-{source.replace('/', '-')}-{(skill_id or fallback_name or 'unknown')}"


def make_skills_sh_repository(source: str, skill_id: str) -> str:
    repository = f"https://skills.sh/{source.strip()}/{skill_id.strip()}".rstrip("/")
    return repository if repository != "https://skills.sh" else ""


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
    ranking_map = {}
    ranking_payload = {}
    if SKILLS_SH_RANKINGS_FILE.exists():
        ranking_payload = json.loads(SKILLS_SH_RANKINGS_FILE.read_text(encoding="utf-8"))
        for ranking in ranking_payload.get("skills", []):
            key = f"{ranking.get('source', '')}::{ranking.get('skillId', '')}"
            ranking_map[key] = ranking

    if not SKILLS_SH_FILE.exists() and not ranking_map:
        print("ℹ️ 未找到 skills.sh 数据文件，跳过")
        return 0

    payload = {"skills": []}
    if SKILLS_SH_FILE.exists():
        payload = json.loads(SKILLS_SH_FILE.read_text(encoding="utf-8"))

    skills = payload.get("skills", [])
    count = 0
    ranking_only_count = 0
    imported_keys = set()

    cursor.execute("DELETE FROM skills WHERE source = 'skills.sh'")

    for item in skills:
        agent_trust_hub = item.get("agentTrustHub") or {}
        snyk_data = item.get("snyk") or {}
        socket_data = item.get("socket") or {}
        source = item.get("source", "unknown")
        raw_skill_id = item.get("skillId", item.get("name", "unknown"))
        skill_id = make_skills_sh_id(source, raw_skill_id, item.get("name", "unknown"))
        name = item.get("displayName") or item.get("name") or item.get("skillId") or "unknown"
        description = item.get("summary") or ""
        version = ""
        maintainer = source.split("/")[0] if source else "Unknown"
        repository = make_skills_sh_repository(source, item.get("skillId", ""))
        classification = infer_skills_sh_classification(item)
        ranking_key = f"{source}::{item.get('skillId', '')}"
        ranking = ranking_map.get(ranking_key, {})
        last_updated = ""

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
                datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            ),
        )
        imported_keys.add(ranking_key)
        count += 1

    for ranking in ranking_payload.get("skills", []):
        ranking_key = f"{ranking.get('source', '')}::{ranking.get('skillId', '')}"
        if ranking_key in imported_keys:
            continue

        source = ranking.get("source", "unknown")
        raw_skill_id = ranking.get("skillId", ranking.get("name", "unknown"))
        name = ranking.get("name") or ranking.get("skillId") or "unknown"
        maintainer = source.split("/")[0] if source else "Unknown"

        cursor.execute(
            """
            INSERT OR REPLACE INTO skills
            (id, name, version, description, category, maintainer, source, classification,
             security_score, downloads, rating, verified, last_updated, permissions,
             repository, file_structure, dependencies, skill_content, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                make_skills_sh_id(source, raw_skill_id, name),
                name,
                "",
                "",
                categorize_skill(name, ""),
                maintainer,
                "skills.sh",
                "unknown",
                0,
                int(ranking.get("installs") or 0),
                0.0,
                False,
                "",
                json.dumps([]),
                make_skills_sh_repository(source, ranking.get("skillId", "")),
                json.dumps([]),
                json.dumps([]),
                "",
                datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            ),
        )
        ranking_only_count += 1
        count += 1

    print(f"✅ 已导入 skills.sh: {count} 条（审计 {count - ranking_only_count}，排名补充 {ranking_only_count}）")
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
                    normalize_date(item.get("updatedAt") or item.get("lastUpdated")),
                    json.dumps([]),
                    item.get("url") or "",
                    json.dumps([]),
                    json.dumps([]),
                    item.get("summary") or "",
                    datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                ),
            )
            total_count += 1

    print(f"✅ 已导入 GenDigital: {total_count} 条")
    return total_count


def import_koi(cursor):
    if not KOI_MALICIOUS_FILE.exists():
        print("ℹ️ 未找到 KOI 恶意技能文件，跳过")
        return 0

    cursor.execute("DELETE FROM skills WHERE source = 'koi'")
    total_count = 0
    imported_names = set()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for raw_line in KOI_MALICIOUS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or "|" not in line:
            continue

        campaign, names = line.split("|", 1)
        for skill_name in [item.strip() for item in names.split(",") if item.strip()]:
            imported_names.add(skill_name)
            cursor.execute(
                """
                INSERT OR REPLACE INTO skills
                (id, name, version, description, category, maintainer, source, classification,
                 security_score, downloads, rating, verified, last_updated, permissions,
                 repository, file_structure, dependencies, skill_content, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"koi-{skill_name}",
                    skill_name,
                    "unknown",
                    "",
                    "unknown",
                    "unknown",
                    "koi",
                    "malicious",
                    0,
                    0,
                    0.0,
                    False,
                    "",
                    json.dumps([]),
                    "unknown",
                    json.dumps([]),
                    json.dumps([]),
                    campaign.strip(),
                    today,
                ),
            )
            total_count += 1

    print(f"✅ 已导入 KOI 恶意技能: {total_count} 条")
    return total_count


def import_clawsec_confirmed(cursor):
    if not CLAWSEC_CONFIRMED_DIR.exists():
        print("ℹ️ 未找到 clawsec 确认恶意技能目录，跳过")
        return 0

    cursor.execute("DELETE FROM skills WHERE source = 'clawsec'")

    total_count = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for meta_file in sorted(CLAWSEC_CONFIRMED_DIR.rglob("_meta.json")):
        version_dir = meta_file.parent
        owner_dir = version_dir.parent.parent
        owner = owner_dir.name

        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8").lstrip("\ufeff"))
        except json.JSONDecodeError as exc:
            print(f"⚠️  解析 clawsec 元数据失败 {meta_file}: {exc}")
            continue

        slug = (meta.get("slug") or owner_dir.name or version_dir.name).strip()
        display_name = (meta.get("displayName") or slug or "unknown").strip()
        latest = meta.get("latest") or {}
        version = (latest.get("version") or "1.0.0").strip()
        published_at = normalize_timestamp_millis(latest.get("publishedAt"))
        repository = (latest.get("commit") or "").strip()

        audit_file = version_dir.with_name(f"{version_dir.name}_audit.json")
        audit_summary = {}
        if audit_file.exists():
            try:
                audit_payload = json.loads(audit_file.read_text(encoding="utf-8").lstrip("\ufeff"))
                audit_summary = audit_payload.get("audit_summary") or {}
            except json.JSONDecodeError as exc:
                print(f"⚠️  解析 clawsec 审计文件失败 {audit_file}: {exc}")

        description = (audit_summary.get("summary_text") or display_name or slug).strip()
        skill_file = version_dir / "SKILL.md"
        skill_content = skill_file.read_text(encoding="utf-8") if skill_file.exists() else ""

        file_structure = sorted(
            [
                item.name
                for item in version_dir.iterdir()
                if not item.name.startswith(".") and item.name != "_meta.json"
            ]
        )

        dependencies = meta.get("history") if isinstance(meta.get("history"), list) else []
        category = categorize_skill(slug, description)
        existing_clawhub_id = f"clawhub-{owner}-{slug}"

        existing_row = cursor.execute(
            "SELECT id FROM skills WHERE id = ?",
            (existing_clawhub_id,),
        ).fetchone()
        skill_id = existing_clawhub_id if existing_row else f"clawsec-{owner}-{slug}"

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
                slug,
                version,
                description,
                category,
                owner,
                "clawsec",
                "malicious",
                0,
                0,
                0.0,
                True,
                published_at,
                json.dumps([]),
                repository,
                json.dumps(file_structure),
                json.dumps(dependencies),
                skill_content,
                today,
            ),
        )
        total_count += 1

    print(f"✅ 已导入 clawsec 确认恶意技能: {total_count} 条")
    return total_count


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    skills_sh_count = import_skills_sh(cursor)
    gendigital_count = import_gendigital(cursor)
    koi_count = import_koi(cursor)
    clawsec_count = import_clawsec_confirmed(cursor)

    conn.commit()
    conn.close()

    print("🎉 外部 Skills 数据导入完成")
    print(f"   skills.sh: {skills_sh_count}")
    print(f"   gendigital: {gendigital_count}")
    print(f"   koi: {koi_count}")
    print(f"   clawsec: {clawsec_count}")


if __name__ == "__main__":
    main()
