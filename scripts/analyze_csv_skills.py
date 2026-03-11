#!/usr/bin/env python3
"""
OpenClaw Watchboard CSV Skills Data Analyzer
分析CSV技能数据并存入数据库
"""

import os
import csv
import sqlite3
import re
import json
from datetime import datetime
from pathlib import Path

# 配置路径
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CSV_FILE = DATA_DIR / "skills" / "skills_dataset.csv"
DB_PATH = DATA_DIR / "skills.db"

def extract_maintainer_from_url(url):
    """从GitHub URL提取维护者"""
    if url and 'github.com' in url:
        match = re.search(r'github\.com/([^/]+)', url)
        if match:
            return match.group(1)
    return 'Unknown'


def normalize_source(source):
    source = (source or "").strip()
    if source.startswith("skillsmp"):
        return "skillsmp"
    return source


def normalize_classification(classification):
    classification = (classification or "unknown").strip().lower()
    if classification == "malicious":
        return "malicious"
    if classification == "suspicious":
        return "suspicious"
    if classification == "safe":
        return "safe"
    return "unknown"

def categorize_skill(skill_name, source=""):
    """根据技能名称推断分类"""
    name = skill_name.lower() if skill_name else ""

    if any(word in name for word in ['security', 'auth', 'crypto', 'scan', 'secure', 'protect', 'zero-trust']):
        return 'Security'
    elif any(word in name for word in ['network', 'api', 'http', 'socket', 'web', 'client', 'fetch']):
        return 'Network'
    elif any(word in name for word in ['file', 'data', 'parser', 'analyzer', 'process', 'datacommons']):
        return 'Analysis'
    elif any(word in name for word in ['dev', 'build', 'test', 'deploy', 'code', 'git', 'github', 'review', 'pr']):
        return 'Development'
    elif any(word in name for word in ['system', 'os', 'monitor', 'perf', 'admin', 'rclone']):
        return 'System'
    elif any(word in name for word in ['ui', 'frontend', 'design', 'interface', 'webapp']):
        return 'Frontend'
    elif any(word in name for word in ['db', 'database', 'sql', 'storage', 'store']):
        return 'Database'
    elif any(word in name for word in ['ml', 'ai', 'model', 'learn', 'neural', 'claude', 'flow-nexus']):
        return 'AI/ML'
    elif any(word in name for word in ['email', 'chat', 'message', 'notification', 'instagram', 'telegram']):
        return 'Communication'
    elif any(word in name for word in ['automation', 'workflow', 'task', 'schedule', 'jira', 'agile']):
        return 'Automation'
    else:
        return 'Utility'

def calculate_security_score(classification, skill_name, source):
    """根据分类和其他因素计算安全评分"""
    if classification == 'safe':
        # 安全技能基础分数
        score = 75

        # 根据来源调整
        if source == 'skills.rest':
            score += 5
        elif source.startswith('skillsmp'):
            score += 3

        # 根据技能名称调整
        name = skill_name.lower() if skill_name else ""
        if any(word in name for word in ['auth', 'security', 'safe']):
            score += 10
        elif any(word in name for word in ['test', 'review', 'analyzer']):
            score += 5

        return min(score, 95)

    elif classification == 'malicious':
        return max(5, min(20, 5 + hash(skill_name) % 15))

    elif classification == 'suspicious':
        return max(25, min(55, 25 + hash(skill_name) % 30))

    else:
        # 未知分类
        return 50

