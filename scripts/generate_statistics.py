#!/usr/bin/env python3
"""
OpenClaw Watchboard Skills Statistics Generator
生成技能统计数据
"""

import sqlite3
from datetime import datetime
from pathlib import Path

# 配置路径
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DB_PATH = DATA_DIR / "skills.db"

def generate_statistics():
    """生成统计数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("📊 开始生成统计数据...")

    # 清除旧的统计数据
    cursor.execute("DELETE FROM skill_stats")
    cursor.execute("DELETE FROM developer_stats")
    cursor.execute("DELETE FROM category_stats")

    # 1. 基础统计
    cursor.execute("SELECT COUNT(*) FROM skills")
    total_skills = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM skills WHERE source = 'clawhub'")
    source_clawhub = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM skills WHERE source = 'skills.rest'")
    source_skills_rest = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM skills WHERE source LIKE 'skillsmp%'")
    source_skillsmp = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM skills WHERE classification = 'safe'")
    classification_safe = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM skills WHERE classification = 'suspicious'")
    classification_suspicious = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM skills WHERE classification = 'malicious'")
    classification_malicious = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM skills WHERE classification = 'unknown'")
    classification_unknown = cursor.fetchone()[0]

    # 插入基础统计
    cursor.execute('''
        INSERT INTO skill_stats
        (total_skills, source_clawhub, source_skills_rest, source_skillsmp,
         classification_safe, classification_suspicious, classification_malicious, classification_unknown)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (total_skills, source_clawhub, source_skills_rest, source_skillsmp,
          classification_safe, classification_suspicious, classification_malicious, classification_unknown))

    print(f"   总技能数: {total_skills}")
    print(f"   ClawHub: {source_clawhub}")
    print(f"   Skills.rest: {source_skills_rest}")
    print(f"   SkillsMP: {source_skillsmp}")
    print(f"   安全: {classification_safe}")
    print(f"   可疑: {classification_suspicious}")
    print(f"   恶意: {classification_malicious}")
    print(f"   未知: {classification_unknown}")

    # 2. 开发者统计
    cursor.execute('''
        SELECT
            maintainer,
            COUNT(*) as total,
            SUM(CASE WHEN classification = 'safe' THEN 1 ELSE 0 END) as safe,
            SUM(CASE WHEN classification = 'suspicious' THEN 1 ELSE 0 END) as suspicious,
            SUM(CASE WHEN classification = 'malicious' THEN 1 ELSE 0 END) as malicious,
            SUM(CASE WHEN classification = 'unknown' THEN 1 ELSE 0 END) as unknown
        FROM skills
        WHERE maintainer != 'Unknown'
        GROUP BY maintainer
        ORDER BY total DESC
        LIMIT 50
    ''')

    developer_stats = cursor.fetchall()
    for dev_stat in developer_stats:
        cursor.execute('''
            INSERT INTO developer_stats
            (developer, total_skills, safe_skills, suspicious_skills, malicious_skills, unknown_skills)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', dev_stat)

    print(f"   开发者统计: {len(developer_stats)} 个开发者")

    # 3. 分类统计
    cursor.execute('''
        SELECT
            category,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / ?, 2) as percentage
        FROM skills
        GROUP BY category
        ORDER BY count DESC
    ''', (total_skills,))

    category_stats = cursor.fetchall()
    for cat_stat in category_stats:
        cursor.execute('''
            INSERT INTO category_stats
            (category, skill_count, percentage)
            VALUES (?, ?, ?)
        ''', cat_stat)

    print(f"   分类统计: {len(category_stats)} 个分类")

    conn.commit()
    conn.close()

    print("✅ 统计数据生成完成!")

if __name__ == "__main__":
    generate_statistics()
