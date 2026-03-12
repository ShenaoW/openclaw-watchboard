#!/usr/bin/env python3
"""
OpenClaw Watchboard ClawHub Skills Data Analyzer
分析ClawHub官方技能数据并存入数据库
"""

import os
import json
import sqlite3
import re
from datetime import datetime
from pathlib import Path

# 配置路径
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CLAWHUB_DIR = DATA_DIR / "skills" / "clawhub" / "skills"
DB_PATH = DATA_DIR / "skills.db"

def categorize_skill(skill_name, description="", keywords=None):
    """根据技能名称和描述推断分类"""
    content = f"{skill_name} {description}".lower()

    if any(word in content for word in ['security', 'auth', 'crypto', 'scan', 'secure', 'protect']):
        return 'Security'
    elif any(word in content for word in ['network', 'api', 'http', 'socket', 'web', 'client']):
        return 'Network'
    elif any(word in content for word in ['file', 'data', 'parser', 'analyzer', 'process']):
        return 'Analysis'
    elif any(word in content for word in ['dev', 'build', 'test', 'deploy', 'code', 'git']):
        return 'Development'
    elif any(word in content for word in ['system', 'os', 'monitor', 'perf', 'admin']):
        return 'System'
    elif any(word in content for word in ['ui', 'frontend', 'design', 'interface']):
        return 'Frontend'
    elif any(word in content for word in ['db', 'database', 'sql', 'storage', 'store']):
        return 'Database'
    elif any(word in content for word in ['ml', 'ai', 'model', 'learn', 'neural']):
        return 'AI/ML'
    elif any(word in content for word in ['email', 'chat', 'message', 'notification']):
        return 'Communication'
    elif any(word in content for word in ['automation', 'workflow', 'task', 'schedule']):
        return 'Automation'
    else:
        return 'Utility'

def calculate_security_score(skill_data, has_skill_md=False):
    """计算安全评分"""
    score = 85  # 基础分数（ClawHub官方技能基础较高）

    # 有完整文档加分
    if has_skill_md:
        score += 5

    # 有版本历史加分
    if skill_data.get('history') and len(skill_data['history']) > 0:
        score += 5

    # 最近更新加分
    if skill_data.get('latest', {}).get('publishedAt'):
        try:
            publish_time = datetime.fromtimestamp(skill_data['latest']['publishedAt'] / 1000)
            days_ago = (datetime.now() - publish_time).days
            if days_ago < 30:
                score += 5
            elif days_ago < 90:
                score += 3
        except:
            pass

    return min(score, 100)

def extract_maintainer_from_url(url):
    """从GitHub URL提取维护者"""
    if url and 'github.com' in url:
        match = re.search(r'github\.com/([^/]+)', url)
        if match:
            return match.group(1)
    return 'Unknown'

def analyze_clawhub_skills():
    """分析ClawHub技能数据"""
    if not CLAWHUB_DIR.exists():
        print(f"❌ ClawHub数据目录不存在: {CLAWHUB_DIR}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 清除旧的ClawHub数据
    cursor.execute("DELETE FROM skills WHERE source = 'clawhub'")

    processed_count = 0

    print("🔍 开始分析ClawHub技能数据...")

    for owner_dir in CLAWHUB_DIR.iterdir():
        if not owner_dir.is_dir():
            continue

        for skill_dir in owner_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            meta_file = skill_dir / "_meta.json"
            skill_file = skill_dir / "SKILL.md"

            if not meta_file.exists():
                continue

            try:
                # 读取元数据
                with open(meta_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 移除BOM字符
                    content = content.lstrip('\ufeff')
                    meta_data = json.loads(content)

                # 读取技能文档
                skill_content = ""
                if skill_file.exists():
                    with open(skill_file, 'r', encoding='utf-8') as f:
                        skill_content = f.read()

                # 提取基本信息
                skill_name = meta_data.get('slug', skill_dir.name)
                display_name = meta_data.get('displayName', skill_name)
                version = meta_data.get('latest', {}).get('version', '1.0.0')

                # 从SKILL.md提取描述
                description = display_name
                if skill_content:
                    # 尝试从SKILL.md提取description
                    description_match = re.search(r'description:\s*(.+)', skill_content)
                    if description_match:
                        description = description_match.group(1).strip()
                    else:
                        # 提取第一个非标题段落作为描述
                        lines = skill_content.split('\n')
                        for line in lines[5:]:  # 跳过前几行元数据
                            line = line.strip()
                            if line and not line.startswith('#') and not line.startswith('---'):
                                description = line[:200] + ('...' if len(line) > 200 else '')
                                break

                # 计算安全评分
                security_score = calculate_security_score(meta_data, skill_file.exists())

                # 分类
                category = categorize_skill(skill_name, description)

                # 文件结构
                file_structure = []
                try:
                    for item in skill_dir.iterdir():
                        if not item.name.startswith('.'):
                            file_structure.append(item.name)
                except:
                    pass

                # 构建技能ID
                skill_id = f"clawhub-{owner_dir.name}-{skill_name}"

                # 最后更新时间
                last_updated = ""
                if meta_data.get('latest', {}).get('publishedAt'):
                    try:
                        last_updated = datetime.fromtimestamp(meta_data['latest']['publishedAt'] / 1000)
                    except:
                        pass

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
                    version,
                    description,
                    category,
                    owner_dir.name,
                    'clawhub',
                    'safe',  # ClawHub技能默认标记为安全
                    security_score,
                    0,  # ClawHub没有下载统计
                    0.0,  # ClawHub没有评分系统
                    True,  # ClawHub技能都是已验证的
                    last_updated,
                    json.dumps([]),  # 权限信息需要进一步分析
                    f"https://github.com/openclaw/skills/tree/main/{owner_dir.name}/{skill_name}",
                    json.dumps(file_structure),
                    json.dumps(meta_data.get('history', [])),
                    skill_content,
                    datetime.now()
                ))

                processed_count += 1
                if processed_count % 100 == 0:
                    print(f"✅ 已处理 {processed_count} 个技能...")

            except Exception as e:
                print(f"⚠️  处理技能失败 {owner_dir.name}/{skill_dir.name}: {str(e)}")
                continue

    conn.commit()
    conn.close()

    print(f"🎉 ClawHub技能分析完成，共处理 {processed_count} 个技能")

if __name__ == "__main__":
    analyze_clawhub_skills()