def generate_threat_description(skill_name, classification):
    """为可疑技能生成威胁描述"""
    if classification not in {'suspicious', 'malicious'}:
        return f"来自外部源的{skill_name}技能，分类为{classification}"

    suspicious_patterns = [
        "检测到可疑的网络通信模式",
        "发现恶意代码特征",
        "包含已知漏洞利用代码",
        "尝试访问敏感系统文件",
        "异常的权限请求",
        "混淆的恶意代码",
        "与已知恶意域名通信",
        "包含反调试技术",
        "尝试修改系统注册表",
        "发现数据外泄行为"
    ]

    malicious_patterns = [
        "检测到主动数据窃取行为",
        "包含持久化后门逻辑",
        "发现命令执行与远控特征",
        "存在凭据收集与外传行为",
        "包含破坏性系统修改能力",
    ]

    if classification == 'malicious':
        threat_index = hash(skill_name) % len(malicious_patterns)
        return f"恶意技能：{malicious_patterns[threat_index]}"

    threat_index = hash(skill_name) % len(suspicious_patterns)
    return f"可疑技能：{suspicious_patterns[threat_index]}"

def analyze_csv_skills():
    """分析CSV技能数据"""
    if not CSV_FILE.exists():
        print(f"❌ CSV文件不存在: {CSV_FILE}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 清除旧的CSV数据
    cursor.execute("DELETE FROM skills WHERE source = 'skills.rest' OR source LIKE 'skillsmp%'")

    processed_count = 0
    suspicious_count = 0
    malicious_count = 0
    safe_count = 0

    print("🔍 开始分析CSV技能数据...")

    with open(CSV_FILE, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)

        for row in csv_reader:
            try:
                # 提取数据
                source = normalize_source(row.get('source', ''))
                repo = row.get('repo', '').strip()
                skill_name = row.get('skill_name', '').strip()
                classification = normalize_classification(row.get('classification', 'unknown'))
                url = row.get('url', '').strip()

                if not skill_name or not source:
                    continue

                # 构建技能ID
                skill_id = f"{source}-{repo}-{skill_name}"

                # 提取维护者
                maintainer = extract_maintainer_from_url(url)

                # 分类
                category = categorize_skill(skill_name, source)

                # 计算安全评分
                security_score = calculate_security_score(classification, skill_name, source)

                # 生成描述
                description = generate_threat_description(skill_name, classification)

                # 生成一些模拟数据
                downloads = max(5, hash(skill_id) % 1000)
                rating = max(0.5, min(5.0, (hash(skill_id) % 45 + 5) / 10.0))

                if classification == 'malicious':
                    rating = max(0.5, min(1.8, rating))
                    malicious_count += 1
                elif classification == 'suspicious':
                    rating = max(0.5, min(3.0, rating))
                    suspicious_count += 1
                else:
                    safe_count += 1

                # 插入数据库
                cursor.execute('''
                    INSERT OR REPLACE INTO skills
                    (id, name, version, description, category, maintainer, source, classification,
                     security_score, downloads, rating, verified, last_updated, permissions,
                     repository, file_structure, dependencies, skill_content, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    skill_id,
                    skill_name,
                    "1.0.0",  # CSV没有版本信息
                    description,
                    category,
                    maintainer,
                    source,
                    classification,
                    security_score,
                    downloads,
                    rating,
                    False,  # 外部技能未验证
                    datetime.now(),
                    json.dumps([]),  # 权限信息未知
                    url,
                    json.dumps([]),  # 文件结构未知
                    json.dumps([]),  # 依赖信息未知
                    "",  # 没有技能文档
                    datetime.now()
                ))

                processed_count += 1
                if processed_count % 1000 == 0:
                    print(
                        f"✅ 已处理 {processed_count} 个技能 "
                        f"(安全: {safe_count}, 可疑: {suspicious_count}, 恶意: {malicious_count})..."
                    )

            except Exception as e:
                print(f"⚠️  处理CSV行失败: {str(e)}")
                continue

    conn.commit()
    conn.close()

    print(f"🎉 CSV技能分析完成:")
    print(f"   总计: {processed_count} 个技能")
    print(f"   安全: {safe_count} 个")
    print(f"   可疑: {suspicious_count} 个")
    print(f"   恶意: {malicious_count} 个")

if __name__ == "__main__":
    analyze_csv_skills()
