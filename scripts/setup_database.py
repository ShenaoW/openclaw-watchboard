#!/usr/bin/env python3
"""OpenClaw Watchboard database setup."""

import os
import sqlite3


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SKILLS_DB_PATH = os.path.join(DATA_DIR, "skills.db")
EXPOSURE_DB_PATH = os.path.join(DATA_DIR, "exposure.db")
RISKS_DB_PATH = os.path.join(DATA_DIR, "risks.db")


def setup_skills_database():
    """创建 skills 数据库表结构"""
    conn = sqlite3.connect(SKILLS_DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS skills (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT,
            description TEXT,
            category TEXT,
            maintainer TEXT,
            source TEXT NOT NULL,
            classification TEXT NOT NULL,
            security_score INTEGER DEFAULT 0,
            downloads INTEGER DEFAULT 0,
            rating REAL DEFAULT 0.0,
            verified BOOLEAN DEFAULT FALSE,
            last_updated TIMESTAMP,
            permissions TEXT, -- JSON格式存储权限列表
            repository TEXT,
            file_structure TEXT, -- JSON格式存储文件结构
            dependencies TEXT, -- JSON格式存储依赖
            skill_content TEXT, -- SKILL.md内容
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS skill_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_skills INTEGER,
            source_clawhub INTEGER,
            source_skills_rest INTEGER,
            source_skillsmp INTEGER,
            classification_safe INTEGER,
            classification_suspicious INTEGER,
            classification_malicious INTEGER,
            classification_unknown INTEGER,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS developer_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            developer TEXT NOT NULL,
            total_skills INTEGER,
            safe_skills INTEGER,
            suspicious_skills INTEGER,
            malicious_skills INTEGER,
            unknown_skills INTEGER,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS category_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            skill_count INTEGER,
            percentage REAL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    existing_skill_stats = {
        row[1] for row in cursor.execute("PRAGMA table_info(skill_stats)").fetchall()
    }
    if "classification_malicious" not in existing_skill_stats:
        cursor.execute("ALTER TABLE skill_stats ADD COLUMN classification_malicious INTEGER DEFAULT 0")

    existing_developer_stats = {
        row[1] for row in cursor.execute("PRAGMA table_info(developer_stats)").fetchall()
    }
    if "malicious_skills" not in existing_developer_stats:
        cursor.execute("ALTER TABLE developer_stats ADD COLUMN malicious_skills INTEGER DEFAULT 0")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_source ON skills(source)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_classification ON skills(classification)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_maintainer ON skills(maintainer)")

    conn.commit()
    conn.close()

    print(f"✅ Skills 数据库初始化完成: {SKILLS_DB_PATH}")


def setup_exposure_database():
    """创建 exposure 数据库表结构"""
    conn = sqlite3.connect(EXPOSURE_DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS exposure_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_port TEXT NOT NULL UNIQUE,
            ip TEXT,
            masked_ip TEXT,
            port INTEGER,
            service TEXT,
            assistant_name TEXT,
            country TEXT,
            country_name TEXT,
            authenticated TEXT,
            active TEXT,
            status TEXT,
            asn TEXT,
            organization TEXT,
            isp TEXT,
            first_seen TEXT,
            last_seen TEXT,
            credentials_leaked TEXT,
            has_mcp TEXT,
            apt_groups TEXT,
            apt_group_count INTEGER DEFAULT 0,
            cve_list TEXT,
            cve_count INTEGER DEFAULT 0,
            scan_time TEXT,
            domains TEXT,
            runtime_status TEXT,
            server_version TEXT,
            is_china_instance TEXT,
            province TEXT,
            cn_city TEXT,
            historical_vuln_count INTEGER DEFAULT 0,
            historical_vuln_max_severity TEXT,
            historical_vuln_matches TEXT,
            risk_level TEXT,
            risk_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS exposure_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_instances INTEGER,
            active_instances INTEGER,
            china_exposed_services INTEGER DEFAULT 0,
            china_active_instances INTEGER DEFAULT 0,
            province_count INTEGER DEFAULT 0,
            city_count INTEGER DEFAULT 0,
            clean_count INTEGER,
            leaked_count INTEGER,
            credentials_yes INTEGER,
            credentials_no INTEGER,
            credentials_unknown INTEGER,
            critical_count INTEGER,
            high_count INTEGER,
            medium_count INTEGER,
            low_count INTEGER,
            country_count INTEGER,
            historical_vulnerable_instances INTEGER DEFAULT 0,
            historical_vulnerable_active_instances INTEGER DEFAULT 0,
            historical_matched_vulnerability_count INTEGER DEFAULT 0,
            last_scan_time TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS exposure_country_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT,
            country_name TEXT,
            count INTEGER,
            leaked_count INTEGER,
            critical_count INTEGER,
            high_count INTEGER,
            medium_count INTEGER,
            low_count INTEGER,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS exposure_isp_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isp TEXT,
            count INTEGER,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS exposure_port_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            port INTEGER,
            service TEXT,
            count INTEGER,
            percentage REAL,
            risk TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS exposure_province_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            province TEXT,
            city TEXT,
            count INTEGER,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    existing_exposure_instances = {
        row[1] for row in cursor.execute("PRAGMA table_info(exposure_instances)").fetchall()
    }
    if "masked_ip" not in existing_exposure_instances:
        cursor.execute("ALTER TABLE exposure_instances ADD COLUMN masked_ip TEXT")
    if "runtime_status" not in existing_exposure_instances:
        cursor.execute("ALTER TABLE exposure_instances ADD COLUMN runtime_status TEXT")
    if "server_version" not in existing_exposure_instances:
        cursor.execute("ALTER TABLE exposure_instances ADD COLUMN server_version TEXT")
    if "is_china_instance" not in existing_exposure_instances:
        cursor.execute("ALTER TABLE exposure_instances ADD COLUMN is_china_instance TEXT")
    if "province" not in existing_exposure_instances:
        cursor.execute("ALTER TABLE exposure_instances ADD COLUMN province TEXT")
    if "cn_city" not in existing_exposure_instances:
        cursor.execute("ALTER TABLE exposure_instances ADD COLUMN cn_city TEXT")
    if "historical_vuln_count" not in existing_exposure_instances:
        cursor.execute("ALTER TABLE exposure_instances ADD COLUMN historical_vuln_count INTEGER DEFAULT 0")
    if "historical_vuln_max_severity" not in existing_exposure_instances:
        cursor.execute("ALTER TABLE exposure_instances ADD COLUMN historical_vuln_max_severity TEXT")
    if "historical_vuln_matches" not in existing_exposure_instances:
        cursor.execute("ALTER TABLE exposure_instances ADD COLUMN historical_vuln_matches TEXT")

    existing_exposure_summary = {
        row[1] for row in cursor.execute("PRAGMA table_info(exposure_summary)").fetchall()
    }
    if "active_instances" not in existing_exposure_summary:
        cursor.execute("ALTER TABLE exposure_summary ADD COLUMN active_instances INTEGER")
    if "china_exposed_services" not in existing_exposure_summary:
        cursor.execute("ALTER TABLE exposure_summary ADD COLUMN china_exposed_services INTEGER DEFAULT 0")
    if "china_active_instances" not in existing_exposure_summary:
        cursor.execute("ALTER TABLE exposure_summary ADD COLUMN china_active_instances INTEGER DEFAULT 0")
    if "province_count" not in existing_exposure_summary:
        cursor.execute("ALTER TABLE exposure_summary ADD COLUMN province_count INTEGER DEFAULT 0")
    if "city_count" not in existing_exposure_summary:
        cursor.execute("ALTER TABLE exposure_summary ADD COLUMN city_count INTEGER DEFAULT 0")
    if "historical_vulnerable_instances" not in existing_exposure_summary:
        cursor.execute("ALTER TABLE exposure_summary ADD COLUMN historical_vulnerable_instances INTEGER DEFAULT 0")
    if "historical_vulnerable_active_instances" not in existing_exposure_summary:
        cursor.execute("ALTER TABLE exposure_summary ADD COLUMN historical_vulnerable_active_instances INTEGER DEFAULT 0")
    if "historical_matched_vulnerability_count" not in existing_exposure_summary:
        cursor.execute("ALTER TABLE exposure_summary ADD COLUMN historical_matched_vulnerability_count INTEGER DEFAULT 0")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exposure_status ON exposure_instances(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exposure_country ON exposure_instances(country_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exposure_risk ON exposure_instances(risk_level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exposure_port ON exposure_instances(port)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exposure_last_seen ON exposure_instances(last_seen)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exposure_historical_vuln_count ON exposure_instances(historical_vuln_count)")

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS probe_instances (
            ip_port TEXT PRIMARY KEY,
            ip TEXT NOT NULL,
            port INTEGER NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_active_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL,
            country_name TEXT,
            region TEXT,
            city TEXT,
            asn TEXT,
            org TEXT,
            server_version TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS probe_daily_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL,
            ip_port TEXT NOT NULL,
            is_active INTEGER NOT NULL,
            server_version TEXT,
            UNIQUE(snapshot_date, ip_port)
        )
        '''
    )

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_probe_instances_active ON probe_instances(is_active)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_probe_snapshots_date ON probe_daily_snapshots(snapshot_date)")

    conn.commit()
    conn.close()

    print(f"✅ Exposure 数据库初始化完成: {EXPOSURE_DB_PATH}")


def setup_risks_database():
    """创建 risks 数据库表结构"""
    conn = sqlite3.connect(RISKS_DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS vulnerabilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_index INTEGER NOT NULL,
            vulnerability_title TEXT NOT NULL,
            stage TEXT,
            reason TEXT,
            vulnerability_id TEXT,
            severity TEXT,
            affected_versions TEXT,
            cve TEXT,
            cwe TEXT,
            vulnerability_link TEXT,
            vulnerability_nature_id TEXT NOT NULL,
            vulnerability_nature_label TEXT NOT NULL,
            top10_primary_id TEXT,
            top10_primary_label TEXT,
            top10_match_ids TEXT,
            top10_match_labels TEXT,
            top10_match_count INTEGER DEFAULT 0,
            top10_rank INTEGER,
            mapping_confidence REAL DEFAULT 0,
            analysis_reason TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS vulnerability_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_count INTEGER,
            llm_specific_count INTEGER,
            general_software_count INTEGER,
            mapped_top10_count INTEGER,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vuln_nature ON vulnerabilities(vulnerability_nature_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vuln_top10_primary ON vulnerabilities(top10_primary_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vuln_top10_rank ON vulnerabilities(top10_rank)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vuln_severity ON vulnerabilities(severity)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vuln_source_index ON vulnerabilities(source_index)")

    conn.commit()
    conn.close()

    print(f"✅ Risks 数据库初始化完成: {RISKS_DB_PATH}")


def setup_database():
    """创建所有数据库表结构"""
    os.makedirs(DATA_DIR, exist_ok=True)
    setup_skills_database()
    setup_exposure_database()
    setup_risks_database()

if __name__ == "__main__":
    setup_database()
